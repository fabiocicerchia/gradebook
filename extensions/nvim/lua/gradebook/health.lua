local M = {}

function M.check()
  vim.health.start('gradebook')
  local opts = require('gradebook').options

  if not opts.enabled then
    vim.health.warn('disabled (enabled = false)')
  end

  for _, tool in ipairs(opts.tools) do
    local cmd = opts.cmd[tool]
    if not cmd or #cmd == 0 then
      vim.health.error(('no cmd configured for %s'):format(tool))
    elseif vim.fn.executable(cmd[1]) == 0 then
      vim.health.error(
        ('%s is not executable'):format(cmd[1]),
        {
          -- Neither tool is on PyPI, and each is a package rather than a
          -- loose file: it is imported by name off PYTHONPATH.
          ('pipx install "git+https://github.com/fabiocicerchia/gradebook.git#subdirectory=gradebook-%s"'):format(
            tool
          ),
          ("or set cmd.%s = { 'env', 'PYTHONSAFEPATH=1', 'PYTHONPATH=/path/to/gradebook-%s', 'python3', '-m', 'gradebook_%s' }"):format(
            tool,
            tool,
            tool
          ),
        }
      )
    else
      local result = vim.system(vim.list_extend(vim.deepcopy(cmd), { '--version' }), { text = true }):wait()
      if result.code == 0 then
        vim.health.ok(vim.trim(result.stdout))
      else
        vim.health.error(('%s --version failed: %s'):format(cmd[1], vim.trim(result.stderr or '')))
      end
    end
  end

  for _, bucket in ipairs({ 'high', 'medium', 'low' }) do
    if opts.diagnostics.severity[bucket] == nil then
      vim.health.error(('no diagnostic severity mapped for "%s"'):format(bucket))
    end
  end
end

return M
