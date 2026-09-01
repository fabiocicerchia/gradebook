import * as assert from 'node:assert/strict';
import { test } from 'node:test';
import { bar, renderHtml, Section } from '../report';
import { Report } from '../types';

const report = (over: Partial<Report> = {}): Report => ({
  tool: 'gradebook-code',
  version: '0.2.0',
  root: '/repo',
  score: 53.6,
  grade: 'D',
  dimensions: [
    {
      id: 'kiss',
      title: 'Simplicity (KISS)',
      weight: 13,
      score: 0.25,
      points: 3.2,
      lost: 9.8,
      detail: '8.9 average complexity',
      advice: 'split the big ones',
    },
    {
      id: 'hotspots',
      title: 'Hotspots (churn x complexity)',
      weight: 6,
      score: null,
      points: 0,
      lost: 0,
      detail: 'no churn history to rank by',
      advice: '',
    },
  ],
  not_scored: ['Hotspots (churn x complexity)'],
  recommendations: [{ dimension: 'kiss', points: 9.8, advice: 'split the big ones' }],
  findings: [],
  ...over,
});

test('an unscored dimension draws a dotted bar', () => {
  assert.equal(bar(null), '·'.repeat(20));
  assert.equal(bar(1), '█'.repeat(20));
  assert.equal(bar(0.5), '█'.repeat(10) + '░'.repeat(10));
});

test('the view shows the grade, the table and the wins', () => {
  const html = renderHtml([{ tool: 'code', report: report(), workspace: [] }]);
  assert.match(html, /53\.6\/100/);
  assert.match(html, /grade D/);
  assert.match(html, /Simplicity \(KISS\)/);
  assert.match(html, /n\/a\/6/);
  assert.match(html, /Biggest wins/);
  assert.match(html, /Not scored/);
});

test('workspace findings land in the view, not on a file', () => {
  const section: Section = {
    tool: 'code',
    report: report(),
    workspace: [
      {
        file: 'a -> b -> a',
        line: 0,
        kind: 'dependency-cycle',
        message: 'modules import each other in a loop',
        severity: 'high',
      },
    ],
  };
  const html = renderHtml([section]);
  assert.match(html, /Workspace findings \(1\)/);
  assert.match(html, /a -&gt; b -&gt; a/);
});

test('markup in a message is escaped, not rendered', () => {
  const html = renderHtml([
    {
      tool: 'code',
      report: report(),
      workspace: [
        {
          file: 'x.py',
          line: 0,
          kind: 'dead-code',
          message: '<script>alert(1)</script>',
          severity: 'low',
        },
      ],
    },
  ]);
  assert.ok(!html.includes('<script>'));
  assert.match(html, /&lt;script&gt;/);
});

test('with nothing scanned the view says so', () => {
  assert.match(renderHtml([]), /No scan yet/);
});
