"""The measurements: length, complexity, parameters, nesting."""

from __future__ import annotations

import os
import re
from collections.abc import Callable, Iterator
from pathlib import Path

from .base import (
    ARTIFACT_DIRS,
    BRACE_LANGS,
    JS_EXT,
    MAX_FILE_BYTES,
    SIGNATURE_SCAN_CHARS,
    SIGNATURE_SPAN,
    SKIP_DIRS,
    TEST_DIR_NAMES,
    Profile,
)

# ------------------------------------------------------------------ metrics

DECISION_RE = re.compile(
    r"(?<![.\w])(?:if|elif|else\s+if|elsif|for|foreach|while|case|when|catch|rescue|except)"
    r"(?![\w])|&&|\|\||\?(?=[^:\n]{1,60}:)|(?<![.\w])and(?![\w])|(?<![.\w])or(?![\w])"
)
DEMETER_RE = re.compile(r"(?<![\w.])(?!self\.|this\.|super\.)\w+(?:\.\w+){3,}")
MAGIC_NUMBER_RE = re.compile(r"(?<![\w.])\d{2,}(?:\.\d+)?(?![\w.])")
COMMENTED_CODE_RE = re.compile(
    r"^[ \t]*(?://|#)[ \t]*(?:if|for|while|return|def |func |function |class |import |from |var "
    r"|let |const |print|console\.|[\w.]+\s*=[^=]|[\w.]+\([^)]*\)\s*;?\s*$)",
    re.MULTILINE,
)
TODO_RE = re.compile(r"(?://|#|/\*|\*)[ \t]*(?:TODO|FIXME|HACK|XXX|WIP|LATER)\b", re.IGNORECASE)
STUB_RE = re.compile(
    r"NotImplementedError|not[ _]implemented|TODO\(\)|unimplemented!\("
    r"|throw new UnsupportedOperationException|abstract[ \t]+method",
    re.IGNORECASE,
)
GLOBAL_STATE_RE = {
    "python": re.compile(r"^[A-Za-z_]\w*[ \t]*=[ \t]*(?:\[\]|\{\}|set\(\)|dict\(|list\(|defaultdict)", re.MULTILINE),
    "javascript": re.compile(r"^(?:export[ \t]+)?(?:let|var)[ \t]+\w+[ \t]*=[ \t]*(?:\[|\{)", re.MULTILINE),
    "go": re.compile(r"^var[ \t]+\w+[ \t]+(?:map\[|\[\]|\*)", re.MULTILINE),
}
GLOBAL_STATE_RE["typescript"] = GLOBAL_STATE_RE["javascript"]

# Infrastructure reached for directly: the DIP signal is how far it spreads.
INFRA_RE = re.compile(
    r"psycopg\d?|sqlalchemy|pymongo|redis\.|boto3|requests\.(?:get|post|put|delete)"
    r"|urllib\.request|http\.client|axios\.|fetch\(|node-fetch|mongoose|knex|pg\.Pool"
    r"|sql\.Open|gorm\.|http\.(?:Get|Post|Client)|net/http|DriverManager|JdbcTemplate"
    r"|HttpClient|RestTemplate|SqlConnection|PDO\(|mysqli_|curl_init|File\.(?:Open|ReadAll)"
    r"|open\([^)]*['\"][wra]|os\.(?:remove|mkdir|rename)|smtplib|sendgrid|stripe\.",
    re.IGNORECASE,
)
CONCERN_RE = {
    "database": re.compile(
        r"psycopg|sqlalchemy|sqlite3|pymongo|redis|gorm|jdbc|mysqli|mongoose"
        r"|knex|SqlConnection|\bsql\b",
        re.IGNORECASE,
    ),
    "http": re.compile(
        r"requests\.|axios|fetch\(|net/http|HttpClient|RestTemplate|urllib|flask"
        r"|fastapi|express|gin-gonic|spring",
        re.IGNORECASE,
    ),
    "filesystem": re.compile(r"\bos\.path|pathlib|fs\.readFile|ioutil|File\.Open|fopen", re.IGNORECASE),
    "ui": re.compile(r"react|vue|angular|swing|tkinter|template|render\(|jsx", re.IGNORECASE),
    "crypto": re.compile(r"hashlib|bcrypt|jwt|crypto\.|openssl|argon2", re.IGNORECASE),
    "queue": re.compile(r"kafka|rabbitmq|celery|sqs|pubsub|amqp", re.IGNORECASE),
}
VAGUE_NAMES = {
    "data",
    "info",
    "item",
    "items",
    "obj",
    "object",
    "value",
    "val",
    "temp",
    "tmp",
    "result",
    "res",
    "ret",
    "foo",
    "bar",
    "baz",
    "thing",
    "things",
    "stuff",
    "handler",
    "manager",
    "helper",
    "helpers",
    "util",
    "utils",
    "utility",
    "utilities",
    "process",
    "handle",
    "do",
    "run",
    "execute",
    "perform",
    "misc",
    "common",
    "base",
    "core",
    "main",
    "wrapper",
    "impl",
}
INTERFACE_RE = {
    "python": re.compile(r"class[ \t]+(\w+)[ \t]*\([^)]*(?:ABC|Protocol|abstractmethod)"),
    "java": re.compile(r"(?:^|\s)interface[ \t]+(\w+)"),
    "typescript": re.compile(r"(?:^|\s)interface[ \t]+(\w+)"),
    "go": re.compile(r"^type[ \t]+(\w+)[ \t]+interface", re.MULTILINE),
    "csharp": re.compile(r"(?:^|\s)interface[ \t]+(I\w+)"),
    "php": re.compile(r"(?:^|\s)interface[ \t]+(\w+)"),
    "rust": re.compile(r"(?:^|\s)trait[ \t]+(\w+)"),
    "scala": re.compile(r"(?:^|\s)trait[ \t]+(\w+)"),
}
INTERFACE_RE["kotlin"] = INTERFACE_RE["java"]
IMPLEMENTS_RE = re.compile(r"(?:implements|extends|impl|:)\s+([\w, ]+)")

# Per-language tolerances: Go functions carry explicit error handling, Java
# carries ceremony, Python and Ruby are terse and should stay small.
LANGUAGE_PROFILES = {
    #             max_lines  max_complexity  max_params  max_nesting
    "python": (40, 10, 5, 4),
    "javascript": (40, 10, 4, 4),
    "typescript": (40, 10, 4, 4),
    "go": (60, 12, 5, 4),
    "java": (50, 12, 5, 4),
    "kotlin": (40, 10, 5, 4),
    "csharp": (50, 12, 5, 4),
    "ruby": (25, 8, 4, 3),
    "php": (45, 10, 5, 4),
    "rust": (50, 12, 5, 4),
    "elixir": (20, 6, 4, 3),
    "scala": (35, 10, 4, 4),
    "shell": (40, 10, 5, 3),
    "c": (60, 14, 6, 4),
    "cpp": (60, 14, 6, 4),
}
DEFAULT_PROFILE = (45, 11, 5, 4)


def blend_profile(language_lines: dict[str, int]) -> Profile:
    """Weight each ecosystem's tolerances by how much of the code it is."""
    total = sum(language_lines.values())
    if not total:
        return {
            "max_lines": DEFAULT_PROFILE[0],
            "max_complexity": DEFAULT_PROFILE[1],
            "max_params": DEFAULT_PROFILE[2],
            "max_nesting": DEFAULT_PROFILE[3],
            "languages": [],
        }
    values = [0.0, 0.0, 0.0, 0.0]
    for lang, lines in language_lines.items():
        profile = LANGUAGE_PROFILES.get(lang, DEFAULT_PROFILE)
        share = lines / total
        values = [v + p * share for v, p in zip(values, profile, strict=True)]
    return {
        "max_lines": round(values[0]),
        "max_complexity": round(values[1]),
        "max_params": round(values[2]),
        "max_nesting": round(values[3], 1),
        "languages": sorted(language_lines, key=language_lines.get, reverse=True)[:2],
    }


def read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        return path.read_text(errors="replace")
    except OSError:
        return None


def walk(root: Path) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            abs_path = Path(dirpath) / name
            rel = abs_path.relative_to(root)
            if any(p in ARTIFACT_DIRS for p in rel.parts[:-1]):
                continue
            yield abs_path, rel


# How each ecosystem spells a test file, by suffix. A table rather than a
# chain of returns: adding a language is a row, and the rules sit side by side
# where they can be compared.
_TEST_STEM_RULES: dict[str, Callable[[str], bool]] = {
    ".py": lambda stem: stem.startswith("test_") or stem.endswith("_test") or stem == "conftest",
    ".go": lambda stem: stem.endswith("_test"),
    ".java": lambda stem: stem.endswith(("Test", "Tests", "Spec")),
    ".kt": lambda stem: stem.endswith(("Test", "Tests", "Spec")),
    ".cs": lambda stem: stem.endswith(("Test", "Tests", "Spec")),
    ".rb": lambda stem: stem.endswith(("_spec", "_test")),
    ".php": lambda stem: stem.endswith("Test"),
    **{ext: lambda stem: bool(re.search(r"\.(test|spec)$", stem)) for ext in JS_EXT},
}


def is_test_file(rel: Path) -> bool:
    stem, suffix = rel.stem, rel.suffix
    parts = {p.lower() for p in rel.parts[:-1]}
    if parts & TEST_DIR_NAMES or suffix == ".feature":
        return True
    rule = _TEST_STEM_RULES.get(suffix)
    return bool(rule and rule(stem))


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def body_of(text: str, start: int, lang: str) -> str:
    """The source of one function, by brace matching or by indentation."""
    if lang in BRACE_LANGS:
        opening = text.find("{", start)
        if opening == -1 or opening - start > SIGNATURE_SCAN_CHARS:
            return text[start : start + 400]
        depth = 0
        for index in range(opening, len(text)):
            char = text[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
        return text[start:]
    lines = text[start:].splitlines()
    if not lines:
        return ""
    base = len(lines[0]) - len(lines[0].lstrip())
    body = [lines[0]]
    for line in lines[1:]:
        if line.strip() and (len(line) - len(line.lstrip())) <= base:
            break
        body.append(line)
    return "\n".join(body)


def signature_window(body: str, name: str, span: int = SIGNATURE_SPAN) -> str:
    """The text just after a function's name, where its parameters live."""
    position = body.find(name)
    if position == -1:
        return body[:span]
    start = position + len(name)
    return body[start : start + span]


def nesting_depth(body: str, lang: str) -> int:
    if lang in BRACE_LANGS:
        depth = peak = 0
        for char in body:
            if char == "{":
                depth += 1
                peak = max(peak, depth)
            elif char == "}":
                depth = max(0, depth - 1)
        return max(0, peak - 1)
    lines = [ln for ln in body.splitlines() if ln.strip()]
    if not lines:
        return 0
    base = len(lines[0]) - len(lines[0].lstrip())
    indents = sorted({len(ln) - len(ln.lstrip()) for ln in lines[1:]})
    unit = min((i - base for i in indents if i > base), default=4) or 4
    deepest = max((len(ln) - len(ln.lstrip()) for ln in lines[1:]), default=base)
    return max(0, round((deepest - base) / unit) - 1)


# `self` is not a parameter the caller passes; counting it penalises every
# method against every free function.
IMPLICIT_FIRST_PARAM = {"python"}
IMPLICIT_NAMES = {"self", "cls", "this", "$this"}


def count_params(signature: str, *, implicit_self: bool = False) -> int:
    """Count declared parameters, across line breaks and nested generics."""
    start = signature.find("(")
    if start == -1:
        return 0
    depth = 0
    collected = []
    for char in signature[start:]:
        if char in "([{":
            depth += 1
            if depth == 1:
                continue
        elif char in ")]}":
            depth -= 1
            if depth == 0:
                break
        collected.append(char)
    parts = [part.strip() for part in re.split(r",(?![^(\[{<]*[)\]}>])", "".join(collected)) if part.strip()]
    if implicit_self and parts and parts[0].split(":")[0].strip() in IMPLICIT_NAMES:
        parts = parts[1:]
    return len(parts)


