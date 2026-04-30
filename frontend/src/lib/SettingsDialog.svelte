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
      ingestMsg = `+${r.ingested} neu · ${r.skipped} übersprungen · ${r.failed} Fehler`;
    } catch (e: any) {
      ingestMsg = `Fehler: ${e?.message ?? e}`;
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
    if (importReplace && !confirm("Wirklich vorhandene Daten überschreiben? Diese Aktion ist nicht rückgängig.")) {
      input.value = "";
      return;
    }
    importBusy = true;
    importMsg = "";
    try {
      const r = await api.importData(f, importReplace);
      importMsg = `${r.extracted} Dateien importiert. Bitte Seite neu laden.`;
    } catch (err: any) {
      importMsg = `Fehler: ${err?.message ?? err}`;
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
      bikesError = e?.message ?? String(e);
    } finally {
      bikeBusy = false;
    }
  }

  async function removeBike(b: Bike) {
    if (!confirm(`Rad „${b.name}" wirklich löschen?`)) return;
    bikesError = "";
    try {
      await api.deleteBike(b.id);
      await loadBikes();
    } catch (e: any) {
      bikesError = e?.message ?? String(e);
    }
  }

  async function recomputePowerBests() {
    recomputeBusy = true;
    recomputeMsg = "";
    try {
      const r = await api.powerBestsRecompute(true);
      recomputeMsg = `${r.processed} verarbeitet · ${r.failed} Fehler`;
    } catch (e: any) {
      recomputeMsg = `Fehler: ${e?.message ?? e}`;
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
        <h3>Einstellungen</h3>
        <button class="x" type="button" on:click={close} aria-label="Schließen"><X size={18} /></button>
      </header>

      <section>
        <h4>Profil</h4>
        <label class="row inline">
          Körpergewicht
          <input type="number" min="20" max="200" step="0.1" bind:value={$settings.weightKg} />
          kg
        </label>
        <label class="row inline">
          Alter
          <input type="number" min="10" max="120" step="1" bind:value={$settings.ageYears} />
          Jahre
        </label>
        <label class="row inline">
          Geschlecht
          <select bind:value={$settings.sex}>
            <option value="male">männlich</option>
            <option value="female">weiblich</option>
          </select>
        </label>
        <label class="row inline">
          Power-Anzeige
          <select bind:value={$settings.powerUnit}>
            <option value="W">Watt (W)</option>
            <option value="W/kg">W pro kg</option>
          </select>
        </label>
      </section>

      <section>
        <h4>Auswertung</h4>

        <label class="row">
          <input type="checkbox" bind:checked={$settings.excludeZeroPower} />
          <span>
            <strong>Power: 0 W ausblenden</strong>
            <small>Rollphasen aus Charts und Mittelwerten entfernen.</small>
          </span>
        </label>

        <label class="row">
          <input type="checkbox" bind:checked={$settings.excludeZeroCadence} />
          <span>
            <strong>Trittfrequenz: 0 rpm ausblenden</strong>
            <small>Rollen / Stillstand nicht in Cadence-Statistik.</small>
          </span>
        </label>

        <label class="row">
          <input type="checkbox" bind:checked={$settings.hidePauses} />
          <span>
            <strong>Fahrtpausen ausblenden</strong>
            <small>Phasen mit Geschwindigkeit ≈ 0 aus Charts entfernen.</small>
          </span>
        </label>

        {#if $settings.hidePauses}
          <div class="sub">
            <label class="inline">
              Pause ab
              <input type="number" min="1" max="120" step="1" bind:value={$settings.pauseThresholdS} />
              Sekunden
            </label>
            <label class="inline">
              Schwelle
              <input type="number" min="0" max="3" step="0.1" bind:value={$settings.pauseSpeedMs} />
              m/s
            </label>
          </div>
        {/if}
      </section>

      <!-- <section>
        <h4>Darstellung</h4>
        <label class="row inline">
          Einheiten
          <select bind:value={$settings.units}>
            <option value="metric">Metrisch (km, km/h, m)</option>
            <option value="imperial">Imperial (mi, mph, ft)</option>
          </select>
        </label>
        <label class="row inline">
          Theme
          <select bind:value={$settings.theme}>
            <option value="dark">Dunkel</option>
            <option value="light">Hell</option>
            <option value="system">System</option>
          </select>
        </label>
      </section> -->

      <section>
        <h4>Räder</h4>
        {#if bikesError}<small class="status error-text">{bikesError}</small>{/if}
        {#if bikes.length}
          <ul class="bike-list">
            {#each bikes as b}
              <li>
                <span class="bname">{b.name}</span>
                {#if b.brand || b.model}
                  <small class="dim">{[b.brand, b.model].filter(Boolean).join(" ")}</small>
                {/if}
                <button type="button" class="del" on:click={() => removeBike(b)} title="Löschen"><Trash2 size={14} /></button>
              </li>
            {/each}
          </ul>
        {/if}
        <div class="add-bike">
          <input type="text" placeholder="Name *" bind:value={newBike.name} />
          <input type="text" placeholder="Marke" bind:value={newBike.brand} />
          <input type="text" placeholder="Modell" bind:value={newBike.model} />
          <button type="button" on:click={addBike} disabled={bikeBusy || !newBike.name.trim()}>
            <Plus size={16} /> Rad hinzufügen
          </button>
        </div>
      </section>

      <section>
        <h4>Daten</h4>

        <div class="row">
          <button type="button" on:click={runStravaIngest} disabled={ingestBusy} class="wide">
            {#if ingestBusy}Ingestiere…{:else}<RefreshCw size={16} /> Strava-Export ingestieren{/if}
          </button>
          {#if ingestMsg}<small class="status">{ingestMsg}</small>{/if}
        </div>

        <div class="row">
          <button type="button" on:click={recomputePowerBests} disabled={recomputeBusy} class="wide">
            {#if recomputeBusy}Berechne…{:else}<Zap size={16} /> Power-Bestwerte neu berechnen{/if}
          </button>
          {#if recomputeMsg}<small class="status">{recomputeMsg}</small>{/if}
        </div>

        <div class="row">
          <button type="button" on:click={downloadExport} class="wide"><Download size={16} /> Daten exportieren (.zip)</button>
        </div>

        <div class="row">
          <label class="file-import wide">
            {#if importBusy}
              <span>Importiere…</span>
            {:else}
              <span><Upload size={16} /> Daten importieren</span>
            {/if}
            <input type="file" accept=".zip,application/zip" on:change={onImportFile} disabled={importBusy} />
          </label>
          <label class="inline tight">
            <input type="checkbox" bind:checked={importReplace} />
            <small>vorher löschen (Reset)</small>
          </label>
          {#if importMsg}<small class="status">{importMsg}</small>{/if}
        </div>
      </section>

      <footer class="actions">
        <button type="button" class="primary" on:click={close}>Fertig</button>
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
  .row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 10px;
    flex-wrap: wrap;
  }
  .row.inline { align-items: center; }
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
    color: white;
    border-color: var(--accent);
  }
  .primary:hover { filter: brightness(1.1); }
</style>
