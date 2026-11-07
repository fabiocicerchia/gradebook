@domain:test-quality-analysis @area:suppressed-tests @from:gradebook-tests/detection
Feature: Flagging tests whose failures are silenced
  Shows a maintainer, line by line, the tests that can never fail because their check was commented out, swallowed, dead or skipped without reason.

  Background:
    Given the maintainer runs gradebook-tests over their repository

  @id:gradebook-tests.test-quality-analysis.suppressed-tests.001 @rule:tests.suppressed.silenced-failure-flagged-with-location @verified @source:gradebook-tests/gradebook_tests/detection.py#_suppressed_failures @test:gradebook-tests/tests/test_gradebook_tests.py#test_suppressed_failures_are_found @test:gradebook-tests/tests/test_gradebook_tests.py#test_logged_and_swallowed_failures_are_flagged
  Scenario Outline: A test that cannot fail is flagged at its file and line
    Given the test file "tests/test_billing.py" contains a test where <silencing>
    When the maintainer grades the repository
    Then a suppressed-failure red flag points at "tests/test_billing.py" with a line number above zero
    And its message reads "<message>"

    Examples:
      | silencing                                | message                                              |
      | the assertion is commented out           | assertion commented out                              |
      | the failure is caught and only logged    | failure logged and swallowed — the test still passes |
      | the failure is caught by an empty except | failure swallowed by an empty except/catch           |
      | the assertions sit behind if False       | assertions behind an `if False` branch               |
      | the test is skipped with no reason       | test skipped with no reason given                    |

  @id:gradebook-tests.test-quality-analysis.suppressed-tests.002 @rule:tests.suppressed.skip-with-reason-not-flagged @verified @source:gradebook-tests/gradebook_tests/detection.py#_suppressed_failures @test:gradebook-tests/tests/test_gradebook_tests.py#test_skip_with_a_reason_is_not_a_suppressed_failure
  Scenario: A test skipped with a stated reason is not flagged as silenced
    Given the test file "tests/test_billing.py" skips a test with the reason "waiting on the payment sandbox"
    When the maintainer grades the repository
    Then no suppressed-failure red flag is reported
