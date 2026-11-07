@domain:design-checks @area:inheritance-interfaces @from:gradebook-code/collection
Feature: Flagging interfaces that are too wide
  Shows a maintainer which interfaces force their clients to depend on more methods than they use.

  Background:
    Given a repository the operator wants to grade with gradebook-code

  @id:gradebook-code.design-checks.inheritance-interfaces.001 @rule:code.design.fat-interface-flagged @verified @source:gradebook-code/gradebook_code/collection.py#_accumulate @test:gradebook-code/tests/test_gradebook_code.py#test_fat_interfaces_are_flagged
  Scenario: An interface declaring more than seven methods is flagged
    Given the source file "src/port.py" declares the abstract interface "Port" with 9 methods
    When the operator grades the repository
    Then a fat-interface red flag points at the line where "Port" is declared in "src/port.py"
    And its message reads "`Port` declares 9 methods — clients depend on more than they use"
