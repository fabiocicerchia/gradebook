#!/usr/bin/env python3
"""gradebook-tests — score how effective a repository's test suite actually is.

Coverage percentage alone says nothing about whether a suite would catch a
regression. gradebook-tests walks any repo, finds and classifies its tests (unit,
integration, functional/E2E, BDD), reads whatever coverage evidence exists,
mines git history for TDD discipline, and grades the suite 0-100 across nine
weighted dimensions — then tells you which fix buys the most points.

  gradebook-tests .
  gradebook-tests /path/to/repo --format markdown
  gradebook-tests . --fail-under 60
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

VERSION = "0.1.0"
MAX_FILE_BYTES = 512 * 1024

# Directories never worth walking into.
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "bower_components", ".venv", "venv", "env",
    "__pycache__", ".tox", ".nox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".gradle", ".idea", ".vscode", ".next", ".nuxt", ".terraform", "vendor",
    "third_party", "site-packages", ".cache", ".yarn", "Pods",
}
# Walked (coverage artifacts live here) but excluded from source/test counting.
ARTIFACT_DIRS = {
    "coverage", "htmlcov", "build", "dist", "target", "out", "obj", "reports",
    ".nyc_output", "coverage-reports", "test-results", "allure-results",
}

LANG_BY_EXT = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
    ".cjs": "javascript", ".ts": "typescript", ".tsx": "typescript", ".go": "go",
    ".java": "java", ".kt": "kotlin", ".rb": "ruby", ".php": "php", ".rs": "rust",
    ".cs": "csharp", ".ex": "elixir", ".exs": "elixir", ".scala": "scala",
    ".swift": "swift", ".c": "c", ".h": "c", ".cc": "cpp", ".cpp": "cpp", ".hpp": "cpp",
    ".lua": "lua", ".sh": "shell", ".bash": "shell",
}
JS_EXT = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
TEST_DIR_NAMES = {"test", "tests", "spec", "specs", "__tests__", "testing", "e2e", "features"}

# ---------------------------------------------------------------- detection

def is_test_file(rel: Path) -> bool:
    """True if the path looks like a test/spec file in any common ecosystem."""
    suffix = rel.suffix
    stem = rel.stem
    name = rel.name
    parts = {p.lower() for p in rel.parts[:-1]}

    if suffix == ".feature":
        return True
    if suffix == ".py" and (name.startswith("test_") or stem.endswith("_test")
                            or name == "conftest.py"):
        return True
    if suffix in JS_EXT and (re.search(r"\.(test|spec)$", stem) or "__tests__" in parts):
        return True
    if suffix == ".go" and stem.endswith("_test"):
        return True
    if suffix in {".java", ".kt"} and (stem.endswith(("Test", "Tests", "Spec", "IT", "ITCase"))
                                       or stem.startswith("Test")):
        return True
    if suffix == ".rb" and stem.endswith(("_spec", "_test")):
        return True
    if suffix == ".php" and stem.endswith(("Test", "Spec")):
        return True
    if suffix == ".cs" and stem.endswith(("Test", "Tests", "Spec")):
        return True
    if suffix == ".exs" and stem.endswith("_test"):
        return True
    if suffix == ".scala" and stem.endswith(("Spec", "Test", "Suite")):
        return True
    if suffix in {".sh", ".bash"} and (stem.startswith("test") or stem.endswith("_test")):
        return True
    # Anything of a known language living under a test directory.
    return suffix in LANG_BY_EXT and bool(parts & TEST_DIR_NAMES)


# kind -> directory-name hints, most specific first.
KIND_DIR_HINTS = [
    ("e2e", {"e2e", "end2end", "end-to-end", "acceptance", "functional", "system",
             "systemtest", "systemtests", "ui", "uitests", "browser", "smoke"}),
    ("contract", {"contract", "contracts", "pact", "pacts"}),
    ("integration", {"integration", "integrations", "it", "itest", "integrationtest",
                     "integration-tests", "integrationtests", "component"}),
    ("performance", {"perf", "performance", "load", "stress", "bench", "benchmark",
                     "benchmarks"}),
    ("unit", {"unit", "unittest", "unittests"}),
]

KIND_CONTENT_HINTS = [
    ("e2e", re.compile(
        r"playwright|cypress|selenium|puppeteer|webdriver|capybara|testcafe|nightwatch"
        r"|page\.goto\(|browser\.(?:get|url)\(|\bdriver\.get\(|detox", re.IGNORECASE)),
    ("contract", re.compile(r"\bpact\b|pactum|spring-cloud-contract|consumer_?driven", re.IGNORECASE)),
    ("integration", re.compile(
        r"testcontainers|dockertest|docker-compose|supertest|@SpringBootTest|@DataJpaTest"
        r"|httptest\.NewServer|sqlalchemy\.create_engine|psycopg|pg_pool|live_server"
        r"|TestClient\(|WebApplicationFactory|rails_helper|mark\.integration"
        r"|RSpec\.describe.*type:\s*:request", re.IGNORECASE)),
    ("performance", re.compile(r"\bk6\b|locust|jmeter|\bJMH\b|pytest-benchmark|criterion|autocannon",
                               re.IGNORECASE)),
]

# Gherkin-style BDD (a shared language with the business) is scored above
# spec-style BDD (describe/it), which is mostly a naming convention.
GHERKIN_RE = re.compile(
    r"\bcucumber\b|\bbehave\b|pytest[_-]bdd|\bgodog\b|specflow|jbehave|behat|\bgherkin\b"
    r"|^[ \t]*(?:Given|When|Then)\b|@given\(|@when\(|@then\(", re.MULTILINE)
SPEC_STYLE_RE = re.compile(
    r"(?<![.\w$])(?:describe|context|feature|Scenario)\s*\(|RSpec\.(?:describe|feature)"
    r"|\bFeatureSpec\b|\bshould\s+[\"']")
PROPERTY_RE = re.compile(r"\bhypothesis\b|fast-check|\bfc\.(?:assert|property)\b|quickcheck"
                         r"|proptest|jqwik|scalacheck|@given\(st\.", re.IGNORECASE)
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
    r"|be_truthy|be_falsey|be_present|not_to be_nil|\.to be_a\b|should exist")
# Bare truthiness: `assert thing` with nothing compared against.
BARE_ASSERT_RE = {
    "python": re.compile(r"^[ \t]*assert\s+(?![^\n]*(?:==|!=|<|>|\bin\b|\bis\b))\S[^\n]*$",
                         re.MULTILINE),
    "rust": re.compile(r"assert!\(\s*[\w.()]+\s*[,)]"),
}
TAUTOLOGY_RE = re.compile(
    r"assert\s+True\b|assert\s+1\s*==\s*1|assertTrue\(\s*true\s*\)"
    r"|expect\(\s*(?:true|1)\s*\)\.(?:toBe|toEqual)\(\s*(?:true|1)\s*\)"
    r"|assertEquals?\(\s*(\d+)\s*,\s*\1\s*\)", re.IGNORECASE)

# Failure-path tests: the paths that regressions actually escape through.
ERROR_ASSERT_RE = re.compile(
    r"pytest\.raises\(|assertRaises\w*|\.toThrow\w*\(|rejects\.\w+|assertThrows"
    r"|@Test\s*\(\s*expected|expectException|raise_error|should_panic|catch_unwind"
    r"|(?:assert|require)\.(?:Error|Panics|EqualError)\(|Assert\.Throws|ThrowsAsync"
    r"|rejectedWith|willThrow|assert_raises|expectThrows")
ERROR_NAME_WORDS = {
    "error", "errors", "invalid", "missing", "fails", "fail", "failure", "raises", "raise",
    "throws", "throw", "rejects", "rejected", "timeout", "denied", "unauthorized", "forbidden",
    "expired", "duplicate", "conflict", "empty", "null", "nil", "none", "negative", "malformed",
    "corrupt", "unavailable", "panic", "exception", "refuses", "refused", "not", "without",
    "unknown", "unsupported", "invalidates", "aborts", "rollback", "retries", "retry",
}

SKIP_RE = re.compile(
    r"@pytest\.mark\.(?:skip|xfail)|pytest\.skip\(|@unittest\.skip|(?<![.\w$])(?:it|test|describe)"
    r"\.(?:skip|todo)\s*\(|\bxit\s*\(|\bxdescribe\s*\(|\bt\.Skip(?:Now)?\(|@Ignore\b|@Disabled\b"
    r"|\[Ignore|#\[ignore\]|markTestSkipped|markTestIncomplete|\bpending\b|@tag\(:skip\)")
FOCUS_RE = re.compile(r"(?<![.\w$])(?:it|test|describe|context)\.only\s*\(|\bfdescribe\s*\("
                      r"|\bfit\s*\(|:focus\b|@Focus\b")
SLEEP_RE = re.compile(r"time\.sleep\s*\(|Thread\.sleep\s*\(|(?<![.\w$])sleep\s*\(\s*[0-9]"
                      r"|waitForTimeout\s*\(|setTimeout\s*\([^,]+,\s*[0-9]{3,}\)"
                      r"|time\.Sleep\s*\(|usleep\s*\(")
PARAM_RE = re.compile(r"@pytest\.mark\.parametrize|(?<![.\w$])(?:it|test|describe)\.each"
                      r"|@ParameterizedTest|\[Theory\]|for\s+_,\s*\w+\s*:=\s*range"
                      r"|for\s+\w+\s+in\s+\[|table\s*:?=|subTest\(|where:")
MOCK_RE = re.compile(r"\bmock\w*\b|\bstub\w*\b|@patch\b|jest\.(?:mock|fn)\(|sinon\.|MagicMock"
                     r"|Mockito|gomock|unittest\.mock", re.IGNORECASE)

# Test names, per language: group 1 (or the first non-empty group) is the name.
NAME_RE = {
    "python": [re.compile(r"^[ \t]*(?:async[ \t]+)?def[ \t]+(test\w*)[ \t]*\(", re.MULTILINE)],
    "javascript": [re.compile(r"(?<![.\w$])(?:it|test)\s*(?:\.\w+)*\s*\(\s*[`'\"]([^`'\"]{1,140})")],
    "go": [re.compile(r"^func[ \t]+(Test\w*)[ \t]*\(", re.MULTILINE),
           re.compile(r"t\.Run\(\s*\"([^\"]{1,140})\"")],
    "java": [re.compile(r"@(?:Test|ParameterizedTest|RepeatedTest)\b[\s\S]{0,240}?"
                        r"(?:void|fun)\s+(?:`([^`]{1,140})`|(\w+))\s*\(")],
    "ruby": [re.compile(r"^[ \t]*(?:it|specify|scenario)[ \t]+['\"]([^'\"]{1,140})", re.MULTILINE),
             re.compile(r"^[ \t]*def[ \t]+(test_\w+)", re.MULTILINE)],
    "php": [re.compile(r"function[ \t]+(test\w+)[ \t]*\(")],
    "rust": [re.compile(r"#\[[\w:]*test\][\s\S]{0,120}?fn\s+(\w+)\s*\(")],
    "csharp": [re.compile(r"\[(?:Fact|Theory|Test|TestMethod|TestCase)[^\]]*\][\s\S]{0,240}?"
                          r"(?:void|Task)\s+(\w+)\s*\(")],
    "elixir": [re.compile(r"^[ \t]*(?:test|property)[ \t]+\"([^\"]{1,140})\"", re.MULTILINE)],
    "scala": [re.compile(r"(?<![.\w])(?:test|it)\s*\(\s*\"([^\"]{1,140})\""),
              re.compile(r"\"([^\"]{1,140})\"\s+(?:should|must|in)\b")],
    "shell": [re.compile(r"^[ \t]*(?:function[ \t]+)?(test_\w+)[ \t]*\(\)", re.MULTILINE)],
    "feature": [re.compile(r"^[ \t]*(?:Scenario Outline|Scenario Template|Scenario|Example):"
                           r"[ \t]*(.+)$", re.MULTILINE)],
}
NAME_RE["typescript"] = NAME_RE["javascript"]
NAME_RE["kotlin"] = NAME_RE["java"]

# Names that describe nothing. "test_1", "it works", "testFoo".
FILLER_WORDS = {
    "", "works", "work", "working", "ok", "okay", "fine", "basic", "simple", "stuff", "thing",
    "things", "foo", "bar", "baz", "qux", "case", "cases", "test", "tests", "testing", "it",
    "example", "sanity", "main", "run", "runs", "todo", "tmp", "temp", "x", "y", "z", "a", "b",
    "success", "successful", "happy", "path", "good", "bad", "new", "old", "one", "two", "three",
    "first", "second", "third", "func", "function", "method", "class", "obj", "object", "data",
}
BEHAVIOUR_WORDS = {
    "returns", "return", "raises", "raise", "throws", "throw", "rejects", "resolves", "fails",
    "fail", "errors", "handles", "handle", "creates", "create", "updates", "update", "deletes",
    "delete", "validates", "validate", "ignores", "ignore", "retries", "retry", "skips", "logs",
    "emits", "calls", "parses", "renders", "redirects", "sends", "saves", "loads", "rounds",
    "sorts", "filters", "counts", "matches", "adds", "removes", "allows", "denies", "preserves",
    "keeps", "propagates", "escapes", "normalises", "normalizes", "converts", "maps", "detects",
    "reports", "exits", "aborts", "caches", "locks", "yields", "wraps", "flags", "scores",
    "should", "must", "does", "expects", "prevents", "truncates", "falls", "defaults",
}
CONDITION_WORDS = {
    "when", "if", "given", "unless", "with", "without", "after", "before", "while", "once",
    "until", "on", "empty", "missing", "invalid", "duplicate", "expired", "disabled",
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
    r"|responses\.add\(|httpretty|stub_request\(|fakeredis|moto\.", re.IGNORECASE)
SPY_RE = re.compile(r"spyOn\(|sinon\.spy|Mockito\.spy|\bspy\(|wraps\s*=|@Spy\b|SpyOn", re.IGNORECASE)
STUB_RE = re.compile(r"\bstub\b|thenReturn|return_value|side_effect|\.Returns\(|mockReturnValue"
                     r"|mockResolvedValue|\.willReturn|and_return", re.IGNORECASE)
MOCK_ASSERT_RE = re.compile(
    r"toHaveBeenCalled\w*|toBeCalled\w*|assert_called\w*|assert_any_call|assert_has_calls"
    r"|assert_not_called|called_once|\.called\b|sinon\.assert|(?<![.\w])verify\s*\("
    r"|verifyNoMoreInteractions|\.Received\(|\.Verify\(|AssertCalled|AssertExpectations"
    r"|AssertNumberOfCalls|toHaveReceived|have_received|shouldReceive")
DOUBLE_CLEANUP_RE = re.compile(
    r"restoreAllMocks|resetAllMocks|clearAllMocks|restoreMocks\s*:|resetMocks\s*:|\.restore\(\)"
    r"|sinon\.restore|@patch\b|with patch|patch\.stopall|addCleanup|monkeypatch"
    r"|defer\s+ctrl\.Finish|ctrl\.Finish\(\)|verifyNoMoreInteractions|afterEach\(|tearDown"
    r"|teardown|td\.reset|nock\.cleanAll")


def name_words(name: str):
    """Split a test name into meaningful lowercase words."""
    text = re.sub(r"^(?:test[_\s-]*|should[_\s-]+|it[_\s-]+)", "", name.strip(), flags=re.IGNORECASE)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-.]+", " ", text)
    return [w.lower() for w in re.findall(r"[A-Za-z]+|\d+", text)]


def classify_name(name: str):
    """Return (is_placeholder, is_descriptive, states_a_condition) for a test name."""
    words = name_words(name)
    meaningful = [w for w in words if not w.isdigit() and w not in FILLER_WORDS]
    placeholder = not meaningful
    behaviour = any(w in BEHAVIOUR_WORDS for w in words) or "should" in name.lower()
    condition = any(w in CONDITION_WORDS for w in words)
    descriptive = not placeholder and (
        len(meaningful) >= 3 or (len(meaningful) >= 2 and (behaviour or condition)))
    return placeholder, descriptive, condition


def extract_names(text: str, lang: str):
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
    re.MULTILINE)
SWALLOW_RE = re.compile(
    r"except[^\n:]*:[ \t]*(?:#[^\n]*)?\n[ \t]*(?:pass|\.\.\.)[ \t]*$"
    r"|catch\s*\([^)]*\)\s*\{\s*\}|contextlib\.suppress|recover\(\)\s*;?\s*\}",
    re.MULTILINE)
DEAD_BRANCH_RE = re.compile(r"^[ \t]*if\s+(?:False|0)\s*:|^[ \t]*if\s*\(\s*(?:false|0)\s*\)",
                            re.MULTILINE)
SKIP_NO_REASON_RE = re.compile(
    r"@pytest\.mark\.skip(?!\w)(?!\s*\(\s*reason)|@unittest\.skip\s*\(\s*\)"
    r"|\bt\.Skip\(\s*\)|@Disabled\s*(?:\n|$)|@Ignore\s*(?:\n|$)")

# Flakiness and environment coupling: the Butterfly, the Local Hero, Resource
# Optimism, Chain Gang / Generous Leftovers.
UNFROZEN_TIME_RE = re.compile(
    r"datetime\.now\(|datetime\.utcnow\(|date\.today\(|time\.time\(|Date\.now\("
    r"|new Date\(\s*\)|time\.Now\(|LocalDate(?:Time)?\.now\(|DateTime\.Now|Time\.now\b"
    r"|Instant\.now\(|System\.currentTimeMillis")
FROZEN_TIME_RE = re.compile(
    r"freeze_time|freezegun|time_machine|useFakeTimers|setSystemTime|MockDate|timecop"
    r"|Clock\.fixed|fixedClock|libfaketime|travel_to|frozen_time", re.IGNORECASE)
UNSEEDED_RANDOM_RE = re.compile(
    r"(?<![.\w])random\.\w+\(|Math\.random\(|uuid4\(|uuid\.New|(?<![.\w])rand\.\w+\("
    r"|secrets\.token|(?<![.\w])Random\(\)|faker\.\w+\(|Faker\(\)")
SEEDED_RANDOM_RE = re.compile(
    r"random\.seed\(|\bseed\s*[=(]|Faker\.seed|faker\.seed|NewSource\(|srand\(", re.IGNORECASE)
ENV_COUPLING_RE = re.compile(
    r"(?:localhost|127\.0\.0\.1):\d+"
    r"|https?://(?!localhost|127\.0\.0\.1|example\.(?:com|org|net)|test\b|foo\b)[\w.-]+\.\w{2,}"
    r"|/home/\w+|/Users/\w+|[A-Z]:\\\\|(?<![\w.])~/\w+")
ORDER_DEPENDENT_RE = re.compile(
    r"def[ \t]+test_?\d{1,2}_|it\(\s*['\"]\d{1,2}[.)_ ]|pytest\.mark\.dependency"
    r"|@Test\s*\([^)]*dependsOn|@(?:FixMethodOrder|TestMethodOrder)|\.serial\b"
    r"|^[ \t]*global[ \t]+\w+", re.MULTILINE)

# The Giant, the Eager Test, Assertion Roulette, Conditional Test Logic.
BRANCH_RE = re.compile(r"^[ \t]*(?:\}[ \t]*)?(?:if|switch|match)[ \t(]", re.MULTILINE)
ELSE_RE = re.compile(r"^[ \t]*(?:\}[ \t]*)?(?:else|elif)\b", re.MULTILINE)
# `if got != want { t.Fatal(...) }` is how a stdlib-style Go test asserts, and
# `if (x) fail()` is the same idea elsewhere: a guard, not branching logic.
GUARD_RE = re.compile(r"\bt\.(?:Error|Fatal|Skip)\w*\(|(?<![.\w])fail\w*\(|\bassert\w*\b"
                      r"|(?<![.\w$])expect\s*\(|\braise\b|\bthrow\b")


def conditional_logic(block: str, window=400):
    """Branches that decide what a test checks, ignoring assertion guards."""
    count = 0
    for match in BRANCH_RE.finditer(block):
        tail = block[match.start():match.start() + window]
        if ELSE_RE.search(tail[len(match.group(0)):]):
            count += 1          # an if/else picks between outcomes
        elif not GUARD_RE.search(tail):
            count += 1          # a branch that guards behaviour, not a failure
    return count
SETUP_BLOCK_RE = re.compile(
    r"^[ \t]*(?:def[ \t]+(?:setUp|setup_method|setup_class|setup_module)\b"
    r"|(?:before(?:Each|All))\s*\(|@(?:Before|BeforeEach|BeforeAll)\b"
    r"|def[ \t]+\w+\([^)]*\):[ \t]*(?:#[^\n]*)?$)", re.MULTILINE)

# Ecosystems differ, and a single set of thresholds mis-scores most of them.
# Go tests are verbose (table-driven, explicit error checks) so a 0.5x test:code
# ratio is a low bar; pytest is terse so it is a high one. pytest and jest print
# the compared values on failure, so a bare assert is fine there — JUnit's
# assertTrue(x) tells you nothing, which is where Assertion Roulette came from.
LANGUAGE_PROFILES = {
    #                 test:code  cases/file  bare-assert check  spec-style is idiomatic
    "python":        (0.50,      2.0,        False,             False),
    "javascript":    (0.60,      2.0,        True,              True),
    "typescript":    (0.60,      2.0,        True,              True),
    "go":            (0.80,      1.5,        True,              False),
    "java":          (0.90,      2.0,        True,              False),
    "kotlin":        (0.80,      2.0,        True,              False),
    "csharp":        (0.90,      2.0,        True,              False),
    "ruby":          (0.70,      2.5,        False,             True),
    "php":           (0.70,      2.0,        True,              False),
    "rust":          (0.40,      1.5,        False,             False),
    "elixir":        (0.50,      2.0,        False,             False),
    "scala":         (0.70,      2.0,        False,             True),
    "shell":         (0.30,      1.0,        False,             False),
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


def blend_profile(language_lines):
    """Weight each ecosystem's thresholds by how much of the source it is."""
    total = sum(language_lines.values())
    if not total:
        return {"test_code_ratio": DEFAULT_PROFILE[0], "cases_per_source": DEFAULT_PROFILE[1],
                "bare_assert_check": False, "spec_style_idiomatic": False, "languages": []}
    ratio = cases = 0.0
    bare = spec = 0.0
    for lang, lines in language_lines.items():
        target_ratio, target_cases, bare_check, spec_ok = LANGUAGE_PROFILES.get(
            lang, DEFAULT_PROFILE)
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
        "bare_assert_check": bare >= 0.5,
        "spec_style_idiomatic": spec >= 0.5,
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
    r"|\.repeat\(\s*\d{3,}|\*\s*\d{4,}")
BOUNDARY_NAME_WORDS = {
    "empty", "zero", "negative", "max", "maximum", "min", "minimum", "boundary", "boundaries",
    "edge", "overflow", "underflow", "limit", "limits", "blank", "whitespace", "unicode",
    "huge", "truncates", "truncated", "rounding", "precision", "offbyone", "single", "nothing",
}
# Suites pinned to one worker cannot be run in parallel — an independence smell.
SERIAL_ONLY_RE = re.compile(
    r"--runInBand|maxWorkers\s*[:=]\s*['\"]?1\b|--max-workers[= ]1|-p\s+no:randomly"
    r"|pytest\.mark\.serial|describe\.serial|test\.describe\.serial|@Execution\(\s*SAME_THREAD"
    r"|@NotThreadSafe|-parallel[= ]1|--serial\b")

# The Loudmouth: console chatter instead of assertions.
CHATTER_RE = re.compile(r"(?<![.\w])print\s*\(|console\.(?:log|debug|info)\s*\("
                        r"|System\.out\.print|fmt\.Print|(?<![.\w])puts\s+")
# The Operating System Evangelist: a test that branches on the platform.
PLATFORM_RE = re.compile(r"sys\.platform|os\.name\b|process\.platform|runtime\.GOOS"
                         r"|System\.getProperty\(\s*[\"']os\.name|RUBY_PLATFORM|PHP_OS")
# The Greedy Catcher: the failure is logged, then the test passes anyway.
GREEDY_CATCH_RE = re.compile(
    r"except[^\n:]*:[ \t]*(?:#[^\n]*)?\n[ \t]*(?:print|log\w*|logger\.\w+|console\.\w+)\s*\("
    r"|catch\s*\([^)]*\)\s*\{[ \t]*\n?[ \t]*console\.\w+\s*\([^)]*\)[ \t]*;?[ \t]*\n?[ \t]*\}",
    re.MULTILINE)

# Brittle locators: record-and-playback output and hand-written positional
# XPath, the standard cause of flaky UI tests.
BRITTLE_SELECTOR_RE = re.compile(
    r"//\w+\[\d+\]|//\*\[|//div\b|//span\b|//tr\[|nth-child\(|nth-of-type\("
    r"|find_element_by_xpath|By\.xpath|\$x\(|\.css-[a-z0-9]{5,}|Mui[A-Z]\w+-root"
    r"|>\s*div\s*>\s*div|\[class\^=|\[class\*=")
ROBUST_SELECTOR_RE = re.compile(
    r"getBy(?:Role|TestId|LabelText|Text|Title|PlaceholderText)|findBy(?:Role|TestId)"
    r"|data-testid|byTestId|By\.id\(|getByAltText|screen\.getBy")

# The Ugly Mirror / Doppelgänger: the expected value is recomputed from the
# inputs, so the test cannot catch a wrong formula — it shares it.
MIRROR_SAFE_CALLS = (r"pytest\.approx|approx|mock\.ANY|len|str|int|float|bool|repr|sorted|list"
                     r"|dict|set|tuple|frozenset|bytes|Decimal|datetime|date|time|UUID|Path"
                     r"|json\.loads|json\.dumps|Number|String|Array|Object|BigInt")
_MIRROR_EXPECTED = (r"(?!(?:" + MIRROR_SAFE_CALLS + r")\s*\()[\w.]*[A-Za-z_]\w*"
                    r"\([^)\n]*[A-Za-z_]\w*[^)\n]*\)")
MIRROR_RE = re.compile(
    r"==\s*" + _MIRROR_EXPECTED
    + r"|\.(?:toBe|toEqual|toStrictEqual|toHaveValue)\(\s*" + _MIRROR_EXPECTED
    + r"|assert(?:Equals?|That)\([^,\n]+,\s*" + _MIRROR_EXPECTED)

# The Inspector / Anal Probe: reaching into internals instead of behaviour.
PRIVATE_ACCESS_RE = re.compile(
    r"\.(_[a-zA-Z]\w*)\b(?!\s*=\s*(?:Mock|MagicMock))|\.#(\w+)|getDeclaredField|setAccessible"
    r"|__dict__|\breflect\.ValueOf|Reflect\.get\(")

# Symbols a repo actually defines, so a test referring to anything else can be
# flagged as dead or invented.
SYMBOL_RE = {
    "python": [re.compile(r"^[ \t]*(?:async[ \t]+)?def[ \t]+(\w+)", re.MULTILINE),
               re.compile(r"^[ \t]*class[ \t]+(\w+)", re.MULTILINE),
               re.compile(r"^(\w+)[ \t]*(?::[^=\n]+)?=", re.MULTILINE)],
    "javascript": [re.compile(r"(?:export[ \t]+)?(?:async[ \t]+)?function[ \t]+(\w+)"),
                   re.compile(r"(?:export[ \t]+)?(?:const|let|var|class)[ \t]+(\w+)"),
                   re.compile(r"export[ \t]*\{([^}]*)\}")],
    "go": [re.compile(r"^func[ \t]+(?:\([^)]*\)[ \t]*)?(\w+)", re.MULTILINE),
           re.compile(r"^type[ \t]+(\w+)", re.MULTILINE)],
    "ruby": [re.compile(r"^[ \t]*def[ \t]+(\w+)", re.MULTILINE),
             re.compile(r"^[ \t]*(?:class|module)[ \t]+(\w+)", re.MULTILINE)],
    "php": [re.compile(r"function[ \t]+(\w+)"), re.compile(r"(?:class|trait)[ \t]+(\w+)")],
    "rust": [re.compile(r"(?:pub[ \t]+)?fn[ \t]+(\w+)"),
             re.compile(r"(?:pub[ \t]+)?(?:struct|enum|trait)[ \t]+(\w+)")],
}
SYMBOL_RE["typescript"] = SYMBOL_RE["javascript"]
# Only languages whose imports name the symbols they pull in can be checked.
PHANTOM_LANGS = {"python", "javascript", "typescript"}
PY_IMPORT_RE = re.compile(r"^[ \t]*from[ \t]+([.\w]+)[ \t]+import[ \t]+(\([^)]*\)|[^\n#]+)",
                          re.MULTILINE)
JS_IMPORT_RE = re.compile(r"import[ \t]*\{([^}]*)\}[ \t]*from[ \t]*['\"](\.[^'\"]*)['\"]"
                          r"|(?:const|let|var)[ \t]*\{([^}]*)\}[ \t]*=[ \t]*require\("
                          r"[ \t]*['\"](\.[^'\"]*)['\"]")


def line_of(text: str, offset: int):
    return text.count("\n", 0, offset) + 1


def normalise_body(block: str):
    """A case body with its name, comments and literals removed, for duplicate hunting."""
    body = block.split("\n", 1)[1] if "\n" in block else ""
    body = COMMENT_RE.sub("", body)
    body = LITERAL_RE.sub("@", body)
    return re.sub(r"\s+", " ", body).strip()


def imported_project_names(text: str, lang: str, modules: set):
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

def read_text(path: Path):
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        return path.read_text(errors="replace")
    except OSError:
        return None


def walk(root: Path):
    """Yield (absolute_path, relative_path, in_artifact_dir) for every file."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            abs_path = Path(dirpath) / name
            rel = abs_path.relative_to(root)
            in_artifact = any(p in ARTIFACT_DIRS for p in rel.parts[:-1])
            yield abs_path, rel, in_artifact


def language_of(rel: Path):
    if rel.suffix == ".feature":
        return "feature"
    return LANG_BY_EXT.get(rel.suffix)


def classify_kind(rel: Path, text: str):
    """Return (kind, flags) for one test file. Most specific signal wins."""
    flags = set()
    dirs = {p.lower() for p in rel.parts[:-1]} | {rel.stem.lower()}
    kind = None
    for candidate, hints in KIND_DIR_HINTS:
        if dirs & hints:
            kind = candidate
            break
    # Conjoined Twins: filed as a unit test, but talking to something real.
    if kind == "unit" and any(pattern.search(text) for name, pattern in KIND_CONTENT_HINTS
                              if name in {"integration", "e2e"}):
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
    if GHERKIN_RE.search(text):
        flags.add("bdd")
    if SPEC_STYLE_RE.search(text):
        flags.add("spec-style")
    if PROPERTY_RE.search(text):
        flags.add("property")
    if SNAPSHOT_RE.search(text):
        flags.add("snapshot")
    if PARAM_RE.search(text):
        flags.add("parametrized")
    if MOCK_RE.search(text):
        flags.add("mocked")
    return kind, flags


def with_decorators(text: str, start: int):
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


def analyse_test_file(rel: Path, text: str, lang: str):
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
    for i, start in enumerate(blocks):
        end = blocks[i + 1] if i + 1 < len(blocks) else len(text)
        block = text[start:end]
        assertions = len(assert_re.findall(block))
        mock_assertions = len(MOCK_ASSERT_RE.findall(block))
        block_doubles = len(DOUBLE_RE.findall(block))
        weak = len(WEAK_ASSERT_RE.findall(block)) + len(TAUTOLOGY_RE.findall(block))
        if bare_re:
            weak += len(bare_re.findall(block))
        weak = min(weak, assertions)
        weak_assertions += weak
        if not assertions:
            without += 1
        elif weak == assertions:
            # It asserts, but only that something is truthy/not-null/a snapshot.
            weak_only += 1
        if block_doubles:
            cases_with_doubles += 1
            doubles += block_doubles
        # A case whose every assertion is an interaction check tests the double,
        # not the behaviour.
        if mock_assertions and assertions <= mock_assertions:
            mock_only += 1
        first_line = block.split("\n", 1)[0]
        words = set(name_words(first_line))
        if ERROR_ASSERT_RE.search(block) or words & ERROR_NAME_WORDS:
            error_cases += 1
        if BOUNDARY_RE.search(block) or words & BOUNDARY_NAME_WORDS:
            boundary_cases += 1
        body = normalise_body(block)
        if len(body) >= 20:
            bodies.append((body, line_of(text, start)))

        body_lines = [ln for ln in block.splitlines()[1:] if ln.strip()]
        if len(body_lines) > 50:
            giant_cases += 1
        if assertions > 10:
            roulette_cases += 1
        if conditional_logic(block) > 0:
            branching_cases += 1
        for match in MIRROR_RE.finditer(block):
            mirrors.append({"file": str(rel), "line": line_of(text, start + match.start()),
                            "kind": "mirror-assertion",
                            "message": "the expected value is recomputed from the inputs — "
                                       "the test shares the formula it is meant to check"})
    # Doubles wired up in setUp/beforeEach, outside any single case.
    doubles += len(DOUBLE_RE.findall(text[:blocks[0]] if blocks else text))

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

    uninformative = len(UNINFORMATIVE_ASSERT_RE[lang].findall(text)) \
        if lang in UNINFORMATIVE_ASSERT_RE else 0
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
        rest = text[setup_match.end():].splitlines()
        for line in rest:
            if line.strip() and not line[:1].isspace():
                break
            setup_lines += 1 if line.strip() else 0

    brittle = []
    if not ROBUST_SELECTOR_RE.search(text):
        for match in BRITTLE_SELECTOR_RE.finditer(text):
            brittle.append({"file": str(rel), "line": line_of(text, match.start()),
                            "kind": "brittle-selector",
                            "message": "positional or generated locator — prefer a role, label "
                                       "or data-testid that survives a redesign"})

    suppressed = []
    for match in PRIVATE_ACCESS_RE.finditer(text):
        member = next((g for g in match.groups() if g), "an internal")
        suppressed.append({"file": str(rel), "line": line_of(text, match.start()),
                           "kind": "implementation-access",
                           "message": f"reaches into `{member}` — testing the implementation, "
                                      "not the behaviour"})
    for pattern, message in (
            (COMMENTED_ASSERT_RE, "assertion commented out"),
            (GREEDY_CATCH_RE, "failure logged and swallowed — the test still passes"),
            (SWALLOW_RE, "failure swallowed by an empty except/catch"),
            (DEAD_BRANCH_RE, "assertions behind an `if False` branch"),
            (SKIP_NO_REASON_RE, "test skipped with no reason given")):
        for match in pattern.finditer(text):
            suppressed.append({"file": str(rel), "line": line_of(text, match.start()),
                               "kind": "suppressed-failure", "message": message})

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


# ----------------------------------------------------------------- coverage

COVERAGE_CONFIG_FILES = {
    ".coveragerc", "setup.cfg", "pyproject.toml", "tox.ini", "pytest.ini", "package.json",
    "jest.config.js", "jest.config.ts", "jest.config.mjs", "jest.config.json", ".nycrc",
    ".nycrc.json", ".nycrc.yml", "vitest.config.ts", "vitest.config.js", "codecov.yml",
    ".codecov.yml", "pom.xml", "build.gradle", "build.gradle.kts", ".simplecov", "Makefile",
    "phpunit.xml", "phpunit.xml.dist", "sonar-project.properties", "Cargo.toml", "karma.conf.js",
}
COVERAGE_TOOL_RE = re.compile(
    r"--cov\b|\bcoverage\b|\bnyc\b|istanbul|jacoco|codecov|coveralls|simplecov|tarpaulin"
    r"|-coverprofile|opencover|\bc8\b|clover|pytest-cov|@vitest/coverage", re.IGNORECASE)
THRESHOLD_PATTERNS = [
    re.compile(r"fail_under\s*[:=]\s*(\d{1,3})"),
    re.compile(r"--cov-fail-under[=\s]+(\d{1,3})"),
    re.compile(r"--fail-under[=\s]+(\d{1,3})"),
    re.compile(r"coverageThreshold[\s\S]{0,400}?[\"']?(?:lines|statements)[\"']?\s*:\s*(\d{1,3})"),
    re.compile(r"check-coverage[\s\S]{0,300}?lines[\"'=:\s]+(\d{1,3})"),
    re.compile(r"minimum_coverage\s*[:=\s]\s*(\d{1,3})"),
    re.compile(r"(?:coverage[_-]?)?target:\s*(\d{1,3})%?"),
    re.compile(r"<minimum>\s*0?\.(\d{1,2})\s*</minimum>"),
]


def parse_cobertura(text):
    m = re.search(r'line-rate="([0-9.]+)"', text)
    return round(float(m.group(1)) * 100, 1) if m else None


def parse_lcov(text):
    found = sum(int(x) for x in re.findall(r"^LF:(\d+)", text, re.MULTILINE))
    hit = sum(int(x) for x in re.findall(r"^LH:(\d+)", text, re.MULTILINE))
    return round(hit / found * 100, 1) if found else None


def parse_jacoco(text):
    counters = re.findall(r'<counter type="LINE" missed="(\d+)" covered="(\d+)"', text)
    if not counters:
        return None
    missed, covered = max(((int(a), int(b)) for a, b in counters), key=sum)
    total = missed + covered
    return round(covered / total * 100, 1) if total else None


def parse_go_profile(text):
    total = covered = 0
    for line in text.splitlines():
        m = re.match(r"^.+:\d+\.\d+,\d+\.\d+ (\d+) (\d+)$", line)
        if m:
            statements, count = int(m.group(1)), int(m.group(2))
            total += statements
            if count > 0:
                covered += statements
    return round(covered / total * 100, 1) if total else None


def parse_json_report(text):
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    if isinstance(data, dict):
        totals = data.get("totals")
        if isinstance(totals, dict) and "percent_covered" in totals:
            return round(float(totals["percent_covered"]), 1)
        total = data.get("total")
        if isinstance(total, dict):
            lines = total.get("lines")
            if isinstance(lines, dict) and "pct" in lines:
                return round(float(lines["pct"]), 1)
    return None


def cobertura_files(text):
    out = {}
    for tag in re.finditer(r"<class\b[^>]*>", text):
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', tag.group(0)))
        if "filename" in attrs and "line-rate" in attrs:
            out[Path(attrs["filename"]).name] = round(float(attrs["line-rate"]) * 100, 1)
    return out


def lcov_files(text):
    out = {}
    current, found, hit = None, 0, 0
    for line in text.splitlines():
        if line.startswith("SF:"):
            current, found, hit = line[3:], 0, 0
        elif line.startswith("LF:"):
            found = int(line[3:] or 0)
        elif line.startswith("LH:"):
            hit = int(line[3:] or 0)
        elif line.startswith("end_of_record") and current and found:
            out[Path(current).name] = round(hit / found * 100, 1)
            current = None
    return out


def jacoco_files(text):
    out = {}
    for block in re.finditer(r"<sourcefile[^>]*name=\"([^\"]+)\"[^>]*>(.*?)</sourcefile>",
                             text, re.DOTALL):
        counters = re.findall(r'<counter type="LINE" missed="(\d+)" covered="(\d+)"',
                              block.group(2))
        if counters:
            missed, covered = (int(counters[-1][0]), int(counters[-1][1]))
            total = missed + covered
            if total:
                out[Path(block.group(1)).name] = round(covered / total * 100, 1)
    return out


def go_profile_files(text):
    totals = {}
    for line in text.splitlines():
        match = re.match(r"^(.+?):\d+\.\d+,\d+\.\d+ (\d+) (\d+)$", line)
        if not match:
            continue
        name = Path(match.group(1)).name
        statements, count = int(match.group(2)), int(match.group(3))
        covered, total = totals.get(name, (0, 0))
        totals[name] = (covered + (statements if count else 0), total + statements)
    return {name: round(c / t * 100, 1) for name, (c, t) in totals.items() if t}


def json_report_files(text):
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return {}
    out = {}
    if isinstance(data, dict):
        files = data.get("files")
        if isinstance(files, dict):  # python coverage json
            for path, entry in files.items():
                pct = (entry or {}).get("summary", {}).get("percent_covered")
                if isinstance(pct, (int, float)):
                    out[Path(path).name] = round(float(pct), 1)
        for path, entry in data.items():  # istanbul summary
            if path in {"total", "files", "totals"} or not isinstance(entry, dict):
                continue
            pct = (entry.get("lines") or {}).get("pct")
            if isinstance(pct, (int, float)):
                out[Path(path).name] = round(float(pct), 1)
    return out


PER_FILE_COVERAGE = {
    parse_cobertura: cobertura_files,
    parse_lcov: lcov_files,
    parse_jacoco: jacoco_files,
    parse_go_profile: go_profile_files,
    parse_json_report: json_report_files,
}


COVERAGE_REPORTS = [
    (re.compile(r"^(?:coverage|cobertura(?:-coverage)?|clover)\.xml$"), parse_cobertura),
    (re.compile(r"^jacoco.*\.xml$", re.IGNORECASE), parse_jacoco),
    (re.compile(r"^lcov\.info$|\.lcov$"), parse_lcov),
    (re.compile(r"^(?:coverage-summary|coverage-final|coverage)\.json$"), parse_json_report),
    (re.compile(r"^(?:coverage|cover|profile)\.(?:out|cov)$"), parse_go_profile),
]


def measure_coverage(rel: Path, path: Path):
    """Return (total_percent, {basename: percent}) for a coverage report."""
    for pattern, parser in COVERAGE_REPORTS:
        if pattern.search(rel.name):
            text = read_text(path)
            if text is None:
                return None, {}
            if (rel.name.endswith(".xml") and "jacoco" not in rel.name.lower()
                    and "<counter" in text and "line-rate" not in text):
                parser = parse_jacoco
            total = parser(text)
            if total is None:
                return None, {}
            return total, PER_FILE_COVERAGE[parser](text)
    return None, {}


def parse_stryker(text):
    """Stryker mutation.json: files -> mutants -> status."""
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    files = data.get("files")
    if not isinstance(files, dict):
        return None
    killed = total = 0
    for entry in files.values():
        for mutant in (entry or {}).get("mutants", []):
            status = str(mutant.get("status", "")).lower()
            if status in {"killed", "timeout"}:
                killed += 1
                total += 1
            elif status in {"survived", "nocoverage", "no coverage"}:
                total += 1
    return round(killed / total * 100, 1) if total else None


def parse_pitest(text):
    """PIT mutations.xml: <mutation detected='true' status='KILLED'>."""
    detections = re.findall(r"<mutation[^>]*\bdetected=[\"']([a-z]+)[\"']", text, re.IGNORECASE)
    if not detections:
        return None
    killed = sum(1 for d in detections if d.lower() == "true")
    return round(killed / len(detections) * 100, 1)


def parse_cargo_mutants(text):
    """cargo-mutants outcomes.json: summary per mutant."""
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    outcomes = data.get("outcomes") if isinstance(data, dict) else None
    if not isinstance(outcomes, list):
        return None
    caught = missed = 0
    for outcome in outcomes:
        summary = str((outcome or {}).get("summary", "")).lower()
        if summary in {"caughtmutant", "caught"}:
            caught += 1
        elif summary in {"missedmutant", "missed"}:
            missed += 1
    total = caught + missed
    return round(caught / total * 100, 1) if total else None


def parse_generic_mutation(text):
    """Anything exposing a mutation score directly."""
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    for key in ("mutationScore", "mutation_score", "score"):
        value = data.get(key)
        if isinstance(value, (int, float)) and 0 <= value <= 100:
            return round(float(value), 1)
    return None


MUTATION_REPORTS = [
    (re.compile(r"^mutations?\.xml$|^mutations-report\.xml$", re.IGNORECASE), parse_pitest),
    (re.compile(r"^outcomes\.json$"), parse_cargo_mutants),
    (re.compile(r"^(?:mutation|stryker)[\w.-]*\.json$", re.IGNORECASE), parse_stryker),
]


def measure_mutation(rel: Path, path: Path):
    for pattern, parser in MUTATION_REPORTS:
        if pattern.search(rel.name):
            text = read_text(path)
            if text is None:
                return None
            return parser(text) or (parse_generic_mutation(text) if rel.suffix == ".json"
                                    else None)
    return None


def find_threshold(texts):
    best = None
    for text in texts:
        for pattern in THRESHOLD_PATTERNS:
            for raw in pattern.findall(text):
                value = int(raw)
                if pattern.pattern.startswith("<minimum>"):
                    value = value * 10 if value < 10 else value
                if 1 <= value <= 100:
                    best = value if best is None else max(best, value)
    return best


# ----------------------------------------------------------------------- CI

CI_FILES = re.compile(r"^(?:\.gitlab-ci\.ya?ml|Jenkinsfile|azure-pipelines\.ya?ml"
                      r"|\.travis\.ya?ml|bitbucket-pipelines\.ya?ml|\.drone\.ya?ml)$")
TEST_CMD_RE = re.compile(
    r"\bpytest\b|\btox\b|\bnox\b|python -m unittest|npm (?:run )?test|yarn test|pnpm test"
    r"|\bjest\b|\bvitest\b|\bmocha\b|\bcypress run\b|playwright test|go test|mvn .*test"
    r"|gradle\w* .*test|\brspec\b|\bphpunit\b|cargo test|dotnet test|make test|\bbats\b"
    r"|\bbehave\b|\bcucumber\b|mix test", re.IGNORECASE)
CI_COVERAGE_RE = re.compile(r"codecov|coveralls|--cov|coverprofile|coverage", re.IGNORECASE)
CI_STRICT_RE = re.compile(r"strategy:\s*\n\s*matrix|matrix:|-race\b|--strict|fail-fast"
                          r"|--fail-under|coverageThreshold|--check-coverage", re.IGNORECASE)


def is_ci_file(rel: Path):
    parts = [p.lower() for p in rel.parts]
    if ".github" in parts and "workflows" in parts and rel.suffix in {".yml", ".yaml"}:
        return True
    if ".circleci" in parts and rel.name in {"config.yml", "config.yaml"}:
        return True
    return bool(CI_FILES.match(rel.name))


# ---------------------------------------------------------------------- git

# "Not converting production bugs into regression tests" — a fix that ships no
# test is a bug free to come back.
FIX_COMMIT_RE = re.compile(r"\b(?:fix|fixes|fixed|bug|bugfix|hotfix|regression|patch|repair)\b",
                           re.IGNORECASE)


def git_history(root: Path, limit=400):
    """Commit-level TDD signal: do source changes arrive with test changes?"""
    def run(*args):
        try:
            result = subprocess.run(["git", "-C", str(root), *args],
                                    capture_output=True, text=True, timeout=60, check=False)
        except (OSError, subprocess.SubprocessError):
            return None
        return result.stdout if result.returncode == 0 else None

    # git reports paths from the repository root while the scan uses paths
    # relative to wherever it started. Without stripping the prefix, nothing
    # matches on a subdirectory scan and the stale-test and pairing checks
    # silently find nothing.
    prefix = run("rev-parse", "--show-prefix")
    if prefix is None:
        return None
    prefix = prefix.strip()
    log = run("log", "-n", str(limit), "--no-merges", "--name-only",
              "--pretty=format:%x00%H %s", "--", ".")
    if not log or not log.strip():
        return None

    commits = source_commits = cochanged = test_only = 0
    fix_commits = fix_commits_with_tests = 0
    file_commits = {}
    for position, chunk in enumerate(log.split("\x00")):
        rows = chunk.splitlines()
        subject = rows[0] if rows else ""
        lines = [ln for ln in rows[1:] if ln.strip()]
        if prefix:
            lines = [ln[len(prefix):] for ln in lines if ln.startswith(prefix)]
        if not lines:
            continue
        commits += 1
        is_fix = bool(FIX_COMMIT_RE.search(subject))
        # Position in the log, newest first: ordering beats timestamps, which
        # collapse when several commits land in the same second.
        for line in lines:
            file_commits.setdefault(line, []).append(position)
        paths = [Path(ln) for ln in lines]
        tests = [p for p in paths if is_test_file(p)]
        sources = [p for p in paths
                   if not is_test_file(p) and p.suffix in LANG_BY_EXT]
        if sources:
            source_commits += 1
            if tests:
                cochanged += 1
            if is_fix:
                fix_commits += 1
                if tests:
                    fix_commits_with_tests += 1
        elif tests:
            test_only += 1
    return {
        "commits_analysed": commits,
        "source_commits": source_commits,
        "source_commits_with_tests": cochanged,
        "test_only_commits": test_only,
        "fix_commits": fix_commits,
        "fix_commits_with_tests": fix_commits_with_tests,
        "file_commits": file_commits,
    }


def find_hotspots(file_commits, source_files, tested, coverage_by_file, limit=20):
    """Kapelonis AP4: is the code that changes most often the code under test?"""
    churn = sorted(((len(file_commits.get(path, [])), path) for path in source_files),
                   key=lambda item: (-item[0], item[1]))
    churn = [(count, path) for count, path in churn if count > 1]
    if len(churn) < 3:
        return None      # too little history to say which files are hot
    hot_count = max(5, round(len(churn) * 0.2))
    hot = churn[:hot_count]
    findings = []
    covered = []
    untested = 0
    for count, path in hot:
        pct = coverage_by_file.get(Path(path).name)
        if pct is not None:
            covered.append(pct)
        if path not in tested:
            untested += 1
            if len(findings) < limit:
                findings.append({
                    "file": path, "line": 0, "kind": "untested-hotspot",
                    "message": f"changed {count} times and has no test file — "
                               "the code that breaks most often is untested",
                })
    return {
        "hot_files": len(hot),
        "untested_hot_files": untested,
        "hot_coverage": round(sum(covered) / len(covered), 1) if covered else None,
        "findings": findings,
    }


# --------------------------------------------------------------- substance

def source_stem(rel: Path):
    """The source file stem a test file is named after, if any."""
    stem = rel.stem
    name = stem
    if rel.suffix == ".py":
        name = name[5:] if name.startswith("test_") else re.sub(r"_test$", "", name)
    elif rel.suffix in JS_EXT:
        name = re.sub(r"\.(test|spec)$", "", name)
    elif rel.suffix == ".go":
        name = re.sub(r"_test$", "", name)
    elif rel.suffix in {".java", ".kt"}:
        name = re.sub(r"(?:Tests?|Spec|IT)$", "", name)
    elif rel.suffix == ".rb":
        name = re.sub(r"_(?:spec|test)$", "", name)
    elif rel.suffix in {".php", ".cs"}:
        name = re.sub(r"(?:Tests?|Spec)$", "", name)
    elif rel.suffix == ".exs":
        name = re.sub(r"_test$", "", name)
    return name if name and name != stem else None


def find_duplicates(bodies_by_file, limit=20, min_cluster=3):
    """Cases whose bodies are identical once names and literals are stripped.

    Two matching bodies are common and often legitimate; three or more is a
    copy-paste run, and the fix is one parametrised case.
    """
    clusters = {}
    for file, bodies in bodies_by_file:
        for body, line in bodies:
            clusters.setdefault(body, []).append((file, line))
    findings = []
    redundant = 0
    for places in sorted(clusters.values(), key=len, reverse=True):
        if len(places) < min_cluster:
            continue
        redundant += len(places) - 1
        origin = places[0]
        for file, line in places[1:]:
            if len(findings) < limit:
                findings.append({
                    "file": file, "line": line, "kind": "duplicate-case",
                    "message": f"same body as {origin[0]}:{origin[1]} — parametrise instead",
                })
    return redundant, findings


def find_phantoms(imports_by_file, symbols, limit=20):
    """Test imports of project symbols that no source file defines."""
    findings = []
    seen = set()
    for file, names in imports_by_file:
        for name in names:
            if name in symbols or (file, name) in seen:
                continue
            seen.add((file, name))
            if len(findings) < limit:
                findings.append({
                    "file": file, "line": 0, "kind": "phantom-symbol",
                    "message": f"imports `{name}`, which no source file defines — "
                               "dead or invented test",
                })
    return len(seen), findings


def find_stale(pairs, file_commits, min_changes=5, limit=20):
    """Tests frozen while the code they cover kept changing.

    Positions come from `git log` newest-first, so a lower number is a more
    recent commit.
    """
    findings = []
    stale = 0
    for test_file, source_file in pairs:
        test_positions = file_commits.get(test_file)
        source_positions = file_commits.get(source_file)
        if not test_positions or not source_positions:
            continue
        last_test = min(test_positions)
        changes = sum(1 for position in source_positions if position < last_test)
        if changes >= min_changes:
            stale += 1
            if len(findings) < limit:
                findings.append({
                    "file": test_file, "line": 0, "kind": "stale-test",
                    "message": f"{source_file} changed {changes} times since this test last did",
                })
    return stale, findings


def find_decorative(pairs, file_coverage, threshold=40.0, limit=20):
    """Source files that have a test file and are still barely covered."""
    findings = []
    decorative = 0
    for test_file, source_file in pairs:
        pct = file_coverage.get(source_file)
        if pct is None or pct >= threshold:
            continue
        decorative += 1
        if len(findings) < limit:
            findings.append({
                "file": test_file, "line": 0, "kind": "decorative-test",
                "message": f"{source_file} has this test file and is still {pct:.0f}% covered",
            })
    return decorative, findings


# ------------------------------------------------------------------ collect

def collect(root: Path, use_git=True):
    stats = {
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
    config_texts = []
    ci_texts = []
    bodies_by_file = []
    imports_by_file = []
    symbols = set()
    source_symbols = set()
    test_names = []
    source_by_stem = {}
    source_paths = []
    test_paths = []
    modules = {p.name for p in root.iterdir() if p.is_dir()} if root.is_dir() else set()

    for abs_path, rel, in_artifact in walk(root):
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

        if in_artifact:
            continue
        lang = language_of(rel)
        if lang is None:
            continue
        if is_test_file(rel):
            text = read_text(abs_path)
            if text is None:
                continue
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
                stats["findings"].append({
                    "file": str(rel), "line": 0, "kind": "conjoined-twin",
                    "message": "filed as a unit test but talks to a real database, HTTP "
                               "service or browser — it is an integration test",
                })
            for key in ("cases", "assertions", "cases_without_assertions",
                        "skips", "focused", "sleeps", "weak_assertions", "weak_only_cases",
                        "error_cases", "giant_cases", "roulette_cases", "branching_cases",
                        "chatter", "platform_branches", "boundary_cases",
                        "uninformative_assertions",
                        "unfrozen_time", "unseeded_random", "env_coupling", "order_dependent",
                        "doubles", "cases_with_doubles",
                        "mock_only_cases", "test_names", "placeholder_names",
                        "descriptive_names", "conditional_names", "name_words"):
                stats[key] += info[key]
            stats["double_cleanup"] = stats["double_cleanup"] or info["double_cleanup"]
            if info["spies"]:
                stats["double_kinds"].add("spies")
            if info["stubs"]:
                stats["double_kinds"].add("stubs")
            if info["doubles"]:
                stats["double_kinds"].add("mocks")
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
            for pattern in SYMBOL_RE.get(lang, []):
                for match in pattern.findall(text):
                    for name in str(match).split(","):
                        name = name.strip().split(" as ")[-1].strip()
                        if name.isidentifier():
                            symbols.add(name)
            if lang in PHANTOM_LANGS:
                imports_by_file.append((str(rel), imported_project_names(text, lang, modules)))
            if "bdd" in info["flags"]:
                stats["bdd_cases"] += info["cases"]
            elif "spec-style" in info["flags"]:
                stats["spec_cases"] += info["cases"]
        else:
            stats["source_files"] += 1
            stats["languages"][lang] += 1
            source_by_stem.setdefault(rel.stem, rel)
            source_paths.append(str(rel))
            modules.add(rel.stem)
            text = read_text(abs_path)
            if text:
                lines = sum(1 for line in text.splitlines() if line.strip())
                stats["source_lines"] += lines
                stats["language_lines"][lang] += lines
                for pattern in SYMBOL_RE.get(lang, []):
                    for match in pattern.findall(text):
                        for name in str(match).split(","):
                            name = name.strip().split(" as ")[-1].strip()
                            if name.isidentifier():
                                symbols.add(name)
                                source_symbols.add(name.lower())

    stats["profile"] = blend_profile(stats["language_lines"])
    stats["coverage_threshold"] = find_threshold(config_texts + ci_texts)
    if use_git:
        stats["git"] = git_history(root)

    for name in test_names:
        words = [w for w in name_words(name) if w not in FILLER_WORDS]
        if 1 <= len(words) <= 2 and "_".join(words) in source_symbols:
            stats["method_mirror_names"] += 1

    symbols |= modules | {stem for stem in source_by_stem}

    stats["duplicate_cases"], duplicate_findings = find_duplicates(bodies_by_file)
    stats["findings"].extend(duplicate_findings)
    if symbols:
        stats["phantom_symbols"], phantom_findings = find_phantoms(imports_by_file, symbols)
        stats["findings"].extend(phantom_findings)

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
        coverage_pairs = [(test, source) for test, source in pairs
                          if Path(source).name in stats["coverage_by_file"]]
        lookup = {source: stats["coverage_by_file"][Path(source).name]
                  for _, source in coverage_pairs}
        stats["decorative_tests"], decorative_findings = find_decorative(coverage_pairs, lookup)
        stats["findings"].extend(decorative_findings)
    if stats["git"]:
        hotspots = find_hotspots(stats["git"]["file_commits"], source_paths,
                                 {source for _, source in pairs}, stats["coverage_by_file"])
        if hotspots:
            stats["hot_files"] = hotspots["hot_files"]
            stats["untested_hot_files"] = hotspots["untested_hot_files"]
            stats["hot_coverage"] = hotspots["hot_coverage"]
            stats["findings"].extend(hotspots["findings"])

    stats["suppressed_failures"] = sum(1 for f in stats["findings"]
                                       if f["kind"] == "suppressed-failure")
    order = {"phantom-symbol": 0, "suppressed-failure": 1, "untested-hotspot": 2,
             "mirror-assertion": 3, "conjoined-twin": 4, "decorative-test": 5,
             "implementation-access": 6, "brittle-selector": 7, "duplicate-case": 8,
             "stale-test": 9}
    stats["findings"].sort(key=lambda f: (order.get(f["kind"], 9), f["file"], f["line"]))
    return stats


# -------------------------------------------------------------------- score

# The twelve base dimensions add up to 100. "Mutation score" is scored only
# when a mutation report exists; when it does, every weight renormalises.
DIMENSIONS = [
    ("coverage", "Coverage", 12),
    ("mutation", "Mutation score", 8),
    ("unit", "Unit tests", 9),
    ("integration", "Integration tests", 7),
    ("e2e", "Functional / E2E", 6),
    ("pyramid", "Suite shape", 4),
    ("tdd", "TDD discipline", 7),
    ("assertions", "Assertion quality", 7),
    ("failure", "Edge & failure paths", 5),
    ("risk", "Risk targeting", 5),
    ("substance", "Test substance", 6),
    ("determinism", "Determinism & isolation", 6),
    ("focus", "Test focus", 5),
    ("naming", "Test naming", 5),
    ("doubles", "Test doubles", 6),
    ("hygiene", "Suite hygiene", 4),
    ("bdd", "BDD / behaviour specs", 2),
    ("ci", "CI enforcement", 4),
]
GRADES = [(85, "A"), (70, "B"), (55, "C"), (40, "D"), (0, "F")]


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def score_coverage(s):
    """0.25 for tooling, 0.20 for a gate, 0.55 for what is actually covered."""
    configured = bool(s["coverage_config"]) or s["ci_coverage"]
    threshold = s["coverage_threshold"]
    measured = s["coverage_measured"]
    gate = threshold is not None or (s["ci_coverage"] and s["ci_strict"])
    if not configured and measured is None:
        return 0.0, "no coverage tooling detected", \
            "wire up a coverage tool (pytest-cov, nyc, go -coverprofile, jacoco) and publish it"
    score = 0.25 + (0.20 if gate else 0.0)
    if measured is not None:
        score += 0.55 * clamp(measured / 85.0)
        detail = f"measured {measured}% ({s['coverage_source']})"
    elif threshold is not None:
        # A declared bar is worth less than a measured result.
        score += 0.55 * 0.6 * clamp(threshold / 85.0)
        detail = "declared only, no report committed"
    else:
        detail = "tooling present, no threshold, no report"
    if threshold is not None:
        detail += f", gate {threshold}%"
    if s["mutation_testing"]:
        score = clamp(score + 0.05)
        detail += ", mutation testing"
    advice = "raise measured line coverage towards 85% and fail the build under a threshold"
    if measured is None:
        advice = "publish a coverage report (lcov/cobertura/coverage.out) and gate CI on it"
    return clamp(score), detail, advice


def score_unit(s):
    source = s["source_files"]
    if source == 0:
        return None, "no source files found", ""
    files = s["kind_files"]["unit"]
    cases = s["kind_cases"]["unit"]
    # Files, cases and volume: a repo can have a test file per module and still
    # have written 20 lines of test against 2,000 lines of code.
    profile = s["profile"]
    ratio = (s["test_lines"] / s["source_lines"]) if s["source_lines"] else 0
    score = (0.4 * clamp((files / source) / 0.4)
             + 0.35 * clamp((cases / source) / profile["cases_per_source"])
             + 0.25 * clamp(ratio / profile["test_code_ratio"]))
    detail = f"{files} file(s), {cases} case(s) for {source} source files"
    if s["source_lines"]:
        detail += (f", {ratio:.2f}x test:code lines "
                   f"(target {profile['test_code_ratio']:.2f}x)")
    return score, detail, (f"add unit tests: ~1 test file per 2-3 source files, "
                           f"~{profile['cases_per_source']:.1f} cases per source file and "
                           f"~{profile['test_code_ratio']:.2f} lines of test per line of code "
                           f"for {'/'.join(profile['languages']) or 'this stack'}")


def score_layer(s, kind, target_share, label, advice):
    cases = s["kind_cases"][kind]
    files = s["kind_files"][kind]
    if not cases and not files:
        return 0.0, "none found", advice
    share = cases / max(s["cases"], 1)
    # Share of the suite, tempered by absolute size: one token test is not a layer.
    score = clamp(0.35 + 0.65 * clamp(share / target_share)) * (0.6 + 0.4 * clamp(cases / 5))
    detail = f"{files} file(s), {cases} case(s) ({share * 100:.0f}% of all cases)"
    return score, detail, f"grow the {label} layer — {advice}"


def score_tdd(s):
    git = s["git"]
    if not git:
        return None, "no git history available", ""
    source_commits = git["source_commits"]
    if source_commits < 5:
        return None, f"only {source_commits} source commit(s) — not enough signal", ""
    ratio = git["source_commits_with_tests"] / source_commits
    test_only = git["test_only_commits"] / max(git["commits_analysed"], 1)
    fixes = git["fix_commits"]
    fix_ratio = (git["fix_commits_with_tests"] / fixes) if fixes else None
    regression = clamp(fix_ratio / 0.8) if fix_ratio is not None else clamp(ratio / 0.6)
    score = 0.7 * clamp(ratio / 0.6) + 0.1 * clamp(test_only / 0.05) + 0.2 * regression
    detail = (f"{ratio * 100:.0f}% of {source_commits} source commits also touched tests "
              f"({git['test_only_commits']} test-only)")
    advice = ("ship tests in the same commit as the code they cover — "
              "aim for 60%+ of source commits touching tests")
    if fixes:
        detail += f", {git['fix_commits_with_tests']}/{fixes} bugfixes shipped a test"
        if fix_ratio < 0.5:
            advice = (f"{fixes - git['fix_commits_with_tests']} of {fixes} bugfix commits shipped "
                      "no test — a fix without a regression test is a bug free to come back")
    return clamp(score), detail, advice


def score_assertions(s):
    cases = s["cases"]
    if cases == 0:
        return 0.0, "no test cases detected", "write tests that assert something"
    density = s["assertions"] / cases
    silent = s["cases_without_assertions"] / cases
    weak_only = s["weak_only_cases"] / cases
    # A case that asserts nothing cannot fail for the right reason, and one that
    # only asserts truthy/not-null barely can; density matters least (a single
    # focused assertion per case is fine).
    effective = clamp(1 - silent - 0.6 * weak_only)
    score = 0.25 * clamp(density / 2.0) + 0.75 * effective
    uninformative = 0
    if s["profile"]["bare_assert_check"] and s["uninformative_assertions"]:
        # Frameworks that print the compared values make this a non-issue; the
        # rest leave you with "expected true, got false".
        uninformative = s["uninformative_assertions"] / cases
        score = clamp(score - 0.25 * clamp(uninformative / 0.20))
    detail = f"{density:.1f} assertions/case"
    if s["cases_without_assertions"]:
        detail += f", {s['cases_without_assertions']} case(s) assert nothing"
    if s["weak_only_cases"]:
        detail += f", {s['weak_only_cases']} assert only truthy/not-null/snapshot"
    if uninformative:
        detail += f", {s['uninformative_assertions']} report no values on failure"
    if not s["cases_without_assertions"] and not s["weak_only_cases"] and not uninformative:
        detail += ", every case asserts a value"
    if silent >= weak_only:
        advice = ("assert on behaviour: tests that only exercise code without asserting "
                  "cannot fail for the right reason")
    else:
        advice = (f"{s['weak_only_cases']} case(s) only assert truthiness or not-null — "
                  "assert the value you expect, so a wrong value fails the test")
    if uninformative > max(silent, weak_only):
        advice = (f"{s['uninformative_assertions']} assertion(s) print nothing useful when they "
                  "fail — compare values, or pass a message saying what was expected")
    return score, detail, advice


def score_failure_paths(s):
    """Regressions escape through the error paths and the boundaries."""
    cases = s["cases"]
    if cases == 0:
        return None, "no test cases detected", ""
    error_share = s["error_cases"] / cases
    boundary_share = s["boundary_cases"] / cases
    score = 0.75 * clamp(error_share / 0.25) + 0.25 * clamp(boundary_share / 0.20)
    detail = (f"{s['error_cases']}/{cases} cases ({error_share * 100:.0f}%) exercise a failure "
              f"path, {s['boundary_cases']} ({boundary_share * 100:.0f}%) touch a boundary value")
    if error_share <= boundary_share:
        advice = ("test what happens when things go wrong: invalid input, timeouts, denied "
                  "permissions, missing records — aim for ~25% of cases")
    else:
        advice = ("test the boundaries as well as the middle: empty, zero, negative, null, "
                  "maximum — that is where the off-by-ones live")
    return score, detail, advice


def score_mutation(s):
    """The only direct evidence that the suite kills bugs — scored when present."""
    measured = s["mutation_measured"]
    if measured is None:
        return None, "no mutation report found", ""
    score = clamp(measured / 80.0)
    detail = f"{measured}% of mutants killed ({s['mutation_source']})"
    return score, detail, ("survived mutants are code paths a bug could change without any "
                           "test noticing — kill them or delete the code")


def score_pyramid(s):
    """The test pyramid's shape: unit-only, integration-only and ice-cream cone."""
    unit = s["kind_cases"]["unit"]
    integration = s["kind_cases"]["integration"] + s["kind_cases"]["contract"]
    e2e = s["kind_cases"]["e2e"]
    total = unit + integration + e2e
    if total == 0:
        return None, "no classified test cases", ""
    unit_share, integration_share, e2e_share = (unit / total, integration / total, e2e / total)
    # Healthy: unit-heavy base, a real integration band, a thin E2E tip.
    unit_term = clamp(unit_share / 0.5)
    integration_term = clamp(integration_share / 0.15) if integration_share <= 0.35 else 1.0
    e2e_term = 1.0 if e2e_share <= 0.20 else clamp(1 - (e2e_share - 0.20) / 0.4)
    score = 0.4 * unit_term + 0.3 * integration_term + 0.3 * e2e_term
    if e2e_share > 0.4:
        shape = "ice-cream cone — E2E heavy"
    elif unit_share >= 0.5 and integration_share >= 0.1:
        shape = "healthy pyramid"
    elif integration_share < 0.05:
        shape = "unit tests without integration tests"
    elif unit_share < 0.3:
        shape = "integration tests without a unit base"
    else:
        shape = "lopsided"
    detail = (f"{unit_share * 100:.0f}/{integration_share * 100:.0f}/{e2e_share * 100:.0f} "
              f"unit/integration/E2E — {shape}")
    return score, detail, ("rebalance towards a broad unit base, a real integration band and a "
                           "thin E2E tip — slow layers should be the smallest")


def score_determinism(s):
    """Flakiness and environment coupling: the Butterfly, the Local Hero, Chain Gang."""
    cases = s["cases"]
    if cases == 0:
        return None, "no test cases detected", ""
    penalties = []
    for count, share, label, weight in (
            (s["unfrozen_time"], 0.10, "unfrozen clock reads", 0.30),
            (s["unseeded_random"], 0.10, "unseeded randomness", 0.20),
            (s["env_coupling"], 0.05, "host/path/URL coupling", 0.25),
            (s["order_dependent"], 0.05, "order-dependent or shared state", 0.15),
            (s["sleeps"], 0.10, "hard-coded sleeps", 0.20),
            (s["brittle_selectors"], 0.10, "brittle locators", 0.20),
            (s["platform_branches"], 0.05, "platform-specific branches", 0.15)):
        if count:
            penalties.append((f"{count} {label}", weight * clamp((count / cases) / share)))
    if s["serial_only"]:
        penalties.append(("pinned to a single worker", 0.15))
    score = clamp(1 - sum(p for _, p in penalties))
    if penalties:
        detail = ", ".join(label for label, _ in penalties)
        advice = ("freeze the clock, seed the randomness, inject hosts and paths, and let cases "
                  "run in any order — these are the tests that fail on someone else's machine")
    else:
        detail = "no clock, randomness, host or ordering dependencies"
        advice = "keep tests deterministic and independently runnable"
    return score, detail, advice


def score_focus(s):
    """One case, one behaviour: the Giant, the Eager Test, Assertion Roulette."""
    cases = s["cases"]
    if cases == 0:
        return None, "no test cases detected", ""
    penalties = []
    if s["giant_cases"]:
        penalties.append((f"{s['giant_cases']} case(s) over 50 lines",
                          0.35 * clamp((s["giant_cases"] / cases) / 0.10)))
    if s["branching_cases"]:
        penalties.append((f"{s['branching_cases']} case(s) with if/switch logic",
                          0.30 * clamp((s["branching_cases"] / cases) / 0.10)))
    if s["roulette_cases"]:
        penalties.append((f"{s['roulette_cases']} case(s) with 10+ assertions",
                          0.25 * clamp((s["roulette_cases"] / cases) / 0.10)))
    if s["setup_lines"] > 30:
        penalties.append((f"{s['setup_lines']}-line setup block",
                          0.10 * clamp((s["setup_lines"] - 30) / 50)))
    score = clamp(1 - sum(p for _, p in penalties))
    detail = ", ".join(label for label, _ in penalties) or "cases are small, linear and focused"
    return score, detail, ("split giant cases and drop branching: a test with an `if` does not "
                           "test one thing, and half of it may never run")


def score_risk(s):
    """Are the files that change most often the ones under test?"""
    if not s["hot_files"]:
        return None, "no churn history to rank by", ""
    hot = s["hot_files"]
    tested = hot - s["untested_hot_files"]
    score = 0.6 * (tested / hot) if s["hot_coverage"] is not None else tested / hot
    detail = f"{tested}/{hot} of the most-changed files have tests"
    if s["hot_coverage"] is not None:
        score += 0.4 * clamp(s["hot_coverage"] / 85.0)
        detail += f", {s['hot_coverage']}% covered"
    advice = ("test the code that changes most: churn is the best available proxy for where "
              "the next bug will be")
    return clamp(score), detail, advice


def score_substance(s):
    """Is there a real test behind each case, or just something shaped like one?"""
    cases = s["cases"]
    if cases == 0:
        return None, "no test cases detected", ""
    paired = max(s["paired_tests"], 1)
    penalties = []
    if s["duplicate_cases"]:
        penalties.append((
            f"{s['duplicate_cases']} duplicate case(s)",
            0.30 * clamp((s["duplicate_cases"] / cases) / 0.25),
            (f"{s['duplicate_cases']} case(s) are copies of another case with different "
             "literals — parametrise them and spend the time on an untested path")))
    if s["suppressed_failures"]:
        penalties.append((
            f"{s['suppressed_failures']} suppressed failure(s)",
            0.25 * clamp((s["suppressed_failures"] / cases) / 0.05),
            (f"{s['suppressed_failures']} assertion(s) cannot fail: commented out, swallowed "
             "by an empty except/catch, or skipped with no reason")))
    if s["phantom_symbols"]:
        penalties.append((
            f"{s['phantom_symbols']} phantom symbol(s)",
            0.20 * clamp(s["phantom_symbols"] / 3),
            (f"{s['phantom_symbols']} test import(s) name code no source file defines — "
             "those tests never ran against this repo")))
    if s["private_access"]:
        penalties.append((
            f"{s['private_access']} private-member access(es)",
            0.15 * clamp((s["private_access"] / cases) / 0.10),
            (f"{s['private_access']} case(s) reach into internals — assert on what the unit "
             "does, or the next refactor breaks the test without breaking the code")))
    if s["mirror_assertions"]:
        penalties.append((
            f"{s['mirror_assertions']} mirrored expectation(s)",
            0.15 * clamp((s["mirror_assertions"] / cases) / 0.10),
            (f"{s['mirror_assertions']} assertion(s) recompute the expected value from the "
             "inputs — write the answer down as a literal so a wrong formula fails")))
    if s["conjoined_files"]:
        penalties.append((
            f"{s['conjoined_files']} unit test(s) doing real I/O",
            0.15 * clamp(s["conjoined_files"] / 5),
            (f"{s['conjoined_files']} file(s) filed as unit tests talk to a real database, "
             "HTTP service or browser — move them to the integration suite so the fast "
             "suite stays fast and honest")))
    if s["stale_tests"]:
        penalties.append((
            f"{s['stale_tests']} stale test file(s)",
            0.15 * clamp((s["stale_tests"] / paired) / 0.3),
            (f"{s['stale_tests']} test file(s) never changed while the code they cover kept "
             "churning — they no longer describe it")))
    if s["decorative_tests"]:
        penalties.append((
            f"{s['decorative_tests']} decorative test file(s)",
            0.10 * clamp((s["decorative_tests"] / paired) / 0.3),
            (f"{s['decorative_tests']} module(s) have a test file and almost no coverage — "
             "the test exercises nearly nothing")))
    score = clamp(1 - sum(p for _, p, _ in penalties))
    if penalties:
        detail = ", ".join(label for label, _, _ in penalties)
        advice = max(penalties, key=lambda p: p[1])[2]
    else:
        detail = "no duplicate, suppressed, phantom or stale tests found"
        advice = "keep cases distinct and let every assertion be able to fail"
    return score, detail, advice


def score_naming(s):
    """Do the names say what behaviour is expected, or just that a thing exists?"""
    total = s["test_names"]
    if not total:
        return None, "no test names could be extracted", ""
    descriptive = s["descriptive_names"] / total
    conditional = s["conditional_names"] / total
    placeholder = s["placeholder_names"] / total
    average_words = s["name_words"] / total
    mirrored = s["method_mirror_names"] / total
    score = clamp(0.6 * clamp(descriptive / 0.9) + 0.4 * clamp(conditional / 0.5)
                  - 0.3 * placeholder - 0.2 * clamp(mirrored / 0.5))
    detail = (f"{average_words:.1f} words/name, {descriptive * 100:.0f}% describe behaviour, "
              f"{conditional * 100:.0f}% state a condition")
    if s["placeholder_names"]:
        detail += f", {s['placeholder_names']} placeholder"
    if s["method_mirror_names"]:
        detail += f", {s['method_mirror_names']} named after a method"
    advice = ('name the behaviour, not the subject: '
              '"<unit> <expected result> when <condition>"')
    if mirrored > 0.3:
        advice = (f"{s['method_mirror_names']} test(s) are named after the method they call — "
                  "one test per method mirrors the code instead of describing what it should do")
    samples = [n for n in s["bad_names"] if n][:3]
    if samples:
        advice += " — start with " + ", ".join(samples)
    return score, detail, advice


def score_doubles(s):
    """Are mocks, stubs and spies used at real seams, or is the suite testing itself?"""
    cases = s["cases"]
    if cases == 0:
        return None, "no test cases detected", ""
    doubles = s["doubles"]
    if doubles == 0:
        return 0.9, "no test doubles — nothing is faked", \
            "double only the slow or nondeterministic seams (clock, network, payments)"
    with_doubles = s["cases_with_doubles"]
    tautological = s["mock_only_cases"] / max(with_doubles, 1)
    density = doubles / max(with_doubles, 1)
    saturation = with_doubles / cases
    penalty = (0.45 * tautological                      # asserts only that a mock was called
               + 0.25 * clamp((density - 3) / 5)        # a case wiring 5+ doubles tests wiring
               + 0.20 * clamp((saturation - 0.6) / 0.4))  # almost nothing real left to break
    if not s["double_cleanup"]:
        penalty += 0.10
    unmocked_layer = s["kind_cases"]["integration"] + s["kind_cases"]["e2e"]
    if not unmocked_layer:
        # Nothing anywhere exercises the real collaborator the doubles stand in for.
        penalty += 0.15
    score = clamp(1 - penalty)
    kinds = "/".join(sorted(s["double_kinds"]))
    if with_doubles:
        detail = f"{doubles} double(s) in {with_doubles}/{cases} cases ({kinds})"
    else:
        detail = f"{doubles} double(s), all in fixtures/setup ({kinds})"
    if s["mock_only_cases"]:
        detail += f", {s['mock_only_cases']} assert only on the double"
    if not s["double_cleanup"]:
        detail += ", no reset/restore"
    if s["mock_only_cases"]:
        advice = (f"{s['mock_only_cases']} case(s) only verify that a double was called — "
                  "assert on the returned value or the resulting state instead")
    elif density > 3:
        advice = ("trim doubles back to real seams; a case wiring several doubles mostly "
                  "tests its own wiring")
    elif not s["double_cleanup"]:
        advice = "reset or restore doubles between cases so state cannot leak"
    elif not unmocked_layer:
        advice = ("every collaborator is doubled and no integration test exercises the real "
                  "one — the bugs live in that interaction, and nothing here would see them")
    else:
        advice = "keep doubles at the edges and let the rest of the suite run real code"
    return score, detail, advice


def score_hygiene(s):
    cases = s["cases"]
    if cases == 0:
        return 0.0, "no test cases detected", "write some tests first"
    penalties = []
    skip_ratio = s["skips"] / cases
    if skip_ratio:
        penalties.append(("skipped/xfailed tests", 0.4 * clamp(skip_ratio / 0.10)))
    if s["focused"]:
        penalties.append((".only/fdescribe focus left in", 0.30))
    if s["chatter"]:
        penalties.append(("console chatter instead of assertions",
                          0.15 * clamp((s["chatter"] / cases) / 0.20)))
    if cases > 20 and not s["flag_files"]["parametrized"]:
        penalties.append(("no parametrised/table-driven tests", 0.10))
    score = clamp(1.0 - sum(p for _, p in penalties))
    if penalties:
        detail = ", ".join(f"{name} (-{value * 100:.0f}%)" for name, value in penalties)
    else:
        detail = f"{cases} cases, no skips, no focused tests"
    return score, detail, ("un-skip or delete dead tests, drop .only, and table-drive "
                           "repetitive cases")


def score_bdd(s):
    total = max(s["cases"], 1)
    scenarios = s["bdd_cases"]
    features = s["feature_files"]
    spec_style = s["spec_cases"]
    if not scenarios and not features and not spec_style:
        return 0.0, "no behaviour specs found", \
            "describe behaviour in the domain's language (Gherkin features, or spec-style tests)"
    if scenarios or features:
        score = clamp(0.6 + 0.4 * clamp((scenarios / total) / 0.05))
        detail = f"{features} feature file(s), {scenarios} Gherkin-style case(s)"
        advice = "cover more critical behaviour with executable specs"
    else:
        # describe/it is a weak BDD signal in most stacks, but it *is* the
        # ecosystem's own idiom in RSpec/Jasmine-style suites.
        ceiling = 0.8 if s["profile"]["spec_style_idiomatic"] else 0.55
        score = clamp(ceiling * clamp((spec_style / total) / 0.30))
        detail = f"spec-style only ({spec_style} describe/it case(s)), no Gherkin"
        advice = ("write the critical journeys as Given/When/Then specs the business can read "
                  "(cucumber, behave, pytest-bdd, godog)")
    return score, detail, advice


def score_ci(s):
    if not s["ci_files"]:
        return 0.0, "no CI configuration found", "run the suite on every push/PR"
    score = 0.0
    bits = []
    if s["ci_runs_tests"]:
        score += 0.6
        bits.append("runs tests")
    if s["ci_coverage"]:
        score += 0.25
        bits.append("collects coverage")
    if s["ci_strict"]:
        score += 0.15
        bits.append("matrix/strict flags")
    detail = f"{len(s['ci_files'])} config(s): " + (", ".join(bits) or "no test invocation found")
    return clamp(score), detail, "make CI run the suite, collect coverage and fail on regressions"


SCORERS = {
    "coverage": score_coverage,
    "unit": score_unit,
    "integration": lambda s: score_layer(
        s, "integration", 0.12, "integration",
        "test real collaborators (db, queue, http) rather than mocks only"),
    "e2e": lambda s: score_layer(
        s, "e2e", 0.07, "functional/E2E",
        "cover the critical user journeys end to end"),
    "tdd": score_tdd,
    "assertions": score_assertions,
    "failure": score_failure_paths,
    "risk": score_risk,
    "pyramid": score_pyramid,
    "determinism": score_determinism,
    "focus": score_focus,
    "substance": score_substance,
    "mutation": score_mutation,
    "naming": score_naming,
    "doubles": score_doubles,
    "hygiene": score_hygiene,
    "bdd": score_bdd,
    "ci": score_ci,
}


def grade_for(score):
    for floor, letter in GRADES:
        if score >= floor:
            return letter
    return "F"


def evaluate(stats):
    results = []
    weighted = 0.0
    total_weight = 0.0
    for key, title, weight in DIMENSIONS:
        score, detail, advice = SCORERS[key](stats)
        entry = {"id": key, "title": title, "weight": weight, "score": score,
                 "detail": detail, "advice": advice}
        if score is None:
            entry["points"] = None
            entry["lost"] = 0.0
        else:
            entry["points"] = round(score * weight, 1)
            entry["lost"] = round((1 - score) * weight, 1)
            weighted += score * weight
            total_weight += weight
        results.append(entry)
    total = round(weighted / total_weight * 100, 1) if total_weight else 0.0
    skipped = [r["title"] for r in results if r["score"] is None]
    return {
        "version": VERSION,
        "root": stats["root"],
        "score": total,
        "grade": grade_for(total),
        "scored_weight": total_weight,
        "not_scored": skipped,
        "dimensions": results,
        "findings": stats["findings"],
        "stats": {
            "source_files": stats["source_files"],
            "test_files": stats["test_files"],
            "test_cases": stats["cases"],
            "assertions": stats["assertions"],
            "cases_without_assertions": stats["cases_without_assertions"],
            "skipped_markers": stats["skips"],
            "focused_markers": stats["focused"],
            "sleeps": stats["sleeps"],
            "duplicate_cases": stats["duplicate_cases"],
            "suppressed_failures": stats["suppressed_failures"],
            "phantom_symbols": stats["phantom_symbols"],
            "stale_tests": stats["stale_tests"],
            "decorative_tests": stats["decorative_tests"],
            "paired_tests": stats["paired_tests"],
            "weak_assertions": stats["weak_assertions"],
            "weak_only_cases": stats["weak_only_cases"],
            "error_cases": stats["error_cases"],
            "boundary_cases": stats["boundary_cases"],
            "serial_only": stats["serial_only"],
            "profile": stats["profile"],
            "language_lines": dict(stats["language_lines"].most_common()),
            "uninformative_assertions": stats["uninformative_assertions"],
            "source_lines": stats["source_lines"],
            "test_lines": stats["test_lines"],
            "test_to_code_ratio": (round(stats["test_lines"] / stats["source_lines"], 2)
                                   if stats["source_lines"] else None),
            "method_mirror_names": stats["method_mirror_names"],
            "hot_files": stats["hot_files"],
            "untested_hot_files": stats["untested_hot_files"],
            "hot_coverage": stats["hot_coverage"],
            "conjoined_files": stats["conjoined_files"],
            "chatter": stats["chatter"],
            "platform_branches": stats["platform_branches"],
            "mirror_assertions": stats["mirror_assertions"],
            "brittle_selectors": stats["brittle_selectors"],
            "private_access": stats["private_access"],
            "giant_cases": stats["giant_cases"],
            "roulette_cases": stats["roulette_cases"],
            "branching_cases": stats["branching_cases"],
            "setup_lines": stats["setup_lines"],
            "unfrozen_time": stats["unfrozen_time"],
            "unseeded_random": stats["unseeded_random"],
            "env_coupling": stats["env_coupling"],
            "order_dependent": stats["order_dependent"],
            "mutation_measured": stats["mutation_measured"],
            "mutation_source": stats["mutation_source"],
            "doubles": stats["doubles"],
            "cases_with_doubles": stats["cases_with_doubles"],
            "mock_only_cases": stats["mock_only_cases"],
            "double_kinds": sorted(stats["double_kinds"]),
            "double_cleanup": stats["double_cleanup"],
            "test_names": stats["test_names"],
            "descriptive_names": stats["descriptive_names"],
            "conditional_names": stats["conditional_names"],
            "placeholder_names": stats["placeholder_names"],
            "worst_names": stats["bad_names"][:10],
            "feature_files": stats["feature_files"],
            "gherkin_cases": stats["bdd_cases"],
            "spec_style_cases": stats["spec_cases"],
            "languages": dict(stats["languages"].most_common()),
            "test_languages": dict(stats["test_languages"].most_common()),
            "kind_files": dict(stats["kind_files"]),
            "kind_cases": dict(stats["kind_cases"]),
            "flag_files": dict(stats["flag_files"]),
            "coverage_measured": stats["coverage_measured"],
            "coverage_threshold": stats["coverage_threshold"],
            "coverage_source": stats["coverage_source"],
            "coverage_config": stats["coverage_config"],
            "ci_files": stats["ci_files"],
            "mutation_testing": stats["mutation_testing"],
            "git": stats["git"],
        },
    }


def compare(report, baseline):
    """Attach per-dimension and total deltas against a previous JSON report."""
    if not isinstance(baseline, dict) or "score" not in baseline:
        raise ValueError("baseline is not a gradebook-tests JSON report")
    previous = {d["id"]: d for d in baseline.get("dimensions", []) if isinstance(d, dict)}
    deltas = {}
    for dim in report["dimensions"]:
        was = previous.get(dim["id"], {}).get("points")
        now = dim["points"]
        dim["delta"] = round(now - was, 1) if was is not None and now is not None else None
        deltas[dim["id"]] = dim["delta"]
    comparable = sorted(baseline.get("not_scored", [])) == sorted(report["not_scored"])
    report["baseline"] = {
        "score": baseline["score"],
        "delta": round(report["score"] - baseline["score"], 1),
        "dimensions": deltas,
        "comparable": comparable,
    }
    return report


def score_directories(root: Path, use_git=True):
    """Score each immediate subdirectory that holds code of its own."""
    results = []
    for child in sorted(p for p in root.iterdir() if p.is_dir()):
        if child.name in SKIP_DIRS or child.name in ARTIFACT_DIRS:
            continue
        stats = collect(child, use_git=use_git)
        if not stats["source_files"] and not stats["test_files"]:
            continue
        report = evaluate(stats)
        top = recommendations(report, 1)
        results.append({
            "path": child.name,
            "score": report["score"],
            "grade": report["grade"],
            "source_files": stats["source_files"],
            "test_files": stats["test_files"],
            "test_cases": stats["cases"],
            "top_win": top[0]["advice"] if top else "",
            "top_win_points": top[0]["lost"] if top else 0.0,
        })
    return sorted(results, key=lambda r: r["score"])


def recommendations(report, top=5):
    ranked = [d for d in report["dimensions"] if d["score"] is not None and d["lost"] >= 0.5]
    ranked.sort(key=lambda d: d["lost"], reverse=True)
    return ranked[:top]


# ------------------------------------------------------------------- render

def bar(score, width=20):
    if score is None:
        return "·" * width
    filled = round(score * width)
    return "█" * filled + "░" * (width - filled)


def render_text(report, top=5, max_flags=10):
    stats = report["stats"]
    out = [f"gradebook-tests {VERSION} — {report['root']}"]
    langs = ", ".join(f"{k} ({v})" for k, v in list(stats["languages"].items())[:5]) or "none"
    profile = stats.get("profile") or {}
    if profile.get("languages"):
        langs += (f"  ·  calibrated for {'/'.join(profile['languages'])}: "
                  f"{profile['test_code_ratio']:.2f}x test:code, "
                  f"{profile['cases_per_source']:.1f} cases/file")
    out.append(f"languages: {langs}")
    volume = ""
    if stats.get("test_to_code_ratio") is not None:
        volume = (f" · {stats['test_lines']:,} test lines / {stats['source_lines']:,} source "
                  f"lines ({stats['test_to_code_ratio']:.2f}x)")
    out.append(f"{stats['source_files']} source files · {stats['test_files']} test files · "
               f"{stats['test_cases']} test cases · {stats['assertions']} assertions{volume}")
    out.append("")
    show_delta = "baseline" in report
    for dim in report["dimensions"]:
        if dim["score"] is None:
            points = "  n/a "
        else:
            points = f"{dim['points']:5.1f}"
        delta = ""
        if show_delta:
            value = dim.get("delta")
            delta = f"{value:+5.1f} " if value else ("      " if value is None else "    · ")
        out.append(f"  {dim['title']:<22} {bar(dim['score'])} {points}/{dim['weight']:<3.0f} "
                   f"{delta}{dim['detail']}")
    out.append("")
    headline = f"SCORE  {report['score']:.1f}/100   grade {report['grade']}"
    if show_delta:
        headline += (f"   {report['baseline']['delta']:+.1f} vs baseline "
                     f"({report['baseline']['score']:.1f})")
    out.append(headline)
    if show_delta and not report["baseline"]["comparable"]:
        out.append("note: the baseline scored a different set of dimensions — "
                   "the total is not directly comparable")
    if report["not_scored"]:
        out.append(f"not scored (weights redistributed): {', '.join(report['not_scored'])}")
    wins = recommendations(report, top)
    if wins:
        out.append("")
        out.append("Biggest wins:")
        for dim in wins:
            out.append(f"  +{dim['lost']:<5.1f} {dim['title']} — {dim['advice']}")
    out.extend(render_flags(report.get("findings"), max_flags))
    out.extend(render_directories(report.get("directories")))
    return "\n".join(out)


def location(finding):
    return f"{finding['file']}:{finding['line']}" if finding["line"] else finding["file"]


def render_flags(findings, limit):
    if not findings or limit <= 0:
        return []
    shown = findings[:limit]
    width = max(len(location(f)) for f in shown)
    out = ["", f"Red flags ({len(findings)}):"]
    for finding in shown:
        out.append(f"  {location(finding):<{width}}  {finding['kind']:<18} {finding['message']}")
    if len(findings) > limit:
        out.append(f"  … {len(findings) - limit} more (see --format json)")
    return out


def render_directories(directories):
    if not directories:
        return []
    width = max(len(d["path"]) for d in directories)
    out = ["", "By directory (worst first):"]
    for entry in directories:
        counts = f"{entry['source_files']} src / {entry['test_files']} test"
        out.append(f"  {entry['grade']}  {entry['score']:5.1f}  {entry['path']:<{width}}  "
                   f"{counts:<20} → {entry['top_win']}")
    return out


def render_markdown(report, top=5, max_flags=10):
    stats = report["stats"]
    out = [f"## Test suite score: **{report['score']:.1f}/100** (grade {report['grade']})", ""]
    out.append(f"`{report['root']}` — {stats['source_files']} source files, "
               f"{stats['test_files']} test files, {stats['test_cases']} test cases, "
               f"{stats['assertions']} assertions")
    out.append("")
    show_delta = "baseline" in report
    if show_delta:
        out.append(f"Baseline: **{report['baseline']['score']:.1f}** "
                   f"({report['baseline']['delta']:+.1f})"
                   + ("" if report["baseline"]["comparable"]
                      else " — baseline scored a different set of dimensions"))
        out.append("")
        out.append("| Dimension | Score | Δ | Weight | Detail |")
        out.append("|---|---:|---:|---:|---|")
    else:
        out.append("| Dimension | Score | Weight | Detail |")
        out.append("|---|---:|---:|---|")
    for dim in report["dimensions"]:
        points = "n/a" if dim["score"] is None else f"{dim['points']:.1f}"
        delta = ""
        if show_delta:
            value = dim.get("delta")
            delta = f" {value:+.1f} |" if value else (" |" if value is None else " · |")
        out.append(f"| {dim['title']} | {points} |{delta} {dim['weight']:.0f} | {dim['detail']} |")
    if report["not_scored"]:
        out.append("")
        out.append(f"_Not scored (weights redistributed): {', '.join(report['not_scored'])}._")
    wins = recommendations(report, top)
    if wins:
        out.append("")
        out.append("### Biggest wins")
        for dim in wins:
            out.append(f"- **+{dim['lost']:.1f} {dim['title']}** — {dim['advice']}")
    findings = report.get("findings") or []
    if findings and max_flags > 0:
        out.append("")
        out.append(f"### Red flags ({len(findings)})")
        for finding in findings[:max_flags]:
            out.append(f"- `{location(finding)}` **{finding['kind']}** — {finding['message']}")
        if len(findings) > max_flags:
            out.append(f"- … {len(findings) - max_flags} more")
    if report.get("directories"):
        out.append("")
        out.append("### By directory")
        out.append("| Directory | Score | Grade | Tests | Biggest win |")
        out.append("|---|---:|---|---:|---|")
        for entry in report["directories"]:
            out.append(f"| `{entry['path']}` | {entry['score']:.1f} | {entry['grade']} | "
                       f"{entry['test_files']} file(s) | {entry['top_win']} |")
    return "\n".join(out)


# ---------------------------------------------------------------------- cli

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="gradebook-tests", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", default=".", help="repository to evaluate")
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    parser.add_argument("--fail-under", type=float, metavar="N",
                        help="exit 1 when the score is below N (CI gate)")
    parser.add_argument("--baseline", metavar="FILE",
                        help="a previous --format json report to diff against")
    parser.add_argument("--fail-on-drop", type=float, nargs="?", const=0.0, metavar="N",
                        help="with --baseline, exit 1 when the score drops by more than N "
                             "(default 0)")
    parser.add_argument("--max-flags", type=int, default=10, metavar="N",
                        help="how many red flags to list (default 10, 0 to hide)")
    parser.add_argument("--by-dir", action="store_true",
                        help="also score each immediate subdirectory that holds code")
    parser.add_argument("--no-git", action="store_true",
                        help="skip the git-history TDD analysis")
    parser.add_argument("--top", type=int, default=5, metavar="N",
                        help="how many recommendations to show (default 5)")
    parser.add_argument("--list-dimensions", action="store_true",
                        help="print the scoring model and exit")
    parser.add_argument("--version", action="version", version=f"gradebook-tests {VERSION}")
    args = parser.parse_args(argv)

    if args.list_dimensions:
        for key, title, weight in DIMENSIONS:
            note = "  (only when a mutation report exists)" if key == "mutation" else ""
            print(f"{key:<12} {weight:>3} pts  {title}{note}")
        print("\nThe always-scored dimensions total 100; any dimension that cannot be "
              "judged is\nleft unscored and the remaining weights renormalise.")
        return 0

    root = Path(args.path)
    if not root.is_dir():
        print(f"gradebook-tests: not a directory: {root}", file=sys.stderr)
        return 2

    if args.fail_on_drop is not None and not args.baseline:
        print("gradebook-tests: --fail-on-drop needs --baseline", file=sys.stderr)
        return 2

    stats = collect(root, use_git=not args.no_git)
    report = evaluate(stats)
    report["recommendations"] = [
        {"dimension": d["id"], "points": d["lost"], "advice": d["advice"]}
        for d in recommendations(report, args.top)
    ]
    if args.by_dir:
        report["directories"] = score_directories(root, use_git=not args.no_git)
    if args.baseline:
        try:
            with open(args.baseline) as handle:
                compare(report, json.load(handle))
        except (OSError, ValueError) as error:
            print(f"gradebook-tests: cannot read baseline {args.baseline}: {error}", file=sys.stderr)
            return 2

    if args.format == "json":
        json.dump(report, sys.stdout, indent=2, sort_keys=False)
        print()
    elif args.format == "markdown":
        print(render_markdown(report, args.top, args.max_flags))
    else:
        print(render_text(report, args.top, args.max_flags))

    failed = False
    if args.fail_under is not None and report["score"] < args.fail_under:
        print(f"gradebook-tests: {report['score']:.1f} is below --fail-under {args.fail_under}",
              file=sys.stderr)
        failed = True
    if args.fail_on_drop is not None:
        drop = -report["baseline"]["delta"]
        if drop > args.fail_on_drop:
            print(f"gradebook-tests: dropped {drop:.1f} points against the baseline "
                  f"(tolerance {args.fail_on_drop})", file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
