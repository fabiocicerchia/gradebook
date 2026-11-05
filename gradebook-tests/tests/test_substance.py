from pathlib import Path

import pytest

from gradebook_tests.substance import find_decorative, find_duplicates, find_phantoms, find_stale, source_stem

# ------------------------------------------------------------ source_stem


@pytest.mark.parametrize(
    ("path", "stem"),
    [
        ("tests/test_billing.py", "billing"),
        ("tests/billing_test.py", "billing"),
        ("src/billing.test.ts", "billing"),
        ("src/billing.spec.js", "billing"),
        ("pkg/billing_test.go", "billing"),
        ("src/BillingTest.java", "Billing"),
        ("src/BillingIT.java", "Billing"),
        ("spec/billing_spec.rb", "billing"),
        ("tests/BillingTest.php", "Billing"),
        ("test/billing_test.exs", "billing"),
    ],
)
def test_source_stem_strips_each_language_test_marker(path, stem):
    assert source_stem(Path(path)) == stem


@pytest.mark.parametrize("path", ["src/billing.py", "tests/test_.py", "src/billing.ts", "README.md"])
def test_source_stem_is_none_when_the_name_names_no_source(path):
    assert source_stem(Path(path)) is None


# -------------------------------------------------------------- duplicates


def test_a_pair_of_identical_bodies_is_not_a_cluster():
    bodies = [("tests/test_a.py", [("assert charge(@)", 4), ("assert charge(@)", 9)])]
    assert find_duplicates(bodies) == (0, [])


def test_duplicate_findings_stop_at_the_limit_but_the_count_does_not():
    bodies = [("tests/test_a.py", [("assert charge(@)", line) for line in range(1, 6)])]
    redundant, findings = find_duplicates(bodies, limit=2)
    assert redundant == 4
    assert [f["line"] for f in findings] == [2, 3]
    assert all(f["kind"] == "duplicate-case" for f in findings)


# ---------------------------------------------------------------- phantoms


def test_phantoms_count_each_missing_name_once_per_file():
    imports = [
        ("tests/test_a.py", ["charge", "refund", "refund"]),
        ("tests/test_b.py", ["refund"]),
    ]
    count, findings = find_phantoms(imports, {"charge"})
    assert count == 2
    assert [f["file"] for f in findings] == ["tests/test_a.py", "tests/test_b.py"]
    assert all("`refund`" in f["message"] for f in findings)


def test_no_phantoms_when_every_import_is_defined():
    assert find_phantoms([("tests/test_a.py", ["charge"])], {"charge"}) == (0, [])


# ------------------------------------------------------------------- stale


def test_a_test_is_stale_once_its_source_moved_on_enough_times():
    # positions are newest-first: 0 is the latest commit
    commits = {"tests/test_a.py": [5, 9], "src/a.py": [0, 1, 2, 7]}
    count, findings = find_stale([("tests/test_a.py", "src/a.py")], commits, min_changes=3)
    assert count == 1
    assert findings[0]["kind"] == "stale-test"
    assert "changed 3 times" in findings[0]["message"]


def test_a_test_changed_alongside_its_source_is_not_stale():
    commits = {"tests/test_a.py": [0], "src/a.py": [0, 1, 2]}
    assert find_stale([("tests/test_a.py", "src/a.py")], commits, min_changes=1) == (0, [])


def test_stale_is_not_scored_without_history_for_both_files():
    commits = {"src/a.py": [0, 1, 2, 3]}
    assert find_stale([("tests/test_a.py", "src/a.py")], commits, min_changes=1) == (0, [])


# -------------------------------------------------------------- decorative


def test_decorative_flags_only_measured_files_under_the_threshold():
    pairs = [
        ("tests/test_a.py", "src/a.py"),
        ("tests/test_b.py", "src/b.py"),
        ("tests/test_c.py", "src/c.py"),
    ]
    coverage = {"src/a.py": 12.0, "src/b.py": 80.0}
    count, findings = find_decorative(pairs, coverage, threshold=30)
    assert count == 1
    assert findings[0]["file"] == "tests/test_a.py"
    assert "12% covered" in findings[0]["message"]
