@domain:scan-engine @area:tool-discovery @from:vscode/server
Feature: Finding the gradebook tools
  Lets the scan server find each gradebook tool where the user put it, and explain how to fix things when a tool is missing or too old, without one missing tool disabling the other.

  Background:
    Given the scan server is running

  @id:extensions.scan-engine.tool-discovery.001 @rule:scan-engine.tool-discovery.source-precedence @verified @source:extensions/vscode/server/gradebook_server.py#load_tool @test:extensions/vscode/src/test/server.test.ts#an explicit module path is honoured
  Scenario Outline: A configured tool location wins over an installed tool, which wins over a checkout
    Given gradebook-code is available from <sources>
    When the editor extension pings the scan server
    Then the reply says gradebook-code was loaded from <chosen>

    Examples:
      | sources                                                                         | chosen                              |
      | a configured folder and the installed package                                   | the configured folder               |
      | the installed package and a gradebook checkout open in the editor               | the installed package               |
      | the checkout the extension ships in and a gradebook checkout open in the editor | the checkout the extension ships in |
      | only a gradebook checkout open in the editor                                    | the checkout open in the editor     |

  @id:extensions.scan-engine.tool-discovery.002 @rule:scan-engine.tool-discovery.stale-module-file-setting @inferred @source:extensions/vscode/server/gradebook_server.py#load_tool
  Scenario: A configured path to a module file that no longer exists is read as the folder holding the package
    Given the configured gradebook-code path is /opt/gb/gradebook-code/gradebook_code.py
    And that file does not exist and /opt/gb/gradebook-code holds the gradebook_code package
    When the editor extension asks to scan /home/dev/acme-api with tool code
    Then the reply says ok is true
    And the report names the tool "gradebook-code"

  @id:extensions.scan-engine.tool-discovery.003 @rule:scan-engine.tool-discovery.too-old-tool-refused @inferred @source:extensions/vscode/server/gradebook_server.py#_load_checked
  Scenario: A tool too old for the extension is refused, naming what it lacks
    Given the reachable gradebook-code has no severity_for
    When the editor extension asks to scan /home/dev/acme-api with tool code
    Then the reply says ok is false
    And the error says gradebook-code at its file location "is too old for this extension: it has no severity_for"
    And the error carries the installation advice
