@domain:score-reporting @area:score-report @from:nvim/lua
Feature: Reading the score report in Neovim
  Shows a Neovim user each tool's score, grade, dimension breakdown and biggest wins in one window, matching what the CLI prints.

  @id:extensions.score-reporting.score-report.001 @rule:score-reporting.score-report.score-grade-dimensions-wins @verified @source:extensions/nvim/lua/gradebook/core.lua#M.summary @test:extensions/nvim/tests/core_spec.lua#carries the grade and both rows @test:extensions/nvim/tests/decode_spec.lua#survives a real report from each tool
  Scenario: The report shows each tool's score, grade, dimensions and biggest wins
    Given the last gradebook-code 0.2.0 scan scored 53.6 with grade D
    And its Simplicity (KISS) dimension earned 3.2 of 13 points
    And its top recommendation is worth 9.8 points: 'split the big ones'
    When the user runs :GradebookReport
    Then a window titled gradebook opens, headed "gradebook-code 0.2.0 — 53.6/100   grade D"
    And a Simplicity (KISS) row shows a bar and "3.2/13"
    And under "Biggest wins:" it reads "+9.8   split the big ones"
    And code comes before tests when both have reported
    And q or Esc closes the window

  @id:extensions.score-reporting.score-report.002 @rule:score-reporting.score-report.unscored-dimension-shown-as-na @verified @source:extensions/nvim/lua/gradebook/core.lua#M.summary @test:extensions/nvim/tests/core_spec.lua#lines the n/a row up with the scored one @test:extensions/nvim/tests/core_spec.lua#draws dots for an unscored dimension @test:extensions/nvim/tests/decode_spec.lua#renders an unscored dimension instead of raising @test:extensions/nvim/tests/decode_spec.lua#turns a null into nil, not into vim.NIL
  Scenario: A dimension with nothing to measure is shown as n/a, not as zero
    Given the last gradebook-code scan left Hotspots unscored because there is no churn history
    When the user runs :GradebookReport
    Then the Hotspots row shows a dotted bar and "n/a/6" instead of points
    And the overall score is still shown

  @id:extensions.score-reporting.score-report.003 @rule:score-reporting.score-report.no-scan-yet @verified @source:extensions/nvim/lua/gradebook/ui.lua#M.lines @test:extensions/nvim/tests/integration/scan_spec.lua#reports a tool that produced no report as a failure
  Scenario: Before any scan has succeeded, the report says how to start one
    Given no scan has produced a report in this session
    When the user runs :GradebookReport
    Then the window reads "No scan yet — run :Gradebook."
