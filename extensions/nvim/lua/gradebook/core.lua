-- The part of the plugin with no `vim.` in it.
--
-- Building argv, deciding which findings can be anchored to a line, and
-- shaping diagnostics are all plain data work — keeping them here means they
-- test under plain Lua, with no editor and no plenary.

local M = {}

--- The command line for one tool over one directory.
function M.argv(cmd, root)
  local argv = {}
  for _, part in ipairs(cmd) do
    argv[#argv + 1] = part
  end
  argv[#argv + 1] = root
  argv[#argv + 1] = '--format'
  argv[#argv + 1] = 'json'
  return argv
end

function M.excluded(file, prefixes)
  for _, prefix in ipairs(prefixes or {}) do
    if prefix ~= '' and file:sub(1, #prefix) == prefix then
      return true
    end
  end
  return false
end

--- A finding that names a real file at a real line can be squiggled.
--
-- `dependency-cycle` puts "a -> b -> a" in `file` with line 0; guessing a path
-- for it would flag innocent code, so it goes to the report window instead.
function M.anchored(finding, exists)
  return finding.line ~= nil and finding.line > 0 and exists(finding.file)
end

--- Split findings into the ones that get a diagnostic and the ones that do not.
function M.split(findings, prefixes, exists)
  exists = exists or function()
    return true
  end
  local anchored, workspace = {}, {}
  for _, finding in ipairs(findings or {}) do
    if not M.excluded(finding.file, prefixes) then
      local bucket = M.anchored(finding, exists) and anchored or workspace
      bucket[#bucket + 1] = finding
    end
  end
  return anchored, workspace
end

--- Diagnostics, grouped by the file they belong to. Lines are 0-based here.
--
-- A bucket mapped to `false` means "do not report these", which is not the
-- same as unmapped: an unmapped bucket falls back to `low` rather than
-- vanishing, because a finding the tools produced must not disappear because
-- this table has not caught up with them.
function M.diagnostics(findings, severity, source)
  local by_file = {}
  for _, finding in ipairs(findings) do
    local level = severity[finding.severity]
    if level == nil then
      level = severity.low
    end
    if level ~= false then
      local list = by_file[finding.file]
      if not list then
        list = {}
        by_file[finding.file] = list
      end
      list[#list + 1] = {
        lnum = finding.line - 1,
        col = 0,
        message = finding.message,
        severity = level,
        source = source,
        code = finding.kind,
      }
    end
  end
  return by_file
end

--- The CLI's bar, so the window and `gradebook-code .` read the same.
function M.bar(score, width)
  width = width or 20
  if score == nil then
    return string.rep('·', width)
  end
  local filled = math.floor(score * width + 0.5)
  return string.rep('█', filled) .. string.rep('░', width - filled)
end

--- The report window's lines: grade, the dimension table, the biggest wins.
function M.summary(report, workspace)
  local out = {
    string.format('%s %s — %.1f/100   grade %s', report.tool, report.version, report.score, report.grade),
    '',
  }
  for _, dim in ipairs(report.dimensions or {}) do
    local points = dim.score == nil and '  n/a' or string.format('%5.1f', dim.points)
    out[#out + 1] = string.format('  %-30s %s %s/%-3d %s', dim.title, M.bar(dim.score), points, dim.weight, dim.detail)
  end
  if report.recommendations and #report.recommendations > 0 then
    out[#out + 1] = ''
    out[#out + 1] = 'Biggest wins:'
    for _, win in ipairs(report.recommendations) do
      out[#out + 1] = string.format('  +%-5.1f %s', win.points, win.advice)
    end
  end
  if workspace and #workspace > 0 then
    out[#out + 1] = ''
    out[#out + 1] = string.format('Workspace findings (%d):', #workspace)
    for _, finding in ipairs(workspace) do
      out[#out + 1] = string.format('  %s  %s — %s', finding.file, finding.kind, finding.message)
    end
  end
  return out
end

return M
