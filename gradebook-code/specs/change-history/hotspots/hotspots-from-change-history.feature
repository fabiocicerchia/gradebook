@domain:change-history @area:hotspots @from:gradebook-code/churn
Feature: Finding hotspots in change history
  Shows the operator which files are both complex and frequently changed, because complexity where the changes land is the complexity that costs money to maintain.

  @id:gradebook-code.change-history.hotspots.001 @rule:change-history.churn.counts-recent-non-merge-commits @verified @source:gradebook-code/gradebook_code/churn.py#git_churn @test:gradebook-code/tests/test_gradebook_code.py#test_git_churn_counts_commits_per_file @test:gradebook-code/tests/test_gradebook_code.py#test_complexity_that_sits_where_the_changes_land_scores_badly @questionable
  Scenario: A file's change count is the number of recent non-merge commits that touched it
    Given a git repository where "src/billing.py" was added in one commit and changed in 7 later commits
    And a merge commit that also brought in changes to "src/billing.py"
    And "src/billing.py" is among the most complex and most changed files
    When the operator scans the repository with gradebook-code
    Then the hotspot flag for "src/billing.py" says it was "changed 8 times"
    And the merge commit is not counted
    And only the most recent 800 commits are looked at

  @id:gradebook-code.change-history.hotspots.002 @rule:change-history.churn.subdirectory-scan-matches-history @verified @source:gradebook-code/gradebook_code/churn.py#git_churn @test:gradebook-code/tests/test_gradebook_code.py#test_git_churn_strips_the_subdirectory_prefix
  Scenario: Scanning a subdirectory still matches each file to its history
    Given a git repository whose code lives under "src/"
    And "src/billing.py" has changed in many commits
    When the operator scans only the "src" directory
    Then the change history is attributed to "billing.py", the path the scan reports
    And history for files outside "src/" is ignored
    And the Hotspots dimension is scored from that history rather than left empty

  @id:gradebook-code.change-history.hotspots.003 @rule:change-history.hotspots.unscored-without-enough-history @verified @source:gradebook-code/gradebook_code/churn.py#find_hotspots @test:gradebook-code/tests/test_gradebook_code.py#test_hotspots_are_not_scored_without_history @test:gradebook-code/tests/test_gradebook_code.py#test_find_hotspots_needs_enough_files_and_churn @test:gradebook-code/tests/test_gradebook_code.py#test_git_churn_is_empty_outside_a_repository
  Scenario Outline: Hotspots are left unscored when there is not enough history to rank by
    Given <situation>
    When the operator scans the repository with gradebook-code
    Then the Hotspots dimension has no score
    And "Hotspots (churn x complexity)" is listed among the dimensions not scored
    And no hotspot flags are reported
    And the remaining dimensions decide the overall score

    Examples:
      | situation                                             |
      | the folder is not a git repository                    |
      | git is not installed                                  |
      | the repository has fewer than 5 source files          |
      | fewer than 3 source files have changed more than once |

  @id:gradebook-code.change-history.hotspots.004 @rule:change-history.hotspots.flags-complex-frequently-changed-files @verified @source:gradebook-code/gradebook_code/churn.py#find_hotspots @test:gradebook-code/tests/test_gradebook_code.py#test_complexity_that_sits_where_the_changes_land_scores_badly
  Scenario: A frequently changed file that is more complex than average is flagged as a hotspot
    Given a git repository with 9 source files
    And "src/billing.py" and "src/orders.py" are complex and changed in 8 commits each
    And the other files are simple, with at least one of them also changed more than once
    When the operator scans the repository with gradebook-code
    Then a hotspot red flag is reported at "src/billing.py:1" and at "src/orders.py:1"
    And each message reads "changed <n> times and carries <complexity> complexity (codebase average <average>) — the expensive kind"

  @id:gradebook-code.change-history.hotspots.005 @rule:change-history.hotspots.simple-churn-not-flagged @verified @source:gradebook-code/gradebook_code/churn.py#find_hotspots @test:gradebook-code/tests/test_gradebook_code.py#test_complexity_away_from_the_changes_scores_well
  Scenario: Frequently changed files that are no more complex than average are not flagged
    Given a git repository where "src/billing.py" and "src/orders.py" are simple but changed in 8 commits each, along with a third simple file
    And the most complex file, "src/tangle.py", has not changed since it was added
    When the operator scans the repository with gradebook-code
    Then no hotspot red flags are reported
    And the Hotspots dimension still receives a score

  @id:gradebook-code.change-history.hotspots.006 @rule:change-history.hotspots.only-most-changed-fifth-considered @inferred @source:gradebook-code/gradebook_code/churn.py#find_hotspots
  Scenario: Only the most-changed fifth of files, and at least three, can be hotspots
    Given a git repository with 20 source files, each changed at least twice
    And "src/report.py" is the most complex file but ranks 5th by number of changes
    When the operator scans the repository with gradebook-code
    Then only the 4 most-changed files are considered hot
    And "src/report.py" gets no hotspot flag
