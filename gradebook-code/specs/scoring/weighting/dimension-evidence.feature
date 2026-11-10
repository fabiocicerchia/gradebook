@domain:scoring @area:weighting @from:gradebook-code/scorers
Feature: Leaving dimensions without evidence unscored
  Keeps a repository from being scored down for things it doesn't have, such as git history, interfaces or inheritance.

  Background:
    Given the developer runs gradebook-code over a repository

  @id:gradebook-code.scoring.weighting.004 @rule:code.scoring.unscored-without-evidence @verified @source:gradebook-code/gradebook_code/scorers.py#SCORERS @test:gradebook-code/tests/test_gradebook_code.py#test_lsp_is_not_scored_without_inheritance @test:gradebook-code/tests/test_gradebook_code.py#test_isp_is_not_scored_without_interfaces @test:gradebook-code/tests/test_gradebook_code.py#test_coupling_is_not_scored_for_tiny_codebases @test:gradebook-code/tests/test_gradebook_code.py#test_cohesion_is_not_scored_without_stateful_classes @test:gradebook-code/tests/test_gradebook_code.py#test_hotspots_are_not_scored_without_history
  Scenario Outline: A dimension with nothing to measure is reported as not scored, with the reason
    Given the repository has <missing>
    When the developer runs gradebook-code over the repository
    Then <dimension> has no score and no points
    And <dimension> is listed as not scored
    And its detail reads "<reason>"

    Examples:
      | missing                                  | dimension                      | reason                                |
      | no functions                             | Simplicity (KISS)              | no functions found                    |
      | no functions                             | Open/closed                    | no functions found                    |
      | no functions                             | Speculative generality (YAGNI) | no functions found                    |
      | no git history                           | Hotspots (churn x complexity)  | no churn history to rank by           |
      | git history but no measurable complexity | Hotspots (churn x complexity)  | no complexity to weigh                |
      | no lines of code                         | Duplication (DRY)              | no code found                         |
      | no lines of code                         | Law of Demeter                 | no code found                         |
      | no source files                          | Single responsibility          | no code found                         |
      | no source files                          | Dependency inversion           | no code found                         |
      | no subclasses                            | Liskov substitution            | no inheritance to judge               |
      | no interfaces or protocols               | Interface segregation          | no interfaces or protocols declared   |
      | fewer than 3 modules                     | Coupling (GRASP)               | too few modules to judge              |
      | no classes with fields                   | Cohesion (GRASP)               | no classes with shared state to judge |
      | no named classes or functions            | Naming & intent                | nothing named to judge                |
