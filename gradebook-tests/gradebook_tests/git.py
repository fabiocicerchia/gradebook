"""What git says about how the tests have been maintained."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess

from .base import HISTORY_LIMIT, LANG_BY_EXT, LIST_LIMIT, MIN_CHURN_FILES, Stats, _GIT
from .detection import is_test_file

# ---------------------------------------------------------------------- git

# "Not converting production bugs into regression tests" — a fix that ships no
# test is a bug free to come back.
FIX_COMMIT_RE = re.compile(r"\b(?:fix|fixes|fixed|bug|bugfix|hotfix|regression|patch|repair)\b", re.IGNORECASE)


def git_history(root: Path, limit: int = HISTORY_LIMIT) -> Stats | None:
    """Commit-level TDD signal: do source changes arrive with test changes?"""

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

    # git reports paths from the repository root while the scan uses paths
    # relative to wherever it started. Without stripping the prefix, nothing
    # matches on a subdirectory scan and the stale-test and pairing checks
    # silently find nothing.
    prefix = run("rev-parse", "--show-prefix")
    if prefix is None:
        return None
    prefix = prefix.strip()
    log = run(
        "log",
        "-n",
        str(limit),
        "--no-merges",
        "--name-only",
        "--pretty=format:%x00%H %s",
        "--",
        ".",
    )
    if not log or not log.strip():
        return None

    commits = source_commits = cochanged = test_only = 0
    fix_commits = fix_commits_with_tests = 0
    file_commits = {}
    for position, chunk in enumerate(log.split("\x00")):
        rows = chunk.splitlines()
        subject = rows[0] if rows else ""
        lines = [ln for ln in rows[1:] if ln.strip()]
        if prefix:
            lines = [ln[len(prefix) :] for ln in lines if ln.startswith(prefix)]
        if not lines:
            continue
        commits += 1
        is_fix = bool(FIX_COMMIT_RE.search(subject))
        # Position in the log, newest first: ordering beats timestamps, which
        # collapse when several commits land in the same second.
        for line in lines:
            file_commits.setdefault(line, []).append(position)
        paths = [Path(ln) for ln in lines]
        tests = [p for p in paths if is_test_file(p)]
        sources = [p for p in paths if not is_test_file(p) and p.suffix in LANG_BY_EXT]
        if sources:
            source_commits += 1
            if tests:
                cochanged += 1
            if is_fix:
                fix_commits += 1
                if tests:
                    fix_commits_with_tests += 1
        elif tests:
            test_only += 1
    return {
        "commits_analysed": commits,
        "source_commits": source_commits,
        "source_commits_with_tests": cochanged,
        "test_only_commits": test_only,
        "fix_commits": fix_commits,
        "fix_commits_with_tests": fix_commits_with_tests,
        "file_commits": file_commits,
    }


def find_hotspots(
    file_commits: dict[str, int],
    source_files: list[str],
    tested: set[str],
    coverage_by_file: dict[str, float],
    limit: int = LIST_LIMIT,
) -> Stats | None:
    """Kapelonis AP4: is the code that changes most often the code under test?"""
    churn = sorted(
        ((len(file_commits.get(path, [])), path) for path in source_files),
        key=lambda item: (-item[0], item[1]),
    )
    churn = [(count, path) for count, path in churn if count > 1]
    if len(churn) < MIN_CHURN_FILES:
        return None  # too little history to say which files are hot
    hot_count = max(5, round(len(churn) * 0.2))
    hot = churn[:hot_count]
    findings = []
    covered = []
    untested = 0
    for count, path in hot:
        pct = coverage_by_file.get(Path(path).name)
        if pct is not None:
            covered.append(pct)
        if path not in tested:
            untested += 1
            if len(findings) < limit:
                findings.append(
                    {
                        "file": path,
                        "line": 0,
                        "kind": "untested-hotspot",
                        "message": f"changed {count} times and has no test file — "
                        "the code that breaks most often is untested",
                    }
                )
    return {
        "hot_files": len(hot),
        "untested_hot_files": untested,
        "hot_coverage": round(sum(covered) / len(covered), 1) if covered else None,
        "findings": findings,
    }


