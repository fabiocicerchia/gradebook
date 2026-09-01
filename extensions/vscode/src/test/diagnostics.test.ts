import * as assert from 'node:assert/strict';
import { test } from 'node:test';
import { byFile, isAnchored, partition, severityOf } from '../diagnostics';
import { Finding } from '../types';
import { vscode } from './vscode-shim';

const finding = (over: Partial<Finding> = {}): Finding => ({
  file: 'src/a.py',
  line: 12,
  kind: 'complex-function',
  message: 'too much',
  severity: 'high',
  ...over,
});

const onDisk = (files: string[]) => (file: string) => files.includes(file);

test('a finding on a real file at a real line anchors', () => {
  assert.equal(isAnchored(finding(), onDisk(['src/a.py'])), true);
});

test('line 0 is workspace-level even when the file exists', () => {
  assert.equal(isAnchored(finding({ line: 0 }), onDisk(['src/a.py'])), false);
});

test('a dependency cycle never squiggles a guessed path', () => {
  const cycle = finding({ file: 'a -> b -> a', line: 0, kind: 'dependency-cycle' });
  const split = partition([cycle], [], onDisk([]));
  assert.deepEqual(split.anchored, []);
  assert.deepEqual(split.workspace, [cycle]);
});

test('a finding on a file that is not on disk goes to the report view', () => {
  const split = partition([finding({ file: 'gone.py' })], [], onDisk([]));
  assert.equal(split.anchored.length, 0);
  assert.equal(split.workspace.length, 1);
});

test('excluded prefixes are dropped entirely', () => {
  const split = partition([finding({ file: 'vendor/a.py' })], ['vendor/'], onDisk(['vendor/a.py']));
  assert.equal(split.anchored.length, 0);
  assert.equal(split.workspace.length, 0);
});

test('severity maps high/medium/low onto the editor scale', () => {
  assert.equal(severityOf(finding({ severity: 'high' })), vscode.DiagnosticSeverity.Error);
  assert.equal(severityOf(finding({ severity: 'medium' })), vscode.DiagnosticSeverity.Warning);
  assert.equal(severityOf(finding({ severity: 'low' })), vscode.DiagnosticSeverity.Information);
});

test('findings group by absolute path', () => {
  const grouped = byFile('/repo', [finding(), finding({ line: 20 }), finding({ file: 'b.py' })]);
  assert.equal(grouped.size, 2);
  assert.equal(grouped.get('/repo/src/a.py')?.length, 2);
});
