import assert from 'node:assert/strict';
import test from 'node:test';
import { ease } from './pointerMath.js';

test('ease moves toward the target without overshooting and is frame-rate independent', () => {
  const oneStep = ease(0, 10, 0.032);
  const twoSteps = ease(ease(0, 10, 0.016), 10, 0.016);
  assert.ok(oneStep > 0 && oneStep < 10);
  assert.ok(Math.abs(oneStep - twoSteps) < 1e-9);
  assert.equal(ease(5, 5, 0.016), 5);
});
