@domain:reporting @area:text-report @from:gradebook-tests/render
Feature: Reading the test-suite score in the terminal
  Gives a developer or CI reader a plain-text summary of the score, the grade, each dimension and the fixes that would gain the most points, so they can act on it without opening the JSON.

  Background:
    Given a repository has been scanned by gradebook-tests

  @id:gradebook-tests.reporting.text-report.001 @rule:reporting.text-report.headline-and-dimension-rows @verified @source:gradebook-tests/gradebook_tests/render.py#render_text @test:gradebook-tests/tests/test_gradebook_tests.py#test_unscored_rows_line_up_with_scored_ones
  Scenario: The terminal report shows the scan summary, one bar per dimension and the overall score and grade
    Given the scan found 12 source files, 8 test files, 40 test cases and 95 assertions
    And the suite scored 72.4 out of 100, grade C
    When the developer runs gradebook-tests with the default text format
    Then the first line names gradebook-tests, its version and the scanned path
    And a line lists the detected languages with their file counts, or "none"
    And a line reads "12 source files · 8 test files · 40 test cases · 95 assertions"
    And every dimension has one row with its title, a 20-character bar, its points out of its weight and its detail
    And a line reads "SCORE  72.4/100   grade C"

  @id:gradebook-tests.reporting.text-report.002 @rule:reporting.report.unscored-dimension-shown-as-not-applicable @verified @source:gradebook-tests/gradebook_tests/render.py#render_text @test:gradebook-tests/tests/test_gradebook_tests.py#test_unscored_rows_line_up_with_scored_ones
  Scenario Outline: A dimension with no evidence is shown as not applicable and listed as not scored, never as zero
    Given the repository has no git history, so the TDD dimension cannot be judged
    When the developer runs gradebook-tests with the <format> format
    Then the TDD dimension's row shows "n/a" in place of its points
    And the report lists it after "<label>" with the note that weights were redistributed

    Examples:
      | format   | label                                |
      | text     | not scored (weights redistributed):  |
      | markdown | _Not scored (weights redistributed): |

  @id:gradebook-tests.reporting.text-report.003 @rule:reporting.report.baseline-delta-shown @inferred @source:gradebook-tests/gradebook_tests/render.py#render_text
  Scenario Outline: Against a baseline the report shows how the total and each dimension moved, and warns when the two are not comparable
    Given an earlier report scored <baseline_score>
    And the current scan scores <score>
    And the earlier report <same_dims> the same set of dimensions
    When the developer runs gradebook-tests with --baseline pointing at the earlier report
    Then the headline reads "<headline>"
    And each dimension row shows its signed change, or "·" when it did not move
    And <note>

    Examples:
      | baseline_score | score | same_dims     | headline                                            | note                                                                                                   |
      | 70.0           | 72.4  | scored        | SCORE  72.4/100   grade C   +2.4 vs baseline (70.0) | no comparability note is printed                                                                       |
      | 75.0           | 72.4  | did not score | SCORE  72.4/100   grade C   -2.6 vs baseline (75.0) | a note says the baseline scored a different set of dimensions and the total is not directly comparable |

  @id:gradebook-tests.reporting.text-report.004 @rule:reporting.report.biggest-wins-listed @inferred @source:gradebook-tests/gradebook_tests/render.py#render_text
  Scenario: The report lists the fixes worth the most points, each with its advice
    Given the developer asks for the top 3 recommendations
    When the developer runs gradebook-tests with --top 3
    Then a "Biggest wins" section lists at most 3 dimensions
    And each entry shows the points it would recover, the dimension title and its advice

  @id:gradebook-tests.reporting.text-report.005 @rule:reporting.report.directory-breakdown-listed @inferred @source:gradebook-tests/gradebook_tests/render.py#render_directories
  Scenario: With the per-directory breakdown each directory shows its grade, score, file counts and biggest win
    Given the repository has the directories api and web, each holding code
    When the developer runs gradebook-tests with --by-dir
    Then a "By directory" section lists api and web
    And each directory shows its grade, its score, its source and test file counts and its biggest win
