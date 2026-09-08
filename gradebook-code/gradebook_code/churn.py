"""What git says about how the code has changed."""

from __future__ import annotations

import shutil
import subprocess
from collections import Counter
from pathlib import Path

from .base import HOTSPOT_LIMIT, MIN_CHANGED_FOR_HOTSPOTS, MIN_FILES_FOR_HOTSPOTS, Stats

# ------------------------------------------------------------------- churn

FIX_LIMIT = 800
# Resolved once: `git` on PATH, or nothing to ask about churn.
_GIT = shutil.which("git") or "git"


def git_churn(root: Path, limit: int = FIX_LIMIT) -> dict[str, int] | None:
    """How many commits touched each file, keyed the same way as the scan.

    `git log` reports paths from the repository root, so when the scan starts
    in a subdirectory the prefix is stripped — otherwise nothing ever matches
    and the dimension silently scores nothing.
    """

    def run(*args: str) -> str | None:
        try:
            result = subprocess.run(  # noqa: S603 — a fixed argv; `args` is this module's own
                [_GIT, "-C", str(root), *args],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return result.stdout if result.returncode == 0 else None

    prefix = run("rev-parse", "--show-prefix")
    if prefix is None:
        return {}
    prefix = prefix.strip()
    log = run("log", "-n", str(limit), "--no-merges", "--name-only", "--pretty=format:%x00", "--", ".")
    if not log:
        return {}
    counts = Counter()
    for line in log.splitlines():
        path = line.strip()
        if not path or path.startswith("\x00"):
            continue
        if prefix:
            if not path.startswith(prefix):
                continue
            path = path[len(prefix) :]
        counts[path] += 1
    return dict(counts)


def find_hotspots(
    churn_counts: dict[str, int], file_complexity: dict[str, float], limit: int = HOTSPOT_LIMIT
) -> Stats | None:
    """Complexity that sits where the changes land is the expensive kind."""
    scored = [(path, churn_counts.get(path, 0), complexity) for path, complexity in file_complexity.items()]
    changed = [entry for entry in scored if entry[1] > 1]
    # Enough files to have a meaningful average, and enough churn to rank by.
    # Three files hammered while the rest sit still is the hotspot case, not a
    # reason to give up on it.
    if len(scored) < MIN_FILES_FOR_HOTSPOTS or len(changed) < MIN_CHANGED_FOR_HOTSPOTS:
        return None
    changed.sort(key=lambda entry: (-entry[1], entry[0]))
    hot_count = max(3, round(len(changed) * 0.2))
    hot = changed[:hot_count]
    overall = sum(complexity for _, _, complexity in scored) / max(len(scored), 1)
    hot_average = sum(complexity for _, _, complexity in hot) / len(hot)
    findings = []
    for path, commits, complexity in sorted(hot, key=lambda e: -(e[1] * e[2])):
        if complexity <= overall or len(findings) >= limit:
            continue
        findings.append(
            {
                "file": path,
                "line": 1,
                "kind": "hotspot",
                "message": f"changed {commits} times and carries {complexity} complexity "
                f"(codebase average {overall:.0f}) — the expensive kind",
            }
        )
    return {
        "hot_files": len(hot),
        "hot_complexity": round(hot_average, 1),
        "average_complexity": round(overall, 1),
        "findings": findings,
    }
