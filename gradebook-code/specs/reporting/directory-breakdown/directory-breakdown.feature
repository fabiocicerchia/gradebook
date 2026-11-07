@domain:reporting @area:directory-breakdown @from:gradebook-code/render
Feature: Scoring each directory
  Shows a developer which top-level directory drags the score down, so they know where to start.

  Background:
    Given a repository whose top level holds the directories good/ and bad/, each with source code

  @id:gradebook-code.reporting.directory-breakdown.001 @rule:reporting.directory-breakdown.worst-first @verified @source:gradebook-code/gradebook_code/render.py#score_directories @test:gradebook-code/tests/test_gradebook_code.py#test_by_dir_ranks_the_worst_first
  Scenario: Each code directory is scored on its own and listed worst first
    Given bad/ holds a heavily branching function and good/ holds a small clean one
    When the developer runs gradebook-code with --by-dir
    Then a "By directory (worst first):" section lists bad before good
    And each row shows the directory's grade, its score, its name, its file count and its single biggest win after "→"

  @id:gradebook-code.reporting.directory-breakdown.002 @rule:reporting.directory-breakdown.only-code-directories @inferred @source:gradebook-code/gradebook_code/render.py#score_directories
  Scenario: Vendored, artifact and code-free directories are left out of the breakdown
    Given the repository also has node_modules/, a build output directory and docs/ holding only Markdown
    When the developer runs gradebook-code with --by-dir
    Then only bad and good are listed
    And node_modules, the build output directory and docs do not appear

  @id:gradebook-code.reporting.directory-breakdown.003 @rule:reporting.directory-breakdown.markdown-omits-breakdown @inferred @source:gradebook-code/gradebook_code/render.py#render_markdown @questionable
  Scenario: The Markdown report leaves out the directory breakdown even when it was asked for
    Given bad/ and good/ both hold source code
    When the developer runs gradebook-code with --format markdown --by-dir
    Then the report shows the score heading and the principle table
    And no per-directory section appears
