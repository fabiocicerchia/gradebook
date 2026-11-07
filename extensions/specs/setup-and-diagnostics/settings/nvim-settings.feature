@domain:setup-and-diagnostics @area:settings @from:nvim/lua
Feature: Configuring the Neovim plugin
  Gives a Neovim user safe defaults and refuses settings that would make the plugin misbehave, so a typo fails loudly at setup instead of silently.

  @id:extensions.setup-and-diagnostics.settings.001 @rule:setup-and-diagnostics.settings.safe-defaults @verified @source:extensions/nvim/lua/gradebook/config.lua#M.defaults @test:extensions/nvim/tests/config_spec.lua#runs both tools on save by default @test:extensions/nvim/tests/config_spec.lua#does not leak one resolve into the next
  Scenario: With no settings, both tools scan on save and on startup
    Given the user gives no options
    When the user sets up the plugin
    Then both code and tests are selected, run as gradebook-code and gradebook-tests
    And the run mode is on_save, the debounce is 400 ms and the timeout is 30000 ms
    And the startup scan and diagnostics are on, and nothing is excluded

  @id:extensions.setup-and-diagnostics.settings.002 @rule:setup-and-diagnostics.settings.tool-command-override @verified @source:extensions/nvim/lua/gradebook/config.lua#M.resolve @test:extensions/nvim/tests/config_spec.lua#takes a cmd list, so a checkout needs no install @test:extensions/nvim/tests/core_spec.lua#works with a multi-part cmd from a checkout
  Scenario: A tool's command can be replaced without touching the other tool
    Given the user sets the code command to /home/dev/venv/bin/gradebook-code
    When the user sets up the plugin
    Then gradebook-code scans run /home/dev/venv/bin/gradebook-code
    And gradebook-tests scans still run gradebook-tests

  @id:extensions.setup-and-diagnostics.settings.003 @rule:setup-and-diagnostics.settings.invalid-option-refused @verified @source:extensions/nvim/lua/gradebook/config.lua#M.validate @test:extensions/nvim/tests/config_spec.lua#rejects an unknown run mode @test:extensions/nvim/tests/config_spec.lua#rejects an unknown tool @test:extensions/nvim/tests/config_spec.lua#rejects a cmd that is a bare string @test:extensions/nvim/tests/config_spec.lua#rejects a debounce too short to be a debounce
  Scenario Outline: An invalid setting is refused when the plugin is set up
    Given the user sets <option> to <value>
    When the user sets up the plugin
    Then setup fails with an error naming <option> and expecting <expected>

    Examples:
      | option                   | value                            | expected                                  |
      | run                      | 'sometimes'                      | one of: on_save, on_type, manual          |
      | tools                    | { 'style' }                      | a non-empty list of: code, tests          |
      | tools                    | {}                               | a non-empty list of: code, tests          |
      | cmd.code                 | 'gradebook-code' (a bare string) | a non-empty list of strings               |
      | debounce_ms              | 5                                | a number >= 100                           |
      | diagnostics.severity.low | 'loud'                           | false, or a vim.diagnostic.severity value |
