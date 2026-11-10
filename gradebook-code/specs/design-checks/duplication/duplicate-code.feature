@domain:design-checks @area:duplication @from:gradebook-code/analysis
Feature: Finding code repeated across files
  Points a maintainer at blocks of real statements copied between files, so DRY violations can be merged, without crying wolf over declaration boilerplate.

  @id:gradebook-code.design-checks.duplication.001 @rule:code.duplication.repeated-block-flagged @verified @source:gradebook-code/gradebook_code/analysis.py#find_duplicate_blocks @test:gradebook-code/tests/test_gradebook_code.py#test_duplicate_blocks_are_found
  Scenario: A block of statements repeated in another file is flagged at the copy
    Given src/a.py and src/b.py each contain the same 8 consecutive lines of statements starting on line 2
    When the operator grades the repository
    Then the red flags include a duplicate-block finding at src/b.py:2
    And its message reads "8 lines repeated from src/a.py:2"
    And the report counts 8 duplicated lines
    And the DRY dimension scores below 100%

  @id:gradebook-code.design-checks.duplication.002 @rule:code.duplication.declaration-boilerplate-ignored @verified @source:gradebook-code/gradebook_code/analysis.py#find_duplicate_blocks @test:gradebook-code/tests/test_gradebook_code.py#test_declaration_boilerplate_is_not_duplication
  Scenario: Repeated declaration boilerplate is not reported as duplication
    Given a.go and b.go each build the same command literal made of field declarations
    When the operator grades the repository
    Then no duplicate-block finding is reported
    And the report counts 0 duplicated lines

  @id:gradebook-code.design-checks.duplication.003 @rule:code.duplication.findings-capped @inferred @source:gradebook-code/gradebook_code/analysis.py#find_duplicate_blocks
  Scenario: Duplicate-block flags stop at twenty while every duplicated line still counts
    Given the repository copies the same block of statements into 30 files
    When the operator grades the repository
    Then the red flags include 20 duplicate-block findings
    And the duplicated-line count includes the copies in all 29 later files
