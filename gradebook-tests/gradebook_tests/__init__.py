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

from .base import ARTIFACT_DIRS as ARTIFACT_DIRS
from .base import BAR_WIDTH as BAR_WIDTH
from .base import BUSY_DOUBLE_DENSITY as BUSY_DOUBLE_DENSITY
from .base import CONDITION_WINDOW as CONDITION_WINDOW
from .base import DECORATIVE_COVERAGE as DECORATIVE_COVERAGE
from .base import E2E_CEILING as E2E_CEILING
from .base import E2E_TARGET as E2E_TARGET
from .base import E2E_TOLERANCE as E2E_TOLERANCE
from .base import FIX_COMMIT_SHARE as FIX_COMMIT_SHARE
from .base import FRACTION_AS_PERCENT as FRACTION_AS_PERCENT
from .base import GIANT_CASE_LINES as GIANT_CASE_LINES
from .base import HEAVY_SETUP_LINES as HEAVY_SETUP_LINES
from .base import HIGH_SEVERITY_RANK as HIGH_SEVERITY_RANK
from .base import HISTORY_LIMIT as HISTORY_LIMIT
from .base import INTEGRATION_CEILING as INTEGRATION_CEILING
from .base import INTEGRATION_FLOOR as INTEGRATION_FLOOR
from .base import INTEGRATION_SPARSE as INTEGRATION_SPARSE
from .base import INTEGRATION_TARGET as INTEGRATION_TARGET
from .base import JS_EXT as JS_EXT
from .base import LANG_BY_EXT as LANG_BY_EXT
from .base import LIST_LIMIT as LIST_LIMIT
from .base import LONG_CASE_LINES as LONG_CASE_LINES
from .base import MANY_ASSERTIONS as MANY_ASSERTIONS
from .base import MANY_CASES as MANY_CASES
from .base import MAX_FILE_BYTES as MAX_FILE_BYTES
from .base import MAX_NAME_WORDS_FOR_MIRROR as MAX_NAME_WORDS_FOR_MIRROR
from .base import MEDIUM_SEVERITY_RANK as MEDIUM_SEVERITY_RANK
from .base import MIN_CHANGES as MIN_CHANGES
from .base import MIN_CHURN_FILES as MIN_CHURN_FILES
from .base import MIN_CLUSTER as MIN_CLUSTER
from .base import MIN_MEANINGFUL_WORDS as MIN_MEANINGFUL_WORDS
from .base import MIN_POINTS_LOST_TO_RECOMMEND as MIN_POINTS_LOST_TO_RECOMMEND
from .base import MIN_SOURCE_COMMITS_FOR_TDD as MIN_SOURCE_COMMITS_FOR_TDD
from .base import MIN_WORDS_WITH_CONTEXT as MIN_WORDS_WITH_CONTEXT
from .base import MIRRORED_NAME_SHARE as MIRRORED_NAME_SHARE
from .base import MOSTLY as MOSTLY
from .base import PERCENT_MAX as PERCENT_MAX
from .base import SKIP_DIRS as SKIP_DIRS
from .base import TEST_DIR_NAMES as TEST_DIR_NAMES
from .base import TOP_RECOMMENDATIONS as TOP_RECOMMENDATIONS
from .base import UNIT_FLOOR as UNIT_FLOOR
from .base import UNIT_SPARSE as UNIT_SPARSE
from .base import VERSION as VERSION
from .base import FileInfo as FileInfo
from .base import Finding as Finding
from .base import Profile as Profile
from .base import Report as Report
from .base import Stats as Stats
from .cli import main as main
from .collection import collect as collect
from .coverage import CI_COVERAGE_RE as CI_COVERAGE_RE
from .coverage import CI_FILES as CI_FILES
from .coverage import CI_STRICT_RE as CI_STRICT_RE
from .coverage import COVERAGE_CONFIG_FILES as COVERAGE_CONFIG_FILES
from .coverage import COVERAGE_REPORTS as COVERAGE_REPORTS
from .coverage import COVERAGE_TOOL_RE as COVERAGE_TOOL_RE
from .coverage import MUTATION_REPORTS as MUTATION_REPORTS
from .coverage import PER_FILE_COVERAGE as PER_FILE_COVERAGE
from .coverage import TEST_CMD_RE as TEST_CMD_RE
from .coverage import THRESHOLD_PATTERNS as THRESHOLD_PATTERNS
from .coverage import cobertura_files as cobertura_files
from .coverage import find_threshold as find_threshold
from .coverage import go_profile_files as go_profile_files
from .coverage import is_ci_file as is_ci_file
from .coverage import jacoco_files as jacoco_files
from .coverage import json_report_files as json_report_files
from .coverage import lcov_files as lcov_files
from .coverage import measure_coverage as measure_coverage
from .coverage import measure_mutation as measure_mutation
from .coverage import parse_cargo_mutants as parse_cargo_mutants
from .coverage import parse_cobertura as parse_cobertura
from .coverage import parse_generic_mutation as parse_generic_mutation
from .coverage import parse_go_profile as parse_go_profile
from .coverage import parse_jacoco as parse_jacoco
from .coverage import parse_json_report as parse_json_report
from .coverage import parse_lcov as parse_lcov
from .coverage import parse_pitest as parse_pitest
from .coverage import parse_stryker as parse_stryker
from .detection import ASSERT_RE as ASSERT_RE
from .detection import BARE_ASSERT_RE as BARE_ASSERT_RE
from .detection import BEHAVIOUR_WORDS as BEHAVIOUR_WORDS
from .detection import BOUNDARY_NAME_WORDS as BOUNDARY_NAME_WORDS
from .detection import BOUNDARY_RE as BOUNDARY_RE
from .detection import BRANCH_RE as BRANCH_RE
from .detection import BRITTLE_SELECTOR_RE as BRITTLE_SELECTOR_RE
from .detection import CASE_RE as CASE_RE
from .detection import CHATTER_RE as CHATTER_RE
from .detection import COMMENT_RE as COMMENT_RE
from .detection import COMMENTED_ASSERT_RE as COMMENTED_ASSERT_RE
from .detection import CONDITION_WORDS as CONDITION_WORDS
from .detection import DEAD_BRANCH_RE as DEAD_BRANCH_RE
from .detection import DEFAULT_PROFILE as DEFAULT_PROFILE
from .detection import DOUBLE_CLEANUP_RE as DOUBLE_CLEANUP_RE
from .detection import DOUBLE_RE as DOUBLE_RE
from .detection import ELSE_RE as ELSE_RE
from .detection import ENV_COUPLING_RE as ENV_COUPLING_RE
from .detection import ERROR_ASSERT_RE as ERROR_ASSERT_RE
from .detection import ERROR_NAME_WORDS as ERROR_NAME_WORDS
from .detection import FILLER_WORDS as FILLER_WORDS
from .detection import FOCUS_RE as FOCUS_RE
from .detection import FROZEN_TIME_RE as FROZEN_TIME_RE
from .detection import GENERIC_ASSERT as GENERIC_ASSERT
from .detection import GHERKIN_RE as GHERKIN_RE
from .detection import GREEDY_CATCH_RE as GREEDY_CATCH_RE
from .detection import GUARD_RE as GUARD_RE
from .detection import JS_IMPORT_RE as JS_IMPORT_RE
from .detection import KIND_CONTENT_HINTS as KIND_CONTENT_HINTS
from .detection import KIND_DIR_HINTS as KIND_DIR_HINTS
from .detection import LANGUAGE_PROFILES as LANGUAGE_PROFILES
from .detection import LITERAL_RE as LITERAL_RE
from .detection import MIRROR_RE as MIRROR_RE
from .detection import MIRROR_SAFE_CALLS as MIRROR_SAFE_CALLS
from .detection import MOCK_ASSERT_RE as MOCK_ASSERT_RE
from .detection import MOCK_RE as MOCK_RE
from .detection import MUTATION_RE as MUTATION_RE
from .detection import NAME_RE as NAME_RE
from .detection import ORDER_DEPENDENT_RE as ORDER_DEPENDENT_RE
from .detection import PARAM_RE as PARAM_RE
from .detection import PHANTOM_LANGS as PHANTOM_LANGS
from .detection import PLATFORM_RE as PLATFORM_RE
from .detection import PRIVATE_ACCESS_RE as PRIVATE_ACCESS_RE
from .detection import PROPERTY_RE as PROPERTY_RE
from .detection import PY_IMPORT_RE as PY_IMPORT_RE
from .detection import ROBUST_SELECTOR_RE as ROBUST_SELECTOR_RE
from .detection import SEEDED_RANDOM_RE as SEEDED_RANDOM_RE
from .detection import SERIAL_ONLY_RE as SERIAL_ONLY_RE
from .detection import SETUP_BLOCK_RE as SETUP_BLOCK_RE
from .detection import SKIP_NO_REASON_RE as SKIP_NO_REASON_RE
from .detection import SKIP_RE as SKIP_RE
from .detection import SLEEP_RE as SLEEP_RE
from .detection import SNAPSHOT_RE as SNAPSHOT_RE
from .detection import SPEC_STYLE_RE as SPEC_STYLE_RE
from .detection import SPY_RE as SPY_RE
from .detection import STUB_RE as STUB_RE
from .detection import STYLE_FLAGS as STYLE_FLAGS
from .detection import SWALLOW_RE as SWALLOW_RE
from .detection import SYMBOL_RE as SYMBOL_RE
from .detection import TAUTOLOGY_RE as TAUTOLOGY_RE
from .detection import UNFROZEN_TIME_RE as UNFROZEN_TIME_RE
from .detection import UNINFORMATIVE_ASSERT_RE as UNINFORMATIVE_ASSERT_RE
from .detection import UNSEEDED_RANDOM_RE as UNSEEDED_RANDOM_RE
from .detection import WEAK_ASSERT_RE as WEAK_ASSERT_RE
from .detection import analyse_test_file as analyse_test_file
from .detection import blend_profile as blend_profile
from .detection import classify_kind as classify_kind
from .detection import classify_name as classify_name
from .detection import conditional_logic as conditional_logic
from .detection import extract_names as extract_names
from .detection import imported_project_names as imported_project_names
from .detection import is_test_file as is_test_file
from .detection import language_of as language_of
from .detection import line_of as line_of
from .detection import name_words as name_words
from .detection import normalise_body as normalise_body
from .detection import read_text as read_text
from .detection import walk as walk
from .detection import with_decorators as with_decorators
from .git import FIX_COMMIT_RE as FIX_COMMIT_RE
from .git import find_hotspots as find_hotspots
from .git import git_history as git_history
from .render import bar as bar
from .render import capped as capped
from .render import location as location
from .render import render_directories as render_directories
from .render import render_flags as render_flags
from .render import render_markdown as render_markdown
from .render import render_text as render_text
from .score import DIMENSIONS as DIMENSIONS
from .score import GRADES as GRADES
from .score import SCORERS as SCORERS
from .score import clamp as clamp
from .score import compare as compare
from .score import evaluate as evaluate
from .score import grade_for as grade_for
from .score import recommendations as recommendations
from .score import score_assertions as score_assertions
from .score import score_bdd as score_bdd
from .score import score_ci as score_ci
from .score import score_coverage as score_coverage
from .score import score_determinism as score_determinism
from .score import score_directories as score_directories
from .score import score_doubles as score_doubles
from .score import score_failure_paths as score_failure_paths
from .score import score_focus as score_focus
from .score import score_hygiene as score_hygiene
from .score import score_layer as score_layer
from .score import score_mutation as score_mutation
from .score import score_naming as score_naming
from .score import score_pyramid as score_pyramid
from .score import score_risk as score_risk
from .score import score_substance as score_substance
from .score import score_tdd as score_tdd
from .score import score_unit as score_unit
from .severity import FLAG_ORDER as FLAG_ORDER
from .severity import severity_for as severity_for
from .substance import find_decorative as find_decorative
from .substance import find_duplicates as find_duplicates
from .substance import find_phantoms as find_phantoms
from .substance import find_stale as find_stale
from .substance import source_stem as source_stem

__all__ = [
    "ARTIFACT_DIRS",
    "ASSERT_RE",
    "BARE_ASSERT_RE",
    "BAR_WIDTH",
    "BEHAVIOUR_WORDS",
    "BOUNDARY_NAME_WORDS",
    "BOUNDARY_RE",
    "BRANCH_RE",
    "BRITTLE_SELECTOR_RE",
    "BUSY_DOUBLE_DENSITY",
    "CASE_RE",
    "CHATTER_RE",
    "CI_COVERAGE_RE",
    "CI_FILES",
    "CI_STRICT_RE",
    "COMMENTED_ASSERT_RE",
    "COMMENT_RE",
    "CONDITION_WINDOW",
    "CONDITION_WORDS",
    "COVERAGE_CONFIG_FILES",
    "COVERAGE_REPORTS",
    "COVERAGE_TOOL_RE",
    "DEAD_BRANCH_RE",
    "DECORATIVE_COVERAGE",
    "DEFAULT_PROFILE",
    "DIMENSIONS",
    "DOUBLE_CLEANUP_RE",
    "DOUBLE_RE",
    "E2E_CEILING",
    "E2E_TARGET",
    "E2E_TOLERANCE",
    "ELSE_RE",
    "ENV_COUPLING_RE",
    "ERROR_ASSERT_RE",
    "ERROR_NAME_WORDS",
    "FILLER_WORDS",
    "FIX_COMMIT_RE",
    "FIX_COMMIT_SHARE",
    "FLAG_ORDER",
    "FOCUS_RE",
    "FRACTION_AS_PERCENT",
    "FROZEN_TIME_RE",
    "GENERIC_ASSERT",
    "GHERKIN_RE",
    "GIANT_CASE_LINES",
    "GRADES",
    "GREEDY_CATCH_RE",
    "GUARD_RE",
    "HEAVY_SETUP_LINES",
    "HIGH_SEVERITY_RANK",
    "HISTORY_LIMIT",
    "INTEGRATION_CEILING",
    "INTEGRATION_FLOOR",
    "INTEGRATION_SPARSE",
    "INTEGRATION_TARGET",
    "JS_EXT",
    "JS_IMPORT_RE",
    "KIND_CONTENT_HINTS",
    "KIND_DIR_HINTS",
    "LANGUAGE_PROFILES",
    "LANG_BY_EXT",
    "LIST_LIMIT",
    "LITERAL_RE",
    "LONG_CASE_LINES",
    "MANY_ASSERTIONS",
    "MANY_CASES",
    "MAX_FILE_BYTES",
    "MAX_NAME_WORDS_FOR_MIRROR",
    "MEDIUM_SEVERITY_RANK",
    "MIN_CHANGES",
    "MIN_CHURN_FILES",
    "MIN_CLUSTER",
    "MIN_MEANINGFUL_WORDS",
    "MIN_POINTS_LOST_TO_RECOMMEND",
    "MIN_SOURCE_COMMITS_FOR_TDD",
    "MIN_WORDS_WITH_CONTEXT",
    "MIRRORED_NAME_SHARE",
    "MIRROR_RE",
    "MIRROR_SAFE_CALLS",
    "MOCK_ASSERT_RE",
    "MOCK_RE",
    "MOSTLY",
    "MUTATION_RE",
    "MUTATION_REPORTS",
    "NAME_RE",
    "ORDER_DEPENDENT_RE",
    "PARAM_RE",
    "PERCENT_MAX",
    "PER_FILE_COVERAGE",
    "PHANTOM_LANGS",
    "PLATFORM_RE",
    "PRIVATE_ACCESS_RE",
    "PROPERTY_RE",
    "PY_IMPORT_RE",
    "ROBUST_SELECTOR_RE",
    "SCORERS",
    "SEEDED_RANDOM_RE",
    "SERIAL_ONLY_RE",
    "SETUP_BLOCK_RE",
    "SKIP_DIRS",
    "SKIP_NO_REASON_RE",
    "SKIP_RE",
    "SLEEP_RE",
    "SNAPSHOT_RE",
    "SPEC_STYLE_RE",
    "SPY_RE",
    "STUB_RE",
    "STYLE_FLAGS",
    "SWALLOW_RE",
    "SYMBOL_RE",
    "TAUTOLOGY_RE",
    "TEST_CMD_RE",
    "TEST_DIR_NAMES",
    "THRESHOLD_PATTERNS",
    "TOP_RECOMMENDATIONS",
    "UNFROZEN_TIME_RE",
    "UNINFORMATIVE_ASSERT_RE",
    "UNIT_FLOOR",
    "UNIT_SPARSE",
    "UNSEEDED_RANDOM_RE",
    "VERSION",
    "WEAK_ASSERT_RE",
    "FileInfo",
    "Finding",
    "Profile",
    "Report",
    "Stats",
    "analyse_test_file",
    "bar",
    "blend_profile",
    "capped",
    "clamp",
    "classify_kind",
    "classify_name",
    "cobertura_files",
    "collect",
    "compare",
    "conditional_logic",
    "evaluate",
    "extract_names",
    "find_decorative",
    "find_duplicates",
    "find_hotspots",
    "find_phantoms",
    "find_stale",
    "find_threshold",
    "git_history",
    "go_profile_files",
    "grade_for",
    "imported_project_names",
    "is_ci_file",
    "is_test_file",
    "jacoco_files",
    "json_report_files",
    "language_of",
    "lcov_files",
    "line_of",
    "location",
    "main",
    "measure_coverage",
    "measure_mutation",
    "name_words",
    "normalise_body",
    "parse_cargo_mutants",
    "parse_cobertura",
    "parse_generic_mutation",
    "parse_go_profile",
    "parse_jacoco",
    "parse_json_report",
    "parse_lcov",
    "parse_pitest",
    "parse_stryker",
    "read_text",
    "recommendations",
    "render_directories",
    "render_flags",
    "render_markdown",
    "render_text",
    "score_assertions",
    "score_bdd",
    "score_ci",
    "score_coverage",
    "score_determinism",
    "score_directories",
    "score_doubles",
    "score_failure_paths",
    "score_focus",
    "score_hygiene",
    "score_layer",
    "score_mutation",
    "score_naming",
    "score_pyramid",
    "score_risk",
    "score_substance",
    "score_tdd",
    "score_unit",
    "severity_for",
    "source_stem",
    "walk",
    "with_decorators",
]
