"""Finding the declarations a file makes, per language."""

from __future__ import annotations

import re

# ------------------------------------------------------------- declarations

FUNC_RE = {
    "python": re.compile(r"^([ \t]*)(?:async[ \t]+)?def[ \t]+(\w+)[ \t]*\(", re.MULTILINE),
    "javascript": re.compile(
        r"^([ \t]*)(?:export[ \t]+)?(?:async[ \t]+)?function[ \t]+(\w+)[ \t]*\("
        r"|^([ \t]*)(?:export[ \t]+)?(?:const|let)[ \t]+(\w+)[ \t]*=[ \t]*(?:async[ \t]+)?\("
        r"|^([ \t]*)(?:public|private|protected|static|async)*[ \t]*(\w+)[ \t]*\([^)]*\)[ \t]*\{",
        re.MULTILINE,
    ),
    "go": re.compile(r"^()func[ \t]+(?:\([^)]*\)[ \t]*)?(\w+)[ \t]*\(", re.MULTILINE),
    "java": re.compile(
        r"^([ \t]*)(?:@\w+[ \t]*)*(?:public|private|protected|static|final|synchronized"
        r"|abstract|native)[\w<>\[\], \t]*[ \t](\w+)[ \t]*\([^;]*\)[ \t]*\{",
        re.MULTILINE,
    ),
    "ruby": re.compile(r"^([ \t]*)def[ \t]+(\w+[?!]?)", re.MULTILINE),
    "php": re.compile(
        r"^([ \t]*)(?:(?:public|private|protected|static|final|abstract)[ \t]+)*"
        r"function[ \t]+(\w+)[ \t]*\(",
        re.MULTILINE,
    ),
    "rust": re.compile(r"^([ \t]*)(?:pub(?:\([^)]*\))?[ \t]+)?(?:async[ \t]+)?fn[ \t]+(\w+)", re.MULTILINE),
    "csharp": re.compile(
        r"^([ \t]*)(?:\[[^\]]*\][ \t]*)*(?:public|private|protected|internal"
        r"|static|async|override|virtual)[\w<>\[\], \t]*[ \t](\w+)[ \t]*\("
        r"[^;]*\)[ \t]*\{",
        re.MULTILINE,
    ),
    "elixir": re.compile(r"^([ \t]*)defp?[ \t]+(\w+[?!]?)", re.MULTILINE),
    "scala": re.compile(r"^([ \t]*)(?:override[ \t]+)?(?:private[ \t]+)?def[ \t]+(\w+)", re.MULTILINE),
    "shell": re.compile(r"^()(?:function[ \t]+)?(\w+)[ \t]*\(\)[ \t]*\{", re.MULTILINE),
    "lua": re.compile(r"^([ \t]*)(?:local[ \t]+)?function[ \t]+([\w.:]+)", re.MULTILINE),
}
FUNC_RE["typescript"] = FUNC_RE["javascript"]
FUNC_RE["kotlin"] = re.compile(
    r"^([ \t]*)(?:(?:private|internal|public|override|suspend)[ \t]+)*"
    r"fun[ \t]+(?:<[^>]+>[ \t]*)?(\w+)[ \t]*\(",
    re.MULTILINE,
)
for _lang in ("c", "cpp", "swift"):
    FUNC_RE.setdefault(_lang, re.compile(r"^()[\w:<>*&\[\] \t]+?(\w+)[ \t]*\([^;]*\)[ \t]*\{", re.MULTILINE))

CLASS_RE = {
    "python": re.compile(r"^[ \t]*class[ \t]+(\w+)[ \t]*(?:\(([^)]*)\))?", re.MULTILINE),
    "javascript": re.compile(
        r"^[ \t]*(?:export[ \t]+)?(?:default[ \t]+)?class[ \t]+(\w+)"
        r"(?:[ \t]+extends[ \t]+([\w.]+))?",
        re.MULTILINE,
    ),
    "java": re.compile(
        r"^[ \t]*(?:public|private|protected|final|abstract|static|[ \t])*"
        r"(?:class|interface|enum|record)[ \t]+(\w+)"
        r"((?:[ \t]+(?:extends|implements)[ \t]+[\w., <>]+)?)",
        re.MULTILINE,
    ),
    "go": re.compile(r"^type[ \t]+(\w+)[ \t]+(struct|interface)", re.MULTILINE),
    "ruby": re.compile(r"^[ \t]*(?:class|module)[ \t]+(\w+)(?:[ \t]*<[ \t]*([\w:]+))?", re.MULTILINE),
    "php": re.compile(
        r"^[ \t]*(?:final[ \t]+|abstract[ \t]+)?(?:class|interface|trait)[ \t]+(\w+)"
        r"((?:[ \t]+(?:extends|implements)[ \t]+[\w, \\]+)?)",
        re.MULTILINE,
    ),
    "rust": re.compile(r"^[ \t]*(?:pub[ \t]+)?(?:struct|enum|trait)[ \t]+(\w+)()", re.MULTILINE),
    "csharp": re.compile(
        r"^[ \t]*(?:public|private|protected|internal|sealed|abstract|static"
        r"|partial|[ \t])*(?:class|interface|record|struct)[ \t]+(\w+)"
        r"([ \t]*:[ \t]*[\w, <>]+)?",
        re.MULTILINE,
    ),
    "elixir": re.compile(r"^[ \t]*defmodule[ \t]+([\w.]+)()", re.MULTILINE),
    "scala": re.compile(
        r"^[ \t]*(?:case[ \t]+)?(?:class|object|trait)[ \t]+(\w+)"
        r"((?:[ \t]+extends[ \t]+[\w, \[\]]+)?)",
        re.MULTILINE,
    ),
}
CLASS_RE["typescript"] = re.compile(
    r"^[ \t]*(?:export[ \t]+)?(?:default[ \t]+)?(?:abstract[ \t]+)?(?:class|interface)[ \t]+(\w+)"
    r"((?:[ \t]+(?:extends|implements)[ \t]+[\w., <>]+)?)",
    re.MULTILINE,
)
CLASS_RE["kotlin"] = re.compile(
    r"^[ \t]*(?:(?:open|abstract|sealed|data|internal|private)[ \t]+)*"
    r"(?:class|interface|object)[ \t]+(\w+)([^\n{]*)",
    re.MULTILINE,
)

IMPORT_RE = {
    # `from pkg import module` names the dependency in the second group, so both
    # halves are kept and resolved against the repo's own module names.
    "python": re.compile(
        r"^[ \t]*(?:from[ \t]+([.\w]+)[ \t]+import[ \t]+([^\n#]+)"
        r"|import[ \t]+([.\w]+))",
        re.MULTILINE,
    ),
    "javascript": re.compile(
        r"""^[ \t]*import[^'"\n]*['"]([^'"]+)['"]"""
        r"""|require\(\s*['"]([^'"]+)['"]\s*\)""",
        re.MULTILINE,
    ),
    "go": re.compile(r'^[ \t]*(?:_[ \t]+|\w+[ \t]+)?"([^"]+)"', re.MULTILINE),
    "java": re.compile(r"^[ \t]*import[ \t]+(?:static[ \t]+)?([\w.]+)", re.MULTILINE),
    "ruby": re.compile(r"^[ \t]*require(?:_relative)?[ \t]+['\"]([^'\"]+)['\"]", re.MULTILINE),
    "php": re.compile(r"^[ \t]*use[ \t]+([\w\\]+)", re.MULTILINE),
    "rust": re.compile(r"^[ \t]*(?:pub[ \t]+)?use[ \t]+([\w:]+)", re.MULTILINE),
    "csharp": re.compile(r"^[ \t]*using[ \t]+(?:static[ \t]+)?([\w.]+)", re.MULTILINE),
    "elixir": re.compile(r"^[ \t]*(?:alias|import|use)[ \t]+([\w.]+)", re.MULTILINE),
    "scala": re.compile(r"^[ \t]*import[ \t]+([\w.]+)", re.MULTILINE),
}
IMPORT_RE["typescript"] = IMPORT_RE["javascript"]
IMPORT_RE["kotlin"] = IMPORT_RE["java"]
