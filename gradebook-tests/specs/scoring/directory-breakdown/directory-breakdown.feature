@domain:scoring @area:directory-breakdown @from:gradebook-tests/score
Feature: Scoring each top-level directory
  Shows a maintainer of a multi-part repo which top-level directory drags the grade down and the single biggest fix for it.

  Background:
    Given the maintainer asks for a per-directory breakdown of a repository

  @id:gradebook-tests.scoring.directory-breakdown.001 @rule:scoring.directory-breakdown.weakest-first-with-top-win @verified @source:gradebook-tests/gradebook_tests/score.py#score_directories @test:gradebook-tests/tests/test_gradebook_tests.py#test_score_directories_ranks_the_weakest_first
  Scenario: Directories are listed weakest first, each with its biggest win
    Given directory "good" has tests, a coverage report and an error-path test
    And directory "bad" has source code and no tests
    When the maintainer scores the repository by directory
    Then "bad" is listed before "good"
    And each directory shows its own score, grade, source files, test files and test cases
    And each directory shows the advice and points of its top recommendation

  @id:gradebook-tests.scoring.directory-breakdown.002 @rule:scoring.directory-breakdown.only-directories-with-code @verified @source:gradebook-tests/gradebook_tests/score.py#score_directories @test:gradebook-tests/tests/test_gradebook_tests.py#test_score_directories_skips_directories_without_code
  Scenario Outline: Directories without code, and vendored or build directories, are left out of the breakdown
    Given the repository has a directory "<directory>" that <contents>
    When the maintainer scores the repository by directory
    Then "<directory>" does not appear in the breakdown

    Examples:
      | directory    | contents                  |
      | docs         | holds only Markdown       |
      | node_modules | holds vendored JavaScript |
      | build        | holds build output        |
