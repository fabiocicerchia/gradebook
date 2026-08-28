-- Defaults and validation.

local M = {}

M.defaults = {
  enabled = true,

  --- Which of the two tools to run.
  tools = { 'code', 'tests' },

  --- How to run each tool. A list, so an interpreter can go in front of it:
  --- `{ 'python3', '/path/to/gradebook_code.py' }` for a checkout.
  cmd = {
    code = { 'gradebook-code' },
    tests = { 'gradebook-tests' },
  },

  --- When to rescan.
  ---   'on_save'  scan when a file is written (the default: the tools read
  ---              files, not buffers, so this is the only mode that scores
  ---              exactly what is on disk)
  ---   'on_type'  scan as you go, debounced. A full scan of a mid-sized repo
  ---              is about 0.25s, which is what makes this viable
  ---   'manual'   only when you ask
  run = 'on_save',

  --- Idle time before an on_type scan. The cost of a keystroke is this timer
  --- being reset, not a scan.
  debounce_ms = 400,

  --- Scan the whole project once when the plugin loads.
  scan_project_on_startup = true,

  --- Give up on a scan that takes longer than this.
  timeout_ms = 30000,

  --- Path prefixes whose findings are dropped, editor-side only.
  exclude = {},

  diagnostics = {
    enabled = true,
    --- The three buckets `severity_for` produces, as editor severities. A
    --- fourth bucket appearing upstream fails tests/severity_order_spec.lua.
    severity = {
      high = vim.diagnostic.severity.ERROR,
      medium = vim.diagnostic.severity.WARN,
      low = vim.diagnostic.severity.HINT,
    },
  },
}

local function merge(defaults, opts)
  local out = {}
  for key, value in pairs(defaults) do
    if type(value) == 'table' and not vim.islist(value) then
      out[key] = merge(value, (opts or {})[key] or {})
    elseif opts and opts[key] ~= nil then
      out[key] = opts[key]
    else
      out[key] = value
    end
  end
  for key, value in pairs(opts or {}) do
    if out[key] == nil then
      out[key] = value
    end
  end
  return out
end

local RUN_MODES = { on_save = true, on_type = true, manual = true }
local TOOLS = { code = true, tests = true }
local SEVERITIES = {
  [vim.diagnostic.severity.ERROR] = true,
  [vim.diagnostic.severity.WARN] = true,
  [vim.diagnostic.severity.INFO] = true,
  [vim.diagnostic.severity.HINT] = true,
}

function M.validate(cfg)
  vim.validate('enabled', cfg.enabled, 'boolean')
  vim.validate('tools', cfg.tools, function(v)
    if not vim.islist(v) or #v == 0 then
      return false
    end
    for _, tool in ipairs(v) do
      if not TOOLS[tool] then
        return false
      end
    end
    return true
  end, 'a non-empty list of: code, tests')
  for tool in pairs(TOOLS) do
    vim.validate('cmd.' .. tool, cfg.cmd[tool], function(v)
      return vim.islist(v) and #v > 0 and type(v[1]) == 'string'
    end, 'a non-empty list of strings')
  end
  vim.validate('run', cfg.run, function(v)
    return RUN_MODES[v] == true
  end, 'one of: on_save, on_type, manual')
  vim.validate('debounce_ms', cfg.debounce_ms, function(v)
    return type(v) == 'number' and v >= 100
  end, 'a number >= 100')
  vim.validate('scan_project_on_startup', cfg.scan_project_on_startup, 'boolean')
  vim.validate('timeout_ms', cfg.timeout_ms, 'number')
  vim.validate('exclude', cfg.exclude, vim.islist, 'a list of path prefixes')
  vim.validate('diagnostics.enabled', cfg.diagnostics.enabled, 'boolean')
  for severity, value in pairs(cfg.diagnostics.severity) do
    vim.validate('diagnostics.severity.' .. severity, value, function(v)
      return v == false or SEVERITIES[v] == true
    end, 'false, or a vim.diagnostic.severity value')
  end
  return cfg
end

function M.resolve(opts)
  return M.validate(merge(M.defaults, opts or {}))
end

return M
