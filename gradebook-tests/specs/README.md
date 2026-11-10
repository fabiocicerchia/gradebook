# Specifications of gradebook / gradebook-tests

What this code does, one atomic Gherkin scenario per behaviour, read from the code by code-atlas.
Tags: `@verified` a test asserts it · `@inferred` read from the code only · `@gap` an entry point no test covers · `@human` written or amended by a person, never rewritten.

## Command line
How people and CI run the tool and use its result.

- **Options and output formats**: [Running a test-suite scan from the command line](command-line/cli-options/tests-cli-run.feature) (5)
- **Packaging and entry points**: [Running gradebook-tests](command-line/packaging-entry/running-gradebook-tests.feature) (1)
- **CI quality gate**: [Failing a pipeline on the test-suite score](command-line/quality-gate/tests-ci-quality-gate.feature) (4)

## External evidence
Reads the results that test tools have already produced, plus the git history, without running anything.

- **Change history and TDD signals**: [Judging test-first discipline from change history](external-evidence/change-history/tdd-signals-from-history.feature) (4)
- **Coverage thresholds in CI**: [Detecting coverage thresholds and CI test runs](external-evidence/coverage-gates/coverage-gates.feature) (2)
- **Coverage reports**: [Reading measured coverage reports](external-evidence/coverage-reports/coverage-reports.feature) (4)
- **Mutation testing reports**: [Reading mutation testing reports](external-evidence/mutation-reports/mutation-reports.feature) (3)
- **Risk hotspots**: [Finding often-changed code that has no tests](external-evidence/risk-hotspots/untested-hotspots.feature) (2)

## Reporting
Shows the score, dimensions and red flags in a form people and tools can act on.

- **Markdown report**: [Posting the test-suite score as Markdown](reporting/markdown-report/markdown-report.feature) (1)
- **Red flag listing**: [Listing red flags with their location](reporting/red-flags/red-flag-listing.feature) (4), [Listing the suite's findings](reporting/red-flags/repository-findings-list.feature) (1)
- **Terminal report**: [Reading the test-suite score in the terminal](reporting/text-report/terminal-report.feature) (3)

## Repository scan
How gradebook-tests walks a working tree and decides what each file is before anything gets scored.

- **Config and CI discovery**: [Gathering the evidence a test-suite score is built from](repository-scan/config-and-ci-discovery/gathering-suite-evidence.feature) (2)
- **File discovery**: [Walking the repository](repository-scan/file-discovery/walking-the-repository.feature) (5)
- **Test file recognition**: [Recognising test files](repository-scan/test-file-recognition/recognising-test-files.feature) (3)
- **Test kind classification**: [Sorting tests into unit, integration and end-to-end](repository-scan/test-kind-classification/classifying-test-kinds.feature) (3)

## Scoring and grading
Turns the evidence into a weighted score and a letter grade, and says which fix is worth the most points.

- **Baseline comparison**: [Comparing a run against an earlier report](scoring/baseline-comparison/baseline-comparison.feature) (2)
- **Per-directory breakdown**: [Scoring each top-level directory](scoring/directory-breakdown/directory-breakdown.feature) (2)
- **Overall score and grade**: [Scoring a test suite against the rubric](scoring/grades/scoring-a-test-suite.feature) (4)
- **Recommendations**: [Recommending the fixes worth the most points](scoring/recommendations/recommendations.feature) (2)
- **Finding severity**: [Ranking red flags by severity](scoring/severity/finding-severity.feature) (3)

## Test quality analysis
Checks inside each test file for the habits that make a suite trustworthy or hollow.

- **Skipped and suppressed tests**: [Flagging tests whose failures are silenced](test-quality-analysis/suppressed-tests/flagging-silenced-failures.feature) (2)
- **Test naming**: [Judging whether test names describe behaviour](test-quality-analysis/test-naming/judging-test-names.feature) (2)
- **Test substance**: [Flagging tests coupled to the implementation](test-quality-analysis/test-substance/flagging-implementation-coupled-tests.feature) (4), [Spotting tests that pad the count without checking anything](test-quality-analysis/test-substance/test-substance.feature) (7)
