@domain:test-quality-analysis @area:test-naming @from:gradebook-tests/detection
Feature: Judging whether test names describe behaviour
  Tells a maintainer which tests have placeholder names so a failure says what broke without opening the file.

  Background:
    Given the maintainer runs gradebook-tests over their repository

  @id:gradebook-tests.test-quality-analysis.test-naming.001 @rule:tests.naming.descriptive-vs-placeholder @verified @source:gradebook-tests/gradebook_tests/detection.py#classify_name @test:gradebook-tests/tests/test_gradebook_tests.py#test_descriptive_names_are_recognised @test:gradebook-tests/tests/test_gradebook_tests.py#test_placeholder_names_are_flagged
  Scenario Outline: A test name is descriptive only when it states behaviour, not a placeholder
    Given a test is named "<name>"
    When the maintainer grades the repository
    Then the name is judged <verdict>

    Examples:
      | name                                       | verdict       |
      | test_returns_404_when_the_user_is_missing  | descriptive   |
      | shouldRejectExpiredTokens                  | descriptive   |
      | charges the card once when retried         | descriptive   |
      | test_raises_value_error_on_negative_amount | descriptive   |
      | test_1                                     | a placeholder |
      | it works                                   | a placeholder |
      | testFoo                                    | a placeholder |
      | test_stuff                                 | a placeholder |

  @id:gradebook-tests.test-quality-analysis.test-naming.002 @rule:tests.naming.placeholder-names-listed-in-advice @verified @source:gradebook-tests/gradebook_tests/detection.py#_name_tally @test:gradebook-tests/tests/test_gradebook_tests.py#test_naming_dimension_separates_good_from_placeholder_names
  Scenario: Placeholder-named tests are named in the naming advice
    Given the suite's only tests are named "test_1" and "test_works"
    When the maintainer grades the repository
    Then the naming dimension scores 0
    And its detail mentions placeholder names
    And its advice names "test_1"
