local config = require('gradebook.config')
local core = require('gradebook.core')
local ui = require('gradebook.ui')

local M = {}

M.options = config.resolve({})

local namespaces = {}
local timer = nil

local function namespace(tool)
  namespaces[tool] = namespaces[tool] or vim.api.nvim_create_namespace('gradebook-' .. tool)
  return namespaces[tool]
end

local function root()
  return vim.fs.root(0, { '.git' }) or vim.uv.cwd()
end

local function exists(base)
  return function(file)
    local stat = vim.uv.fs_stat(base .. '/' .. file)
    return stat ~= nil and stat.type == 'file'
  end
end

local function publish(tool, report, opts)
  local anchored, workspace = core.split(report.findings, opts.exclude, exists(report.root))
  local ns = namespace(tool)
  vim.diagnostic.reset(ns)
  if not opts.diagnostics.enabled then
    anchored = {}
  end
  for file, diagnostics in pairs(core.diagnostics(anchored, opts.diagnostics.severity, 'gradebook-' .. tool)) do
    local bufnr = vim.fn.bufnr(report.root .. '/' .. file)
    if bufnr > 0 then
      vim.diagnostic.set(ns, bufnr, diagnostics)
    end
  end
  ui.remember(tool, report, workspace)
end

--- Decode a report, mapping JSON `null` to Lua `nil`.
---
--- Not `vim.json.decode` on its own: by default it turns `null` into
--- `vim.NIL`, a userdata that is not equal to `nil`. An unscored dimension has
--- `score`, `points` and `lost` all null, so every `== nil` check downstream
--- would quietly take the *scored* branch and then format a userdata as a
--- number. `luanil` is the one place to get this right, rather than teaching
--- each consumer about a sentinel.
function M.decode(text)
  return vim.json.decode(text, { luanil = { object = true, array = true } })
end

local function run(tool, opts, done)
  local cmd = opts.cmd[tool]
  if not cmd then
    return done(false)
  end
  vim.system(core.argv(cmd, root()), { text = true, timeout = opts.timeout_ms }, function(result)
    vim.schedule(function()
      -- exit 1 is a --fail-under gate, not a crash; the report is still on stdout.
      if result.code > 1 or result.stdout == '' then
        vim.notify(('gradebook-%s failed: %s'):format(tool, result.stderr or result.code), vim.log.levels.WARN)
        return done(false)
      end
      local ok, report = pcall(M.decode, result.stdout)
      if not ok then
        vim.notify('gradebook: unreadable report: ' .. tostring(report), vim.log.levels.WARN)
        return done(false)
      end
      report.tool = report.tool or ('gradebook-' .. tool)
      report.version = report.version or ''
      publish(tool, report, opts)
      done(true)
    end)
  end)
end

--- Scan the whole project. Hotspots need `git log` and duplication is
--- cross-file, so there is no meaningful single-file score.
---
--- The two tools run concurrently and land independently, so `on_done` is the
--- only way to know the whole scan finished — the report window fills in as
--- each one arrives, which looks the same as "done" one tool early.
---@param args table|nil { on_done = fun(ok: boolean) }
function M.scan(args)
  args = type(args) == 'table' and args or {}
  local finish = args.on_done or function() end
  local opts = M.options
  if not opts.enabled or #opts.tools == 0 then
    return finish(false)
  end
  local pending, failed = #opts.tools, false
  for _, tool in ipairs(opts.tools) do
    run(tool, opts, function(ok)
      failed = failed or not ok
      pending = pending - 1
      if pending == 0 then
        finish(not failed)
      end
    end)
  end
end

function M.report()
  ui.show()
end

local function schedule(delay)
  if timer then
    timer:stop()
    timer:close()
  end
  timer = vim.uv.new_timer()
  timer:start(delay, 0, function()
    vim.schedule(M.scan)
  end)
end

function M.setup(opts)
  local options = config.resolve(opts)
  M.options = options
  local group = vim.api.nvim_create_augroup('gradebook', { clear = true })
  if options.run == 'on_save' or options.run == 'on_type' then
    vim.api.nvim_create_autocmd('BufWritePost', {
      group = group,
      callback = function()
        schedule(0)
      end,
    })
  end
  if options.run == 'on_type' then
    vim.api.nvim_create_autocmd({ 'TextChanged', 'TextChangedI' }, {
      group = group,
      callback = function()
        schedule(options.debounce_ms)
      end,
    })
  end
  if options.scan_project_on_startup then
    schedule(0)
  end
  return options
end

return M
