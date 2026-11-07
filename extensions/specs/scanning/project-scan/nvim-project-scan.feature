@domain:scanning @area:project-scan @from:nvim/lua
Feature: Scanning a project from Neovim
  Lets a Neovim user score the whole repository they are editing with the gradebook tools they selected, without leaving the editor.

  Background:
    Given the gradebook-code and gradebook-tests tools are installed

  @id:extensions.scanning.project-scan.001 @rule:scanning.project-scan.whole-repository-per-selected-tool @verified @source:extensions/nvim/lua/gradebook/init.lua#M.scan @test:extensions/nvim/tests/core_spec.lua#appends the root and asks for json @test:extensions/nvim/tests/integration/scan_spec.lua#publishes the report even when --fail-under exits 1
  Scenario Outline: A scan scores the whole repository with every selected tool
    Given the user is editing a file inside a git repository at /home/dev/acme
    And the selected tools are <tools>
    When the user runs :Gradebook
    Then each of <tools> is run once over /home/dev/acme, asking for a JSON report
    And the score report shows a section for each of <tools>

    Examples:
      | tools       |
      | code, tests |
      | code        |
      | tests       |

  @id:extensions.scanning.project-scan.002 @rule:scanning.project-scan.disabled-plugin-does-not-scan @inferred @source:extensions/nvim/lua/gradebook/init.lua#M.scan
  Scenario: A disabled plugin does not scan
    Given the user has set enabled to false
    When the user runs :Gradebook
    Then no gradebook tool is run
    And the diagnostics and the score report are left as they were

  @id:extensions.scanning.project-scan.003 @rule:scanning.scan-failures.gate-exit-still-publishes @verified @source:extensions/nvim/lua/gradebook/init.lua#run @test:extensions/nvim/tests/integration/scan_spec.lua#publishes the report even when --fail-under exits 1
  Scenario: A tool that fails its fail-under gate still has its report shown
    Given gradebook-code is configured with --fail-under 101
    And the repository scores below 101
    When the user runs :Gradebook
    Then no failure warning is shown
    And the score report shows the gradebook-code section
    And the findings appear as diagnostics on the open files

  @id:extensions.scanning.project-scan.004 @rule:scanning.scan-failures.failed-tool-warns-and-publishes-nothing @verified @source:extensions/nvim/lua/gradebook/init.lua#run @test:extensions/nvim/tests/integration/scan_spec.lua#reports a tool that produced no report as a failure @questionable
  Scenario Outline: A tool that crashes or returns an unreadable report is reported as a warning
    Given gradebook-code <outcome>
    When the user runs :Gradebook
    Then the user sees the warning "<warning>"
    And no new findings from gradebook-code are shown
    And the score report keeps what it showed before

    Examples:
      | outcome                                                                 | warning                                               |
      | exits with code 2 and writes 'No module named gradebook_code' to stderr | gradebook-code failed: No module named gradebook_code |
      | exits with code 0 but prints nothing                                    | gradebook-code failed: <its stderr>                   |
      | prints output that is not JSON                                          | gradebook: unreadable report: <the decode error>      |
      | runs longer than timeout_ms (30000 by default)                          | gradebook-code failed: <its stderr>                   |
