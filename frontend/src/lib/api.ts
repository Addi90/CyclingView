// Typed API client for the FastAPI backend.

export interface Bike {
  id: number;
  name: string;
  brand: string | null;
  model: string | null;
  default_sport: string | null;
}

export interface Ride {
  id: number;
  start_time: string;
  name: string | null;
  type: string | null;
  description: string | null;
  bike_id: number | null;
  bike_name: string | null;
  bike_brand: string | null;
  bike_model: string | null;
  filename: string | null;

  distance_m: number | null;
  elapsed_s: number | null;
  moving_s: number | null;

  avg_speed_ms: number | null;
  max_speed_ms: number | null;

  avg_hr: number | null;
  max_hr: number | null;

  avg_power: number | null;
  max_power: number | null;
  np_power: number | null;

  avg_cadence: number | null;
  max_cadence: number | null;

  elevation_gain_m: number | null;
  elevation_low_m: number | null;
  elevation_high_m: number | null;

  has_geo: number;
  has_power: number;
  has_hr: number;
  has_cadence: number;

  point_count: number;
  estimated_power: number;
}

export interface RidesPage {
  total: number;
  limit: number;
  offset: number;
  items: Ride[];
}

export type StreamField =
  | "power"
  | "heart_rate"
  | "speed"
  | "altitude"
  | "cadence"
  | "distance"
  | "temperature";

export interface StreamsResponse {
  activity_id: number;
  fields: StreamField[];
  count: number;
  t: number[];
  [key: string]: any;
}

export interface GeoResponse {
  type: "Feature";
  geometry: { type: "LineString"; coordinates: [number, number][] };
  properties: {
    activity_id: number;
    t: number[];
    streams: Partial<Record<StreamField, (number | null)[]>>;
  };
}

const BASE = "/api";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
  return res.json();
}

export interface OverallStats {
  totals: {
    rides: number;
    distance_m: number;
    moving_s: number;
    elapsed_s: number;
    elevation_gain_m: number;
    longest_distance_m: number | null;
    longest_moving_s: number | null;
  };
  longest_distance: { id: number; name: string | null; start_time: string; distance_m: number; moving_s: number } | null;
  longest_duration: { id: number; name: string | null; start_time: string; distance_m: number; moving_s: number } | null;
  per_year: Array<{
    year: string;
    rides: number;
    distance_m: number;
    moving_s: number;
    elevation_gain_m: number;
    longest_distance_m: number | null;
    longest_moving_s: number | null;
  }>;
  per_bike: Array<{
    bike_id: number;
    bike_name: string;
    rides: number;
    distance_m: number;
    moving_s: number;
    elevation_gain_m: number;
    first_ride: string | null;
    last_ride: string | null;
  }>;
  unassigned: { rides: number; distance_m: number; moving_s: number };
}

export interface PowerBest {
  window_s: number;
  watts: number | null;
}

export interface AllTimeBestEntry {
  activity_id: number;
  watts: number;
  start_time: string;
  name: string | null;
  estimated_power: number;
}

export const api = {
  bikes: () => get<Bike[]>("/bikes"),
  rides: (params: {
    bike_id?: number;
    date_from?: string;
    date_to?: string;
    limit?: number;
    offset?: number;
  } = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    });
    const s = qs.toString();
    return get<RidesPage>(`/rides${s ? `?${s}` : ""}`);
  },
  ride: (id: number | string) => get<Ride>(`/rides/${id}`),

  updateRide: async (
    id: number | string,
    patch: { name?: string | null; type?: string | null; description?: string | null; bike_id?: number | null },
  ): Promise<Ride> => {
    const res = await fetch(`${BASE}/rides/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
    return res.json();
  },

  deleteRide: async (id: number | string): Promise<{ deleted: number }> => {
    const res = await fetch(`${BASE}/rides/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
    return res.json();
  },
  streams: (id: number | string, fields: StreamField[], n_points = 0) =>
    get<StreamsResponse>(
      `/rides/${id}/streams?fields=${fields.join(",")}&n_points=${n_points}`,
    ),
  geo: (id: number | string) => get<GeoResponse>(`/rides/${id}/geo`),

  uploadRide: async (
    file: File,
    opts: { name?: string; bike_id?: number | null; activity_type?: string; description?: string } = {},
  ): Promise<{ activity_id: number }> => {
    const fd = new FormData();
    fd.append("file", file);
    if (opts.name) fd.append("name", opts.name);
    if (opts.bike_id != null) fd.append("bike_id", String(opts.bike_id));
    if (opts.activity_type) fd.append("activity_type", opts.activity_type);
    if (opts.description) fd.append("description", opts.description);
    const res = await fetch(`${BASE}/uploads`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
    return res.json();
  },

  ingestStrava: async (path?: string, force = false): Promise<{ ingested: number; skipped: number; failed: number; path: string }> => {
    const res = await fetch(`${BASE}/ingest/strava`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: path ?? null, force }),
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
    return res.json();
  },

  exportDataUrl: (): string => `${BASE}/export`,

  importData: async (file: File, replace = false): Promise<{ extracted: number; data_dir: string; replaced: boolean }> => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("replace", String(replace));
    const res = await fetch(`${BASE}/import`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
    return res.json();
  },

  stats: () => get<OverallStats>("/stats"),

  powerBestsForRide: (id: number | string) =>
    get<{ activity_id: number; windows_s: number[]; bests: PowerBest[] }>(`/power-bests/${id}`),

  powerBestsAllTime: (top_n = 5) =>
    get<{ windows_s: number[]; leaderboard: Record<string, AllTimeBestEntry[]> }>(
      `/power-bests?top_n=${top_n}`,
    ),

  powerBestsRecompute: async (force = false) => {
    const res = await fetch(`${BASE}/power-bests/recompute?force=${force}`, { method: "POST" });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
    return res.json() as Promise<{ processed: number; skipped: number; failed: number; total: number }>;
  },

  createBike: async (b: { name: string; brand?: string; model?: string; default_sport?: string }): Promise<Bike> => {
    const res = await fetch(`${BASE}/bikes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(b),
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
    return res.json();
  },

  deleteBike: async (id: number) => {
    const res = await fetch(`${BASE}/bikes/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
    return res.json();
  },
};
