@domain:score-reporting @area:score-report @from:vscode/src
Feature: Reading the score report
  Developers read each tool's score, grade, dimension breakdown and biggest wins beside their code, laid out like the CLI.

  Background:
    Given a workspace folder is open

  @id:extensions.score-reporting.score-report.004 @rule:score-reporting.report.score-dimensions-and-wins @verified @source:extensions/vscode/src/report.ts#renderHtml @test:extensions/vscode/src/test/report.test.ts#the view shows the grade, the table and the wins @test:extensions/vscode/src/test/report.test.ts#an unscored dimension draws a dotted bar
  Scenario: The report shows each tool's score and grade, every dimension, the unscored ones and the biggest wins
    Given the code scan scored 53.6/100, grade D
    And its "Simplicity (KISS)" dimension earned 3.2 of 13 points
    And its "Hotspots (churn x complexity)" dimension, weight 6, was left unscored
    And its top recommendation is worth 9.8 points: "split the big ones"
    When the developer shows the report
    Then the code section heads "gradebook-code — 53.6/100 (grade D)"
    And Simplicity (KISS) reads 3.2/13 and Hotspots reads n/a/6 with a dotted bar
    And the report notes "Not scored (weights redistributed): Hotspots (churn x complexity)."
    And "Biggest wins" lists "+9.8 split the big ones"

  @id:extensions.score-reporting.score-report.005 @rule:score-reporting.report.no-scan-yet @verified @source:extensions/vscode/src/report.ts#renderHtml @test:extensions/vscode/src/test/report.test.ts#with nothing scanned the view says so
  Scenario: Before any scan the report says there is nothing yet and how to get it
    Given no scan has completed
    When the developer shows the report
    Then the report reads "No scan yet — run gradebook: Scan Workspace."

  @id:extensions.score-reporting.score-report.006 @rule:score-reporting.report.markup-shown-as-text @verified @source:extensions/vscode/src/report.ts#escape @test:extensions/vscode/src/test/report.test.ts#markup in a message is escaped, not rendered
  Scenario: Text from the scanned repository is shown as text, never run as markup
    Given a workspace finding (one with no line to point at) carries the message "<script>alert(1)</script>"
    When the developer shows the report
    Then the report shows the message literally as "<script>alert(1)</script>"
    And no script from the repository runs in the report
