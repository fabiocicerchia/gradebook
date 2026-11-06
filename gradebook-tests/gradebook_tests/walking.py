"""Reading the working tree: the walk and the file reads, the only I/O the
detectors need."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from .base import ARTIFACT_DIRS, LANG_BY_EXT, MAX_FILE_BYTES, SKIP_DIRS

# ------------------------------------------------------------------ walking


def read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        return path.read_text(errors="replace")
    except OSError:
        return None


def walk(root: Path) -> Iterator[tuple[Path, Path, bool]]:
    """Yield (absolute_path, relative_path, in_artifact_dir) for every file."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            abs_path = Path(dirpath) / name
            rel = abs_path.relative_to(root)
            in_artifact = any(p in ARTIFACT_DIRS for p in rel.parts[:-1])
            yield abs_path, rel, in_artifact


def language_of(rel: Path) -> str | None:
    if rel.suffix == ".feature":
        return "feature"
    return LANG_BY_EXT.get(rel.suffix)
