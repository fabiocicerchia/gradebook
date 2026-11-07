@domain:scoring @area:simplicity-dimensions @from:gradebook-code/scorers
Feature: Scoring simplicity: KISS, DRY, YAGNI, naming and hotspots
  Tells a maintainer how simple their code is, one 0-1 score per simplicity dimension with a detail line saying what cost the points.

  Background:
    Given the developer runs gradebook-code over a repository

  @id:gradebook-code.scoring.simplicity-dimensions.001 @rule:code.simplicity.penalty-scales-to-target-share @verified @source:gradebook-code/gradebook_code/scorers.py#penalise @test:gradebook-code/tests/test_gradebook_code.py#test_long_and_complex_functions_are_flagged @test:gradebook-code/tests/test_gradebook_code.py#test_small_functions_score_well @test:gradebook-code/tests/test_gradebook_code.py#test_duplicate_blocks_are_found @test:gradebook-code/tests/test_gradebook_code.py#test_a_clean_codebase_scores_dry @test:gradebook-code/tests/test_gradebook_code.py#test_stubs_and_commented_code_lower_yagni
  Scenario Outline: Each simplicity problem costs its share of the dimension once it reaches its target rate
    Given <share> of the <counted> is <problem>
    When the developer runs gradebook-code over the repository
    Then the <dimension> score loses up to <weight> of its 1.0, in proportion to how close <share> is to <target>
    And the loss stops growing once <share> reaches <target>
    And a dimension with none of its problems scores 1.0

    Examples:
      | dimension | problem                             | counted   | target     | weight | share      |
      | KISS      | over the complexity limit           | functions | 15%        | 0.35   | 15%        |
      | KISS      | over the line limit                 | functions | 15%        | 0.30   | 10%        |
      | KISS      | nested past the nesting limit       | functions | 10%        | 0.20   | 5%         |
      | KISS      | over the parameter limit            | functions | 10%        | 0.15   | 10%        |
      | DRY       | duplicated elsewhere                | lines     | 5%         | 0.70   | 5%         |
      | DRY       | a repeated magic literal (per file) | files     | 1 per file | 0.30   | 1 per file |
      | YAGNI     | an unreferenced private symbol      | functions | 5%         | 0.35   | 5%         |
      | YAGNI     | an abstraction with one implementer | classes   | 20%        | 0.25   | 20%        |
      | YAGNI     | an unimplemented stub               | functions | 5%         | 0.20   | 5%         |
      | YAGNI     | commented-out code (per file)       | files     | 1 per file | 0.10   | 1 per file |
      | YAGNI     | a TODO/FIXME marker (per file)      | files     | 2 per file | 0.10   | 1 per file |

  @id:gradebook-code.scoring.simplicity-dimensions.002 @rule:code.simplicity.detail-names-the-cost @inferred @source:gradebook-code/gradebook_code/scorers.py#score_kiss
  Scenario: The KISS detail line gives the average complexity and names each limit that cost points
    Given the repository has 40 functions with a total complexity of 160
    And 6 of them are over the complexity limit of 10
    When the developer runs gradebook-code over the repository
    Then the KISS detail reads "4.0 average complexity over 40 functions, 6 over complexity 10"
    And the KISS advice says to split the worst offenders

  @id:gradebook-code.scoring.simplicity-dimensions.003 @rule:code.hotspots.complexity-where-changes-land @verified @source:gradebook-code/gradebook_code/scorers.py#score_hotspots @test:gradebook-code/tests/test_gradebook_code.py#test_complexity_that_sits_where_the_changes_land_scores_badly @test:gradebook-code/tests/test_gradebook_code.py#test_complexity_away_from_the_changes_scores_well
  Scenario Outline: Complexity that sits in the most-changed files lowers the hotspots score
    Given the repository has git history
    And its most-changed files average <hot> complexity against <overall> across the codebase
    When the developer runs gradebook-code over the repository
    Then the hotspots score is <score>
    And the hotspots detail reads "the <n> most-changed files average <hot> complexity against <overall> across the codebase (<ratio>x)"

    Examples:
      | n | hot | overall | ratio | score |
      | 5 | 2   | 4       | 0.5   | 1.0   |
      | 5 | 4   | 4       | 1.0   | 1.0   |
      | 5 | 6   | 4       | 1.5   | 0.5   |
      | 5 | 8   | 4       | 2.0   | 0.0   |

  @id:gradebook-code.scoring.simplicity-dimensions.004 @rule:code.naming.vague-names-and-flag-parameters @verified @source:gradebook-code/gradebook_code/scorers.py#score_naming @test:gradebook-code/tests/test_gradebook_code.py#test_vague_names_and_flag_arguments_lower_naming @test:gradebook-code/tests/test_gradebook_code.py#test_clear_names_score_well
  Scenario Outline: Vague names and boolean flag parameters lower the naming score
    Given <vague> of the <named> named things are vague names such as Manager, Helper, data or process
    And <flags> of the <functions> functions take a boolean flag parameter
    When the developer runs gradebook-code over the repository
    Then the naming score is <score>
    And the naming detail starts "<vague>/<named> vague names"

    Examples:
      | vague | named | flags | functions | score |
      | 0     | 20    | 0     | 10        | 1.0   |
      | 3     | 40    | 0     | 20        | 0.5   |
      | 6     | 40    | 0     | 20        | 0.0   |
      | 0     | 20    | 1     | 10        | 0.85  |
