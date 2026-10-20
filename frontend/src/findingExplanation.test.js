import assert from 'node:assert/strict';
import { test } from 'node:test';
import { unknownExplanation } from './findingExplanation.js';

test('blank legacy reason with invalid links is explained as a tool verification problem', () => {
  const info = unknownExplanation({ status: 'UNKNOWN', reason: '', verification: {
    valid: false, errors: ['claim[1]:invalid_evidence_indices', 'claim[1]:invalid_path_evidence'],
  } });
  assert.equal(info.category, 'verification');
  assert.match(info.description, /liên kết/);
});

test('budget exhaustion is distinguished from insufficient code evidence', () => {
  assert.equal(unknownExplanation({ status: 'UNKNOWN', reason: 'tool_budget' }).category, 'budget');
  assert.equal(unknownExplanation({ status: 'UNKNOWN', verification: { valid: true } }).category, 'coverage');
  assert.equal(unknownExplanation({ status: 'PASS' }), null);
});
