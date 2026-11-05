-- `gradebook.scan()` against the real CLIs: argv, vim.system, the exit-code
-- check, decode and publish, with nothing doubled.
--
-- decode_spec runs the CLIs itself and smoke.lua only takes the happy path.
-- The branches in `run()` that decide whether a report is used at all — exit
-- 1 is a --fail-under gate and still carries a report, a crash does not — are
-- only reachable through a real process.

local gradebook = require('gradebook')
local ui = require('gradebook.ui')

local repo = vim.fn.fnamemodify(vim.fn.resolve(debug.getinfo(1, 'S').source:sub(2)), ':p:h:h:h:h:h')

--- Run one scan to completion and return what `on_done` was told.
local function scan(cmd)
  gradebook.setup({ cmd = cmd, tools = { 'code' }, run = 'manual', scan_project_on_startup = false })
  local done, result = false, nil
  gradebook.scan({
    on_done = function(ok)
      done, result = true, ok
    end,
  })
  assert.is_true(vim.wait(60000, function()
    return done
  end, 50), 'the scan never finished')
  return result
end

describe('scan against the real CLI', function()
  local project, bufnr

  before_each(function()
    if vim.fn.executable('python3') ~= 1 then
      pending('no python3')
      return
    end
    ui.forget()
    project = vim.fn.tempname()
    vim.fn.mkdir(project .. '/src', 'p')
    local tangled = { 'def tangled(x):' }
    for i = 1, 40 do
      tangled[#tangled + 1] = ('    if x == %d:'):format(i)
      tangled[#tangled + 1] = '        pass'
    end
    tangled[#tangled + 1] = '    return x'
    vim.fn.writefile(tangled, project .. '/src/tangled.py')
    vim.uv.chdir(project)
    vim.env.PYTHONPATH = repo .. '/gradebook-code'
    vim.cmd.edit(project .. '/src/tangled.py')
    bufnr = vim.fn.bufnr('%')
  end)

  after_each(function()
    vim.cmd('silent! %bwipeout!')
    vim.diagnostic.reset()
  end)

  it('publishes the report even when --fail-under exits 1', function()
    local ok = scan({ code = { 'python3', '-m', 'gradebook_code', '--fail-under', '101' } })
    assert.is_true(ok)
    assert.truthy(table.concat(ui.lines(), '\n'):find('gradebook%-code'))
    local kinds = {}
    for _, diagnostic in ipairs(vim.diagnostic.get(bufnr)) do
      kinds[diagnostic.code] = true
    end
    assert.is_true(kinds['complex-function'] == true)
  end)

  it('reports a tool that produced no report as a failure', function()
    local ok = scan({ code = { 'python3', '-m', 'gradebook_nonexistent' } })
    assert.is_false(ok)
    assert.same({ 'No scan yet — run :Gradebook.' }, ui.lines())
    assert.equals(0, #vim.diagnostic.get(bufnr))
  end)
end)
