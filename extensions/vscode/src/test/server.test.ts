import { spawnSync } from 'node:child_process';
import * as assert from 'node:assert/strict';
import * as path from 'node:path';
import { test } from 'node:test';

import { frame, Message } from '../engine';

const server = path.join(__dirname, '..', '..', 'server', 'gradebook_server.py');
const repo = path.join(__dirname, '..', '..', '..', '..');

/** Drive the real server: requests in, correlated responses out. */
function talk(requests: object[], args: string[] = []): Map<number, Message> {
  const input = requests.map((r) => JSON.stringify(r)).join('\n') + '\n';
  const run = spawnSync('python3', [server, ...args], { input, encoding: 'utf8' });
  assert.equal(run.status, 0, run.stderr);
  const { lines } = frame('', run.stdout);
  return new Map(
    lines.map((line) => JSON.parse(line) as Message).map((m) => [m.id as number, m]),
  );
}

test('the server announces itself before anything is asked of it', () => {
  const replies = talk([{ id: 1, op: 'ping' }]);
  const ready = replies.get(0);
  assert.equal(ready?.ok, true);
  assert.equal(ready?.event, 'ready');
  assert.equal(ready?.protocol, 1);
});

test('ping reports both versions and every kind bucketed', () => {
  const reply = talk([{ id: 1, op: 'ping' }]).get(1);
  assert.equal(reply?.ok, true);
  const order = reply?.severityOrder as Record<string, string>;
  assert.equal(order['dependency-cycle'], 'high');
  assert.equal(order['stale-test'], 'low');
  const versions = reply?.versions as Record<string, string>;
  assert.match(versions.code, /^\d+\.\d+\.\d+$/);
  assert.match(versions.tests, /^\d+\.\d+\.\d+$/);
});

test('scanProject grades this repo and every finding carries a severity', () => {
  const reply = talk([{ id: 1, op: 'scanProject', root: repo, tool: 'code' }]).get(1);
  assert.equal(reply?.ok, true, reply?.error);
  const report = reply?.report as {
    score: number;
    grade: string;
    tool: string;
    findings: Array<{ severity: string }>;
  };
  assert.equal(report.tool, 'gradebook-code');
  assert.ok(report.score >= 0 && report.score <= 100);
  assert.match(report.grade, /^[A-F]$/);
  for (const finding of report.findings) {
    assert.ok(['high', 'medium', 'low'].includes(finding.severity), finding.severity);
  }
});

test('a bad request fails that request, not the server', () => {
  const replies = talk([
    { id: 1, op: 'nonsense' },
    { id: 2, op: 'ping' },
  ]);
  assert.equal(replies.get(1)?.ok, false);
  assert.match(replies.get(1)?.error ?? '', /unknown op/);
  assert.equal(replies.get(2)?.ok, true);
});

test('malformed json is reported without an id and does not stop the loop', () => {
  const run = spawnSync('python3', [server], {
    input: 'not json\n{"id":2,"op":"ping"}\n',
    encoding: 'utf8',
  });
  const messages = frame('', run.stdout).lines.map((l) => JSON.parse(l) as Message);
  assert.ok(messages.some((m) => m.id === null && m.ok === false));
  assert.ok(messages.some((m) => m.id === 2 && m.ok === true));
});

test('scanning something that is not a directory is an error, not a crash', () => {
  const reply = talk([
    { id: 1, op: 'scanProject', root: path.join(repo, 'README.md'), tool: 'code' },
  ]).get(1);
  assert.equal(reply?.ok, false);
  assert.match(reply?.error ?? '', /not a directory/);
});

test('an explicit module path is honoured', () => {
  const ping = talk(
    [{ id: 1, op: 'ping' }],
    ['--code', path.join(repo, 'gradebook-code'), '--tests', path.join(repo, 'gradebook-tests')],
  ).get(1);
  const modules = ping?.modules as Record<string, string>;
  assert.match(modules.code, /gradebook-code\/gradebook_code\.py$/);
});

test('a module path that does not exist fails the scan, not the server', () => {
  const replies = talk([
    { id: 1, op: 'ping' },
    { id: 2, op: 'scanProject', root: repo, tool: 'code' },
  ], ['--code', '/nope/gradebook_code.py']);
  // Startup used to abort here, which is how a bad path became a silent no-op:
  // the client logged the fatal line to a channel nobody had open.
  assert.equal(replies.get(1)?.ok, true);
  assert.equal(replies.get(2)?.ok, false);
  assert.match(replies.get(2)?.error ?? '', /gradebook-code is not available/);
});

// --- a server that cannot find the tools ------------------------------------
//
// This is what "Scan Workspace does nothing" was: installed from a VSIX with
// neither package on the system, the server died at startup and the client
// said nothing. It must now stay up and explain itself.
//
// The unreachable case is forced with an explicit path that cannot exist,
// never by hiding an installed package. An editable install puts a .pth in
// site-packages that no PYTHONPATH setting can mask, so a test that assumed
// "not installed" passed on a bare checkout and failed on any machine that had
// run `make dev` — an assertion about the developer's environment rather than
// about this code.
const NOWHERE = ['--code', '/nonexistent/gradebook_code.py', '--tests', '/nonexistent/gradebook_tests.py'];

test('with no tool reachable the server still comes up and answers ping', () => {
  const replies = talk([{ id: 1, op: 'ping' }], NOWHERE);
  assert.equal(replies.get(0)?.event, 'ready');
  const ping = replies.get(1);
  assert.equal(ping?.ok, true, 'ping must not fail just because a tool is missing');
  assert.deepEqual(ping?.versions, {});
  assert.deepEqual(Object.keys(ping?.unavailable as object).sort(), ['code', 'tests']);
});

test('a scan with no tool reachable explains how to fix it', () => {
  const reply = talk([{ id: 1, op: 'scanProject', root: repo, tool: 'code' }], NOWHERE).get(1);
  assert.equal(reply?.ok, false);
  assert.match(reply?.error ?? '', /gradebook-code is not available/);
  assert.match(reply?.error ?? '', /pip install gradebook-code/);
  assert.match(reply?.error ?? '', /gradebook\.codePath/);
});

test('one missing tool does not take the other down with it', () => {
  const replies = talk(
    [
      { id: 1, op: 'scanProject', root: repo, tool: 'tests' },
      { id: 2, op: 'scanProject', root: repo, tool: 'code' },
      { id: 3, op: 'ping' },
    ],
    ['--code', path.join(repo, 'gradebook-code'), '--tests', '/nonexistent/gradebook_tests.py'],
  );
  assert.equal(replies.get(1)?.ok, false, 'the tests module was pointed at nothing');
  assert.equal(replies.get(2)?.ok, true, replies.get(2)?.error);
  assert.equal(replies.get(3)?.ok, true);
  assert.deepEqual(Object.keys(replies.get(3)?.unavailable as object), ['tests']);
});
