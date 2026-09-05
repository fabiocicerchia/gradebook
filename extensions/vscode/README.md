# gradebook for VS Code

Grades the repository you have open against a weighted rubric, puts every red
flag on the line that owns it, and shows which fix buys the most points.

Two tools, one extension:

- **gradebook-code** scores the code — SOLID, KISS, DRY, hotspots, duplication.
- **gradebook-tests** scores the test suite that covers it.

Both run by default. Diagnostics carry a distinct `source`
(`gradebook-code` / `gradebook-tests`), so they stay separable in the Problems
panel.

## Requirements

Python 3.10+, plus the tools themselves:

```sh
pipx install gradebook-code gradebook-tests
```

Working from a checkout instead? Point `gradebook.codePath` and
`gradebook.testsPath` at `gradebook-code/` and `gradebook-tests/`.

## What it does

- **Diagnostics** on the file and line each red flag names. Severity comes from
  the tool, not from a copy of its ranking kept here.
- **A score view** (`gradebook: Open Report`) with the grade, the dimension
  table and the biggest wins.
- **Two status bar entries**, one per tool — `$(code) C 68.2` and
  `$(beaker) D 41.7` — so both scores are visible at once. Click either to
  open the report; they turn amber below `failUnder`.
- **Workspace-level findings** — a `dependency-cycle` names a loop of modules,
  not a line — land in the score view rather than on a guessed path.
- **Whole-repo, not per-file.** Hotspots need `git log` and duplication is
  cross-file, so there is no meaningful single-file score. A full scan of a
  mid-sized repo is ~0.25s, which is why `onSave` is the default.

## Commands

| Command                                | What it does                                           |
| -------------------------------------- | ------------------------------------------------------ |
| `gradebook: Scan Workspace`            | Rescan now                                             |
| `gradebook: Open Report`               | Open the score view                                    |
| `gradebook: Filter Findings`           | Narrow the panel by severity and tool                  |
| `gradebook: Clear the findings filter` | Show everything again                                  |
| `gradebook: Expand All Findings`       | Open every group (collapse uses the view's own button) |
| `gradebook: Show Log`                  | Open the log channel                                   |
| `gradebook: Restart Scan Server`       | Restart the Python scan server                         |
| `gradebook: Cancel Running Scan`       | Drop the answer to a scan in flight                    |

## Settings

| Setting                          | Default            | What it does                                                                                           |
| -------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------ |
| `gradebook.enable`               | `true`             | Turn the extension off without uninstalling it                                                         |
| `gradebook.run`                  | `onSave`           | `onSave`, `onType` or `manual`                                                                         |
| `gradebook.debounceMs`           | `400`              | Idle time before an `onType` scan                                                                      |
| `gradebook.pythonPath`           | `python3`          | Interpreter for the scan server                                                                        |
| `gradebook.codePath`             | `""`               | `gradebook_code.py` or its folder. Empty finds a checkout in the workspace, then the installed package |
| `gradebook.testsPath`            | `""`               | `gradebook_tests.py` or its folder, same fallback                                                      |
| `gradebook.tools`                | `["code","tests"]` | Which tools to run                                                                                     |
| `gradebook.scanProjectOnStartup` | `true`             | Scan once when the window opens                                                                        |
| `gradebook.failUnder`            | `0`                | Flag the status bar below this score                                                                   |
| `gradebook.exclude`              | `[]`               | Path prefixes whose findings are dropped                                                               |
| `gradebook.trace`                | `false`            | Log every request and response                                                                         |

## Development

```sh
npm install
npm run typecheck
npm test            # node --test, no test-runner dependency
npm run build       # esbuild -> out/extension.js
npm run package     # gradebook-<version>.vsix
```

`npm run package` runs `vscode:prepublish` first — typecheck, the tests, the
production bundle, then the licence and changelog the VSIX has to carry. A red
test never reaches a registry.

Or from the repository root: `make ext-build`, `make ext-package`,
`make ext-install`, `make ext-publish`.

The scan server (`server/gradebook_server.py`) is standard library only, like
the two tools it imports. The Node toolchain is build-time for this extension
and nothing else.
