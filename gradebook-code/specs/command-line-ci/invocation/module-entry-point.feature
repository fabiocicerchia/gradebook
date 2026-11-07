@domain:command-line-ci @area:invocation @from:gradebook-code/gradebook-code
Feature: Running gradebook-code as a Python module
  Editor plugins and CI jobs run `python3 -m gradebook_code` and need the same report and exit status as the `gradebook-code` command, so a quality gate fails the job in the same way either way.

  Background:
    Given a git repository with source code to grade

  @id:gradebook-code.command-line-ci.invocation.004 @rule:gradebook-code.invocation.module-runs-the-same-command @verified @source:gradebook-code/gradebook_code/__main__.py#main @test:gradebook-code/tests/test_gradebook_code.py#test_end_to_end_a_git_repo_through_the_module
  Scenario Outline: Running the tool as a Python module gives the same report and exit status as the command
    Given a baseline report saved from an earlier run of the same repository
    When the CI job runs "python3 -m gradebook_code" on the repository with <options>
    Then the output is <output>
    And the process exits with status <status>

    Examples:
      | options                                   | output                                                                            | status |
      | --format json                             | a JSON report that includes findings and recommendations                          | 0      |
      | --format markdown --by-dir                | a Markdown report with a "| Principle |" table                                    | 0      |
      | --baseline baseline.json --fail-under 100 | a text report showing "+0.0 vs baseline", with "below --fail-under 100" on stderr | 1      |
