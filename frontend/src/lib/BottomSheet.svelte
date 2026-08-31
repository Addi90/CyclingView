<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { slide, fade } from "svelte/transition";

  export let open = false;
  export let title = "";
  export let danger = false;

  function onKey(e: KeyboardEvent) {
    if (e.key === "Escape") open = false;
  }
  onMount(() => window.addEventListener("keydown", onKey));
  onDestroy(() => window.removeEventListener("keydown", onKey));
</script>

{#if open}
  <div
    class="backdrop"
    transition:fade={{ duration: 120 }}
    on:click|self={() => (open = false)}
  >
    <div
      class="sheet"
      class:danger
      role="dialog"
      aria-modal="true"
      transition:slide={{ duration: 160, axis: "y" }}
    >
      {#if title}
        <div class="sheet-title">{title}</div>
      {/if}
      <slot />
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 100;
    background: rgba(0, 0, 0, 0.55);
    display: flex;
    align-items: flex-end;
  }
  .sheet {
    background: var(--panel);
    border: 1px solid var(--border);
    border-bottom: none;
    border-radius: 12px 12px 0 0;
    padding: 16px 16px calc(16px + env(safe-area-inset-bottom, 0px));
    width: 100%;
    max-width: 640px;
    margin: 0 auto;
    max-height: 80vh;
    overflow-y: auto;
  }
  .sheet-title {
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--muted);
    margin-bottom: 12px;
  }
  .sheet.danger .sheet-title { color: var(--hr); }
</style>