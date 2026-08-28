-- End-to-end: this plugin, the real gradebook CLIs, real files, nothing else
-- on the runtimepath.
--
--   nvim --headless --clean -u tests/smoke.lua

local here = vim.fn.fnamemodify(vim.fn.resolve(debug.getinfo(1, 'S').source:sub(2)), ':p:h:h')
vim.opt.runtimepath:prepend(here)
vim.opt.swapfile = false
vim.cmd('runtime! plugin/gradebook.lua')

local repo = vim.fn.fnamemodify(here, ':h:h')

local failures = {}
local function check(ok, what)
  print((ok and '  ok   ' or '  FAIL ') .. what)
  if not ok then
    failures[#failures + 1] = what
  end
end

-- A project with something to find: one file well over the god-file line, and
-- a function well over the complexity limit.
local project = vim.fn.tempname()
vim.fn.mkdir(project .. '/src', 'p')
local big = { 'def tangled(x):' }
for i = 1, 40 do
  big[#big + 1] = ('    if x == %d:'):format(i)
  big[#big + 1] = '        pass'
end
big[#big + 1] = '    return x'
vim.fn.writefile(big, project .. '/src/tangled.py')
vim.fn.writefile({ 'def ok(a, b):', '    return a + b' }, project .. '/src/ok.py')
vim.fn.writefile({ 'def test_ok():', '    assert 1 == 1' }, project .. '/src/test_ok.py')
vim.uv.chdir(project)

local cmd = {
  code = { 'python3', repo .. '/gradebook-code/gradebook_code.py' },
  tests = { 'python3', repo .. '/gradebook-tests/gradebook_tests.py' },
}

print('gradebook.nvim smoke test')
print('  code:    ' .. table.concat(cmd.code, ' '))
print('  project: ' .. project)

local gradebook = require('gradebook')
gradebook.setup({ cmd = cmd, run = 'manual', scan_project_on_startup = false })

vim.cmd.edit(project .. '/src/tangled.py')
local bufnr = vim.fn.bufnr('%')

-- Both tools run concurrently; `#ui.lines() > 1` would return the moment the
-- faster one lands, so wait on the callback that means "all of them".
local done, all_ok = false, false
gradebook.scan({
  on_done = function(ok)
    done, all_ok = true, ok
  end,
})

local ui = require('gradebook.ui')
check(vim.wait(60000, function()
  return done
end, 100), 'both scans finish within 60s')
check(all_ok, 'neither tool reported a failure')

local report = table.concat(ui.lines(), '\n')
check(report:find('grade %u') ~= nil, 'the report carries a grade')
check(report:find('gradebook%-code') ~= nil, 'the report has a gradebook-code section')
check(report:find('gradebook%-tests') ~= nil, 'the report has a gradebook-tests section')

local diagnostics = vim.diagnostic.get(bufnr)
check(#diagnostics > 0, 'the tangled file gets diagnostics')

local sources, kinds = {}, {}
for _, diagnostic in ipairs(diagnostics) do
  sources[diagnostic.source] = true
  kinds[diagnostic.code] = true
end
check(sources['gradebook-code'] == true, 'diagnostics are sourced to gradebook-code')
check(kinds['complex-function'] == true, 'the over-complex function is flagged')

for _, diagnostic in ipairs(diagnostics) do
  check(diagnostic.lnum >= 0, '0-based line for ' .. tostring(diagnostic.code))
end

-- A clean file gets nothing; a squiggle on ok.py would mean the fan-out put a
-- finding on the wrong buffer.
vim.cmd.edit(project .. '/src/ok.py')
check(#vim.diagnostic.get(vim.fn.bufnr('%')) == 0, 'the clean file stays clean')

if #failures > 0 then
  io.stderr:write(('smoke: %d failure(s)\n'):format(#failures))
  vim.cmd('cq')
end
print('smoke ok')
vim.cmd('qa!')
