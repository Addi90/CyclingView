<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { slide, fade } from "svelte/transition";

  export let open = false;
  export let title = "";
  export let danger = false;

  // Swipe-down-to-close. Claimable only when the sheet content is scrolled to
  // the top (else the drag scrolls the content); preventDefault stops the
  // overscroll chain to the page behind. Manual listeners (not on:touchmove)
  // so touchmove is registered non-passive and preventDefault actually works.
  // Gate is only input/textarea/select: links and buttons cover most of the
  // sheet content, and a plain tap (no >8px movement) still fires normally.
  const SLOP = 8; // px of downward movement before claiming the drag
  const VEL = 0.3; // px/ms downward release velocity that dismisses

  let backdropDim = false;
  let dragging = false;
  let settling = false;

  function onKey(e: KeyboardEvent) {
    if (e.key === "Escape") open = false;
  }
  onMount(() => window.addEventListener("keydown", onKey));
  onDestroy(() => window.removeEventListener("keydown", onKey));

  function dragClose(node: HTMLDivElement) {
    let startY = 0;
    let startX = 0;
    let dragY = 0;
    let touchId = -1;
    let claimed = false;
    let samples: { t: number; y: number }[] = [];

    const reset = () => {
      claimed = false;
      settling = false;
      dragging = false;
      dragY = 0;
      backdropDim = false;
      node.style.transform = "";
    };

    const onStart = (e: TouchEvent) => {
      const t = e.touches[0];
      if (!t) return;
      if ((e.target as HTMLElement).closest?.("input,textarea,select")) return;
      touchId = t.identifier;
      claimed = false;
      startY = t.clientY;
      startX = t.clientX;
      samples = [{ t: performance.now(), y: t.clientY }];
    };

    const onMove = (e: TouchEvent) => {
      if (settling) return;
      const t = Array.from(e.touches).find((x) => x.identifier === touchId);
      if (!t) return;
      const dy = t.clientY - startY;
      const dx = t.clientX - startX;
      if (!claimed) {
        // Content not at the top → let it scroll natively; a drag that later
        // reaches the top can still claim (iOS sheet behaviour).
        if (node.scrollTop > 0 || dy < SLOP || Math.abs(dx) > dy) return;
        claimed = true;
        dragging = true;
      }
      e.preventDefault();
      const h = node.clientHeight;
      // 1:1 for the first half of the sheet, then rubber-band resistance.
      dragY = dy > h * 0.5 ? h * 0.5 + (dy - h * 0.5) * 0.25 : Math.max(0, dy);
      backdropDim = dragY > 40;
      node.style.transform = `translateY(${dragY}px)`;
      const now = performance.now();
      samples.push({ t: now, y: t.clientY });
      while (samples.length > 1 && now - samples[0].t > 120) samples.shift();
    };

    const onEnd = () => {
      if (!claimed || settling) return;
      claimed = false;
      settling = true;
      const h = node.clientHeight;
      const last = samples[samples.length - 1];
      const ref = [...samples].reverse().find((s) => last.t - s.t >= 80) ?? samples[0];
      const vel = last.t > ref.t ? (last.y - ref.y) / (last.t - ref.t) : 0;
      const dismiss = vel >= VEL || dragY >= Math.max(100, h * 0.3);
      dragging = false;
      node.style.transform = dismiss ? `translateY(${h + 100}px)` : "translateY(0)";
      setTimeout(() => {
        reset();
        if (dismiss) open = false;
      }, 220);
    };

    node.addEventListener("touchstart", onStart, { passive: true });
    node.addEventListener("touchmove", onMove, { passive: false });
    node.addEventListener("touchend", onEnd);
    node.addEventListener("touchcancel", onEnd);
    return {
      destroy() {
        node.removeEventListener("touchstart", onStart);
        node.removeEventListener("touchmove", onMove);
        node.removeEventListener("touchend", onEnd);
        node.removeEventListener("touchcancel", onEnd);
        reset();
      },
    };
  }
</script>

{#if open}
  <div
    class="backdrop"
    class:dim={backdropDim}
    transition:fade={{ duration: 120 }}
    on:click|self={() => (open = false)}
  >
    <div
      class="sheet"
      class:danger
      class:dragging
      class:settling
      use:dragClose
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
    transition: background 0.2s ease-out;
  }
  .backdrop.dim {
    background: rgba(0, 0, 0, 0.75);
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
    overscroll-behavior: contain;
    will-change: transform;
  }
  /* While dragging: follow the finger with no transition.
     While settling: spring back / slide off over 0.2s. */
  .sheet.dragging {
    transition: none !important;
  }
  .sheet.settling {
    transition: transform 0.2s ease-out;
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