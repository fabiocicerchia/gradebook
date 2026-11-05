local config = require('gradebook.config')
local gradebook = require('gradebook')
local health = require('gradebook.health')

-- :checkhealth output is recorded rather than rendered, so each case can say
-- exactly which line it expects.
describe('health', function()
  local saved, saved_options, report

  local function check(opts)
    gradebook.options = opts
    health.check()
    return report
  end

  local function only(level)
    return vim.tbl_filter(function(entry)
      return entry.level == level
    end, report)
  end

  before_each(function()
    saved, saved_options, report = vim.health, gradebook.options, {}
    local function record(level)
      return function(msg, advice)
        table.insert(report, { level = level, msg = msg, advice = advice })
      end
    end
    vim.health = {
      start = function() end,
      ok = record('ok'),
      warn = record('warn'),
      error = record('error'),
    }
  end)

  after_each(function()
    vim.health, gradebook.options = saved, saved_options
  end)

  it('reports the version of a tool that runs', function()
    check(config.resolve({ tools = { 'code' }, cmd = { code = { 'sh', '-c', 'echo gradebook-code 9.9.9' } } }))
    assert.are.same({ 'gradebook-code 9.9.9' }, vim.tbl_map(function(e)
      return e.msg
    end, only('ok')))
    assert.are.same({}, only('error'))
  end)

  it('says how to install a tool that is not on the PATH', function()
    check(config.resolve({ tools = { 'tests' }, cmd = { tests = { 'gradebook-nowhere-on-path' } } }))
    local errors = only('error')
    assert.equals(1, #errors)
    assert.equals('gradebook-nowhere-on-path is not executable', errors[1].msg)
    assert.matches('subdirectory=gradebook%-tests', errors[1].advice[1])
    assert.matches('cmd%.tests', errors[1].advice[2])
  end)

  it('passes on the stderr of a --version that fails', function()
    check(config.resolve({ tools = { 'code' }, cmd = { code = { 'sh', '-c', 'echo broken >&2; exit 2' } } }))
    local errors = only('error')
    assert.equals(1, #errors)
    assert.equals('sh --version failed: broken', errors[1].msg)
  end)

  it('warns when the plugin is disabled', function()
    check(config.resolve({ enabled = false, tools = { 'code' }, cmd = { code = { 'sh', '-c', 'echo ok' } } }))
    assert.equals('disabled (enabled = false)', only('warn')[1].msg)
  end)

  it('flags a severity bucket with no diagnostic level', function()
    local opts = config.resolve({ tools = { 'code' }, cmd = { code = { 'sh', '-c', 'echo ok' } } })
    opts.diagnostics.severity.medium = nil
    check(opts)
    assert.are.same({ 'no diagnostic severity mapped for "medium"' }, vim.tbl_map(function(e)
      return e.msg
    end, only('error')))
  end)
end)
