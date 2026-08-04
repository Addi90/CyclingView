<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import maplibregl, { type Map as MapLibreMap, type LngLatBoundsLike } from "maplibre-gl";
  import "maplibre-gl/dist/maplibre-gl.css";
  import { api, type GeoResponse, type StreamField } from "./api";
  import { rampColor, robustRange } from "./colormap";
  import { hoverTime, selectionRange } from "./hover";
  import { t } from "./i18n";

  export let activityId: number | string;
  export let hasGeo = true;

  type Mode = "none" | StreamField;
  $: MODE_LABEL = {
    none: $t("map.mode.none"),
    power: $t("ride.card.power"),
    heart_rate: $t("ride.card.hr"),
    speed: $t("ride.chart.speed"),
    altitude: $t("ride.chart.elevation"),
    cadence: $t("ride.card.cadence"),
    distance: $t("ride.card.distance"),
    temperature: $t("ride.card.temperature"),
  } as Record<Mode, string>;
  const UNIT: Partial<Record<Mode, string>> = {
    power: "W",
    heart_rate: "bpm",
    speed: "km/h",
    altitude: "m",
    cadence: "rpm",
    temperature: "°C",
  };

  let mapEl: HTMLDivElement;
  let map: MapLibreMap | null = null;
  let geo: GeoResponse | null = null;
  let mode: Mode = "none";
  let availableModes: Mode[] = ["none"];
  let error = "";
  let legend: { min: number; max: number; unit: string; stops: number[] } | null = null;
  let hoverMarker: maplibregl.Marker | null = null;
  let unsubHover: (() => void) | null = null;
  let unsubSelection: (() => void) | null = null;

  const SOURCE_ID = "ride-route";
  const LAYER_ID = "ride-route-layer";
  const SELECTION_SOURCE_ID = "ride-selection";
  const SELECTION_LAYER_ID = "ride-selection-layer";

  const OSM_STYLE: maplibregl.StyleSpecification = {
    version: 8,
    sources: {
      osm: {
        type: "raster",
        tiles: [
          "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
          "https://b.tile.openstreetmap.org/{z}/{x}/{y}.png",
          "https://c.tile.openstreetmap.org/{z}/{x}/{y}.png",
        ],
        tileSize: 256,
        attribution: "© OpenStreetMap contributors",
      },
    },
    layers: [{ id: "osm", type: "raster", source: "osm" }],
  };

  function bboxOf(coords: [number, number][]): LngLatBoundsLike {
    let minX = coords[0][0], maxX = coords[0][0], minY = coords[0][1], maxY = coords[0][1];
    for (const [x, y] of coords) {
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
    return [[minX, minY], [maxX, maxY]];
  }

  function lastValid(arr: (number | null)[], from: number): number | null {
    for (let i = from; i >= 0; i--) {
      const v = arr[i];
      if (v != null && Number.isFinite(v)) return v;
    }
    return null;
  }

  /** Build a FeatureCollection of segments grouped by color into MultiLineStrings.
   *  This is much more efficient than thousands of individual LineStrings and
   *  prevents rendering artifacts/culling issues at low zoom levels. */
  function buildSegments(g: GeoResponse, m: Mode): GeoJSON.FeatureCollection {
    const coords = g.geometry.coordinates;
    const features: GeoJSON.Feature[] = [];

    if (m === "none" || !g.properties.streams[m]) {
      // Single solid line
      features.push({
        type: "Feature",
        geometry: { type: "LineString", coordinates: coords },
        properties: { color: "#fc5200" },
      });
      legend = null;
      return { type: "FeatureCollection", features };
    }

    const raw = g.properties.streams[m]!;
    const conv = (v: number | null) =>
      v == null ? null : m === "speed" ? v * 3.6 : v;
    const values = raw.map(conv);

    const [lo, hi] = robustRange(values);
    legend = {
      min: lo,
      max: hi,
      unit: UNIT[m] ?? "",
      stops: [lo, lo + (hi - lo) * 0.25, lo + (hi - lo) * 0.5, lo + (hi - lo) * 0.75, hi],
    };

    const STEPS = 64; // Quantization steps to group segments by color
    const groups: Record<string, [number, number][][]> = {};

    let currentLine: [number, number][] = [coords[0] as [number, number]];
    let lastColor = "";

    for (let i = 0; i < coords.length - 1; i++) {
      const v = values[i] ?? lastValid(values, i);
      const range = hi - lo || 1;
      const t = v == null ? 0 : (v - lo) / range;
      const qt = Math.round(t * STEPS) / STEPS;
      const color = v == null ? "#888" : rampColor(qt);

      if (i > 0 && color !== lastColor) {
        if (!groups[lastColor]) groups[lastColor] = [];
        groups[lastColor].push(currentLine);
        currentLine = [coords[i] as [number, number]];
      }
      
      currentLine.push(coords[i + 1] as [number, number]);
      lastColor = color;
    }

    if (currentLine.length > 1) {
      if (!groups[lastColor]) groups[lastColor] = [];
      groups[lastColor].push(currentLine);
    }

    for (const [color, lines] of Object.entries(groups)) {
      features.push({
        type: "Feature",
        geometry: { type: "MultiLineString", coordinates: lines },
        properties: { color },
      });
    }

    return { type: "FeatureCollection", features };
  }

  function applyData() {
    if (!map || !geo) return;
    const fc = buildSegments(geo, mode);
    const src = map.getSource(SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
    if (src) {
      src.setData(fc);
    } else {
      map.addSource(SOURCE_ID, { type: "geojson", data: fc });
      // Add a thin semi-transparent base line for better visibility on varied maps
      map.addLayer({
        id: LAYER_ID + "-bg",
        type: "line",
        source: SOURCE_ID,
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": "#000",
          "line-opacity": 0.15,
          "line-width": ["interpolate", ["linear"], ["zoom"], 4, 4, 10, 5, 14, 10, 18, 14],
        },
      });
      map.addLayer({
        id: LAYER_ID,
        type: "line",
        source: SOURCE_ID,
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": ["get", "color"],
          "line-width": ["interpolate", ["linear"], ["zoom"], 4, 3, 10, 4, 14, 8, 18, 12],
        },
      });
      // Selection highlight line (hidden until a selection is made)
      map.addSource(SELECTION_SOURCE_ID, {
        type: "geojson",
        data: { type: "Feature", geometry: { type: "LineString", coordinates: [] as [number, number][] } },
      });
      map.addLayer({
        id: SELECTION_LAYER_ID + "-border",
        type: "line",
        source: SELECTION_SOURCE_ID,
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": "#fc5200",
          "line-width": ["interpolate", ["linear"], ["zoom"], 4, 8, 10, 11, 14, 17, 18, 22],
          "line-opacity": 0.9,
        },
      });
      map.addLayer({
        id: SELECTION_LAYER_ID,
        type: "line",
        source: SELECTION_SOURCE_ID,
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": "#ffffff",
          "line-width": ["interpolate", ["linear"], ["zoom"], 4, 5, 10, 7, 14, 12, 18, 16],
          "line-opacity": 0.85,
        },
      });
    }
  }

  async function load() {
    try {
      geo = await api.geo(activityId);
      const present: Mode[] = ["none"];
      for (const f of ["power", "heart_rate", "speed", "altitude", "cadence"] as StreamField[]) {
        const arr = geo.properties.streams[f];
        if (arr && arr.some((v) => v != null && Number.isFinite(v))) present.push(f);
      }
      availableModes = present;

      map = new maplibregl.Map({
        container: mapEl,
        style: OSM_STYLE,
        bounds: bboxOf(geo.geometry.coordinates),
        fitBoundsOptions: { padding: 30 },
      });
      map.addControl(new maplibregl.NavigationControl(), "top-right");
      map.on("load", applyData);
    } catch (e: any) {
      error = e?.message ?? String(e);
    }
  }

  function onModeChange() {
    applyData();
  }

  /** Find the index in geo.properties.t whose value is closest to `t`. */
  function nearestIndex(ts: number[], t: number): number {
    if (ts.length === 0) return -1;
    // Binary search since ts is monotonically increasing.
    let lo = 0, hi = ts.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (ts[mid] < t) lo = mid + 1;
      else hi = mid;
    }
    if (lo > 0 && Math.abs(ts[lo - 1] - t) < Math.abs(ts[lo] - t)) lo -= 1;
    return lo;
  }

  function ensureHoverMarker(): maplibregl.Marker {
    if (hoverMarker) return hoverMarker;
    const el = document.createElement("div");
    el.className = "hover-dot";
    hoverMarker = new maplibregl.Marker({ element: el, anchor: "center" });
    return hoverMarker;
  }

  function updateHover(t: number | null) {
    if (!map || !geo) return;
    if (t == null) {
      hoverMarker?.remove();
      return;
    }
    const ts = geo.properties.t;
    const coords = geo.geometry.coordinates;
    if (!ts.length || !coords.length) return;
    const i = nearestIndex(ts, t);
    if (i < 0 || i >= coords.length) return;
    const m = ensureHoverMarker();
    m.setLngLat(coords[i] as [number, number]).addTo(map);
  }

  function updateSelection(range: { t0: number; t1: number } | null) {
    if (!map || !geo) return;
    const src = map.getSource(SELECTION_SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
    if (!src) return;
    if (range == null) {
      src.setData({ type: "Feature", geometry: { type: "LineString", coordinates: [] as [number, number][] } });
      return;
    }
    const ts = geo.properties.t;
    const coords = geo.geometry.coordinates;
    if (!ts.length || !coords.length) return;
    const i0 = nearestIndex(ts, range.t0);
    const i1 = nearestIndex(ts, range.t1);
    if (i0 < 0 || i1 < 0 || i0 >= coords.length || i1 >= coords.length) return;
    const lo = Math.min(i0, i1);
    const hi = Math.max(i0, i1);
    const selCoords: [number, number][] = [];
    for (let i = lo; i <= hi; i++) {
      selCoords.push(coords[i] as [number, number]);
    }
    src.setData({ type: "Feature", geometry: { type: "LineString", coordinates: selCoords } });
  }

  onMount(() => {
    if (hasGeo) load();
    unsubHover = hoverTime.subscribe((t) => updateHover(t));
    unsubSelection = selectionRange.subscribe((r) => updateSelection(r));
  });
  onDestroy(() => {
    unsubHover?.();
    unsubSelection?.();
    hoverMarker?.remove();
    map?.remove();
  });
</script>

{#if !hasGeo}
  <div class="empty">{$t("map.no_geo")}</div>
{:else}
  <div class="map-wrap">
    <div class="controls">
      <label>
        {$t("map.color_by")}
        <select bind:value={mode} on:change={onModeChange}>
          {#each availableModes as m}
            <option value={m}>{MODE_LABEL[m]}</option>
          {/each}
        </select>
      </label>
      {#if legend}
        <div class="legend">
          <span class="lo">{legend.min.toFixed(0)} {legend.unit}</span>
          <div class="bar"></div>
          <span class="hi">{legend.max.toFixed(0)} {legend.unit}</span>
        </div>
      {/if}
    </div>
    {#if error}<div class="error">{error}</div>{/if}
    <div class="map" bind:this={mapEl}></div>
  </div>
{/if}

<style>
  .map-wrap {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
  }
  .controls {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
  }
  .controls label {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--muted);
    font-size: 13px;
  }
  .map { width: 100%; height: 480px; }
  .empty {
    background: var(--panel);
    border: 1px dashed var(--border);
    border-radius: 8px;
    padding: 24px;
    text-align: center;
    color: var(--muted);
  }
  .error {
    color: #ef4444;
    padding: 8px 14px;
    border-bottom: 1px solid var(--border);
  }
  .legend {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: var(--muted);
    margin-left: auto;
  }
  .legend .bar {
    width: 180px;
    height: 10px;
    border-radius: 5px;
    background: linear-gradient(
      to right,
      rgb(48,18,59) 0%,
      rgb(70,50,126) 13%,
      rgb(54,117,173) 25%,
      rgb(40,174,162) 38%,
      rgb(97,220,102) 50%,
      rgb(194,224,65) 63%,
      rgb(253,175,60) 75%,
      rgb(240,86,32) 88%,
      rgb(122,4,3) 100%
    );
  }

  /* Force MapLibre's controls to be readable on dark panel */
  :global(.maplibregl-ctrl-attrib) {
    background: rgba(15, 17, 21, 0.7) !important;
    color: var(--muted) !important;
  }
  :global(.maplibregl-ctrl-attrib a) { color: var(--text) !important; }

  /* Hover marker pinned to the route while hovering a chart */
  :global(.hover-dot) {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: #fc5200;
    border: 2px solid #fff;
    box-shadow: 0 0 0 2px rgba(252, 82, 0, 0.35), 0 1px 4px rgba(0,0,0,0.5);
    pointer-events: none;
  }
</style>
