@domain:command-line @area:cli-options @from:gradebook-tests/cli
Feature: Running a test-suite scan from the command line
  Gives an operator the test-suite grade of a repository in the format their terminal, pull request or pipeline needs, and refuses bad inputs clearly.

  @id:gradebook-tests.command-line.cli-options.001 @rule:tests.cli.output-format @verified @source:gradebook-tests/gradebook_tests/cli.py#_emit @test:gradebook-tests/tests/test_gradebook_tests.py#test_cli_json_output_and_fail_under
  Scenario Outline: The report is printed in the requested format
    Given a repository with source files and tests to grade
    When the operator runs gradebook-tests with --format <format>
    Then standard output holds <output>
    And the exit code is 0

    Examples:
      | format         | output                                                                                                   |
      | text (default) | the plain-text terminal report                                                                           |
      | markdown       | the Markdown report                                                                                      |
      | json           | one JSON document with the score, dimensions, findings and recommendations, usable later as a --baseline |

  @id:gradebook-tests.command-line.cli-options.002 @rule:tests.cli.recommendation-count @inferred @source:gradebook-tests/gradebook_tests/cli.py#main
  Scenario Outline: The number of recommendations follows the requested count
    Given a repository whose suite loses points on several dimensions
    When the operator runs gradebook-tests with --top <n>
    Then at most <n> recommendations are reported, each naming a dimension, the points it would win back and advice

    Examples:
      | n           |
      | 5 (default) |
      | 2           |

  @id:gradebook-tests.command-line.cli-options.003 @rule:tests.cli.rejects-missing-directory @verified @source:gradebook-tests/gradebook_tests/cli.py#main @test:gradebook-tests/tests/test_gradebook_tests.py#test_cli_rejects_missing_path
  Scenario: A path that is not a directory is refused
    Given the path "./no-such-repo" does not exist or is a file
    When the operator runs gradebook-tests on that path
    Then stderr says "gradebook-tests: not a directory: ./no-such-repo"
    And the exit code is 2

  @id:gradebook-tests.command-line.cli-options.004 @rule:tests.cli.rejects-unusable-baseline @verified @source:gradebook-tests/gradebook_tests/cli.py#main @test:gradebook-tests/tests/test_gradebook_tests.py#test_cli_rejects_an_unreadable_baseline
  Scenario Outline: A baseline that cannot be read as an earlier report is refused
    Given a repository with source files and tests to grade
    And the baseline file <baseline>
    When the operator runs gradebook-tests with --baseline pointing at that file
    Then stderr says "gradebook-tests: cannot read baseline" followed by the file and the reason
    And no report is printed
    And the exit code is 2

    Examples:
      | baseline                                                     |
      | does not exist                                               |
      | is not valid JSON                                            |
      | is JSON but has no score, so is not a gradebook-tests report |

  @id:gradebook-tests.command-line.cli-options.005 @rule:tests.cli.list-dimensions @inferred @source:gradebook-tests/gradebook_tests/cli.py#main
  Scenario: Listing the dimensions prints the scoring model without scanning
    When the operator runs gradebook-tests with --list-dimensions
    Then each dimension is printed with its key, its weight in points and its title
    And the mutation dimension is marked as scored only when a mutation report exists
    And a note says the always-scored dimensions total 100 and unjudgeable ones are left unscored with the weights renormalised
    And the exit code is 0
