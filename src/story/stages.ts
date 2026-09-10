/**
 * Scroll-progress ranges for the nine story stages.
 *
 * Each stage owns a slice of [0, 1]. Nothing outside this file may invent a
 * threshold — beats, the network, the rail and the lens all read from here, so
 * retiming the story is a single edit and the pieces cannot drift apart.
 */
export const STAGES = {
  arrival: [0.0, 0.085],
  horizon: [0.085, 0.175],
  breach: [0.175, 0.3],
  blast: [0.3, 0.425],
  candidates: [0.425, 0.53],
  intervention: [0.53, 0.632],
  realityLens: [0.632, 0.762],
  recovery: [0.762, 0.918],
  closing: [0.918, 1.0],
} as const;

export type StageKey = keyof typeof STAGES;

export const STAGE_ORDER: StageKey[] = [
  'arrival',
  'horizon',
  'breach',
  'blast',
  'candidates',
  'intervention',
  'realityLens',
  'recovery',
  'closing',
];

/**
 * The moment a human confirms the field evidence. Deliberately late inside the
 * realityLens stage so the "awaiting confirmation" state is held long enough to
 * be read — the pause is the point.
 */
export const CONFIRM_AT = 0.717;

/** Sub-beats inside the recovery stage. */
export const RECOVERY = {
  replanDraw: [0.766, 0.826],
  verify: [0.83, 0.914],
} as const;

export const clamp = (v: number, lo = 0, hi = 1) => (v < lo ? lo : v > hi ? hi : v);

/** Linear position of `p` inside [a, b], clamped to 0–1. */
export const within = (p: number, a: number, b: number) => clamp((p - a) / (b - a || 1e-6));

/** Smoothstep easing between two edges. */
export const smoothstep = (a: number, b: number, v: number) => {
  const t = clamp((v - a) / (b - a || 1e-6));
  return t * t * (3 - 2 * t);
};

/**
 * Opacity for a copy block that owns [a, b], fading in and out at its edges.
 * Returns 0 well outside the range so hidden beats stay non-interactive.
 */
export const beatOpacity = (p: number, a: number, b: number, fadeIn = 0.14, fadeOut = 0.14) => {
  const t = (p - a) / (b - a || 1e-6);
  if (t < -0.03 || t > 1.03) return 0;
  // A zero-length fade means "already there" — without this the first beat
  // would be invisible at progress 0 and the page would open blank.
  const rising = fadeIn <= 0 ? 1 : smoothstep(0, fadeIn, t);
  const falling = fadeOut <= 0 ? 1 : 1 - smoothstep(1 - fadeOut, 1, t);
  return Math.min(rising, falling);
};

export const stageOpacity = (p: number, key: StageKey, fadeIn?: number, fadeOut?: number) =>
  beatOpacity(p, STAGES[key][0], STAGES[key][1], fadeIn, fadeOut);
