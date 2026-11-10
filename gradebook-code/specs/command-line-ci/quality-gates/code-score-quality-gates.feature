@domain:command-line-ci @area:quality-gates @from:gradebook-code/cli
Feature: Gating a build on the code score
  Lets a CI operator fail a pipeline when the code score is below a floor or has dropped against an earlier report, so quality cannot slip without anyone seeing it.

  Background:
    Given a repository with source code to score

  @id:gradebook-code.command-line-ci.quality-gates.001 @rule:gradebook-code.gates.fail-under-floor @verified @source:gradebook-code/gradebook_code/cli.py#_gate_failed @test:gradebook-code/tests/test_gradebook_code.py#test_cli_json_and_gates @test:gradebook-code/tests/test_gradebook_code.py#test_end_to_end_a_git_repo_through_the_module
  Scenario Outline: A score below the floor fails the run
    Given the repository scores <score>
    When the operator runs gradebook-code with --fail-under <floor>
    Then the report is still printed
    And the exit status is <status>
    And stderr says "<message>"

    Examples:
      | score | floor | status | message                                         |
      | 62.4  | 99    | 1      | gradebook-code: 62.4 is below --fail-under 99.0 |
      | 62.4  | 0     | 0      |                                                 |
      | 62.4  | 62.4  | 0      |                                                 |

  @id:gradebook-code.command-line-ci.quality-gates.002 @rule:gradebook-code.gates.fail-on-drop @verified @source:gradebook-code/gradebook_code/cli.py#_gate_failed @test:gradebook-code/tests/test_gradebook_code.py#test_cli_baseline_gate
  Scenario Outline: A score that drops against the baseline by more than the tolerance fails the run
    Given a baseline report that scored <baseline>
    And the repository now scores <current>
    When the operator runs gradebook-code with --baseline baseline.json --fail-on-drop <tolerance>
    Then the exit status is <status>
    And stderr says "<message>"

    Examples:
      | baseline | current | tolerance | status | message                                                 |
      | 80.0     | 80.0    | (none)    | 0      |                                                         |
      | 80.0     | 79.5    | (none)    | 1      | gradebook-code: dropped 0.5 points against the baseline |
      | 80.0     | 78.0    | 3         | 0      |                                                         |
      | 80.0     | 85.0    | (none)    | 0      |                                                         |

  @id:gradebook-code.command-line-ci.quality-gates.003 @rule:gradebook-code.gates.drop-gate-needs-baseline @verified @source:gradebook-code/gradebook_code/cli.py#main @test:gradebook-code/tests/test_gradebook_code.py#test_cli_rejects_bad_input
  Scenario: The drop gate is refused without a baseline
    When the operator runs gradebook-code with --fail-on-drop and no --baseline
    Then nothing is scored
    And stderr says "gradebook-code: --fail-on-drop needs --baseline"
    And the exit status is 2

  @id:gradebook-code.command-line-ci.quality-gates.004 @rule:gradebook-code.gates.unreadable-baseline-refused @verified @source:gradebook-code/gradebook_code/cli.py#main @test:gradebook-code/tests/test_gradebook_code.py#test_cli_rejects_bad_input @questionable
  Scenario Outline: An unreadable baseline report is refused
    Given the baseline file <problem>
    When the operator runs gradebook-code with --baseline baseline.json
    Then no report is printed
    And stderr says "gradebook-code: cannot read baseline baseline.json: ..."
    And the exit status is 2

    Examples:
      | problem                        |
      | does not exist                 |
      | is not valid JSON              |
      | is a JSON object with no score |

  @id:gradebook-code.command-line-ci.quality-gates.005 @rule:gradebook-code.gates.baseline-delta-shown @verified @source:gradebook-code/gradebook_code/cli.py#_emit @test:gradebook-code/tests/test_gradebook_code.py#test_end_to_end_a_git_repo_through_the_module @questionable
  Scenario Outline: The report shows how the score moved against the baseline
    Given a baseline report that scored <baseline>
    And the repository now scores <current>
    When the operator runs gradebook-code with --baseline baseline.json --format <format>
    Then <shown>

    Examples:
      | baseline | current | format   | shown                                                         |
      | 80.0     | 82.5    | text     | the score line reads "grade B   +2.5 vs baseline (80.0)"      |
      | 80.0     | 82.5    | json     | the report carries baseline.score 80.0 and baseline.delta 2.5 |
      | 80.0     | 82.5    | markdown | the report does not mention the baseline                      |
