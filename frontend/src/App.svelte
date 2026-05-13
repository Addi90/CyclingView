<script lang="ts">
  import { Router, Route, Link } from "svelte-routing";
  import { Settings as SettingsIcon } from "lucide-svelte";
    import { Bike } from "lucide-svelte";
  import RidesList from "./routes/RidesList.svelte";
  import RideDetail from "./routes/RideDetail.svelte";
  import SettingsDialog from "./lib/SettingsDialog.svelte";
  import { t } from "./lib/i18n";

  export let url = "";

  let settingsOpen = false;
</script>

<Router {url}>
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
</style>