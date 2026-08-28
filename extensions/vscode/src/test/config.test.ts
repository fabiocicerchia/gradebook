import * as assert from 'node:assert/strict';
import { test } from 'node:test';
import { modulePath, readConfig, withWorkspaceDefaults } from '../config';
import { Store } from '../store';
import { Report } from '../types';
import { configuration } from './vscode-shim';

test('defaults run both tools on save', () => {
  const config = readConfig();
  assert.deepEqual(config.tools, ['code', 'tests']);
  assert.equal(config.run, 'onSave');
  assert.equal(config.debounceMs, 400);
  assert.equal(config.enable, true);
});

test('each tool reads its own module path override', () => {
  configuration.gradebook = { codePath: '/checkout/gradebook-code', testsPath: '' };
  const config = readConfig();
  assert.equal(modulePath(config, 'code'), '/checkout/gradebook-code');
  assert.equal(modulePath(config, 'tests'), '');
  delete configuration.gradebook;
});

test('the store keeps one report per tool and notifies on change', () => {
  const store = new Store();
  let calls = 0;
  store.onChange(() => (calls += 1));
  const report = { tool: 'gradebook-code', score: 1 } as unknown as Report;
  store.set('code', report);
  store.set('tests', report);
  assert.equal(calls, 2);
  assert.equal(store.entries().length, 2);
  store.clear();
  assert.equal(store.get('code'), undefined);
});

// --- module resolution ------------------------------------------------------
//
// The bug these cover: installed from a VSIX, the server sits under the
// extensions directory, so the path it derives from its own location points at
// nothing. With both packages uninstalled — which is every fresh clone, since
// neither is on PyPI yet — "Scan Workspace" then found no tool and said
// nothing. Opening the gradebook repo has to work on its own.

test('an open checkout supplies the module paths', () => {
  const onDisk = ['/repo/gradebook-code/gradebook_code.py', '/repo/gradebook-tests/gradebook_tests.py'];
  const resolved = withWorkspaceDefaults(readConfig(), '/repo', (f) => onDisk.includes(f));
  assert.equal(modulePath(resolved, 'code'), '/repo/gradebook-code/gradebook_code.py');
  assert.equal(modulePath(resolved, 'tests'), '/repo/gradebook-tests/gradebook_tests.py');
});

test('an explicit setting beats the checkout', () => {
  configuration.gradebook = { codePath: '/elsewhere/gradebook_code.py' };
  const resolved = withWorkspaceDefaults(readConfig(), '/repo', () => true);
  assert.equal(modulePath(resolved, 'code'), '/elsewhere/gradebook_code.py');
  delete configuration.gradebook;
});

test('a workspace that is not a gradebook checkout is left alone', () => {
  const resolved = withWorkspaceDefaults(readConfig(), '/some/app', () => false);
  assert.equal(modulePath(resolved, 'code'), '');
  assert.equal(modulePath(resolved, 'tests'), '');
});

test('one tool present does not invent a path for the other', () => {
  const resolved = withWorkspaceDefaults(readConfig(), '/repo', (f) => f.includes('gradebook-code'));
  assert.equal(modulePath(resolved, 'code'), '/repo/gradebook-code/gradebook_code.py');
  assert.equal(modulePath(resolved, 'tests'), '');
});

test('with no folder open there is nothing to resolve against', () => {
  const resolved = withWorkspaceDefaults(readConfig(), undefined, () => true);
  assert.equal(modulePath(resolved, 'code'), '');
});
