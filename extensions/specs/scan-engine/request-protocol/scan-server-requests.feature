@domain:scan-engine @area:request-protocol @from:vscode/server
Feature: Exchanging requests with the scan server
  Keeps the newline-delimited JSON conversation between the editor extension and the scan server usable, so one bad request or stray output never ends the session.

  Background:
    Given Given the scan server is running

  @id:extensions.scan-engine.request-protocol.001 @rule:scan-engine.request-protocol.stdout-carries-only-replies @inferred @source:extensions/vscode/server/gradebook_server.py#main
  Scenario: Stray output from a tool never lands in the reply stream
    Given a gradebook tool prints a warning while it loads
    When the editor extension asks for a scan
    Then the warning appears on the server's error output
    And the reply stream holds only JSON reply lines, one per line
