"""The dimensions, the evaluation, and the recommendations that follow."""

from __future__ import annotations

from pathlib import Path

from .base import (
    ARTIFACT_DIRS,
    BUSY_DOUBLE_DENSITY,
    E2E_CEILING,
    E2E_TARGET,
    E2E_TOLERANCE,
    FIX_COMMIT_SHARE,
    HEAVY_SETUP_LINES,
    INTEGRATION_CEILING,
    INTEGRATION_FLOOR,
    INTEGRATION_SPARSE,
    INTEGRATION_TARGET,
    MANY_CASES,
    MIN_POINTS_LOST_TO_RECOMMEND,
    MIN_SOURCE_COMMITS_FOR_TDD,
    MIRRORED_NAME_SHARE,
    SKIP_DIRS,
    TOP_RECOMMENDATIONS,
    UNIT_FLOOR,
    UNIT_SPARSE,
    VERSION,
    Report,
    Stats,
)
from .collect import collect

# -------------------------------------------------------------------- score

# The twelve base dimensions add up to 100. "Mutation score" is scored only
# when a mutation report exists; when it does, every weight renormalises.
DIMENSIONS = [
    ("coverage", "Coverage", 12),
    ("mutation", "Mutation score", 8),
    ("unit", "Unit tests", 9),
    ("integration", "Integration tests", 7),
    ("e2e", "Functional / E2E", 6),
    ("pyramid", "Suite shape", 4),
    ("tdd", "TDD discipline", 7),
    ("assertions", "Assertion quality", 7),
    ("failure", "Edge & failure paths", 5),
    ("risk", "Risk targeting", 5),
    ("substance", "Test substance", 6),
    ("determinism", "Determinism & isolation", 6),
    ("focus", "Test focus", 5),
    ("naming", "Test naming", 5),
    ("doubles", "Test doubles", 6),
    ("hygiene", "Suite hygiene", 4),
    ("bdd", "BDD / behaviour specs", 2),
    ("ci", "CI enforcement", 4),
]
GRADES = [(85, "A"), (70, "B"), (55, "C"), (40, "D"), (0, "F")]


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def score_coverage(s: Stats) -> tuple[float | None, str, str]:
    """0.25 for tooling, 0.20 for a gate, 0.55 for what is actually covered."""
    configured = bool(s["coverage_config"]) or s["ci_coverage"]
    threshold = s["coverage_threshold"]
    measured = s["coverage_measured"]
    gate = threshold is not None or (s["ci_coverage"] and s["ci_strict"])
    if not configured and measured is None:
        return (
            0.0,
            "no coverage tooling detected",
            "wire up a coverage tool (pytest-cov, nyc, go -coverprofile, jacoco) and publish it",
        )
    score = 0.25 + (0.20 if gate else 0.0)
    if measured is not None:
        score += 0.55 * clamp(measured / 85.0)
        detail = f"measured {measured}% ({s['coverage_source']})"
    elif threshold is not None:
        # A declared bar is worth less than a measured result.
        score += 0.55 * 0.6 * clamp(threshold / 85.0)
        detail = "declared only, no report committed"
    else:
        detail = "tooling present, no threshold, no report"
    if threshold is not None:
        detail += f", gate {threshold}%"
    if s["mutation_testing"]:
        score = clamp(score + 0.05)
        detail += ", mutation testing"
    advice = "raise measured line coverage towards 85% and fail the build under a threshold"
    if measured is None:
        advice = "publish a coverage report (lcov/cobertura/coverage.out) and gate CI on it"
    return clamp(score), detail, advice


def score_unit(s: Stats) -> tuple[float | None, str, str]:
    source = s["source_files"]
    if source == 0:
        return None, "no source files found", ""
    files = s["kind_files"]["unit"]
    cases = s["kind_cases"]["unit"]
    # Files, cases and volume: a repo can have a test file per module and still
    # have written 20 lines of test against 2,000 lines of code.
    profile = s["profile"]
    ratio = (s["test_lines"] / s["source_lines"]) if s["source_lines"] else 0
    score = (
        0.4 * clamp((files / source) / 0.4)
        + 0.35 * clamp((cases / source) / profile["cases_per_source"])
        + 0.25 * clamp(ratio / profile["test_code_ratio"])
    )
    detail = f"{files} file(s), {cases} case(s) for {source} source files"
    if s["source_lines"]:
        detail += f", {ratio:.2f}x test:code lines (target {profile['test_code_ratio']:.2f}x)"
    return (
        score,
        detail,
        (
            f"add unit tests: ~1 test file per 2-3 source files, "
            f"~{profile['cases_per_source']:.1f} cases per source file and "
            f"~{profile['test_code_ratio']:.2f} lines of test per line of code "
            f"for {'/'.join(profile['languages']) or 'this stack'}"
        ),
    )


def score_layer(s: Stats, kind: str, target_share: float, label: str, advice: str) -> tuple[float | None, str, str]:
    cases = s["kind_cases"][kind]
    files = s["kind_files"][kind]
    if not cases and not files:
        return 0.0, "none found", advice
    share = cases / max(s["cases"], 1)
    # Share of the suite, tempered by absolute size: one token test is not a layer.
    score = clamp(0.35 + 0.65 * clamp(share / target_share)) * (0.6 + 0.4 * clamp(cases / 5))
    detail = f"{files} file(s), {cases} case(s) ({share * 100:.0f}% of all cases)"
    return score, detail, f"grow the {label} layer — {advice}"


def score_tdd(s: Stats) -> tuple[float | None, str, str]:
    git = s["git"]
    if not git:
        return None, "no git history available", ""
    source_commits = git["source_commits"]
    if source_commits < MIN_SOURCE_COMMITS_FOR_TDD:
        return None, f"only {source_commits} source commit(s) — not enough signal", ""
    ratio = git["source_commits_with_tests"] / source_commits
    test_only = git["test_only_commits"] / max(git["commits_analysed"], 1)
    fixes = git["fix_commits"]
    fix_ratio = (git["fix_commits_with_tests"] / fixes) if fixes else None
    regression = clamp(fix_ratio / 0.8) if fix_ratio is not None else clamp(ratio / 0.6)
    score = 0.7 * clamp(ratio / 0.6) + 0.1 * clamp(test_only / 0.05) + 0.2 * regression
    detail = (
        f"{ratio * 100:.0f}% of {source_commits} source commits also touched tests "
        f"({git['test_only_commits']} test-only)"
    )
    advice = "ship tests in the same commit as the code they cover — aim for 60%+ of source commits touching tests"
    if fixes:
        detail += f", {git['fix_commits_with_tests']}/{fixes} bugfixes shipped a test"
        if fix_ratio < FIX_COMMIT_SHARE:
            advice = (
                f"{fixes - git['fix_commits_with_tests']} of {fixes} bugfix commits shipped "
                "no test — a fix without a regression test is a bug free to come back"
            )
    return clamp(score), detail, advice


def score_assertions(s: Stats) -> tuple[float | None, str, str]:
    cases = s["cases"]
    if cases == 0:
        return 0.0, "no test cases detected", "write tests that assert something"
    density = s["assertions"] / cases
    silent = s["cases_without_assertions"] / cases
    weak_only = s["weak_only_cases"] / cases
    # A case that asserts nothing cannot fail for the right reason, and one that
    # only asserts truthy/not-null barely can; density matters least (a single
    # focused assertion per case is fine).
    effective = clamp(1 - silent - 0.6 * weak_only)
    score = 0.25 * clamp(density / 2.0) + 0.75 * effective
    uninformative = 0
    if s["profile"]["bare_assert_check"] and s["uninformative_assertions"]:
        # Frameworks that print the compared values make this a non-issue; the
        # rest leave you with "expected true, got false".
        uninformative = s["uninformative_assertions"] / cases
        score = clamp(score - 0.25 * clamp(uninformative / 0.20))
    detail = f"{density:.1f} assertions/case"
    if s["cases_without_assertions"]:
        detail += f", {s['cases_without_assertions']} case(s) assert nothing"
    if s["weak_only_cases"]:
        detail += f", {s['weak_only_cases']} assert only truthy/not-null/snapshot"
    if uninformative:
        detail += f", {s['uninformative_assertions']} report no values on failure"
    if not s["cases_without_assertions"] and not s["weak_only_cases"] and not uninformative:
        detail += ", every case asserts a value"
    if silent >= weak_only:
        advice = "assert on behaviour: tests that only exercise code without asserting cannot fail for the right reason"
    else:
        advice = (
            f"{s['weak_only_cases']} case(s) only assert truthiness or not-null — "
            "assert the value you expect, so a wrong value fails the test"
        )
    if uninformative > max(silent, weak_only):
        advice = (
            f"{s['uninformative_assertions']} assertion(s) print nothing useful when they "
            "fail — compare values, or pass a message saying what was expected"
        )
    return score, detail, advice


def score_failure_paths(s: Stats) -> tuple[float | None, str, str]:
    """Regressions escape through the error paths and the boundaries."""
    cases = s["cases"]
    if cases == 0:
        return None, "no test cases detected", ""
    error_share = s["error_cases"] / cases
    boundary_share = s["boundary_cases"] / cases
    score = 0.75 * clamp(error_share / 0.25) + 0.25 * clamp(boundary_share / 0.20)
    detail = (
        f"{s['error_cases']}/{cases} cases ({error_share * 100:.0f}%) exercise a failure "
        f"path, {s['boundary_cases']} ({boundary_share * 100:.0f}%) touch a boundary value"
    )
    if error_share <= boundary_share:
        advice = (
            "test what happens when things go wrong: invalid input, timeouts, denied "
            "permissions, missing records — aim for ~25% of cases"
        )
    else:
        advice = (
            "test the boundaries as well as the middle: empty, zero, negative, null, "
            "maximum — that is where the off-by-ones live"
        )
    return score, detail, advice


def score_mutation(s: Stats) -> tuple[float | None, str, str]:
    """The only direct evidence that the suite kills bugs — scored when present."""
    measured = s["mutation_measured"]
    if measured is None:
        return None, "no mutation report found", ""
    score = clamp(measured / 80.0)
    detail = f"{measured}% of mutants killed ({s['mutation_source']})"
    return (
        score,
        detail,
        ("survived mutants are code paths a bug could change without any test noticing — kill them or delete the code"),
    )


def score_pyramid(s: Stats) -> tuple[float | None, str, str]:
    """The test pyramid's shape: unit-only, integration-only and ice-cream cone."""
    unit = s["kind_cases"]["unit"]
    integration = s["kind_cases"]["integration"] + s["kind_cases"]["contract"]
    e2e = s["kind_cases"]["e2e"]
    total = unit + integration + e2e
    if total == 0:
        return None, "no classified test cases", ""
    unit_share, integration_share, e2e_share = (unit / total, integration / total, e2e / total)
    # Healthy: unit-heavy base, a real integration band, a thin E2E tip.
    unit_term = clamp(unit_share / 0.5)
    integration_term = (
        clamp(integration_share / INTEGRATION_TARGET) if integration_share <= INTEGRATION_CEILING else 1.0
    )
    e2e_term = 1.0 if e2e_share <= E2E_TARGET else clamp(1 - (e2e_share - E2E_TARGET) / E2E_TOLERANCE)
    score = 0.4 * unit_term + 0.3 * integration_term + 0.3 * e2e_term
    if e2e_share > E2E_CEILING:
        shape = "ice-cream cone — E2E heavy"
    elif unit_share >= UNIT_FLOOR and integration_share >= INTEGRATION_FLOOR:
        shape = "healthy pyramid"
    elif integration_share < INTEGRATION_SPARSE:
        shape = "unit tests without integration tests"
    elif unit_share < UNIT_SPARSE:
        shape = "integration tests without a unit base"
    else:
        shape = "lopsided"
    detail = (
        f"{unit_share * 100:.0f}/{integration_share * 100:.0f}/{e2e_share * 100:.0f} unit/integration/E2E — {shape}"
    )
    return (
        score,
        detail,
        (
            "rebalance towards a broad unit base, a real integration band and a "
            "thin E2E tip — slow layers should be the smallest"
        ),
    )


def score_determinism(s: Stats) -> tuple[float | None, str, str]:
    """Flakiness and environment coupling: the Butterfly, the Local Hero, Chain Gang."""
    cases = s["cases"]
    if cases == 0:
        return None, "no test cases detected", ""
    penalties = []
    for count, share, label, weight in (
        (s["unfrozen_time"], 0.10, "unfrozen clock reads", 0.30),
        (s["unseeded_random"], 0.10, "unseeded randomness", 0.20),
        (s["env_coupling"], 0.05, "host/path/URL coupling", 0.25),
        (s["order_dependent"], 0.05, "order-dependent or shared state", 0.15),
        (s["sleeps"], 0.10, "hard-coded sleeps", 0.20),
        (s["brittle_selectors"], 0.10, "brittle locators", 0.20),
        (s["platform_branches"], 0.05, "platform-specific branches", 0.15),
    ):
        if count:
            penalties.append((f"{count} {label}", weight * clamp((count / cases) / share)))
    if s["serial_only"]:
        penalties.append(("pinned to a single worker", 0.15))
    score = clamp(1 - sum(p for _, p in penalties))
    if penalties:
        detail = ", ".join(label for label, _ in penalties)
        advice = (
            "freeze the clock, seed the randomness, inject hosts and paths, and let cases "
            "run in any order — these are the tests that fail on someone else's machine"
        )
    else:
        detail = "no clock, randomness, host or ordering dependencies"
        advice = "keep tests deterministic and independently runnable"
    return score, detail, advice


def score_focus(s: Stats) -> tuple[float | None, str, str]:
    """One case, one behaviour: the Giant, the Eager Test, Assertion Roulette."""
    cases = s["cases"]
    if cases == 0:
        return None, "no test cases detected", ""
    penalties = []
    if s["giant_cases"]:
        penalties.append(
            (
                f"{s['giant_cases']} case(s) over 50 lines",
                0.35 * clamp((s["giant_cases"] / cases) / 0.10),
            )
        )
    if s["branching_cases"]:
        penalties.append(
            (
                f"{s['branching_cases']} case(s) with if/switch logic",
                0.30 * clamp((s["branching_cases"] / cases) / 0.10),
            )
        )
    if s["roulette_cases"]:
        penalties.append(
            (
                f"{s['roulette_cases']} case(s) with 10+ assertions",
                0.25 * clamp((s["roulette_cases"] / cases) / 0.10),
            )
        )
    if s["setup_lines"] > HEAVY_SETUP_LINES:
        penalties.append((f"{s['setup_lines']}-line setup block", 0.10 * clamp((s["setup_lines"] - 30) / 50)))
    score = clamp(1 - sum(p for _, p in penalties))
    detail = ", ".join(label for label, _ in penalties) or "cases are small, linear and focused"
    return (
        score,
        detail,
        (
            "split giant cases and drop branching: a test with an `if` does not "
            "test one thing, and half of it may never run"
        ),
    )


def score_risk(s: Stats) -> tuple[float | None, str, str]:
    """Are the files that change most often the ones under test?"""
    if not s["hot_files"]:
        return None, "no churn history to rank by", ""
    hot = s["hot_files"]
    tested = hot - s["untested_hot_files"]
    score = 0.6 * (tested / hot) if s["hot_coverage"] is not None else tested / hot
    detail = f"{tested}/{hot} of the most-changed files have tests"
    if s["hot_coverage"] is not None:
        score += 0.4 * clamp(s["hot_coverage"] / 85.0)
        detail += f", {s['hot_coverage']}% covered"
    advice = "test the code that changes most: churn is the best available proxy for where the next bug will be"
    return clamp(score), detail, advice


def score_substance(s: Stats) -> tuple[float | None, str, str]:
    """Is there a real test behind each case, or just something shaped like one?"""
    cases = s["cases"]
    if cases == 0:
        return None, "no test cases detected", ""
    paired = max(s["paired_tests"], 1)
    penalties = []
    if s["duplicate_cases"]:
        penalties.append(
            (
                f"{s['duplicate_cases']} duplicate case(s)",
                0.30 * clamp((s["duplicate_cases"] / cases) / 0.25),
                (
                    f"{s['duplicate_cases']} case(s) are copies of another case with different "
                    "literals — parametrise them and spend the time on an untested path"
                ),
            )
        )
    if s["suppressed_failures"]:
        penalties.append(
            (
                f"{s['suppressed_failures']} suppressed failure(s)",
                0.25 * clamp((s["suppressed_failures"] / cases) / 0.05),
                (
                    f"{s['suppressed_failures']} assertion(s) cannot fail: commented out, swallowed "
                    "by an empty except/catch, or skipped with no reason"
                ),
            )
        )
    if s["phantom_symbols"]:
        penalties.append(
            (
                f"{s['phantom_symbols']} phantom symbol(s)",
                0.20 * clamp(s["phantom_symbols"] / 3),
                (
                    f"{s['phantom_symbols']} test import(s) name code no source file defines — "
                    "those tests never ran against this repo"
                ),
            )
        )
    if s["private_access"]:
        penalties.append(
            (
                f"{s['private_access']} private-member access(es)",
                0.15 * clamp((s["private_access"] / cases) / 0.10),
                (
                    f"{s['private_access']} case(s) reach into internals — assert on what the unit "
                    "does, or the next refactor breaks the test without breaking the code"
                ),
            )
        )
    if s["mirror_assertions"]:
        penalties.append(
            (
                f"{s['mirror_assertions']} mirrored expectation(s)",
                0.15 * clamp((s["mirror_assertions"] / cases) / 0.10),
                (
                    f"{s['mirror_assertions']} assertion(s) recompute the expected value from the "
                    "inputs — write the answer down as a literal so a wrong formula fails"
                ),
            )
        )
    if s["conjoined_files"]:
        penalties.append(
            (
                f"{s['conjoined_files']} unit test(s) doing real I/O",
                0.15 * clamp(s["conjoined_files"] / 5),
                (
                    f"{s['conjoined_files']} file(s) filed as unit tests talk to a real database, "
                    "HTTP service or browser — move them to the integration suite so the fast "
                    "suite stays fast and honest"
                ),
            )
        )
    if s["stale_tests"]:
        penalties.append(
            (
                f"{s['stale_tests']} stale test file(s)",
                0.15 * clamp((s["stale_tests"] / paired) / 0.3),
                (
                    f"{s['stale_tests']} test file(s) never changed while the code they cover kept "
                    "churning — they no longer describe it"
                ),
            )
        )
    if s["decorative_tests"]:
        penalties.append(
            (
                f"{s['decorative_tests']} decorative test file(s)",
                0.10 * clamp((s["decorative_tests"] / paired) / 0.3),
                (
                    f"{s['decorative_tests']} module(s) have a test file and almost no coverage — "
                    "the test exercises nearly nothing"
                ),
            )
        )
    score = clamp(1 - sum(p for _, p, _ in penalties))
    if penalties:
        detail = ", ".join(label for label, _, _ in penalties)
        advice = max(penalties, key=lambda p: p[1])[2]
    else:
        detail = "no duplicate, suppressed, phantom or stale tests found"
        advice = "keep cases distinct and let every assertion be able to fail"
    return score, detail, advice


def score_naming(s: Stats) -> tuple[float | None, str, str]:
    """Do the names say what behaviour is expected, or just that a thing exists?"""
    total = s["test_names"]
    if not total:
        return None, "no test names could be extracted", ""
    descriptive = s["descriptive_names"] / total
    conditional = s["conditional_names"] / total
    placeholder = s["placeholder_names"] / total
    average_words = s["name_words"] / total
    mirrored = s["method_mirror_names"] / total
    score = clamp(
        0.6 * clamp(descriptive / 0.9)
        + 0.4 * clamp(conditional / 0.5)
        - 0.3 * placeholder
        - 0.2 * clamp(mirrored / 0.5)
    )
    detail = (
        f"{average_words:.1f} words/name, {descriptive * 100:.0f}% describe behaviour, "
        f"{conditional * 100:.0f}% state a condition"
    )
    if s["placeholder_names"]:
        detail += f", {s['placeholder_names']} placeholder"
    if s["method_mirror_names"]:
        detail += f", {s['method_mirror_names']} named after a method"
    advice = 'name the behaviour, not the subject: "<unit> <expected result> when <condition>"'
    if mirrored > MIRRORED_NAME_SHARE:
        advice = (
            f"{s['method_mirror_names']} test(s) are named after the method they call — "
            "one test per method mirrors the code instead of describing what it should do"
        )
    samples = [n for n in s["bad_names"] if n][:3]
    if samples:
        advice += " — start with " + ", ".join(samples)
    return score, detail, advice


def _doubles_advice(s: Stats, *, density: float, unmocked_layer: int) -> str:
    """The one thing worth changing about this suite's doubles, worst first."""
    if s["mock_only_cases"]:
        return (
            f"{s['mock_only_cases']} case(s) only verify that a double was called — "
            "assert on the returned value or the resulting state instead"
        )
    if density > BUSY_DOUBLE_DENSITY:
        return "trim doubles back to real seams; a case wiring several doubles mostly tests its own wiring"
    if not s["double_cleanup"]:
        return "reset or restore doubles between cases so state cannot leak"
    if not unmocked_layer:
        return (
            "every collaborator is doubled and no integration test exercises the real "
            "one — the bugs live in that interaction, and nothing here would see them"
        )
    return "keep doubles at the edges and let the rest of the suite run real code"


def score_doubles(s: Stats) -> tuple[float | None, str, str]:
    """Are mocks, stubs and spies used at real seams, or is the suite testing itself?"""
    cases = s["cases"]
    if cases == 0:
        return None, "no test cases detected", ""
    doubles = s["doubles"]
    if doubles == 0:
        return (
            0.9,
            "no test doubles — nothing is faked",
            "double only the slow or nondeterministic seams (clock, network, payments)",
        )
    with_doubles = s["cases_with_doubles"]
    tautological = s["mock_only_cases"] / max(with_doubles, 1)
    density = doubles / max(with_doubles, 1)
    saturation = with_doubles / cases
    penalty = (
        0.45 * tautological  # asserts only that a mock was called
        + 0.25 * clamp((density - 3) / 5)  # a case wiring 5+ doubles tests wiring
        + 0.20 * clamp((saturation - 0.6) / 0.4)
    )  # almost nothing real left to break
    if not s["double_cleanup"]:
        penalty += 0.10
    unmocked_layer = s["kind_cases"]["integration"] + s["kind_cases"]["e2e"]
    if not unmocked_layer:
        # Nothing anywhere exercises the real collaborator the doubles stand in for.
        penalty += 0.15
    score = clamp(1 - penalty)
    kinds = "/".join(sorted(s["double_kinds"]))
    if with_doubles:
        detail = f"{doubles} double(s) in {with_doubles}/{cases} cases ({kinds})"
    else:
        detail = f"{doubles} double(s), all in fixtures/setup ({kinds})"
    if s["mock_only_cases"]:
        detail += f", {s['mock_only_cases']} assert only on the double"
    if not s["double_cleanup"]:
        detail += ", no reset/restore"
    return score, detail, _doubles_advice(s, density=density, unmocked_layer=unmocked_layer)


def score_hygiene(s: Stats) -> tuple[float | None, str, str]:
    cases = s["cases"]
    if cases == 0:
        return 0.0, "no test cases detected", "write some tests first"
    penalties = []
    skip_ratio = s["skips"] / cases
    if skip_ratio:
        penalties.append(("skipped/xfailed tests", 0.4 * clamp(skip_ratio / 0.10)))
    if s["focused"]:
        penalties.append((".only/fdescribe focus left in", 0.30))
    if s["chatter"]:
        penalties.append(("console chatter instead of assertions", 0.15 * clamp((s["chatter"] / cases) / 0.20)))
    if cases > MANY_CASES and not s["flag_files"]["parametrized"]:
        penalties.append(("no parametrised/table-driven tests", 0.10))
    score = clamp(1.0 - sum(p for _, p in penalties))
    if penalties:
        detail = ", ".join(f"{name} (-{value * 100:.0f}%)" for name, value in penalties)
    else:
        detail = f"{cases} cases, no skips, no focused tests"
    return (
        score,
        detail,
        ("un-skip or delete dead tests, drop .only, and table-drive repetitive cases"),
    )


def score_bdd(s: Stats) -> tuple[float | None, str, str]:
    total = max(s["cases"], 1)
    scenarios = s["bdd_cases"]
    features = s["feature_files"]
    spec_style = s["spec_cases"]
    if not scenarios and not features and not spec_style:
        return (
            0.0,
            "no behaviour specs found",
            "describe behaviour in the domain's language (Gherkin features, or spec-style tests)",
        )
    if scenarios or features:
        score = clamp(0.6 + 0.4 * clamp((scenarios / total) / 0.05))
        detail = f"{features} feature file(s), {scenarios} Gherkin-style case(s)"
        advice = "cover more critical behaviour with executable specs"
    else:
        # describe/it is a weak BDD signal in most stacks, but it *is* the
        # ecosystem's own idiom in RSpec/Jasmine-style suites.
        ceiling = 0.8 if s["profile"]["spec_style_idiomatic"] else 0.55
        score = clamp(ceiling * clamp((spec_style / total) / 0.30))
        detail = f"spec-style only ({spec_style} describe/it case(s)), no Gherkin"
        advice = (
            "write the critical journeys as Given/When/Then specs the business can read "
            "(cucumber, behave, pytest-bdd, godog)"
        )
    return score, detail, advice


def score_ci(s: Stats) -> tuple[float | None, str, str]:
    if not s["ci_files"]:
        return 0.0, "no CI configuration found", "run the suite on every push/PR"
    score = 0.0
    bits = []
    if s["ci_runs_tests"]:
        score += 0.6
        bits.append("runs tests")
    if s["ci_coverage"]:
        score += 0.25
        bits.append("collects coverage")
    if s["ci_strict"]:
        score += 0.15
        bits.append("matrix/strict flags")
    detail = f"{len(s['ci_files'])} config(s): " + (", ".join(bits) or "no test invocation found")
    return clamp(score), detail, "make CI run the suite, collect coverage and fail on regressions"


SCORERS = {
    "coverage": score_coverage,
    "unit": score_unit,
    "integration": lambda s: score_layer(
        s,
        "integration",
        0.12,
        "integration",
        "test real collaborators (db, queue, http) rather than mocks only",
    ),
    "e2e": lambda s: score_layer(s, "e2e", 0.07, "functional/E2E", "cover the critical user journeys end to end"),
    "tdd": score_tdd,
    "assertions": score_assertions,
    "failure": score_failure_paths,
    "risk": score_risk,
    "pyramid": score_pyramid,
    "determinism": score_determinism,
    "focus": score_focus,
    "substance": score_substance,
    "mutation": score_mutation,
    "naming": score_naming,
    "doubles": score_doubles,
    "hygiene": score_hygiene,
    "bdd": score_bdd,
    "ci": score_ci,
}


def grade_for(score: float) -> str:
    for floor, letter in GRADES:
        if score >= floor:
            return letter
    return "F"


def evaluate(stats: Stats) -> Report:
    results = []
    weighted = 0.0
    total_weight = 0.0
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
            entry["points"] = None
            entry["lost"] = 0.0
        else:
            entry["points"] = round(score * weight, 1)
            entry["lost"] = round((1 - score) * weight, 1)
            weighted += score * weight
            total_weight += weight
        results.append(entry)
    total = round(weighted / total_weight * 100, 1) if total_weight else 0.0
    skipped = [r["title"] for r in results if r["score"] is None]
    return {
        "version": VERSION,
        "root": stats["root"],
        "score": total,
        "grade": grade_for(total),
        "scored_weight": total_weight,
        "not_scored": skipped,
        "dimensions": results,
        "findings": stats["findings"],
        "stats": {
            "source_files": stats["source_files"],
            "test_files": stats["test_files"],
            "test_cases": stats["cases"],
            "assertions": stats["assertions"],
            "cases_without_assertions": stats["cases_without_assertions"],
            "skipped_markers": stats["skips"],
            "focused_markers": stats["focused"],
            "sleeps": stats["sleeps"],
            "duplicate_cases": stats["duplicate_cases"],
            "suppressed_failures": stats["suppressed_failures"],
            "phantom_symbols": stats["phantom_symbols"],
            "stale_tests": stats["stale_tests"],
            "decorative_tests": stats["decorative_tests"],
            "paired_tests": stats["paired_tests"],
            "weak_assertions": stats["weak_assertions"],
            "weak_only_cases": stats["weak_only_cases"],
            "error_cases": stats["error_cases"],
            "boundary_cases": stats["boundary_cases"],
            "serial_only": stats["serial_only"],
            "profile": stats["profile"],
            "language_lines": dict(stats["language_lines"].most_common()),
            "uninformative_assertions": stats["uninformative_assertions"],
            "source_lines": stats["source_lines"],
            "test_lines": stats["test_lines"],
            "test_to_code_ratio": (
                round(stats["test_lines"] / stats["source_lines"], 2) if stats["source_lines"] else None
            ),
            "method_mirror_names": stats["method_mirror_names"],
            "hot_files": stats["hot_files"],
            "untested_hot_files": stats["untested_hot_files"],
            "hot_coverage": stats["hot_coverage"],
            "conjoined_files": stats["conjoined_files"],
            "chatter": stats["chatter"],
            "platform_branches": stats["platform_branches"],
            "mirror_assertions": stats["mirror_assertions"],
            "brittle_selectors": stats["brittle_selectors"],
            "private_access": stats["private_access"],
            "giant_cases": stats["giant_cases"],
            "roulette_cases": stats["roulette_cases"],
            "branching_cases": stats["branching_cases"],
            "setup_lines": stats["setup_lines"],
            "unfrozen_time": stats["unfrozen_time"],
            "unseeded_random": stats["unseeded_random"],
            "env_coupling": stats["env_coupling"],
            "order_dependent": stats["order_dependent"],
            "mutation_measured": stats["mutation_measured"],
            "mutation_source": stats["mutation_source"],
            "doubles": stats["doubles"],
            "cases_with_doubles": stats["cases_with_doubles"],
            "mock_only_cases": stats["mock_only_cases"],
            "double_kinds": sorted(stats["double_kinds"]),
            "double_cleanup": stats["double_cleanup"],
            "test_names": stats["test_names"],
            "descriptive_names": stats["descriptive_names"],
            "conditional_names": stats["conditional_names"],
            "placeholder_names": stats["placeholder_names"],
            "worst_names": stats["bad_names"][:10],
            "feature_files": stats["feature_files"],
            "gherkin_cases": stats["bdd_cases"],
            "spec_style_cases": stats["spec_cases"],
            "languages": dict(stats["languages"].most_common()),
            "test_languages": dict(stats["test_languages"].most_common()),
            "kind_files": dict(stats["kind_files"]),
            "kind_cases": dict(stats["kind_cases"]),
            "flag_files": dict(stats["flag_files"]),
            "coverage_measured": stats["coverage_measured"],
            "coverage_threshold": stats["coverage_threshold"],
            "coverage_source": stats["coverage_source"],
            "coverage_config": stats["coverage_config"],
            "ci_files": stats["ci_files"],
            "mutation_testing": stats["mutation_testing"],
            "git": stats["git"],
        },
    }


def compare(report: Report, baseline: Report) -> Report:
    """Attach per-dimension and total deltas against a previous JSON report."""
    if not isinstance(baseline, dict) or "score" not in baseline:
        raise ValueError("baseline is not a gradebook-tests JSON report")
    previous = {d["id"]: d for d in baseline.get("dimensions", []) if isinstance(d, dict)}
    deltas = {}
    for dim in report["dimensions"]:
        was = previous.get(dim["id"], {}).get("points")
        now = dim["points"]
        dim["delta"] = round(now - was, 1) if was is not None and now is not None else None
        deltas[dim["id"]] = dim["delta"]
    comparable = sorted(baseline.get("not_scored", [])) == sorted(report["not_scored"])
    report["baseline"] = {
        "score": baseline["score"],
        "delta": round(report["score"] - baseline["score"], 1),
        "dimensions": deltas,
        "comparable": comparable,
    }
    return report


def score_directories(root: Path, *, use_git: bool = True) -> list[Stats]:
    """Score each immediate subdirectory that holds code of its own."""
    results = []
    for child in sorted(p for p in root.iterdir() if p.is_dir()):
        if child.name in SKIP_DIRS or child.name in ARTIFACT_DIRS:
            continue
        stats = collect(child, use_git=use_git)
        if not stats["source_files"] and not stats["test_files"]:
            continue
        report = evaluate(stats)
        top = recommendations(report, 1)
        results.append(
            {
                "path": child.name,
                "score": report["score"],
                "grade": report["grade"],
                "source_files": stats["source_files"],
                "test_files": stats["test_files"],
                "test_cases": stats["cases"],
                "top_win": top[0]["advice"] if top else "",
                "top_win_points": top[0]["lost"] if top else 0.0,
            }
        )
    return sorted(results, key=lambda r: r["score"])


def recommendations(report: Report, top: int = TOP_RECOMMENDATIONS) -> list[Stats]:
    ranked = [d for d in report["dimensions"] if d["score"] is not None and d["lost"] >= MIN_POINTS_LOST_TO_RECOMMEND]
    ranked.sort(key=lambda d: d["lost"], reverse=True)
    return ranked[:top]
