"""Walking a tree and gathering everything the score is computed from."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .base import MAX_NAME_WORDS_FOR_MIRROR, Stats
from .coverage import (
    CI_COVERAGE_RE,
    CI_STRICT_RE,
    COVERAGE_CONFIG_FILES,
    COVERAGE_TOOL_RE,
    TEST_CMD_RE,
    find_threshold,
    is_ci_file,
    measure_coverage,
    measure_mutation,
)
from .detection import (
    FILLER_WORDS,
    MUTATION_RE,
    PHANTOM_LANGS,
    SERIAL_ONLY_RE,
    SYMBOL_RE,
    analyse_test_file,
    blend_profile,
    imported_project_names,
    is_test_file,
    language_of,
    name_words,
    read_text,
    walk,
)
from .git import find_hotspots, git_history
from .severity import FLAG_ORDER, severity_for
from .substance import find_decorative, find_duplicates, find_phantoms, find_stale, source_stem

# ------------------------------------------------------------------ collect


@dataclass
class _WalkState:
    """What the walk gathers for the whole-project passes that come after it."""

    symbols: set[str] = field(default_factory=set)
    source_symbols: set[str] = field(default_factory=set)
    modules: set[str] = field(default_factory=set)
    test_names: list[str] = field(default_factory=list)
    test_paths: list[Path] = field(default_factory=list)
    source_paths: list[str] = field(default_factory=list)
    source_by_stem: dict[str, Path] = field(default_factory=dict)
    bodies_by_file: list[tuple[str, list]] = field(default_factory=list)
    imports_by_file: list[tuple[str, set[str]]] = field(default_factory=list)


@dataclass
class _ConfigTexts:
    """The two text buckets the threshold search reads at the end of the walk:
    coverage config files and CI workflows."""

    config: list[str] = field(default_factory=list)
    ci: list[str] = field(default_factory=list)


def _scrape_ci(stats: Stats, rel: Path, abs_path: Path, ci_texts: list[str]) -> None:
    """What one CI workflow says: whether it runs the suite, measures
    coverage, fails on it, mutates, or pins itself to one worker."""
    text = read_text(abs_path) or ""
    ci_texts.append(text)
    stats["ci_files"].append(str(rel))
    if TEST_CMD_RE.search(text):
        stats["ci_runs_tests"] = True
    if CI_COVERAGE_RE.search(text):
        stats["ci_coverage"] = True
    if CI_STRICT_RE.search(text):
        stats["ci_strict"] = True
    if MUTATION_RE.search(text):
        stats["mutation_testing"] = True
    if SERIAL_ONLY_RE.search(text):
        stats["serial_only"] = True


def _scrape_config(stats: Stats, rel: Path, abs_path: Path, texts: _ConfigTexts, *, in_artifact: bool) -> None:
    """What one file says about how the suite is run: coverage config, CI
    workflows, and the first coverage or mutation report found."""
    config_texts, ci_texts = texts.config, texts.ci
    name = rel.name
    if not in_artifact and (name in COVERAGE_CONFIG_FILES or name.startswith(".coveragerc")):
        text = read_text(abs_path)
        if text:
            config_texts.append(text)
            if COVERAGE_TOOL_RE.search(text):
                stats["coverage_config"].append(str(rel))
            if MUTATION_RE.search(text):
                stats["mutation_testing"] = True
            if SERIAL_ONLY_RE.search(text):
                stats["serial_only"] = True
    if not in_artifact and is_ci_file(rel):
        _scrape_ci(stats, rel, abs_path, ci_texts)
    if stats["coverage_measured"] is None:
        pct, per_file = measure_coverage(rel, abs_path)
        if pct is not None:
            stats["coverage_measured"] = pct
            stats["coverage_source"] = str(rel)
            stats["coverage_by_file"] = per_file
    if stats["mutation_measured"] is None:
        pct = measure_mutation(rel, abs_path)
        if pct is not None:
            stats["mutation_measured"] = pct
            stats["mutation_source"] = str(rel)


# Which kind of double a file uses, by the count it reported.
_DOUBLE_KINDS = (("spies", "spies"), ("stubs", "stubs"), ("doubles", "mocks"))


def _symbols_in(text: str, lang: str) -> set[str]:
    """Every identifier this file defines or imports, as its language spells it."""
    found: set[str] = set()
    for pattern in SYMBOL_RE.get(lang, []):
        for match in pattern.findall(text):
            for raw in str(match).split(","):
                name = raw.strip().split(" as ")[-1].strip()
                if name.isidentifier():
                    found.add(name)
    return found


def _fold_test_file(stats: Stats, rel: Path, text: str, lang: str, walk_state: _WalkState) -> None:
    """One test file's measurements, folded into the totals and into the
    per-file records the whole-project passes read afterwards."""
    symbols, test_names = walk_state.symbols, walk_state.test_names
    bodies_by_file, test_paths = walk_state.bodies_by_file, walk_state.test_paths
    imports_by_file, modules = walk_state.imports_by_file, walk_state.modules
    stats["test_files"] += 1
    stats["test_languages"][lang] += 1
    stats["test_lines"] += sum(1 for line in text.splitlines() if line.strip())
    if lang == "feature":
        stats["feature_files"] += 1
    info = analyse_test_file(rel, text, lang)
    stats["kind_files"][info["kind"]] += 1
    stats["kind_cases"][info["kind"]] += info["cases"]
    for flag in info["flags"]:
        stats["flag_files"][flag] += 1
    if "conjoined" in info["flags"]:
        stats["conjoined_files"] += 1
        stats["findings"].append(
            {
                "file": str(rel),
                "line": 0,
                "kind": "conjoined-twin",
                "message": "filed as a unit test but talks to a real database, HTTP "
                "service or browser — it is an integration test",
            }
        )
    for key in (
        "cases",
        "assertions",
        "cases_without_assertions",
        "skips",
        "focused",
        "sleeps",
        "weak_assertions",
        "weak_only_cases",
        "error_cases",
        "giant_cases",
        "roulette_cases",
        "branching_cases",
        "chatter",
        "platform_branches",
        "boundary_cases",
        "uninformative_assertions",
        "unfrozen_time",
        "unseeded_random",
        "env_coupling",
        "order_dependent",
        "doubles",
        "cases_with_doubles",
        "mock_only_cases",
        "test_names",
        "placeholder_names",
        "descriptive_names",
        "conditional_names",
        "name_words",
    ):
        stats[key] += info[key]
    stats["double_cleanup"] = stats["double_cleanup"] or info["double_cleanup"]
    stats["double_kinds"].update(kind for key, kind in _DOUBLE_KINDS if info[key])
    stats["bad_names"].extend(info["bad_names"][:3])
    test_names.extend(info["names"])
    stats["findings"].extend(info["suppressed"])
    stats["findings"].extend(info["mirrors"][:5])
    stats["findings"].extend(info["brittle"][:5])
    stats["mirror_assertions"] += len(info["mirrors"])
    stats["brittle_selectors"] += len(info["brittle"])
    stats["private_access"] += info["private_access"]
    stats["setup_lines"] = max(stats["setup_lines"], info["setup_lines"])
    bodies_by_file.append((str(rel), info["case_bodies"]))
    test_paths.append(rel)
    symbols |= _symbols_in(text, lang)
    if lang in PHANTOM_LANGS:
        imports_by_file.append((str(rel), imported_project_names(text, lang, modules)))
    if "bdd" in info["flags"]:
        stats["bdd_cases"] += info["cases"]
    elif "spec-style" in info["flags"]:
        stats["spec_cases"] += info["cases"]


def _empty_stats(root: Path) -> Stats:
    """Every counter this pass fills, at zero."""
    return {
        "root": str(root.resolve()),
        "source_files": 0,
        "test_files": 0,
        "languages": Counter(),
        "language_lines": Counter(),
        "test_languages": Counter(),
        "kind_files": Counter(),
        "kind_cases": Counter(),
        "flag_files": Counter(),
        "cases": 0,
        "assertions": 0,
        "cases_without_assertions": 0,
        "skips": 0,
        "focused": 0,
        "sleeps": 0,
        "feature_files": 0,
        "bdd_cases": 0,
        "spec_cases": 0,
        "weak_assertions": 0,
        "weak_only_cases": 0,
        "error_cases": 0,
        "giant_cases": 0,
        "roulette_cases": 0,
        "mirror_assertions": 0,
        "brittle_selectors": 0,
        "private_access": 0,
        "branching_cases": 0,
        "setup_lines": 0,
        "unfrozen_time": 0,
        "unseeded_random": 0,
        "env_coupling": 0,
        "order_dependent": 0,
        "doubles": 0,
        "cases_with_doubles": 0,
        "mock_only_cases": 0,
        "double_cleanup": False,
        "double_kinds": set(),
        "test_names": 0,
        "method_mirror_names": 0,
        "source_lines": 0,
        "test_lines": 0,
        "placeholder_names": 0,
        "descriptive_names": 0,
        "conditional_names": 0,
        "name_words": 0,
        "bad_names": [],
        "findings": [],
        "duplicate_cases": 0,
        "phantom_symbols": 0,
        "suppressed_failures": 0,
        "stale_tests": 0,
        "decorative_tests": 0,
        "paired_tests": 0,
        "hot_files": 0,
        "untested_hot_files": 0,
        "hot_coverage": None,
        "chatter": 0,
        "platform_branches": 0,
        "boundary_cases": 0,
        "uninformative_assertions": 0,
        "serial_only": False,
        "conjoined_files": 0,
        "mutation_testing": False,
        "mutation_measured": None,
        "mutation_source": None,
        "coverage_config": [],
        "coverage_threshold": None,
        "coverage_measured": None,
        "coverage_source": None,
        "coverage_by_file": {},
        "ci_files": [],
        "ci_runs_tests": False,
        "ci_coverage": False,
        "ci_strict": False,
        "git": None,
        "profile": None,
    }


def _pairing_passes(stats: Stats, walk_state: _WalkState) -> None:
    """What the test/source pairing says: which tests are stale, which are
    decorative, and where the churn lands without cover."""
    test_paths, source_by_stem = walk_state.test_paths, walk_state.source_by_stem
    source_paths = walk_state.source_paths
    pairs = []
    for rel in test_paths:
        stem = source_stem(rel)
        source = source_by_stem.get(stem) if stem else None
        if source is not None:
            pairs.append((str(rel), str(source)))
    stats["paired_tests"] = len(pairs)
    if stats["git"]:
        stats["stale_tests"], stale_findings = find_stale(pairs, stats["git"]["file_commits"])
        stats["findings"].extend(stale_findings)
    if stats["coverage_by_file"]:
        coverage_pairs = [(test, source) for test, source in pairs if Path(source).name in stats["coverage_by_file"]]
        lookup = {source: stats["coverage_by_file"][Path(source).name] for _, source in coverage_pairs}
        stats["decorative_tests"], decorative_findings = find_decorative(coverage_pairs, lookup)
        stats["findings"].extend(decorative_findings)
    if stats["git"]:
        hotspots = find_hotspots(
            stats["git"]["file_commits"],
            source_paths,
            {source for _, source in pairs},
            stats["coverage_by_file"],
        )
        if hotspots:
            stats["hot_files"] = hotspots["hot_files"]
            stats["untested_hot_files"] = hotspots["untested_hot_files"]
            stats["hot_coverage"] = hotspots["hot_coverage"]
            stats["findings"].extend(hotspots["findings"])


def collect(root: Path, *, use_git: bool = True) -> Stats:
    stats = _empty_stats(root)
    texts = _ConfigTexts()
    walk_state = _WalkState(modules={p.name for p in root.iterdir() if p.is_dir()} if root.is_dir() else set())
    bodies_by_file, imports_by_file = walk_state.bodies_by_file, walk_state.imports_by_file
    symbols, source_symbols = walk_state.symbols, walk_state.source_symbols
    test_names, source_by_stem, modules = walk_state.test_names, walk_state.source_by_stem, walk_state.modules

    for abs_path, rel, in_artifact in walk(root):
        _scrape_config(stats, rel, abs_path, texts, in_artifact=in_artifact)

        if in_artifact:
            continue
        lang = language_of(rel)
        if lang is None:
            continue
        if is_test_file(rel):
            text = read_text(abs_path)
            if text is None:
                continue
            _fold_test_file(stats, rel, text, lang, walk_state)
        else:
            stats["source_files"] += 1
            stats["languages"][lang] += 1
            source_by_stem.setdefault(rel.stem, rel)
            walk_state.source_paths.append(str(rel))
            modules.add(rel.stem)
            text = read_text(abs_path)
            if text:
                lines = sum(1 for line in text.splitlines() if line.strip())
                stats["source_lines"] += lines
                stats["language_lines"][lang] += lines
                found = _symbols_in(text, lang)
                symbols |= found
                source_symbols |= {name.lower() for name in found}

    stats["profile"] = blend_profile(stats["language_lines"])
    stats["coverage_threshold"] = find_threshold(texts.config + texts.ci)
    if use_git:
        stats["git"] = git_history(root)

    for name in test_names:
        words = [w for w in name_words(name) if w not in FILLER_WORDS]
        if 1 <= len(words) <= MAX_NAME_WORDS_FOR_MIRROR and "_".join(words) in source_symbols:
            stats["method_mirror_names"] += 1

    symbols |= modules | set(source_by_stem)

    stats["duplicate_cases"], duplicate_findings = find_duplicates(bodies_by_file)
    stats["findings"].extend(duplicate_findings)
    if symbols:
        stats["phantom_symbols"], phantom_findings = find_phantoms(imports_by_file, symbols)
        stats["findings"].extend(phantom_findings)

    _pairing_passes(stats, walk_state)

    stats["suppressed_failures"] = sum(1 for f in stats["findings"] if f["kind"] == "suppressed-failure")
    stats["findings"].sort(key=lambda f: (FLAG_ORDER.get(f["kind"], 9), f["file"], f["line"]))
    for finding in stats["findings"]:
        finding["severity"] = severity_for(finding["kind"])
    return stats
