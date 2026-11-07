@domain:scanning @area:scan-failures @from:vscode/src
Feature: Recovering from scan failures
  Developers learn why a scan failed and how to fix it, without being nagged or losing the last good scores.

  Background:
    Given a workspace folder is open
    And gradebook is enabled

  @id:extensions.scanning.scan-failures.001 @rule:scanning.failures.error-shown-once-report-kept @inferred @source:extensions/vscode/src/extension.ts#activate @questionable
  Scenario: A failed scan shows its reason once, offers settings and the log, and keeps the last scores
    Given the last code scan scored 68.2
    And code is the only selected tool and it now fails with "gradebook-code is not installed"
    When the developer saves a file twice
    Then one error "gradebook: gradebook-code is not installed" is shown, offering "Open Settings" and "Show Log"
    And the message is also written to the gradebook output log
    And the report and status bar still show the code score 68.2

  @id:extensions.scanning.scan-failures.002 @rule:scanning.failures.server-exit-reported-and-recovered @inferred @source:extensions/vscode/src/engine.ts#Engine
  Scenario Outline: When the scan server dies the developer is told why, and the next scan starts it again
    Given a scan is running
    When the scan server <event>
    Then the error "gradebook: <message>" is shown
    And the next scan starts a fresh scan server

    Examples:
      | event                                                 | message                                 |
      | exits with code 1                                     | gradebook server exited (1)             |
      | reports a fatal failure on its startup line (id 0)    | the startup failure the server reported |
