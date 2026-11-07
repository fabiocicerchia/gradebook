@domain:scoring @area:letter-grade @from:gradebook-code/score
Feature: Turning the code score into a letter grade
  Gives a maintainer a letter grade alongside the code score so the result reads at a glance in reports and badges.

  @id:gradebook-code.scoring.letter-grade.001 @rule:scoring.letter-grade.grade-bands @verified @source:gradebook-code/gradebook_code/score.py#grade_for @test:gradebook-code/tests/test_gradebook_code.py#test_score_is_bounded_and_ordered
  Scenario Outline: The letter grade follows fixed score bands
    Given a repository whose code score is <score>
    When the operator grades the repository
    Then the report shows grade <grade>

    Examples:
      | score | grade |
      | 100.0 | A     |
      | 85.0  | A     |
      | 84.9  | B     |
      | 70.0  | B     |
      | 55.0  | C     |
      | 54.9  | D     |
      | 40.0  | D     |
      | 39.9  | F     |
      | 0.0   | F     |
