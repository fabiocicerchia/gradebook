# Specifications of gradebook / gradebook-code

What this code does, one atomic Gherkin scenario per behaviour, read from the code by code-atlas.
Tags: `@verified` a test asserts it · `@inferred` read from the code only · `@gap` an entry point no test covers · `@human` written or amended by a person, never rewritten.

## Change History

Using git history to find where risk concentrates.

- **Hotspots**: [Finding hotspots in change history](change-history/hotspots/hotspots-from-change-history.feature) (6)

## Command Line and CI

Running the grader from a terminal or pipeline and gating builds on the result.

- **Invocation and options**: [Running a code score from the command line](command-line-ci/invocation/code-score-invocation.feature) (3), [Running gradebook-code as a Python module](command-line-ci/invocation/module-entry-point.feature) (1)
- **Quality gates**: [Gating a build on the code score](command-line-ci/quality-gates/code-score-quality-gates.feature) (5)
- **Scoring model listing**: [Listing the code scoring model](command-line-ci/scoring-model-listing/code-score-model-listing.feature) (1)

## Size and Complexity Checks

Detecting code that is too big, too deep or too convoluted to read.

- **File and class size**: [Flagging files that do too many jobs](complexity-checks/file-size/god-files-and-mixed-concerns.feature) (2)
- **Function limits**: [Flagging functions past the size and complexity limits](complexity-checks/function-limits/function-limits.feature) (3)

## Design and Structure Checks

Detecting structural design problems across files and modules.

- **Dead and speculative code**: [Spotting private helpers nobody calls](design-checks/dead-code/unused-private-helpers.feature) (2)
- **Dependency cycles and coupling**: [Reporting import cycles](design-checks/dependency-cycles/dependency-cycle-flags.feature) (1), [Detecting import cycles between the repository's own modules](design-checks/dependency-cycles/dependency-cycles.feature) (1)
- **Duplicate code**: [Finding code repeated across files](design-checks/duplication/duplicate-code.feature) (3)
- **Inheritance and interfaces**: [Flagging interfaces that are too wide](design-checks/inheritance-interfaces/fat-interface-flags.feature) (1)

## Reporting

Presenting the grade, red flags and recommendations to people and machines.

- **Per-directory breakdown**: [Scoring each directory](reporting/directory-breakdown/directory-breakdown.feature) (3)
- **Output formats**: [Reading the code score report](reporting/output-formats/report-formats.feature) (3)
- **Red flags**: [Listing red flags](reporting/red-flags/red-flag-listing.feature) (4)
- **Severity levels**: [Grading the severity of each finding](reporting/severity/finding-severity.feature) (2)

## Repository Scanning

Finding the source files worth grading in a working tree and preparing them for measurement.

- **Language profiles**: [Calibrating function limits to the languages in the repository](repository-scanning/language-profiles/language-calibrated-limits.feature) (3)
- **Comment and string stripping**: [Ignoring comments and string literals when measuring code](repository-scanning/noise-stripping/comment-and-string-stripping.feature) (4)
- **Generated and test file skipping**: [Recognising generated and minified files](repository-scanning/skipped-files/generated-file-recognition.feature) (5), [Leaving test files out of the code score](repository-scanning/skipped-files/test-files-left-out.feature) (1)
- **Source discovery**: [Choosing which files the scan reads](repository-scanning/source-discovery/source-walk-exclusions.feature) (2)

## Scoring and Grading

Turning measurements into weighted dimension scores, an overall grade and prioritised advice.

- **Overall score and letter grade**: [Turning the code score into a letter grade](scoring/letter-grade/code-letter-grade.feature) (1)
- **Design principle dimensions**: [Scoring design principles: SOLID, coupling, cohesion and Law of Demeter](scoring/principle-dimensions/principle-dimension-scores.feature) (4)
- **Recommendations**: [Recommending the fixes worth the most points](scoring/recommendations/code-biggest-wins.feature) (2)
- **Simplicity dimensions**: [Scoring simplicity: KISS, DRY, YAGNI, naming and hotspots](scoring/simplicity-dimensions/simplicity-dimension-scores.feature) (4)
- **Weighting and unscored dimensions**: [Leaving dimensions without evidence unscored](scoring/weighting/dimension-evidence.feature) (1), [Combining principle scores into one weighted code score](scoring/weighting/weighted-code-score.feature) (3)
