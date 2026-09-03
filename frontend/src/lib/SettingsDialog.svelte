<script lang="ts">
  import { X } from "lucide-svelte";
  import SettingsProfile from "./SettingsProfile.svelte";
  import SettingsAnalysis from "./SettingsAnalysis.svelte";
  import SettingsBikes from "./SettingsBikes.svelte";
  import SettingsData from "./SettingsData.svelte";
  import { t } from "./i18n";

  export let open = false;

  function close() {
    open = false;
  }
</script>

{#if open}
  <div
    class="backdrop"
    on:click|self={close}
    on:keydown={(e) => e.key === "Escape" && close()}
    role="dialog"
    aria-modal="true"
    tabindex="-1"
  >
    <div class="modal" role="document">
      <header class="head">
        <h3>{$t("settings.title")}</h3>
        <button class="x" type="button" on:click={close} aria-label="Schließen"><X size={18} /></button>
      </header>
      <div class="body">
        <SettingsProfile />
        <SettingsAnalysis />
        <SettingsBikes />
        <SettingsData />
      </div>
      <footer class="actions">
        <button type="button" class="primary" on:click={close}>{$t("settings.done")}</button>
      </footer>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
  }
  .modal {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 22px 20px;
    width: min(520px, 94vw);
    max-height: 90vh;
    overflow: auto;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  }
  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .head h3 { margin: 0; }
  .x {
    background: transparent;
    border: none;
    color: var(--muted);
    font-size: 18px;
    cursor: pointer;
    padding: 4px 8px;
  }
  /* Sections are self-styled components; the flex gap spaces them. */
  .body {
    margin-top: 4px;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 18px;
  }
  .primary {
    background: var(--accent);
    color: var(--bg);
    font-weight: 600;
    border-color: var(--accent);
  }
  .primary:hover { filter: brightness(1.1); }
</style>