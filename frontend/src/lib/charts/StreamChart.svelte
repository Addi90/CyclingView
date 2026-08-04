<script lang="ts">
  import { onMount, onDestroy, tick } from "svelte";
  import uPlot, { type Options as UPlotOptions } from "uplot";
  import "uplot/dist/uPlot.min.css";
  import { robustRange } from "../colormap";
  import { hoverTime, selectionRange } from "../hover";

  export let label: string;
  export let color: string = "#fc5200";
  export let xs: number[];
  export let ys: (number | null)[];
  export let unit = "";
  export let height = 180;
  export let syncKey = "ride";
  export let valueDigits = 0;
  export let zones: { from: number; to: number; color: string }[] | null = null;
  export let lowQ = 0.005;
  export let highQ = 0.995;

  let container: HTMLDivElement;
  let plot: uPlot | null = null;
  let ro: ResizeObserver | null = null;

  const AXIS_TEXT = "#98a2b3";
  const GRID = "rgba(152, 162, 179, 0.18)";
  const TICK = "rgba(152, 162, 179, 0.4)";

  function fmtX(_u: uPlot, val: number): string {
    const s = Math.max(0, Math.round(val));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    return h > 0
      ? `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`
      : `${m}:${String(sec).padStart(2, "0")}`;
  }

  function toData(): uPlot.AlignedData {
    const x = new Float64Array(xs.length);
    const y = new Float64Array(xs.length);
    for (let i = 0; i < xs.length; i++) {
      x[i] = xs[i];
      const v = ys[i];
      y[i] = v == null ? NaN : v;
    }
    return [x, y];
  }

  /** Robust y-scale: trim outliers (lowQ/highQ percentile) so a single sensor
   *  spike (e.g. cadence 65535) doesn't flatten the real signal to a line at 0. */
  function yRange(): [number, number] | null {
    const [lo, hi] = robustRange(ys, lowQ, highQ);
    if (!Number.isFinite(lo) || !Number.isFinite(hi) || lo === hi) return null;
    const pad = (hi - lo) * 0.08 || 1;
    return [Math.min(lo - pad, lo), hi + pad];
  }

  function build() {
    if (!container) return;
    if (plot) { plot.destroy(); plot = null; }
    if (!xs?.length) return;

    const opts: UPlotOptions = {
      width: Math.max(300, container.clientWidth || 800),
      height,
      cursor: { sync: { key: syncKey } },
      scales: {
        x: { time: false },
        y: {
          auto: true,
          range: (_u, min, max) => {
            const r = yRange();
            return r || [min, max];
          },
        },
      },
      axes: [
        {
          stroke: AXIS_TEXT,
          grid: { stroke: GRID, width: 1 },
          ticks: { stroke: TICK, width: 1 },
          values: (_u, splits) => splits.map((v) => fmtX(_u, v)),
        },
        {
          stroke: AXIS_TEXT,
          grid: { stroke: GRID, width: 1 },
          ticks: { stroke: TICK, width: 1 },
          size: 55,
        },
      ],
      series: [
        { label: "t", value: (_u, v) => (v == null ? "–" : fmtX(_u, v)) },
        {
          label,
          stroke: color,
          width: 1.75,
          fill: color + "22",
          spanGaps: true,
          points: { show: false },
          value: (_u, v) =>
            v == null || Number.isNaN(v)
              ? "–"
              : `${v.toFixed(valueDigits)}${unit ? " " + unit : ""}`,
        },
      ],
      legend: { show: true, live: true },
      hooks: {
        setCursor: [
          (u) => {
            const idx = u.cursor.idx;
            if (idx == null) {
              hoverTime.set(null);
              selectionRange.set(null);
            } else {
              const t = u.data[0][idx];
              hoverTime.set(typeof t === "number" ? t : null);
            }
          },
        ],
        setSelect: [
          (u) => {
            const { left, width, show } = u.select;
            if (width <= 0 || show === false) {
              selectionRange.set(null);
              return;
            }
            const t0 = u.posToVal(left, "x");
            const t1 = u.posToVal(left + width, "x");
            if (typeof t0 === "number" && typeof t1 === "number") {
              selectionRange.set({ t0: Math.min(t0, t1), t1: Math.max(t0, t1) });
            }
          },
        ],
        draw: [
          (u) => {
            if (!zones || !zones.length) return;
            const { ctx } = u;
            const { left, top, width, height } = u.bbox;
            
            const sKey = u.series[1].scale || "y";
            const s = u.scales[sKey];
            if (!s || s.min == null || s.max == null) return;

            const min = s.min;
            const max = s.max;
            const range = max - min;
            if (range <= 0) return;

            ctx.save();
            ctx.beginPath();
            ctx.rect(left, top, width, height);
            ctx.clip();

            for (const z of zones) {
              // Calculate pixel positions manually to be 100% sure of the alignment.
              // uPlot Y axis is inverted: max is at top (0), min is at bottom (height).
              // We work relative to the bbox top/height.
              
              const vTop = Math.min(max, Math.max(min, z.to));
              const vBot = Math.min(max, Math.max(min, z.from));
              
              if (vTop <= vBot) continue;

              // Percentage from bottom (0 = min, 1 = max)
              const pctTop = (vTop - min) / range;
              const pctBot = (vBot - min) / range;

              // Canvas Y (top-down): top + height * (1 - pct)
              const yTop = top + height * (1 - pctTop);
              const yBot = top + height * (1 - pctBot);

              ctx.fillStyle = z.color + "26";
              ctx.fillRect(left, yTop, width, yBot - yTop);
            }
            ctx.restore();
          },
        ],
      },
    };

    plot = new uPlot(opts, toData(), container);
  }

  function resize() {
    if (!plot || !container) return;
    const w = container.clientWidth;
    if (w > 0) plot.setSize({ width: w, height });
  }

  let _lastZones: typeof zones = null;

  $: if (xs && ys && container) {
    if (!plot || zones !== _lastZones) {
      _lastZones = zones;
      build();
    } else {
      plot.setData(toData());
    }
  }

  onMount(async () => {
    // Initial build if data is already present
    if (xs?.length && ys?.length) build();
    // After layout settles (sidebar grid columns resolved), force a correct size.
    await tick();
    requestAnimationFrame(resize);
    // And again after the next frame, in case fonts/layout shifted.
    requestAnimationFrame(() => requestAnimationFrame(resize));

    ro = new ResizeObserver(() => resize());
    ro.observe(container);
    window.addEventListener("resize", resize);
    container.addEventListener("mouseup", () => selectionRange.set(null));
  });

  onDestroy(() => {
    window.removeEventListener("resize", resize);
    ro?.disconnect();
    container?.removeEventListener("mouseup", () => selectionRange.set(null));
    plot?.destroy();
  });
</script>

<div class="chart-card">
  <div class="title" style:color={color}>
    <div class="title-left">
      <span>{label}</span>
      {#if unit}<span class="unit">({unit})</span>{/if}
    </div>
    <div class="title-right">
      <slot name="title-right" />
    </div>
  </div>
  <div class="chart" bind:this={container}></div>
</div>

<style>
  .chart-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 14px 14px;
  }
  .title {
    font-size: 13px;
    font-weight: 600;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 6px;
  }
  .title-left {
    display: flex;
    gap: 6px;
    align-items: baseline;
  }
  .unit { color: var(--muted); font-weight: 400; font-size: 11px; }
  .chart { width: 100%; min-height: 180px; }

  :global(.u-legend) {
    color: var(--text);
    font-size: 12px;
    margin-top: 4px;
  }
  :global(.u-legend .u-marker) { border-color: var(--border) !important; }
  :global(.u-legend th, .u-legend td) { color: var(--text) !important; }
  :global(.u-cursor-pt) { display: none !important; }
  :global(.u-select) {
    background: rgba(252, 82, 0, 0.07) !important;
    border: 1px solid var(--accent) !important;
  }
</style>
