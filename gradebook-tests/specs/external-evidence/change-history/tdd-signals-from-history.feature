@domain:external-evidence @area:change-history @from:gradebook-tests/git
Feature: Judging test-first discipline from change history
  Gives a team lead evidence from git log of whether tests ship in the same commit as the code they cover and whether bug fixes come with regression tests.

  Background:
    Given the repository under scan is a git working tree

  @id:gradebook-tests.external-evidence.change-history.001 @rule:history.tdd.source-commits-cochanged-with-tests @verified @source:gradebook-tests/gradebook_tests/git.py#_tally_log @test:gradebook-tests/tests/test_gradebook_tests.py#test_tdd_rewards_tests_shipped_with_source @test:gradebook-tests/tests/test_gradebook_tests.py#test_tdd_penalises_untested_source_commits @test:gradebook-tests/tests/integration/test_scan_a_git_repo.py#test_a_git_repo_is_scored_from_its_history_coverage_and_ci
  Scenario Outline: Source commits that also change tests are counted as test-first evidence
    Given the last commits each changed a source file
    And only some of those commits also changed a test file
    When the operator scans the repository
    Then the report's git stats show how many source commits there were
    And the report's git stats show how many of them also touched tests
    And the TDD detail reads "<share>% of <source_commits> source commits also touched tests"

    Examples:
      | source_commits | with_tests | share |
      | 6              | 6          | 100   |
      | 6              | 0          | 0     |
      | 5              | 1          | 20    |

  @id:gradebook-tests.external-evidence.change-history.002 @rule:history.tdd.bugfixes-need-regression-tests @verified @source:gradebook-tests/gradebook_tests/git.py#_tally_log @test:gradebook-tests/tests/test_gradebook_tests.py#test_bugfixes_without_regression_tests_lower_tdd @test:gradebook-tests/tests/test_gradebook_tests.py#test_bugfixes_with_tests_do_not_lower_tdd
  Scenario: Bug-fix commits that ship no test are called out
    Given one commit added a source file with its test
    And five later commits with subjects like "fix: wrong value" changed only the source file
    When the operator scans the repository
    Then the report's git stats count 5 fix commits and 0 fix commits with tests
    And the TDD detail includes "0/5 bugfixes shipped a test"
    And the TDD advice says a fix without a regression test is a bug free to come back

  @id:gradebook-tests.external-evidence.change-history.003 @rule:history.tdd.subdirectory-scan-uses-scan-relative-paths @verified @source:gradebook-tests/gradebook_tests/git.py#git_history @test:gradebook-tests/tests/test_gradebook_tests.py#test_git_paths_are_relative_to_the_scan_not_the_repository
  Scenario: Scanning a subfolder of a repository still matches history to the files scanned
    Given the repository keeps a service in its "service" folder
    And one commit added "service/src/billing.py" together with "service/tests/test_billing.py"
    When the operator scans only the "service" folder
    Then the history lists the changed files as "src/billing.py" and "tests/test_billing.py"
    And the commit counts as 1 source commit that also touched tests
    And changes outside the "service" folder are not counted

  @id:gradebook-tests.external-evidence.change-history.004 @rule:history.tdd.no-history-leaves-git-dimensions-unscored @inferred @source:gradebook-tests/gradebook_tests/git.py#git_history
  Scenario: A folder with no readable git history gets no history-based scores
    Given the scanned folder is not a git repository, has no commits, or git is not installed
    When the operator scans it
    Then the report has no git stats
    And "TDD discipline" and "Risk targeting" are listed as not scored
    And their weight is spread over the other dimensions
