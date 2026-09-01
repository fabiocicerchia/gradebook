-- The seam between the CLI and core.lua.
--
-- core_spec builds its tables by hand, where an absent value really is `nil`.
-- A decoded report is not that: `vim.json.decode` turns JSON `null` into
-- `vim.NIL`, a userdata that is *not* equal to `nil`, so every `== nil` check
-- in core.lua takes the wrong branch and then formats a userdata as a number.
-- An unscored dimension is exactly that case, and every repo has one.

local core = require('gradebook.core')
local gradebook = require('gradebook')

local UNSCORED = [[
{
  "tool": "gradebook-code",
  "version": "0.2.0",
  "root": "/repo",
  "score": 53.6,
  "grade": "D",
  "not_scored": ["Hotspots (churn x complexity)"],
  "dimensions": [
    {"id": "kiss", "title": "Simplicity (KISS)", "weight": 13, "score": 0.25,
     "points": 3.2, "lost": 9.8, "detail": "complex", "advice": "split them"},
    {"id": "hotspots", "title": "Hotspots", "weight": 6, "score": null,
     "points": null, "lost": null, "detail": "no churn history", "advice": ""}
  ],
  "recommendations": [{"dimension": "kiss", "points": 9.8, "advice": "split them"}],
  "findings": [
    {"file": "a -> b -> a", "line": 0, "kind": "dependency-cycle",
     "message": "a loop", "severity": "high"}
  ]
}
]]

describe('decode', function()
  it('turns a null into nil, not into vim.NIL', function()
    local report = gradebook.decode(UNSCORED)
    assert.is_nil(report.dimensions[2].score)
    assert.is_nil(report.dimensions[2].points)
    assert.is_nil(report.dimensions[2].lost)
    -- The guard that would have caught the bug: vim.NIL is not nil.
    assert.is_false(report.dimensions[2].score == vim.NIL)
  end)

  it('renders an unscored dimension instead of raising', function()
    local lines = core.summary(gradebook.decode(UNSCORED), {})
    local text = table.concat(lines, '\n')
    assert.truthy(text:find('n/a', 1, true))
    assert.truthy(text:find('53.6/100', 1, true))
  end)

  it('keeps the scored dimensions numeric', function()
    local report = gradebook.decode(UNSCORED)
    assert.equals(0.25, report.dimensions[1].score)
    assert.equals(3.2, report.dimensions[1].points)
  end)

  it('routes a line-0 finding away from a file', function()
    local report = gradebook.decode(UNSCORED)
    local anchored, workspace = core.split(report.findings, {}, function()
      return true
    end)
    assert.equals(0, #anchored)
    assert.equals(1, #workspace)
  end)

  it('survives a real report from each tool', function()
    local root = vim.fn.fnamemodify(vim.fn.resolve(debug.getinfo(1, 'S').source:sub(2)), ':p:h:h:h:h')
    if vim.fn.executable('python3') ~= 1 then
      pending('no python3')
      return
    end
    for _, tool in ipairs({ 'code', 'tests' }) do
      local module = vim.fs.joinpath(root, ('gradebook-%s'):format(tool), ('gradebook_%s.py'):format(tool))
      local out = vim.system({ 'python3', module, root, '--format', 'json' }, { text = true }):wait(120000)
      assert.is_true(out.code <= 1, out.stderr)
      local report = gradebook.decode(out.stdout)
      -- Whatever the repo scores today, the window must render it.
      local lines = core.summary(report, {})
      assert.is_true(#lines > 2)
      for _, dim in ipairs(report.dimensions) do
        assert.is_true(dim.score == nil or type(dim.score) == 'number')
      end
    end
  end)
end)
