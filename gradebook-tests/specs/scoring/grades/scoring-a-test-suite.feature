@domain:scoring @area:grades @from:gradebook-tests/score
Feature: Scoring a test suite against the rubric
  Gives a maintainer one 0-100 score and a letter grade for their test suite, without punishing the repo for signals it cannot provide.

  Background:
    Given the maintainer runs gradebook-tests over a repository

  @id:gradebook-tests.scoring.grades.001 @rule:scoring.grades.unscored-dimensions-renormalise @verified @source:gradebook-tests/gradebook_tests/score.py#evaluate @test:gradebook-tests/tests/test_gradebook_tests.py#test_tdd_not_scored_without_git @test:gradebook-tests/tests/test_gradebook_tests.py#test_mutation_is_not_scored_without_a_report
  Scenario Outline: A dimension with no evidence is left unscored and its weight is shared out
    Given the repository has <missing evidence>
    When the maintainer scores the repository
    Then "<dimension>" is listed under not scored, with no points
    And the scored weight is <scored weight> of the 108 rubric points
    And the total is the weighted average over the scored dimensions only, out of 100

    Examples:
      | missing evidence                                            | dimension      | scored weight |
      | no mutation report                                          | Mutation score | 100           |
      | no git history and no mutation report                       | TDD discipline | 88            |
      | fewer than 5 commits touching source and no mutation report | TDD discipline | 93            |

  @id:gradebook-tests.scoring.grades.002 @rule:scoring.rubric-dimensions.missing-essentials-score-zero @inferred @source:gradebook-tests/gradebook_tests/score.py#score_coverage
  Scenario Outline: Missing coverage tooling, CI, test layers or behaviour specs score zero rather than unscored
    Given the repository has <missing practice>
    When the maintainer scores the repository
    Then "<dimension>" scores 0 with the detail "<detail>"
    And its full weight counts as points lost
    And its advice is "<advice>"

    Examples:
      | missing practice                                 | dimension             | detail                       | advice                                                                              |
      | no coverage configuration and no coverage report | Coverage              | no coverage tooling detected | wire up a coverage tool (pytest-cov, nyc, go -coverprofile, jacoco) and publish it  |
      | no CI configuration                              | CI enforcement        | no CI configuration found    | run the suite on every push/PR                                                      |
      | no integration tests                             | Integration tests     | none found                   | test real collaborators (db, queue, http) rather than mocks only                    |
      | no Gherkin features and no describe/it specs     | BDD / behaviour specs | no behaviour specs found     | describe behaviour in the domain's language (Gherkin features, or spec-style tests) |

  @id:gradebook-tests.scoring.grades.003 @rule:scoring.rubric-dimensions.mutation-scored-when-reported @verified @source:gradebook-tests/gradebook_tests/score.py#score_mutation @test:gradebook-tests/tests/test_gradebook_tests.py#test_mutation_report_is_scored_when_present
  Scenario: A mutation report adds the mutation score to the rubric
    Given the repository contains a mutation report in which 75% of mutants were killed
    When the maintainer scores the repository
    Then "Mutation score" is scored 75/80 of its 8 weight points
    And its detail reads "75.0% of mutants killed" with the report's source
    And the scored weight grows by 8 and every other weight renormalises

  @id:gradebook-tests.scoring.grades.004 @rule:scoring.grades.letter-grade-bands @verified @source:gradebook-tests/gradebook_tests/score.py#grade_for @test:gradebook-tests/tests/test_gradebook_tests.py#test_score_is_bounded_and_ordered
  Scenario Outline: The total maps to a letter grade by fixed bands
    Given the scored dimensions combine to a total of <total>
    When the maintainer scores the repository
    Then the report shows the score <total>
    And the report shows grade <grade>

    Examples:
      | total | grade |
      | 92.0  | A     |
      | 85.0  | A     |
      | 84.9  | B     |
      | 70.0  | B     |
      | 55.0  | C     |
      | 40.0  | D     |
      | 39.9  | F     |
