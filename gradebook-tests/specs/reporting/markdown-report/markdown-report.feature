@domain:reporting @area:markdown-report @from:gradebook-tests/render
Feature: Posting the test-suite score as Markdown
  Gives a reviewer a Markdown report to paste into a pull request or documentation, with the score in the heading and the dimensions as a table.

  Background:
    Given a repository has been scanned by gradebook-tests

  @id:gradebook-tests.reporting.markdown-report.001 @rule:reporting.markdown-report.score-heading-and-dimension-table @verified @source:gradebook-tests/gradebook_tests/render.py#render_markdown @test:gradebook-tests/tests/test_gradebook_tests.py#test_markdown_render_contains_table_and_score
  Scenario Outline: The Markdown report leads with the score and grade and tabulates every dimension
    Given the suite scored 72.4 out of 100, grade C
    And <baseline>
    When the developer runs gradebook-tests with --format markdown
    Then the report starts with the heading "## Test suite score: **72.4/100** (grade C)"
    And a line gives the scanned path with its source file, test file, test case and assertion counts
    And a table with the columns "<columns>" has one row per dimension

    Examples:
      | baseline                                    | columns                                 |
      | no baseline was given                       | Dimension | Score | Weight | Detail     |
      | an earlier report was given with --baseline | Dimension | Score | Δ | Weight | Detail |
