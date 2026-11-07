@domain:design-checks @area:dead-code @from:gradebook-code/collection
Feature: Spotting private helpers nobody calls
  Shows a maintainer the private code that can be deleted because nothing references it.

  Background:
    Given a repository the operator wants to grade with gradebook-code

  @id:gradebook-code.design-checks.dead-code.001 @rule:code.design.unreferenced-private-helper-flagged @verified @source:gradebook-code/gradebook_code/collection.py#_count_dead_code @test:gradebook-code/tests/test_gradebook_code.py#test_dead_private_code_is_flagged @test:gradebook-code/tests/test_gradebook_code.py#test_referenced_private_code_is_not_flagged @questionable
  Scenario Outline: A private helper that is never referenced is flagged as dead code
    Given the source file "src/a.py" defines "<helper>" at line 1
    And <usage>
    When the operator grades the repository
    Then <outcome>

    Examples:
      | helper        | usage                                                   | outcome                                                                                      |
      | _never_called | nothing else in the repository mentions "_never_called" | a dead-code red flag at "src/a.py:1" reads "`_never_called` is private and never referenced" |
      | _helper       | another function in the repository calls "_helper"      | no dead-code red flag is raised                                                              |

  @id:gradebook-code.design-checks.dead-code.002 @rule:code.design.dead-code-flags-capped @inferred @source:gradebook-code/gradebook_code/collection.py#_count_dead_code
  Scenario: At most 20 dead-code red flags are listed while every unused helper still counts
    Given the repository has 25 private helpers that nothing references
    When the operator grades the repository
    Then exactly 20 dead-code red flags are listed
    And the report counts 25 dead symbols
