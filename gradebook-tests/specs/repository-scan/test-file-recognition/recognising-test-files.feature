@domain:repository-scan @area:test-file-recognition @from:gradebook-tests/detection
Feature: Recognising test files
  Lets a maintainer trust that the grade counts their real test suite, whatever ecosystem its files follow, and does not mistake source for tests.

  Background:
    Given the maintainer runs gradebook-tests over their repository

  @id:gradebook-tests.repository-scan.test-file-recognition.001 @rule:tests.files.recognised-by-ecosystem-convention @verified @source:gradebook-tests/gradebook_tests/detection.py#is_test_file @test:gradebook-tests/tests/test_gradebook_tests.py#test_recognises_test_files
  Scenario Outline: A file named the way its ecosystem names tests is counted as a test file
    Given the repository contains the file "<path>"
    When the maintainer grades the repository
    Then "<path>" is counted among the test files, not the source files

    Examples:
      | path                         |
      | tests/test_thing.py          |
      | app/thing_test.py            |
      | conftest.py                  |
      | src/thing.test.ts            |
      | src/thing.spec.js            |
      | src/__tests__/thing.js       |
      | pkg/thing_test.go            |
      | src/test/java/ThingTest.java |
      | spec/thing_spec.rb           |
      | tests/ThingTest.php          |
      | Thing.Tests.cs               |
      | test/thing_test.exs          |
      | features/checkout.feature    |

  @id:gradebook-tests.repository-scan.test-file-recognition.002 @rule:tests.files.test-directory-makes-a-test @verified @source:gradebook-tests/gradebook_tests/detection.py#is_test_file @test:gradebook-tests/tests/test_gradebook_tests.py#test_recognises_test_files
  Scenario Outline: Code living under a test directory counts as test code even without a test name
    Given the repository contains the helper "<path>" with no test marker in its name
    When the maintainer grades the repository
    Then "<path>" is counted among the test files

    Examples:
      | path                      |
      | tests/helpers.py          |
      | spec/support/factories.rb |
      | e2e/fixtures.ts           |

  @id:gradebook-tests.repository-scan.test-file-recognition.003 @rule:tests.files.source-is-not-a-test @verified @source:gradebook-tests/gradebook_tests/detection.py#is_test_file @test:gradebook-tests/tests/test_gradebook_tests.py#test_ignores_non_test_files @test:gradebook-tests/tests/test_gradebook_tests.py#test_source_and_test_files_are_counted_separately
  Scenario Outline: Ordinary source files are not counted as tests
    Given the repository contains the source file "<path>"
    When the maintainer grades the repository
    Then "<path>" is not counted among the test files

    Examples:
      | path                     |
      | src/thing.py             |
      | src/latest.js            |
      | pkg/thing.go             |
      | src/main/java/Thing.java |
      | lib/contest.rb           |
