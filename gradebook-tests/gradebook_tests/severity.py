"""Which findings count as which severity. Neither collection nor rendering:
both of them ask."""

from __future__ import annotations

from .base import HIGH_SEVERITY_RANK, MEDIUM_SEVERITY_RANK

# Findings arrive from `collect` already in this order.
FLAG_ORDER = {
    "phantom-symbol": 0,
    "suppressed-failure": 1,
    "untested-hotspot": 2,
    "mirror-assertion": 3,
    "conjoined-twin": 4,
    "decorative-test": 5,
    "implementation-access": 6,
    "brittle-selector": 7,
    "duplicate-case": 8,
    "stale-test": 9,
}


def severity_for(kind: str) -> str:
    """One ranking, three buckets — editors read this, they don't re-derive it."""
    rank = FLAG_ORDER.get(kind, 9)
    if rank <= HIGH_SEVERITY_RANK:
        return "high"
    return "medium" if rank <= MEDIUM_SEVERITY_RANK else "low"
