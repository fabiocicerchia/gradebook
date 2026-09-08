"""Which findings count as which severity. Neither collection nor rendering:
both of them ask."""

from __future__ import annotations

from .base import HIGH_SEVERITY_RANK, MEDIUM_SEVERITY_RANK

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
