@domain:findings @area:inline-diagnostics @from:vscode/src
Feature: Seeing findings in the editor
  Developers see each gradebook red flag on the file and line it points at, ranked by severity, while flags with nothing to point at still reach them elsewhere.

  Background:
    Given a workspace folder is open
    And gradebook is enabled

  @id:extensions.findings.inline-diagnostics.004 @rule:findings.inline.severity-per-tool @verified @source:extensions/vscode/src/diagnostics.ts#Diagnostics @test:extensions/vscode/src/test/diagnostics.test.ts#severity maps high/medium/low onto the editor scale @test:extensions/vscode/src/test/diagnostics.test.ts#a finding on a real file at a real line anchors
  Scenario Outline: A finding appears on its line with the severity gradebook gave it
    Given the <tool> scan reports a <severity> "complex-function" finding at src/a.py line 12
    And src/a.py exists in the workspace
    When the scan completes
    Then src/a.py shows an editor <level> on line 12 with the finding's message
    And the problem is labelled source "gradebook-<tool>" and code "complex-function"

    Examples:
      | tool  | severity | level       |
      | code  | high     | error       |
      | code  | medium   | warning     |
      | tests | low      | information |

  @id:extensions.findings.inline-diagnostics.005 @rule:findings.project-wide.never-on-a-guessed-file @verified @source:extensions/vscode/src/diagnostics.ts#partition @test:extensions/vscode/src/test/diagnostics.test.ts#a dependency cycle never squiggles a guessed path @test:extensions/vscode/src/test/diagnostics.test.ts#line 0 is workspace-level even when the file exists @test:extensions/vscode/src/test/diagnostics.test.ts#a finding on a file that is not on disk goes to the report view @test:extensions/vscode/src/test/report.test.ts#workspace findings land in the view, not on a file
  Scenario Outline: A finding with no real file and line goes to the report and panel, never onto the editor
    Given the code scan reports a <kind> finding with file "<file>" at line <line>
    And <file_state>
    When the scan completes
    Then no editor problem is shown for it
    And the score report lists it under "Workspace findings (1)"
    And the Findings panel lists it without a way to jump to a file

    Examples:
      | kind             | file        | line | file_state             |
      | dependency-cycle | a -> b -> a | 0    | no such file exists    |
      | dead-code        | src/a.py    | 0    | src/a.py exists        |
      | god-file         | gone.py     | 12   | gone.py is not on disk |

  @id:extensions.findings.inline-diagnostics.006 @rule:findings.exclusions.prefix-drops-everywhere @verified @source:extensions/vscode/src/diagnostics.ts#excluded @test:extensions/vscode/src/test/diagnostics.test.ts#excluded prefixes are dropped entirely
  Scenario: Findings under an excluded path prefix are dropped from the editor, the report and the panel
    Given the exclude setting lists "vendor/"
    And the code scan reports a finding at vendor/a.py line 3 and one at src/a.py line 12
    When the scan completes
    Then vendor/a.py shows no gradebook problem
    And neither the report's workspace findings nor the Findings panel lists the vendor/a.py finding
    And the src/a.py finding is still shown
