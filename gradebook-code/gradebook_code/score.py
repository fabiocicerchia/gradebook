"""Turning the measurements into a grade."""

from __future__ import annotations

from collections import Counter

from .base import MIN_MODULES_FOR_COUPLING, MIN_POINTS_LOST_TO_RECOMMEND, TOP_RECOMMENDATIONS, VERSION, Report, Stats

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


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def penalise(pairs: list[tuple[str, float, float, float]]) -> tuple[float, list[tuple[str, float]]]:
    """Turn (label, ratio, target, weight) tuples into a score and a detail line."""
    penalties = [(label, weight * clamp(ratio / target)) for label, ratio, target, weight in pairs if ratio]
    score = clamp(1 - sum(value for _, value in penalties))
    return score, penalties


def score_kiss(s: Stats) -> tuple[float | None, str, str]:
    functions = s["functions"]
    if not functions:
        return None, "no functions found", ""
    profile = s["profile"]
    score, penalties = penalise(
        [
            (
                f"{s['complex_functions']} over complexity {profile['max_complexity']}",
                s["complex_functions"] / functions,
                0.15,
                0.35,
            ),
            (
                f"{s['long_functions']} over {profile['max_lines']} lines",
                s["long_functions"] / functions,
                0.15,
                0.30,
            ),
            (
                f"{s['deep_functions']} nested deeper than {profile['max_nesting']:g}",
                s["deep_functions"] / functions,
                0.10,
                0.20,
            ),
            (
                f"{s['wide_functions']} with more than {profile['max_params']} parameters",
                s["wide_functions"] / functions,
                0.10,
                0.15,
            ),
        ]
    )
    average = s["complexity_total"] / functions
    detail = f"{average:.1f} average complexity over {functions} functions"
    if penalties:
        detail += ", " + ", ".join(label for label, _ in penalties)
    return (
        score,
        detail,
        (
            "split the worst offenders: a function past ~10 branches or ~40 lines "
            "is doing several things and hiding the seams between them"
        ),
    )


def score_hotspots(s: Stats) -> tuple[float | None, str, str]:
    """Complexity in the files that change most is the complexity that costs."""
    if not s["hot_files"]:
        return None, "no churn history to rank by", ""
    hot, overall = s["hot_complexity"], s["average_complexity"]
    if overall <= 0:
        return None, "no complexity to weigh", ""
    ratio = hot / overall
    score = clamp(1 - (ratio - 1))
    detail = (
        f"the {s['hot_files']} most-changed files average {hot:g} complexity "
        f"against {overall:g} across the codebase ({ratio:.1f}x)"
    )
    return (
        score,
        detail,
        (
            "refactor where the changes land: complexity in a file nobody touches "
            "is a fact, complexity in one that changes weekly is a bill"
        ),
    )


def score_dry(s: Stats) -> tuple[float | None, str, str]:
    if not s["lines"]:
        return None, "no code found", ""
    duplicate_share = s["duplicate_lines"] / s["lines"]
    score, _ = penalise(
        [
            (f"{s['duplicate_lines']} duplicated lines", duplicate_share, 0.05, 0.7),
            (
                f"{s['magic_literals']} repeated magic literals",
                s["magic_literals"] / max(s["files"], 1),
                1.0,
                0.3,
            ),
        ]
    )
    detail = f"{duplicate_share * 100:.1f}% of lines duplicated elsewhere"
    if s["magic_literals"]:
        detail += f", {s['magic_literals']} repeated magic literals"
    return (
        score,
        detail,
        (
            "extract the repeated blocks; duplication is where fixes go to be "
            "applied in three places and forgotten in the fourth"
        ),
    )


def score_srp(s: Stats) -> tuple[float | None, str, str]:
    if not s["files"]:
        return None, "no code found", ""
    score, penalties = penalise(
        [
            (f"{s['god_files']} god file(s)", s["god_files"] / s["files"], 0.10, 0.45),
            (
                f"{s['mixed_concern_files']} file(s) mixing 3+ concerns",
                s["mixed_concern_files"] / s["files"],
                0.10,
                0.35,
            ),
            (
                f"{s['wide_classes']} class(es) with 15+ methods",
                s["wide_classes"] / max(s["classes"], 1),
                0.10,
                0.20,
            ),
        ]
    )
    detail = ", ".join(label for label, _ in penalties) or "no god files, no class doing three jobs"
    return (
        score,
        detail,
        (
            "give each module one reason to change: split the files that hold a "
            "subsystem, and move I/O out of the ones that hold rules"
        ),
    )


def score_ocp(s: Stats) -> tuple[float | None, str, str]:
    if not s["functions"]:
        return None, "no functions found", ""
    score, penalties = penalise(
        [
            (
                f"{s['type_switches']} branch(es) on a type or kind field",
                s["type_switches"] / s["functions"],
                0.10,
                0.55,
            ),
            (
                f"{s['type_checks']} runtime type check(s)",
                s["type_checks"] / s["functions"],
                0.10,
                0.45,
            ),
        ]
    )
    detail = ", ".join(label for label, _ in penalties) or "no type-branching found"
    return (
        score,
        detail,
        (
            "replace the type switches with polymorphism: every new case should "
            "add a class, not another branch in the same three functions"
        ),
    )


def score_lsp(s: Stats) -> tuple[float | None, str, str]:
    if not s["subclasses"]:
        return None, "no inheritance to judge", ""
    score, penalties = penalise(
        [
            (
                f"{s['stub_overrides']} unimplemented override(s)",
                s["stub_overrides"] / s["subclasses"],
                0.15,
                0.6,
            ),
            (
                f"{s['type_checks']} runtime type check(s) around them",
                s["type_checks"] / max(s["subclasses"], 1),
                0.5,
                0.4,
            ),
        ]
    )
    detail = f"{s['subclasses']} subclass(es)"
    if penalties:
        detail += ", " + ", ".join(label for label, _ in penalties)
    return (
        score,
        detail,
        (
            "a subclass that throws NotImplementedError is not substitutable — "
            "split the base type instead of narrowing it"
        ),
    )


def score_isp(s: Stats) -> tuple[float | None, str, str]:
    if not s["interfaces"]:
        return None, "no interfaces or protocols declared", ""
    score, penalties = penalise(
        [
            (
                f"{s['fat_interfaces']} interface(s) with 8+ methods",
                s["fat_interfaces"] / s["interfaces"],
                0.20,
                1.0,
            ),
        ]
    )
    detail = f"{s['interfaces']} interface(s)"
    if penalties:
        detail += ", " + ", ".join(label for label, _ in penalties)
    else:
        detail += ", none oversized"
    return (
        score,
        detail,
        (
            "split the wide interfaces: a client forced to implement methods it "
            "never calls is coupled to code it does not use"
        ),
    )


def score_dip(s: Stats) -> tuple[float | None, str, str]:
    if not s["files"]:
        return None, "no code found", ""
    spread = s["infra_files"] / s["files"]
    score, _ = penalise(
        [
            (
                f"{s['infra_files']}/{s['files']} files reach infrastructure directly",
                spread,
                0.30,
                0.6,
            ),
            (f"{s['global_state']} mutable global(s)", s["global_state"] / s["files"], 0.20, 0.4),
        ]
    )
    detail = f"{spread * 100:.0f}% of files touch a database, HTTP client or filesystem directly"
    if s["global_state"]:
        detail += f", {s['global_state']} mutable global(s)"
    return (
        score,
        detail,
        (
            "concentrate infrastructure behind a few adapters and inject it, so "
            "the rules can be read and tested without a database"
        ),
    )


def score_coupling(s: Stats) -> tuple[float | None, str, str]:
    if s["modules"] < MIN_MODULES_FOR_COUPLING:
        return None, "too few modules to judge", ""
    fan_out = s["fan_out_total"] / s["modules"]
    score, _ = penalise(
        [
            (f"{len(s['cycles'])} import cycle(s)", len(s["cycles"]) / s["modules"], 0.05, 0.6),
            (f"{fan_out:.1f} average internal imports per module", fan_out, 8.0, 0.4),
        ]
    )
    detail = f"{fan_out:.1f} internal imports per module"
    if s["cycles"]:
        detail += f", {len(s['cycles'])} cycle(s)"
    return (
        score,
        detail,
        (
            "break the import cycles first — they are the coupling that stops any "
            "module being understood, tested or moved on its own"
        ),
    )


def score_cohesion(s: Stats) -> tuple[float | None, str, str]:
    if not s["cohesion_classes"]:
        return None, "no classes with shared state to judge", ""
    share = s["cohesion_score"] / s["cohesion_classes"]
    detail = f"{share * 100:.0f}% of methods use their object's own state"
    return (
        clamp(share / 0.8),
        detail,
        ("methods that never touch their object's fields belong somewhere else — usually next to the data they do use"),
    )


def score_demeter(s: Stats) -> tuple[float | None, str, str]:
    if not s["lines"]:
        return None, "no code found", ""
    per_hundred = s["demeter_chains"] / (s["lines"] / 100)
    score = clamp(1 - clamp(per_hundred / 3.0))
    detail = f"{s['demeter_chains']} chains of 3+ dots ({per_hundred:.1f} per 100 lines)"
    return (
        score,
        detail,
        (
            "a.b.c.d ties the caller to the shape of things it does not own — ask "
            "the neighbour for what you need instead of reaching through it"
        ),
    )


def score_yagni(s: Stats) -> tuple[float | None, str, str]:
    if not s["functions"]:
        return None, "no functions found", ""
    score, penalties = penalise(
        [
            (
                f"{s['dead_symbols']} unreferenced private symbol(s)",
                s["dead_symbols"] / s["functions"],
                0.05,
                0.35,
            ),
            (
                f"{s['single_impl_interfaces']} abstraction(s) with one implementer",
                s["single_impl_interfaces"] / max(s["classes"], 1),
                0.20,
                0.25,
            ),
            (f"{s['stubs']} unimplemented stub(s)", s["stubs"] / s["functions"], 0.05, 0.20),
            (
                f"{s['commented_code']} block(s) of commented-out code",
                s["commented_code"] / max(s["files"], 1),
                1.0,
                0.10,
            ),
            (f"{s['todos']} TODO/FIXME marker(s)", s["todos"] / max(s["files"], 1), 2.0, 0.10),
        ]
    )
    detail = ", ".join(label for label, _ in penalties) or "no dead code or unused abstraction"
    return (
        score,
        detail,
        (
            "delete what nothing calls and collapse the abstractions with a single "
            "implementer — they cost reading time and buy nothing yet"
        ),
    )


def score_naming(s: Stats) -> tuple[float | None, str, str]:
    if not s["named_things"]:
        return None, "nothing named to judge", ""
    share = s["vague_names"] / s["named_things"]
    score = clamp(1 - clamp(share / 0.15))
    detail = f"{s['vague_names']}/{s['named_things']} vague names (manager, helper, data, process, …)"
    if s["flag_params"]:
        score = clamp(score - 0.15 * clamp((s["flag_params"] / s["functions"]) / 0.10))
        detail += f", {s['flag_params']} boolean flag parameter(s)"
    return (
        score,
        detail,
        (
            "name things for what they are: a Manager or a Helper is a class "
            "nobody could describe, and a boolean parameter hides two functions"
        ),
    )


SCORERS = {
    "kiss": score_kiss,
    "hotspots": score_hotspots,
    "dry": score_dry,
    "srp": score_srp,
    "ocp": score_ocp,
    "lsp": score_lsp,
    "isp": score_isp,
    "dip": score_dip,
    "coupling": score_coupling,
    "cohesion": score_cohesion,
    "demeter": score_demeter,
    "yagni": score_yagni,
    "naming": score_naming,
}


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
