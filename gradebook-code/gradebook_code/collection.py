"""Walking a tree and gathering everything the score is computed from."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

from .analysis import analyse_file, find_cycles, find_duplicate_blocks
from .base import (
    DEAD_NAME_CHARS,
    GOD_CLASS_METHODS,
    GOD_FILE_FUNCTIONS,
    GOD_FILE_LINES,
    LANG_BY_EXT,
    MAX_CONCERNS_PER_FILE,
    MAX_DEAD_CODE_FINDINGS,
    MIN_FUNCTIONS_FOR_COHESION,
    MIN_NAME_CHARS,
    REPEATED_LITERAL_USES,
    UNIT_LITERALS,
    WIDE_INTERFACE_METHODS,
    FileInfo,
    Profile,
    Stats,
    is_generated,
)
from .churn import find_hotspots, git_churn
from .declarations import FUNC_RE
from .metrics import (
    INTERFACE_RE,
    MAGIC_NUMBER_RE,
    VAGUE_NAMES,
    blend_profile,
    body_of,
    is_test_file,
    line_of,
    read_text,
    walk,
)
from .severity import severity_for

# ----------------------------------------------------------------- collect


def _yagni_pass(stats: Stats, infos: list[FileInfo], corpus: str) -> None:
    """Private helpers nobody calls, and abstractions with one implementer."""
    for info in infos:
        for function in info["functions"]:
            name = function["name"]
            private = name.startswith("_") or (info["lang"] == "go" and name[:1].islower())
            if private and len(name) > DEAD_NAME_CHARS and corpus.count(name) <= 1:
                stats["dead_symbols"] += 1
                if len([f for f in stats["findings"] if f["kind"] == "dead-code"]) < MAX_DEAD_CODE_FINDINGS:
                    stats["findings"].append(
                        {
                            "file": info["file"],
                            "line": function["line"],
                            "kind": "dead-code",
                            "message": f"`{name}` is private and never referenced",
                        }
                    )
        for klass in info["classes"]:
            if not klass["bases"].strip():
                continue
            for base in re.findall(r"\w+", klass["bases"]):
                if base in {"extends", "implements", "object", "Exception", "Enum", "ABC"}:
                    continue
                implementers = len(re.findall(rf"(?:extends|implements|:|\()\s*{base}\b", corpus))
                if implementers == 1:
                    stats["single_impl_interfaces"] += 1
                break
        stats["stub_overrides"] += info["stubs"]


def _cohesion_pass(stats: Stats, infos: list[FileInfo]) -> None:
    """How much of a class's own state its methods actually use."""
    for info in infos:
        if not info["classes"] or info["lang"] not in {
            "python",
            "ruby",
            "javascript",
            "typescript",
            "php",
        }:
            continue
        fields = set(re.findall(r"(?:self|this)\.(\w+)\s*=", "\n".join(f["body"] for f in info["functions"])))
        if not fields or len(info["functions"]) < MIN_FUNCTIONS_FOR_COHESION:
            continue
        used = [
            len({m for m in re.findall(r"(?:self|this)\.(\w+)", f["body"]) if m in fields}) for f in info["functions"]
        ]
        share = sum(1 for count in used if count) / len(used)
        stats["cohesion_classes"] += 1
        stats["cohesion_score"] += share


def _sources(root: Path, stats: Stats) -> list[tuple[Path, str, str]]:
    """Every source file worth reading, and the language tallies as a side
    effect: what was skipped for being generated is part of the report."""
    sources = []
    for abs_path, rel in walk(root):
        lang = LANG_BY_EXT.get(rel.suffix)
        if lang is None or is_test_file(rel):
            continue
        text = read_text(abs_path)
        if text is None:
            continue
        if is_generated(rel, text):
            stats["generated_skipped"] += 1
            continue
        sources.append((rel, text, lang))
        stats["languages"][lang] += 1
        stats["language_lines"][lang] += sum(1 for line in text.splitlines() if line.strip())
    return sources


def _name_and_size_tallies(stats: Stats, info: FileInfo, profile: Profile) -> None:
    """One file's function and class measurements, folded into the totals: the
    size and shape counts, the vague names, and the god-file finding."""
    for function in info["functions"]:
        stats["complexity_total"] += function["complexity"]
        stats["long_functions"] += function["lines"] > profile["max_lines"]
        stats["complex_functions"] += function["complexity"] > profile["max_complexity"]
        stats["deep_functions"] += function["nesting"] > profile["max_nesting"]
        stats["wide_functions"] += function["params"] > profile["max_params"]
        stats["flag_params"] += function["flag_params"]
        stats["named_things"] += 1
        if function["name"].lower() in VAGUE_NAMES or len(function["name"]) <= MIN_NAME_CHARS:
            stats["vague_names"] += 1

    # A file that is most of a subsystem on its own.
    if info["lines"] > GOD_FILE_LINES or len(info["functions"]) > GOD_FILE_FUNCTIONS:
        stats["god_files"] += 1
        stats["findings"].append(
            {
                "file": info["file"],
                "line": 1,
                "kind": "god-file",
                "message": f"{info['lines']} lines, {len(info['functions'])} functions, "
                f"{len(info['classes'])} classes — more than one reason to change",
            }
        )
    for klass in info["classes"]:
        stats["named_things"] += 1
        if klass["name"].lower() in VAGUE_NAMES or klass["name"].lower().endswith(
            ("manager", "helper", "util", "utils", "processor", "handler", "data")
        ):
            stats["vague_names"] += 1
        if klass["bases"].strip():
            stats["subclasses"] += 1


def _accumulate(
    stats: Stats, sources: list[tuple[Path, str, str]], profile: Profile, module_names: set[str]
) -> tuple[list[FileInfo], list[str], Counter, dict[str, set[str]]]:
    """Fold every file's measurements into `stats`, and hand back what the
    whole-project passes below need: the per-file records, their stripped
    text, the literal counts and the import graph."""
    graph: dict[str, set[str]] = defaultdict(set)
    literals: Counter = Counter()
    all_text: list[str] = []
    infos: list[FileInfo] = []
    for rel, text, lang in sources:
        info = analyse_file(rel, text, lang, profile)
        infos.append(info)
        all_text.append(info["code"])
        stats["files"] += 1
        stats["lines"] += info["lines"]
        stats["functions"] += len(info["functions"])
        stats["classes"] += len(info["classes"])
        stats["findings"].extend(info["findings"])
        stats["demeter_chains"] += info["demeter"]
        stats["todos"] += info["todos"]
        stats["commented_code"] += info["commented_code"]
        stats["stubs"] += info["stubs"]
        stats["global_state"] += info["globals"]
        if info["infra"]:
            stats["infra_files"] += 1
        if len(info["concerns"]) >= MAX_CONCERNS_PER_FILE:
            stats["mixed_concern_files"] += 1
            stats["findings"].append(
                {
                    "file": info["file"],
                    "line": 1,
                    "kind": "mixed-concerns",
                    "message": f"touches {', '.join(sorted(info['concerns']))} in one file",
                }
            )

        _name_and_size_tallies(stats, info, profile)

        # OCP: branching on a type or kind instead of dispatching on it.
        stats["type_switches"] += len(
            re.findall(
                r"(?:if|elif|else if|case|when)[^\n:{]{0,40}\b(?:type|kind|sort|category|status)\b"
                r"[^\n]{0,30}==",
                info["code"],
            )
        )
        stats["type_checks"] += len(
            re.findall(
                r"isinstance\(|instanceof\b|\.GetType\(\)|reflect\.TypeOf|\.class\s*==|is_a\?",
                info["code"],
            )
        )

        interface_re = INTERFACE_RE.get(lang)
        if interface_re:
            for match in interface_re.finditer(info["code"]):
                stats["interfaces"] += 1
                block = body_of(info["code"], match.start(), lang)
                methods = len(FUNC_RE[lang].findall(block)) if lang in FUNC_RE else 0
                if methods > WIDE_INTERFACE_METHODS:
                    stats["fat_interfaces"] += 1
                    stats["findings"].append(
                        {
                            "file": info["file"],
                            "line": line_of(text, match.start()),
                            "kind": "fat-interface",
                            "message": f"`{match.group(1)}` declares {methods} methods — "
                            "clients depend on more than they use",
                        }
                    )
        if len(info["classes"]) and lang in FUNC_RE:
            methods_per_class = len(info["functions"]) / len(info["classes"])
            if methods_per_class > GOD_CLASS_METHODS:
                stats["wide_classes"] += 1

        for match in MAGIC_NUMBER_RE.finditer(info["code"]):
            literals[match.group(0)] += 1

        module = rel.stem
        for target in info["imports"]:
            leaf = re.split(r"[./\\:]", target.strip("./"))[-1]
            if leaf and leaf != module and leaf in module_names:
                graph[module].add(leaf)
    return infos, all_text, literals, graph


def collect(root: Path) -> Stats:
    stats = {
        "root": str(root.resolve()),
        "files": 0,
        "lines": 0,
        "generated_skipped": 0,
        "languages": Counter(),
        "language_lines": Counter(),
        "functions": 0,
        "classes": 0,
        "findings": [],
        "long_functions": 0,
        "complex_functions": 0,
        "deep_functions": 0,
        "wide_functions": 0,
        "flag_params": 0,
        "complexity_total": 0,
        "god_files": 0,
        "wide_classes": 0,
        "mixed_concern_files": 0,
        "type_switches": 0,
        "type_checks": 0,
        "interfaces": 0,
        "fat_interfaces": 0,
        "single_impl_interfaces": 0,
        "stub_overrides": 0,
        "subclasses": 0,
        "infra_files": 0,
        "global_state": 0,
        "duplicate_lines": 0,
        "magic_literals": 0,
        "demeter_chains": 0,
        "cycles": [],
        "fan_out_total": 0,
        "modules": 0,
        "dead_symbols": 0,
        "todos": 0,
        "commented_code": 0,
        "stubs": 0,
        "vague_names": 0,
        "named_things": 0,
        "cohesion_classes": 0,
        "cohesion_score": 0.0,
        "hot_files": 0,
        "hot_complexity": 0.0,
        "average_complexity": 0.0,
        "profile": None,
    }
    sources = _sources(root, stats)

    profile = blend_profile(stats["language_lines"])
    stats["profile"] = profile

    module_names = {rel.stem for rel, _, _ in sources}
    infos, all_text, literals, graph = _accumulate(stats, sources, profile, module_names)

    stats["modules"] = len(module_names)
    stats["fan_out_total"] = sum(len(v) for v in graph.values())
    stats["cycles"] = find_cycles(graph)
    for cycle in stats["cycles"][:5]:
        stats["findings"].append(
            {
                "file": " -> ".join(cycle),
                "line": 0,
                "kind": "dependency-cycle",
                "message": "modules import each other in a loop — neither can be understood alone",
            }
        )

    duplicate_lines, duplicate_findings = find_duplicate_blocks([(info["file"], info["code"]) for info in infos])
    stats["duplicate_lines"] = duplicate_lines
    stats["findings"].extend(duplicate_findings)

    corpus = "\n".join(all_text)
    stats["magic_literals"] = sum(
        1 for value, count in literals.items() if count >= REPEATED_LITERAL_USES and value not in UNIT_LITERALS
    )

    # YAGNI and cohesion, each a pass of its own over the same files.
    _yagni_pass(stats, infos, corpus)
    _cohesion_pass(stats, infos)

    hotspots = find_hotspots(
        git_churn(root),
        {info["file"]: sum(f["complexity"] for f in info["functions"]) for info in infos},
    )
    if hotspots:
        stats["hot_files"] = hotspots["hot_files"]
        stats["hot_complexity"] = hotspots["hot_complexity"]
        stats["average_complexity"] = hotspots["average_complexity"]
        stats["findings"].extend(hotspots["findings"])

    stats["findings"].sort(key=lambda f: (f["kind"], f["file"], f["line"]))
    for finding in stats["findings"]:
        finding["severity"] = severity_for(finding["kind"])
    return stats
