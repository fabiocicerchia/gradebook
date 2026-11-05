"""Recognising test files and what is inside them: the rules that apply the
patterns in `patterns` to one file's text."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .base import (
    CONDITION_WINDOW,
    GIANT_CASE_LINES,
    JS_EXT,
    LANG_BY_EXT,
    LONG_CASE_LINES,
    MANY_ASSERTIONS,
    MIN_MEANINGFUL_WORDS,
    MIN_WORDS_WITH_CONTEXT,
    MOSTLY,
    TEST_DIR_NAMES,
    FileInfo,
    Finding,
    Profile,
)
from .patterns import (
    ASSERT_RE,
    BARE_ASSERT_RE,
    BEHAVIOUR_WORDS,
    BOUNDARY_NAME_WORDS,
    BOUNDARY_RE,
    BRANCH_RE,
    BRITTLE_SELECTOR_RE,
    CASE_RE,
    CHATTER_RE,
    COMMENT_RE,
    COMMENTED_ASSERT_RE,
    CONDITION_WORDS,
    DEAD_BRANCH_RE,
    DEFAULT_PROFILE,
    DOUBLE_CLEANUP_RE,
    DOUBLE_RE,
    ELSE_RE,
    ENV_COUPLING_RE,
    ERROR_ASSERT_RE,
    ERROR_NAME_WORDS,
    FILLER_WORDS,
    FOCUS_RE,
    FROZEN_TIME_RE,
    GENERIC_ASSERT,
    GREEDY_CATCH_RE,
    GUARD_RE,
    JS_IMPORT_RE,
    KIND_CONTENT_HINTS,
    KIND_DIR_HINTS,
    LANGUAGE_PROFILES,
    LITERAL_RE,
    MIRROR_RE,
    MOCK_ASSERT_RE,
    NAME_RE,
    ORDER_DEPENDENT_RE,
    PLATFORM_RE,
    PRIVATE_ACCESS_RE,
    PY_IMPORT_RE,
    ROBUST_SELECTOR_RE,
    SEEDED_RANDOM_RE,
    SETUP_BLOCK_RE,
    SKIP_NO_REASON_RE,
    SKIP_RE,
    SLEEP_RE,
    SPY_RE,
    STUB_RE,
    STYLE_FLAGS,
    SWALLOW_RE,
    TAUTOLOGY_RE,
    UNFROZEN_TIME_RE,
    UNINFORMATIVE_ASSERT_RE,
    UNSEEDED_RANDOM_RE,
    WEAK_ASSERT_RE,
)

# ---------------------------------------------------------------- detection


# How each ecosystem spells a test file. A table rather than a chain of
# returns: adding a language is a row, and the rules sit side by side where
# they can be compared.
def _jvm_test_name(stem: str, _name: str, _parts: set[str]) -> bool:
    """JUnit's conventions, which allow the marker at either end of the name."""
    return stem.endswith(("Test", "Tests", "Spec", "IT", "ITCase")) or stem.startswith("Test")


_TEST_NAME_RULES: dict[str, Callable[[str, str, set[str]], bool]] = {
    ".py": lambda stem, name, _parts: name.startswith("test_") or stem.endswith("_test") or name == "conftest.py",
    ".go": lambda stem, _name, _parts: stem.endswith("_test"),
    ".java": _jvm_test_name,
    ".kt": _jvm_test_name,
    ".rb": lambda stem, _name, _parts: stem.endswith(("_spec", "_test")),
    ".php": lambda stem, _name, _parts: stem.endswith(("Test", "Spec")),
    ".cs": lambda stem, _name, _parts: stem.endswith(("Test", "Tests", "Spec")),
    ".exs": lambda stem, _name, _parts: stem.endswith("_test"),
    ".scala": lambda stem, _name, _parts: stem.endswith(("Spec", "Test", "Suite")),
    ".sh": lambda stem, _name, _parts: stem.startswith("test") or stem.endswith("_test"),
    ".bash": lambda stem, _name, _parts: stem.startswith("test") or stem.endswith("_test"),
    **{
        ext: lambda stem, _name, parts: bool(re.search(r"\.(test|spec)$", stem)) or "__tests__" in parts
        for ext in JS_EXT
    },
}


def is_test_file(rel: Path) -> bool:
    """True if the path looks like a test/spec file in any common ecosystem."""
    suffix, stem, name = rel.suffix, rel.stem, rel.name
    parts = {p.lower() for p in rel.parts[:-1]}
    if suffix == ".feature":
        return True
    rule = _TEST_NAME_RULES.get(suffix)
    if rule and rule(stem, name, parts):
        return True
    # Anything of a known language living under a test directory.
    return suffix in LANG_BY_EXT and bool(parts & TEST_DIR_NAMES)


def name_words(name: str) -> list[str]:
    """Split a test name into meaningful lowercase words."""
    text = re.sub(r"^(?:test[_\s-]*|should[_\s-]+|it[_\s-]+)", "", name.strip(), flags=re.IGNORECASE)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-.]+", " ", text)
    return [w.lower() for w in re.findall(r"[A-Za-z]+|\d+", text)]


def classify_name(name: str) -> tuple[bool, bool, bool]:
    """Return (is_placeholder, is_descriptive, states_a_condition) for a test name."""
    words = name_words(name)
    meaningful = [w for w in words if not w.isdigit() and w not in FILLER_WORDS]
    placeholder = not meaningful
    behaviour = any(w in BEHAVIOUR_WORDS for w in words) or "should" in name.lower()
    condition = any(w in CONDITION_WORDS for w in words)
    descriptive = not placeholder and (
        len(meaningful) >= MIN_MEANINGFUL_WORDS
        or (len(meaningful) >= MIN_WORDS_WITH_CONTEXT and (behaviour or condition))
    )
    return placeholder, descriptive, condition


def extract_names(text: str, lang: str) -> list[str]:
    names = []
    for pattern in NAME_RE.get(lang, []):
        for match in pattern.finditer(text):
            value = next((g for g in match.groups() if g), None)
            if value:
                names.append(value.strip())
    return names


def conditional_logic(block: str, window: int = CONDITION_WINDOW) -> int:
    """Branches that decide what a test checks, ignoring assertion guards."""
    count = 0
    for match in BRANCH_RE.finditer(block):
        tail = block[match.start() : match.start() + window]
        if ELSE_RE.search(tail[len(match.group(0)) :]):
            count += 1  # an if/else picks between outcomes
        elif not GUARD_RE.search(tail):
            count += 1  # a branch that guards behaviour, not a failure
    return count


def blend_profile(language_lines: dict[str, int]) -> Profile:
    """Weight each ecosystem's thresholds by how much of the source it is."""
    total = sum(language_lines.values())
    if not total:
        return {
            "test_code_ratio": DEFAULT_PROFILE[0],
            "cases_per_source": DEFAULT_PROFILE[1],
            "bare_assert_check": False,
            "spec_style_idiomatic": False,
            "languages": [],
        }
    ratio = cases = 0.0
    bare = spec = 0.0
    for lang, lines in language_lines.items():
        target_ratio, target_cases, bare_check, spec_ok = LANGUAGE_PROFILES.get(lang, DEFAULT_PROFILE)
        share = lines / total
        ratio += target_ratio * share
        cases += target_cases * share
        bare += share if bare_check else 0.0
        spec += share if spec_ok else 0.0
    dominant = sorted(language_lines, key=lambda lang: language_lines[lang], reverse=True)[:2]
    return {
        "test_code_ratio": round(ratio, 2),
        "cases_per_source": round(cases, 2),
        # Only apply an ecosystem-specific check when that ecosystem is most of the repo.
        "bare_assert_check": bare >= MOSTLY,
        "spec_style_idiomatic": spec >= MOSTLY,
        "languages": dominant,
    }


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def normalise_body(block: str) -> str:
    """A case body with its name, comments and literals removed, for duplicate hunting."""
    body = block.split("\n", 1)[1] if "\n" in block else ""
    body = COMMENT_RE.sub("", body)
    body = LITERAL_RE.sub("@", body)
    return re.sub(r"\s+", " ", body).strip()


def imported_project_names(text: str, lang: str, modules: set[str]) -> list[str]:
    """Names a test pulls in from the project's own code."""
    names = []
    if lang == "python":
        for module, raw in PY_IMPORT_RE.findall(text):
            root = module.lstrip(".").split(".")[0]
            if not module.startswith(".") and root not in modules:
                continue
            for part in raw.strip("()").split(","):
                name = part.strip().split(" as ")[0].strip()
                if name and name != "*" and name.isidentifier():
                    names.append(name)
    elif lang in {"javascript", "typescript"}:
        for match in JS_IMPORT_RE.finditer(text):
            raw = match.group(1) or match.group(3) or ""
            for part in raw.split(","):
                name = part.strip().split(" as ")[0].strip()
                if name and name.isidentifier():
                    names.append(name)
    return names


def classify_kind(rel: Path, text: str) -> tuple[str, set[str]]:
    """Return (kind, flags) for one test file. Most specific signal wins."""
    flags = set()
    dirs = {p.lower() for p in rel.parts[:-1]} | {rel.stem.lower()}
    kind = None
    for candidate, hints in KIND_DIR_HINTS:
        if dirs & hints:
            kind = candidate
            break
    # Conjoined Twins: filed as a unit test, but talking to something real.
    if kind == "unit" and any(
        pattern.search(text) for name, pattern in KIND_CONTENT_HINTS if name in {"integration", "e2e"}
    ):
        flags.add("conjoined")
    if kind is None:
        for candidate, pattern in KIND_CONTENT_HINTS:
            if pattern.search(text):
                kind = candidate
                break
    if rel.suffix == ".feature":
        kind = kind or "e2e"
        flags.add("bdd")
    if kind is None:
        kind = "unit"
    flags |= {flag for pattern, flag in STYLE_FLAGS if pattern.search(text)}
    return kind, flags


def with_decorators(text: str, start: int) -> int:
    """Extend a case start backwards over its decorators/annotations."""
    position = start
    while position > 0:
        line_start = text.rfind("\n", 0, position - 1) + 1
        if line_start >= position:
            break
        if not re.match(r"^[ \t]*[@\[]", text[line_start:position]):
            break
        position = line_start
    return position


@dataclass
class _CaseTally:
    """What one file's cases add up to, before the file-level signals."""

    without: int = 0
    doubles: int = 0
    cases_with_doubles: int = 0
    mock_only: int = 0
    weak_assertions: int = 0
    weak_only: int = 0
    error_cases: int = 0
    giant_cases: int = 0
    roulette_cases: int = 0
    branching_cases: int = 0
    boundary_cases: int = 0
    bodies: list = field(default_factory=list)
    mirrors: list = field(default_factory=list)


def _tally_assertions(tally: _CaseTally, block: str, assert_re: re.Pattern, bare_re: re.Pattern | None) -> int:
    """How one case asserts: how many, how many of those are weak, and whether
    it only ever checks its doubles. Returns the assertion count."""
    assertions = len(assert_re.findall(block))
    mock_assertions = len(MOCK_ASSERT_RE.findall(block))
    block_doubles = len(DOUBLE_RE.findall(block))
    weak = len(WEAK_ASSERT_RE.findall(block)) + len(TAUTOLOGY_RE.findall(block))
    if bare_re:
        weak += len(bare_re.findall(block))
    weak = min(weak, assertions)
    tally.weak_assertions += weak
    if not assertions:
        tally.without += 1
    elif weak == assertions:
        # It asserts, but only that something is truthy/not-null/a snapshot.
        tally.weak_only += 1
    if block_doubles:
        tally.cases_with_doubles += 1
        tally.doubles += block_doubles
    # A case whose every assertion is an interaction check tests the double,
    # not the behaviour.
    if mock_assertions and assertions <= mock_assertions:
        tally.mock_only += 1
    return assertions


def _tally_cases(
    rel: Path, text: str, blocks: list[int], assert_re: re.Pattern, bare_re: re.Pattern | None
) -> _CaseTally:
    """Walk the file's cases once and count what each one is: how it asserts,
    whether it asserts at all, how big it got, and what it duplicates."""
    tally = _CaseTally()
    for i, start in enumerate(blocks):
        end = blocks[i + 1] if i + 1 < len(blocks) else len(text)
        block = text[start:end]
        assertions = _tally_assertions(tally, block, assert_re, bare_re)
        first_line = block.split("\n", 1)[0]
        words = set(name_words(first_line))
        if ERROR_ASSERT_RE.search(block) or words & ERROR_NAME_WORDS:
            tally.error_cases += 1
        if BOUNDARY_RE.search(block) or words & BOUNDARY_NAME_WORDS:
            tally.boundary_cases += 1
        body = normalise_body(block)
        if len(body) >= LONG_CASE_LINES:
            tally.bodies.append((body, line_of(text, start)))

        body_lines = [ln for ln in block.splitlines()[1:] if ln.strip()]
        if len(body_lines) > GIANT_CASE_LINES:
            tally.giant_cases += 1
        if assertions > MANY_ASSERTIONS:
            tally.roulette_cases += 1
        if conditional_logic(block) > 0:
            tally.branching_cases += 1
        for match in MIRROR_RE.finditer(block):
            tally.mirrors.append(
                {
                    "file": str(rel),
                    "line": line_of(text, start + match.start()),
                    "kind": "mirror-assertion",
                    "message": "the expected value is recomputed from the inputs — "
                    "the test shares the formula it is meant to check",
                }
            )
    return tally


def _brittle_and_private(rel: Path, text: str) -> tuple[list[Finding], list[Finding]]:
    """(brittle selectors, implementation access) — the two findings that come
    from reading the file rather than its cases."""
    brittle = []
    if not ROBUST_SELECTOR_RE.search(text):
        for match in BRITTLE_SELECTOR_RE.finditer(text):
            brittle.append(
                {
                    "file": str(rel),
                    "line": line_of(text, match.start()),
                    "kind": "brittle-selector",
                    "message": "positional or generated locator — prefer a role, label "
                    "or data-testid that survives a redesign",
                }
            )

    suppressed = []
    for match in PRIVATE_ACCESS_RE.finditer(text):
        member = next((g for g in match.groups() if g), "an internal")
        suppressed.append(
            {
                "file": str(rel),
                "line": line_of(text, match.start()),
                "kind": "implementation-access",
                "message": f"reaches into `{member}` — testing the implementation, not the behaviour",
            }
        )
    return brittle, suppressed


def _name_tally(names: list[str]) -> tuple[int, int, int, int, list[str]]:
    """Placeholder, descriptive and conditional counts, total words, and the
    names that do not describe anything."""
    placeholder = descriptive = conditional = words = 0
    bad_names = []
    for name in names:
        is_placeholder, is_descriptive, has_condition = classify_name(name)
        words += len(name_words(name))
        placeholder += is_placeholder
        descriptive += is_descriptive
        conditional += has_condition
        if not is_descriptive:
            bad_names.append(name)
    return placeholder, descriptive, conditional, words, bad_names


def _setup_lines(text: str) -> int:
    """Non-blank lines in the indented body of the first setUp/beforeEach."""
    setup_lines = 0
    setup_match = SETUP_BLOCK_RE.search(text)
    if setup_match:
        rest = text[setup_match.end() :].splitlines()
        for line in rest:
            if line.strip() and not line[:1].isspace():
                break
            setup_lines += 1 if line.strip() else 0
    return setup_lines


def _suppressed_failures(rel: Path, text: str) -> list[Finding]:
    suppressed = []
    for pattern, message in (
        (COMMENTED_ASSERT_RE, "assertion commented out"),
        (GREEDY_CATCH_RE, "failure logged and swallowed — the test still passes"),
        (SWALLOW_RE, "failure swallowed by an empty except/catch"),
        (DEAD_BRANCH_RE, "assertions behind an `if False` branch"),
        (SKIP_NO_REASON_RE, "test skipped with no reason given"),
    ):
        for match in pattern.finditer(text):
            suppressed.append(
                {
                    "file": str(rel),
                    "line": line_of(text, match.start()),
                    "kind": "suppressed-failure",
                    "message": message,
                }
            )
    return suppressed


def analyse_test_file(rel: Path, text: str, lang: str) -> FileInfo:
    case_re = CASE_RE.get(lang)
    assert_re = ASSERT_RE.get(lang, GENERIC_ASSERT)
    starts = [m.start() for m in case_re.finditer(text)] if case_re else []

    bare_re = BARE_ASSERT_RE.get(lang)
    bodies = []
    giant_cases = roulette_cases = branching_cases = boundary_cases = 0
    mirrors = []
    blocks = [with_decorators(text, start) for start in starts]
    without = doubles = cases_with_doubles = mock_only = 0
    weak_assertions = weak_only = error_cases = 0
    tally = _tally_cases(rel, text, blocks, assert_re, bare_re)
    bodies, mirrors = tally.bodies, tally.mirrors
    giant_cases, roulette_cases = tally.giant_cases, tally.roulette_cases
    branching_cases, boundary_cases = tally.branching_cases, tally.boundary_cases
    without, doubles = tally.without, tally.doubles
    cases_with_doubles, mock_only = tally.cases_with_doubles, tally.mock_only
    weak_assertions, weak_only, error_cases = tally.weak_assertions, tally.weak_only, tally.error_cases

    # Doubles wired up in setUp/beforeEach, outside any single case.
    doubles += len(DOUBLE_RE.findall(text[: blocks[0]] if blocks else text))

    names = extract_names(text, lang)
    placeholder, descriptive, conditional, words, bad_names = _name_tally(names)

    uninformative = len(UNINFORMATIVE_ASSERT_RE[lang].findall(text)) if lang in UNINFORMATIVE_ASSERT_RE else 0
    chatter = len(CHATTER_RE.findall(text))
    platform_branches = len(PLATFORM_RE.findall(text))
    frozen = bool(FROZEN_TIME_RE.search(text))
    seeded = bool(SEEDED_RANDOM_RE.search(text))
    unfrozen_time = 0 if frozen else len(UNFROZEN_TIME_RE.findall(text))
    unseeded_random = 0 if seeded else len(UNSEEDED_RANDOM_RE.findall(text))
    env_coupling = len(ENV_COUPLING_RE.findall(text))
    order_dependent = len(ORDER_DEPENDENT_RE.findall(text))

    setup_lines = _setup_lines(text)

    brittle, suppressed = _brittle_and_private(rel, text)
    suppressed.extend(_suppressed_failures(rel, text))

    kind, flags = classify_kind(rel, text)
    return {
        "file": str(rel),
        "case_bodies": bodies,
        "suppressed": suppressed,
        "mirrors": mirrors,
        "boundary_cases": boundary_cases,
        "uninformative_assertions": uninformative,
        "chatter": chatter,
        "platform_branches": platform_branches,
        "brittle": brittle,
        "private_access": sum(1 for f in suppressed if f["kind"] == "implementation-access"),
        "giant_cases": giant_cases,
        "roulette_cases": roulette_cases,
        "branching_cases": branching_cases,
        "setup_lines": setup_lines,
        "unfrozen_time": unfrozen_time,
        "unseeded_random": unseeded_random,
        "env_coupling": env_coupling,
        "order_dependent": order_dependent,
        "lang": lang,
        "kind": kind,
        "flags": sorted(flags),
        "cases": len(starts),
        "assertions": len(assert_re.findall(text)),
        "cases_without_assertions": without,
        "skips": len(SKIP_RE.findall(text)),
        "focused": len(FOCUS_RE.findall(text)),
        "sleeps": len(SLEEP_RE.findall(text)),
        "weak_assertions": weak_assertions,
        "weak_only_cases": weak_only,
        "error_cases": error_cases,
        "doubles": doubles,
        "cases_with_doubles": cases_with_doubles,
        "mock_only_cases": mock_only,
        "double_cleanup": bool(DOUBLE_CLEANUP_RE.search(text)),
        "spies": bool(SPY_RE.search(text)),
        "stubs": bool(STUB_RE.search(text)),
        "names": names,
        "test_names": len(names),
        "placeholder_names": placeholder,
        "descriptive_names": descriptive,
        "conditional_names": conditional,
        "name_words": words,
        "bad_names": bad_names,
    }
