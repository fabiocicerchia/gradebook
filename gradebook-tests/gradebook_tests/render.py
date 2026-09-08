"""Rendering a result as text or as Markdown."""

from __future__ import annotations

from .base import BAR_WIDTH, TOP_RECOMMENDATIONS, VERSION, Finding, Report, Stats
from .score import recommendations

# ------------------------------------------------------------------- render


def bar(score: float | None, width: int = BAR_WIDTH) -> str:
    if score is None:
        return "·" * width
    filled = round(score * width)
    return "█" * filled + "░" * (width - filled)


def render_text(report: Report, top: int = TOP_RECOMMENDATIONS, max_flags: int | None = None) -> str:
    stats = report["stats"]
    out = [f"gradebook-tests {VERSION} — {report['root']}"]
    langs = ", ".join(f"{k} ({v})" for k, v in list(stats["languages"].items())[:5]) or "none"
    profile = stats.get("profile") or {}
    if profile.get("languages"):
        langs += (
            f"  ·  calibrated for {'/'.join(profile['languages'])}: "
            f"{profile['test_code_ratio']:.2f}x test:code, "
            f"{profile['cases_per_source']:.1f} cases/file"
        )
    out.append(f"languages: {langs}")
    volume = ""
    if stats.get("test_to_code_ratio") is not None:
        volume = (
            f" · {stats['test_lines']:,} test lines / {stats['source_lines']:,} source "
            f"lines ({stats['test_to_code_ratio']:.2f}x)"
        )
    out.append(
        f"{stats['source_files']} source files · {stats['test_files']} test files · "
        f"{stats['test_cases']} test cases · {stats['assertions']} assertions{volume}"
    )
    out.append("")
    show_delta = "baseline" in report
    for dim in report["dimensions"]:
        points = "  n/a" if dim["score"] is None else f"{dim['points']:5.1f}"
        delta = ""
        if show_delta:
            value = dim.get("delta")
            delta = f"{value:+5.1f} " if value else ("      " if value is None else "    · ")
        out.append(f"  {dim['title']:<22} {bar(dim['score'])} {points}/{dim['weight']:<3.0f} {delta}{dim['detail']}")
    out.append("")
    headline = f"SCORE  {report['score']:.1f}/100   grade {report['grade']}"
    if show_delta:
        headline += f"   {report['baseline']['delta']:+.1f} vs baseline ({report['baseline']['score']:.1f})"
    out.append(headline)
    if show_delta and not report["baseline"]["comparable"]:
        out.append("note: the baseline scored a different set of dimensions — the total is not directly comparable")
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


def location(finding: Finding) -> str:
    return f"{finding['file']}:{finding['line']}" if finding["line"] else finding["file"]


def capped(findings: list[Finding], limit: int | None) -> list[Finding]:
    """None lists every finding; 0 or less hides the section."""
    if limit is None:
        return list(findings)
    return findings[:limit] if limit > 0 else []


def render_flags(findings: list[Finding] | None, limit: int | None) -> list[str]:
    findings = findings or []
    shown = capped(findings, limit)
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
        counts = f"{entry['source_files']} src / {entry['test_files']} test"
        out.append(
            f"  {entry['grade']}  {entry['score']:5.1f}  {entry['path']:<{width}}  {counts:<20} → {entry['top_win']}"
        )
    return out


def render_markdown(report: Report, top: int = TOP_RECOMMENDATIONS, max_flags: int | None = None) -> str:
    stats = report["stats"]
    out = [f"## Test suite score: **{report['score']:.1f}/100** (grade {report['grade']})", ""]
    out.append(
        f"`{report['root']}` — {stats['source_files']} source files, "
        f"{stats['test_files']} test files, {stats['test_cases']} test cases, "
        f"{stats['assertions']} assertions"
    )
    out.append("")
    show_delta = "baseline" in report
    if show_delta:
        out.append(
            f"Baseline: **{report['baseline']['score']:.1f}** "
            f"({report['baseline']['delta']:+.1f})"
            + ("" if report["baseline"]["comparable"] else " — baseline scored a different set of dimensions")
        )
        out.append("")
        out.append("| Dimension | Score | Δ | Weight | Detail |")
        out.append("|---|---:|---:|---:|---|")
    else:
        out.append("| Dimension | Score | Weight | Detail |")
        out.append("|---|---:|---:|---|")
    for dim in report["dimensions"]:
        points = "n/a" if dim["score"] is None else f"{dim['points']:.1f}"
        delta = ""
        if show_delta:
            value = dim.get("delta")
            delta = f" {value:+.1f} |" if value else (" |" if value is None else " · |")
        out.append(f"| {dim['title']} | {points} |{delta} {dim['weight']:.0f} | {dim['detail']} |")
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
    shown = capped(findings, max_flags)
    if shown:
        out.append("")
        out.append(f"### Red flags ({len(findings)})")
        for finding in shown:
            out.append(f"- `{location(finding)}` **{finding['kind']}** — {finding['message']}")
        if len(findings) > len(shown):
            out.append(f"- … {len(findings) - len(shown)} more")
    if report.get("directories"):
        out.append("")
        out.append("### By directory")
        out.append("| Directory | Score | Grade | Tests | Biggest win |")
        out.append("|---|---:|---|---:|---|")
        for entry in report["directories"]:
            out.append(
                f"| `{entry['path']}` | {entry['score']:.1f} | {entry['grade']} | "
                f"{entry['test_files']} file(s) | {entry['top_win']} |"
            )
    return "\n".join(out)
