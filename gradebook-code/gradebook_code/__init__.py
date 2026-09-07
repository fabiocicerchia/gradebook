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

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from .analysis import COMMENT_LINE_RE as COMMENT_LINE_RE
from .analysis import DECLARATION_RE as DECLARATION_RE
from .analysis import NORMALISE_RE as NORMALISE_RE
from .analysis import STATEMENT_RE as STATEMENT_RE
from .analysis import analyse_file, find_cycles, find_duplicate_blocks
from .analysis import normalise_line as normalise_line
from .base import (
    ARTIFACT_DIRS,
    BAR_WIDTH,
    DEAD_NAME_CHARS,
    GOD_CLASS_METHODS,
    GOD_FILE_FUNCTIONS,
    GOD_FILE_LINES,
    HIGH_SEVERITY_RANK,
    LANG_BY_EXT,
    MAX_CONCERNS_PER_FILE,
    MAX_DEAD_CODE_FINDINGS,
    MEDIUM_SEVERITY_RANK,
    MIN_FUNCTIONS_FOR_COHESION,
    MIN_NAME_CHARS,
    REPEATED_LITERAL_USES,
    SKIP_DIRS,
    TOP_RECOMMENDATIONS,
    UNIT_LITERALS,
    VERSION,
    WIDE_INTERFACE_METHODS,
    FileInfo,
    Finding,
    Profile,
    Report,
    Stats,
    is_generated,
)
from .base import BRACE_LANGS as BRACE_LANGS
from .base import CYCLE_LIMIT as CYCLE_LIMIT
from .base import DUPE_LIMIT as DUPE_LIMIT
from .base import DUPE_WINDOW as DUPE_WINDOW
from .base import GENERATED_NAME_RE as GENERATED_NAME_RE
from .base import GENERATED_RE as GENERATED_RE
from .base import HOTSPOT_LIMIT as HOTSPOT_LIMIT
from .base import JS_EXT as JS_EXT
from .base import MAX_FILE_BYTES as MAX_FILE_BYTES
from .base import MIN_CHANGED_FOR_HOTSPOTS as MIN_CHANGED_FOR_HOTSPOTS
from .base import MIN_FILES_FOR_HOTSPOTS as MIN_FILES_FOR_HOTSPOTS
from .base import MIN_MODULES_FOR_COUPLING as MIN_MODULES_FOR_COUPLING
from .base import MIN_POINTS_LOST_TO_RECOMMEND as MIN_POINTS_LOST_TO_RECOMMEND
from .base import MINIFIED_LINE_CHARS as MINIFIED_LINE_CHARS
from .base import SIGNATURE_SCAN_CHARS as SIGNATURE_SCAN_CHARS
from .base import SIGNATURE_SPAN as SIGNATURE_SPAN
from .base import TEST_DIR_NAMES as TEST_DIR_NAMES
from .churn import FIX_LIMIT as FIX_LIMIT
from .churn import find_hotspots, git_churn
from .declarations import CLASS_RE as CLASS_RE
from .declarations import FUNC_RE
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
from .metrics import LANGUAGE_PROFILES as LANGUAGE_PROFILES
from .metrics import STUB_RE as STUB_RE
from .metrics import TODO_RE as TODO_RE
from .metrics import count_params as count_params
from .metrics import nesting_depth as nesting_depth
from .metrics import signature_window as signature_window
from .scanning import BLOCK_COMMENTS as BLOCK_COMMENTS
from .scanning import DEFAULT_BLOCK_COMMENTS as DEFAULT_BLOCK_COMMENTS
from .scanning import DEFAULT_LINE_COMMENTS as DEFAULT_LINE_COMMENTS
from .scanning import DEFAULT_QUOTES as DEFAULT_QUOTES
from .scanning import LINE_COMMENTS as LINE_COMMENTS
from .scanning import STRING_QUOTES as STRING_QUOTES
from .scanning import TRIPLE_QUOTE_LANGS as TRIPLE_QUOTE_LANGS
from .scanning import strip_noise as strip_noise
from .score import DIMENSIONS, evaluate, recommendations
from .score import GRADES as GRADES
from .score import SCORERS as SCORERS
from .score import clamp as clamp
from .score import grade_for as grade_for
from .score import penalise as penalise
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


# ------------------------------------------------------------------- render


def bar(score: float | None, width: int = BAR_WIDTH) -> str:
    if score is None:
        return "·" * width
    filled = round(score * width)
    return "█" * filled + "░" * (width - filled)


def location(finding: Finding) -> str:
    return f"{finding['file']}:{finding['line']}" if finding["line"] else finding["file"]


def capped(findings: list[Finding], limit: int | None) -> list[Finding]:
    """None lists every finding; 0 or less hides the section."""
    if limit is None:
        return list(findings)
    return findings[:limit] if limit > 0 else []


def rank_flags(findings: list[Finding] | None) -> list[Finding]:
    return sorted(findings or [], key=lambda f: (FLAG_ORDER.get(f["kind"], 9), f["file"], f["line"]))


def render_flags(findings: list[Finding] | None, limit: int | None) -> list[str]:
    findings = findings or []
    shown = capped(rank_flags(findings), limit)
    if not shown:
        return []
    width = max(len(location(f)) for f in shown)
    out = ["", f"Red flags ({len(findings)}):"]
    for finding in shown:
        out.append(f"  {location(finding):<{width}}  {finding['kind']:<18} {finding['message']}")
    if len(findings) > len(shown):
        out.append(f"  … {len(findings) - len(shown)} more (raise --max-flags)")
    return out


FLAG_ORDER = {
    "hotspot": 0,
    "dependency-cycle": 1,
    "god-file": 2,
    "complex-function": 2,
    "duplicate-block": 3,
    "deep-nesting": 4,
    "mixed-concerns": 5,
    "fat-interface": 6,
    "dead-code": 7,
    "long-function": 8,
    "many-parameters": 9,
}


def severity_for(kind: str) -> str:
    """One ranking, three buckets — editors read this, they don't re-derive it."""
    rank = FLAG_ORDER.get(kind, 9)
    if rank <= HIGH_SEVERITY_RANK:
        return "high"
    return "medium" if rank <= MEDIUM_SEVERITY_RANK else "low"


def render_directories(directories: list[Stats]) -> list[str]:
    if not directories:
        return []
    width = max(len(d["path"]) for d in directories)
    out = ["", "By directory (worst first):"]
    for entry in directories:
        out.append(
            f"  {entry['grade']}  {entry['score']:5.1f}  {entry['path']:<{width}}  "
            f"{entry['files']:>4} files  → {entry['top_win']}"
        )
    return out


def render_text(report: Report, top: int = TOP_RECOMMENDATIONS, max_flags: int | None = None) -> str:
    stats = report["stats"]
    out = [f"gradebook-code {VERSION} — {report['root']}"]
    langs = ", ".join(f"{k} ({v})" for k, v in list(stats["languages"].items())[:5]) or "none"
    profile = stats.get("profile") or {}
    if profile.get("languages"):
        langs += (
            f"  ·  calibrated for {'/'.join(profile['languages'])}: "
            f"{profile['max_lines']} lines, complexity {profile['max_complexity']}, "
            f"{profile['max_params']} params"
        )
    out.append(f"languages: {langs}")
    counts = (
        f"{stats['files']} files · {stats['lines']:,} lines · {stats['functions']} "
        f"functions · {stats['classes']} classes · {stats['modules']} modules"
    )
    if stats.get("generated_skipped"):
        counts += f" · {stats['generated_skipped']} generated file(s) skipped"
    out.append(counts)
    out.append("")
    for dim in report["dimensions"]:
        points = "  n/a" if dim["score"] is None else f"{dim['points']:5.1f}"
        out.append(f"  {dim['title']:<30} {bar(dim['score'])} {points}/{dim['weight']:<3.0f} {dim['detail']}")
    out.append("")
    out.append(f"SCORE  {report['score']:.1f}/100   grade {report['grade']}")
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


def render_markdown(report: Report, top: int = TOP_RECOMMENDATIONS, max_flags: int | None = None) -> str:
    stats = report["stats"]
    out = [f"## Code score: **{report['score']:.1f}/100** (grade {report['grade']})", ""]
    out.append(
        f"`{report['root']}` — {stats['files']} files, {stats['lines']:,} lines, "
        f"{stats['functions']} functions, {stats['classes']} classes"
    )
    out.append("")
    out.append("| Principle | Score | Weight | Detail |")
    out.append("|---|---:|---:|---|")
    for dim in report["dimensions"]:
        points = "n/a" if dim["score"] is None else f"{dim['points']:.1f}"
        out.append(f"| {dim['title']} | {points} | {dim['weight']:.0f} | {dim['detail']} |")
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
    shown = capped(rank_flags(findings), max_flags)
    if shown:
        out.append("")
        out.append(f"### Red flags ({len(findings)})")
        for finding in shown:
            out.append(f"- `{location(finding)}` **{finding['kind']}** — {finding['message']}")
        if len(findings) > len(shown):
            out.append(f"- … {len(findings) - len(shown)} more")
    return "\n".join(out)


def score_directories(root: Path) -> list[Stats]:
    results = []
    for child in sorted(p for p in root.iterdir() if p.is_dir()):
        if child.name in SKIP_DIRS or child.name in ARTIFACT_DIRS:
            continue
        stats = collect(child)
        if not stats["files"]:
            continue
        report = evaluate(stats)
        top = recommendations(report, 1)
        results.append(
            {
                "path": child.name,
                "score": report["score"],
                "grade": report["grade"],
                "files": stats["files"],
                "lines": stats["lines"],
                "top_win": top[0]["advice"] if top else "",
            }
        )
    return sorted(results, key=lambda r: r["score"])


# ---------------------------------------------------------------------- cli


def _build_parser() -> argparse.ArgumentParser:
    """The CLI surface, in one place."""
    parser = argparse.ArgumentParser(
        prog="gradebook-code",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", nargs="?", default=".", help="codebase to evaluate")
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    parser.add_argument("--fail-under", type=float, metavar="N", help="exit 1 when the score is below N (CI gate)")
    parser.add_argument("--baseline", metavar="FILE", help="a previous --format json report to diff against")
    parser.add_argument(
        "--fail-on-drop",
        type=float,
        nargs="?",
        const=0.0,
        metavar="N",
        help="with --baseline, exit 1 when the score drops by more than N",
    )
    parser.add_argument(
        "--by-dir",
        action="store_true",
        help="also score each immediate subdirectory that holds code",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        metavar="N",
        help="how many recommendations to show (default 5)",
    )
    parser.add_argument(
        "--max-flags",
        type=int,
        default=None,
        metavar="N",
        help="cap the red flags listed (default: all, 0 to hide)",
    )
    parser.add_argument("--list-dimensions", action="store_true", help="print the scoring model and exit")
    parser.add_argument("--version", action="version", version=f"gradebook-code {VERSION}")
    return parser


def _emit(report: Report, args: argparse.Namespace) -> None:
    """The report, in whichever format was asked for."""
    if args.format == "json":
        json.dump(report, sys.stdout, indent=2, default=str)
        print()  # noqa: T201 — the tool's output
    elif args.format == "markdown":
        print(render_markdown(report, args.top, args.max_flags))  # noqa: T201 — the tool's output
    else:
        text = render_text(report, args.top, args.max_flags)
        if "baseline" in report:
            text = text.replace(
                f"grade {report['grade']}",
                f"grade {report['grade']}   {report['baseline']['delta']:+.1f} vs baseline "
                f"({report['baseline']['score']:.1f})",
                1,
            )
        print(text)  # noqa: T201 — the tool's output


def _gate_failed(report: Report, args: argparse.Namespace) -> bool:
    """Whether either gate — a floor, or a drop against a baseline — was
    crossed. Says which on stderr, since that is the whole point of a gate."""
    failed = False
    if args.fail_under is not None and report["score"] < args.fail_under:
        print(  # noqa: T201 — the tool's output
            f"gradebook-code: {report['score']:.1f} is below --fail-under {args.fail_under}",
            file=sys.stderr,
        )
        failed = True
    if args.fail_on_drop is not None:
        drop = -report["baseline"]["delta"]
        if drop > args.fail_on_drop:
            print(f"gradebook-code: dropped {drop:.1f} points against the baseline", file=sys.stderr)  # noqa: T201 — the tool's output
            failed = True
    return failed


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_dimensions:
        for key, title, weight in DIMENSIONS:
            print(f"{key:<10} {weight:>3} pts  {title}")  # noqa: T201 — the tool's output
        print(  # noqa: T201 — the tool's output
            "\nAny dimension without evidence (no interfaces, no inheritance, too few "
            "modules)\nis left unscored and the remaining weights renormalise."
        )
        return 0
    if args.fail_on_drop is not None and not args.baseline:
        print("gradebook-code: --fail-on-drop needs --baseline", file=sys.stderr)  # noqa: T201 — the tool's output
        return 2

    root = Path(args.path)
    if not root.is_dir():
        print(f"gradebook-code: not a directory: {root}", file=sys.stderr)  # noqa: T201 — the tool's output
        return 2

    report = evaluate(collect(root))
    report["recommendations"] = [
        {"dimension": d["id"], "points": d["lost"], "advice": d["advice"]} for d in recommendations(report, args.top)
    ]
    if args.by_dir:
        report["directories"] = score_directories(root)
    if args.baseline:
        try:
            baseline = json.loads(Path(args.baseline).read_text())
            report["baseline"] = {
                "score": baseline["score"],
                "delta": round(report["score"] - baseline["score"], 1),
            }
        except (OSError, ValueError, KeyError) as error:
            print(f"gradebook-code: cannot read baseline {args.baseline}: {error}", file=sys.stderr)  # noqa: T201 — the tool's output
            return 2

    _emit(report, args)

    return 1 if _gate_failed(report, args) else 0


if __name__ == "__main__":
    sys.exit(main())
