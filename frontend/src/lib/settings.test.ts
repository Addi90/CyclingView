import { describe, expect, it } from "vitest";
import {
  applyStreamFilter,
  buildPauseMask,
  kcalFromPower,
  mean,
  maxOf,
  minOf,
  normalizedPower,
} from "./settings";

describe("mean / maxOf / minOf", () => {
  it("skips nulls", () => {
    expect(mean([1, 2, null, 3])).toBe(2);
    expect(mean([null])).toBeNull();
    expect(maxOf([1, 9, 3])).toBe(9);
    expect(minOf([1, 9, 3])).toBe(1);
  });
});

describe("applyStreamFilter", () => {
  it("nulls out zero power when asked", () =>
    expect(applyStreamFilter([0, 100, null, 0], [], { excludeZero: true })).toEqual([null, 100, null, null]));
  it("nulls out paused samples via mask", () =>
    expect(applyStreamFilter([1, 2, 3], [0, 1, 2], { pauseMask: [false, true, false] })).toEqual([1, null, 3]));
});

describe("buildPauseMask", () => {
  it("marks stops longer than the threshold", () => {
    const t = Array.from({ length: 10 }, (_, i) => i); // 1s cadence, 9s stop
    expect(buildPauseMask([0, 0, 0, 0, 0, 0, 0, 0, 0, 0], t, 5, 0.5).every((m) => m)).toBe(true);
  });
  it("ignores stops shorter than the threshold", () => {
    const t = [0, 1, 2]; // 2s stop
    expect(buildPauseMask([0, 0, 0], t, 5, 0.5).every((m) => !m)).toBe(true);
  });
});

describe("normalizedPower", () => {
  it("constant power returns that power", () => {
    const t = Array.from({ length: 60 }, (_, i) => i);
    const power = Array.from({ length: 60 }, () => 200);
    expect(normalizedPower(power, t)).toBeCloseTo(200, 0);
  });
  it("empty input is null", () => expect(normalizedPower([], [])).toBeNull());
});

describe("kcalFromPower", () => {
  it("200 W for one hour ≈ 717 kcal at η=0.24", () => {
    const t = Array.from({ length: 3600 }, (_, i) => i);
    const power = Array.from({ length: 3600 }, () => 200);
    expect(kcalFromPower(power, t)).toBeCloseTo(717, 1);
  });
  it("length mismatch is null", () => expect(kcalFromPower([200], [0, 1])).toBeNull());
});
