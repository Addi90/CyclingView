<script lang="ts">
  import { RefreshCw, Zap, Download, Upload } from "lucide-svelte";
  import { api } from "./api";
  import { t } from "./i18n";

  let ingestBusy = false;
  let ingestMsg = "";
  let importBusy = false;
  let importMsg = "";
  let importReplace = false;
  let recomputeBusy = false;
  let recomputeMsg = "";

  async function runStravaIngest() {
    ingestBusy = true;
    ingestMsg = "";
    try {
      const r = await api.ingestStrava();
      ingestMsg = $t("settings.strava_ingest_msg")
        .replace("{ingested}", String(r.ingested))
        .replace("{skipped}", String(r.skipped))
        .replace("{failed}", String(r.failed));
    } catch (e: any) {
      ingestMsg = $t("settings.error").replace("{message}", e?.message ?? String(e));
    } finally {
      ingestBusy = false;
    }
  }

  function downloadExport() {
    window.location.href = api.exportDataUrl();
  }

  async function onImportFile(e: Event) {
    const input = e.target as HTMLInputElement;
    const f = input.files?.[0];
    if (!f) return;
    if (importReplace && !confirm($t("settings.import_confirm"))) {
      input.value = "";
      return;
    }
    importBusy = true;
    importMsg = "";
    try {
      const r = await api.importData(f, importReplace);
      importMsg = $t("settings.import_success").replace("{extracted}", String(r.extracted));
    } catch (err: any) {
      importMsg = $t("settings.error").replace("{message}", err?.message ?? String(err));
    } finally {
      importBusy = false;
      input.value = "";
    }
  }

  async function recomputePowerBests() {
    recomputeBusy = true;
    recomputeMsg = "";
    try {
      const r = await api.powerBestsRecompute(true);
      recomputeMsg = $t("settings.recompute_power_msg")
        .replace("{processed}", String(r.processed))
        .replace("{failed}", String(r.failed));
    } catch (e: any) {
      recomputeMsg = $t("settings.error").replace("{message}", e?.message ?? String(e));
    } finally {
      recomputeBusy = false;
    }
  }
</script>

<section>
  <h4>{$t("settings.data")}</h4>

  <div class="row">
    <button type="button" on:click={runStravaIngest} disabled={ingestBusy} class="wide">
      {#if ingestBusy}{$t("settings.strava_ingest_busy")}{:else}<RefreshCw size={16} /> {$t("settings.strava_ingest")}{/if}
    </button>
    {#if ingestMsg}<small class="status">{ingestMsg}</small>{/if}
  </div>

  <div class="row">
    <button type="button" on:click={recomputePowerBests} disabled={recomputeBusy} class="wide">
      {#if recomputeBusy}{$t("settings.recompute_power_busy")}{:else}<Zap size={16} /> {$t("settings.recompute_power")}{/if}
    </button>
    {#if recomputeMsg}<small class="status">{recomputeMsg}</small>{/if}
  </div>

  <div class="row">
    <button type="button" on:click={downloadExport} class="wide">
      <Download size={16} /> {$t("settings.export")}
    </button>
  </div>

  <div class="row">
    <label class="file-import wide">
      {#if importBusy}
        <span>{$t("settings.import_busy")}</span>
      {:else}
        <span><Upload size={16} /> {$t("settings.import")}</span>
      {/if}
      <input type="file" accept=".zip,application/zip" on:change={onImportFile} disabled={importBusy} />
    </label>
    <label class="inline tight">
      <input type="checkbox" bind:checked={importReplace} />
      <small>{$t("settings.import_replace")}</small>
    </label>
    {#if importMsg}<small class="status">{importMsg}</small>{/if}
  </div>
</section>

<style>
  h4 {
    margin: 0 0 8px;
    font-size: 12px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 10px;
    flex-wrap: wrap;
  }
  .wide { width: 100%; text-align: left; display: inline-flex; align-items: center; gap: 8px; }
  .file-import {
    display: inline-flex;
    align-items: center;
    width: 100%;
    padding: 6px 10px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--bg);
    cursor: pointer;
    font-size: 13px;
    box-sizing: border-box;
  }
  .file-import span { display: inline-flex; align-items: center; gap: 8px; }
  .file-import input { display: none; }
  .file-import:hover { background: color-mix(in oklab, var(--bg), rgb(255, 255, 255) 5%); }
  .status { display: block; color: var(--muted); margin-top: 4px; width: 100%; }
  .inline { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; }
  .inline.tight { margin-left: 4px; }
</style>