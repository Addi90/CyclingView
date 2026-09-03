<script lang="ts">
  import SettingsProfile from "./SettingsProfile.svelte";
  import SettingsAnalysis from "./SettingsAnalysis.svelte";
  import SettingsBikes from "./SettingsBikes.svelte";
  import SettingsData from "./SettingsData.svelte";
  import PillBar from "./PillBar.svelte";
  import { t } from "./i18n";

  /** Page order: 0 = Profil, 1 = Auswertung, 2 = Räder, 3 = Daten. */
  const TABS = [
    { key: "settings.profile" as const },
    { key: "settings.analysis" as const },
    { key: "settings.bikes" as const },
    { key: "settings.data" as const },
  ];
  const COUNT = TABS.length;

  let page = 0;
  let dragging = false;
  let dx = 0;

  // Pill-bar options (string[] → value is the page index).
  $: pageOptions = TABS.map((tab) => $t(tab.key));

  // Horizontal page swipe — same pattern as StatsSheet. Manual listeners (not
  // on:touchmove) so touchmove is registered non-passive and preventDefault
  // actually works. Claiming rule: horizontal only when |dx| dominates |dy| —
  // vertical gestures fall through to the sheet's own scroll / drag-close, and
  // claimed swipes preventDefault so the page doesn't scroll vertically mid-swipe.
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
      const atEdge = (page === 0 && ddx > 0) || (page === COUNT - 1 && ddx < 0);
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
      if (flip) page = Math.max(0, Math.min(COUNT - 1, page + (dx < 0 ? 1 : -1)));
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

<!-- Pill page indicator: tap a pill to jump, swipe the track to move. -->
<div class="pills">
  <PillBar options={pageOptions} value={page} on:change={(e) => (page = e.detail)} ariaLabel={$t("settings.title")} />
</div>

<!-- Swipeable page track: width COUNT*100%, each page 1/COUNT. -->
<div class="pages" use:swipe>
  <div
    class="page-track"
    role="tabpanel"
    style="transform: translateX(calc({-page * (100 / COUNT)}% + {dx}px)); transition: {dragging ? 'none' : 'transform 0.22s ease-out'};"
  >
    <div class="page"><SettingsProfile /></div>
    <div class="page"><SettingsAnalysis /></div>
    <div class="page"><SettingsBikes /></div>
    <div class="page"><SettingsData /></div>
  </div>
</div>

<style>
  /* Pill bar wrapper: spacing above the swipe track. */
  .pills {
    margin-bottom: 12px;
  }

  .pages {
    overflow: hidden;
  }
  .page-track {
    display: flex;
    width: 400%;
    will-change: transform;
  }
  .page {
    flex: 0 0 25%;
    min-width: 0;
  }
</style>