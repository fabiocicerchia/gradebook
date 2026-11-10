@domain:reporting @area:output-formats @from:gradebook-code/render
Feature: Reading the code score report
  Gives a developer or reviewer the score, the per-principle breakdown and the biggest wins as terminal text or as Markdown they can paste into a pull request.

  Background:
    Given a repository with source code has been scored by gradebook-code

  @id:gradebook-code.reporting.output-formats.001 @rule:reporting.output-formats.text-shows-score-and-dimensions @verified @source:gradebook-code/gradebook_code/render.py#render_text @test:gradebook-code/tests/test_gradebook_code.py#test_renderers_contain_the_essentials
  Scenario: The text report shows the overall score, grade and every dimension with a score bar
    Given the repository scores 72.4 with grade B
    When the developer runs gradebook-code with the default text format
    Then the first line reads "gradebook-code <version> — <path>"
    And a languages line and a line counting files, lines, functions, classes and modules are shown
    And each dimension appears on its own row with a 20-character bar, points earned and its weight
    And the summary line reads "SCORE  72.4/100   grade B"

  @id:gradebook-code.reporting.output-formats.003 @rule:reporting.output-formats.generated-skip-count-shown @verified @source:gradebook-code/gradebook_code/render.py#render_text @test:gradebook-code/tests/test_gradebook_code.py#test_generated_files_are_excluded_from_the_score
  Scenario: The text report says how many generated files were skipped
    Given the repository contains 1 hand-written source file and 1 generated protobuf file
    When the developer runs gradebook-code with the default text format
    Then the counts line ends with "· 1 generated file(s) skipped"
    And the counts line reports 1 file

  @id:gradebook-code.reporting.output-formats.005 @rule:reporting.output-formats.markdown-summary @verified @source:gradebook-code/gradebook_code/render.py#render_markdown @test:gradebook-code/tests/test_gradebook_code.py#test_renderers_contain_the_essentials @test:gradebook-code/tests/test_gradebook_code.py#test_end_to_end_a_git_repo_through_the_module @questionable
  Scenario: The Markdown report gives a score heading and a principle table ready to paste
    Given the repository scores 72.4 with grade B
    When the developer runs gradebook-code with --format markdown
    Then the report opens with "## Code score: **72.4/100** (grade B)"
    And a table with columns Principle, Score, Weight and Detail has one row per dimension, unscored ones showing "n/a"
    And the language calibration, the generated-file skip count and any baseline delta are not shown
