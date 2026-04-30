<script lang="ts">
  import { onMount, onDestroy, tick } from "svelte";
  import uPlot, { type Options as UPlotOptions } from "uplot";
  import "uplot/dist/uPlot.min.css";
  import { robustRange } from "../colormap";
  import { hoverTime } from "../hover";

  export let label: string;
  export let color: string = "#fc5200";
  export let xs: number[];
  export let ys: (number | null)[];
  export let unit = "";
  export let height = 180;
  export let syncKey = "ride";
  export let valueDigits = 0;

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

  /** Robust y-scale: trim outliers (1st/99th percentile) so a single sensor
   *  spike (e.g. cadence 65535) doesn't flatten the real signal to a line at 0. */
  function yRange(): [number, number] | null {
    const [lo, hi] = robustRange(ys, 0.005, 0.995);
    if (!Number.isFinite(lo) || !Number.isFinite(hi) || lo === hi) return null;
    const pad = (hi - lo) * 0.08 || 1;
    return [Math.min(lo - pad, lo), hi + pad];
  }

  function build() {
    if (!container) return;
    if (plot) { plot.destroy(); plot = null; }
    if (!xs?.length) return;

    const yr = yRange();

    const opts: UPlotOptions = {
      width: Math.max(300, container.clientWidth || 800),
      height,
      cursor: { sync: { key: syncKey } },
      scales: {
        x: { time: false },
        y: yr
          ? { auto: false, range: () => yr }
          : { auto: true },
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
            } else {
              const t = u.data[0][idx];
              hoverTime.set(typeof t === "number" ? t : null);
            }
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

  $: if (plot && xs && ys) {
    plot.setData(toData());
  }

  onMount(async () => {
    build();
    // After layout settles (sidebar grid columns resolved), force a correct size.
    await tick();
    requestAnimationFrame(resize);
    // And again after the next frame, in case fonts/layout shifted.
    requestAnimationFrame(() => requestAnimationFrame(resize));

    ro = new ResizeObserver(() => resize());
    ro.observe(container);
    window.addEventListener("resize", resize);
  });

  onDestroy(() => {
    window.removeEventListener("resize", resize);
    ro?.disconnect();
    plot?.destroy();
  });
</script>

<div class="chart-card">
  <div class="title" style:color={color}>
    <span>{label}</span>
    {#if unit}<span class="unit">({unit})</span>{/if}
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
    gap: 6px;
    align-items: baseline;
    padding-bottom: 6px;
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
</style>
