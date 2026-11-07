@domain:complexity-checks @area:function-limits @from:gradebook-code/analysis
Feature: Flagging functions past the size and complexity limits
  Shows a maintainer each function that is too long, too branchy, too deeply nested or takes too many parameters, at the line where it is declared, so they know exactly what to split.

  Background:
    Given the repository's limits are the Python profile: 40 lines, complexity 10, nesting 4, 5 parameters

  @id:gradebook-code.complexity-checks.function-limits.001 @rule:code.function-limits.flag-each-limit-exceeded @verified @source:gradebook-code/gradebook_code/analysis.py#_limit_findings @test:gradebook-code/tests/test_gradebook_code.py#test_long_and_complex_functions_are_flagged @test:gradebook-code/tests/test_gradebook_code.py#test_wrapped_signatures_still_trip_the_limit
  Scenario Outline: A function past a limit is flagged at its declaration line
    Given src/a.py declares the function `big` on line 1
    And `big` measures <value> <measure>
    When the operator grades the repository
    Then the red flags include a `<kind>` finding at src/a.py:1
    And its message reads "`big` has <value> <measure> (limit <limit>)"

    Examples:
      | measure    | value | limit | kind             |
      | lines      | 62    | 40    | long-function    |
      | complexity | 31    | 10    | complex-function |
      | nesting    | 6     | 4     | deep-nesting     |
      | params     | 8     | 5     | many-parameters  |

  @id:gradebook-code.complexity-checks.function-limits.002 @rule:code.function-limits.at-limit-not-flagged @inferred @source:gradebook-code/gradebook_code/analysis.py#_limit_findings
  Scenario: A function exactly at a limit is not flagged
    Given src/a.py declares a function of exactly 40 lines with 5 parameters
    When the operator grades the repository
    Then no long-function finding is reported for it
    And no many-parameters finding is reported for it

  @id:gradebook-code.complexity-checks.function-limits.003 @rule:code.function-limits.prose-is-not-branching @verified @source:gradebook-code/gradebook_code/analysis.py#analyse_file @test:gradebook-code/tests/test_gradebook_code.py#test_prose_does_not_add_branches
  Scenario Outline: Words in comments and strings do not count as branches
    Given a <language> function whose only statement returns a value
    And its comments and strings contain the words if, for, while, and, or
    When the operator grades the repository
    Then the function's complexity is 1

    Examples:
      | language   |
      | python     |
      | javascript |
      | go         |

  @id:gradebook-code.complexity-checks.function-limits.004 @rule:code.function-limits.parameters-the-caller-passes @verified @source:gradebook-code/gradebook_code/analysis.py#_measure_function @test:gradebook-code/tests/test_gradebook_code.py#test_parameter_counting @test:gradebook-code/tests/test_gradebook_code.py#test_parameter_count_matches_a_real_parser
  Scenario Outline: Only the parameters a caller passes count toward the parameter limit
    Given a <language> function declared as <signature>
    When the operator grades the repository
    Then the function is measured at <count> parameters

    Examples:
      | language   | signature                                                                    | count |
      | python     | def method(self, a, b)                                                       | 2     |
      | python     | def wrapped(alpha, beta, gamma, delta, epsilon, zeta) split over seven lines | 6     |
      | go         | func (r *Repo) Save(ctx context.Context, o Order) error                      | 2     |
      | typescript | function pick(items: Map<string, number>, key: string)                       | 2     |
      | python     | def none()                                                                   | 0     |
