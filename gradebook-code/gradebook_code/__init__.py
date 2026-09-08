"""gradebook-code — score a codebase against DRY, YAGNI, GRASP, SOLID and KISS.

The principles are famous and the arguments about them are endless, so this
scores the *observable* consequences: how complex the functions are, how much
is copy-pasted, how wide the classes are, how far the dependencies reach, how
much abstraction exists for a single caller. Every finding carries a file and
a line, because "SRP 4.1/10" is not something anyone can act on.

  gradebook-code .
  gradebook-code /path/to/repo --format markdown
  gradebook-code . --fail-under 60 --by-dir
"""

from .analysis import COMMENT_LINE_RE as COMMENT_LINE_RE
from .analysis import DECLARATION_RE as DECLARATION_RE
from .analysis import NORMALISE_RE as NORMALISE_RE
from .analysis import STATEMENT_RE as STATEMENT_RE
from .analysis import analyse_file as analyse_file
from .analysis import find_cycles as find_cycles
from .analysis import find_duplicate_blocks as find_duplicate_blocks
from .analysis import normalise_line as normalise_line
from .base import ARTIFACT_DIRS as ARTIFACT_DIRS
from .base import BAR_WIDTH as BAR_WIDTH
from .base import BRACE_LANGS as BRACE_LANGS
from .base import CYCLE_LIMIT as CYCLE_LIMIT
from .base import DEAD_NAME_CHARS as DEAD_NAME_CHARS
from .base import DUPE_LIMIT as DUPE_LIMIT
from .base import DUPE_WINDOW as DUPE_WINDOW
from .base import GENERATED_NAME_RE as GENERATED_NAME_RE
from .base import GENERATED_RE as GENERATED_RE
from .base import GOD_CLASS_METHODS as GOD_CLASS_METHODS
from .base import GOD_FILE_FUNCTIONS as GOD_FILE_FUNCTIONS
from .base import GOD_FILE_LINES as GOD_FILE_LINES
from .base import HIGH_SEVERITY_RANK as HIGH_SEVERITY_RANK
from .base import HOTSPOT_LIMIT as HOTSPOT_LIMIT
from .base import JS_EXT as JS_EXT
from .base import LANG_BY_EXT as LANG_BY_EXT
from .base import MAX_CONCERNS_PER_FILE as MAX_CONCERNS_PER_FILE
from .base import MAX_DEAD_CODE_FINDINGS as MAX_DEAD_CODE_FINDINGS
from .base import MAX_FILE_BYTES as MAX_FILE_BYTES
from .base import MEDIUM_SEVERITY_RANK as MEDIUM_SEVERITY_RANK
from .base import MIN_CHANGED_FOR_HOTSPOTS as MIN_CHANGED_FOR_HOTSPOTS
from .base import MIN_FILES_FOR_HOTSPOTS as MIN_FILES_FOR_HOTSPOTS
from .base import MIN_FUNCTIONS_FOR_COHESION as MIN_FUNCTIONS_FOR_COHESION
from .base import MIN_MODULES_FOR_COUPLING as MIN_MODULES_FOR_COUPLING
from .base import MIN_NAME_CHARS as MIN_NAME_CHARS
from .base import MIN_POINTS_LOST_TO_RECOMMEND as MIN_POINTS_LOST_TO_RECOMMEND
from .base import MINIFIED_LINE_CHARS as MINIFIED_LINE_CHARS
from .base import REPEATED_LITERAL_USES as REPEATED_LITERAL_USES
from .base import SIGNATURE_SCAN_CHARS as SIGNATURE_SCAN_CHARS
from .base import SIGNATURE_SPAN as SIGNATURE_SPAN
from .base import SKIP_DIRS as SKIP_DIRS
from .base import TEST_DIR_NAMES as TEST_DIR_NAMES
from .base import TOP_RECOMMENDATIONS as TOP_RECOMMENDATIONS
from .base import UNIT_LITERALS as UNIT_LITERALS
from .base import VERSION as VERSION
from .base import WIDE_INTERFACE_METHODS as WIDE_INTERFACE_METHODS
from .base import FileInfo as FileInfo
from .base import Finding as Finding
from .base import Profile as Profile
from .base import Report as Report
from .base import Stats as Stats
from .base import is_generated as is_generated
from .churn import FIX_LIMIT as FIX_LIMIT
from .churn import find_hotspots as find_hotspots
from .churn import git_churn as git_churn
from .cli import main as main
from .collect import collect as collect
from .declarations import CLASS_RE as CLASS_RE
from .declarations import FUNC_RE as FUNC_RE
from .declarations import IMPORT_RE as IMPORT_RE
from .metrics import COMMENTED_CODE_RE as COMMENTED_CODE_RE
from .metrics import CONCERN_RE as CONCERN_RE
from .metrics import DECISION_RE as DECISION_RE
from .metrics import DEFAULT_PROFILE as DEFAULT_PROFILE
from .metrics import DEMETER_RE as DEMETER_RE
from .metrics import GLOBAL_STATE_RE as GLOBAL_STATE_RE
from .metrics import IMPLEMENTS_RE as IMPLEMENTS_RE
from .metrics import IMPLICIT_FIRST_PARAM as IMPLICIT_FIRST_PARAM
from .metrics import IMPLICIT_NAMES as IMPLICIT_NAMES
from .metrics import INFRA_RE as INFRA_RE
from .metrics import INTERFACE_RE as INTERFACE_RE
from .metrics import LANGUAGE_PROFILES as LANGUAGE_PROFILES
from .metrics import MAGIC_NUMBER_RE as MAGIC_NUMBER_RE
from .metrics import STUB_RE as STUB_RE
from .metrics import TODO_RE as TODO_RE
from .metrics import VAGUE_NAMES as VAGUE_NAMES
from .metrics import blend_profile as blend_profile
from .metrics import body_of as body_of
from .metrics import count_params as count_params
from .metrics import is_test_file as is_test_file
from .metrics import line_of as line_of
from .metrics import nesting_depth as nesting_depth
from .metrics import read_text as read_text
from .metrics import signature_window as signature_window
from .metrics import walk as walk
from .render import bar as bar
from .render import capped as capped
from .render import location as location
from .render import rank_flags as rank_flags
from .render import render_directories as render_directories
from .render import render_flags as render_flags
from .render import render_markdown as render_markdown
from .render import render_text as render_text
from .render import score_directories as score_directories
from .scanning import BLOCK_COMMENTS as BLOCK_COMMENTS
from .scanning import DEFAULT_BLOCK_COMMENTS as DEFAULT_BLOCK_COMMENTS
from .scanning import DEFAULT_LINE_COMMENTS as DEFAULT_LINE_COMMENTS
from .scanning import DEFAULT_QUOTES as DEFAULT_QUOTES
from .scanning import LINE_COMMENTS as LINE_COMMENTS
from .scanning import STRING_QUOTES as STRING_QUOTES
from .scanning import TRIPLE_QUOTE_LANGS as TRIPLE_QUOTE_LANGS
from .scanning import strip_noise as strip_noise
from .score import DIMENSIONS as DIMENSIONS
from .score import GRADES as GRADES
from .score import SCORERS as SCORERS
from .score import clamp as clamp
from .score import evaluate as evaluate
from .score import grade_for as grade_for
from .score import penalise as penalise
from .score import recommendations as recommendations
from .score import score_cohesion as score_cohesion
from .score import score_coupling as score_coupling
from .score import score_demeter as score_demeter
from .score import score_dip as score_dip
from .score import score_dry as score_dry
from .score import score_hotspots as score_hotspots
from .score import score_isp as score_isp
from .score import score_kiss as score_kiss
from .score import score_lsp as score_lsp
from .score import score_naming as score_naming
from .score import score_ocp as score_ocp
from .score import score_srp as score_srp
from .score import score_yagni as score_yagni
from .severity import FLAG_ORDER as FLAG_ORDER
from .severity import severity_for as severity_for

__all__ = [
    "ARTIFACT_DIRS",
    "BAR_WIDTH",
    "BLOCK_COMMENTS",
    "BRACE_LANGS",
    "CLASS_RE",
    "COMMENTED_CODE_RE",
    "COMMENT_LINE_RE",
    "CONCERN_RE",
    "CYCLE_LIMIT",
    "DEAD_NAME_CHARS",
    "DECISION_RE",
    "DECLARATION_RE",
    "DEFAULT_BLOCK_COMMENTS",
    "DEFAULT_LINE_COMMENTS",
    "DEFAULT_PROFILE",
    "DEFAULT_QUOTES",
    "DEMETER_RE",
    "DIMENSIONS",
    "DUPE_LIMIT",
    "DUPE_WINDOW",
    "FIX_LIMIT",
    "FLAG_ORDER",
    "FUNC_RE",
    "GENERATED_NAME_RE",
    "GENERATED_RE",
    "GLOBAL_STATE_RE",
    "GOD_CLASS_METHODS",
    "GOD_FILE_FUNCTIONS",
    "GOD_FILE_LINES",
    "GRADES",
    "HIGH_SEVERITY_RANK",
    "HOTSPOT_LIMIT",
    "IMPLEMENTS_RE",
    "IMPLICIT_FIRST_PARAM",
    "IMPLICIT_NAMES",
    "IMPORT_RE",
    "INFRA_RE",
    "INTERFACE_RE",
    "JS_EXT",
    "LANGUAGE_PROFILES",
    "LANG_BY_EXT",
    "LINE_COMMENTS",
    "MAGIC_NUMBER_RE",
    "MAX_CONCERNS_PER_FILE",
    "MAX_DEAD_CODE_FINDINGS",
    "MAX_FILE_BYTES",
    "MEDIUM_SEVERITY_RANK",
    "MINIFIED_LINE_CHARS",
    "MIN_CHANGED_FOR_HOTSPOTS",
    "MIN_FILES_FOR_HOTSPOTS",
    "MIN_FUNCTIONS_FOR_COHESION",
    "MIN_MODULES_FOR_COUPLING",
    "MIN_NAME_CHARS",
    "MIN_POINTS_LOST_TO_RECOMMEND",
    "NORMALISE_RE",
    "REPEATED_LITERAL_USES",
    "SCORERS",
    "SIGNATURE_SCAN_CHARS",
    "SIGNATURE_SPAN",
    "SKIP_DIRS",
    "STATEMENT_RE",
    "STRING_QUOTES",
    "STUB_RE",
    "TEST_DIR_NAMES",
    "TODO_RE",
    "TOP_RECOMMENDATIONS",
    "TRIPLE_QUOTE_LANGS",
    "UNIT_LITERALS",
    "VAGUE_NAMES",
    "VERSION",
    "WIDE_INTERFACE_METHODS",
    "FileInfo",
    "Finding",
    "Profile",
    "Report",
    "Stats",
    "analyse_file",
    "bar",
    "blend_profile",
    "body_of",
    "capped",
    "clamp",
    "collect",
    "count_params",
    "evaluate",
    "find_cycles",
    "find_duplicate_blocks",
    "find_hotspots",
    "git_churn",
    "grade_for",
    "is_generated",
    "is_test_file",
    "line_of",
    "location",
    "main",
    "nesting_depth",
    "normalise_line",
    "penalise",
    "rank_flags",
    "read_text",
    "recommendations",
    "render_directories",
    "render_flags",
    "render_markdown",
    "render_text",
    "score_cohesion",
    "score_coupling",
    "score_demeter",
    "score_dip",
    "score_directories",
    "score_dry",
    "score_hotspots",
    "score_isp",
    "score_kiss",
    "score_lsp",
    "score_naming",
    "score_ocp",
    "score_srp",
    "score_yagni",
    "severity_for",
    "signature_window",
    "strip_noise",
    "walk",
]
