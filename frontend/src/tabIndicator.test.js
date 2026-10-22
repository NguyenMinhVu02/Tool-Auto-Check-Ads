import assert from 'node:assert/strict';
import test from 'node:test';
import { tabTitle } from './tabIndicator.js';

test('running title spins through frames and carries the progress label', () => {
  assert.notEqual(tabTitle('running', '3/7', 0), tabTitle('running', '3/7', 1));
  assert.match(tabTitle('running', '3/7', 4), /Đang kiểm tra 3\/7/);
});

test('finished, waiting, error and idle titles are static and distinct', () => {
  const titles = ['done', 'waiting', 'error', 'idle'].map((state) => tabTitle(state, '', 3));
  assert.equal(new Set(titles).size, 4);
  assert.equal(tabTitle('done', '', 0), tabTitle('done', '', 9));
});
