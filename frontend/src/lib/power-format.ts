/** Format a power window duration in seconds as "5s", "1m", "20m", "1h", "4h". */
export function fmtWindow(s: number): string {
  if (s < 60) return `${s} s`;
  if (s < 3600) return `${Math.round(s / 60)} min`;
  return `${s / 3600} h`;
}

/** Format watts or W/kg depending on settings. */
export function fmtPower(watts: number | null, weightKg: number, unit: "W" | "W/kg"): string {
  if (watts == null || !Number.isFinite(watts)) return "–";
  if (unit === "W/kg") {
    if (!weightKg || weightKg <= 0) return "–";
    return `${(watts / weightKg).toFixed(2)} W/kg`;
  }
  return `${Math.round(watts)} W`;
}
