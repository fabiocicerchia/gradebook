"""The vocabulary the rest of the package is written in."""

from __future__ import annotations

import shutil
from typing import Any

VERSION = "0.3.0"  # x-release-please-version

# The shapes this module passes around. All JSON-shaped: the report is written
# out as JSON and read back by the extension and by --baseline, so nothing here
# is richer than what survives that round trip.
Stats = dict[str, Any]
Report = dict[str, Any]
Finding = dict[str, Any]
FileInfo = dict[str, Any]
Profile = dict[str, Any]

# The defaults the analysis runs with. Each is a judgement about what is worth
# reporting rather than an arbitrary number.
CONDITION_WINDOW = 400  # past this, the branch found belongs to another case
HISTORY_LIMIT = 400  # commits read for the churn and TDD signals
LIST_LIMIT = 20  # as many findings of one kind as anyone acts on
MIN_CLUSTER = 3  # three identical bodies is a pattern, two a coincidence
MIN_CHANGES = 5  # a file touched fewer times says nothing about staleness
DECORATIVE_COVERAGE = 40.0  # a test file whose source is barely covered
TOP_RECOMMENDATIONS = 5
BAR_WIDTH = 20
# Resolved once: `git` on PATH, or nothing to ask about history.
_GIT = shutil.which("git") or "git"

# What the rubric judges by. Each is a claim about test quality, so each is
# named rather than sitting as a number in the middle of a condition.
MIN_MEANINGFUL_WORDS = 3  # a name of three real words describes something
MIN_WORDS_WITH_CONTEXT = 2  # two, if one of them says what the behaviour is
MOSTLY = 0.5  # "most of the suite does this"
LONG_CASE_LINES = 20  # past this the case is doing more than one thing
GIANT_CASE_LINES = 50
MANY_ASSERTIONS = 10
PERCENT_MAX = 100.0
FRACTION_AS_PERCENT = 10.0  # below this, a "percentage" is really a fraction
MIN_CHURN_FILES = 3  # fewer, and there is no ranking to make
MAX_NAME_WORDS_FOR_MIRROR = 2  # `test_parse` mirrors `parse`, and says no more
MIN_SOURCE_COMMITS_FOR_TDD = 5
FIX_COMMIT_SHARE = 0.5  # more fixes than features is a suite arriving late
INTEGRATION_TARGET = 0.15
INTEGRATION_CEILING = 0.35
E2E_TARGET = 0.20
E2E_TOLERANCE = 0.4
E2E_CEILING = 0.4
UNIT_FLOOR = 0.5
INTEGRATION_FLOOR = 0.1
INTEGRATION_SPARSE = 0.05
UNIT_SPARSE = 0.3
HEAVY_SETUP_LINES = 30
MIRRORED_NAME_SHARE = 0.3  # a third of the names just echo the function
BUSY_DOUBLE_DENSITY = 3  # three doubles per case is a test about mocks
MANY_CASES = 20  # past this, unparametrized repetition shows
MIN_POINTS_LOST_TO_RECOMMEND = 0.5
HIGH_SEVERITY_RANK = 2
MEDIUM_SEVERITY_RANK = 6
MAX_FILE_BYTES = 512 * 1024

# Directories never worth walking into.
SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "bower_components",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".tox",
    ".nox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".gradle",
    ".idea",
    ".vscode",
    ".next",
    ".nuxt",
    ".terraform",
    "vendor",
    "third_party",
    "site-packages",
    ".cache",
    ".yarn",
    "Pods",
}
# Walked (coverage artifacts live here) but excluded from source/test counting.
ARTIFACT_DIRS = {
    "coverage",
    "htmlcov",
    "build",
    "dist",
    "target",
    "out",
    "obj",
    "reports",
    ".nyc_output",
    "coverage-reports",
    "test-results",
    "allure-results",
}

LANG_BY_EXT = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".kt": "kotlin",
    ".rb": "ruby",
    ".php": "php",
    ".rs": "rust",
    ".cs": "csharp",
    ".ex": "elixir",
    ".exs": "elixir",
    ".scala": "scala",
    ".swift": "swift",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".lua": "lua",
    ".sh": "shell",
    ".bash": "shell",
}
JS_EXT = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
TEST_DIR_NAMES = {"test", "tests", "spec", "specs", "__tests__", "testing", "e2e", "features"}

