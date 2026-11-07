@domain:test-quality-analysis @area:test-substance @from:gradebook-tests/substance
Feature: Spotting tests that pad the count without checking anything
  Lets a team lead see which tests are copy-pasted, import code that does not exist, have gone stale or leave their source barely covered, so the test count is not mistaken for real checking.

  Background:
    Given the operator runs gradebook-tests over a repository

  @id:gradebook-tests.test-quality-analysis.test-substance.005 @rule:tests.substance.copy-paste-run-of-three @verified @source:gradebook-tests/gradebook_tests/substance.py#find_duplicates @test:gradebook-tests/tests/test_substance.py#test_a_pair_of_identical_bodies_is_not_a_cluster @test:gradebook-tests/tests/test_substance.py#test_duplicate_findings_stop_at_the_limit_but_the_count_does_not
  Scenario Outline: Three or more tests with the same body are flagged as a copy-paste run
    Given the repository has <copies> test cases whose bodies are identical once names and literals are ignored
    When the operator scores the repository
    Then the report counts <redundant> redundant test cases
    And <flags> duplicate-case flags are listed, each pointing at a copy's file:line and naming the first copy's file:line with the advice to parametrise instead

    Examples:
      | copies | redundant | flags |
      | 2      | 0         | 0     |
      | 3      | 2         | 2     |
      | 5      | 4         | 4     |

  @id:gradebook-tests.test-quality-analysis.test-substance.006 @rule:tests.substance.findings-capped-count-complete @verified @source:gradebook-tests/gradebook_tests/substance.py#find_duplicates @test:gradebook-tests/tests/test_substance.py#test_duplicate_findings_stop_at_the_limit_but_the_count_does_not
  Scenario: Each substance check lists at most 20 flags but counts every case
    Given the repository has 25 copies of one test body
    When the operator scores the repository
    Then the report counts 24 redundant test cases
    And only the first 20 duplicate-case flags are listed

  @id:gradebook-tests.test-quality-analysis.test-substance.007 @rule:tests.substance.phantom-import-flagged @verified @source:gradebook-tests/gradebook_tests/substance.py#find_phantoms @test:gradebook-tests/tests/test_substance.py#test_phantoms_count_each_missing_name_once_per_file @test:gradebook-tests/tests/test_substance.py#test_no_phantoms_when_every_import_is_defined @questionable
  Scenario: A test that imports a name no source file defines is flagged as phantom
    Given test file tests/test_a.py imports `charge` and imports `refund` twice
    And test file tests/test_b.py imports `refund`
    And the source files define `charge` but nothing defines `refund`
    When the operator scores the repository
    Then the report counts 2 phantom imports
    And tests/test_a.py and tests/test_b.py each get one phantom-symbol flag saying it imports `refund`, which no source file defines

  @id:gradebook-tests.test-quality-analysis.test-substance.008 @rule:tests.substance.stale-test-flagged @verified @source:gradebook-tests/gradebook_tests/substance.py#find_stale @test:gradebook-tests/tests/test_substance.py#test_a_test_is_stale_once_its_source_moved_on_enough_times @test:gradebook-tests/tests/test_substance.py#test_a_test_changed_alongside_its_source_is_not_stale
  Scenario Outline: A test whose source has changed many times since the test last did is flagged as stale
    Given tests/test_a.py is paired with src/a.py
    And src/a.py has had <changes> commits since tests/test_a.py last changed
    When the operator scores the repository with git history
    Then the stale-test count is <stale>
    And <outcome>

    Examples:
      | changes | stale | outcome                                                                                         |
      | 4       | 0     | no stale-test flag is listed                                                                    |
      | 5       | 1     | tests/test_a.py gets a stale-test flag saying src/a.py changed 5 times since this test last did |

  @id:gradebook-tests.test-quality-analysis.test-substance.009 @rule:tests.substance.stale-needs-history-for-both @verified @source:gradebook-tests/gradebook_tests/substance.py#find_stale @test:gradebook-tests/tests/test_substance.py#test_stale_is_not_scored_without_history_for_both_files
  Scenario: Staleness is not judged when either the test or its source has no history
    Given tests/test_a.py is paired with src/a.py
    And src/a.py has 4 commits and tests/test_a.py has none
    When the operator scores the repository with git history
    Then the stale-test count is 0
    And no stale-test flag is listed for tests/test_a.py

  @id:gradebook-tests.test-quality-analysis.test-substance.010 @rule:tests.substance.decorative-test-flagged @verified @source:gradebook-tests/gradebook_tests/substance.py#find_decorative @test:gradebook-tests/tests/test_substance.py#test_decorative_flags_only_measured_files_under_the_threshold @questionable
  Scenario Outline: A test file whose source stays barely covered is flagged as decorative
    Given a coverage report is present
    And tests/test_a.py is paired with src/a.py at <coverage> coverage
    When the operator scores the repository
    Then the decorative-test count is <count>
    And <outcome>

    Examples:
      | coverage     | count | outcome                                                                                                 |
      | 12%          | 1     | tests/test_a.py gets a decorative-test flag saying src/a.py has this test file and is still 12% covered |
      | 80%          | 0     | no decorative-test flag is listed                                                                       |
      | not measured | 0     | no decorative-test flag is listed                                                                       |

  @id:gradebook-tests.test-quality-analysis.test-substance.011 @rule:tests.substance.test-named-after-source @verified @source:gradebook-tests/gradebook_tests/substance.py#source_stem @test:gradebook-tests/tests/test_substance.py#test_source_stem_strips_each_language_test_marker @test:gradebook-tests/tests/test_substance.py#test_source_stem_is_none_when_the_name_names_no_source @questionable
  Scenario Outline: A test file is paired with the source file its name points to
    Given the repository has a source file named <source> and a test file <test>
    When the operator scores the repository
    Then <test> counts as the test for <source> in the stale and decorative checks

    Examples:
      | test                  | source       |
      | tests/test_billing.py | billing.py   |
      | tests/billing_test.py | billing.py   |
      | src/billing.test.ts   | billing.ts   |
      | src/billing.spec.js   | billing.js   |
      | pkg/billing_test.go   | billing.go   |
      | src/BillingTest.java  | Billing.java |
      | src/BillingIT.java    | Billing.java |
      | spec/billing_spec.rb  | billing.rb   |
      | tests/BillingTest.php | Billing.php  |
      | test/billing_test.exs | billing.ex   |
