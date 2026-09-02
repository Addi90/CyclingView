<script lang="ts">
  import StatsPanel from "./StatsPanel.svelte";
  import PowerBestsTable from "./PowerBestsTable.svelte";
  import { t } from "./i18n";

  /** 0 = all-time stats, 1 = power bests. */
  let page = 0;
  let dragging = false;
  let dx = 0;

  // Horizontal page swipe. Manual listeners (not on:touchmove) so touchmove is
  // registered non-passive and preventDefault actually works. Claiming rule:
  // horizontal only when |dx| dominates |dy| — vertical gestures fall through
  // to the sheet's own scroll / drag-close, and claimed swipes preventDefault
  // so the page doesn't scroll vertically mid-swipe.
  const SLOP = 10; // px horizontal before claiming the swipe
  const VEL = 0.2; // px/ms horizontal release velocity that flips the page

  let touchId = -1;
  let startX = 0;
  let startY = 0;
  let claimed: "none" | "page" | "vertical" = "none";
  let samples: { t: number; x: number }[] = [];

  function swipe(el: HTMLDivElement) {
    // The track's transform is driven by the reactive inline style, so
    // resetting state alone snaps it back.
    const reset = () => {
      claimed = "none";
      dragging = false;
      dx = 0;
    };

    const onStart = (e: TouchEvent) => {
      const t0 = e.touches[0];
      if (!t0) return;
      touchId = t0.identifier;
      startX = t0.clientX;
      startY = t0.clientY;
      claimed = "none";
      dx = 0;
      samples = [{ t: performance.now(), x: t0.clientX }];
    };

    const onMove = (e: TouchEvent) => {
      if (claimed === "vertical") return;
      const t = Array.from(e.touches).find((x) => x.identifier === touchId);
      if (!t) return;
      const ddx = t.clientX - startX;
      const ddy = t.clientY - startY;
      if (claimed === "none") {
        if (Math.abs(ddx) >= SLOP && Math.abs(ddx) > Math.abs(ddy)) {
          claimed = "page";
          dragging = true;
        } else if (Math.abs(ddy) >= SLOP) {
          claimed = "vertical"; // sheet scroll / drag-close handles it
          return;
        } else {
          return;
        }
      }
      e.preventDefault();
      const w = el.clientWidth;
      // 1:1 within range; a faint rubber-band at the track edges (no other
      // page peeks in) so the sheet doesn't dead-stop mid-gesture.
      const atEdge = (page === 0 && ddx > 0) || (page === 1 && ddx < 0);
      dx = atEdge ? ddx * 0.15 : ddx;
      dx = Math.max(-w, Math.min(w, dx));
      const now = performance.now();
      samples.push({ t: now, x: t.clientX });
      while (samples.length > 1 && now - samples[0].t > 120) samples.shift();
    };

    const onEnd = () => {
      if (claimed !== "page") {
        reset();
        return;
      }
      const last = samples[samples.length - 1];
      const ref = [...samples].reverse().find((s) => last.t - s.t >= 80) ?? samples[0];
      const vel = last.t > ref.t ? (last.x - ref.x) / (last.t - ref.t) : 0;
      const w = el.clientWidth;
      const flip = Math.abs(dx) > w * 0.25 || Math.abs(vel) >= VEL;
      if (flip) page = Math.max(0, Math.min(1, page + (dx < 0 ? 1 : -1)));
      reset();
    };

    el.addEventListener("touchstart", onStart, { passive: true });
    el.addEventListener("touchmove", onMove, { passive: false });
    el.addEventListener("touchend", onEnd);
    el.addEventListener("touchcancel", onEnd);
    return { destroy() {
      el.removeEventListener("touchstart", onStart);
      el.removeEventListener("touchmove", onMove);
      el.removeEventListener("touchend", onEnd);
      el.removeEventListener("touchcancel", onEnd);
      reset();
    } };
  }
</script>

<!-- Page indicator pills: tap to switch, swipe to swipe. -->
<div class="pills" role="tablist" aria-label={$t("stats.andBests")}>
  <button
    type="button"
    role="tab"
    aria-selected={page === 0}
    class:active={page === 0}
    on:click={() => (page = 0)}
  >{$t("stats.alltime")}</button>
  <button
    type="button"
    role="tab"
    aria-selected={page === 1}
    class:active={page === 1}
    on:click={() => (page = 1)}
  >{$t("power.bests.short")}</button>
</div>

<div class="pages" use:swipe>
  <!-- One page = 50% of the 200%-wide track: translateX percentages resolve
       against the track's own box, so -50% = one page (not -100%). -->
  <div
    class="page-track"
    role="tabpanel"
    style="transform: translateX(calc({-page * 50}% + {dx}px)); transition: {dragging ? "none" : "transform 0.22s ease-out"};"
  >
    <div class="page">
      <StatsPanel />
    </div>
    <div class="page">
      <PowerBestsTable activityId={null} compact />
    </div>
  </div>
</div>

<style>
  .pills {
    display: inline-flex;
    border: 1px solid var(--border);
    border-radius: 999px;
    overflow: hidden;
    margin-bottom: 12px;
  }
  .pills button {
    background: transparent;
    border: 0;
    color: var(--muted);
    padding: 4px 14px;
    font-size: 12px;
    cursor: pointer;
    min-height: 28px;
  }
  .pills button.active {
    background: var(--accent);
    color: var(--bg); /* dark on orange: white fails WCAG AA */
    font-weight: 600;
  }
  .pages { overflow: hidden; }
  .page-track {
    display: flex;
    width: 200%;
    will-change: transform;
  }
  .page {
    flex: 0 0 50%;
    min-width: 0;
  }
</style>