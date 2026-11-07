@domain:reporting @area:red-flags @from:gradebook-tests/collection
Feature: Listing the suite's findings
  Serves maintainers reading the red flags: findings come out ranked by how much they matter, each with a severity, so the worst problems are read first.

  Background:
    Given a repository whose test suite has several kinds of problems

  @id:gradebook-tests.reporting.red-flags.001 @rule:tests.findings.ranked-and-severity-tagged @verified @source:gradebook-tests/gradebook_tests/collection.py#collect @test:gradebook-tests/tests/test_gradebook_tests.py#test_every_finding_carries_a_known_severity
  Scenario: Findings are listed by flag rank, then file, then line, and each carries a severity
    Given the suite has findings of several kinds across several files
    When the maintainer grades the test suite
    Then findings of a higher-ranked kind come before lower-ranked ones
    And within one kind, findings are ordered by file and then line
    And every finding has a severity of high, medium or low

  @id:gradebook-tests.reporting.red-flags.002 @rule:tests.findings.unit-test-doing-real-io-flagged @verified @source:gradebook-tests/gradebook_tests/collection.py#_fold_test_file @test:gradebook-tests/tests/test_gradebook_tests.py#test_unit_tests_doing_real_io_are_flagged @questionable
  Scenario: A unit test that talks to a real database, HTTP service or browser is flagged as a disguised integration test
    Given a test file under "tests/unit/" uses a real database container
    When the maintainer grades the test suite
    Then one "conjoined-twin" finding is listed for that file
    And its message says it is filed as a unit test but is an integration test
    And it points at line 0 of the file

  @id:gradebook-tests.reporting.red-flags.003 @rule:tests.findings.per-file-caps @inferred @source:gradebook-tests/gradebook_tests/collection.py#_fold_test_file @questionable
  Scenario: Each test file contributes at most five mirror-assertion findings and five brittle-selector findings
    Given one test file has 8 assertions that mirror the code and 8 brittle selectors
    When the maintainer grades the test suite
    Then 5 mirror-assertion findings and 5 brittle-selector findings are listed for that file
    And the mirror-assertion and brittle-selector totals still count all 8 of each
