@domain:command-line-ci @area:invocation @from:gradebook-code/cli
Feature: Running a code score from the command line
  Gives an operator one command that scores a directory and prints a report people or other tools can read, refusing input it cannot score.

  @id:gradebook-code.command-line-ci.invocation.001 @rule:gradebook-code.cli.json-report @verified @source:gradebook-code/gradebook_code/cli.py#main @test:gradebook-code/tests/test_gradebook_code.py#test_cli_json_and_gates @test:gradebook-code/tests/test_gradebook_code.py#test_end_to_end_a_git_repo_through_the_module
  Scenario Outline: The JSON report carries the score, findings and ranked recommendations
    Given a repository with a function far over the complexity limit
    When the operator runs gradebook-code on the repository with --format json --top <top>
    Then stdout is one JSON document with a score below 100 and a grade
    And every finding carries a file and a line
    And recommendations list at most <top> entries, each with dimension, points and advice
    And the exit status is 0

    Examples:
      | top |
      | 5   |
      | 1   |

  @id:gradebook-code.command-line-ci.invocation.002 @rule:gradebook-code.cli.path-must-be-directory @verified @source:gradebook-code/gradebook_code/cli.py#main @test:gradebook-code/tests/test_gradebook_code.py#test_cli_rejects_bad_input
  Scenario Outline: A path that is not a directory is refused
    Given <path> <state>
    When the operator runs gradebook-code on <path>
    Then nothing is scored
    And stderr says "gradebook-code: not a directory: <path>"
    And the exit status is 2

    Examples:
      | path        | state          |
      | missing     | does not exist |
      | README.md   | is a file      |

  @id:gradebook-code.command-line-ci.invocation.003 @rule:gradebook-code.cli.version-reported @inferred @source:gradebook-code/gradebook_code/cli.py#_build_parser
  Scenario: The command reports its version
    Given gradebook-code 0.4.2 is installed
    When the operator runs gradebook-code --version
    Then stdout reads "gradebook-code 0.4.2"
    And the exit status is 0
