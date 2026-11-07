@domain:external-evidence @area:coverage-gates @from:gradebook-tests/coverage
Feature: Detecting coverage thresholds and CI test runs
  Tells a team lead whether the repository declares a minimum coverage and whether its CI actually runs the tests and measures coverage, so a gate on paper can be told apart from one that is enforced.

  @id:gradebook-tests.external-evidence.coverage-gates.001 @rule:gradebook-tests.gates.highest-declared-threshold @verified @source:gradebook-tests/gradebook_tests/coverage.py#find_threshold @test:gradebook-tests/tests/test_gradebook_tests.py#test_measured_coverage_beats_declared_only @test:gradebook-tests/tests/test_gradebook_tests.py#test_detects_ci_running_tests_and_coverage
  Scenario Outline: The highest coverage threshold declared in config or CI is reported
    Given the repository declares <declaration>
    When the operator grades the repository
    Then the coverage threshold is <threshold>

    Examples:
      | declaration                                                  | threshold |
      | fail_under = 90 in .coveragerc                               | 90        |
      | pytest --cov-fail-under=80 in a GitHub workflow              | 80        |
      | a Jest coverageThreshold with lines: 85                      | 85        |
      | a JaCoCo rule with <minimum>0.8</minimum> in pom.xml         | 80        |
      | fail_under = 70 in .coveragerc and --cov-fail-under=85 in CI | 85        |

  @id:gradebook-tests.external-evidence.coverage-gates.002 @rule:gradebook-tests.gates.ci-runs-tests-and-coverage @verified @source:gradebook-tests/gradebook_tests/coverage.py#is_ci_file @test:gradebook-tests/tests/test_gradebook_tests.py#test_detects_ci_running_tests_and_coverage @test:gradebook-tests/tests/test_gradebook_tests.py#test_ci_without_tests_scores_low
  Scenario Outline: A CI pipeline is credited for running tests and for measuring coverage only when it does
    Given the repository has a CI file <ci_file> whose steps run <command>
    When the operator grades the repository
    Then CI is reported as running tests: <runs_tests>
    And CI is reported as measuring coverage: <measures_coverage>

    Examples:
      | ci_file                  | command                               | runs_tests | measures_coverage |
      | .github/workflows/ci.yml | pytest --cov=src --cov-fail-under=80  | yes        | yes               |
      | .github/workflows/ci.yml | ruff .                                | no         | no                |
      | .gitlab-ci.yml           | go test ./... -coverprofile=cover.out | yes        | yes               |
      | Jenkinsfile              | npm test                              | yes        | no                |
