@domain:setup-and-diagnostics @area:health-check @from:nvim/lua
Feature: Checking the Neovim setup
  Lets a Neovim user run :checkhealth gradebook to confirm the selected tools run and the configuration is usable, with install advice when they are not.

  Background:
    Given the user runs :checkhealth gradebook

  @id:extensions.setup-and-diagnostics.health-check.001 @rule:setup-and-diagnostics.health-check.tool-status @verified @source:extensions/nvim/lua/gradebook/health.lua#M.check @test:extensions/nvim/tests/health_spec.lua#reports the version of a tool that runs @test:extensions/nvim/tests/health_spec.lua#says how to install a tool that is not on the PATH @test:extensions/nvim/tests/health_spec.lua#passes on the stderr of a --version that fails
  Scenario Outline: Each selected tool is reported as working, missing or broken
    Given the selected tool is code
    And its command <state>
    When the user runs the health check
    Then the check reports <level>: "<message>"
    And <advice>

    Examples:
      | state                                         | level | message                                 | advice                                                                                                                                                                     |
      | prints 'gradebook-code 0.2.0' for --version   | OK    | gradebook-code 0.2.0                    | no advice is given                                                                                                                                                         |
      | is not on the PATH                            | ERROR | gradebook-code is not executable        | the advice gives a pipx install from git+https://github.com/fabiocicerchia/gradebook.git#subdirectory=gradebook-code, or setting cmd.code to a virtualenv's gradebook-code |
      | fails --version and writes 'broken' to stderr | ERROR | gradebook-code --version failed: broken | no advice is given                                                                                                                                                         |

  @id:extensions.setup-and-diagnostics.health-check.002 @rule:setup-and-diagnostics.health-check.disabled-warning @verified @source:extensions/nvim/lua/gradebook/health.lua#M.check @test:extensions/nvim/tests/health_spec.lua#warns when the plugin is disabled
  Scenario: The health check warns when the plugin is disabled
    Given the user has set enabled to false
    When the user runs the health check
    Then the check reports WARNING: "disabled (enabled = false)"

  @id:extensions.setup-and-diagnostics.health-check.003 @rule:setup-and-diagnostics.health-check.unmapped-severity-bucket @verified @source:extensions/nvim/lua/gradebook/health.lua#M.check @test:extensions/nvim/tests/health_spec.lua#flags a severity bucket with no diagnostic level
  Scenario: The health check flags a severity bucket with no level
    Given the medium severity bucket has no editor level mapped
    When the user runs the health check
    Then the check reports ERROR: "no diagnostic severity mapped for \"medium\""
