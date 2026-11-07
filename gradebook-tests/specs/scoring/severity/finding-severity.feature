@domain:scoring @area:severity @from:gradebook-tests/severity
Feature: Ranking red flags by severity
  Gives developers and the editor integrations one fixed severity for every kind of test-suite red flag, so the findings that matter most are seen first and filtered the same way everywhere.

  Background:
    Given gradebook-tests has scanned a repository that has red flags in its test suite

  @id:gradebook-tests.scoring.severity.001 @rule:tests.severity.kind-maps-to-fixed-bucket @verified @source:gradebook-tests/gradebook_tests/severity.py#severity_for @test:gradebook-tests/tests/test_gradebook_tests.py#test_every_finding_carries_a_known_severity
  Scenario Outline: Each kind of red flag always gets the same severity
    Given the scan found a "<kind>" red flag
    When the developer asks for the report in JSON
    Then that finding carries the severity "<severity>"
    And every finding carries a severity of high, medium or low

    Examples:
      | kind                  | severity |
      | phantom-symbol        | high     |
      | suppressed-failure    | high     |
      | untested-hotspot      | high     |
      | mirror-assertion      | medium   |
      | conjoined-twin        | medium   |
      | decorative-test       | medium   |
      | implementation-access | medium   |
      | brittle-selector      | low      |
      | duplicate-case        | low      |
      | stale-test            | low      |

  @id:gradebook-tests.scoring.severity.002 @rule:tests.severity.unknown-kind-is-low @inferred @source:gradebook-tests/gradebook_tests/severity.py#severity_for @questionable
  Scenario: A red flag kind outside the ranking is reported as low severity
    Given a red flag of a kind the severity ranking does not list
    When the developer asks for the report in JSON
    Then that finding carries the severity "low"
    And it is listed with the lowest-ranked findings

  @id:gradebook-tests.scoring.severity.003 @rule:tests.severity.findings-listed-most-severe-first @inferred @source:gradebook-tests/gradebook_tests/collection.py#collect
  Scenario: Red flags are listed most severe first, then by file and line
    Given the scan found a "stale-test" red flag in tests/test_a.py at line 3
    And a "phantom-symbol" red flag in tests/test_b.py at line 9
    And a "phantom-symbol" red flag in tests/test_a.py at line 12
    When the developer asks for the report
    Then the findings are listed as tests/test_a.py:12 phantom-symbol, tests/test_b.py:9 phantom-symbol, tests/test_a.py:3 stale-test
