"""Whether a test asserts anything, or only runs."""

from __future__ import annotations

from pathlib import Path
import re

from .base import DECORATIVE_COVERAGE, Finding, JS_EXT, LIST_LIMIT, MIN_CHANGES, MIN_CLUSTER

# --------------------------------------------------------------- substance


def source_stem(rel: Path) -> str:
    """The source file stem a test file is named after, if any."""
    stem = rel.stem
    name = stem
    if rel.suffix == ".py":
        name = name[5:] if name.startswith("test_") else re.sub(r"_test$", "", name)
    elif rel.suffix in JS_EXT:
        name = re.sub(r"\.(test|spec)$", "", name)
    elif rel.suffix == ".go":
        name = re.sub(r"_test$", "", name)
    elif rel.suffix in {".java", ".kt"}:
        name = re.sub(r"(?:Tests?|Spec|IT)$", "", name)
    elif rel.suffix == ".rb":
        name = re.sub(r"_(?:spec|test)$", "", name)
    elif rel.suffix in {".php", ".cs"}:
        name = re.sub(r"(?:Tests?|Spec)$", "", name)
    elif rel.suffix == ".exs":
        name = re.sub(r"_test$", "", name)
    return name if name and name != stem else None


def find_duplicates(
    bodies_by_file: dict[str, list[tuple[str, int, str]]], limit: int = LIST_LIMIT, min_cluster: int = MIN_CLUSTER
) -> tuple[int, list[Finding]]:
    """Cases whose bodies are identical once names and literals are stripped.

    Two matching bodies are common and often legitimate; three or more is a
    copy-paste run, and the fix is one parametrised case.
    """
    clusters = {}
    for file, bodies in bodies_by_file:
        for body, line in bodies:
            clusters.setdefault(body, []).append((file, line))
    findings = []
    redundant = 0
    for places in sorted(clusters.values(), key=len, reverse=True):
        if len(places) < min_cluster:
            continue
        redundant += len(places) - 1
        origin = places[0]
        for file, line in places[1:]:
            if len(findings) < limit:
                findings.append(
                    {
                        "file": file,
                        "line": line,
                        "kind": "duplicate-case",
                        "message": f"same body as {origin[0]}:{origin[1]} — parametrise instead",
                    }
                )
    return redundant, findings


def find_phantoms(
    imports_by_file: dict[str, set[str]], symbols: set[str], limit: int = LIST_LIMIT
) -> tuple[int, list[Finding]]:
    """Test imports of project symbols that no source file defines."""
    findings = []
    seen = set()
    for file, names in imports_by_file:
        for name in names:
            if name in symbols or (file, name) in seen:
                continue
            seen.add((file, name))
            if len(findings) < limit:
                findings.append(
                    {
                        "file": file,
                        "line": 0,
                        "kind": "phantom-symbol",
                        "message": f"imports `{name}`, which no source file defines — dead or invented test",
                    }
                )
    return len(seen), findings


def find_stale(
    pairs: list[tuple[str, str]], file_commits: dict[str, int], min_changes: int = MIN_CHANGES, limit: int = LIST_LIMIT
) -> tuple[int, list[Finding]]:
    """Tests frozen while the code they cover kept changing.

    Positions come from `git log` newest-first, so a lower number is a more
    recent commit.
    """
    findings = []
    stale = 0
    for test_file, source_file in pairs:
        test_positions = file_commits.get(test_file)
        source_positions = file_commits.get(source_file)
        if not test_positions or not source_positions:
            continue
        last_test = min(test_positions)
        changes = sum(1 for position in source_positions if position < last_test)
        if changes >= min_changes:
            stale += 1
            if len(findings) < limit:
                findings.append(
                    {
                        "file": test_file,
                        "line": 0,
                        "kind": "stale-test",
                        "message": f"{source_file} changed {changes} times since this test last did",
                    }
                )
    return stale, findings


def find_decorative(
    pairs: list[tuple[str, str]],
    file_coverage: dict[str, float],
    threshold: float = DECORATIVE_COVERAGE,
    limit: int = LIST_LIMIT,
) -> tuple[int, list[Finding]]:
    """Source files that have a test file and are still barely covered."""
    findings = []
    decorative = 0
    for test_file, source_file in pairs:
        pct = file_coverage.get(source_file)
        if pct is None or pct >= threshold:
            continue
        decorative += 1
        if len(findings) < limit:
            findings.append(
                {
                    "file": test_file,
                    "line": 0,
                    "kind": "decorative-test",
                    "message": f"{source_file} has this test file and is still {pct:.0f}% covered",
                }
            )
    return decorative, findings


