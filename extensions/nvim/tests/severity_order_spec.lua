-- Drift guard. The tools own the ranking (`FLAG_ORDER` + `severity_for`); this
-- plugin only maps the buckets they produce onto diagnostic levels. If a
-- fourth bucket ever appears upstream, findings in it would quietly fall back
-- to the `low` level — so fail here instead.
--
-- It reads the two modules. Skipped when there is no interpreter or no
-- checkout to read, so the suite still runs anywhere.

local config = require('gradebook.config')

local function buckets_of(tool)
  local root = vim.fn.fnamemodify(vim.fn.resolve(debug.getinfo(1, 'S').source:sub(2)), ':p:h:h:h:h')
  local module = vim.fs.joinpath(root, ('gradebook-%s'):format(tool), ('gradebook_%s.py'):format(tool))
  if vim.fn.executable('python3') ~= 1 or not vim.uv.fs_stat(module) then
    return nil
  end
  local out = vim.system({
    'python3',
    '-c',
    ([[
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("m", %q)
module = importlib.util.module_from_spec(spec)
sys.modules["m"] = module
spec.loader.exec_module(module)
print(json.dumps(sorted({module.severity_for(kind) for kind in module.FLAG_ORDER})))
]]):format(module),
  }, { text = true }):wait(20000)
  if out.code ~= 0 then
    return nil
  end
  local ok, decoded = pcall(vim.json.decode, out.stdout)
  return ok and decoded or nil
end

describe("the tools' severity buckets", function()
  for _, tool in ipairs({ 'code', 'tests' }) do
    it(('every bucket gradebook-%s emits is mapped'):format(tool), function()
      local buckets = buckets_of(tool)
      if not buckets then
        pending(('no python3 or no gradebook-%s to compare against'):format(tool))
        return
      end
      local mapped = config.resolve({}).diagnostics.severity
      assert.is_true(#buckets > 0)
      for _, bucket in ipairs(buckets) do
        assert.is_not_nil(mapped[bucket], 'unmapped severity bucket: ' .. bucket)
      end
    end)
  end

  it('maps nothing the tools do not emit', function()
    local buckets = buckets_of('code')
    if not buckets then
      pending('no python3 or no gradebook-code to compare against')
      return
    end
    local known = {}
    for _, bucket in ipairs(buckets) do
      known[bucket] = true
    end
    for _, bucket in ipairs(buckets_of('tests') or {}) do
      known[bucket] = true
    end
    for bucket in pairs(config.resolve({}).diagnostics.severity) do
      assert.is_true(known[bucket] == true, 'maps a bucket no tool emits: ' .. bucket)
    end
  end)
end)
