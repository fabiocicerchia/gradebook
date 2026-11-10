@domain:external-evidence @area:mutation-reports @from:gradebook-tests/coverage
Feature: Reading mutation testing reports
  Gives a team lead the share of mutants their suite kills, from the mutation tool they already run, as the strongest evidence that tests catch real faults.

  Background:
    Given the repository has source files and a test suite

  @id:gradebook-tests.external-evidence.mutation-reports.001 @rule:gradebook-tests.mutation.report-formats-yield-kill-rate @verified @source:gradebook-tests/gradebook_tests/coverage.py#measure_mutation @test:gradebook-tests/tests/test_gradebook_tests.py#test_parses_stryker_report @test:gradebook-tests/tests/test_gradebook_tests.py#test_parses_pitest_report @test:gradebook-tests/tests/test_gradebook_tests.py#test_parses_cargo_mutants_report @test:gradebook-tests/tests/test_gradebook_tests.py#test_mutation_report_is_scored_when_present
  Scenario Outline: A mutation report gives the share of mutants the suite killed
    Given the repository contains a mutation report named <report> with <mutants>
    When the operator grades the repository
    Then the mutation score is <percent>% of mutants killed

    Examples:
      | report                | mutants                                                        | percent |
      | reports/mutation.json | Stryker: 1 killed, 1 timed out, 1 survived, 1 with no coverage | 50.0    |
      | mutations.xml         | PIT: 1 detected, 1 not detected                                | 50.0    |
      | outcomes.json         | cargo-mutants: 2 caught, 1 missed                              | 66.7    |
      | reports/mutation.json | Stryker: 3 killed, 1 survived                                  | 75.0    |

  @id:gradebook-tests.external-evidence.mutation-reports.002 @rule:gradebook-tests.mutation.generic-score-fallback @inferred @source:gradebook-tests/gradebook_tests/coverage.py#parse_generic_mutation
  Scenario: A JSON mutation report that states its score directly is accepted
    Given the repository contains mutation-report.json holding only a mutationScore of 72
    When the operator grades the repository
    Then the mutation score is 72.0%

  @id:gradebook-tests.external-evidence.mutation-reports.003 @rule:gradebook-tests.mutation.zero-kill-rate-reads-as-no-report @inferred @source:gradebook-tests/gradebook_tests/coverage.py#measure_mutation @questionable
  Scenario: A mutation report where no mutant was killed is treated as no report at all
    Given the repository contains reports/mutation.json in which every Stryker mutant survived
    When the operator grades the repository
    Then no mutation score is recorded
    And the mutation dimension is listed as not scored
