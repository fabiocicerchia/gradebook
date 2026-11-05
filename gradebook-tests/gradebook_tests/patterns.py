"""The patterns that recognise what is inside a test file: case and assertion
syntax per language, smells, doubles, and the word lists that judge a test
name. Data only — the code that applies them lives in detection."""

import re

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

# The idioms a file can be written in, each recognised by one pattern.
STYLE_FLAGS = [
    (GHERKIN_RE, "bdd"),
    (SPEC_STYLE_RE, "spec-style"),
    (PROPERTY_RE, "property"),
    (SNAPSHOT_RE, "snapshot"),
    (PARAM_RE, "parametrized"),
    (MOCK_RE, "mocked"),
]
