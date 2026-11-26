import test from 'node:test';
import assert from 'node:assert/strict';
import { pageFromHash } from './pages.js';

test('pageFromHash reads known pages and falls back to audit', () => {
  assert.equal(pageFromHash('#/setup'), 'setup');
  assert.equal(pageFromHash('#results'), 'results');
  assert.equal(pageFromHash(''), 'audit');
  assert.equal(pageFromHash('#/unknown'), 'audit');
  assert.equal(pageFromHash('#overview'), 'audit');
});
