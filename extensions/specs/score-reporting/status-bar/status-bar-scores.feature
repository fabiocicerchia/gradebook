@domain:score-reporting @area:status-bar @from:vscode/src
Feature: Watching scores in the status bar
  Developers keep both latest scores in view at a glance and are warned when one drops below the level they set.

  Background:
    Given a workspace folder is open
    And gradebook is enabled

  @id:extensions.score-reporting.status-bar.001 @rule:score-reporting.status-bar.both-scores-fixed-order @verified @source:extensions/vscode/src/status.ts#summaryFor @test:extensions/vscode/src/test/status.test.ts#both scores sit next to each other in one entry @test:extensions/vscode/src/test/status.test.ts#code comes first whichever scan finished first @test:extensions/vscode/src/test/status.test.ts#one tool alone still reads correctly @test:extensions/vscode/src/test/status.test.ts#the two are distinguishable when the scores match
  Scenario Outline: The status bar shows the code score before the tests score, whichever finished first
    Given <scanned>
    When the scans complete
    Then the status bar reads "<text>"
    And choosing it opens the score report

    Examples:
      | scanned                                                           | text                             |
      | code scored C 68.2 and tests scored D 41.7, tests finishing first | $(code) C 68.2  $(beaker) D 41.7 |
      | only tests was scanned, scoring D 41.7                            | $(beaker) D 41.7                 |

  @id:extensions.score-reporting.status-bar.002 @rule:score-reporting.status-bar.tooltip-detail @verified @source:extensions/vscode/src/status.ts#summaryFor @test:extensions/vscode/src/test/status.test.ts#the tooltip covers both tools, with the biggest win for each
  Scenario: Hovering the status bar shows each tool's version, score, unscored dimensions and biggest win
    Given code 0.2.0 scored 68.2, grade C, with Hotspots unscored and a top win of +9.8 "split the big ones"
    And tests 0.2.0 scored 41.7, grade D, with a top win of +12.0 "measure coverage"
    When the developer hovers the status bar entry
    Then it shows "gradebook-code 0.2.0 — 68.2/100, grade C" and "gradebook-tests 0.2.0 — 41.7/100, grade D"
    And it shows "not scored: Hotspots"
    And it shows "biggest win: +9.8 split the big ones" and "biggest win: +12.0 measure coverage"

  @id:extensions.score-reporting.status-bar.003 @rule:score-reporting.threshold.warn-below-fail-under @verified @source:extensions/vscode/src/status.ts#summaryFor @test:extensions/vscode/src/test/status.test.ts#either score below failUnder colours the entry
  Scenario Outline: The status bar turns to the warning colour when any score is below the fail-under level
    Given code scored 68.2 and tests scored 41.7
    And the fail-under setting is <fail_under>
    When the scans complete
    Then the status bar entry is shown in the warning colour: <warned>
    And no popup is shown

    Examples:
      | fail_under | warned |
      | 60         | yes    |
      | 30         | no     |
      | 0          | no     |
