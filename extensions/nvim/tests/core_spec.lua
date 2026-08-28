local core = require('gradebook.core')

local function finding(over)
  local base = {
    file = 'src/a.py',
    line = 12,
    kind = 'complex-function',
    message = 'too much',
    severity = 'high',
  }
  for key, value in pairs(over or {}) do
    base[key] = value
  end
  return base
end

local function on_disk(files)
  return function(file)
    for _, name in ipairs(files) do
      if name == file then
        return true
      end
    end
    return false
  end
end

describe('core.argv', function()
  it('appends the root and asks for json', function()
    assert.are.same(
      { 'gradebook-code', '/repo', '--format', 'json' },
      core.argv({ 'gradebook-code' }, '/repo')
    )
  end)

  it('works with a multi-part cmd from a checkout', function()
    assert.are.same(
      { 'python3', '/src/gradebook_code.py', '/repo', '--format', 'json' },
      core.argv({ 'python3', '/src/gradebook_code.py' }, '/repo')
    )
  end)
end)

describe('core.split', function()
  it('anchors a finding on a real file at a real line', function()
    local anchored, workspace = core.split({ finding() }, {}, on_disk({ 'src/a.py' }))
    assert.equals(1, #anchored)
    assert.equals(0, #workspace)
  end)

  it('sends a dependency cycle to the report, not to a guessed path', function()
    local cycle = finding({ file = 'a -> b -> a', line = 0, kind = 'dependency-cycle' })
    local anchored, workspace = core.split({ cycle }, {}, on_disk({}))
    assert.equals(0, #anchored)
    assert.equals(1, #workspace)
  end)

  it('sends a finding on a missing file to the report', function()
    local anchored, workspace = core.split({ finding({ file = 'gone.py' }) }, {}, on_disk({}))
    assert.equals(0, #anchored)
    assert.equals(1, #workspace)
  end)

  it('drops excluded prefixes entirely', function()
    local anchored, workspace =
      core.split({ finding({ file = 'vendor/a.py' }) }, { 'vendor/' }, on_disk({ 'vendor/a.py' }))
    assert.equals(0, #anchored)
    assert.equals(0, #workspace)
  end)
end)

describe('core.diagnostics', function()
  it('groups by file and makes the line 0-based', function()
    local severity = { high = 1, medium = 2, low = 4 }
    local by_file = core.diagnostics(
      { finding(), finding({ line = 20 }), finding({ file = 'b.py', severity = 'low' }) },
      severity,
      'gradebook-code'
    )
    assert.equals(2, #by_file['src/a.py'])
    assert.equals(11, by_file['src/a.py'][1].lnum)
    assert.equals(1, by_file['src/a.py'][1].severity)
    assert.equals(4, by_file['b.py'][1].severity)
    assert.equals('gradebook-code', by_file['b.py'][1].source)
    assert.equals('complex-function', by_file['b.py'][1].code)
  end)

  it('falls back to low for a severity it does not know', function()
    local by_file = core.diagnostics({ finding({ severity = 'unheard-of' }) }, { low = 4 }, 'x')
    assert.equals(4, by_file['src/a.py'][1].severity)
  end)

  it('drops a bucket mapped to false, and only that bucket', function()
    local severity = { high = false, medium = 2, low = 4 }
    local by_file = core.diagnostics(
      { finding({ severity = 'high' }), finding({ file = 'b.py', severity = 'medium' }) },
      severity,
      'x'
    )
    assert.is_nil(by_file['src/a.py'])
    assert.equals(1, #by_file['b.py'])
  end)
end)

describe('core.summary', function()
  local report = {
    tool = 'gradebook-code',
    version = '0.2.0',
    score = 53.6,
    grade = 'D',
    dimensions = {
      { title = 'Simplicity (KISS)', weight = 13, score = 0.25, points = 3.2, detail = 'complex' },
      { title = 'Hotspots', weight = 6, score = nil, points = 0, detail = 'no churn' },
    },
    recommendations = { { points = 9.8, advice = 'split the big ones' } },
  }

  it('carries the grade and both rows', function()
    local lines = core.summary(report, {})
    assert.truthy(lines[1]:find('53.6/100'))
    assert.truthy(lines[1]:find('grade D'))
    assert.truthy(table.concat(lines, '\n'):find('Biggest wins'))
  end)

  it('lines the n/a row up with the scored one', function()
    local lines = core.summary(report, {})
    local scored, unscored = lines[3], lines[4]
    -- The points field is a fixed 5 wide, so " 3.2/" and "  n/a/" are the same
    -- width. ("n/a" carries a slash of its own — skip past it before looking.)
    local function field(line)
      local bar = line:match('[█░·]+', 33)
      local last = select(2, line:find(bar, 33, true))
      return line:sub(last + 1, line:find('/', last + 6, true))
    end
    assert.equals('   3.2/', field(scored))
    assert.equals('   n/a/', field(unscored))
  end)

  it('lists workspace findings under their own heading', function()
    local lines = core.summary(report, {
      { file = 'a -> b -> a', kind = 'dependency-cycle', message = 'loop' },
    })
    assert.truthy(table.concat(lines, '\n'):find('Workspace findings %(1%)'))
  end)
end)

describe('core.bar', function()
  it('draws dots for an unscored dimension', function()
    assert.equals(string.rep('·', 20), core.bar(nil))
    assert.equals(string.rep('█', 20), core.bar(1))
    assert.equals(string.rep('█', 10) .. string.rep('░', 10), core.bar(0.5))
  end)
end)
