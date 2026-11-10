# Specifications of gradebook / extensions

What this code does, one atomic Gherkin scenario per behaviour, read from the code by code-atlas.
Tags: `@verified` a test asserts it · `@inferred` read from the code only · `@gap` an entry point no test covers · `@human` written or amended by a person, never rewritten.

## Findings
Showing each red flag where the developer works, with a file and line wherever there is one.

- **Findings panel**: [Browsing findings in the Findings panel](findings/findings-panel/findings-panel.feature) (2)
- **Inline diagnostics**: [Seeing findings in the editor](findings/inline-diagnostics/editor-findings.feature) (3), [Seeing findings in the code](findings/inline-diagnostics/nvim-inline-diagnostics.feature) (3)
- **Project-wide findings**: [Keeping findings that have no line, and dropping excluded ones](findings/project-wide-findings/nvim-findings-routing.feature) (2)
- **Severity**: [Ranking findings by severity in Neovim](findings/severity/nvim-finding-severity.feature) (1)

## Scan engine
The background scan server the VS Code extension talks to, which loads the gradebook tools and answers scan requests.

- **Request protocol**: [Exchanging requests with the scan server](scan-engine/request-protocol/scan-server-requests.feature) (1)
- **Tool discovery**: [Finding the gradebook tools](scan-engine/tool-discovery/tool-discovery.feature) (3)

## Scanning
Grading the whole project with one or both gradebook tools, and deciding when that happens.

- **Project scan**: [Scanning a project from Neovim](scanning/project-scan/nvim-project-scan.feature) (4)
- **Scan failures**: [Recovering from scan failures](scanning/scan-failures/scan-failures.feature) (2)
- **Scan triggers**: [Choosing when Neovim rescans](scanning/scan-triggers/nvim-scan-triggers.feature) (2), [Scanning the workspace](scanning/scan-triggers/scanning-the-workspace.feature) (5)

## Score reporting
Showing the grade, how it breaks down, and which fix gains the most points.

- **Score report**: [Reading the score report in Neovim](score-reporting/score-report/nvim-score-report.feature) (3), [Reading the score report](score-reporting/score-report/score-report.feature) (3)
- **Status bar**: [Watching scores in the status bar](score-reporting/status-bar/status-bar-scores.feature) (3)

## Setup and diagnostics
Setting up the editor plugins and finding out why they are not working.

- **Health check**: [Checking the Neovim setup](setup-and-diagnostics/health-check/nvim-health-check.feature) (3)
- **Settings**: [Configuring the Neovim plugin](setup-and-diagnostics/settings/nvim-settings.feature) (3)
