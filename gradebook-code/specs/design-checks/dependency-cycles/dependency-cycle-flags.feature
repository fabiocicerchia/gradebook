@domain:design-checks @area:dependency-cycles @from:gradebook-code/collection
Feature: Reporting import cycles
  Shows a maintainer which modules import each other in a loop, so neither can be understood or changed alone.

  Background:
    Given a repository the operator wants to grade with gradebook-code

  @id:gradebook-code.design-checks.dependency-cycles.003 @rule:code.design.dependency-cycle-flagged-without-line @verified @source:gradebook-code/gradebook_code/collection.py#collect @test:gradebook-code/tests/test_gradebook_code.py#test_import_cycles_are_flagged @questionable
  Scenario: Modules that import each other in a loop are flagged with the loop as the location
    Given the module "alpha" imports "beta"
    And the module "beta" imports "alpha"
    When the operator grades the repository
    Then a dependency-cycle red flag names the loop such as "alpha -> beta -> alpha" in place of a file
    And the flag has line 0
    And its message reads "modules import each other in a loop — neither can be understood alone"
    And at most 5 cycles are listed as red flags
