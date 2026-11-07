@domain:findings @area:project-wide-findings @from:nvim/lua
Feature: Keeping findings that have no line, and dropping excluded ones
  Ensures project-wide findings such as dependency cycles reach the Neovim user without flagging innocent code, while paths the user excluded stay quiet.

  Background:
    Given a scan has finished

  @id:extensions.findings.project-wide-findings.001 @rule:findings.project-wide-findings.listed-in-report @verified @source:extensions/nvim/lua/gradebook/core.lua#M.split @test:extensions/nvim/tests/core_spec.lua#sends a dependency cycle to the report, not to a guessed path @test:extensions/nvim/tests/core_spec.lua#sends a finding on a missing file to the report @test:extensions/nvim/tests/core_spec.lua#lists workspace findings under their own heading @test:extensions/nvim/tests/decode_spec.lua#routes a line-0 finding away from a file
  Scenario Outline: A finding with no real file and line is listed in the score report
    Given gradebook-code reported <finding>
    When the user opens the score report
    Then no file carries a diagnostic for it
    And the report lists it under "Workspace findings (1):" as "<line>"

    Examples:
      | finding                                                               | line                                   |
      | a dependency-cycle 'a loop' at a -> b -> a, line 0                    | a -> b -> a  dependency-cycle — a loop |
      | a duplicate-code 'copied block' at gone.py line 5, a file not on disk | gone.py  duplicate-code — copied block |

  @id:extensions.findings.project-wide-findings.002 @rule:findings.exclusions.excluded-prefix-dropped @verified @source:extensions/nvim/lua/gradebook/core.lua#M.excluded @test:extensions/nvim/tests/core_spec.lua#drops excluded prefixes entirely
  Scenario: Findings under an excluded path are not shown anywhere
    Given the user has excluded the path prefix vendor/
    And gradebook-code reported a finding at vendor/lib.py line 3
    When the user opens vendor/lib.py and the score report
    Then vendor/lib.py carries no gradebook diagnostic
    And the report does not list the finding
    And the score itself is unchanged
