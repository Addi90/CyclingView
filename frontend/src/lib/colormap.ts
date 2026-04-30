// Color ramps and helpers for color-coding map line segments by a stream value.

export type ColorStop = [number, [number, number, number]];

// Turbo (Google) colormap stops — perceptually uniform-ish and very legible on dark.
export const TURBO: ColorStop[] = [
  [0.00, [48, 18, 59]],
  [0.13, [70, 50, 126]],
  [0.25, [54, 117, 173]],
  [0.38, [40, 174, 162]],
  [0.50, [97, 220, 102]],
  [0.63, [194, 224, 65]],
  [0.75, [253, 175, 60]],
  [0.88, [240, 86, 32]],
  [1.00, [122, 4, 3]],
];

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

export function rampColor(t: number, stops: ColorStop[] = TURBO): string {
  const x = Math.max(0, Math.min(1, t));
  for (let i = 0; i < stops.length - 1; i++) {
    const [s0, c0] = stops[i];
    const [s1, c1] = stops[i + 1];
    if (x >= s0 && x <= s1) {
      const f = (x - s0) / Math.max(1e-9, s1 - s0);
      const r = Math.round(lerp(c0[0], c1[0], f));
      const g = Math.round(lerp(c0[1], c1[1], f));
      const b = Math.round(lerp(c0[2], c1[2], f));
      return `rgb(${r}, ${g}, ${b})`;
    }
  }
  const [, c] = stops[stops.length - 1];
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

/** Robust min/max using percentiles to ignore outliers. */
export function robustRange(values: (number | null)[], lowQ = 0.02, highQ = 0.98): [number, number] {
  const clean = values.filter((v): v is number => v != null && Number.isFinite(v));
  if (clean.length === 0) return [0, 1];
  const sorted = [...clean].sort((a, b) => a - b);
  const lo = sorted[Math.floor(sorted.length * lowQ)];
  const hi = sorted[Math.floor(sorted.length * highQ)] ?? sorted[sorted.length - 1];
  if (lo === hi) return [lo, lo + 1];
  return [lo, hi];
}
