import * as assert from 'node:assert/strict';
import { test } from 'node:test';
import { frame } from '../engine';

test('whole lines come out, the tail is kept', () => {
  const first = frame('', '{"id":1}\n{"id":2}\n{"id":');
  assert.deepEqual(first.lines, ['{"id":1}', '{"id":2}']);
  assert.equal(first.rest, '{"id":');
  const second = frame(first.rest, '3}\n');
  assert.deepEqual(second.lines, ['{"id":3}']);
  assert.equal(second.rest, '');
});

test('a response split across chunks is not parsed early', () => {
  const first = frame('', '{"id":1,"ok":tr');
  assert.deepEqual(first.lines, []);
  assert.deepEqual(frame(first.rest, 'ue}\n').lines, ['{"id":1,"ok":true}']);
});

test('blank lines are ignored', () => {
  assert.deepEqual(frame('', '\n\n{"id":1}\n').lines, ['{"id":1}']);
});
