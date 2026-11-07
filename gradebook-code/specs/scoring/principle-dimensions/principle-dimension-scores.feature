@domain:scoring @area:principle-dimensions @from:gradebook-code/scorers
Feature: Scoring design principles: SOLID, coupling, cohesion and Law of Demeter
  Tells a maintainer how well their code follows the design principles, one 0-1 score per principle, each driven by a ratio they can act on.

  Background:
    Given the developer runs gradebook-code over a repository

  @id:gradebook-code.scoring.principle-dimensions.001 @rule:code.principles.penalty-scales-to-target-share @verified @source:gradebook-code/gradebook_code/scorers.py#penalise @test:gradebook-code/tests/test_gradebook_code.py#test_god_files_are_flagged @test:gradebook-code/tests/test_gradebook_code.py#test_type_branching_lowers_ocp @test:gradebook-code/tests/test_gradebook_code.py#test_fat_interfaces_are_flagged @test:gradebook-code/tests/test_gradebook_code.py#test_infrastructure_spread_lowers_dip @test:gradebook-code/tests/test_gradebook_code.py#test_import_cycles_are_flagged
  Scenario Outline: Each design-principle violation costs its share of the dimension once it reaches its target rate
    Given the rate of <problem> per <counted> is <share>
    When the developer runs gradebook-code over the repository
    Then the <dimension> score loses up to <weight> of its 1.0, in proportion to how close <share> is to <target>
    And the loss stops growing once <share> reaches <target>

    Examples:
      | dimension             | problem                                | counted   | target | weight | share |
      | Single responsibility | god files                              | file      | 10%    | 0.45   | 10%   |
      | Single responsibility | files mixing 3+ concerns               | file      | 10%    | 0.35   | 5%    |
      | Single responsibility | classes with 15+ methods               | class     | 10%    | 0.20   | 10%   |
      | Open/closed           | branches on a type or kind field       | function  | 10%    | 0.55   | 10%   |
      | Open/closed           | runtime type checks                    | function  | 10%    | 0.45   | 5%    |
      | Interface segregation | interfaces with 8+ methods             | interface | 20%    | 1.00   | 20%   |
      | Dependency inversion  | files reaching infrastructure directly | file      | 30%    | 0.60   | 30%   |
      | Dependency inversion  | mutable globals                        | file      | 20%    | 0.40   | 10%   |
      | Coupling (GRASP)      | import cycles                          | module    | 5%     | 0.60   | 5%    |
      | Coupling (GRASP)      | internal imports                       | module    | 8      | 0.40   | 4     |

  @id:gradebook-code.scoring.principle-dimensions.002 @rule:code.lsp.unimplemented-overrides @verified @source:gradebook-code/gradebook_code/scorers.py#score_lsp @test:gradebook-code/tests/test_gradebook_code.py#test_unimplemented_overrides_lower_lsp @questionable
  Scenario Outline: Subclasses that leave overrides unimplemented lower the Liskov score
    Given the repository declares <subclasses> subclasses
    And <stubs> of them override a method without implementing it
    And the whole codebase has <checks> runtime type checks
    When the developer runs gradebook-code over the repository
    Then the Liskov substitution score is <score>
    And the detail starts "<subclasses> subclass(es)"

    Examples:
      | subclasses | stubs | checks | score |
      | 10         | 0     | 0      | 1.0   |
      | 10         | 1     | 0      | 0.6   |
      | 10         | 0     | 5      | 0.6   |
      | 1          | 1     | 1      | 0.0   |

  @id:gradebook-code.scoring.principle-dimensions.003 @rule:code.cohesion.methods-use-own-state @verified @source:gradebook-code/gradebook_code/scorers.py#score_cohesion @test:gradebook-code/tests/test_gradebook_code.py#test_cohesion_rewards_methods_that_use_their_state
  Scenario Outline: Classes whose methods use their own state score well on cohesion
    Given <share> of methods in classes with fields use their object's own state
    When the developer runs gradebook-code over the repository
    Then the cohesion score is <score>
    And the cohesion detail reads "<share> of methods use their object's own state"

    Examples:
      | share | score |
      | 100%  | 1.0   |
      | 80%   | 1.0   |
      | 40%   | 0.5   |

  @id:gradebook-code.scoring.principle-dimensions.004 @rule:code.demeter.chains-per-hundred-lines @verified @source:gradebook-code/gradebook_code/scorers.py#score_demeter @test:gradebook-code/tests/test_gradebook_code.py#test_demeter_chains_are_counted
  Scenario Outline: Long dot chains lower the Law of Demeter score by how dense they are
    Given the repository has <chains> chains of 3+ dots in <lines> lines of code
    When the developer runs gradebook-code over the repository
    Then the Law of Demeter score is <score>
    And the detail reads "<chains> chains of 3+ dots (<density> per 100 lines)"

    Examples:
      | chains | lines | density | score |
      | 0      | 1000  | 0.0     | 1.0   |
      | 15     | 1000  | 1.5     | 0.5   |
      | 30     | 1000  | 3.0     | 0.0   |
