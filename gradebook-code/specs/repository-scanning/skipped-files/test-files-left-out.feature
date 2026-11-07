@domain:repository-scanning @area:skipped-files @from:gradebook-code/metrics
Feature: Leaving test files out of the code score
  Keeps the code grade about production code, so a team is not marked down for long fixtures or assertion-heavy test functions.

  Background:
    Given Given the operator runs gradebook-code over a repository

  @id:gradebook-code.repository-scanning.skipped-files.008 @rule:gradebook-code.skipped-files.test-files-not-scored @verified @source:gradebook-code/gradebook_code/metrics.py#is_test_file @test:gradebook-code/tests/test_gradebook_code.py#test_test_files_are_excluded @test:gradebook-code/tests/test_gradebook_code.py#test_source_files_are_kept @test:gradebook-code/tests/test_gradebook_code.py#test_only_source_files_are_counted @questionable
  Scenario Outline: Test files are not scored as source code
    Given the repository contains the file <path>
    When the operator scores the repository
    Then <path> is <outcome>

    Examples:
      | path                           | outcome               |
      | tests/test_orders.py           | left out of the score |
      | src/cart.spec.ts               | left out of the score |
      | pkg/billing_test.go            | left out of the score |
      | src/test/java/InvoiceTest.java | left out of the score |
      | spec/user_spec.rb              | left out of the score |
      | src/__tests__/cart.js          | left out of the score |
      | checkout/login.feature         | left out of the score |
      | features/cart/view.tsx         | left out of the score |
      | src/latest.js                  | scored                |
      | lib/contest.rb                 | scored                |
