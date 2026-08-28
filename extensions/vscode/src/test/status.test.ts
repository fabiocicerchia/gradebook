import * as assert from 'node:assert/strict';
import { test } from 'node:test';

import { fragmentFor, summaryFor } from '../status';
import { Report, Tool } from '../types';

const report = (over: Partial<Report> = {}): Report => ({
  tool: 'gradebook-code',
  version: '0.2.0',
  root: '/repo',
  score: 68.2,
  grade: 'C',
  dimensions: [],
  not_scored: [],
  recommendations: [],
  findings: [],
  ...over,
});

const tests = report({ tool: 'gradebook-tests', score: 41.7, grade: 'D' });

const both: Array<[Tool, Report]> = [
  ['code', report()],
  ['tests', tests],
];

test('both scores sit next to each other in one entry', () => {
  assert.equal(summaryFor(both, 0)?.text, '$(code) C 68.2  $(beaker) D 41.7');
});

test('code comes first whichever scan finished first', () => {
  const reversed: Array<[Tool, Report]> = [
    ['tests', tests],
    ['code', report()],
  ];
  assert.equal(summaryFor(reversed, 0)?.text, summaryFor(both, 0)?.text);
});

test('one tool alone still reads correctly', () => {
  assert.equal(summaryFor([['tests', tests]], 0)?.text, '$(beaker) D 41.7');
});

test('nothing scanned means nothing shown', () => {
  assert.equal(summaryFor([], 0), undefined);
});

test('the two are distinguishable when the scores match', () => {
  const same = report({ tool: 'gradebook-tests' });
  assert.notEqual(fragmentFor('code', same), fragmentFor('tests', same));
});

test('either score below failUnder colours the entry', () => {
  assert.equal(summaryFor(both, 60)?.warn, true, 'tests is 41.7, under 60');
  assert.equal(summaryFor(both, 30)?.warn, false);
  assert.equal(summaryFor(both, 0)?.warn, false, 'zero disables the warning');
});

test('the tooltip covers both tools, with the biggest win for each', () => {
  const entry = summaryFor(
    [
      ['code', report({ not_scored: ['Hotspots'], recommendations: [{ dimension: 'kiss', points: 9.8, advice: 'split the big ones' }] })],
      ['tests', report({ tool: 'gradebook-tests', score: 41.7, grade: 'D', recommendations: [{ dimension: 'coverage', points: 12, advice: 'measure coverage' }] })],
    ],
    0,
  );
  assert.match(entry!.tooltip, /gradebook-code 0\.2\.0 — 68\.2\/100, grade C/);
  assert.match(entry!.tooltip, /gradebook-tests 0\.2\.0 — 41\.7\/100, grade D/);
  assert.match(entry!.tooltip, /not scored: Hotspots/);
  assert.match(entry!.tooltip, /\+9\.8 split the big ones/);
  assert.match(entry!.tooltip, /\+12\.0 measure coverage/);
  assert.ok(!entry!.tooltip.includes('undefined'));
  assert.ok(!entry!.tooltip.includes('NaN'));
});
