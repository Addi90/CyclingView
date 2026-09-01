<script lang="ts">
  // Dual-knob range slider: two overlapping native <input type="range">
  // elements (only the thumbs take pointer events) with an accent-colored
  // fill between them. No dependencies.
  import { createEventDispatcher } from "svelte";

  const dispatch = createEventDispatcher();

  export let min = 0;
  export let max = 1;
  export let step = 1;
  export let lo: number;
  export let hi: number;
  export let unit = "";
  export let decimals = 0;
  export let ariaLabel = "";

  const span = Math.max(max - min, step);
  $: pctLo = ((lo - min) / span) * 100;
  $: pctHi = ((hi - min) / span) * 100;
  // When both knobs sit on the same spot, the lower one must stay grabbable.
  $: loOnTop = hi - lo <= step;

  function onLo(e: Event) {
    lo = Math.min(Number((e.target as HTMLInputElement).value), hi);
  }
  function onHi(e: Event) {
    hi = Math.max(Number((e.target as HTMLInputElement).value), lo);
  }
  function fmt(v: number) {
    return v.toFixed(decimals);
  }
</script>

<div class="rs-wrap">
  <div class="rs">
    <div class="rs-track">
      <div class="rs-fill" style="left: {pctLo}%; right: {100 - pctHi}%"></div>
    </div>
    <input
      type="range"
      class="rs-range"
      class:rs-top={loOnTop}
      min={min}
      max={max}
      step={step}
      value={lo}
      aria-label={`${ariaLabel} (${unit} min)`}
      on:input={onLo}
      on:change={() => dispatch("change")}
    />
    <input
      type="range"
      class="rs-range"
      min={min}
      max={max}
      step={step}
      value={hi}
      aria-label={`${ariaLabel} (${unit} max)`}
      on:input={onHi}
      on:change={() => dispatch("change")}
    />
  </div>
  <div class="rs-vals">
    <span>{fmt(lo)} {unit}</span>
    <span>{fmt(hi)} {unit}</span>
  </div>
</div>

<style>
  .rs-wrap { display: flex; flex-direction: column; gap: 2px; }
  .rs { position: relative; height: 32px; }
  .rs-range {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    min-height: 0; /* overrides the global mobile input min-height */
    margin: 0;
    -webkit-appearance: none;
    appearance: none;
    background: transparent;
    pointer-events: none;
    z-index: 2;
  }
  .rs-top { z-index: 3; }
  .rs-track {
    position: absolute;
    left: 0;
    right: 0;
    top: 50%;
    transform: translateY(-50%);
    height: 4px;
    border-radius: 2px;
    background: var(--border);
  }
  .rs-fill {
    position: absolute;
    top: 0;
    bottom: 0;
    border-radius: 2px;
    background: var(--accent);
  }
  .rs-range::-webkit-slider-runnable-track { height: 4px; background: transparent; }
  .rs-range::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 18px;
    height: 18px;
    margin-top: -7px; /* center the 18px thumb on the 4px track */
    border-radius: 50%;
    background: var(--accent);
    border: 2px solid var(--panel);
    pointer-events: auto;
    cursor: grab;
  }
  .rs-range::-moz-range-track { height: 4px; background: transparent; }
  .rs-range::-moz-range-thumb {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--accent);
    border: 2px solid var(--panel);
    pointer-events: auto;
    cursor: grab;
  }
  .rs-vals {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: var(--muted);
    font-variant-numeric: tabular-nums;
  }
  @media (max-width: 768px) {
    .rs { height: 44px; } /* thumb + hit area sized for touch */
    .rs-range::-webkit-slider-thumb { width: 22px; height: 22px; margin-top: -9px; }
    .rs-range::-moz-range-thumb { width: 18px; height: 18px; }
  }
</style>