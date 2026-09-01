import * as assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  allOf,
  compareEntries,
  countBySeverity,
  Entry,
  FindingsProvider,
  group,
  groupKey,
  isNarrowed,
  matches,
} from '../findingsView';

const entry = (over: Partial<Entry> = {}): Entry => ({
  file: 'src/a.py',
  line: 12,
  kind: 'complex-function',
  message: 'too much',
  severity: 'medium',
  tool: 'code',
  ...over,
});

test('findings order worst first, then by file, then by line', () => {
  const sorted = [
    entry({ severity: 'low', file: 'a.py' }),
    entry({ severity: 'high', file: 'z.py' }),
    entry({ severity: 'high', file: 'a.py', line: 9 }),
    entry({ severity: 'high', file: 'a.py', line: 2 }),
  ].sort(compareEntries);
  assert.deepEqual(
    sorted.map((e) => `${e.severity}:${e.file}:${e.line}`),
    ['high:a.py:2', 'high:a.py:9', 'high:z.py:12', 'low:a.py:12'],
  );
});

test('each grouping picks its own key', () => {
  const e = entry({ severity: 'high', kind: 'god-file', file: 'src/big.py' });
  assert.equal(groupKey(e, 'severity'), 'high');
  assert.equal(groupKey(e, 'kind'), 'god-file');
  assert.equal(groupKey(e, 'file'), 'src/big.py');
});

test('groups come back worst-first, not alphabetically', () => {
  const grouped = group(
    [entry({ file: 'a.py', severity: 'low' }), entry({ file: 'z.py', severity: 'high' })],
    'file',
  );
  assert.deepEqual(
    grouped.map(([label]) => label),
    ['z.py', 'a.py'],
  );
});

test('grouping by severity orders high, medium, low', () => {
  const grouped = group(
    [entry({ severity: 'low' }), entry({ severity: 'high' }), entry({ severity: 'medium' })],
    'severity',
  );
  assert.deepEqual(
    grouped.map(([label]) => label),
    ['high', 'medium', 'low'],
  );
});

test('nothing is dropped on the way into a group', () => {
  const entries = [entry(), entry({ file: 'b.py' }), entry({ file: 'b.py', line: 3 })];
  const total = group(entries, 'file').reduce((n, [, children]) => n + children.length, 0);
  assert.equal(total, entries.length);
});

test('severities are counted per bucket', () => {
  assert.deepEqual(countBySeverity([entry({ severity: 'high' }), entry({ severity: 'high' })]), {
    high: 2,
    medium: 0,
    low: 0,
  });
});

// --- filtering ---------------------------------------------------------------

test('the default filter narrows nothing', () => {
  const filter = allOf();
  assert.equal(isNarrowed(filter), false);
  assert.equal(matches(entry(), filter), true);
});

test('a severity filter keeps only that severity', () => {
  const filter = { ...allOf(), severities: new Set<Entry['severity']>(['high']) };
  assert.equal(isNarrowed(filter), true);
  assert.equal(matches(entry({ severity: 'high' }), filter), true);
  assert.equal(matches(entry({ severity: 'low' }), filter), false);
});

test('a tool filter keeps only that tool', () => {
  const filter = { ...allOf(), tools: new Set<Entry['tool']>(['tests']) };
  assert.equal(isNarrowed(filter), true);
  assert.equal(matches(entry({ tool: 'tests' }), filter), true);
  assert.equal(matches(entry({ tool: 'code' }), filter), false);
});

test('the two axes combine', () => {
  const filter = {
    severities: new Set<Entry['severity']>(['high']),
    tools: new Set<Entry['tool']>(['code']),
  };
  assert.equal(matches(entry({ severity: 'high', tool: 'code' }), filter), true);
  assert.equal(matches(entry({ severity: 'high', tool: 'tests' }), filter), false);
});

test('the provider shows only what passes the filter', () => {
  const provider = new FindingsProvider();
  provider.setEntries([
    entry({ severity: 'high' }),
    entry({ severity: 'low', file: 'b.py' }),
    entry({ severity: 'low', file: 'c.py', tool: 'tests' }),
  ]);
  assert.equal(provider.visible().length, 3);
  assert.equal(provider.narrowed, false);

  provider.setFilter({ ...allOf(), severities: new Set<Entry['severity']>(['low']) });
  assert.equal(provider.visible().length, 2);
  assert.equal(provider.all().length, 3, 'the filter hides, it does not discard');
  assert.equal(provider.narrowed, true);

  provider.clearFilter();
  assert.equal(provider.visible().length, 3);
  assert.equal(provider.narrowed, false);
});

test('picking nothing means no constraint, not an empty panel', () => {
  const provider = new FindingsProvider();
  provider.setEntries([entry(), entry({ severity: 'low' })]);
  provider.setFilter({ severities: new Set(), tools: new Set() });
  assert.equal(provider.visible().length, 2, 'an empty pick emptied the panel');
  assert.equal(provider.narrowed, false);
});

test('the tree renders the filtered set, not everything', () => {
  const provider = new FindingsProvider();
  provider.setEntries([
    entry({ severity: 'high', file: 'a.py' }),
    entry({ severity: 'low', file: 'b.py' }),
  ]);
  provider.setFilter({ ...allOf(), severities: new Set<Entry['severity']>(['high']) });
  const groups = provider.getChildren();
  assert.equal(groups.length, 1);
});

// --- expand and collapse -----------------------------------------------------

test('collapsing gives the groups new ids, so VS Code re-reads the state', () => {
  const provider = new FindingsProvider();
  provider.setEntries([entry()]);
  const before = provider.getChildren();
  const idBefore = (provider.getTreeItem(before[0]) as { id?: string }).id;

  provider.setExpanded(false);
  const after = provider.getChildren();
  const item = provider.getTreeItem(after[0]) as { id?: string; collapsibleState?: number };
  // Same group, different id: without this VS Code keeps its stored expansion
  // state and the collapse is silently ignored.
  assert.notEqual(item.id, idBefore);
  assert.equal(item.collapsibleState, 1, 'Collapsed');

  provider.setExpanded(true);
  const expanded = provider.getTreeItem(provider.getChildren()[0]) as { collapsibleState?: number };
  assert.equal(expanded.collapsibleState, 2, 'Expanded');
});

test('group ids are unique even when two files share a basename', () => {
  const provider = new FindingsProvider();
  provider.setEntries([entry({ file: 'a/util.py' }), entry({ file: 'b/util.py' })]);
  const ids = provider.getChildren().map((g) => (provider.getTreeItem(g) as { id?: string }).id);
  assert.equal(new Set(ids).size, 2, 'two groups collided on one id');
});
