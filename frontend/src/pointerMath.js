/** Exponential smoothing that stays frame-rate independent. */
export function ease(current, target, dt, rate = 9) {
  return current + (target - current) * (1 - Math.exp(-rate * dt));
}
