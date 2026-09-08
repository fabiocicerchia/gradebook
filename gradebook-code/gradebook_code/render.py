"""Rendering a result as text or as Markdown, and scoring a directory tree."""

from __future__ import annotations

from pathlib import Path

from .base import ARTIFACT_DIRS, BAR_WIDTH, SKIP_DIRS, TOP_RECOMMENDATIONS, VERSION, Finding, Report, Stats
from .collection import collect
from .score import evaluate, recommendations
from .severity import FLAG_ORDER

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
