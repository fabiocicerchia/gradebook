@domain:scanning @area:scan-triggers @from:vscode/src
Feature: Scanning the workspace
  Developers get their repository rescored whole, when they choose, by the tools they choose, without stray work when gradebook is off.

  Background:
    Given a workspace folder is open

  @id:extensions.scanning.scan-triggers.003 @rule:scanning.triggers.by-run-mode @verified @source:extensions/vscode/src/extension.ts#activate @test:extensions/vscode/src/test/config.test.ts#defaults run both tools on save
  Scenario Outline: When a scan starts depends on the run setting
    Given gradebook is enabled
    And the run setting is <run>
    When the developer <event>
    Then <outcome>

    Examples:
      | run    | event                          | outcome                                                                                     |
      | onSave | saves a file                   | the whole workspace is scanned at once                                                      |
      | onSave | types in a file                | no scan starts                                                                              |
      | onType | types in a file                | the whole workspace is scanned once typing pauses for the debounce time (400 ms by default) |
      | onType | saves a file                   | the whole workspace is scanned at once                                                      |
      | manual | saves a file                   | no scan starts                                                                              |
      | manual | runs gradebook: Scan Workspace | the whole workspace is scanned                                                              |

  @id:extensions.scanning.scan-triggers.004 @rule:scanning.triggers.startup-scan @inferred @source:extensions/vscode/src/extension.ts#activate
  Scenario Outline: The workspace is scanned when the window opens unless startup scanning is turned off
    Given gradebook is enabled
    And scan-on-startup is <startup>
    When the developer opens the window
    Then a scan runs at startup: <scanned>

    Examples:
      | startup          | scanned |
      | on (the default) | yes     |
      | off              | no      |

  @id:extensions.scanning.scan-triggers.005 @rule:scanning.tool-selection.only-chosen-tools-run @verified @source:extensions/vscode/src/extension.ts#activate @test:extensions/vscode/src/test/config.test.ts#defaults run both tools on save @questionable
  Scenario Outline: Only the tools the developer chose are run
    Given gradebook is enabled
    And the tools setting is <tools>
    When the developer runs gradebook: Scan Workspace
    Then the report and status bar show results for <shown>

    Examples:
      | tools                        | shown                              |
      | code and tests (the default) | gradebook-code and gradebook-tests |
      | code only                    | gradebook-code only                |

  @id:extensions.scanning.scan-triggers.006 @rule:scanning.tool-selection.open-folder-is-last-resort @verified @source:extensions/vscode/src/config.ts#withWorkspaceRoot @test:extensions/vscode/src/test/config.test.ts#the open folder travels as a root, not as a module path @test:extensions/vscode/src/test/config.test.ts#an explicit setting is left untouched @test:extensions/vscode/src/test/config.test.ts#the root reaches the server after the module paths
  Scenario Outline: An open gradebook checkout does not replace the installed tools or explicit tool paths
    Given the developer has a gradebook checkout open as the workspace
    And the code path setting is <code_path>
    When the scan server starts
    Then the code tool is loaded from <source>
    And the open folder is offered only as the last place to look

    Examples:
      | code_path                 | source                                                |
      | empty                     | the installed gradebook-code package, if there is one |
      | /elsewhere/gradebook-code | /elsewhere/gradebook-code                             |

  @id:extensions.scanning.scan-triggers.007 @rule:scanning.triggers.disabled-clears-results @inferred @source:extensions/vscode/src/extension.ts#activate @questionable
  Scenario: Turning gradebook off stops scans and clears its problems, panel and status bar
    Given gradebook has shown problems, findings and scores for the workspace
    When the developer turns the enable setting off
    Then no gradebook problems remain in the editor
    And the Findings panel lists no findings
    And the status bar entry is hidden
    And saving a file starts no scan
