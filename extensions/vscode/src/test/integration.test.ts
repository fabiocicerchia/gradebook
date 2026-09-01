// The client against the real server, on this repo's real reports.
//
// Every other test here builds its fixtures by hand, where a missing value is
// whatever the fixture author remembered to write. Real reports are not that:
// an unscored dimension carries `score`, `points` and `lost` all null, and the
// nvim plugin shipped a crash on exactly that until a smoke test ran. This is
// the same check for this side — spawn the server, scan, and put the answer
// through the modules that render it.

import * as assert from 'node:assert/strict';
import * as path from 'node:path';
import { after, test } from 'node:test';

import { readConfig } from '../config';
import { partition } from '../diagnostics';
import { Engine } from '../engine';
import { Entry, group } from '../findingsView';
import { escape, renderHtml } from '../report';
import { Report, Tool } from '../types';

const repo = path.join(__dirname, '..', '..', '..', '..');
const serverPath = path.join(__dirname, '..', '..', 'server', 'gradebook_server.py');

const config = { ...readConfig(), trace: false };
const engine = new Engine(serverPath, config, () => undefined);

after(() => engine.dispose());

/** Reports are reused across tests: two real scans is enough to pay for once. */
const reports = new Map<Tool, Report>();
async function reportFor(tool: Tool): Promise<Report> {
  const cached = reports.get(tool);
  if (cached) {
    return cached;
  }
  const report = await engine.scanProject(repo, tool);
  reports.set(tool, report);
  return report;
}

test('the engine pings a server it spawned itself', async () => {
  const info = await engine.ping();
  assert.equal(info.protocol, 1);
  assert.match(info.python, /^\d+\.\d+/);
  assert.equal(info.severityOrder['god-file'], 'high');
});

test('both tools score this repo end to end', async () => {
  for (const tool of ['code', 'tests'] as Tool[]) {
    const report = await reportFor(tool);
    assert.equal(report.tool, `gradebook-${tool}`);
    assert.ok(report.score >= 0 && report.score <= 100, `${tool}: ${report.score}`);
    assert.match(report.grade, /^[A-F]$/);
    assert.ok(report.dimensions.length > 0);
  }
});

test('an unscored dimension survives the round trip as null, not undefined', async () => {
  const report = await reportFor('code');
  const unscored = report.dimensions.filter((dim) => dim.score === null);
  // This repo has no churn history in a shallow checkout and no interfaces, so
  // there is always at least one. If that stops being true the guard below is
  // no longer guarding anything, and this should fail loudly rather than pass.
  assert.ok(unscored.length > 0, 'no unscored dimension to check');
  for (const dim of unscored) {
    assert.equal(dim.score, null);
    assert.notEqual(dim.score, undefined);
  }
});

test('the report renders every real dimension, scored or not', async () => {
  const sections = (['code', 'tests'] as Tool[]).map((tool) => ({
    tool,
    report: reports.get(tool)!,
    workspace: [],
  }));
  const html = renderHtml(sections);
  for (const section of sections) {
    for (const dim of section.report.dimensions) {
      // Escaped, not raw: "Naming & intent" reaches the page as "Naming &amp;
      // intent", and asserting on the raw title would only pass by accident.
      assert.ok(html.includes(escape(dim.title)), `missing row: ${dim.title}`);
    }
    // The n/a placeholder, not "null" or "NaN" leaking into the page.
    if (section.report.dimensions.some((d) => d.score === null)) {
      assert.match(html, /n\/a\//);
    }
  }
  assert.ok(!html.includes('NaN'), 'NaN reached the report');
  assert.ok(!html.includes('undefined'), 'undefined reached the report');
});

test('every real finding carries a severity the client understands', async () => {
  for (const tool of ['code', 'tests'] as Tool[]) {
    for (const finding of (await reportFor(tool)).findings) {
      assert.ok(
        ['high', 'medium', 'low'].includes(finding.severity),
        `${tool} ${finding.kind}: ${finding.severity}`,
      );
      assert.equal(typeof finding.line, 'number');
    }
  }
});

test('real findings split into anchored and workspace, losing none', async () => {
  const fs = await import('node:fs');
  for (const tool of ['code', 'tests'] as Tool[]) {
    const report = await reportFor(tool);
    const split = partition(report.findings, [], (file) =>
      fs.existsSync(path.resolve(report.root, file)),
    );
    assert.equal(
      split.anchored.length + split.workspace.length,
      report.findings.length,
      `${tool}: a finding went missing`,
    );
    // Anything anchored must be squiggle-able: a real line in a real file.
    for (const finding of split.anchored) {
      assert.ok(finding.line > 0, `${finding.kind} anchored at line ${finding.line}`);
    }
  }
});

test('the tree groups real findings three ways without losing any', async () => {
  const entries: Entry[] = [];
  for (const tool of ['code', 'tests'] as Tool[]) {
    for (const finding of (await reportFor(tool)).findings) {
      entries.push({ ...finding, tool });
    }
  }
  assert.ok(entries.length > 0, 'this repo has no findings to group');
  for (const grouping of ['file', 'severity', 'kind'] as const) {
    const total = group(entries, grouping).reduce((n, [, kids]) => n + kids.length, 0);
    assert.equal(total, entries.length, `${grouping} dropped findings`);
  }
});

test('a failed scan rejects rather than hanging the client', async () => {
  await assert.rejects(
    () => engine.scanProject(path.join(repo, 'README.md'), 'code'),
    /not a directory/,
  );
  // ... and the server is still usable afterwards.
  assert.equal((await engine.ping()).protocol, 1);
});
