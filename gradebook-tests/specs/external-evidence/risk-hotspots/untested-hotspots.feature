@domain:external-evidence @area:risk-hotspots @from:gradebook-tests/git
Feature: Finding often-changed code that has no tests
  Points a team at the files that change most often but have no test file, since that is where the next bug is most likely.

  Background:
    Given the repository under scan is a git working tree

  @id:gradebook-tests.external-evidence.risk-hotspots.001 @rule:risk.hotspots.untested-hot-file-flagged @verified @source:gradebook-tests/gradebook_tests/git.py#find_hotspots @test:gradebook-tests/tests/test_gradebook_tests.py#test_risk_targeting_flags_untested_hotspots @test:gradebook-tests/tests/integration/test_scan_a_git_repo.py#test_a_git_repo_is_scored_from_its_history_coverage_and_ci @questionable
  Scenario: A frequently changed file with no test file is flagged as an untested hotspot
    Given "src/hot.py", "src/warm.py" and "src/quiet.py" were each changed in 5 commits
    And only "src/quiet.py" has a matching test file
    When the operator scans the repository
    Then an "untested-hotspot" red flag is reported for "src/hot.py" and for "src/warm.py"
    And each flag's message reads "changed 5 times and has no test file — the code that breaks most often is untested"
    And no hotspot flag is reported for "src/quiet.py"
    And the Risk targeting detail reads "1/3 of the most-changed files have tests"

  @id:gradebook-tests.external-evidence.risk-hotspots.002 @rule:risk.hotspots.needs-enough-churn @inferred @source:gradebook-tests/gradebook_tests/git.py#find_hotspots
  Scenario: Risk targeting is not scored when too few files have changed more than once
    Given fewer than 3 source files have changed in more than one commit
    When the operator scans the repository
    Then no "untested-hotspot" red flags are reported
    And "Risk targeting" is listed as not scored, with the detail "no churn history to rank by"
