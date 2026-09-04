import { describe, expect, it } from "vitest";
import { fmtPower, fmtWindow } from "./power-format";

describe("fmtWindow", () => {
  it("seconds, minutes, hours", () => {
    expect(fmtWindow(5)).toBe("5 s");
    expect(fmtWindow(120)).toBe("2 min");
    expect(fmtWindow(3600)).toBe("1 h");
  });
});

describe("fmtPower", () => {
  it("watts, rounded", () => expect(fmtPower(250, 75, "W")).toBe("250 W"));
  it("watts per kg, two decimals", () => expect(fmtPower(250, 75, "W/kg")).toBe("3.33 W/kg"));
  it("W/kg without weight falls back to en-dash", () => expect(fmtPower(250, 0, "W/kg")).toBe("–"));
  it("null falls back to en-dash", () => expect(fmtPower(null, 75, "W")).toBe("–"));
});
