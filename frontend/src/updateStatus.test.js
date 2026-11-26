import test from 'node:test';
import assert from 'node:assert/strict';
import { updateView } from './updateStatus.js';

test('updateView offers an update only for non-git installs with a newer release', () => {
  assert.equal(updateView({ available: true }).available, true);
  assert.equal(updateView({ available: true, git_checkout: true }).available, false);
  assert.equal(updateView({ available: false }).available, false);
  assert.equal(updateView(null).available, false);
});
