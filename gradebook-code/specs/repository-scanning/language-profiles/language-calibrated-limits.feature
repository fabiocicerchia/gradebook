@domain:repository-scanning @area:language-profiles @from:gradebook-code/metrics
Feature: Calibrating function limits to the languages in the repository
  Lets a team trust the size and complexity limits it is graded against, because Go is held to Go norms and Ruby to Ruby norms instead of one number for everyone.

  Background:
    Given the operator runs gradebook-code over a repository

  @id:gradebook-code.repository-scanning.language-profiles.001 @rule:gradebook-code.language-profiles.limits-follow-the-language @verified @source:gradebook-code/gradebook_code/metrics.py#blend_profile @test:gradebook-code/tests/test_gradebook_code.py#test_thresholds_follow_the_language
  Scenario Outline: A single-language repository is held to that language's limits
    Given the repository's source code is written only in <language>
    When the operator scores the repository
    Then the report says it is calibrated for <language>
    And functions are flagged past <max_lines> lines, complexity <max_complexity> and <max_params> parameters
    And a <language> function of 47 lines is <verdict>

    Examples:
      | language | max_lines | max_complexity | max_params | verdict             |
      | go       | 60        | 12             | 5          | not flagged as long |
      | python   | 40        | 10             | 5          | flagged as long     |
      | java     | 50        | 12             | 5          | not flagged as long |
      | ruby     | 25        | 8              | 4          | flagged as long     |
      | elixir   | 20        | 6              | 4          | flagged as long     |

  @id:gradebook-code.repository-scanning.language-profiles.002 @rule:gradebook-code.language-profiles.mixed-repo-blends-by-share @verified @source:gradebook-code/gradebook_code/metrics.py#blend_profile @test:gradebook-code/tests/test_gradebook_code.py#test_profile_blends_by_share_of_code
  Scenario: A mixed-language repository gets limits weighted by each language's share of the code
    Given the repository holds 9,000 non-blank lines of Go and 1,000 of Python
    When the operator scores the repository
    Then the report says it is calibrated for go/python
    And functions are flagged past 58 lines, complexity 12 and 5 parameters
    And only the two largest languages are named

  @id:gradebook-code.repository-scanning.language-profiles.003 @rule:gradebook-code.language-profiles.default-limits-without-a-profile @verified @source:gradebook-code/gradebook_code/metrics.py#blend_profile @test:gradebook-code/tests/test_gradebook_code.py#test_profile_falls_back_for_unknown_languages
  Scenario Outline: Languages without their own profile are held to the default limits
    Given the repository's source code is <code>
    When the operator scores the repository
    Then functions are flagged past 45 lines, complexity 11, 5 parameters and nesting 4
    And <calibration_line>

    Examples:
      | code                  | calibration_line                           |
      | written only in Swift | the report says it is calibrated for swift |
      | written only in Lua   | the report says it is calibrated for lua   |
      | absent                | the report shows no calibration line       |
