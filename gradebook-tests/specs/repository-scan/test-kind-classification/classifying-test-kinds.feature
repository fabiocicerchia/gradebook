@domain:repository-scan @area:test-kind-classification @from:gradebook-tests/detection
Feature: Sorting tests into unit, integration and end-to-end
  Lets a maintainer see the shape of their test pyramid and catch unit tests that secretly talk to real systems.

  Background:
    Given the maintainer runs gradebook-tests over their repository

  @id:gradebook-tests.repository-scan.test-kind-classification.001 @rule:tests.kinds.folder-decides-kind @verified @source:gradebook-tests/gradebook_tests/detection.py#classify_kind @test:gradebook-tests/tests/test_gradebook_tests.py#test_classifies_layers_by_directory
  Scenario Outline: The folder a test lives in decides its kind
    Given the repository has a test file under "<folder>"
    When the maintainer grades the repository
    Then that file is counted as a <kind> test

    Examples:
      | folder            | kind        |
      | tests/unit        | unit        |
      | tests/integration | integration |
      | tests/e2e         | e2e         |

  @id:gradebook-tests.repository-scan.test-kind-classification.002 @rule:tests.kinds.content-decides-when-folder-is-neutral @verified @source:gradebook-tests/gradebook_tests/detection.py#classify_kind @test:gradebook-tests/tests/test_gradebook_tests.py#test_classifies_layers_by_content_when_path_is_neutral
  Scenario Outline: A test in a neutral folder is classified by what it uses
    Given the repository has the test file "tests/<file>" that uses <tool>
    When the maintainer grades the repository
    Then that file is counted as a <kind> test

    Examples:
      | file         | tool             | kind        |
      | test_db.py   | testcontainers   | integration |
      | test_ui.py   | playwright       | e2e         |
      | test_math.py | nothing external | unit        |

  @id:gradebook-tests.repository-scan.test-kind-classification.003 @rule:tests.kinds.unit-test-doing-real-io-is-reported @inferred @source:gradebook-tests/gradebook_tests/detection.py#classify_kind @questionable
  Scenario: A unit test that talks to a real database, service or browser is reported
    Given the repository has the test file "tests/unit/test_orders.py" that starts a real database container
    When the maintainer grades the repository
    Then the file is still counted as a unit test
    And a conjoined-twin red flag names "tests/unit/test_orders.py" as an integration test filed as a unit test
    And the report advises moving it to the integration suite
