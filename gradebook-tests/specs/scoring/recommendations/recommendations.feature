@domain:scoring @area:recommendations @from:gradebook-tests/score
Feature: Recommending the fixes worth the most points
  Tells a maintainer which dimensions to fix first by how many rubric points each would recover.

  Background:
    Given the maintainer has scored a repository

  @id:gradebook-tests.scoring.recommendations.001 @rule:scoring.recommendations.ranked-by-points-recoverable @verified @source:gradebook-tests/gradebook_tests/score.py#recommendations @test:gradebook-tests/tests/test_gradebook_tests.py#test_recommendations_are_ranked_by_points_recoverable
  Scenario: Recommendations are ranked by points recoverable and capped
    Given more than five scored dimensions each lose at least half a point
    When the maintainer asks for the recommendations
    Then the dimension losing the most points comes first
    And each later recommendation loses no more points than the one before it
    And at most 5 recommendations are listed by default
    And every recommendation carries advice text

  @id:gradebook-tests.scoring.recommendations.002 @rule:scoring.recommendations.only-recoverable-scored-dimensions @inferred @source:gradebook-tests/gradebook_tests/score.py#recommendations
  Scenario Outline: Unscored dimensions and near-perfect ones are never recommended
    Given "<dimension>" is <state>
    When the maintainer asks for the recommendations
    Then "<dimension>" is not among the recommendations

    Examples:
      | dimension      | state                              |
      | TDD discipline | not scored for lack of git history |
      | CI enforcement | losing 0.4 points                  |
