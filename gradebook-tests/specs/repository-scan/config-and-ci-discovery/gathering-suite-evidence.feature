@domain:repository-scan @area:config-and-ci-discovery @from:gradebook-tests/collection
Feature: Gathering the evidence a test-suite score is built from
  Serves maintainers running gradebook-tests: the score only means something if every coverage report, coverage config and CI workflow in the tree is found and counted once.

  Background:
    Given a repository with source files and a test suite

  @id:gradebook-tests.repository-scan.config-and-ci-discovery.002 @rule:tests.evidence.first-coverage-report-wins @inferred @source:gradebook-tests/gradebook_tests/collection.py#_scrape_config @questionable
  Scenario: Only the first coverage report found is used, and the report names it as the source
    Given the repository holds two coverage reports with different percentages
    When the maintainer grades the test suite
    Then the measured coverage comes from the report the scan reached first
    And the coverage detail names that report's path as the source
    And the second report's percentage is ignored

  @id:gradebook-tests.repository-scan.config-and-ci-discovery.003 @rule:tests.evidence.artifact-folders-cannot-declare-config-or-ci @inferred @source:gradebook-tests/gradebook_tests/collection.py#_scrape_config
  Scenario: Coverage settings and CI workflows inside build or coverage folders are not taken as the project's own
    Given the only coverage config declaring a threshold sits under "build/"
    When the maintainer grades the test suite
    Then no coverage threshold is reported
    And the file is not listed as coverage configuration or as a CI workflow
