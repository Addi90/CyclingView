<script lang="ts">
  import { Router, Route, Link, navigate } from "svelte-routing";
  import { Settings as SettingsIcon, List, Plus, BarChart3 } from "lucide-svelte";
    import { Bike } from "lucide-svelte";
  import RidesList from "./routes/RidesList.svelte";
  import RideDetail from "./routes/RideDetail.svelte";
  import SettingsDialog from "./lib/SettingsDialog.svelte";
  import BottomSheet from "./lib/BottomSheet.svelte";
  import StatsPanel from "./lib/StatsPanel.svelte";
  import PowerBestsTable from "./lib/PowerBestsTable.svelte";
  import { uploadRequest } from "./lib/upload";
  import { t } from "./lib/i18n";

  export let url = "";

  let settingsOpen = false;
  let statsOpen = false;

  // Clicking a <Link> inside the sheet (ride bests, stats) navigates to the
  // ride; close the sheet so it doesn't sit over the loaded detail page.
  function onSheetStackClick(e: MouseEvent) {
    if ((e.target as HTMLElement).closest("a")) statsOpen = false;
  }
</script>

<Router {url} let:location>
  <header>
    <div class="spacer"></div>
<Link to="/"><h1><Bike size={30} /> Cycling View</h1></Link>
    <div class="right">
      <button
        type="button"
        class="cog"
        title={$t("settings.title")}
        aria-label={$t("settings.title")}
        on:click={() => (settingsOpen = true)}
      >
        <SettingsIcon size={30} />
      </button>
    </div>
  </header>
  <main>
    <Route path="/rides/:id" let:params>
      <RideDetail id={params.id} />
    </Route>
    <Route path="/"><RidesList /></Route>
  </main>
  <!-- Mobile bottom tab bar: Rides | + (upload) | Stats & Bests. Settings is
       the floating gear button (FAB) on mobile; on desktop it stays the
       header cog. Hidden ≥769px. -->
  <nav class="tabbar" aria-label="Main navigation">
    <button
      type="button"
      class:active={!location.pathname.startsWith("/rides/")}
      on:click={() => navigate("/")}
    >
      <List size={24} /><span>{$t("rides.title")}</span>
    </button>
    <button
      type="button"
      class="plus"
      aria-label={$t("rides.upload")}
      title={$t("rides.upload")}
      on:click={() => {
        uploadRequest.update((n) => n + 1);
        if (location.pathname.startsWith("/rides/")) navigate("/");
      }}
    >
      <Plus size={26} />
    </button>
    <button type="button" on:click={() => (statsOpen = true)}>
      <BarChart3 size={24} /><span>{$t("stats.andBests")}</span>
    </button>
  </nav>
  <button
    type="button"
    class="fab"
    title={$t("settings.title")}
    aria-label={$t("settings.title")}
    on:click={() => (settingsOpen = true)}
  >
    <SettingsIcon size={22} />
  </button>
  <!-- Must live inside <Router>: StatsPanel/PowerBestsTable render <Link>,
       which needs the router context (crashes the sheet outside). -->
  <BottomSheet bind:open={statsOpen} title={$t("stats.andBests")}>
    <div class="sheet-stack" on:click={onSheetStackClick}>
      <StatsPanel />
      <PowerBestsTable activityId={null} compact />
    </div>
  </BottomSheet>
</Router>

<SettingsDialog bind:open={settingsOpen} />

<style>
  header {
    border-bottom: 1px solid var(--border);
    padding: 12px 24px;
    background: var(--panel);
    position: sticky;
    top: 0;
    z-index: 10;
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 12px;
  }
  .spacer { width: 34px; }
  .right { display: flex; justify-content: flex-end; }
  header :global(a) { color: var(--text); text-decoration: none; }
  h1 {
    margin: 0;
    font-size: 24px;
    font-weight: 600;
    text-align: center;
  }
  .cog {
    padding: 8px 8px;
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 50%;    cursor: pointer;
    display: inline-flex;
    align-items: center;
    line-height: 1;
  }
  .cog:hover { background: rgba(255, 255, 255, 0.06); border-color: var(--accent); color: var(--accent); }
  main { padding: 16px 24px 48px; }

  .tabbar { display: none; }
  .fab { display: none; }
  .sheet-stack { display: grid; gap: 12px; }
  @media (max-width: 768px) {
    .cog { display: none; } /* settings lives in the FAB */
    .fab {
      display: flex;
      align-items: center;
      justify-content: center;
      position: fixed;
      right: 16px;
      bottom: calc(92px + env(safe-area-inset-bottom));
      width: 52px;
      height: 52px;
      min-height: 52px;
      border-radius: 50%;
      background: var(--panel-2);
      color: var(--text);
      border: 1px solid var(--border);
      box-shadow: var(--elev-1);
      cursor: pointer;
      z-index: 20;
      transition: transform 0.12s, box-shadow 0.12s;
    }
    .fab:hover { border-color: var(--accent); color: var(--accent); }
    .fab:active { transform: translateY(1px); box-shadow: var(--elev-1-pressed); }
    .tabbar {
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      position: fixed;
      left: 0;
      right: 0;
      bottom: 0;
      z-index: 30;
      background: var(--panel);
      border-top: 2px solid var(--border);
      padding-bottom: calc(env(safe-area-inset-bottom) + 10px); /* iPhone home indicator + 10px */
    }
    .tabbar button {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center; /* bar is 72px; keep icon+label centered */
      gap: 2px;
      min-height: 72px;
      background: transparent;
      border: 0;
      color: var(--muted);
      font-size: 11px;
      cursor: pointer;
    }
    .tabbar button.active { color: var(--accent); }
    .tabbar .plus {
      /* min-height override: .tabbar button's min-height:72px would clamp
         the 56px height into a 56×72 ellipse (border-radius:50% on a
         non-square box). Keep the box square. */
      width: 56px;
      height: 56px;
      min-height: 56px;
      border-radius: 50%;
      align-self: center;
      display: flex;
      align-items: center;
      justify-content: center;
      /* Plastic: subtle top-lit gradient + elevation, pressed on :active.
         The gradient doubles as contrast: at the icon's (center) position
         the orange is lightened enough for APCA (pure accent would sit at
         Lc ~44, just under the 45 threshold — Strava orange's ceiling). */
      background: linear-gradient(
        180deg,
        color-mix(in oklab, var(--accent), rgb(252, 250, 250) 14%),
        var(--accent)
      );
      box-shadow: var(--elev-1);
      color: var(--bg); /* dark on orange: white fails WCAG AA */
      transition: transform 0.12s, box-shadow 0.12s, filter 0.12s;
    }
    .tabbar .plus:hover { filter: brightness(1.08); }
    .tabbar .plus:active {
      transform: translateY(1px);
      box-shadow: var(--elev-1-pressed);
    }
    /* Keep content clear of the fixed bar */
    main { padding: 16px 16px calc(92px + env(safe-area-inset-bottom)); }
  }
</style>