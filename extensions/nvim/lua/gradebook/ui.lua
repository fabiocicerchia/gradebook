local core = require('gradebook.core')

local M = {}

local state = { reports = {}, workspace = {} }

function M.remember(tool, report, workspace)
  state.reports[tool] = report
  state.workspace[tool] = workspace
end

function M.forget()
  state = { reports = {}, workspace = {} }
end

function M.lines()
  local out = {}
  for _, tool in ipairs({ 'code', 'tests' }) do
    local report = state.reports[tool]
    if report then
      if #out > 0 then
        out[#out + 1] = ''
      end
      vim.list_extend(out, core.summary(report, state.workspace[tool]))
    end
  end
  if #out == 0 then
    out = { 'No scan yet — run :Gradebook.' }
  end
  return out
end

--- A scratch float, closed with q or <Esc>. No plugin state to leak.
function M.show()
  local lines = M.lines()
  local width = 0
  for _, line in ipairs(lines) do
    width = math.max(width, vim.fn.strdisplaywidth(line))
  end
  width = math.min(width + 2, vim.o.columns - 4)
  local height = math.min(#lines, vim.o.lines - 6)

  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.bo[buf].modifiable = false
  vim.bo[buf].filetype = 'gradebook'

  local win = vim.api.nvim_open_win(buf, true, {
    relative = 'editor',
    row = math.floor((vim.o.lines - height) / 2) - 1,
    col = math.floor((vim.o.columns - width) / 2),
    width = width,
    height = height,
    style = 'minimal',
    border = 'rounded',
    title = ' gradebook ',
  })
  for _, key in ipairs({ 'q', '<Esc>' }) do
    vim.keymap.set('n', key, function()
      if vim.api.nvim_win_is_valid(win) then
        vim.api.nvim_win_close(win, true)
      end
    end, { buffer = buf, nowait = true, silent = true })
  end
  return win, buf
end

return M
