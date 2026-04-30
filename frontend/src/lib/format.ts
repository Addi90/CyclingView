export function fmtDuration(seconds: number | null): string {
  if (seconds == null) return "–";
  const s = Math.round(seconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  return `${m}:${String(sec).padStart(2, "0")}`;
}

export function fmtKm(meters: number | null, digits = 2): string {
  if (meters == null) return "–";
  return `${(meters / 1000).toFixed(digits)} km`;
}

export function fmtKmh(ms: number | null, digits = 1): string {
  if (ms == null) return "–";
  return `${(ms * 3.6).toFixed(digits)} km/h`;
}

export function fmtNum(x: number | null, digits = 0, suffix = ""): string {
  if (x == null) return "–";
  return `${x.toFixed(digits)}${suffix}`;
}

export function fmtDate(iso: string | null): string {
  if (!iso) return "–";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export function fmtDateShort(iso: string | null): string {
  if (!iso) return "–";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString();
}
