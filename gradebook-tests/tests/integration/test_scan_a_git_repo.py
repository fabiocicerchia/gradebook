"""The scanner against its real collaborators: a git history, a coverage report
and a CI workflow on disk, and a baseline written to a file and read back."""

import json
import shutil
import subprocess

from gradebook_tests import main

GIT = shutil.which("git") or "git"
ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@e",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@e",
    "PATH": "/usr/bin:/bin",
}


def write(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def git(root, *args):
    subprocess.run([GIT, "-C", str(root), *args], check=True, env=ENV)  # nosec B603 — fixed argv


def commit(root, message):
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


def scan(root, capsys, *args):
    code = main([str(root), "--format", "json", *args])
    return code, json.loads(capsys.readouterr().out)


def dim(report, key):
    return next(d for d in report["dimensions"] if d["id"] == key)


def test_a_git_repo_is_scored_from_its_history_coverage_and_ci(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    write(repo, ".github/workflows/ci.yml", "jobs:\n  test:\n    steps:\n      - run: pytest --cov=src\n")
    write(repo, "coverage.xml", '<coverage line-rate="0.82"></coverage>')
    write(repo, "src/billing.py", "def total():\n    return 0\n")
    write(repo, "tests/test_billing.py", "def test_total_is_zero_when_empty():\n    assert total() == 0\n")
    commit(repo, "feat: billing with tests")
    for i in range(1, 5):
        for name in ("billing", "hot", "warm"):
            write(repo, f"src/{name}.py", f"def {name}():\n    return {i}\n")
        commit(repo, f"feat: change {i}")

    code, report = scan(repo, capsys)
    assert code == 0
    assert report["stats"]["coverage_measured"] == 82.0
    assert dim(report, "ci")["score"] > 0
    assert report["stats"]["git"]["source_commits"] == 5
    assert report["stats"]["git"]["source_commits_with_tests"] == 1
    assert dim(report, "tdd")["score"] is not None
    assert dim(report, "risk")["score"] is not None
    hotspots = [f for f in report["findings"] if f["kind"] == "untested-hotspot"]
    assert {f["file"] for f in hotspots} == {"src/hot.py", "src/warm.py"}

    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps(report))
    write(repo, "tests/test_misc.py", "def test_1():\n    pass\n")
    commit(repo, "test: placeholder")

    code, current = scan(repo, capsys, "--baseline", str(baseline), "--fail-on-drop")
    assert code == 1
    assert current["baseline"]["comparable"] is True
    assert current["baseline"]["delta"] < 0
