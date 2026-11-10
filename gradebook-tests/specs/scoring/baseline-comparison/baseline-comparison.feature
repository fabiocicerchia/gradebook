@domain:scoring @area:baseline-comparison @from:gradebook-tests/score
Feature: Comparing a run against an earlier report
  Shows a maintainer or CI pipeline how the score moved since a saved JSON report, and warns when the two runs measured different things.

  Background:
    Given the maintainer has an earlier gradebook-tests JSON report saved as a baseline

  @id:gradebook-tests.scoring.baseline-comparison.001 @rule:scoring.baseline-comparison.deltas-per-dimension-and-total @verified @source:gradebook-tests/gradebook_tests/score.py#compare @test:gradebook-tests/tests/test_gradebook_tests.py#test_compare_reports_deltas_per_dimension
  Scenario: Each dimension and the total show how many points they moved
    Given since the baseline a placeholder-named test with no assertions was added
    When the maintainer scores the repository against the baseline
    Then the report shows the baseline score and the total delta, which is negative
    And the "Test naming" dimension shows a negative points delta
    And a dimension unscored in either run shows no delta

  @id:gradebook-tests.scoring.baseline-comparison.002 @rule:scoring.baseline-comparison.flags-incomparable-baseline @verified @source:gradebook-tests/gradebook_tests/score.py#compare @test:gradebook-tests/tests/test_gradebook_tests.py#test_compare_reports_deltas_per_dimension @test:gradebook-tests/tests/test_gradebook_tests.py#test_compare_flags_a_baseline_that_scored_other_dimensions
  Scenario Outline: A baseline that scored a different set of dimensions is flagged as not comparable
    Given the baseline left <baseline unscored> unscored
    And the current run leaves <current unscored> unscored
    When the maintainer scores the repository against the baseline
    Then the comparison is marked comparable: <comparable>
    And the deltas are still reported

    Examples:
      | baseline unscored              | current unscored               | comparable |
      | Mutation score, TDD discipline | Mutation score, TDD discipline | true       |
      | nothing                        | Mutation score, TDD discipline | false      |
