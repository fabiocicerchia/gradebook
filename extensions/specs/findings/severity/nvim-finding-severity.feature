@domain:findings @area:severity @from:nvim/lua
Feature: Ranking findings by severity in Neovim
  Maps the severity bucket each gradebook tool gives a finding onto Neovim's levels, so the most serious problems stand out and noisy ones can be hidden.

  @id:extensions.findings.severity.001 @rule:findings.severity.bucket-to-editor-level @verified @source:extensions/nvim/lua/gradebook/core.lua#M.diagnostics @test:extensions/nvim/tests/config_spec.lua#maps every severity bucket onto a diagnostic level @test:extensions/nvim/tests/core_spec.lua#falls back to low for a severity it does not know @test:extensions/nvim/tests/core_spec.lua#drops a bucket mapped to false, and only that bucket @test:extensions/nvim/tests/config_spec.lua#accepts false for a severity, meaning "do not report these"
  Scenario Outline: Each severity bucket is shown at its configured level
    Given the severity mapping is <mapping>
    And a finding is in the <bucket> bucket
    When a scan finishes
    Then <outcome>

    Examples:
      | mapping      | bucket     | outcome                                          |
      | default      | high       | the finding is shown as an error                 |
      | default      | medium     | the finding is shown as a warning                |
      | default      | low        | the finding is shown as a hint                   |
      | high = false | high       | the finding is not shown                         |
      | high = false | medium     | the finding is shown as a warning                |
      | default      | unheard-of | the finding is shown at the low level, as a hint |
