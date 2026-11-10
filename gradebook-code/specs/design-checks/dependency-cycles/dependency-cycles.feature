@domain:design-checks @area:dependency-cycles @from:gradebook-code/analysis
Feature: Detecting import cycles between the repository's own modules
  Tells a maintainer which of their modules import each other in a loop, since neither side of a cycle can be understood or changed alone.

  @id:gradebook-code.design-checks.dependency-cycles.002 @rule:code.dependency-cycles.acyclic-not-flagged @verified @source:gradebook-code/gradebook_code/analysis.py#find_cycles @test:gradebook-code/tests/test_gradebook_code.py#test_find_cycles_ignores_a_dag
  Scenario: Modules that only import downward are not reported as a cycle
    Given a imports b, b imports c, and c imports nothing
    When the operator grades the repository
    Then no dependency-cycle finding is reported
