@domain:reporting @area:red-flags @from:gradebook-tests/collection
Feature: Listing the suite's findings
  Serves maintainers reading the red flags: findings come out ranked by how much they matter, each with a severity, so the worst problems are read first.

  Background:
    Given a repository whose test suite has several kinds of problems

  @id:gradebook-tests.reporting.red-flags.003 @rule:tests.findings.per-file-caps @inferred @source:gradebook-tests/gradebook_tests/collection.py#_fold_test_file @questionable
  Scenario: Each test file contributes at most five mirror-assertion findings and five brittle-selector findings
    Given one test file has 8 assertions that mirror the code and 8 brittle selectors
    When the maintainer grades the test suite
    Then 5 mirror-assertion findings and 5 brittle-selector findings are listed for that file
    And the mirror-assertion and brittle-selector totals still count all 8 of each
