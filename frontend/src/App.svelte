<script lang="ts">
  import { Router, Route, Link, navigate } from "svelte-routing";
  import { Settings as SettingsIcon, List } from "lucide-svelte";
    import { Bike } from "lucide-svelte";
  import RidesList from "./routes/RidesList.svelte";
  import RideDetail from "./routes/RideDetail.svelte";
  import SettingsDialog from "./lib/SettingsDialog.svelte";
  import { t } from "./lib/i18n";

  export let url = "";

  let settingsOpen = false;
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
  <!-- Mobile bottom tab bar: the app has exactly two screens, so two tabs.
       Rides doubles as the back escape hatch (no scroll-to-top needed);
       Settings replaces the header cog, unreachable at the bottom of a
       long ride page. Hidden ≥769px. -->
  <nav class="tabbar" aria-label="Main navigation">
    <button
      type="button"
      class:active={!location.pathname.startsWith("/rides/")}
      on:click={() => navigate("/")}
    >
      <List size={20} /><span>{$t("rides.title")}</span>
    </button>
    <button type="button" on:click={() => (settingsOpen = true)}>
      <SettingsIcon size={20} /><span>{$t("settings.title")}</span>
    </button>
  </nav>
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
  @media (max-width: 768px) {
    .tabbar {
      display: grid;
      grid-template-columns: 1fr 1fr;
      position: fixed;
      left: 0;
      right: 0;
      bottom: 0;
      z-index: 30;
      background: var(--panel);
      border-top: 1px solid var(--border);
      padding-bottom: env(safe-area-inset-bottom); /* iPhone home indicator */
    }
    .tabbar button {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 2px;
      min-height: 56px;
      background: transparent;
      border: 0;
      color: var(--muted);
      font-size: 11px;
      cursor: pointer;
    }
    .tabbar button:active { opacity: 0.7; }
    .tabbar button.active { color: var(--accent); }
    /* Keep content clear of the fixed bar */
    main { padding: 16px 16px calc(76px + env(safe-area-inset-bottom)); }
  }
</style>