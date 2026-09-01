// activate() itself, and the Scan Workspace command it registers.
//
// Nothing here covered the wiring before: every other test imports a module
// directly. An exception thrown during activate() disables the whole
// extension, and VS Code reports that only in the developer console — from the
// outside it looks exactly like "the command does nothing", which is the bug
// this file exists to catch.

import * as assert from 'node:assert/strict';
import * as path from 'node:path';
import { after, test } from 'node:test';

import { activate, deactivate } from '../extension';
import { collections, commands, configuration, contexts, messages, trees, vscode } from './vscode-shim';

const repo = path.join(__dirname, '..', '..', '..', '..');

interface FakeContext {
  subscriptions: Array<{ dispose: () => void }>;
  asAbsolutePath: (relative: string) => string;
}

/** The slice of ExtensionContext the extension actually touches. */
function context(): FakeContext {
  return {
    subscriptions: [],
    asAbsolutePath: (relative: string) => path.join(__dirname, '..', '..', relative),
  };
}

/** activate() wants the real ExtensionContext; the fake covers what it uses. */
const start = (ctx: FakeContext) => activate(ctx as unknown as Parameters<typeof activate>[0]);

function openWorkspace(root: string | undefined): void {
  vscode.workspace.workspaceFolders = root ? [{ uri: { fsPath: root } }] : undefined;
}

after(() => {
  deactivate();
  openWorkspace(undefined);
});

test('activate wires up without throwing, with no folder open', () => {
  openWorkspace(undefined);
  configuration.gradebook = { scanProjectOnStartup: false };
  const ctx = context();
  assert.doesNotThrow(() => start(ctx));
  assert.ok(ctx.subscriptions.length > 0, 'nothing was registered for disposal');
  deactivate();
});

test('every command the manifest promises is registered', () => {
  openWorkspace(undefined);
  configuration.gradebook = { scanProjectOnStartup: false };
  start(context());
  const manifest = require('../../package.json') as {
    contributes: { commands: Array<{ command: string }> };
  };
  for (const { command } of manifest.contributes.commands) {
    assert.ok(commands.has(command), `manifest promises ${command}, activate never registered it`);
  }
  deactivate();
});

test('Scan Workspace scores the open folder and fills the panel', async () => {
  openWorkspace(repo);
  // Point at this checkout explicitly: whether the packages happen to be
  // installed on the machine running the tests is not what this is about.
  configuration.gradebook = {
    scanProjectOnStartup: false,
    codePath: path.join(repo, 'gradebook-code'),
    testsPath: path.join(repo, 'gradebook-tests'),
  };
  messages.length = 0;
  start(context());

  const scan = commands.get('gradebook.scanWorkspace');
  assert.ok(scan, 'gradebook.scanWorkspace is not registered');
  await scan();

  assert.deepEqual(messages, [], `the scan reported: ${messages.join('; ')}`);
  const published = collections.flatMap((c) => [...c.entries.values()].flat());
  assert.ok(published.length > 0, 'no diagnostics were published for this repo');
  deactivate();
});

test('a broken configuration is reported, not swallowed', async () => {
  openWorkspace(repo);
  configuration.gradebook = {
    scanProjectOnStartup: false,
    tools: ['code'],
    codePath: '/nonexistent/gradebook_code.py',
  };
  messages.length = 0;
  start(context());

  await commands.get('gradebook.scanWorkspace')!();

  // The original bug: this went to an output channel nobody had open, so a
  // misconfigured extension was indistinguishable from a broken command.
  assert.equal(messages.length, 1, 'the user was told nothing');
  assert.match(messages[0], /gradebook-code is not available/);
  deactivate();
});

test('the same failure is not repeated on every save', async () => {
  openWorkspace(repo);
  configuration.gradebook = {
    scanProjectOnStartup: false,
    tools: ['code'],
    codePath: '/nonexistent/gradebook_code.py',
  };
  messages.length = 0;
  start(context());

  const scan = commands.get('gradebook.scanWorkspace')!;
  await scan();
  await scan();
  await scan();
  assert.equal(messages.length, 1, 'the same complaint was shown more than once');
  deactivate();
});

test('the Findings panel fills with the flags a scan produced', async () => {
  openWorkspace(repo);
  configuration.gradebook = {
    scanProjectOnStartup: false,
    codePath: path.join(repo, 'gradebook-code'),
    testsPath: path.join(repo, 'gradebook-tests'),
  };
  start(context());

  const tree = trees.get('gradebook.findings');
  assert.ok(tree, 'the Findings view was never created');
  assert.deepEqual(tree.getChildren(), [], 'the tree should start empty');

  await commands.get('gradebook.scanWorkspace')!();

  const groups = tree.getChildren();
  assert.ok(groups.length > 0, 'the panel is empty after a scan that found things');
  const leaves = groups.flatMap((g: unknown) => tree.getChildren(g));
  assert.ok(leaves.length >= groups.length, 'groups with no children');
  // A leaf is a finding, and every finding must be able to name itself.
  for (const leaf of leaves as Array<{ message: string; kind: string }>) {
    assert.ok(leaf.message, 'a finding reached the panel with no message');
    assert.ok(leaf.kind, 'a finding reached the panel with no kind');
  }
  deactivate();
});

test('a clean workspace reads as scanned-and-clean, not as never scanned', async () => {
  // Reproduces the report from a small tidy project: one source file, a few
  // simple functions, no git history — a real scan that finds nothing. The
  // panel used to fall back to "No scan yet", which is indistinguishable from
  // a broken extension.
  const fs = require('node:fs') as typeof import('node:fs');
  const os = require('node:os') as typeof import('node:os');
  const clean = fs.mkdtempSync(path.join(os.tmpdir(), 'gradebook-clean-'));
  fs.writeFileSync(
    path.join(clean, 'app.py'),
    'def add(a, b):\n    return a + b\n\n\ndef greet(name):\n    return f"hi {name}"\n',
  );

  openWorkspace(clean);
  configuration.gradebook = {
    scanProjectOnStartup: false,
    tools: ['code'],
    codePath: path.join(repo, 'gradebook-code'),
  };
  messages.length = 0;
  contexts.clear();
  start(context());

  await commands.get('gradebook.scanWorkspace')!();

  assert.deepEqual(messages, [], `a clean scan should not complain: ${messages.join('; ')}`);
  assert.equal(contexts.get('gradebook.scanned'), true, 'the scan did happen');
  assert.equal(contexts.get('gradebook.hasFindings'), false, 'the project really is clean');
  assert.deepEqual(trees.get('gradebook.findings')!.getChildren(), []);
  deactivate();
  fs.rmSync(clean, { recursive: true, force: true });
});

test('before any scan, the panel says exactly that', () => {
  openWorkspace(repo);
  configuration.gradebook = { scanProjectOnStartup: false };
  contexts.clear();
  start(context());
  assert.notEqual(contexts.get('gradebook.scanned'), true);
  deactivate();
});
