@domain:complexity-checks @area:function-limits @from:gradebook-code/metrics
Feature: Counting the parameters a caller must pass
  Keeps the many-parameters flag fair, so methods are not penalised for self and annotated or defaulted parameters count once each.

  Background:
    Given Given the operator runs gradebook-code over a Python repository

  @id:gradebook-code.complexity-checks.function-limits.005 @rule:gradebook-code.function-limits.parameters-counted-as-callers-see-them @verified @source:gradebook-code/gradebook_code/metrics.py#count_params @test:gradebook-code/tests/test_gradebook_code.py#test_count_params @test:gradebook-code/tests/test_gradebook_code.py#test_parameter_count_matches_a_real_parser
  Scenario Outline: A function's parameters are counted the way a caller passes them
    Given the repository defines a function with the signature <signature>
    When the operator scores the repository
    Then the function is measured at <count> parameters

    Examples:
      | signature                                          | count |
      | def ping():                                        | 0     |
      | def total(a, b, c):                                | 3     |
      | def load(a: dict[str, int], b=(1, 2)):             | 2     |
      | def method(self, alpha, beta=1, *rest, **options): | 4     |
      | def build(cls, name):                              | 1     |
