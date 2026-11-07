@domain:scoring @area:weighting @from:gradebook-code/score
Feature: Combining principle scores into one weighted code score
  Gives a maintainer one 0-100 number for their codebase that is fair to repos lacking some kinds of evidence, so it can be tracked and gated.

  Background:
    Given the scoring model has 13 dimensions whose weights add up to 100: Simplicity (KISS) 13, Hotspots 6, Duplication (DRY) 11, Single responsibility 9, Open/closed 8, Liskov substitution 5, Interface segregation 6, Dependency inversion 8, Coupling 9, Cohesion 7, Law of Demeter 5, Speculative generality (YAGNI) 8, Naming & intent 5

  @id:gradebook-code.scoring.weighting.001 @rule:scoring.weighting.weighted-mean-of-scored-dimensions @inferred @source:gradebook-code/gradebook_code/score.py#evaluate
  Scenario Outline: The code score is the weight-averaged score of the dimensions that were scored
    Given a repository where every dimension has evidence
    And Simplicity (KISS) scores <kiss> and every other dimension scores 100%
    When the operator grades the repository
    Then the code score is <score>/100
    And the Simplicity (KISS) row shows <points> of 13 points

    Examples:
      | kiss | score | points |
      | 100% | 100.0 | 13.0   |
      | 50%  | 93.5  | 6.5    |
      | 0%   | 87.0  | 0.0    |

  @id:gradebook-code.scoring.weighting.002 @rule:scoring.weighting.no-evidence-is-unscored @verified @source:gradebook-code/gradebook_code/score.py#evaluate @test:gradebook-code/tests/test_gradebook_code.py#test_lsp_is_not_scored_without_inheritance @test:gradebook-code/tests/test_gradebook_code.py#test_hotspots_are_not_scored_without_history @test:gradebook-code/tests/test_gradebook_code.py#test_unscored_rows_line_up_with_scored_ones
  Scenario: A dimension with nothing to measure is left unscored and its weight is shared out
    Given a repository with no class inheritance and no git history
    And Simplicity (KISS) scores 50% and every other measurable dimension scores 100%
    When the operator grades the repository
    Then the Liskov substitution and Hotspots rows show n/a instead of points
    And the report says "not scored (weights redistributed): Hotspots (churn x complexity), Liskov substitution"
    And the code score is 92.7/100, computed over the remaining 89 weight points

  @id:gradebook-code.scoring.weighting.003 @rule:scoring.weighting.nothing-to-score-is-zero @inferred @source:gradebook-code/gradebook_code/score.py#evaluate @questionable
  Scenario: A repository with no code to measure scores zero and grade F
    Given a directory that holds no source files
    When the operator grades the directory
    Then every dimension is listed as not scored
    And the code score is 0.0/100 with grade F
