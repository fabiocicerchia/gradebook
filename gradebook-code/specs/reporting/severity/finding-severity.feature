@domain:reporting @area:severity @from:gradebook-code/severity
Feature: Grading the severity of each finding
  Gives every red flag in a gradebook-code report a high, medium or low severity so editors and report consumers can triage the worst problems first without re-deriving a ranking.

  Background:
    Given a repository scanned by gradebook-code

  @id:gradebook-code.reporting.severity.001 @rule:reporting.severity.bucket-per-finding-kind @verified @source:gradebook-code/gradebook_code/severity.py#severity_for @test:gradebook-code/tests/test_units.py#test_severity_buckets_follow_flag_order @test:gradebook-code/tests/test_units.py#test_severity_never_rises_as_rank_falls
  Scenario Outline: Each kind of finding carries a fixed severity
    Given the scan raises a "<kind>" finding
    When the operator runs gradebook-code with JSON output
    Then the finding is reported with severity "<severity>"

    Examples:
      | kind             | severity |
      | hotspot          | high     |
      | dependency-cycle | high     |
      | god-file         | high     |
      | complex-function | high     |
      | duplicate-block  | medium   |
      | deep-nesting     | medium   |
      | mixed-concerns   | medium   |
      | fat-interface    | medium   |
      | dead-code        | low      |
      | long-function    | low      |
      | many-parameters  | low      |

  @id:gradebook-code.reporting.severity.002 @rule:reporting.severity.unknown-kind-is-low @verified @source:gradebook-code/gradebook_code/severity.py#severity_for @test:gradebook-code/tests/test_units.py#test_unknown_kinds_are_low_severity @questionable
  Scenario: A finding of an unranked kind is reported as low severity
    Given a finding of a kind gradebook-code does not rank, such as "no-such-detector"
    When its severity is assigned
    Then the finding is reported with severity "low"
