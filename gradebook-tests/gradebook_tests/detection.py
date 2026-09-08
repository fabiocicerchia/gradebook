"""Recognising test files and what is inside them: the patterns, and the
walk that applies them."""

from __future__ import annotations

import os
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from .base import (
    ARTIFACT_DIRS,
    CONDITION_WINDOW,
    GIANT_CASE_LINES,
    JS_EXT,
    LANG_BY_EXT,
    LONG_CASE_LINES,
    MANY_ASSERTIONS,
    MAX_FILE_BYTES,
    MIN_MEANINGFUL_WORDS,
    MIN_WORDS_WITH_CONTEXT,
    MOSTLY,
    SKIP_DIRS,
    TEST_DIR_NAMES,
    FileInfo,
    Finding,
    Profile,
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


# kind -> directory-name hints, most specific first.
KIND_DIR_HINTS = [
    (
        "e2e",
        {
            "e2e",
            "end2end",
            "end-to-end",
            "acceptance",
            "functional",
            "system",
            "systemtest",
            "systemtests",
            "ui",
            "uitests",
            "browser",
            "smoke",
        },
    ),
    ("contract", {"contract", "contracts", "pact", "pacts"}),
    (
        "integration",
        {
            "integration",
            "integrations",
            "it",
            "itest",
            "integrationtest",
            "integration-tests",
            "integrationtests",
            "component",
        },
    ),
    ("performance", {"perf", "performance", "load", "stress", "bench", "benchmark", "benchmarks"}),
    ("unit", {"unit", "unittest", "unittests"}),
]

KIND_CONTENT_HINTS = [
    (
        "e2e",
        re.compile(
            r"playwright|cypress|selenium|puppeteer|webdriver|capybara|testcafe|nightwatch"
            r"|page\.goto\(|browser\.(?:get|url)\(|\bdriver\.get\(|detox",
            re.IGNORECASE,
        ),
    ),
    (
        "contract",
        re.compile(r"\bpact\b|pactum|spring-cloud-contract|consumer_?driven", re.IGNORECASE),
    ),
    (
        "integration",
        re.compile(
            r"testcontainers|dockertest|docker-compose|supertest|@SpringBootTest|@DataJpaTest"
            r"|httptest\.NewServer|sqlalchemy\.create_engine|psycopg|pg_pool|live_server"
            r"|TestClient\(|WebApplicationFactory|rails_helper|mark\.integration"
            r"|RSpec\.describe.*type:\s*:request",
            re.IGNORECASE,
        ),
    ),
    (
        "performance",
        re.compile(r"\bk6\b|locust|jmeter|\bJMH\b|pytest-benchmark|criterion|autocannon", re.IGNORECASE),
    ),
]

# Gherkin-style BDD (a shared language with the business) is scored above
# spec-style BDD (describe/it), which is mostly a naming convention.
GHERKIN_RE = re.compile(
    r"\bcucumber\b|\bbehave\b|pytest[_-]bdd|\bgodog\b|specflow|jbehave|behat|\bgherkin\b"
    r"|^[ \t]*(?:Given|When|Then)\b|@given\(|@when\(|@then\(",
    re.MULTILINE,
)
SPEC_STYLE_RE = re.compile(
    r"(?<![.\w$])(?:describe|context|feature|Scenario)\s*\(|RSpec\.(?:describe|feature)"
    r"|\bFeatureSpec\b|\bshould\s+[\"']"
)
PROPERTY_RE = re.compile(
    r"\bhypothesis\b|fast-check|\bfc\.(?:assert|property)\b|quickcheck"
    r"|proptest|jqwik|scalacheck|@given\(st\.",
    re.IGNORECASE,
)
MUTATION_RE = re.compile(r"mutmut|cosmic-ray|stryker|pitest|mutant|cargo-mutants", re.IGNORECASE)
SNAPSHOT_RE = re.compile(r"toMatchSnapshot|snapshottest|approvaltests|insta::assert", re.IGNORECASE)

CASE_RE = {
    "python": re.compile(r"^[ \t]*(?:async[ \t]+)?def[ \t]+test\w*[ \t]*\(", re.MULTILINE),
    "javascript": re.compile(r"(?<![.\w$])(?:it|test)\s*(?:\.\w+)*\s*\("),
    "go": re.compile(r"^func[ \t]+(?:Test|Fuzz|Example)\w*[ \t]*\(", re.MULTILINE),
    "java": re.compile(r"@(?:Test|ParameterizedTest|RepeatedTest)\b"),
    "ruby": re.compile(r"^[ \t]*(?:it|specify|scenario)[ \t]+['\"]|^[ \t]*def[ \t]+test_", re.MULTILINE),
    "php": re.compile(r"function[ \t]+test\w*[ \t]*\(|@test\b"),
    "rust": re.compile(r"#\[[\w:]*test\]"),
    "csharp": re.compile(r"\[(?:Fact|Theory|Test|TestMethod|TestCase)[\]\(]"),
    "elixir": re.compile(r"^[ \t]*(?:test|property)[ \t]+[\"']", re.MULTILINE),
    "scala": re.compile(r"(?<![.\w])(?:test|it)\s*(?:should)?\s*[(\"']"),
    "shell": re.compile(r"^[ \t]*(?:function[ \t]+)?test_\w+[ \t]*\(\)", re.MULTILINE),
    "feature": re.compile(r"^[ \t]*(?:Scenario Outline|Scenario Template|Scenario|Example):", re.MULTILINE),
}
CASE_RE["typescript"] = CASE_RE["javascript"]
CASE_RE["kotlin"] = CASE_RE["java"]

ASSERT_RE = {
    "python": re.compile(r"\bassert\b|self\.assert\w+\(|pytest\.raises\(|assert_\w+\("),
    "javascript": re.compile(r"(?<![.\w$])expect\s*\(|(?<![.\w])assert(?:\.\w+)?\s*\(|\.should\b"),
    "go": re.compile(r"\bt\.(?:Error|Errorf|Fatal|Fatalf)\b|\b(?:assert|require)\.\w+\("),
    "java": re.compile(r"\bassert\w*\s*\(|\bverify\s*\(|\bshould\w*\s*\("),
    "ruby": re.compile(r"(?<![.\w])expect\s*\(|\bassert\w*\b|\.should\b|\bis_expected\b"),
    "php": re.compile(r"(?:\$this->|self::|static::)assert\w+\(|\bexpects?\s*\("),
    "rust": re.compile(r"\bassert(?:_eq|_ne)?!\s*\(|\bpanic!\s*\("),
    "csharp": re.compile(r"\bAssert\.\w+\(|\.Should\(\)|\bVerify\("),
    "elixir": re.compile(r"\bassert\b|\brefute\b"),
    "scala": re.compile(r"\bassert\w*\s*\(|\bshould\b|\bmust\b"),
    "shell": re.compile(r"\bassert\w*\b|\[\[ | -eq | -ne "),
    "feature": re.compile(r"^[ \t]*(?:Then|And|But)\b", re.MULTILINE),
}
ASSERT_RE["typescript"] = ASSERT_RE["javascript"]
ASSERT_RE["kotlin"] = ASSERT_RE["java"]
GENERIC_ASSERT = re.compile(r"\bassert\w*\b|(?<![.\w$])expect\s*\(|\bshould\b|\bverify\s*\(")

# Assertions that accept almost any value: they run the code without pinning
# behaviour down. A case whose assertions are all weak cannot fail meaningfully.
WEAK_ASSERT_RE = re.compile(
    r"assertTrue\(|assertFalse\(|assertIsNotNone\(|assertNotNone\(|assertIsInstance\("
    r"|toBeTruthy\(|toBeFalsy\(|toBeDefined\(|not\.toBeNull\(|not\.toBeUndefined\("
    r"|toMatchSnapshot\(|toBeInstanceOf\(|toBeTypeOf\("
    r"|(?:assert|require)\.(?:True|False|NotNil|NotEmpty|Nil|Empty)\("
    r"|assertNotNull\(|isNotNull\(\)|assertNotEmpty\(|assertObjectHasAttribute\("
    r"|Assert\.(?:True|False|NotNull|IsNotNull|IsInstanceOf)\(|NotBeNull\(\)"
    r"|be_truthy|be_falsey|be_present|not_to be_nil|\.to be_a\b|should exist"
)
# Bare truthiness: `assert thing` with nothing compared against.
BARE_ASSERT_RE = {
    "python": re.compile(r"^[ \t]*assert\s+(?![^\n]*(?:==|!=|<|>|\bin\b|\bis\b))\S[^\n]*$", re.MULTILINE),
    "rust": re.compile(r"assert!\(\s*[\w.()]+\s*[,)]"),
}
TAUTOLOGY_RE = re.compile(
    r"assert\s+True\b|assert\s+1\s*==\s*1|assertTrue\(\s*true\s*\)"
    r"|expect\(\s*(?:true|1)\s*\)\.(?:toBe|toEqual)\(\s*(?:true|1)\s*\)"
    r"|assertEquals?\(\s*(\d+)\s*,\s*\1\s*\)",
    re.IGNORECASE,
)

# Failure-path tests: the paths that regressions actually escape through.
ERROR_ASSERT_RE = re.compile(
    r"pytest\.raises\(|assertRaises\w*|\.toThrow\w*\(|rejects\.\w+|assertThrows"
    r"|@Test\s*\(\s*expected|expectException|raise_error|should_panic|catch_unwind"
    r"|(?:assert|require)\.(?:Error|Panics|EqualError)\(|Assert\.Throws|ThrowsAsync"
    r"|rejectedWith|willThrow|assert_raises|expectThrows"
)
ERROR_NAME_WORDS = {
    "error",
    "errors",
    "invalid",
    "missing",
    "fails",
    "fail",
    "failure",
    "raises",
    "raise",
    "throws",
    "throw",
    "rejects",
    "rejected",
    "timeout",
    "denied",
    "unauthorized",
    "forbidden",
    "expired",
    "duplicate",
    "conflict",
    "empty",
    "null",
    "nil",
    "none",
    "negative",
    "malformed",
    "corrupt",
    "unavailable",
    "panic",
    "exception",
    "refuses",
    "refused",
    "not",
    "without",
    "unknown",
    "unsupported",
    "invalidates",
    "aborts",
    "rollback",
    "retries",
    "retry",
}

SKIP_RE = re.compile(
    r"@pytest\.mark\.(?:skip|xfail)|pytest\.skip\(|@unittest\.skip|(?<![.\w$])(?:it|test|describe)"
    r"\.(?:skip|todo)\s*\(|\bxit\s*\(|\bxdescribe\s*\(|\bt\.Skip(?:Now)?\(|@Ignore\b|@Disabled\b"
    r"|\[Ignore|#\[ignore\]|markTestSkipped|markTestIncomplete|\bpending\b|@tag\(:skip\)"
)
FOCUS_RE = re.compile(
    r"(?<![.\w$])(?:it|test|describe|context)\.only\s*\(|\bfdescribe\s*\("
    r"|\bfit\s*\(|:focus\b|@Focus\b"
)
SLEEP_RE = re.compile(
    r"time\.sleep\s*\(|Thread\.sleep\s*\(|(?<![.\w$])sleep\s*\(\s*[0-9]"
    r"|waitForTimeout\s*\(|setTimeout\s*\([^,]+,\s*[0-9]{3,}\)"
    r"|time\.Sleep\s*\(|usleep\s*\("
)
PARAM_RE = re.compile(
    r"@pytest\.mark\.parametrize|(?<![.\w$])(?:it|test|describe)\.each"
    r"|@ParameterizedTest|\[Theory\]|for\s+_,\s*\w+\s*:=\s*range"
    r"|for\s+\w+\s+in\s+\[|table\s*:?=|subTest\(|where:"
)
MOCK_RE = re.compile(
    r"\bmock\w*\b|\bstub\w*\b|@patch\b|jest\.(?:mock|fn)\(|sinon\.|MagicMock"
    r"|Mockito|gomock|unittest\.mock",
    re.IGNORECASE,
)

# Test names, per language: group 1 (or the first non-empty group) is the name.
NAME_RE = {
    "python": [re.compile(r"^[ \t]*(?:async[ \t]+)?def[ \t]+(test\w*)[ \t]*\(", re.MULTILINE)],
    "javascript": [re.compile(r"(?<![.\w$])(?:it|test)\s*(?:\.\w+)*\s*\(\s*[`'\"]([^`'\"]{1,140})")],
    "go": [
        re.compile(r"^func[ \t]+(Test\w*)[ \t]*\(", re.MULTILINE),
        re.compile(r"t\.Run\(\s*\"([^\"]{1,140})\""),
    ],
    "java": [
        re.compile(
            r"@(?:Test|ParameterizedTest|RepeatedTest)\b[\s\S]{0,240}?"
            r"(?:void|fun)\s+(?:`([^`]{1,140})`|(\w+))\s*\("
        )
    ],
    "ruby": [
        re.compile(r"^[ \t]*(?:it|specify|scenario)[ \t]+['\"]([^'\"]{1,140})", re.MULTILINE),
        re.compile(r"^[ \t]*def[ \t]+(test_\w+)", re.MULTILINE),
    ],
    "php": [re.compile(r"function[ \t]+(test\w+)[ \t]*\(")],
    "rust": [re.compile(r"#\[[\w:]*test\][\s\S]{0,120}?fn\s+(\w+)\s*\(")],
    "csharp": [
        re.compile(
            r"\[(?:Fact|Theory|Test|TestMethod|TestCase)[^\]]*\][\s\S]{0,240}?"
            r"(?:void|Task)\s+(\w+)\s*\("
        )
    ],
    "elixir": [re.compile(r"^[ \t]*(?:test|property)[ \t]+\"([^\"]{1,140})\"", re.MULTILINE)],
    "scala": [
        re.compile(r"(?<![.\w])(?:test|it)\s*\(\s*\"([^\"]{1,140})\""),
        re.compile(r"\"([^\"]{1,140})\"\s+(?:should|must|in)\b"),
    ],
    "shell": [re.compile(r"^[ \t]*(?:function[ \t]+)?(test_\w+)[ \t]*\(\)", re.MULTILINE)],
    "feature": [
        re.compile(
            r"^[ \t]*(?:Scenario Outline|Scenario Template|Scenario|Example):"
            r"[ \t]*(.+)$",
            re.MULTILINE,
        )
    ],
}
NAME_RE["typescript"] = NAME_RE["javascript"]
NAME_RE["kotlin"] = NAME_RE["java"]

# Names that describe nothing. "test_1", "it works", "testFoo".
FILLER_WORDS = {
    "",
    "works",
    "work",
    "working",
    "ok",
    "okay",
    "fine",
    "basic",
    "simple",
    "stuff",
    "thing",
    "things",
    "foo",
    "bar",
    "baz",
    "qux",
    "case",
    "cases",
    "test",
    "tests",
    "testing",
    "it",
    "example",
    "sanity",
    "main",
    "run",
    "runs",
    "todo",
    "tmp",
    "temp",
    "x",
    "y",
    "z",
    "a",
    "b",
    "success",
    "successful",
    "happy",
    "path",
    "good",
    "bad",
    "new",
    "old",
    "one",
    "two",
    "three",
    "first",
    "second",
    "third",
    "func",
    "function",
    "method",
    "class",
    "obj",
    "object",
    "data",
}
BEHAVIOUR_WORDS = {
    "returns",
    "return",
    "raises",
    "raise",
    "throws",
    "throw",
    "rejects",
    "resolves",
    "fails",
    "fail",
    "errors",
    "handles",
    "handle",
    "creates",
    "create",
    "updates",
    "update",
    "deletes",
    "delete",
    "validates",
    "validate",
    "ignores",
    "ignore",
    "retries",
    "retry",
    "skips",
    "logs",
    "emits",
    "calls",
    "parses",
    "renders",
    "redirects",
    "sends",
    "saves",
    "loads",
    "rounds",
    "sorts",
    "filters",
    "counts",
    "matches",
    "adds",
    "removes",
    "allows",
    "denies",
    "preserves",
    "keeps",
    "propagates",
    "escapes",
    "normalises",
    "normalizes",
    "converts",
    "maps",
    "detects",
    "reports",
    "exits",
    "aborts",
    "caches",
    "locks",
    "yields",
    "wraps",
    "flags",
    "scores",
    "should",
    "must",
    "does",
    "expects",
    "prevents",
    "truncates",
    "falls",
    "defaults",
}
CONDITION_WORDS = {
    "when",
    "if",
    "given",
    "unless",
    "with",
    "without",
    "after",
    "before",
    "while",
    "once",
    "until",
    "on",
    "empty",
    "missing",
    "invalid",
    "duplicate",
    "expired",
    "disabled",
}

# Test doubles: creation, interaction assertions, and lifecycle cleanup.
DOUBLE_RE = re.compile(
    r"unittest\.mock|MagicMock\(|AsyncMock\(|(?<![.\w])Mock\("
    r"|(?<![.\w])@?(?:mock\.)?patch(?:\.object)?\s*\(|monkeypatch\.\w+|jest\.(?:mock|fn|spyOn)\(|vi\.(?:mock|fn|spyOn)\("
    r"|sinon\.(?:stub|mock|spy|fake|createStubInstance)|td\.(?:replace|func)\(|nock\("
    r"|Mockito\.(?:mock|spy|when)|@Mock\b|@MockBean\b|EasyMock|mock\(\w+\.class\)"
    r"|gomock\.NewController|httpmock\.|Substitute\.For|new Mock<|Mock<\w+>\("
    r"|instance_double\(|class_double\(|double\(|allow\([^)]*\)\.to receive|receive\("
    r"|createMock\(|getMockBuilder\(|prophesize\(|Mockery::|mockall|WireMock"
    r"|responses\.add\(|httpretty|stub_request\(|fakeredis|moto\.",
    re.IGNORECASE,
)
SPY_RE = re.compile(r"spyOn\(|sinon\.spy|Mockito\.spy|\bspy\(|wraps\s*=|@Spy\b|SpyOn", re.IGNORECASE)
STUB_RE = re.compile(
    r"\bstub\b|thenReturn|return_value|side_effect|\.Returns\(|mockReturnValue"
    r"|mockResolvedValue|\.willReturn|and_return",
    re.IGNORECASE,
)
MOCK_ASSERT_RE = re.compile(
    r"toHaveBeenCalled\w*|toBeCalled\w*|assert_called\w*|assert_any_call|assert_has_calls"
    r"|assert_not_called|called_once|\.called\b|sinon\.assert|(?<![.\w])verify\s*\("
    r"|verifyNoMoreInteractions|\.Received\(|\.Verify\(|AssertCalled|AssertExpectations"
    r"|AssertNumberOfCalls|toHaveReceived|have_received|shouldReceive"
)
DOUBLE_CLEANUP_RE = re.compile(
    r"restoreAllMocks|resetAllMocks|clearAllMocks|restoreMocks\s*:|resetMocks\s*:|\.restore\(\)"
    r"|sinon\.restore|@patch\b|with patch|patch\.stopall|addCleanup|monkeypatch"
    r"|defer\s+ctrl\.Finish|ctrl\.Finish\(\)|verifyNoMoreInteractions|afterEach\(|tearDown"
    r"|teardown|td\.reset|nock\.cleanAll"
)


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


def extract_names(text: str, lang: str) -> set[str]:
    names = []
    for pattern in NAME_RE.get(lang, []):
        for match in pattern.finditer(text):
            value = next((g for g in match.groups() if g), None)
            if value:
                names.append(value.strip())
    return names


# Low-effort tells: copy-paste cases, assertions engineered not to fail, and
# references to code that does not exist. These become findings with a
# file:line, not just a number — the fix needs an address.
COMMENT_RE = re.compile(r"#[^\n]*|//[^\n]*|/\*[\s\S]*?\*/")
LITERAL_RE = re.compile(r"'[^'\n]*'|\"[^\"\n]*\"|`[^`\n]*`|\b\d+(?:\.\d+)?\b")
COMMENTED_ASSERT_RE = re.compile(
    r"^[ \t]*(?:#|//)[ \t]*(?:assert|expect\s*\(|self\.assert|require\.|t\.(?:Error|Fatal))",
    re.MULTILINE,
)
SWALLOW_RE = re.compile(
    r"except[^\n:]*:[ \t]*(?:#[^\n]*)?\n[ \t]*(?:pass|\.\.\.)[ \t]*$"
    r"|catch\s*\([^)]*\)\s*\{\s*\}|contextlib\.suppress|recover\(\)\s*;?\s*\}",
    re.MULTILINE,
)
DEAD_BRANCH_RE = re.compile(r"^[ \t]*if\s+(?:False|0)\s*:|^[ \t]*if\s*\(\s*(?:false|0)\s*\)", re.MULTILINE)
SKIP_NO_REASON_RE = re.compile(
    r"@pytest\.mark\.skip(?!\w)(?!\s*\(\s*reason)|@unittest\.skip\s*\(\s*\)"
    r"|\bt\.Skip\(\s*\)|@Disabled\s*(?:\n|$)|@Ignore\s*(?:\n|$)"
)

# Flakiness and environment coupling: the Butterfly, the Local Hero, Resource
# Optimism, Chain Gang / Generous Leftovers.
UNFROZEN_TIME_RE = re.compile(
    r"datetime\.now\(|datetime\.utcnow\(|date\.today\(|time\.time\(|Date\.now\("
    r"|new Date\(\s*\)|time\.Now\(|LocalDate(?:Time)?\.now\(|DateTime\.Now|Time\.now\b"
    r"|Instant\.now\(|System\.currentTimeMillis"
)
FROZEN_TIME_RE = re.compile(
    r"freeze_time|freezegun|time_machine|useFakeTimers|setSystemTime|MockDate|timecop"
    r"|Clock\.fixed|fixedClock|libfaketime|travel_to|frozen_time",
    re.IGNORECASE,
)
UNSEEDED_RANDOM_RE = re.compile(
    r"(?<![.\w])random\.\w+\(|Math\.random\(|uuid4\(|uuid\.New|(?<![.\w])rand\.\w+\("
    r"|secrets\.token|(?<![.\w])Random\(\)|faker\.\w+\(|Faker\(\)"
)
SEEDED_RANDOM_RE = re.compile(
    r"random\.seed\(|\bseed\s*[=(]|Faker\.seed|faker\.seed|NewSource\(|srand\(", re.IGNORECASE
)
ENV_COUPLING_RE = re.compile(
    r"(?:localhost|127\.0\.0\.1):\d+"
    r"|https?://(?!localhost|127\.0\.0\.1|example\.(?:com|org|net)|test\b|foo\b)[\w.-]+\.\w{2,}"
    r"|/home/\w+|/Users/\w+|[A-Z]:\\\\|(?<![\w.])~/\w+"
)
ORDER_DEPENDENT_RE = re.compile(
    r"def[ \t]+test_?\d{1,2}_|it\(\s*['\"]\d{1,2}[.)_ ]|pytest\.mark\.dependency"
    r"|@Test\s*\([^)]*dependsOn|@(?:FixMethodOrder|TestMethodOrder)|\.serial\b"
    r"|^[ \t]*global[ \t]+\w+",
    re.MULTILINE,
)

# The Giant, the Eager Test, Assertion Roulette, Conditional Test Logic.
BRANCH_RE = re.compile(r"^[ \t]*(?:\}[ \t]*)?(?:if|switch|match)[ \t(]", re.MULTILINE)
ELSE_RE = re.compile(r"^[ \t]*(?:\}[ \t]*)?(?:else|elif)\b", re.MULTILINE)
# `if got != want { t.Fatal(...) }` is how a stdlib-style Go test asserts, and
# `if (x) fail()` is the same idea elsewhere: a guard, not branching logic.
GUARD_RE = re.compile(
    r"\bt\.(?:Error|Fatal|Skip)\w*\(|(?<![.\w])fail\w*\(|\bassert\w*\b"
    r"|(?<![.\w$])expect\s*\(|\braise\b|\bthrow\b"
)


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


SETUP_BLOCK_RE = re.compile(
    r"^[ \t]*(?:def[ \t]+(?:setUp|setup_method|setup_class|setup_module)\b"
    r"|(?:before(?:Each|All))\s*\(|@(?:Before|BeforeEach|BeforeAll)\b"
    r"|def[ \t]+\w+\([^)]*\):[ \t]*(?:#[^\n]*)?$)",
    re.MULTILINE,
)

# Ecosystems differ, and a single set of thresholds mis-scores most of them.
# Go tests are verbose (table-driven, explicit error checks) so a 0.5x test:code
# ratio is a low bar; pytest is terse so it is a high one. pytest and jest print
# the compared values on failure, so a bare assert is fine there — JUnit's
# assertTrue(x) tells you nothing, which is where Assertion Roulette came from.
LANGUAGE_PROFILES = {
    #                 test:code  cases/file  bare-assert check  spec-style is idiomatic
    "python": (0.50, 2.0, False, False),
    "javascript": (0.60, 2.0, True, True),
    "typescript": (0.60, 2.0, True, True),
    "go": (0.80, 1.5, True, False),
    "java": (0.90, 2.0, True, False),
    "kotlin": (0.80, 2.0, True, False),
    "csharp": (0.90, 2.0, True, False),
    "ruby": (0.70, 2.5, False, True),
    "php": (0.70, 2.0, True, False),
    "rust": (0.40, 1.5, False, False),
    "elixir": (0.50, 2.0, False, False),
    "scala": (0.70, 2.0, False, True),
    "shell": (0.30, 1.0, False, False),
}
DEFAULT_PROFILE = (0.50, 2.0, False, False)

# Assertions that report nothing useful when they fail. Only checked for the
# ecosystems whose frameworks do not print the compared values themselves.
UNINFORMATIVE_ASSERT_RE = {
    "java": re.compile(r"\bassert(?:True|False)\s*\(\s*[^,\"\n)]+\)"),
    "csharp": re.compile(r"\bAssert\.Is(?:True|False)\s*\(\s*[^,\"\n)]+\)"),
    "php": re.compile(r"assert(?:True|False)\s*\(\s*\$[^,\"\n)]+\)"),
    "javascript": re.compile(r"(?<![.\w$])assert(?:\.ok)?\s*\(\s*[^,\"\'\n)]+\)"),
    # `t.Fatal("boom")` names no values; `t.Errorf("got %v, want %v", ...)` does.
    "go": re.compile(r"\bt\.(?:Error|Fatal)\s*\(\s*\"[^\"%]*\"\s*\)"),
}
UNINFORMATIVE_ASSERT_RE["kotlin"] = UNINFORMATIVE_ASSERT_RE["java"]
UNINFORMATIVE_ASSERT_RE["typescript"] = UNINFORMATIVE_ASSERT_RE["javascript"]


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
    dominant = sorted(language_lines, key=language_lines.get, reverse=True)[:2]
    return {
        "test_code_ratio": round(ratio, 2),
        "cases_per_source": round(cases, 2),
        # Only apply an ecosystem-specific check when that ecosystem is most of the repo.
        "bare_assert_check": bare >= MOSTLY,
        "spec_style_idiomatic": spec >= MOSTLY,
        "languages": dominant,
    }


# Boundary and equivalence-partition values: the edges are where code fails.
# `nil`, `[]` and `{}` are deliberately absent: Go writes `if err != nil` and
# `[]string{...}` constantly, and `{}` is every JS arrow-function body. Empty
# collections are caught by the name words instead.
BOUNDARY_RE = re.compile(
    r"(?<![\w.])(?:None|null|undefined|NaN|Infinity|math\.inf|sys\.maxsize|MAX_VALUE"
    r"|MIN_VALUE|MAX_SAFE_INTEGER|Integer\.MAX|Long\.MAX|Number\.MAX)\b"
    r"|float\(\s*['\"]inf|(?<![\w.])-\s*1\b|(?<![\w])['\"]{2}"
    r"|\.repeat\(\s*\d{3,}|\*\s*\d{4,}"
)
BOUNDARY_NAME_WORDS = {
    "empty",
    "zero",
    "negative",
    "max",
    "maximum",
    "min",
    "minimum",
    "boundary",
    "boundaries",
    "edge",
    "overflow",
    "underflow",
    "limit",
    "limits",
    "blank",
    "whitespace",
    "unicode",
    "huge",
    "truncates",
    "truncated",
    "rounding",
    "precision",
    "offbyone",
    "single",
    "nothing",
}
# Suites pinned to one worker cannot be run in parallel — an independence smell.
SERIAL_ONLY_RE = re.compile(
    r"--runInBand|maxWorkers\s*[:=]\s*['\"]?1\b|--max-workers[= ]1|-p\s+no:randomly"
    r"|pytest\.mark\.serial|describe\.serial|test\.describe\.serial|@Execution\(\s*SAME_THREAD"
    r"|@NotThreadSafe|-parallel[= ]1|--serial\b"
)

# The Loudmouth: console chatter instead of assertions.
CHATTER_RE = re.compile(
    r"(?<![.\w])print\s*\(|console\.(?:log|debug|info)\s*\("
    r"|System\.out\.print|fmt\.Print|(?<![.\w])puts\s+"
)
# The Operating System Evangelist: a test that branches on the platform.
PLATFORM_RE = re.compile(
    r"sys\.platform|os\.name\b|process\.platform|runtime\.GOOS"
    r"|System\.getProperty\(\s*[\"']os\.name|RUBY_PLATFORM|PHP_OS"
)
# The Greedy Catcher: the failure is logged, then the test passes anyway.
GREEDY_CATCH_RE = re.compile(
    r"except[^\n:]*:[ \t]*(?:#[^\n]*)?\n[ \t]*(?:print|log\w*|logger\.\w+|console\.\w+)\s*\("
    r"|catch\s*\([^)]*\)\s*\{[ \t]*\n?[ \t]*console\.\w+\s*\([^)]*\)[ \t]*;?[ \t]*\n?[ \t]*\}",
    re.MULTILINE,
)

# Brittle locators: record-and-playback output and hand-written positional
# XPath, the standard cause of flaky UI tests.
BRITTLE_SELECTOR_RE = re.compile(
    r"//\w+\[\d+\]|//\*\[|//div\b|//span\b|//tr\[|nth-child\(|nth-of-type\("
    r"|find_element_by_xpath|By\.xpath|\$x\(|\.css-[a-z0-9]{5,}|Mui[A-Z]\w+-root"
    r"|>\s*div\s*>\s*div|\[class\^=|\[class\*="
)
ROBUST_SELECTOR_RE = re.compile(
    r"getBy(?:Role|TestId|LabelText|Text|Title|PlaceholderText)|findBy(?:Role|TestId)"
    r"|data-testid|byTestId|By\.id\(|getByAltText|screen\.getBy"
)

# The Ugly Mirror / Doppelgänger: the expected value is recomputed from the
# inputs, so the test cannot catch a wrong formula — it shares it.
MIRROR_SAFE_CALLS = (
    r"pytest\.approx|approx|mock\.ANY|len|str|int|float|bool|repr|sorted|list"
    r"|dict|set|tuple|frozenset|bytes|Decimal|datetime|date|time|UUID|Path"
    r"|json\.loads|json\.dumps|Number|String|Array|Object|BigInt"
)
_MIRROR_EXPECTED = (
    r"(?!(?:" + MIRROR_SAFE_CALLS + r")\s*\()[\w.]*[A-Za-z_]\w*"
    r"\([^)\n]*[A-Za-z_]\w*[^)\n]*\)"
)
MIRROR_RE = re.compile(
    r"==\s*"
    + _MIRROR_EXPECTED
    + r"|\.(?:toBe|toEqual|toStrictEqual|toHaveValue)\(\s*"
    + _MIRROR_EXPECTED
    + r"|assert(?:Equals?|That)\([^,\n]+,\s*"
    + _MIRROR_EXPECTED
)

# The Inspector / Anal Probe: reaching into internals instead of behaviour.
PRIVATE_ACCESS_RE = re.compile(
    r"\.(_[a-zA-Z]\w*)\b(?!\s*=\s*(?:Mock|MagicMock))|\.#(\w+)|getDeclaredField|setAccessible"
    r"|__dict__|\breflect\.ValueOf|Reflect\.get\("
)

# Symbols a repo actually defines, so a test referring to anything else can be
# flagged as dead or invented.
SYMBOL_RE = {
    "python": [
        re.compile(r"^[ \t]*(?:async[ \t]+)?def[ \t]+(\w+)", re.MULTILINE),
        re.compile(r"^[ \t]*class[ \t]+(\w+)", re.MULTILINE),
        re.compile(r"^(\w+)[ \t]*(?::[^=\n]+)?=", re.MULTILINE),
    ],
    "javascript": [
        re.compile(r"(?:export[ \t]+)?(?:async[ \t]+)?function[ \t]+(\w+)"),
        re.compile(r"(?:export[ \t]+)?(?:const|let|var|class)[ \t]+(\w+)"),
        re.compile(r"export[ \t]*\{([^}]*)\}"),
    ],
    "go": [
        re.compile(r"^func[ \t]+(?:\([^)]*\)[ \t]*)?(\w+)", re.MULTILINE),
        re.compile(r"^type[ \t]+(\w+)", re.MULTILINE),
    ],
    "ruby": [
        re.compile(r"^[ \t]*def[ \t]+(\w+)", re.MULTILINE),
        re.compile(r"^[ \t]*(?:class|module)[ \t]+(\w+)", re.MULTILINE),
    ],
    "php": [re.compile(r"function[ \t]+(\w+)"), re.compile(r"(?:class|trait)[ \t]+(\w+)")],
    "rust": [
        re.compile(r"(?:pub[ \t]+)?fn[ \t]+(\w+)"),
        re.compile(r"(?:pub[ \t]+)?(?:struct|enum|trait)[ \t]+(\w+)"),
    ],
}
SYMBOL_RE["typescript"] = SYMBOL_RE["javascript"]
# Only languages whose imports name the symbols they pull in can be checked.
PHANTOM_LANGS = {"python", "javascript", "typescript"}
PY_IMPORT_RE = re.compile(r"^[ \t]*from[ \t]+([.\w]+)[ \t]+import[ \t]+(\([^)]*\)|[^\n#]+)", re.MULTILINE)
JS_IMPORT_RE = re.compile(
    r"import[ \t]*\{([^}]*)\}[ \t]*from[ \t]*['\"](\.[^'\"]*)['\"]"
    r"|(?:const|let|var)[ \t]*\{([^}]*)\}[ \t]*=[ \t]*require\("
    r"[ \t]*['\"](\.[^'\"]*)['\"]"
)


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def normalise_body(block: str) -> str:
    """A case body with its name, comments and literals removed, for duplicate hunting."""
    body = block.split("\n", 1)[1] if "\n" in block else ""
    body = COMMENT_RE.sub("", body)
    body = LITERAL_RE.sub("@", body)
    return re.sub(r"\s+", " ", body).strip()


def imported_project_names(text: str, lang: str, modules: set[str]) -> set[str]:
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


# ------------------------------------------------------------------ walking


def read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        return path.read_text(errors="replace")
    except OSError:
        return None


def walk(root: Path) -> Iterator[tuple[Path, Path]]:
    """Yield (absolute_path, relative_path, in_artifact_dir) for every file."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            abs_path = Path(dirpath) / name
            rel = abs_path.relative_to(root)
            in_artifact = any(p in ARTIFACT_DIRS for p in rel.parts[:-1])
            yield abs_path, rel, in_artifact


def language_of(rel: Path) -> str | None:
    if rel.suffix == ".feature":
        return "feature"
    return LANG_BY_EXT.get(rel.suffix)


# The idioms a file can be written in, each recognised by one pattern.
STYLE_FLAGS = [
    (GHERKIN_RE, "bdd"),
    (SPEC_STYLE_RE, "spec-style"),
    (PROPERTY_RE, "property"),
    (SNAPSHOT_RE, "snapshot"),
    (PARAM_RE, "parametrized"),
    (MOCK_RE, "mocked"),
]


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

    placeholder = descriptive = conditional = words = 0
    bad_names = []
    names = extract_names(text, lang)
    for name in names:
        is_placeholder, is_descriptive, has_condition = classify_name(name)
        words += len(name_words(name))
        placeholder += is_placeholder
        descriptive += is_descriptive
        conditional += has_condition
        if not is_descriptive:
            bad_names.append(name)

    uninformative = len(UNINFORMATIVE_ASSERT_RE[lang].findall(text)) if lang in UNINFORMATIVE_ASSERT_RE else 0
    chatter = len(CHATTER_RE.findall(text))
    platform_branches = len(PLATFORM_RE.findall(text))
    frozen = bool(FROZEN_TIME_RE.search(text))
    seeded = bool(SEEDED_RANDOM_RE.search(text))
    unfrozen_time = 0 if frozen else len(UNFROZEN_TIME_RE.findall(text))
    unseeded_random = 0 if seeded else len(UNSEEDED_RANDOM_RE.findall(text))
    env_coupling = len(ENV_COUPLING_RE.findall(text))
    order_dependent = len(ORDER_DEPENDENT_RE.findall(text))

    setup_lines = 0
    setup_match = SETUP_BLOCK_RE.search(text)
    if setup_match:
        rest = text[setup_match.end() :].splitlines()
        for line in rest:
            if line.strip() and not line[:1].isspace():
                break
            setup_lines += 1 if line.strip() else 0

    brittle, suppressed = _brittle_and_private(rel, text)
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
