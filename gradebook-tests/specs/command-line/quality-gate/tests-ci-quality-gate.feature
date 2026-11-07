@domain:command-line @area:quality-gate @from:gradebook-tests/cli
Feature: Failing a pipeline on the test-suite score
  Lets a CI operator fail a build when the test suite's score falls below a floor or drops against an earlier report, so test quality cannot quietly decay.

  Background:
    Given a repository with source files and tests to grade

  @id:gradebook-tests.command-line.quality-gate.001 @rule:tests.gate.fail-under-floor @verified @source:gradebook-tests/gradebook_tests/cli.py#_gate_failed @test:gradebook-tests/tests/test_gradebook_tests.py#test_cli_json_output_and_fail_under
  Scenario Outline: A score below the required floor fails the run
    Given the repository's test suite scores <score>
    When the operator runs gradebook-tests with --fail-under <floor>
    Then the exit code is <exit>
    And the report is still printed on standard output
    And when the run fails, stderr says "gradebook-tests: <score> is below --fail-under <floor>"

    Examples:
      | score | floor | exit |
      | 30.0  | 50    | 1    |
      | 30.0  | 0     | 0    |
      | 50.0  | 50    | 0    |

  @id:gradebook-tests.command-line.quality-gate.002 @rule:tests.gate.fail-on-drop-against-baseline @verified @source:gradebook-tests/gradebook_tests/cli.py#_gate_failed @test:gradebook-tests/tests/test_gradebook_tests.py#test_cli_fail_on_drop_gate @test:gradebook-tests/tests/integration/test_scan_a_git_repo.py#test_a_git_repo_is_scored_from_its_history_coverage_and_ci
  Scenario Outline: A score drop beyond the tolerance against a baseline fails the run
    Given a baseline JSON report from an earlier run
    And the suite now scores <drop> points lower than the baseline
    When the operator runs gradebook-tests with --baseline and --fail-on-drop <tolerance>
    Then the exit code is <exit>
    And when the run fails, stderr says the score dropped by <drop> points against the baseline with the tolerance

    Examples:
      | drop | tolerance   | exit |
      | 0.0  | 0 (default) | 0    |
      | 12.0 | 0 (default) | 1    |
      | 12.0 | 50          | 0    |

  @id:gradebook-tests.command-line.quality-gate.003 @rule:tests.gate.drop-gate-ignores-comparability @inferred @source:gradebook-tests/gradebook_tests/cli.py#_gate_failed @questionable
  Scenario: The drop gate fails the run even when the baseline scored different dimensions
    Given a baseline JSON report whose set of unscored dimensions differs from the current run
    And the current score is lower than the baseline score
    When the operator runs gradebook-tests with --baseline and --fail-on-drop
    Then the report marks the baseline as not comparable
    And the exit code is 1

  @id:gradebook-tests.command-line.quality-gate.004 @rule:tests.gate.drop-gate-requires-baseline @verified @source:gradebook-tests/gradebook_tests/cli.py#main @test:gradebook-tests/tests/test_gradebook_tests.py#test_cli_rejects_drop_gate_without_baseline
  Scenario: Asking for the drop gate without a baseline is refused
    Given no baseline report is supplied
    When the operator runs gradebook-tests with --fail-on-drop
    Then stderr says "gradebook-tests: --fail-on-drop needs --baseline"
    And no report is printed
    And the exit code is 2
