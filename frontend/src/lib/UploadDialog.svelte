<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import { api, type Bike } from "./api";

  export let open = false;
  export let bikes: Bike[] = [];

  const dispatch = createEventDispatcher<{ uploaded: { activity_id: number } }>();

  const ACTIVITY_TYPES = ["Ride", "Gravel Ride", "Mountain Bike Ride", "Virtual Ride", "E-Bike Ride"];

  let file: File | null = null;
  let name = "";
  let bikeId: number | "" = "";
  let activityType = "Ride";
  let description = "";
  let busy = false;
  let error = "";

  function reset() {
    file = null;
    name = "";
    bikeId = "";
    activityType = "Ride";
    description = "";
    error = "";
    busy = false;
  }

  function close() {
    open = false;
    reset();
  }

  function onFile(e: Event) {
    const input = e.target as HTMLInputElement;
    file = input.files?.[0] ?? null;
    if (file && !name) name = file.name.replace(/\.(fit|tcx|gpx)(\.gz)?$/i, "");
  }

  async function submit() {
    if (!file) {
      error = "Bitte eine Datei auswählen.";
      return;
    }
    busy = true;
    error = "";
    try {
      const res = await api.uploadRide(file, {
        name: name || undefined,
        bike_id: bikeId === "" ? null : Number(bikeId),
        activity_type: activityType,
        description: description || undefined,
      });
      dispatch("uploaded", res);
      close();
    } catch (e: any) {
      error = e?.message ?? String(e);
    } finally {
      busy = false;
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
      <h3>Fahrt hochladen</h3>

      <label class="field">
        <span>Datei (.fit, .tcx, .gpx, optional .gz)</span>
        <input type="file" accept=".fit,.tcx,.gpx,.gz,application/gzip" on:change={onFile} />
      </label>

      <label class="field">
        <span>Name</span>
        <input type="text" bind:value={name} placeholder="z. B. Feierabendrunde" />
      </label>

      <label class="field">
        <span>Rad</span>
        <select bind:value={bikeId}>
          <option value="">– keines –</option>
          {#each bikes as b}
            <option value={b.id}>{b.name}</option>
          {/each}
        </select>
      </label>

      <label class="field">
        <span>Aktivitätstyp</span>
        <select bind:value={activityType}>
          {#each ACTIVITY_TYPES as t}
            <option value={t}>{t}</option>
          {/each}
        </select>
      </label>

      <label class="field">
        <span>Beschreibung / Tags</span>
        <textarea rows="3" bind:value={description} placeholder="optional"></textarea>
      </label>

      {#if error}<div class="error">{error}</div>{/if}

      <div class="actions">
        <button type="button" on:click={close} disabled={busy}>Abbrechen</button>
        <button type="button" class="primary" on:click={submit} disabled={busy || !file}>
          {busy ? "Lade hoch …" : "Hochladen"}
        </button>
      </div>
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
    padding: 20px 22px;
    width: min(440px, 92vw);
    max-height: 90vh;
    overflow: auto;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  }
  .modal h3 { margin-top: 0; }
  .field {
    display: block;
    margin-bottom: 12px;
    font-size: 13px;
    color: var(--muted);
  }
  .field span { display: block; margin-bottom: 4px; }
  .field input[type="text"],
  .field input[type="file"],
  .field select,
  .field textarea {
    width: 100%;
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 16px;
  }
  .primary {
    background: var(--accent);
    color: white;
    border-color: var(--accent);
  }
  .primary:hover { filter: brightness(1.1); }
  .primary:disabled { opacity: 0.5; cursor: not-allowed; }
  .error {
    color: #ef4444;
    background: rgba(239, 68, 68, 0.1);
    padding: 8px;
    border-radius: 6px;
    font-size: 13px;
    margin-top: 8px;
  }
</style>
