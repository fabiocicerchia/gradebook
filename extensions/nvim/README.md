# gradebook.nvim

Grades the project you are in against a weighted rubric, puts every red flag on
the line that owns it, and shows which fix buys the most points.

No LSP — it shells out to the two CLIs and publishes through `vim.diagnostic`.

## Requirements

Neovim 0.10+ and the tools themselves:

```sh
pipx install gradebook-code gradebook-tests
```

## Install

lazy.nvim:

```lua
{
  'FabioCicerchia/gradebook',
  config = function()
    require('gradebook').setup({})
  end,
}
```

Working from a checkout instead? Point `cmd` at the modules:

```lua
require('gradebook').setup({
  cmd = {
    code = { 'python3', '/path/to/gradebook-code/gradebook_code.py' },
    tests = { 'python3', '/path/to/gradebook-tests/gradebook_tests.py' },
  },
})
```

## Commands

| Command | What it does |
|---|---|
| `:Gradebook` | Scan the project now |
| `:GradebookReport` | Open the score report in a float |
| `:checkhealth gradebook` | Check the CLIs are reachable |

Scripting it? `require('gradebook').scan({ on_done = function(ok) ... end })`
— the two tools land independently, so the callback is the only honest
"finished" signal.

## Options

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
  exclude = {},               -- path prefixes whose findings are dropped
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

## Notes

- **Whole-repo, not per-file.** Hotspots need `git log` and duplication is
  cross-file, so there is no meaningful single-file score. A full scan of a
  mid-sized repo is ~0.25s, which is why `on_save` is the default.
- **Findings with no line to point at** — a `dependency-cycle` names a loop of
  modules — go to `:GradebookReport` rather than onto a guessed path.
- Diagnostics carry a `source` of `gradebook-code` or `gradebook-tests`, so
  the two stay separable.

## Development

```sh
make test    # plenary specs, headless
make smoke   # drive the real CLIs against a throwaway project
make lint    # check the Lua parses
```

`lua/gradebook/core.lua` has no `vim.` calls in it — that is deliberate, and
it is why the specs can cover argv building, finding routing and the report
without an editor.
