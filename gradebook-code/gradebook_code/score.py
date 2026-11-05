"""Turning the measurements into a grade."""

from __future__ import annotations

from collections import Counter

from .base import MIN_POINTS_LOST_TO_RECOMMEND, TOP_RECOMMENDATIONS, VERSION, Report, Stats
from .scorers import SCORERS

# -------------------------------------------------------------------- score

DIMENSIONS = [
    ("kiss", "Simplicity (KISS)", 13),
    ("hotspots", "Hotspots (churn x complexity)", 6),
    ("dry", "Duplication (DRY)", 11),
    ("srp", "Single responsibility", 9),
    ("ocp", "Open/closed", 8),
    ("lsp", "Liskov substitution", 5),
    ("isp", "Interface segregation", 6),
    ("dip", "Dependency inversion", 8),
    ("coupling", "Coupling (GRASP)", 9),
    ("cohesion", "Cohesion (GRASP)", 7),
    ("demeter", "Law of Demeter", 5),
    ("yagni", "Speculative generality (YAGNI)", 8),
    ("naming", "Naming & intent", 5),
]
GRADES = [(85, "A"), (70, "B"), (55, "C"), (40, "D"), (0, "F")]


def grade_for(score: float) -> str:
    for floor, letter in GRADES:
        if score >= floor:
            return letter
    return "F"


def evaluate(stats: Stats) -> Report:
    results = []
    weighted = total_weight = 0.0
    for key, title, weight in DIMENSIONS:
        score, detail, advice = SCORERS[key](stats)
        entry = {
            "id": key,
            "title": title,
            "weight": weight,
            "score": score,
            "detail": detail,
            "advice": advice,
        }
        if score is None:
            entry["points"] = entry["lost"] = None
        else:
            entry["points"] = round(score * weight, 1)
            entry["lost"] = round((1 - score) * weight, 1)
            weighted += score * weight
            total_weight += weight
        results.append(entry)
    total = round(weighted / total_weight * 100, 1) if total_weight else 0.0
    return {
        "version": VERSION,
        "root": stats["root"],
        "score": total,
        "grade": grade_for(total),
        "scored_weight": total_weight,
        "not_scored": [r["title"] for r in results if r["score"] is None],
        "dimensions": results,
        "findings": stats["findings"],
        "stats": {k: (dict(v) if isinstance(v, Counter) else v) for k, v in stats.items() if k not in {"findings"}},
    }


def recommendations(report: Report, top: int = TOP_RECOMMENDATIONS) -> list[Stats]:
    ranked = [d for d in report["dimensions"] if d["score"] is not None and d["lost"] >= MIN_POINTS_LOST_TO_RECOMMEND]
    ranked.sort(key=lambda d: d["lost"], reverse=True)
    return ranked[:top]
