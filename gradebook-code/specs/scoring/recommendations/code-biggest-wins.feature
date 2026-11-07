@domain:scoring @area:recommendations @from:gradebook-code/score
Feature: Recommending the fixes worth the most points
  Tells a maintainer which principles to work on first by ranking the dimensions that cost the most points.

  @id:gradebook-code.scoring.recommendations.001 @rule:scoring.recommendations.ranked-by-points-lost @verified @source:gradebook-code/gradebook_code/score.py#recommendations @test:gradebook-code/tests/test_gradebook_code.py#test_recommendations_are_ranked @questionable
  Scenario Outline: Biggest wins list the dimensions that lost the most points, worst first, up to the requested count
    Given a graded repository where Simplicity (KISS) lost 6.5 points, Duplication (DRY) lost 3.3 points and Naming & intent lost 1.0 point
    When the operator grades the repository asking for the top <top> wins
    Then the Biggest wins list shows <wins>, each with its advice

    Examples:
      | top         | wins                                                                 |
      | 5 (default) | +6.5 Simplicity (KISS), +3.3 Duplication (DRY), +1.0 Naming & intent |
      | 2           | +6.5 Simplicity (KISS), +3.3 Duplication (DRY)                       |

  @id:gradebook-code.scoring.recommendations.002 @rule:scoring.recommendations.only-meaningful-scored-wins @inferred @source:gradebook-code/gradebook_code/score.py#recommendations
  Scenario: Unscored dimensions and wins under half a point are never recommended
    Given a graded repository where Liskov substitution is not scored and Law of Demeter lost 0.4 points
    When the operator grades the repository
    Then neither Liskov substitution nor Law of Demeter appears under Biggest wins
    And when no dimension lost at least 0.5 points, the Biggest wins section is absent
