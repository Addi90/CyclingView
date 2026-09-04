<script lang="ts">
  import { createEventDispatcher } from "svelte";

  const dispatch = createEventDispatcher();

  /**
   * Generic segmented pill control — the single source of truth for the pill
   * look shared by the stats/settings page tabs and the power W / W-kg toggle.
   *
   * `options` may be:
   *   - `string[]`              → value is the 0-based index (page indicators)
   *   - `Array<{label, value}>` → value is each entry's `value` (selectors)
   *
   * Drive it one-way: pass the current `value` and listen for `change`
   * (the event detail is the newly selected value). The parent updates its own
   * state; the re-rendered `value` prop moves the highlight.
   */
  export let options: Array<string | { label: string; value: any }>;
  export let value: any;
  export let ariaLabel = "";
  export let title = "";

  function pick(v: any) {
    dispatch("change", v);
  }
</script>

<div class="pillbar" role="tablist" aria-label={ariaLabel} title={title || undefined}>
  {#each options as opt, i}
    {@const isStr = typeof opt === "string"}
    {@const v = isStr ? i : opt.value}
    <button
      type="button"
      role="tab"
      aria-selected={v === value}
      class:active={v === value}
      on:click={() => pick(v)}
    >
      {isStr ? opt : opt.label}
    </button>
  {/each}
</div>

<style>
  .pillbar {
    display: inline-flex;
    border: 1px solid var(--border);
    border-radius: 999px;
    overflow: hidden;
  }
  .pillbar button {
    background: transparent;
    border: 0;
    color: var(--muted);
    padding: 4px 14px;
    font-size: 12px;
    cursor: pointer;
    min-height: 28px;
    white-space: nowrap;
  }
  .pillbar button.active {
    background: var(--accent);
    color: var(--bg); /* dark on orange: white fails WCAG AA */
    font-weight: 600;
  }
</style>