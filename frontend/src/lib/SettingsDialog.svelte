<script lang="ts">
  import { onMount } from "svelte";
  import {
    X,
    Plus,
    RefreshCw,
    Zap,
    Download,
    Upload,
    Trash2,
  } from "lucide-svelte";
  import { settings } from "./settings";
  import { api, type Bike } from "./api";
  import { t } from "./i18n";

  export let open = false;

  let ingestBusy = false;
  let ingestMsg = "";
  let importBusy = false;
  let importMsg = "";
  let importReplace = false;

  let bikes: Bike[] = [];
  let bikesError = "";
  let newBike = { name: "", brand: "", model: "" };
  let bikeBusy = false;
  let recomputeBusy = false;
  let recomputeMsg = "";

  async function loadBikes() {
    try {
      bikes = await api.bikes();
    } catch (e: any) {
      bikesError = e?.message ?? String(e);
    }
  }

  $: if (open) loadBikes();
  onMount(loadBikes);

  function close() {
    open = false;
  }

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

  async function addBike() {
    if (!newBike.name.trim()) return;
    bikeBusy = true;
    bikesError = "";
    try {
      await api.createBike({
        name: newBike.name.trim(),
        brand: newBike.brand.trim() || undefined,
        model: newBike.model.trim() || undefined,
      });
      newBike = { name: "", brand: "", model: "" };
      await loadBikes();
    } catch (e: any) {
      bikesError = $t("settings.error").replace("{message}", e?.message ?? String(e));
    } finally {
      bikeBusy = false;
    }
  }

  async function removeBike(b: Bike) {
    if (!confirm($t("settings.bike.delete_confirm").replace("{name}", b.name))) return;
    bikesError = "";
    try {
      await api.deleteBike(b.id);
      await loadBikes();
    } catch (e: any) {
      bikesError = $t("settings.error").replace("{message}", e?.message ?? String(e));
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

      <section>
        <h4>{$t("settings.profile")}</h4>
        <div class="field">
          <label>{$t("settings.language")}</label>
          <div class="field-input">
            <select bind:value={$settings.language}>
              <option value="de">Deutsch</option>
              <option value="en">English</option>
            </select>
            <span class="unit"></span>
          </div>
        </div>
        <div class="field">
          <label>{$t("settings.weight")}</label>
          <div class="field-input">
            <input type="number" min="20" max="200" step="0.1" bind:value={$settings.weightKg} />
            <span class="unit">kg</span>
          </div>
        </div>
        <div class="field">
          <label>{$t("settings.age")}</label>
          <div class="field-input">
            <input type="number" min="10" max="120" step="1" bind:value={$settings.ageYears} />
            <span class="unit">{$t("settings.years")}</span>
          </div>
        </div>
        <div class="field">
          <label>{$t("settings.sex")}</label>
          <div class="field-input">
            <select bind:value={$settings.sex}>
              <option value="male">{$t("settings.sex.male")}</option>
              <option value="female">{$t("settings.sex.female")}</option>
            </select>
            <span class="unit"></span>
          </div>
        </div>
        <div class="field">
          <label>{$t("settings.maxHR")}</label>
          <div class="field-input">
            <input type="number" min="60" max="250" step="1" bind:value={$settings.maxHR} placeholder="z. B. 190" />
            <span class="unit">{$t("settings.bpm")}</span>
          </div>
        </div>
        <div class="field">
          <label>{$t("settings.powerDisplay")}</label>
          <div class="field-input">
            <select bind:value={$settings.powerUnit}>
              <option value="W">Watt (W)</option>
              <option value="W/kg">W pro kg</option>
            </select>
            <span class="unit"></span>
          </div>
        </div>
      </section>

      <section>
        <h4>{$t("settings.analysis")}</h4>

        <label class="row">
          <input type="checkbox" bind:checked={$settings.excludeZeroPower} />
          <span>
            <strong>{$t("settings.exclude_zero_power")}</strong>
            <small>{$t("settings.exclude_zero_power_hint")}</small>
          </span>
        </label>

        <label class="row">
          <input type="checkbox" bind:checked={$settings.excludeZeroCadence} />
          <span>
            <strong>{$t("settings.exclude_zero_cadence")}</strong>
            <small>{$t("settings.exclude_zero_cadence_hint")}</small>
          </span>
        </label>

        <label class="row">
          <input type="checkbox" bind:checked={$settings.hidePauses} />
          <span>
            <strong>{$t("settings.hide_pauses")}</strong>
            <small>{$t("settings.hide_pauses_hint")}</small>
          </span>
        </label>

        {#if $settings.hidePauses}
          <div class="sub">
            <label class="inline">
              {$t("settings.pause_threshold")}
              <input type="number" min="1" max="120" step="1" bind:value={$settings.pauseThresholdS} />
              {$t("settings.seconds")}
            </label>
            <label class="inline">
              {$t("settings.pause_speed")}
              <input type="number" min="0" max="3" step="0.1" bind:value={$settings.pauseSpeedMs} />
              m/s
            </label>
          </div>
        {/if}
      </section>

      <section>
        <h4>{$t("settings.bikes")}</h4>
        {#if bikesError}<small class="status error-text">{bikesError}</small>{/if}
        {#if bikes.length}
          <ul class="bike-list">
            {#each bikes as b}
              <li>
                <span class="bname">{b.name}</span>
                {#if b.brand || b.model}
                  <small class="dim">{[b.brand, b.model].filter(Boolean).join(" ")}</small>
                {/if}
                <button type="button" class="del" on:click={() => removeBike(b)} title={$t("ride.delete")}><Trash2 size={14} /></button>
              </li>
            {/each}
          </ul>
        {/if}
        <div class="add-bike">
          <input type="text" placeholder={$t("settings.bike.name")} bind:value={newBike.name} />
          <input type="text" placeholder={$t("settings.bike.brand")} bind:value={newBike.brand} />
          <input type="text" placeholder={$t("settings.bike.model")} bind:value={newBike.model} />
          <button type="button" on:click={addBike} disabled={bikeBusy || !newBike.name.trim()}>
            <Plus size={16} /> {$t("settings.bike.add")}
          </button>
        </div>
      </section>

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
          <button type="button" on:click={downloadExport} class="wide"><Download size={16} /> {$t("settings.export")}</button>
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
  .head { display: flex; align-items: center; justify-content: space-between; }
  .head h3 { margin: 0; }
  .x {
    background: transparent;
    border: none;
    color: var(--muted);
    font-size: 18px;
    cursor: pointer;
    padding: 4px 8px;
  }
  section { margin-top: 18px; }
  section h4 {
    margin: 0 0 8px;
    font-size: 12px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .field {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 6px 0;
    border-bottom: 1px solid var(--border);
  }
  .field:last-child { border-bottom: none; }
  .field label {
    font-size: 14px;
    flex-shrink: 0;
  }
  .field-input {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 190px;
    justify-content: flex-end;
  }
  .field-input input, .field-input select {
    flex: 1;
    min-width: 0;
    text-align: right;
    box-sizing: border-box;
  }
  .unit {
    width: 45px;
    flex-shrink: 0;
    color: var(--muted);
    font-size: 13px;
    text-align: left;
    white-space: nowrap;
  }
  .row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 10px;
    flex-wrap: wrap;
  }
  .row > span { display: flex; flex-direction: column; }
  .row > span strong { font-weight: 500; }
  .row > span small { color: var(--muted); font-size: 12px; }
  .sub {
    margin: -4px 0 12px 26px;
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
  }
  .inline {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
  }
  .inline.tight { margin-left: 4px; }
  .inline input[type="number"] { width: 60px; }
  .wide { width: 100%; text-align: left; display: inline-flex; align-items: center; gap: 8px; }
  .file-import {
    display: inline-flex;
    align-items: center;
    width: 100%;
    padding: 6px 10px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--bg, transparent);
    cursor: pointer;
    font-size: 13px;
    box-sizing: border-box;
  }
  .file-import span { display: inline-flex; align-items: center; gap: 8px; }
  .file-import input { display: none; }
  .file-import:hover { background: rgba(255, 255, 255, 0.04); }
  .status { display: block; color: var(--muted); margin-top: 4px; width: 100%; }
  .error-text { color: #ef4444; }
  .bike-list {
    list-style: none;
    padding: 0;
    margin: 0 0 8px;
  }
  .bike-list li {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    border-bottom: 1px solid var(--border);
    font-size: 13px;
  }
  .bike-list .bname { flex: 1; }
  .bike-list .dim { color: var(--muted); }
  .bike-list .del {
    background: transparent;
    border: none;
    color: var(--muted);
    cursor: pointer;
    padding: 2px 6px;
  }
  .bike-list .del:hover { color: #ef4444; }
  .add-bike {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
    margin-top: 4px;
  }
  .add-bike input { width: 100%; box-sizing: border-box; }
  .add-bike button { grid-column: 1 / -1; }
  .actions { display: flex; justify-content: flex-end; margin-top: 18px; }
  .primary {
    background: var(--accent);
    /* Dark text on the orange: white fails WCAG AA (3.3:1). */
    color: var(--bg);
    font-weight: 600;
    border-color: var(--accent);
  }
  .primary:hover { filter: brightness(1.1); }
</style>
