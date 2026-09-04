import { describe, expect, it } from "vitest";
import { fmtDuration, fmtKm, fmtKmh, fmtNum } from "./format";

describe("fmtDuration", () => {
  it("returns en-dash for null", () => expect(fmtDuration(null)).toBe("–"));
  it("formats under an hour as m:ss", () => expect(fmtDuration(125)).toBe("2:05"));
  it("formats over an hour as h:mm:ss", () => expect(fmtDuration(3661)).toBe("1:01:01"));
});

describe("fmtKm / fmtKmh / fmtNum", () => {
  it("converts meters to km", () => expect(fmtKm(12300)).toBe("12.30 km"));
  it("returns en-dash for null", () => {
    expect(fmtKm(null)).toBe("–");
    expect(fmtKmh(null)).toBe("–");
    expect(fmtNum(null)).toBe("–");
  });
  it("converts m/s to km/h", () => expect(fmtKmh(10)).toBe("36.0 km/h"));
  it("applies digits and suffix", () => expect(fmtNum(1.234, 1, " W")).toBe("1.2 W"));
});
