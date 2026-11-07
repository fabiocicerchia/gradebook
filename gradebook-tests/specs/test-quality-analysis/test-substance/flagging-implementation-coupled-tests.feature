@domain:test-quality-analysis @area:test-substance @from:gradebook-tests/detection
Feature: Flagging tests coupled to the implementation
  Points a maintainer at tests that recompute their own expectations, poke at private members or click brittle locators, so they can be rewritten to check behaviour.

  Background:
    Given the maintainer runs gradebook-tests over their repository

  @id:gradebook-tests.test-quality-analysis.test-substance.001 @rule:tests.substance.mirrored-expectation-flagged @verified @source:gradebook-tests/gradebook_tests/detection.py#_tally_cases @test:gradebook-tests/tests/test_gradebook_tests.py#test_mirrored_expectations_are_flagged @test:gradebook-tests/tests/test_gradebook_tests.py#test_mirrored_expectations_in_matcher_style
  Scenario Outline: An expectation recomputed from the inputs is flagged
    Given a test asserts "<assertion>"
    When the maintainer grades the repository
    Then a mirror-assertion red flag is reported: <flagged>

    Examples:
      | assertion                                                         | flagged |
      | total(cart) == sum(i.price for i in cart)                         | yes     |
      | expect(total(items)).toBe(items.reduce((a, i) => a + i.price, 0)) | yes     |
      | total(cart) == 30                                                 | no      |
      | total(cart) == expected                                           | no      |
      | sorted(got) == sorted(want)                                       | no      |

  @id:gradebook-tests.test-quality-analysis.test-substance.002 @rule:tests.substance.private-member-access-flagged @verified @source:gradebook-tests/gradebook_tests/detection.py#_brittle_and_private @test:gradebook-tests/tests/test_gradebook_tests.py#test_reaching_into_privates_is_flagged @test:gradebook-tests/tests/test_gradebook_tests.py#test_private_access_lowers_substance
  Scenario: A test that reaches into a private member is flagged by name
    Given a test in "tests/test_client.py" asserts on "client._session"
    When the maintainer grades the repository
    Then one implementation-access red flag is reported for "tests/test_client.py" at that line
    And its message names "_session"
    And the substance dimension mentions private-member access and scores below full marks

  @id:gradebook-tests.test-quality-analysis.test-substance.003 @rule:tests.determinism.brittle-locator-flagged @verified @source:gradebook-tests/gradebook_tests/detection.py#_brittle_and_private @test:gradebook-tests/tests/test_gradebook_tests.py#test_brittle_selectors_are_flagged
  Scenario Outline: A positional or generated locator in a UI test is flagged
    Given the end-to-end test "tests/e2e/checkout.spec.js" locates an element with "<locator>"
    When the maintainer grades the repository
    Then a brittle-selector red flag is reported: <flagged>

    Examples:
      | locator                            | flagged |
      | //div[3]/span[2]                   | yes     |
      | .css-1a2b3c4d                      | yes     |
      | div > div > div:nth-child(2)       | yes     |
      | getByRole('button', {name: 'Pay'}) | no      |
      | [data-testid=pay]                  | no      |

  @id:gradebook-tests.test-quality-analysis.test-substance.004 @rule:tests.determinism.robust-locator-excuses-file @verified @source:gradebook-tests/gradebook_tests/detection.py#_brittle_and_private @test:gradebook-tests/tests/test_gradebook_tests.py#test_robust_locators_in_the_same_file_suppress_the_flag @questionable
  Scenario: A file that uses any robust locator gets no brittle-locator flags at all
    Given the end-to-end test "tests/e2e/checkout.spec.js" uses getByTestId('pay') and also "div > div > div"
    When the maintainer grades the repository
    Then no brittle-selector red flag is reported for that file
