"""Reading coverage reports, and whether CI runs the suite at all."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .base import FRACTION_AS_PERCENT, PERCENT_MAX
from .detection import read_text

# ----------------------------------------------------------------- coverage

COVERAGE_CONFIG_FILES = {
    ".coveragerc",
    "setup.cfg",
    "pyproject.toml",
    "tox.ini",
    "pytest.ini",
    "package.json",
    "jest.config.js",
    "jest.config.ts",
    "jest.config.mjs",
    "jest.config.json",
    ".nycrc",
    ".nycrc.json",
    ".nycrc.yml",
    "vitest.config.ts",
    "vitest.config.js",
    "codecov.yml",
    ".codecov.yml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    ".simplecov",
    "Makefile",
    "phpunit.xml",
    "phpunit.xml.dist",
    "sonar-project.properties",
    "Cargo.toml",
    "karma.conf.js",
}
COVERAGE_TOOL_RE = re.compile(
    r"--cov\b|\bcoverage\b|\bnyc\b|istanbul|jacoco|codecov|coveralls|simplecov|tarpaulin"
    r"|-coverprofile|opencover|\bc8\b|clover|pytest-cov|@vitest/coverage",
    re.IGNORECASE,
)
THRESHOLD_PATTERNS = [
    re.compile(r"fail_under\s*[:=]\s*(\d{1,3})"),
    re.compile(r"--cov-fail-under[=\s]+(\d{1,3})"),
    re.compile(r"--fail-under[=\s]+(\d{1,3})"),
    re.compile(r"coverageThreshold[\s\S]{0,400}?[\"']?(?:lines|statements)[\"']?\s*:\s*(\d{1,3})"),
    re.compile(r"check-coverage[\s\S]{0,300}?lines[\"'=:\s]+(\d{1,3})"),
    re.compile(r"minimum_coverage\s*[:=\s]\s*(\d{1,3})"),
    re.compile(r"(?:coverage[_-]?)?target:\s*(\d{1,3})%?"),
    re.compile(r"<minimum>\s*0?\.(\d{1,2})\s*</minimum>"),
]


def parse_cobertura(text: str) -> float | None:
    m = re.search(r'line-rate="([0-9.]+)"', text)
    return round(float(m.group(1)) * 100, 1) if m else None


def parse_lcov(text: str) -> float | None:
    found = sum(int(x) for x in re.findall(r"^LF:(\d+)", text, re.MULTILINE))
    hit = sum(int(x) for x in re.findall(r"^LH:(\d+)", text, re.MULTILINE))
    return round(hit / found * 100, 1) if found else None


def parse_jacoco(text: str) -> float | None:
    counters = re.findall(r'<counter type="LINE" missed="(\d+)" covered="(\d+)"', text)
    if not counters:
        return None
    missed, covered = max(((int(a), int(b)) for a, b in counters), key=sum)
    total = missed + covered
    return round(covered / total * 100, 1) if total else None


def parse_go_profile(text: str) -> float | None:
    total = covered = 0
    for line in text.splitlines():
        m = re.match(r"^.+:\d+\.\d+,\d+\.\d+ (\d+) (\d+)$", line)
        if m:
            statements, count = int(m.group(1)), int(m.group(2))
            total += statements
            if count > 0:
                covered += statements
    return round(covered / total * 100, 1) if total else None


def parse_json_report(text: str) -> float | None:
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    if isinstance(data, dict):
        totals = data.get("totals")
        if isinstance(totals, dict) and "percent_covered" in totals:
            return round(float(totals["percent_covered"]), 1)
        total = data.get("total")
        if isinstance(total, dict):
            lines = total.get("lines")
            if isinstance(lines, dict) and "pct" in lines:
                return round(float(lines["pct"]), 1)
    return None


def cobertura_files(text: str) -> dict[str, float]:
    out = {}
    for tag in re.finditer(r"<class\b[^>]*>", text):
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', tag.group(0)))
        if "filename" in attrs and "line-rate" in attrs:
            out[Path(attrs["filename"]).name] = round(float(attrs["line-rate"]) * 100, 1)
    return out


def lcov_files(text: str) -> dict[str, float]:
    out = {}
    current, found, hit = None, 0, 0
    for line in text.splitlines():
        if line.startswith("SF:"):
            current, found, hit = line[3:], 0, 0
        elif line.startswith("LF:"):
            found = int(line[3:] or 0)
        elif line.startswith("LH:"):
            hit = int(line[3:] or 0)
        elif line.startswith("end_of_record") and current and found:
            out[Path(current).name] = round(hit / found * 100, 1)
            current = None
    return out


def jacoco_files(text: str) -> dict[str, float]:
    out = {}
    for block in re.finditer(r"<sourcefile[^>]*name=\"([^\"]+)\"[^>]*>(.*?)</sourcefile>", text, re.DOTALL):
        counters = re.findall(r'<counter type="LINE" missed="(\d+)" covered="(\d+)"', block.group(2))
        if counters:
            missed, covered = (int(counters[-1][0]), int(counters[-1][1]))
            total = missed + covered
            if total:
                out[Path(block.group(1)).name] = round(covered / total * 100, 1)
    return out


def go_profile_files(text: str) -> dict[str, float]:
    totals = {}
    for line in text.splitlines():
        match = re.match(r"^(.+?):\d+\.\d+,\d+\.\d+ (\d+) (\d+)$", line)
        if not match:
            continue
        name = Path(match.group(1)).name
        statements, count = int(match.group(2)), int(match.group(3))
        covered, total = totals.get(name, (0, 0))
        totals[name] = (covered + (statements if count else 0), total + statements)
    return {name: round(c / t * 100, 1) for name, (c, t) in totals.items() if t}


def json_report_files(text: str) -> dict[str, float]:
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return {}
    out = {}
    if isinstance(data, dict):
        files = data.get("files")
        if isinstance(files, dict):  # python coverage json
            for path, entry in files.items():
                pct = (entry or {}).get("summary", {}).get("percent_covered")
                if isinstance(pct, (int, float)):
                    out[Path(path).name] = round(float(pct), 1)
        for path, entry in data.items():  # istanbul summary
            if path in {"total", "files", "totals"} or not isinstance(entry, dict):
                continue
            pct = (entry.get("lines") or {}).get("pct")
            if isinstance(pct, (int, float)):
                out[Path(path).name] = round(float(pct), 1)
    return out


PER_FILE_COVERAGE = {
    parse_cobertura: cobertura_files,
    parse_lcov: lcov_files,
    parse_jacoco: jacoco_files,
    parse_go_profile: go_profile_files,
    parse_json_report: json_report_files,
}


COVERAGE_REPORTS = [
    (re.compile(r"^(?:coverage|cobertura(?:-coverage)?|clover)\.xml$"), parse_cobertura),
    (re.compile(r"^jacoco.*\.xml$", re.IGNORECASE), parse_jacoco),
    (re.compile(r"^lcov\.info$|\.lcov$"), parse_lcov),
    (re.compile(r"^(?:coverage-summary|coverage-final|coverage)\.json$"), parse_json_report),
    (re.compile(r"^(?:coverage|cover|profile)\.(?:out|cov)$"), parse_go_profile),
]


def measure_coverage(rel: Path, path: Path) -> tuple[float | None, dict[str, float]]:
    """Return (total_percent, {basename: percent}) for a coverage report."""
    for pattern, parser in COVERAGE_REPORTS:
        if pattern.search(rel.name):
            text = read_text(path)
            if text is None:
                return None, {}
            # A JaCoCo report whose filename says nothing: cobertura's pattern
            # matched it first, and only the body tells the two apart.
            looks_jacoco = (
                rel.name.endswith(".xml")
                and "jacoco" not in rel.name.lower()
                and "<counter" in text
                and "line-rate" not in text
            )
            chosen = parse_jacoco if looks_jacoco else parser
            total = chosen(text)
            if total is None:
                return None, {}
            return total, PER_FILE_COVERAGE[chosen](text)
    return None, {}


def parse_stryker(text: str) -> float | None:
    """Stryker mutation.json: files -> mutants -> status."""
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    files = data.get("files")
    if not isinstance(files, dict):
        return None
    killed = total = 0
    for entry in files.values():
        for mutant in (entry or {}).get("mutants", []):
            status = str(mutant.get("status", "")).lower()
            if status in {"killed", "timeout"}:
                killed += 1
                total += 1
            elif status in {"survived", "nocoverage", "no coverage"}:
                total += 1
    return round(killed / total * 100, 1) if total else None


def parse_pitest(text: str) -> float | None:
    """PIT mutations.xml: <mutation detected='true' status='KILLED'>."""
    detections = re.findall(r"<mutation[^>]*\bdetected=[\"']([a-z]+)[\"']", text, re.IGNORECASE)
    if not detections:
        return None
    killed = sum(1 for d in detections if d.lower() == "true")
    return round(killed / len(detections) * 100, 1)


def parse_cargo_mutants(text: str) -> float | None:
    """cargo-mutants outcomes.json: summary per mutant."""
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    outcomes = data.get("outcomes") if isinstance(data, dict) else None
    if not isinstance(outcomes, list):
        return None
    caught = missed = 0
    for outcome in outcomes:
        summary = str((outcome or {}).get("summary", "")).lower()
        if summary in {"caughtmutant", "caught"}:
            caught += 1
        elif summary in {"missedmutant", "missed"}:
            missed += 1
    total = caught + missed
    return round(caught / total * 100, 1) if total else None


def parse_generic_mutation(text: str) -> float | None:
    """Anything exposing a mutation score directly."""
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    for key in ("mutationScore", "mutation_score", "score"):
        value = data.get(key)
        if isinstance(value, (int, float)) and 0 <= value <= PERCENT_MAX:
            return round(float(value), 1)
    return None


MUTATION_REPORTS = [
    (re.compile(r"^mutations?\.xml$|^mutations-report\.xml$", re.IGNORECASE), parse_pitest),
    (re.compile(r"^outcomes\.json$"), parse_cargo_mutants),
    (re.compile(r"^(?:mutation|stryker)[\w.-]*\.json$", re.IGNORECASE), parse_stryker),
]


def measure_mutation(rel: Path, path: Path) -> float | None:
    for pattern, parser in MUTATION_REPORTS:
        if pattern.search(rel.name):
            text = read_text(path)
            if text is None:
                return None
            return parser(text) or (parse_generic_mutation(text) if rel.suffix == ".json" else None)
    return None


def find_threshold(texts: list[str]) -> float | None:
    best = None
    for text in texts:
        for pattern in THRESHOLD_PATTERNS:
            for raw in pattern.findall(text):
                value = int(raw)
                if pattern.pattern.startswith("<minimum>"):
                    value = value * 10 if value < FRACTION_AS_PERCENT else value
                if 1 <= value <= PERCENT_MAX:
                    best = value if best is None else max(best, value)
    return best


# ----------------------------------------------------------------------- CI

CI_FILES = re.compile(
    r"^(?:\.gitlab-ci\.ya?ml|Jenkinsfile|azure-pipelines\.ya?ml"
    r"|\.travis\.ya?ml|bitbucket-pipelines\.ya?ml|\.drone\.ya?ml)$"
)
TEST_CMD_RE = re.compile(
    r"\bpytest\b|\btox\b|\bnox\b|python -m unittest|npm (?:run )?test|yarn test|pnpm test"
    r"|\bjest\b|\bvitest\b|\bmocha\b|\bcypress run\b|playwright test|go test|mvn .*test"
    r"|gradle\w* .*test|\brspec\b|\bphpunit\b|cargo test|dotnet test|make test|\bbats\b"
    r"|\bbehave\b|\bcucumber\b|mix test",
    re.IGNORECASE,
)
CI_COVERAGE_RE = re.compile(r"codecov|coveralls|--cov|coverprofile|coverage", re.IGNORECASE)
CI_STRICT_RE = re.compile(
    r"strategy:\s*\n\s*matrix|matrix:|-race\b|--strict|fail-fast"
    r"|--fail-under|coverageThreshold|--check-coverage",
    re.IGNORECASE,
)


def is_ci_file(rel: Path) -> bool:
    parts = [p.lower() for p in rel.parts]
    if ".github" in parts and "workflows" in parts and rel.suffix in {".yml", ".yaml"}:
        return True
    if ".circleci" in parts and rel.name in {"config.yml", "config.yaml"}:
        return True
    return bool(CI_FILES.match(rel.name))
