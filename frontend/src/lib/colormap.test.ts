import { describe, expect, it } from "vitest";
import { rampColor, robustRange } from "./colormap";

describe("rampColor", () => {
  it("clamps below zero to the first stop", () => expect(rampColor(-1)).toBe("rgb(48, 18, 59)"));
  it("clamps above one to the last stop", () => expect(rampColor(2)).toBe("rgb(122, 4, 3)"));
  it("hits exact stops", () => expect(rampColor(0.5)).toBe("rgb(97, 220, 102)"));
});

describe("robustRange", () => {
  it("empty input yields [0, 1]", () => expect(robustRange([])).toEqual([0, 1]));
  it("constant input yields [x, x+1]", () => expect(robustRange([5, 5, 5])).toEqual([5, 6]));
  it("trims outliers via percentiles", () => {
    const values = Array.from({ length: 100 }, (_, i) => i);
    values.push(1000);
    expect(robustRange(values)).toEqual([2, 98]);
  });
});
