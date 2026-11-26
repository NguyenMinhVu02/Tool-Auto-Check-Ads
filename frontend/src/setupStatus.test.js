import test from 'node:test';
import assert from 'node:assert/strict';
import { setupSummary, toolStatus } from './setupStatus.js';

test('toolStatus marks missing required, optional and login-needed tools', () => {
  assert.equal(toolStatus({ installed: false, required: true }), 'missing');
  assert.equal(toolStatus({ installed: false, required: false }), 'optional');
  assert.equal(toolStatus({ installed: true, ai: true, logged_in: false }), 'login');
  assert.equal(toolStatus({ installed: true, ai: true, logged_in: null }), 'ok');
});

test('setupSummary installs Claude with the required tools when no AI is present', () => {
  const summary = setupSummary({ ready: false, items: [
    { id: 'java', required: true, installed: false },
    { id: 'jadx', required: true, installed: true },
    { id: 'claude', ai: true, installed: false },
    { id: 'codex', ai: true, installed: false },
  ] });
  assert.deepEqual(summary.installAll, ['java', 'claude']);
  assert.equal(summary.ready, false);
});

test('setupSummary skips AI install when one AI CLI exists', () => {
  const summary = setupSummary({ ready: true, items: [
    { id: 'java', required: true, installed: true },
    { id: 'codex', ai: true, installed: true, logged_in: true },
    { id: 'claude', ai: true, installed: false },
  ] });
  assert.deepEqual(summary.installAll, []);
  assert.equal(summary.needsLoginHint, false);
});
