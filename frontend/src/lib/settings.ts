// Persistent user settings, backed by localStorage.
import { writable } from "svelte/store";

export interface AppSettings {
  /** Drop samples where power == 0 from power chart + averages (coasting filter). */
  excludeZeroPower: boolean;
  /** Drop samples where cadence == 0 from cadence chart + averages. */
  excludeZeroCadence: boolean;
  /** Hide ride pauses (continuous speed≈0 longer than threshold) from charts. */
  hidePauses: boolean;
  /** Pause threshold in seconds. */
  pauseThresholdS: number;
  /** Speed below this (m/s) counts as paused. */
  pauseSpeedMs: number;
  /** Unit system for display. */
  units: "metric" | "imperial";
  /** Color theme. */
  theme: "dark" | "light" | "system";
  /** Body weight in kg, used for W/kg display. */
  weightKg: number;
  /** Display unit for power values. */
  powerUnit: "W" | "W/kg";
  /** Age in years (used for HR-based calorie estimation). */
  ageYears: number;
  /** Biological sex (used for HR-based calorie estimation). */
  sex: "male" | "female";
  /** Maximum heart rate in bpm (used for HR zone calculation). Null = disabled. */
  maxHR: number | null;
}

const DEFAULTS: AppSettings = {
  excludeZeroPower: true,
  excludeZeroCadence: true,
  hidePauses: false,
  pauseThresholdS: 5,
  pauseSpeedMs: 0.5,
  units: "metric",
  theme: "dark",
  weightKg: 75,
  powerUnit: "W",
  ageYears: 35,
  sex: "male",
  maxHR: null,
};

const KEY = "cycling-view-settings-v1";

function load(): AppSettings {
  if (typeof localStorage === "undefined") return { ...DEFAULTS };
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { ...DEFAULTS };
    return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULTS };
  }
}

export const settings = writable<AppSettings>(load());

settings.subscribe((s) => {
  if (typeof localStorage !== "undefined") {
    try {
      localStorage.setItem(KEY, JSON.stringify(s));
    } catch {
      /* ignore */
    }
  }
});

/** Apply zero/pause filtering to a numeric stream, returning a new array with nulls. */
export function applyStreamFilter(
  values: (number | null)[],
  t: number[],
  opts: {
    excludeZero?: boolean;
    pauseMask?: boolean[]; // true = paused → null out
  } = {},
): (number | null)[] {
  const { excludeZero = false, pauseMask } = opts;
  const out: (number | null)[] = new Array(values.length);
  for (let i = 0; i < values.length; i++) {
    const v = values[i];
    if (v == null) {
      out[i] = null;
    } else if (excludeZero && v === 0) {
      out[i] = null;
    } else if (pauseMask && pauseMask[i]) {
      out[i] = null;
    } else {
      out[i] = v;
    }
  }
  return out;
}

/**
 * Build a boolean mask marking samples that belong to a ride pause.
 * A pause = consecutive samples with speed below `speedMs` lasting `>= thresholdS` seconds.
 */
export function buildPauseMask(
  speedMs: (number | null)[],
  t: number[],
  thresholdS: number,
  speedMs0: number,
): boolean[] {
  const n = speedMs.length;
  const mask = new Array<boolean>(n).fill(false);
  let i = 0;
  while (i < n) {
    const v = speedMs[i];
    if (v == null || v <= speedMs0) {
      let j = i;
      while (j < n) {
        const vj = speedMs[j];
        if (vj == null || vj <= speedMs0) j++;
        else break;
      }
      const dur = (t[j - 1] ?? t[i]) - t[i];
      if (dur >= thresholdS) {
        for (let k = i; k < j; k++) mask[k] = true;
      }
      i = j;
    } else {
      i++;
    }
  }
  return mask;
}

/** Compute mean of non-null values. */
export function mean(values: (number | null)[]): number | null {
  let sum = 0;
  let n = 0;
  for (const v of values) {
    if (v != null) {
      sum += v;
      n++;
    }
  }
  return n ? sum / n : null;
}

export function maxOf(values: (number | null)[]): number | null {
  let m: number | null = null;
  for (const v of values) {
    if (v != null && (m === null || v > m)) m = v;
  }
  return m;
}

export function minOf(values: (number | null)[]): number | null {
  let m: number | null = null;
  for (const v of values) {
    if (v != null && (m === null || v < m)) m = v;
  }
  return m;
}

/**
 * Normalized Power = ⁴√( mean( rolling30s_avg(power)⁴ ) ).
 * Operates on samples with timestamps in seconds.
 */
export function normalizedPower(power: (number | null)[], t: number[]): number | null {
  if (!power.length) return null;
  // 30s rolling average via a simple deque of (time, value) within 30s window.
  const window = 30;
  let sum = 0;
  let count = 0;
  let head = 0;
  let sum4 = 0;
  let n4 = 0;
  for (let i = 0; i < power.length; i++) {
    const v = power[i];
    if (v != null) {
      sum += v;
      count++;
    }
    while (head < i && t[i] - t[head] > window) {
      const vh = power[head];
      if (vh != null) {
        sum -= vh;
        count--;
      }
      head++;
    }
    if (count > 0 && t[i] - t[head] >= window - 1) {
      const avg = sum / count;
      sum4 += avg ** 4;
      n4++;
    }
  }
  if (!n4) return null;
  return Math.pow(sum4 / n4, 0.25);
}

/**
 * Estimate energy expenditure (kcal) from a power stream.
 * Mechanical work W = ∫P dt (kJ). Total metabolic energy E = W / efficiency.
 * kcal = E / 4.184. Default η = 0.24 (gross efficiency for trained cyclists),
 * which yields the well-known shortcut: kcal ≈ kJ of work.
 */
export function kcalFromPower(
  power: (number | null)[],
  t: number[],
  efficiency = 0.24,
): number | null {
  if (!power.length || power.length !== t.length) return null;
  let workKJ = 0;
  let any = false;
  for (let i = 0; i < power.length; i++) {
    const p = power[i];
    if (p == null || p < 0) continue;
    const prev = i > 0 ? t[i] - t[i - 1] : 0;
    const next = i < power.length - 1 ? t[i + 1] - t[i] : 0;
    let dt = (prev + next) / 2;
    if (i === 0) dt = next;
    if (i === power.length - 1) dt = prev;
    if (!isFinite(dt) || dt <= 0 || dt > 30) continue;
    workKJ += (p * dt) / 1000;
    any = true;
  }
  if (!any) return null;
  return workKJ / (efficiency * 4.184);
}

/**
 * Estimate energy expenditure (kcal) from heart rate using the Keytel et al. (2005) formula.
 * kcal/min (male)   = (-55.0969 + 0.6309*HR + 0.1988*W + 0.2017*A) / 4.184
 * kcal/min (female) = (-20.4022 + 0.4472*HR - 0.1263*W + 0.0740*A) / 4.184
 */
export function kcalFromHR(
  hr: (number | null)[],
  t: number[],
  weightKg: number,
  ageYears: number,
  sex: "male" | "female",
): number | null {
  if (!hr.length || hr.length !== t.length || !weightKg) return null;
  let kcal = 0;
  let any = false;
  for (let i = 0; i < hr.length; i++) {
    const h = hr[i];
    if (h == null || h < 30) continue;
    const prev = i > 0 ? t[i] - t[i - 1] : 0;
    const next = i < hr.length - 1 ? t[i + 1] - t[i] : 0;
    let dt = (prev + next) / 2;
    if (i === 0) dt = next;
    if (i === hr.length - 1) dt = prev;
    if (!isFinite(dt) || dt <= 0 || dt > 30) continue;
    const kcalPerMin =
      sex === "female"
        ? (-20.4022 + 0.4472 * h - 0.1263 * weightKg + 0.074 * ageYears) / 4.184
        : (-55.0969 + 0.6309 * h + 0.1988 * weightKg + 0.2017 * ageYears) / 4.184;
    if (kcalPerMin > 0) {
      kcal += (kcalPerMin * dt) / 60;
      any = true;
    }
  }
  return any ? kcal : null;
}
