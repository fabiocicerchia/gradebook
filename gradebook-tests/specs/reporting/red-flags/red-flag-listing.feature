@domain:reporting @area:red-flags @from:gradebook-tests/render
Feature: Listing red flags with their location
  Gives the developer every finding with the file and line to fix, which is the actionable part of the report, and lets them cap how many are shown.

  Background:
    Given a repository has been scanned by gradebook-tests

  @id:gradebook-tests.reporting.red-flags.004 @rule:reporting.red-flags.listed-with-location @verified @source:gradebook-tests/gradebook_tests/render.py#render_flags @test:gradebook-tests/tests/test_gradebook_tests.py#test_findings_are_rendered_with_a_location
  Scenario: Every red flag is listed with its file:line, its kind and its message
    Given line 2 of tests/test_a.py holds a commented-out assertion
    When the developer runs gradebook-tests
    Then a "Red flags (1):" section is printed
    And its entry shows "tests/test_a.py:2", the kind "suppressed-failure" and the message

  @id:gradebook-tests.reporting.red-flags.005 @rule:reporting.red-flags.no-line-shows-file-only @inferred @source:gradebook-tests/gradebook_tests/render.py#location
  Scenario: A red flag with no line number is located by its file alone
    Given a finding in pytest.ini has no line number
    When the developer runs gradebook-tests
    Then its entry is located as "pytest.ini", with no ":0" suffix

  @id:gradebook-tests.reporting.red-flags.006 @rule:reporting.red-flags.max-flags-caps-the-list @verified @source:gradebook-tests/gradebook_tests/render.py#capped @test:gradebook-tests/tests/test_gradebook_tests.py#test_flags_can_be_hidden_and_truncated @questionable
  Scenario Outline: The number of red flags shown can be capped or hidden, and the heading still counts them all
    Given the scan raised 4 red flags
    When the developer runs gradebook-tests <option> with the <format> format
    Then <outcome>

    Examples:
      | option              | format   | outcome                                                                        |
      | with no --max-flags | text     | all 4 are listed under "Red flags (4):" and no "more" line is printed          |
      | --max-flags 3       | text     | 3 are listed under "Red flags (4):" followed by "… 1 more (raise --max-flags)" |
      | --max-flags 3       | markdown | 3 are listed under "### Red flags (4)" followed by "… 1 more"                  |
      | --max-flags 0       | text     | no red-flag section is printed                                                 |
      | --max-flags 0       | markdown | no red-flag section is printed                                                 |

  @id:gradebook-tests.reporting.red-flags.007 @rule:reporting.red-flags.no-section-without-findings @verified @source:gradebook-tests/gradebook_tests/render.py#render_flags @test:gradebook-tests/tests/test_gradebook_tests.py#test_render_flags_is_empty_without_findings
  Scenario: A scan with no red flags prints no red-flag section
    Given the scan raised no red flags
    When the developer runs gradebook-tests
    Then the report has no "Red flags" heading
