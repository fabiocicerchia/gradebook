@domain:scanning @area:scan-triggers @from:nvim/lua
Feature: Choosing when Neovim rescans
  Lets a Neovim user decide whether scores refresh on save, while typing, or only on request, so the cost of scanning matches how they work.

  Background:
    Given the user has called the plugin's setup

  @id:extensions.scanning.scan-triggers.001 @rule:scanning.scan-triggers.run-mode @verified @source:extensions/nvim/lua/gradebook/init.lua#M.setup @test:extensions/nvim/tests/config_spec.lua#runs both tools on save by default @questionable
  Scenario Outline: The run mode decides which edits start a scan
    Given the run mode is <run>
    When the user <edit>
    Then <outcome>

    Examples:
      | run     | edit                                          | outcome                                  |
      | on_save | writes a file                                 | a project scan starts at once            |
      | on_save | types without saving                          | no scan starts                           |
      | on_type | writes a file                                 | a project scan starts at once            |
      | on_type | stops typing for debounce_ms (400 by default) | a project scan starts                    |
      | on_type | keeps typing before debounce_ms has passed    | no scan starts yet; the wait starts over |
      | manual  | writes a file                                 | no scan starts                           |

  @id:extensions.scanning.scan-triggers.002 @rule:scanning.scan-triggers.scan-on-startup @verified @source:extensions/nvim/lua/gradebook/init.lua#M.setup @test:extensions/nvim/tests/config_spec.lua#runs both tools on save by default
  Scenario Outline: The project is scanned once when the plugin starts, unless turned off
    Given scan_project_on_startup is <startup>
    And the run mode is manual
    When the user sets up the plugin
    Then <outcome>

    Examples:
      | startup | outcome                            |
      | true    | a project scan starts right away   |
      | false   | no scan starts until the user asks |
