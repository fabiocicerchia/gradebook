# Editor integration

Both tools run inside the editor: red flags become squiggles on the line that
owns them, and the score, the dimension table and the biggest wins go in a
report view.

There is no language server. VS Code talks to a small standard-library Python
scan server over stdio; Neovim shells out to the two CLIs. Both are thin —
the scoring lives in the two modules and nowhere else.

## What you get

- **Diagnostics** from the red flags, with a `source` of `gradebook-code` or
  `gradebook-tests`, so the two stay separable in the Problems panel or in
  `vim.diagnostic`.
- **Severity** — `high`, `medium`, `low` — comes from the tool. Every finding
  carries one in `--format json`, derived from the same `FLAG_ORDER` that
  ranks the text report, so no editor keeps its own copy of the ranking.
- **A Findings panel** — every red flag, grouped by file, filterable by
  severity and by tool.
- **A score view** with the grade, the dimension table and the biggest wins.
- **Two status bar entries**, one per tool — `$(code) C 68.2` and
  `$(beaker) D 41.7` — so both scores are visible at once. Click either to
  open the report; they turn amber below `failUnder`.
- **Workspace-level findings.** A `dependency-cycle` names a loop of modules
  (`a -> b -> a`) and has no line; anything with no file on disk to point at
  goes to the score view rather than onto a guessed path.

## Why it scans the whole repo

Hotspots need `git log` and duplication is cross-file, so there is no
meaningful single-file score — the tools take a directory and reject anything
else. A full scan of a mid-sized repo is about **0.25 s**, which is why
scanning on save is the default and scanning as you type is viable, debounced.

## VS Code

```sh
pipx install gradebook-code gradebook-tests
```

Install the extension from the marketplace, or side-load a build:

```sh
make ext-install     # builds gradebook-<version>.vsix and installs it
```

### Commands

| Command | What it does |
|---|---|
| `gradebook: Scan Workspace` | Rescan now |
| `gradebook: Open Report` | Open the score view |
| `gradebook: Filter Findings` | Narrow the panel by severity and tool |
| `gradebook: Clear the findings filter` | Show everything again |
| `gradebook: Expand All Findings` | Open every group (collapse uses the view's own button) |
| `gradebook: Show Log` | Open the log channel |
| `gradebook: Restart Scan Server` | Restart the Python scan server |
| `gradebook: Cancel Running Scan` | Drop the answer to a scan in flight |

### Settings

| Setting | Default | What it does |
|---|---|---|
| `gradebook.enable` | `true` | Turn the extension off without uninstalling it |
| `gradebook.run` | `onSave` | `onSave`, `onType` or `manual` |
| `gradebook.debounceMs` | `400` | Idle time before an `onType` scan |
| `gradebook.pythonPath` | `python3` | Interpreter for the scan server |
| `gradebook.codePath` | `""` | `gradebook_code.py` or its folder. Empty finds a checkout in the workspace, then the installed package |
| `gradebook.testsPath` | `""` | `gradebook_tests.py` or its folder, same fallback |
| `gradebook.tools` | `["code","tests"]` | Which tools to run |
| `gradebook.scanProjectOnStartup` | `true` | Scan once when the window opens |
| `gradebook.failUnder` | `0` | Flag the status bar below this score |
| `gradebook.exclude` | `[]` | Path prefixes whose findings are dropped |
| `gradebook.trace` | `false` | Log every request and response |

Neither package installed? Opening the gradebook repository itself still
works — an empty `codePath`/`testsPath` resolves against the workspace root
before falling back to the installed package. For a checkout somewhere else,
point the two settings at it.

If a tool cannot be found the scan says so, with the command that fixes it.
The two are independent: one missing package does not stop the other from
scoring.

## Neovim

Needs Neovim 0.10+ and the two CLIs on `$PATH`.

```lua
{
  'FabioCicerchia/gradebook',
  config = function()
    require('gradebook').setup({})
  end,
}
```

| Command | What it does |
|---|---|
| `:Gradebook` | Scan the project now |
| `:GradebookReport` | Open the score report in a float |
| `:checkhealth gradebook` | Check the CLIs are reachable |

### Options

```lua
require('gradebook').setup({
  enabled = true,
  tools = { 'code', 'tests' },
  cmd = {
    code = { 'gradebook-code' },
    tests = { 'gradebook-tests' },
  },
  run = 'on_save',            -- 'on_save' | 'on_type' | 'manual'
  debounce_ms = 400,
  scan_project_on_startup = true,
  timeout_ms = 30000,
  exclude = {},
  diagnostics = {
    enabled = true,
    -- `false` for a bucket means "do not report these".
    severity = {
      high = vim.diagnostic.severity.ERROR,
      medium = vim.diagnostic.severity.WARN,
      low = vim.diagnostic.severity.HINT,
    },
  },
})
```

`cmd` is a list per tool, so a checkout needs no install:

```lua
cmd = { code = { 'python3', '/path/to/gradebook-code/gradebook_code.py' } }
```

## Building them

```sh
make ext-build      # typecheck + esbuild bundle
make ext-package    # gradebook-<version>.vsix
make ext-install    # side-load into VS Code
make ext-publish    # both marketplaces (needs VSCE_PAT and OVSX_PAT)
make test-nvim      # the Neovim plugin specs
```

Node is a build-time dependency of `extensions/vscode` and nothing else. Both
Python packages, and the scan server the extension ships, stay standard
library only.
