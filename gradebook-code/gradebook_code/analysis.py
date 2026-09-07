"""Putting the measurements together per file."""

from __future__ import annotations

from pathlib import Path
import re

from .base import CYCLE_LIMIT, DUPE_LIMIT, DUPE_WINDOW, FileInfo, Finding, Profile

from .declarations import CLASS_RE, FUNC_RE, IMPORT_RE

from .scanning import strip_noise

from .metrics import COMMENTED_CODE_RE, CONCERN_RE, DECISION_RE, DEMETER_RE, GLOBAL_STATE_RE, IMPLICIT_FIRST_PARAM, INFRA_RE, STUB_RE, TODO_RE, body_of, count_params, line_of, nesting_depth, signature_window

# ------------------------------------------------------------- file analysis


def _imports_in(text: str, lang: str) -> list[str]:
    """Every module name this file imports, in the spelling it used."""
    out: list[str] = []
    import_re = IMPORT_RE.get(lang)
    if import_re:
        for match in import_re.finditer(text):
            for group in match.groups():
                if not group:
                    continue
                for part in group.split(","):
                    target = part.strip().strip("()").split(" as ")[0].strip()
                    if target:
                        out.append(target)
    return out


def analyse_file(rel: Path, text: str, lang: str, profile: Profile) -> FileInfo:
    """Per-function and per-class measurements for one source file.

    Structure is read from `code` — the source with comments and string
    contents blanked — while the comment-shaped signals (TODOs, commented-out
    code) and the import and infrastructure markers are read from the original,
    where the strings they live in still exist.
    """
    func_re = FUNC_RE.get(lang)
    class_re = CLASS_RE.get(lang)
    code = strip_noise(text, lang)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    info = {
        "file": str(rel),
        "lang": lang,
        "lines": len(lines),
        "code": code,
        "functions": [],
        "classes": [],
        "findings": [],
        "demeter": len(DEMETER_RE.findall(code)),
        "todos": len(TODO_RE.findall(text)),
        "commented_code": len(COMMENTED_CODE_RE.findall(text)),
        "stubs": len(STUB_RE.findall(code)),
        "globals": len(GLOBAL_STATE_RE[lang].findall(code)) if lang in GLOBAL_STATE_RE else 0,
        "infra": len(INFRA_RE.findall(text)),
        "concerns": {name for name, pattern in CONCERN_RE.items() if pattern.search(text)},
        "imports": [],
    }

    info["imports"] = _imports_in(text, lang)

    if class_re:
        for match in class_re.finditer(code):
            name = match.group(1)
            bases = (match.group(2) or "").strip() if match.lastindex and match.lastindex > 1 else ""
            info["classes"].append({"name": name, "bases": bases, "line": line_of(code, match.start())})

    if func_re:
        for match in func_re.finditer(code):
            groups = [g for g in match.groups() if g is not None]
            name = groups[-1] if groups else "?"
            if name in {"if", "for", "while", "switch", "catch", "return"}:
                continue
            body = body_of(code, match.start(), lang)
            body_lines = [ln for ln in body.splitlines() if ln.strip()]
            function = {
                "name": name,
                "line": line_of(code, match.start()),
                "lines": len(body_lines),
                "complexity": 1 + len(DECISION_RE.findall(body)),
                "nesting": nesting_depth(body, lang),
                "params": count_params(signature_window(body, name), implicit_self=lang in IMPLICIT_FIRST_PARAM),
                "flag_params": len(re.findall(r"=\s*(?:True|False|true|false)\b", body.split("\n", 1)[0])),
                "body": body,
            }
            info["functions"].append(function)
            for label, value, limit, kind in (
                ("lines", function["lines"], profile["max_lines"], "long-function"),
                (
                    "complexity",
                    function["complexity"],
                    profile["max_complexity"],
                    "complex-function",
                ),
                ("nesting", function["nesting"], profile["max_nesting"], "deep-nesting"),
                ("params", function["params"], profile["max_params"], "many-parameters"),
            ):
                if value > limit:
                    info["findings"].append(
                        {
                            "file": str(rel),
                            "line": function["line"],
                            "kind": kind,
                            "message": f"`{name}` has {value} {label} (limit {limit:g})",
                        }
                    )
    return info


NORMALISE_RE = re.compile(r"'[^'\n]*'|\"[^\"\n]*\"|`[^`\n]*`|\b\d+(?:\.\d+)?\b")
COMMENT_LINE_RE = re.compile(r"^[ \t]*(?:#|//|\*|/\*)")


def normalise_line(line: str) -> str:
    return re.sub(r"\s+", " ", NORMALISE_RE.sub("@", line)).strip()


STATEMENT_RE = re.compile(r"[-+*/%=<>!]=?|\breturn\b|\bif\b|\bfor\b|\bwhile\b|\w+\s*\(")
DECLARATION_RE = re.compile(r"^\s*(?:import|from|package|use|require|#include|\w+\s*:\s*[\"'@])")


def find_duplicate_blocks(
    files: list[FileInfo], window: int = DUPE_WINDOW, limit: int = DUPE_LIMIT
) -> tuple[int, list[Finding]]:
    """Windows of consecutive lines that appear verbatim somewhere else.

    Framework boilerplate — a struct literal of declarations, a block of
    imports — repeats legitimately and would otherwise dominate, so a window
    only counts when most of it is actual statements.
    """
    seen = {}
    duplicated_lines = set()
    findings = []
    reported = set()
    for path, text in files:
        rows = [
            (index + 1, normalise_line(line))
            for index, line in enumerate(text.splitlines())
            if line.strip() and not COMMENT_LINE_RE.match(line)
        ]
        for start in range(len(rows) - window + 1):
            chunk = rows[start : start + window]
            block = "\n".join(line for _, line in chunk)
            if len(block) < window * 14:
                continue
            statements = sum(1 for _, line in chunk if STATEMENT_RE.search(line) and not DECLARATION_RE.match(line))
            if statements < window * 0.6:
                continue
            origin = seen.get(block)
            if origin is None:
                seen[block] = (path, chunk[0][0])
                continue
            if origin[0] == path and abs(origin[1] - chunk[0][0]) < window:
                continue
            # Sliding windows overlap, so each duplicated line is counted once:
            # summing window lengths can report more duplicated lines than the
            # file has.
            duplicated_lines.update((path, number) for number, _ in chunk)
            key = (path, chunk[0][0] // window)
            if key not in reported and len(findings) < limit:
                reported.add(key)
                findings.append(
                    {
                        "file": path,
                        "line": chunk[0][0],
                        "kind": "duplicate-block",
                        "message": f"{window} lines repeated from {origin[0]}:{origin[1]}",
                    }
                )
    return len(duplicated_lines), findings


def find_cycles(graph: dict[str, set[str]], limit: int = CYCLE_LIMIT) -> list[list[str]]:
    """Import cycles between the repo's own modules."""
    colour = {}
    stack = []
    cycles = []

    def visit(node: str) -> None:
        colour[node] = 1
        stack.append(node)
        for neighbour in sorted(graph.get(node, ())):
            if colour.get(neighbour, 0) == 0:
                visit(neighbour)
            elif colour.get(neighbour) == 1 and len(cycles) < limit:
                start = stack.index(neighbour)
                cycles.append([*stack[start:], neighbour])
        stack.pop()
        colour[node] = 2

    for node in sorted(graph):
        if colour.get(node, 0) == 0:
            visit(node)
    return cycles


