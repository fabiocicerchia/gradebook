@domain:findings @area:findings-panel @from:vscode/src
Feature: Browsing findings in the Findings panel
  Developers browse every red flag from both tools in one panel, worst first, narrow it down and jump to the code.

  Background:
    Given a workspace folder is open
    And gradebook is enabled

  @id:extensions.findings.findings-panel.001 @rule:findings.panel.grouped-by-file-worst-first @verified @source:extensions/vscode/src/findingsView.ts#FindingsProvider @test:extensions/vscode/src/test/findingsView.test.ts#groups come back worst-first, not alphabetically @test:extensions/vscode/src/test/findingsView.test.ts#findings order worst first, then by file, then by line @test:extensions/vscode/src/test/findingsView.test.ts#nothing is dropped on the way into a group @test:extensions/vscode/src/test/findingsView.test.ts#group ids are unique even when two files share a basename
  Scenario: Findings are grouped by file, worst file first, each group showing its severity tally
    Given the latest scans report a low finding in a.py and two high findings and one low finding in src/z.py
    When the developer opens the Findings panel
    Then the first group is "z.py" described "src · 2 high, 1 low"
    And the second group is "a.py" described ". · 1 low"
    And within a group findings run worst first, then by line, each labelled with its kind and tool

  @id:extensions.findings.findings-panel.002 @rule:findings.panel.empty-states @inferred @source:extensions/vscode/src/extension.ts#activate
  Scenario Outline: An empty panel says whether nothing was scanned, nothing was found or the filter hides everything
    Given <state>
    When the developer opens the Findings panel
    Then the panel says "<message>" with a "<action>" link

    Examples:
      | state                            | message                               | action           |
      | no scan has completed yet        | No scan yet.                          | Scan Workspace   |
      | the last scan found no red flags | No red flags in this workspace.       | Scan Again       |
      | the filter hides every finding   | No findings match the current filter. | Clear the filter |
