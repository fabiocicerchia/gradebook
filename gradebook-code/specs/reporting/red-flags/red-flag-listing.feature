@domain:reporting @area:red-flags @from:gradebook-code/render
Feature: Listing red flags
  Gives a developer every finding with its file:line, worst first, so the score turns into concrete places to fix.

  Background:
    Given a repository with source code has been scored by gradebook-code

  @id:gradebook-code.reporting.red-flags.001 @rule:reporting.red-flags.all-listed-worst-first @verified @source:gradebook-code/gradebook_code/render.py#render_flags @test:gradebook-code/tests/test_gradebook_code.py#test_every_red_flag_is_listed_by_default
  Scenario: Every red flag is listed by default, worst kind first, each with its location
    Given the scan found 14 red flags, among them a hotspot in src/billing.py and long functions in src/a0.py
    When the developer runs gradebook-code
    Then a "Red flags (14):" section lists all 14 findings
    And hotspots come before dependency cycles, which come before god files and complex functions, and so on down to many-parameters, with ties ordered by file and then line
    And each entry shows its location as "file:line", the finding kind and its message
    And no "more" line is shown

  @id:gradebook-code.reporting.red-flags.002 @rule:reporting.red-flags.lineless-finding-shows-bare-location @inferred @source:gradebook-code/gradebook_code/render.py#location
  Scenario: A finding with no line to point at shows its location without a line number
    Given the scan found a dependency cycle "billing -> ledger -> billing" that has no line
    When the developer runs gradebook-code
    Then the red flag shows "billing -> ledger -> billing" as its location, with no ":0" suffix

  @id:gradebook-code.reporting.red-flags.003 @rule:reporting.red-flags.max-flags-caps-list @verified @source:gradebook-code/gradebook_code/render.py#capped @test:gradebook-code/tests/test_gradebook_code.py#test_max_flags_caps_and_names_the_remainder
  Scenario Outline: Capping red flags shows the worst ones and says how many were left out
    Given the scan found 14 red flags
    When the developer runs gradebook-code with --format <format> --max-flags <cap>
    Then the section header still reads "Red flags (14)"
    And only the <cap> worst flags are listed
    And the list ends with "<remainder line>"

    Examples:
      | format   | cap | remainder line                |
      | text     | 3   | … 11 more (raise --max-flags) |
      | markdown | 3   | - … 11 more                   |

  @id:gradebook-code.reporting.red-flags.004 @rule:reporting.red-flags.zero-cap-hides-section @verified @source:gradebook-code/gradebook_code/render.py#capped @test:gradebook-code/tests/test_gradebook_code.py#test_max_flags_zero_hides_the_section
  Scenario Outline: A cap of zero or less hides the red-flag section
    Given the scan found 14 red flags
    When the developer runs gradebook-code with --format <format> --max-flags <cap>
    Then no "Red flags" section appears in the report

    Examples:
      | format   | cap |
      | text     | 0   |
      | markdown | 0   |
      | text     | -1  |
