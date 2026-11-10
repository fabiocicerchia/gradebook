@domain:findings @area:inline-diagnostics @from:nvim/lua
Feature: Seeing findings in the code
  Puts each gradebook finding on the line it points at in Neovim, labelled by tool and kind, so the user can fix it where it is.

  Background:
    Given a scan has finished

  @id:extensions.findings.inline-diagnostics.001 @rule:findings.inline-diagnostics.finding-on-its-line @verified @source:extensions/nvim/lua/gradebook/init.lua#publish @test:extensions/nvim/tests/core_spec.lua#groups by file and makes the line 0-based @test:extensions/nvim/tests/integration/scan_spec.lua#publishes the report even when --fail-under exits 1
  Scenario: A finding is shown on the line it names, labelled with its tool and kind
    Given gradebook-code reported a complex-function finding at src/billing.py line 12
    And src/billing.py is open in the editor
    When the user looks at src/billing.py
    Then line 12 carries a diagnostic with the finding's message
    And the diagnostic's source is gradebook-code and its code is complex-function
    And findings from gradebook-tests are kept separately and do not replace it

  @id:extensions.findings.inline-diagnostics.002 @rule:findings.inline-diagnostics.only-open-files @inferred @source:extensions/nvim/lua/gradebook/init.lua#publish @questionable
  Scenario: Findings in files that are not open are not shown anywhere
    Given gradebook-code reported a finding at src/ledger.py line 40
    And src/ledger.py exists but is not open in the editor
    When the user opens the score report
    Then src/ledger.py:40 is not listed in the report
    And the finding does not appear when src/ledger.py is opened later, until the next scan

  @id:extensions.findings.inline-diagnostics.003 @rule:findings.inline-diagnostics.can-be-turned-off @inferred @source:extensions/nvim/lua/gradebook/init.lua#publish @questionable
  Scenario: With diagnostics turned off, findings are not placed in the code
    Given the user has set diagnostics.enabled to false
    And gradebook-code reported a finding at src/billing.py line 12
    When a scan finishes
    Then src/billing.py carries no gradebook diagnostics
    And the score report still shows the scores
