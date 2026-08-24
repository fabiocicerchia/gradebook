import json
import subprocess
from pathlib import Path

import pytest

from gradebook_tests import (
    blend_profile,
    classify_name,
    cobertura_files,
    collect,
    compare,
    conditional_logic,
    evaluate,
    find_duplicates,
    go_profile_files,
    is_test_file,
    json_report_files,
    lcov_files,
    main,
    name_words,
    normalise_body,
    parse_cargo_mutants,
    parse_cobertura,
    parse_go_profile,
    parse_jacoco,
    parse_json_report,
    parse_lcov,
    parse_pitest,
    parse_stryker,
    recommendations,
    render_flags,
    render_markdown,
    render_text,
    score_directories,
    source_stem,
)


def write(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def report_for(root, use_git=False):
    return evaluate(collect(root, use_git=use_git))


def dim(report, key):
    return next(d for d in report["dimensions"] if d["id"] == key)


# ------------------------------------------------------------ file detection


@pytest.mark.parametrize(
    "path",
    [
        "tests/test_thing.py",
        "app/thing_test.py",
        "conftest.py",
        "src/thing.test.ts",
        "src/thing.spec.js",
        "src/__tests__/thing.js",
        "pkg/thing_test.go",
        "src/test/java/ThingTest.java",
        "spec/thing_spec.rb",
        "tests/ThingTest.php",
        "Thing.Tests.cs",
        "test/thing_test.exs",
        "features/checkout.feature",
        "tests/helpers.py",
    ],
)
def test_recognises_test_files(path):
    assert is_test_file(Path(path))


@pytest.mark.parametrize(
    "path",
    [
        "src/thing.py",
        "src/latest.js",
        "pkg/thing.go",
        "src/main/java/Thing.java",
        "README.md",
        "lib/contest.rb",
    ],
)
def test_ignores_non_test_files(path):
    assert not is_test_file(Path(path))


def test_source_and_test_files_are_counted_separately(tmp_path):
    write(tmp_path, "src/a.py", "def a():\n    return 1\n")
    write(tmp_path, "src/b.py", "def b():\n    return 2\n")
    write(tmp_path, "tests/test_a.py", "def test_a():\n    assert a() == 1\n")
    stats = collect(tmp_path, use_git=False)
    assert stats["source_files"] == 2
    assert stats["test_files"] == 1
    assert stats["cases"] == 1


def test_build_artifacts_are_not_counted_as_source(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(tmp_path, "dist/bundle.js", "var x = 1;\n")
    write(tmp_path, "node_modules/dep/index.js", "var y = 2;\n")
    assert collect(tmp_path, use_git=False)["source_files"] == 1


# ------------------------------------------------------------ classification


def test_classifies_layers_by_directory(tmp_path):
    write(tmp_path, "tests/unit/test_a.py", "def test_a():\n    assert 1\n")
    write(tmp_path, "tests/integration/test_b.py", "def test_b():\n    assert 1\n")
    write(tmp_path, "tests/e2e/test_c.py", "def test_c():\n    assert 1\n")
    stats = collect(tmp_path, use_git=False)
    assert stats["kind_files"]["unit"] == 1
    assert stats["kind_files"]["integration"] == 1
    assert stats["kind_files"]["e2e"] == 1


def test_classifies_layers_by_content_when_path_is_neutral(tmp_path):
    write(tmp_path, "tests/test_db.py", "import testcontainers\n\ndef test_db():\n    assert 1\n")
    write(
        tmp_path,
        "tests/test_ui.py",
        "from playwright.sync_api import sync_playwright\n\ndef test_ui():\n    assert 1\n",
    )
    stats = collect(tmp_path, use_git=False)
    assert stats["kind_files"]["integration"] == 1
    assert stats["kind_files"]["e2e"] == 1


def test_layer_share_is_relative_to_the_whole_suite(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(tmp_path, "tests/e2e/test_journey.py", "def test_journey():\n    assert 1\n")
    report = report_for(tmp_path)
    assert "100% of all cases" in dim(report, "e2e")["detail"]
    assert dim(report, "e2e")["score"] <= 1.0


def test_gherkin_outranks_spec_style_bdd(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "features/checkout.feature",
        "Feature: checkout\n  Scenario: pay\n    Given a cart\n    When I pay\n    Then I win\n",
    )
    gherkin = report_for(tmp_path)

    other = tmp_path.parent / "spec_only"
    write(other, "src/a.js", "export const a = 1;\n")
    write(
        other,
        "src/a.spec.js",
        "describe('a', () => { it('works', () => { expect(a).toBe(1); }); });\n",
    )
    spec = report_for(other)

    assert dim(gherkin, "bdd")["score"] > dim(spec, "bdd")["score"] > 0


def test_counts_cases_and_assertions_across_languages(tmp_path):
    write(
        tmp_path,
        "tests/test_py.py",
        "def test_one():\n    assert 1 == 1\ndef test_two():\n    assert 2 == 2\n",
    )
    write(
        tmp_path,
        "pkg/thing_test.go",
        'func TestOne(t *testing.T) {\n\tif x != 1 {\n\t\tt.Fatalf("bad")\n\t}\n}\n',
    )
    write(tmp_path, "src/a.spec.ts", "it('works', () => { expect(1).toBe(1); });\n")
    stats = collect(tmp_path, use_git=False)
    assert stats["cases"] == 4
    assert stats["assertions"] >= 4
    assert stats["cases_without_assertions"] == 0


def test_flags_test_cases_without_assertions(tmp_path):
    write(
        tmp_path,
        "tests/test_a.py",
        "def test_asserts():\n    assert 1\n\ndef test_silent():\n    do_something()\n",
    )
    stats = collect(tmp_path, use_git=False)
    assert stats["cases"] == 2
    assert stats["cases_without_assertions"] == 1


def test_detects_skips_focus_and_sleeps(tmp_path):
    write(
        tmp_path,
        "tests/test_a.py",
        "import pytest, time\n\n@pytest.mark.skip\ndef test_a():\n    assert 1\n\n"
        "def test_b():\n    time.sleep(5)\n    assert 1\n",
    )
    write(tmp_path, "src/a.spec.js", "it.only('x', () => { expect(1).toBe(1); });\n")
    stats = collect(tmp_path, use_git=False)
    assert stats["skips"] >= 1
    assert stats["sleeps"] >= 1
    assert stats["focused"] >= 1


# ---------------------------------------------------------------- coverage


def test_parses_cobertura():
    assert parse_cobertura('<coverage line-rate="0.8123" branch-rate="0.5">') == 81.2


def test_parses_lcov():
    assert parse_lcov("SF:a.py\nLF:100\nLH:75\nend_of_record\n") == 75.0


def test_parses_jacoco():
    xml = (
        '<counter type="LINE" missed="1" covered="1"/>'
        '<counter type="LINE" missed="20" covered="80"/>'
    )
    assert parse_jacoco(xml) == 80.0


def test_parses_go_coverprofile():
    profile = "mode: set\npkg/a.go:1.1,2.2 4 1\npkg/a.go:3.1,4.2 6 0\n"
    assert parse_go_profile(profile) == 40.0


def test_parses_json_coverage_reports():
    assert parse_json_report('{"totals": {"percent_covered": 91.4}}') == 91.4
    assert parse_json_report('{"total": {"lines": {"pct": 62.5}}}') == 62.5
    assert parse_json_report("not json") is None


def test_measured_coverage_beats_declared_only(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(tmp_path, "tests/test_a.py", "def test_a():\n    assert 1\n")
    write(tmp_path, ".coveragerc", "[report]\nfail_under = 90\n")
    declared = report_for(tmp_path)
    assert declared["stats"]["coverage_threshold"] == 90
    assert declared["stats"]["coverage_measured"] is None

    write(tmp_path, "coverage.xml", '<coverage line-rate="0.95"></coverage>')
    measured = report_for(tmp_path)
    assert measured["stats"]["coverage_measured"] == 95.0
    assert dim(measured, "coverage")["score"] > dim(declared, "coverage")["score"]


def test_coverage_report_found_inside_artifact_dir(tmp_path):
    write(tmp_path, "src/a.js", "export const a = 1;\n")
    write(tmp_path, "coverage/coverage-summary.json", '{"total": {"lines": {"pct": 88}}}')
    stats = collect(tmp_path, use_git=False)
    assert stats["coverage_measured"] == 88.0
    assert stats["source_files"] == 1  # the coverage dir is not source


def test_no_coverage_tooling_scores_zero(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(tmp_path, "tests/test_a.py", "def test_a():\n    assert 1\n")
    assert dim(report_for(tmp_path), "coverage")["score"] == 0.0


# ---------------------------------------------------------------------- CI


def test_detects_ci_running_tests_and_coverage(tmp_path):
    write(
        tmp_path,
        ".github/workflows/ci.yml",
        "jobs:\n  test:\n    steps:\n      - run: pytest --cov=src --cov-fail-under=80\n",
    )
    stats = collect(tmp_path, use_git=False)
    assert stats["ci_runs_tests"] and stats["ci_coverage"]
    assert stats["coverage_threshold"] == 80


def test_ci_without_tests_scores_low(tmp_path):
    write(tmp_path, ".github/workflows/ci.yml", "jobs:\n  lint:\n    steps:\n      - run: ruff .\n")
    assert dim(report_for(tmp_path), "ci")["score"] == 0.0


# --------------------------------------------------------------------- TDD


def git_repo(path):
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@e",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@e",
        "PATH": "/usr/bin:/bin",
    }
    subprocess.run(["git", "init", "-q", str(path)], check=True, env=env)
    return env


def commit(path, env, message):
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True, env=env)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", message], check=True, env=env)


def test_tdd_rewards_tests_shipped_with_source(tmp_path):
    env = git_repo(tmp_path)
    for i in range(6):
        write(tmp_path, f"src/mod{i}.py", f"def f{i}():\n    return {i}\n")
        write(tmp_path, f"tests/test_mod{i}.py", f"def test_f{i}():\n    assert f{i}() == {i}\n")
        commit(tmp_path, env, f"feat: mod{i} with tests")
    disciplined = report_for(tmp_path, use_git=True)
    assert disciplined["stats"]["git"]["source_commits_with_tests"] == 6
    assert dim(disciplined, "tdd")["score"] > 0.8


def test_tdd_penalises_untested_source_commits(tmp_path):
    env = git_repo(tmp_path)
    for i in range(6):
        write(tmp_path, f"src/mod{i}.py", f"def f{i}():\n    return {i}\n")
        commit(tmp_path, env, f"feat: mod{i}")
    report = report_for(tmp_path, use_git=True)
    assert report["stats"]["git"]["source_commits_with_tests"] == 0
    assert dim(report, "tdd")["score"] == 0.0


def test_tdd_not_scored_without_git(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(tmp_path, "tests/test_a.py", "def test_returns_one_when_called():\n    assert a() == 1\n")
    report = report_for(tmp_path, use_git=False)
    assert dim(report, "tdd")["score"] is None
    assert "TDD discipline" in report["not_scored"]
    # both git-derived dimensions drop out and their weight is redistributed
    assert report["scored_weight"] == 88


# ------------------------------------------------------------- test naming


@pytest.mark.parametrize(
    "name",
    [
        "test_returns_404_when_the_user_is_missing",
        "shouldRejectExpiredTokens",
        "charges the card once when retried",
        "test_raises_value_error_on_negative_amount",
    ],
)
def test_descriptive_names_are_recognised(name):
    placeholder, descriptive, _ = classify_name(name)
    assert descriptive and not placeholder


@pytest.mark.parametrize("name", ["test_1", "test", "it works", "testFoo", "test_stuff", "case2"])
def test_placeholder_names_are_flagged(name):
    placeholder, descriptive, _ = classify_name(name)
    assert placeholder and not descriptive


def test_condition_is_detected_in_names():
    assert classify_name("test_retries_when_the_gateway_times_out")[2]
    assert not classify_name("test_retries_the_gateway_call_twice")[2]


def test_name_words_strips_prefixes_and_splits_camel_case():
    assert name_words("test_returns_none") == ["returns", "none"]
    assert name_words("shouldReturnNone") == ["should", "return", "none"]


def test_naming_dimension_separates_good_from_placeholder_names(tmp_path):
    good = tmp_path / "good"
    write(good, "src/a.py", "x = 1\n")
    write(
        good,
        "tests/test_a.py",
        "def test_returns_receipt_when_the_gateway_accepts():\n    assert charge() == 1\n\n"
        "def test_raises_when_the_amount_is_negative():\n    assert error\n",
    )
    bad = tmp_path / "bad"
    write(bad, "src/a.py", "x = 1\n")
    write(
        bad,
        "tests/test_a.py",
        "def test_1():\n    assert charge() == 1\n\ndef test_works():\n    assert error\n",
    )

    good_naming = dim(report_for(good), "naming")
    bad_naming = dim(report_for(bad), "naming")
    assert good_naming["score"] > 0.8
    assert bad_naming["score"] == 0.0
    assert "placeholder" in bad_naming["detail"]
    assert "test_1" in bad_naming["advice"]


def test_naming_not_scored_when_no_names_can_be_extracted(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(tmp_path, "tests/fixtures.md", "not a test\n")
    assert dim(report_for(tmp_path), "naming")["score"] is None


# ------------------------------------------------------------- test doubles


def test_mock_only_cases_are_detected(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "tests/test_a.py",
        "from unittest.mock import MagicMock\n\n"
        "def test_charges_the_gateway_when_asked():\n"
        "    gateway = MagicMock()\n"
        "    charge(gateway, 10)\n"
        "    gateway.charge.assert_called_once_with(10)\n",
    )
    stats = collect(tmp_path, use_git=False)
    assert stats["doubles"] >= 1
    assert stats["cases_with_doubles"] == 1
    assert stats["mock_only_cases"] == 1


def test_asserting_on_a_value_is_not_a_mock_only_case(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "tests/test_a.py",
        "from unittest.mock import MagicMock\n\n"
        "def test_returns_the_receipt_when_the_gateway_accepts():\n"
        "    gateway = MagicMock()\n"
        "    gateway.charge.return_value = 'r1'\n"
        "    assert charge(gateway, 10) == 'r1'\n",
    )
    stats = collect(tmp_path, use_git=False)
    assert stats["cases_with_doubles"] == 1
    assert stats["mock_only_cases"] == 0


def test_doubles_dimension_punishes_tautological_mock_tests(tmp_path):
    honest = tmp_path / "honest"
    write(honest, "src/a.py", "x = 1\n")
    write(
        honest,
        "tests/test_a.py",
        "from unittest.mock import patch\n\n"
        "@patch('src.a.gateway')\n"
        "def test_returns_the_receipt_when_the_gateway_accepts(gateway):\n"
        "    gateway.charge.return_value = 'r1'\n"
        "    assert charge(gateway, 10) == 'r1'\n",
    )
    fake = tmp_path / "fake"
    write(fake, "src/a.py", "x = 1\n")
    write(
        fake,
        "tests/test_a.py",
        "from unittest.mock import MagicMock\n\n"
        "def test_charges(gateway):\n"
        "    a, b, c, d = MagicMock(), MagicMock(), MagicMock(), MagicMock()\n"
        "    charge(a, 10)\n"
        "    a.charge.assert_called_once()\n",
    )

    honest_doubles = dim(report_for(honest), "doubles")
    fake_doubles = dim(report_for(fake), "doubles")
    assert honest_doubles["score"] > fake_doubles["score"]
    assert "assert only on the double" in fake_doubles["detail"]
    assert "only verify" in fake_doubles["advice"]


def test_a_suite_without_doubles_is_not_punished(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "tests/test_a.py",
        "def test_returns_one_when_called_with_nothing():\n    assert a() == 1\n",
    )
    doubles = dim(report_for(tmp_path), "doubles")
    assert doubles["score"] == 0.9
    assert "no test doubles" in doubles["detail"]


def test_decorated_doubles_belong_to_their_case(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "tests/test_a.py",
        "@patch('src.a.clock')\n"
        "def test_expires_the_token_when_the_clock_advances(clock):\n"
        "    assert expired() is True\n",
    )
    stats = collect(tmp_path, use_git=False)
    assert stats["cases_with_doubles"] == 1
    assert stats["doubles"] == 1  # @patch(...) counted once, not twice


# --------------------------------------------------------- weak assertions


def test_weak_assertions_are_separated_from_real_ones(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "tests/test_a.py",
        "def test_returns_the_total_when_two_items_are_added():\n"
        "    assert total([1, 2]) == 3\n\n"
        "def test_returns_something_when_called():\n"
        "    assert total([1, 2])\n\n"
        "def test_returns_a_truthy_value_when_called():\n"
        "    assert total([1, 2]) is not None\n",
    )
    stats = collect(tmp_path, use_git=False)
    assert stats["weak_only_cases"] == 1  # only the bare `assert total(...)`
    assert stats["weak_assertions"] == 1


@pytest.mark.parametrize(
    "body,weak",
    [
        ("expect(sum(1, 2)).toBe(3);", False),
        ("expect(sum(1, 2)).toBeTruthy();", True),
        ("expect(sum(1, 2)).toBeDefined();", True),
        ("expect(render()).toMatchSnapshot();", True),
    ],
)
def test_weak_javascript_assertions(tmp_path, body, weak):
    write(tmp_path, "src/a.js", "export const a = 1;\n")
    write(
        tmp_path,
        "src/a.spec.js",
        f"it('returns the sum when given two numbers', () => {{ {body} }});\n",
    )
    assert collect(tmp_path, use_git=False)["weak_only_cases"] == (1 if weak else 0)


def test_tautological_assertions_count_as_weak(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(tmp_path, "tests/test_a.py", "def test_the_suite_runs_when_invoked():\n    assert True\n")
    assert collect(tmp_path, use_git=False)["weak_only_cases"] == 1


def test_assertion_dimension_punishes_weak_only_cases(tmp_path):
    strong = tmp_path / "strong"
    write(strong, "src/a.py", "x = 1\n")
    write(
        strong,
        "tests/test_a.py",
        "def test_returns_three_when_adding_one_and_two():\n    assert total() == 3\n",
    )
    weak = tmp_path / "weak"
    write(weak, "src/a.py", "x = 1\n")
    write(
        weak,
        "tests/test_a.py",
        "def test_returns_three_when_adding_one_and_two():\n    assert total()\n",
    )
    strong_score = dim(report_for(strong), "assertions")
    weak_score = dim(report_for(weak), "assertions")
    assert strong_score["score"] > weak_score["score"]
    assert "truthy/not-null" in weak_score["detail"]
    assert "truthiness" in weak_score["advice"]


# ----------------------------------------------------------- failure paths


def test_failure_paths_detected_by_assertion_and_by_name(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "tests/test_a.py",
        "def test_returns_the_receipt_when_the_card_is_accepted():\n    assert charge() == 1\n\n"
        "def test_raises_when_the_amount_is_negative():\n"
        "    with pytest.raises(ValueError):\n        charge(-1)\n\n"
        "def test_returns_none_for_a_missing_record():\n    assert find() is None\n",
    )
    stats = collect(tmp_path, use_git=False)
    assert stats["error_cases"] == 2  # the raises case and the "missing" case


def test_happy_path_only_suite_scores_zero_on_failure_paths(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "tests/test_a.py",
        "\n".join(
            f"def test_returns_{i}_when_asked_for_{i}():\n    assert f() == {i}\n" for i in range(4)
        ),
    )
    failure = dim(report_for(tmp_path), "failure")
    assert failure["score"] == 0.0
    assert "0/4" in failure["detail"]


# --------------------------------------------------------------- mutation


def test_parses_stryker_report():
    payload = (
        '{"files": {"a.js": {"mutants": [{"status": "Killed"}, {"status": "Survived"},'
        ' {"status": "Timeout"}, {"status": "NoCoverage"}]}}}'
    )
    assert parse_stryker(payload) == 50.0


def test_parses_pitest_report():
    xml = (
        "<mutation detected='true' status='KILLED'/><mutation detected='false' status='SURVIVED'/>"
    )
    assert parse_pitest(xml) == 50.0


def test_parses_cargo_mutants_report():
    payload = (
        '{"outcomes": [{"summary": "CaughtMutant"}, {"summary": "MissedMutant"},'
        ' {"summary": "CaughtMutant"}]}'
    )
    assert parse_cargo_mutants(payload) == 66.7


def test_mutation_is_not_scored_without_a_report(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(tmp_path, "tests/test_a.py", "def test_returns_one_when_called():\n    assert a() == 1\n")
    report = report_for(tmp_path)
    assert dim(report, "mutation")["score"] is None
    assert "Mutation score" in report["not_scored"]


def test_mutation_report_is_scored_when_present(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(tmp_path, "tests/test_a.py", "def test_returns_one_when_called():\n    assert a() == 1\n")
    write(
        tmp_path,
        "reports/mutation.json",
        '{"files": {"a.py": {"mutants": [{"status": "Killed"}, {"status": "Killed"},'
        ' {"status": "Killed"}, {"status": "Survived"}]}}}',
    )
    mutation = dim(report_for(tmp_path), "mutation")
    assert mutation["score"] == pytest.approx(75.0 / 80.0)
    assert "75.0% of mutants killed" in mutation["detail"]


# --------------------------------------------------------------- baseline


def test_compare_reports_deltas_per_dimension(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(tmp_path, "tests/test_a.py", "def test_returns_one_when_called():\n    assert a() == 1\n")
    baseline = report_for(tmp_path)

    write(
        tmp_path,
        "tests/test_a.py",
        "def test_returns_one_when_called():\n    assert a() == 1\n\ndef test_1():\n    pass\n",
    )
    current = compare(report_for(tmp_path), json.loads(json.dumps(baseline)))

    assert current["baseline"]["delta"] < 0
    assert current["baseline"]["comparable"] is True
    assert dim(current, "naming")["delta"] < 0


def test_compare_flags_a_baseline_that_scored_other_dimensions(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(tmp_path, "tests/test_a.py", "def test_returns_one_when_called():\n    assert a() == 1\n")
    report = report_for(tmp_path)
    baseline = json.loads(json.dumps(report))
    baseline["not_scored"] = []
    assert compare(report, baseline)["baseline"]["comparable"] is False


def test_compare_rejects_a_file_that_is_not_a_report(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    with pytest.raises(ValueError):
        compare(report_for(tmp_path), {"nonsense": True})


def test_cli_fail_on_drop_gate(tmp_path, capsys):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(tmp_path, "tests/test_a.py", "def test_returns_one_when_called():\n    assert a() == 1\n")
    baseline_file = tmp_path / "baseline.json"
    assert main([str(tmp_path), "--format", "json", "--no-git"]) == 0
    baseline_file.write_text(capsys.readouterr().out)

    assert (
        main([str(tmp_path), "--no-git", "--baseline", str(baseline_file), "--fail-on-drop"]) == 0
    )

    write(tmp_path, "tests/test_b.py", "def test_1():\n    pass\n")
    assert (
        main([str(tmp_path), "--no-git", "--baseline", str(baseline_file), "--fail-on-drop"]) == 1
    )
    assert (
        main([str(tmp_path), "--no-git", "--baseline", str(baseline_file), "--fail-on-drop", "50"])
        == 0
    )


def test_cli_rejects_drop_gate_without_baseline(tmp_path):
    assert main([str(tmp_path), "--no-git", "--fail-on-drop"]) == 2


def test_cli_rejects_an_unreadable_baseline(tmp_path):
    assert main([str(tmp_path), "--no-git", "--baseline", str(tmp_path / "missing.json")]) == 2


# ---------------------------------------------------------------- by-dir


def test_score_directories_ranks_the_weakest_first(tmp_path):
    good = tmp_path / "good"
    write(good, "src/a.py", "x = 1\n")
    write(
        good,
        "tests/test_a.py",
        "def test_returns_one_when_called():\n    assert a() == 1\n\n"
        "def test_raises_when_the_input_is_invalid():\n"
        "    with pytest.raises(ValueError):\n        a(None)\n",
    )
    write(good, "coverage.xml", '<coverage line-rate="0.92"></coverage>')
    bad = tmp_path / "bad"
    write(bad, "src/b.py", "y = 2\n")

    ranked = score_directories(tmp_path, use_git=False)
    assert [entry["path"] for entry in ranked] == ["bad", "good"]
    assert ranked[0]["score"] < ranked[1]["score"]
    assert ranked[0]["top_win"]


def test_score_directories_skips_directories_without_code(tmp_path):
    write(tmp_path, "docs/readme.md", "# hi\n")
    write(tmp_path, "app/main.py", "x = 1\n")
    assert [entry["path"] for entry in score_directories(tmp_path, use_git=False)] == ["app"]


# --------------------------------------------------------------- substance


def findings_of(report, kind):
    return [f for f in report["findings"] if f["kind"] == kind]


def test_normalise_body_strips_names_literals_and_comments():
    a = normalise_body("def test_one():\n    # comment\n    assert charge(10) == 'ok'\n")
    b = normalise_body("def test_two():\n    assert charge(99) == 'nope'\n")
    assert a == b == "assert charge(@) == @"


def test_three_copies_are_flagged_but_a_pair_is_not(tmp_path):
    def case(i):
        return (
            f"def test_charge_returns_the_amount_for_{i}():\n"
            f"    result = charge({i})\n    assert result == {i}\n\n"
        )

    write(tmp_path, "src/a.py", "x = 1\n")
    write(tmp_path, "tests/test_pair.py", case(1) + case(2))
    assert collect(tmp_path, use_git=False)["duplicate_cases"] == 0

    write(tmp_path, "tests/test_pair.py", case(1) + case(2) + case(3))
    stats = collect(tmp_path, use_git=False)
    assert stats["duplicate_cases"] == 2
    assert len([f for f in stats["findings"] if f["kind"] == "duplicate-case"]) == 2


def test_duplicate_findings_point_back_at_the_original():
    bodies = [
        ("tests/test_a.py", [("assert charge(@)", 4), ("assert charge(@)", 9)]),
        ("tests/test_b.py", [("assert charge(@)", 3)]),
    ]
    redundant, findings = find_duplicates(bodies)
    assert redundant == 2
    assert "tests/test_a.py:4" in findings[0]["message"]


@pytest.mark.parametrize(
    "body,message",
    [
        ("def test_a():\n    # assert charge(1) == 2\n    charge(1)\n", "commented out"),
        (
            "def test_a():\n    try:\n        charge(1)\n    except Exception:\n        pass\n",
            "swallowed",
        ),
        ("def test_a():\n    if False:\n        assert charge(1) == 2\n", "if False"),
        ("@pytest.mark.skip\ndef test_a():\n    assert charge(1) == 2\n", "no reason"),
    ],
)
def test_suppressed_failures_are_found(tmp_path, body, message):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(tmp_path, "tests/test_a.py", body)
    report = report_for(tmp_path)
    flags = findings_of(report, "suppressed-failure")
    assert flags and any(message in f["message"] for f in flags)
    assert all(f["line"] > 0 for f in flags)


def test_skip_with_a_reason_is_not_a_suppressed_failure(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "tests/test_a.py",
        "@pytest.mark.skip(reason='waiting on the payment sandbox')\n"
        "def test_charges_when_the_sandbox_is_up():\n    assert charge(1) == 2\n",
    )
    assert not findings_of(report_for(tmp_path), "suppressed-failure")


def test_phantom_symbols_are_flagged(tmp_path):
    write(tmp_path, "src/billing.py", "def charge(a):\n    return a\n")
    write(
        tmp_path,
        "tests/test_billing.py",
        "from src.billing import charge, calculate_discount\n\n"
        "def test_charge_returns_the_amount_when_given_one():\n    assert charge(1) == 1\n",
    )
    flags = findings_of(report_for(tmp_path), "phantom-symbol")
    assert len(flags) == 1
    assert "calculate_discount" in flags[0]["message"]


def test_importing_a_module_or_a_test_helper_is_not_a_phantom(tmp_path):
    write(tmp_path, "billing/__init__.py", "\n")
    write(tmp_path, "billing/gateway.py", "def charge(a):\n    return a\n")
    write(tmp_path, "tests/helpers.py", "def build_order():\n    return {}\n")
    write(
        tmp_path,
        "tests/test_billing.py",
        "from billing import gateway\nfrom tests.helpers import build_order\n\n"
        "def test_charges_the_order_when_it_is_valid():\n"
        "    assert gateway.charge(build_order()) is not None\n",
    )
    assert not findings_of(report_for(tmp_path), "phantom-symbol")


def test_third_party_imports_are_ignored(tmp_path):
    write(tmp_path, "src/a.py", "def a():\n    return 1\n")
    write(
        tmp_path,
        "tests/test_a.py",
        "from unittest.mock import patch\nfrom requests import Session\n\n"
        "def test_returns_one_when_called():\n    assert a() == 1\n",
    )
    assert not findings_of(report_for(tmp_path), "phantom-symbol")


@pytest.mark.parametrize(
    "test_file,source",
    [
        ("tests/test_billing.py", "billing"),
        ("tests/billing_test.py", "billing"),
        ("src/billing.spec.ts", "billing"),
        ("pkg/billing_test.go", "billing"),
        ("src/test/java/BillingTest.java", "Billing"),
        ("spec/billing_spec.rb", "billing"),
    ],
)
def test_source_stem_pairs_tests_with_their_module(test_file, source):
    assert source_stem(Path(test_file)) == source


def test_stale_tests_are_flagged(tmp_path):
    env = git_repo(tmp_path)
    write(tmp_path, "src/billing.py", "def charge(a):\n    return a\n")
    write(
        tmp_path,
        "tests/test_billing.py",
        "def test_charge_returns_the_amount_when_given_one():\n    assert charge(1) == 1\n",
    )
    commit(tmp_path, env, "feat: billing with tests")
    for i in range(6):
        write(tmp_path, "src/billing.py", f"def charge(a):\n    return a + {i}\n")
        commit(tmp_path, env, f"fix: tweak {i}")

    report = report_for(tmp_path, use_git=True)
    flags = findings_of(report, "stale-test")
    assert len(flags) == 1
    assert "changed 6 times" in flags[0]["message"]


def test_a_test_that_keeps_up_is_not_stale(tmp_path):
    env = git_repo(tmp_path)
    for i in range(6):
        write(tmp_path, "src/billing.py", f"def charge(a):\n    return a + {i}\n")
        write(
            tmp_path,
            "tests/test_billing.py",
            f"def test_charge_adds_{i}_when_given_an_amount():\n    assert charge(1) == {i + 1}\n",
        )
        commit(tmp_path, env, f"fix: tweak {i}")
    assert not findings_of(report_for(tmp_path, use_git=True), "stale-test")


def test_decorative_tests_are_flagged_from_per_file_coverage(tmp_path):
    write(tmp_path, "src/billing.py", "def charge(a):\n    return a\n")
    write(
        tmp_path,
        "tests/test_billing.py",
        "def test_charge_returns_the_amount_when_given_one():\n    assert charge(1) == 1\n",
    )
    write(
        tmp_path,
        "coverage.xml",
        '<coverage line-rate="0.30"><class filename="src/billing.py" line-rate="0.12"/></coverage>',
    )
    flags = findings_of(report_for(tmp_path), "decorative-test")
    assert len(flags) == 1
    assert "12% covered" in flags[0]["message"]


def test_well_covered_modules_are_not_decorative(tmp_path):
    write(tmp_path, "src/billing.py", "def charge(a):\n    return a\n")
    write(
        tmp_path,
        "tests/test_billing.py",
        "def test_charge_returns_the_amount_when_given_one():\n    assert charge(1) == 1\n",
    )
    write(
        tmp_path,
        "coverage.xml",
        '<coverage line-rate="0.90"><class filename="src/billing.py" line-rate="0.95"/></coverage>',
    )
    assert not findings_of(report_for(tmp_path), "decorative-test")


def test_substance_dimension_separates_slop_from_real_tests(tmp_path):
    honest = tmp_path / "honest"
    write(honest, "src/a.py", "def charge(a):\n    return a\n")
    write(
        honest,
        "tests/test_a.py",
        "def test_charge_returns_the_amount_when_given_one():\n    assert charge(1) == 1\n\n"
        "def test_charge_raises_when_the_amount_is_negative():\n"
        "    with pytest.raises(ValueError):\n        charge(-1)\n",
    )
    slop = tmp_path / "slop"
    write(slop, "src/a.py", "def charge(a):\n    return a\n")
    write(
        slop,
        "tests/test_a.py",
        "from src.a import charge, calculate_discount\n\n"
        + "".join(
            f"def test_charge_{i}():\n    result = charge({i})\n    assert result is not None\n\n"
            for i in range(4)
        )
        + "def test_discount():\n    try:\n        calculate_discount(1)\n"
        "    except Exception:\n        pass\n",
    )

    honest_substance = dim(report_for(honest), "substance")
    slop_substance = dim(report_for(slop), "substance")
    assert honest_substance["score"] == 1.0
    assert slop_substance["score"] < 0.5
    assert "duplicate" in slop_substance["detail"]


# ------------------------------------------------------------- red flags


def test_findings_are_rendered_with_a_location(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path, "tests/test_a.py", "def test_a():\n    # assert charge(1) == 2\n    charge(1)\n"
    )
    report = report_for(tmp_path)
    text = render_text(report)
    assert "Red flags (1):" in text
    assert "tests/test_a.py:2" in text
    assert "suppressed-failure" in text


def test_flags_can_be_hidden_and_truncated(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "tests/test_a.py",
        "".join(
            f"def test_{i}():\n    # assert charge({i}) == {i}\n    charge({i})\n\n"
            for i in range(4)
        ),
    )
    report = report_for(tmp_path)
    assert "Red flags" not in render_text(report, max_flags=0)
    assert "1 more" in render_text(report, max_flags=3)
    assert "Red flags" in render_markdown(report)
    assert "Red flags" not in render_markdown(report, max_flags=0)


def test_render_flags_is_empty_without_findings():
    assert render_flags([], 10) == []


# ------------------------------------------------------- per-file coverage


def test_per_file_coverage_parsers():
    assert lcov_files("SF:src/a.py\nLF:10\nLH:5\nend_of_record\n") == {"a.py": 50.0}
    assert cobertura_files('<class filename="src/a.py" line-rate="0.11"/>') == {"a.py": 11.0}
    assert json_report_files(
        '{"total": {"lines": {"pct": 80}}, "/x/src/a.js": {"lines": {"pct": 12}}}'
    ) == {"a.js": 12.0}
    assert go_profile_files("mode: set\npkg/a.go:1.1,2.2 4 1\npkg/a.go:3.1,4.2 6 0\n") == {
        "a.go": 40.0
    }


# ------------------------------------------------------------- suite shape


def suite(tmp_path, unit=0, integration=0, e2e=0):
    write(tmp_path, "src/a.py", "x = 1\n")
    for kind, count in (("unit", unit), ("integration", integration), ("e2e", e2e)):
        if not count:
            continue
        write(
            tmp_path,
            f"tests/{kind}/test_{kind}.py",
            "".join(
                f"def test_returns_{i}_when_called_with_{i}():\n    assert f() == {i}\n\n"
                for i in range(count)
            ),
        )
    return report_for(tmp_path)


def test_pyramid_prefers_a_broad_unit_base(tmp_path):
    healthy = dim(suite(tmp_path / "healthy", unit=20, integration=6, e2e=2), "pyramid")
    assert healthy["score"] > 0.9
    assert "healthy pyramid" in healthy["detail"]


def test_pyramid_flags_the_ice_cream_cone(tmp_path):
    cone = dim(suite(tmp_path / "cone", unit=2, integration=1, e2e=20), "pyramid")
    assert cone["score"] < 0.4
    assert "ice-cream cone" in cone["detail"]


def test_pyramid_flags_unit_tests_without_integration_tests(tmp_path):
    only = dim(suite(tmp_path / "only", unit=20), "pyramid")
    assert only["score"] < 0.8
    assert "without integration" in only["detail"]


def test_pyramid_not_scored_without_classified_cases(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    assert dim(report_for(tmp_path), "pyramid")["score"] is None


# ------------------------------------------------------- determinism


def determinism_of(tmp_path, body):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(tmp_path, "tests/test_a.py", body)
    return dim(report_for(tmp_path), "determinism")


def test_unfrozen_clock_is_flagged(tmp_path):
    result = determinism_of(
        tmp_path,
        "import datetime\n\n"
        "def test_expires_when_the_deadline_passes():\n"
        "    now = datetime.datetime.now()\n    assert expired(now) is True\n",
    )
    assert result["score"] < 1.0
    assert "unfrozen clock" in result["detail"]


def test_a_frozen_clock_is_not_flagged(tmp_path):
    result = determinism_of(
        tmp_path,
        "from freezegun import freeze_time\n\n"
        "@freeze_time('2024-01-01')\n"
        "def test_expires_when_the_deadline_passes():\n"
        "    now = datetime.datetime.now()\n    assert expired(now) is True\n",
    )
    assert "unfrozen clock" not in result["detail"]


def test_unseeded_randomness_is_flagged_but_seeded_is_not(tmp_path):
    unseeded = determinism_of(
        tmp_path / "a",
        "import random\n\n"
        "def test_returns_a_value_when_given_noise():\n"
        "    assert score(random.random()) > 0\n",
    )
    seeded = determinism_of(
        tmp_path / "b",
        "import random\n\nrandom.seed(1)\n\n"
        "def test_returns_a_value_when_given_noise():\n"
        "    assert score(random.random()) > 0\n",
    )
    assert "unseeded randomness" in unseeded["detail"]
    assert "unseeded randomness" not in seeded["detail"]


@pytest.mark.parametrize(
    "line,flagged",
    [
        ("    resp = client.get('http://staging.internal.corp/orders')", True),
        ("    path = '/home/ci/fixtures/orders.json'", True),
        ("    resp = client.get('http://localhost:8080/orders')", True),
        ("    resp = client.get('https://example.com/orders')", False),
        ("    resp = client.get(base_url + '/orders')", False),
    ],
)
def test_environment_coupling(tmp_path, line, flagged):
    result = determinism_of(
        tmp_path,
        "def test_returns_the_order_when_it_exists():\n"
        f"{line}\n    assert resp.status_code == 200\n",
    )
    assert ("coupling" in result["detail"]) is flagged


def test_order_dependent_tests_are_flagged(tmp_path):
    result = determinism_of(
        tmp_path, "def test_01_creates_the_user_when_posted():\n    assert create() == 1\n"
    )
    assert "order-dependent" in result["detail"]


def test_sleeps_are_scored_under_determinism_not_hygiene(tmp_path):
    result = determinism_of(
        tmp_path,
        "import time\n\n"
        "def test_returns_the_result_when_the_worker_finishes():\n"
        "    time.sleep(5)\n    assert result() == 1\n",
    )
    assert "sleeps" in result["detail"]


# ------------------------------------------------------------- test focus


def test_assertion_guards_are_not_conditional_logic():
    go_test = (
        "func TestScore(t *testing.T) {\n"
        "\tgot, err := Score(5)\n"
        '\tif err != nil {\n\t\tt.Fatalf("boom")\n\t}\n'
        '\tif got != 5 {\n\t\tt.Errorf("want 5")\n\t}\n}'
    )
    assert conditional_logic(go_test) == 0


def test_if_else_in_a_case_is_conditional_logic():
    body = (
        "def test_paths():\n    if sys.platform == 'win32':\n"
        "        assert path() == 1\n    else:\n        assert path() == 2\n"
    )
    assert conditional_logic(body) == 1


def test_focus_flags_branching_and_assertion_roulette(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "tests/test_a.py",
        "def test_branches_on_the_platform_when_run():\n"
        "    if sys.platform == 'win32':\n        assert path() == 1\n"
        "    else:\n        assert path() == 2\n\n"
        "def test_checks_everything_about_the_order_at_once():\n"
        + "".join(f"    assert order[{i}] == {i}\n" for i in range(12)),
    )
    focus = dim(report_for(tmp_path), "focus")
    assert focus["score"] < 0.6
    assert "if/switch logic" in focus["detail"] and "10+ assertions" in focus["detail"]


def test_focus_is_clean_for_small_linear_cases(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(tmp_path, "tests/test_a.py", "def test_returns_one_when_called():\n    assert a() == 1\n")
    focus = dim(report_for(tmp_path), "focus")
    assert focus["score"] == 1.0
    assert "small, linear and focused" in focus["detail"]


def test_giant_cases_are_flagged(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "tests/test_a.py",
        "def test_does_far_too_much_when_it_runs():\n"
        + "".join(f"    step_{i}()\n" for i in range(55))
        + "    assert done() is True\n",
    )
    assert "over 50 lines" in dim(report_for(tmp_path), "focus")["detail"]


# ------------------------------------------------------- implementation access


def test_reaching_into_privates_is_flagged(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "tests/test_a.py",
        "def test_caches_the_session_when_reused():\n    assert client._session is not None\n",
    )
    flags = [f for f in report_for(tmp_path)["findings"] if f["kind"] == "implementation-access"]
    assert len(flags) == 1
    assert "_session" in flags[0]["message"]


# -------------------------------------------------- bugfixes without tests


def test_bugfixes_without_regression_tests_lower_tdd(tmp_path):
    env = git_repo(tmp_path)
    write(tmp_path, "src/a.py", "def f():\n    return 1\n")
    write(tmp_path, "tests/test_a.py", "def test_returns_one_when_called():\n    assert f() == 1\n")
    commit(tmp_path, env, "feat: f with tests")
    for i in range(5):
        write(tmp_path, "src/a.py", f"def f():\n    return {i}\n")
        commit(tmp_path, env, f"fix: wrong value {i}")

    report = report_for(tmp_path, use_git=True)
    assert report["stats"]["git"]["fix_commits"] == 5
    assert report["stats"]["git"]["fix_commits_with_tests"] == 0
    tdd = dim(report, "tdd")
    assert "0/5 bugfixes shipped a test" in tdd["detail"]
    assert "regression test" in tdd["advice"]


def test_bugfixes_with_tests_do_not_lower_tdd(tmp_path):
    env = git_repo(tmp_path)
    for i in range(5):
        write(tmp_path, "src/a.py", f"def f():\n    return {i}\n")
        write(
            tmp_path,
            "tests/test_a.py",
            f"def test_returns_{i}_when_called():\n    assert f() == {i}\n",
        )
        commit(tmp_path, env, f"fix: wrong value {i}")
    tdd = dim(report_for(tmp_path, use_git=True), "tdd")
    assert "5/5 bugfixes shipped a test" in tdd["detail"]
    # full co-change and regression credit; the missing 0.1 is the test-only-commit term
    assert tdd["score"] == pytest.approx(0.9)


# ------------------------------------------- brittle locators & ugly mirrors


@pytest.mark.parametrize(
    "call,brittle",
    [
        ("page.click('//div[3]/span[2]')", True),
        ("page.click('.css-1a2b3c4d')", True),
        ("page.textContent('div > div > div:nth-child(2)')", True),
        ("driver.find_element_by_xpath('//*[@id=\"x\"]')", True),
        ("page.getByRole('button', {name: 'Pay'}).click()", False),
        ("page.click('[data-testid=pay]')", False),
    ],
)
def test_brittle_selectors_are_flagged(tmp_path, call, brittle):
    write(tmp_path, "src/a.js", "export const a = 1;\n")
    write(
        tmp_path,
        "tests/e2e/checkout.spec.js",
        "it('completes the checkout when the card is accepted', async () => {\n"
        f"  await {call};\n  expect(await title()).toBe('Done');\n}});\n",
    )
    report = report_for(tmp_path)
    flags = [f for f in report["findings"] if f["kind"] == "brittle-selector"]
    assert bool(flags) is brittle
    if brittle:
        assert "brittle locators" in dim(report, "determinism")["detail"]


def test_robust_locators_in_the_same_file_suppress_the_flag(tmp_path):
    write(tmp_path, "src/a.js", "export const a = 1;\n")
    write(
        tmp_path,
        "tests/e2e/checkout.spec.js",
        "it('completes the checkout when the card is accepted', async () => {\n"
        "  await page.getByTestId('pay').click();\n"
        "  await page.click('div > div > div');\n"
        "  expect(await title()).toBe('Done');\n});\n",
    )
    assert not [f for f in report_for(tmp_path)["findings"] if f["kind"] == "brittle-selector"]


@pytest.mark.parametrize(
    "assertion,mirrored",
    [
        ("assert total(cart) == sum(i.price for i in cart)", True),
        ("assert total(cart) == 30", False),
        ("assert total(cart) == expected", False),
        ("assert sorted(got) == sorted(want)", False),
        ("assert price(x) == pytest.approx(1.5)", False),
    ],
)
def test_mirrored_expectations_are_flagged(tmp_path, assertion, mirrored):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "tests/test_a.py",
        f"def test_totals_the_cart_when_items_are_added():\n    {assertion}\n",
    )
    report = report_for(tmp_path)
    flags = [f for f in report["findings"] if f["kind"] == "mirror-assertion"]
    assert bool(flags) is mirrored
    if mirrored:
        assert "mirrored expectation" in dim(report, "substance")["detail"]


def test_mirrored_expectations_in_matcher_style(tmp_path):
    write(tmp_path, "src/a.js", "export const a = 1;\n")
    write(
        tmp_path,
        "src/a.spec.js",
        "it('totals the cart when items are added', () => {\n"
        "  expect(total(items)).toBe(items.reduce((a, i) => a + i.price, 0));\n});\n",
    )
    assert [f for f in report_for(tmp_path)["findings"] if f["kind"] == "mirror-assertion"]


def test_private_access_lowers_substance(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "tests/test_a.py",
        "def test_caches_the_session_when_reused():\n    assert client._session is not None\n",
    )
    substance = dim(report_for(tmp_path), "substance")
    assert substance["score"] < 1.0
    assert "private-member access" in substance["detail"]


# ---------------------------------------------------- risk targeting (churn)


def test_risk_targeting_flags_untested_hotspots(tmp_path):
    env = git_repo(tmp_path)
    write(tmp_path, "src/quiet.py", "def quiet():\n    return 1\n")
    write(
        tmp_path,
        "tests/test_quiet.py",
        "def test_returns_one_when_called():\n    assert quiet() == 1\n",
    )
    write(tmp_path, "src/hot.py", "def hot():\n    return 1\n")
    write(tmp_path, "src/warm.py", "def warm():\n    return 1\n")
    commit(tmp_path, env, "feat: initial")
    for i in range(4):
        write(tmp_path, "src/hot.py", f"def hot():\n    return {i}\n")
        write(tmp_path, "src/warm.py", f"def warm():\n    return {i}\n")
        write(tmp_path, "src/quiet.py", f"def quiet():\n    return {i}\n")
        commit(tmp_path, env, f"feat: change {i}")

    report = report_for(tmp_path, use_git=True)
    risk = dim(report, "risk")
    assert risk["score"] is not None and risk["score"] < 1.0
    hotspots = [f for f in report["findings"] if f["kind"] == "untested-hotspot"]
    assert {f["file"] for f in hotspots} == {"src/hot.py", "src/warm.py"}
    assert "changed 5 times" in hotspots[0]["message"]


def test_risk_targeting_is_not_scored_without_churn(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(tmp_path, "tests/test_a.py", "def test_returns_one_when_called():\n    assert a() == 1\n")
    report = report_for(tmp_path, use_git=False)
    assert dim(report, "risk")["score"] is None
    assert "Risk targeting" in report["not_scored"]


# ------------------------------------------------- conjoined twins & chatter


def test_unit_tests_doing_real_io_are_flagged(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "tests/unit/test_a.py",
        "import testcontainers\n\n"
        "def test_saves_the_order_when_the_database_accepts_it():\n"
        "    assert save(order) == 1\n",
    )
    report = report_for(tmp_path)
    flags = [f for f in report["findings"] if f["kind"] == "conjoined-twin"]
    assert len(flags) == 1
    assert "unit test(s) doing real I/O" in dim(report, "substance")["detail"]


def test_console_chatter_lowers_hygiene(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "tests/test_a.py",
        "def test_returns_one_when_called():\n    print(a())\n    assert a() == 1\n",
    )
    hygiene = dim(report_for(tmp_path), "hygiene")
    assert hygiene["score"] < 1.0
    assert "console chatter" in hygiene["detail"]


def test_platform_branches_lower_determinism(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "tests/test_a.py",
        "import sys\n\ndef test_returns_the_path_for_the_platform():\n"
        "    assert path().startswith('/') or sys.platform == 'win32'\n",
    )
    assert "platform-specific" in dim(report_for(tmp_path), "determinism")["detail"]


def test_logged_and_swallowed_failures_are_flagged(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "tests/test_a.py",
        "def test_charges_the_card_when_it_is_valid():\n    try:\n        charge()\n"
        "    except Exception as exc:\n        logger.error(exc)\n",
    )
    flags = [
        f
        for f in report_for(tmp_path)["findings"]
        if f["kind"] == "suppressed-failure" and "logged and swallowed" in f["message"]
    ]
    assert len(flags) == 1


def test_mocking_everything_with_no_integration_layer_is_penalised(tmp_path):
    isolated = tmp_path / "isolated"
    write(isolated, "src/a.py", "x = 1\n")
    write(
        isolated,
        "tests/test_a.py",
        "from unittest.mock import patch\n\n@patch('src.a.gateway')\n"
        "def test_returns_the_receipt_when_the_gateway_accepts(gateway):\n"
        "    gateway.charge.return_value = 'r1'\n    assert charge(gateway) == 'r1'\n",
    )
    backed = tmp_path / "backed"
    write(backed, "src/a.py", "x = 1\n")
    write(
        backed,
        "tests/test_a.py",
        "from unittest.mock import patch\n\n@patch('src.a.gateway')\n"
        "def test_returns_the_receipt_when_the_gateway_accepts(gateway):\n"
        "    gateway.charge.return_value = 'r1'\n    assert charge(gateway) == 'r1'\n",
    )
    write(
        backed,
        "tests/integration/test_gateway.py",
        "def test_charges_the_real_gateway_when_it_is_up():\n    assert charge(live) == 'r1'\n",
    )

    assert (
        dim(report_for(isolated), "doubles")["score"] < dim(report_for(backed), "doubles")["score"]
    )
    assert (
        "no integration test exercises the real one"
        in dim(report_for(isolated), "doubles")["advice"]
    )


# ------------------------------------------------------- test-to-code ratio


def test_test_to_code_line_ratio_is_reported(tmp_path):
    write(tmp_path, "src/a.py", "\n".join(f"line_{i} = {i}" for i in range(100)) + "\n")
    write(
        tmp_path,
        "tests/test_a.py",
        "def test_returns_the_value_when_asked():\n" + "    assert a() == 1\n" * 24,
    )
    report = report_for(tmp_path)
    assert report["stats"]["source_lines"] == 100
    assert report["stats"]["test_lines"] == 25
    assert report["stats"]["test_to_code_ratio"] == 0.25
    assert "0.25x test:code lines" in dim(report, "unit")["detail"]


def test_a_thin_suite_scores_below_a_thorough_one_at_the_same_file_count(tmp_path):
    def build(root, assertions):
        write(root, "src/a.py", "\n".join(f"line_{i} = {i}" for i in range(200)) + "\n")
        write(
            root,
            "tests/test_a.py",
            "def test_returns_the_value_when_asked():\n" + "    assert a() == 1\n" * assertions,
        )
        return dim(report_for(root), "unit")

    thin = build(tmp_path / "thin", 2)
    thorough = build(tmp_path / "thorough", 120)
    assert thorough["score"] > thin["score"]


def test_ratio_is_absent_when_there_is_no_source(tmp_path):
    write(tmp_path, "tests/test_a.py", "def test_returns_one_when_called():\n    assert a() == 1\n")
    assert report_for(tmp_path)["stats"]["test_to_code_ratio"] is None


# --------------------------------------------------------- test-per-method


def test_tests_named_after_production_methods_are_flagged(tmp_path):
    write(
        tmp_path,
        "src/billing.py",
        "def charge(a):\n    return a\n\ndef refund(a):\n    return -a\n",
    )
    write(
        tmp_path,
        "tests/test_billing.py",
        "def test_charge():\n    assert charge(1) == 1\n\n"
        "def test_refund():\n    assert refund(1) == -1\n",
    )
    report = report_for(tmp_path)
    assert report["stats"]["method_mirror_names"] == 2
    naming = dim(report, "naming")
    assert "named after a method" in naming["detail"]
    assert "mirrors the code" in naming["advice"]


def test_behaviour_names_are_not_method_mirrors(tmp_path):
    write(tmp_path, "src/billing.py", "def charge(a):\n    return a\n")
    write(
        tmp_path,
        "tests/test_billing.py",
        "def test_charge_returns_the_amount_when_the_card_is_accepted():\n"
        "    assert charge(1) == 1\n",
    )
    assert report_for(tmp_path)["stats"]["method_mirror_names"] == 0


# ------------------------------------------------------- boundary coverage


def test_boundary_cases_are_counted(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    write(
        tmp_path,
        "tests/test_a.py",
        "def test_returns_the_total_when_the_cart_has_items():\n    assert total(cart) == 30\n\n"
        "def test_returns_zero_when_the_cart_is_empty():\n    assert total([]) == 0\n\n"
        "def test_returns_none_when_the_record_is_missing():\n    assert find(1) is None\n",
    )
    report = report_for(tmp_path)
    assert report["stats"]["boundary_cases"] == 2
    assert "touch a boundary value" in dim(report, "failure")["detail"]


def test_go_nil_checks_are_not_boundary_tests(tmp_path):
    write(tmp_path, "src/a.go", "package a\n")
    write(
        tmp_path,
        "pkg/a_test.go",
        "func TestScoreReturnsTheTotalWhenGivenItems(t *testing.T) {\n"
        '\tgot, err := Score([]string{"a"})\n'
        '\tif err != nil {\n\t\tt.Fatalf("boom")\n\t}\n'
        '\tif got != 5 {\n\t\tt.Errorf("want 5")\n\t}\n}\n',
    )
    assert report_for(tmp_path)["stats"]["boundary_cases"] == 0


def test_a_suite_testing_boundaries_scores_higher(tmp_path):
    def build(root, extra):
        write(root, "src/a.py", "x = 1\n")
        write(
            root,
            "tests/test_a.py",
            "".join(
                f"def test_returns_{i}_when_given_{i}():\n    assert f({i}) == {i}\n\n"
                for i in range(4)
            )
            + extra,
        )
        return dim(report_for(root), "failure")

    middles = build(tmp_path / "middles", "")
    edges = build(
        tmp_path / "edges",
        "def test_returns_zero_when_the_input_is_empty():\n    assert f('') == 0\n",
    )
    assert edges["score"] > middles["score"]


def test_serial_only_suites_lose_determinism_points(tmp_path):
    write(tmp_path, "src/a.js", "export const a = 1;\n")
    write(
        tmp_path, "src/a.spec.js", "it('returns one when called', () => { expect(a).toBe(1); });\n"
    )
    write(tmp_path, "package.json", '{"scripts": {"test": "jest --runInBand"}}')
    determinism = dim(report_for(tmp_path), "determinism")
    assert "single worker" in determinism["detail"]
    assert determinism["score"] < 1.0


# ------------------------------------------------------ language calibration


def test_profile_blends_by_share_of_source():
    go_heavy = blend_profile({"go": 8000, "python": 2000})
    assert go_heavy["test_code_ratio"] == 0.74  # between go's 0.80 and python's 0.50
    assert go_heavy["languages"] == ["go", "python"]
    assert blend_profile({"python": 9000})["test_code_ratio"] == 0.50


def test_profile_falls_back_for_unknown_stacks():
    profile = blend_profile({"cobol": 100})
    assert profile["test_code_ratio"] == 0.50
    assert profile["bare_assert_check"] is False


def test_profile_is_empty_without_source():
    assert blend_profile({})["languages"] == []


def test_unit_targets_follow_the_language(tmp_path):
    def build(root, name, source_ext, test_name, body):
        write(root, f"src/a.{source_ext}", "\n".join(f"line{i} = {i}" for i in range(100)))
        write(root, test_name, body)
        return report_for(root)

    py = build(
        tmp_path / "py",
        "python",
        "py",
        "tests/test_a.py",
        "def test_returns_one_when_called():\n" + "    assert a() == 1\n" * 49,
    )
    write(tmp_path / "go", "src/a.go", "\n".join(f"var x{i} = {i}" for i in range(100)))
    write(
        tmp_path / "go",
        "pkg/a_test.go",
        "func TestReturnsOneWhenCalled(t *testing.T) {\n"
        + '\tif got != 1 {\n\t\tt.Errorf("got %v want 1", got)\n\t}\n' * 16
        + "}\n",
    )
    go = report_for(tmp_path / "go")

    # Same 0.5x volume, but Go is held to 0.80x and Python to 0.50x.
    assert py["stats"]["profile"]["test_code_ratio"] == 0.50
    assert go["stats"]["profile"]["test_code_ratio"] == 0.80
    assert "target 0.50x" in dim(py, "unit")["detail"]
    assert "target 0.80x" in dim(go, "unit")["detail"]


def test_bare_asserts_are_scored_in_java_but_not_python(tmp_path):
    write(tmp_path / "java", "src/main/java/Billing.java", "public class Billing {}\n")
    write(
        tmp_path / "java",
        "src/test/java/BillingTest.java",
        "public class BillingTest {\n"
        "  @Test public void chargeReturnsTheAmountWhenAccepted() {\n"
        "    assertTrue(billing.charge(10) > 0);\n  }\n}\n",
    )
    write(tmp_path / "py", "src/billing.py", "def charge(a):\n    return a\n")
    write(
        tmp_path / "py",
        "tests/test_billing.py",
        "def test_charge_returns_the_amount_when_accepted():\n    assert charge(10) > 0\n",
    )

    java = report_for(tmp_path / "java")
    python = report_for(tmp_path / "py")
    assert java["stats"]["uninformative_assertions"] == 1
    assert "report no values on failure" in dim(java, "assertions")["detail"]
    assert python["stats"]["uninformative_assertions"] == 0
    assert "every case asserts a value" in dim(python, "assertions")["detail"]


def test_go_failure_messages_without_values_are_flagged(tmp_path):
    write(tmp_path, "pkg/a.go", "package pkg\n")
    write(
        tmp_path,
        "pkg/a_test.go",
        "func TestChargeReturnsTheAmountWhenAccepted(t *testing.T) {\n"
        '\tif got != 10 {\n\t\tt.Fatal("charge broken")\n\t}\n}\n',
    )
    assert report_for(tmp_path)["stats"]["uninformative_assertions"] == 1


def test_go_failure_messages_with_values_are_not_flagged(tmp_path):
    write(tmp_path, "pkg/a.go", "package pkg\n")
    write(
        tmp_path,
        "pkg/a_test.go",
        "func TestChargeReturnsTheAmountWhenAccepted(t *testing.T) {\n"
        '\tif got != 10 {\n\t\tt.Fatalf("got %v, want 10", got)\n\t}\n}\n',
    )
    assert report_for(tmp_path)["stats"]["uninformative_assertions"] == 0


def test_spec_style_bdd_scores_higher_where_it_is_the_idiom(tmp_path):
    write(tmp_path / "rb", "app/billing.rb", "def charge(a)\n  a\nend\n")
    write(
        tmp_path / "rb",
        "spec/billing_spec.rb",
        "RSpec.describe Billing do\n"
        "  it 'returns the amount when the card is accepted' do\n"
        "    expect(charge(10)).to eq(10)\n  end\nend\n",
    )
    write(tmp_path / "py", "src/billing.py", "def charge(a):\n    return a\n")
    write(
        tmp_path / "py",
        "tests/test_billing.py",
        "def describe_billing():\n    pass\n\n"
        "def test_returns_the_amount_when_the_card_is_accepted():\n    assert charge(10) == 10\n",
    )

    ruby = report_for(tmp_path / "rb")
    assert ruby["stats"]["profile"]["spec_style_idiomatic"] is True
    assert report_for(tmp_path / "py")["stats"]["profile"]["spec_style_idiomatic"] is False


def test_git_paths_are_relative_to_the_scan_not_the_repository(tmp_path):
    env = git_repo(tmp_path)
    write(tmp_path, "service/src/billing.py", "def charge(a):\n    return a\n")
    write(
        tmp_path,
        "service/tests/test_billing.py",
        "def test_charge_returns_the_amount_when_given_one():\n    assert charge(1) == 1\n",
    )
    commit(tmp_path, env, "feat: billing with tests")

    # Scanning the subdirectory: git reports service/src/billing.py while the
    # scan sees src/billing.py, and the pairing only works if they meet.
    history = report_for(tmp_path / "service", use_git=True)["stats"]["git"]
    assert set(history["file_commits"]) == {"src/billing.py", "tests/test_billing.py"}
    assert history["source_commits_with_tests"] == 1


# ------------------------------------------------------------------ scoring


def test_score_is_bounded_and_ordered(tmp_path):
    bare = tmp_path / "bare"
    write(bare, "src/a.py", "def a():\n    return 1\n")
    good = tmp_path / "good"
    write(good, "src/a.py", "def a():\n    return 1\n")
    write(
        good,
        "tests/unit/test_a.py",
        "\n".join(f"def test_a{i}():\n    assert a() == 1\n" for i in range(4)),
    )
    write(good, "tests/integration/test_db.py", "def test_db():\n    assert 1\n")
    write(good, "tests/e2e/test_journey.py", "def test_journey():\n    assert 1\n")
    write(
        good,
        "features/pay.feature",
        "Feature: pay\n  Scenario: pay\n    Given a cart\n    Then it works\n",
    )
    write(good, "coverage.xml", '<coverage line-rate="0.91"></coverage>')
    write(good, ".coveragerc", "[report]\nfail_under = 85\n")
    write(good, ".github/workflows/ci.yml", "jobs:\n  t:\n    steps:\n      - run: pytest --cov\n")

    bare_report, good_report = report_for(bare), report_for(good)
    assert 0 <= bare_report["score"] <= 100
    assert 0 <= good_report["score"] <= 100
    assert good_report["score"] > bare_report["score"]
    assert good_report["grade"] in {"A", "B"}
    assert bare_report["grade"] == "F"


def test_recommendations_are_ranked_by_points_recoverable(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    report = report_for(tmp_path)
    wins = recommendations(report)
    assert wins
    assert [w["lost"] for w in wins] == sorted((w["lost"] for w in wins), reverse=True)
    assert all(w["advice"] for w in wins)


def test_markdown_render_contains_table_and_score(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n")
    out = render_markdown(report_for(tmp_path))
    assert "| Dimension |" in out and "Test suite score" in out


# ---------------------------------------------------------------------- cli


def test_cli_json_output_and_fail_under(tmp_path, capsys):
    write(tmp_path, "src/a.py", "x = 1\n")
    assert main([str(tmp_path), "--format", "json", "--no-git"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["score"] < 40
    assert payload["recommendations"]

    assert main([str(tmp_path), "--no-git", "--fail-under", "50"]) == 1
    assert main([str(tmp_path), "--no-git", "--fail-under", "0"]) == 0


def test_cli_rejects_missing_path(tmp_path, capsys):
    assert main([str(tmp_path / "nope")]) == 2
