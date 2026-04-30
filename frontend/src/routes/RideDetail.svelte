<script lang="ts">
  import { onMount } from "svelte";
  import { navigate } from "svelte-routing";
  import { Pencil, Trash2, Bike as BikeIcon } from "lucide-svelte";
  import { api, type Ride, type StreamsResponse, type StreamField, type Bike } from "../lib/api";
  import { fmtKm, fmtKmh, fmtDuration, fmtNum, fmtDate } from "../lib/format";
  import StreamChart from "../lib/charts/StreamChart.svelte";
  import RouteMap from "../lib/RouteMap.svelte";
  import PowerBestsTable from "../lib/PowerBestsTable.svelte";
  import {
    settings,
    applyStreamFilter,
    buildPauseMask,
    mean,
    maxOf,
    minOf,
    normalizedPower,
    kcalFromPower,
    kcalFromHR,
  } from "../lib/settings";

  export let id: string;

  let ride: Ride | null = null;
  let streams: StreamsResponse | null = null;
  let bikes: Bike[] = [];
  let error = "";

  // Edit state
  const ACTIVITY_TYPES = ["Ride", "Gravel Ride", "Mountain Bike Ride", "Virtual Ride", "E-Bike Ride"];
  let editing = false;
  let editName = "";
  let editType = "";
  let editBikeId: number | "" = "";
  let saveBusy = false;
  let saveErr = "";

  function beginEdit() {
    if (!ride) return;
    editName = ride.name ?? "";
    editType = ride.type ?? "Ride";
    editBikeId = ride.bike_id ?? "";
    saveErr = "";
    editing = true;
  }

  async function saveEdit() {
    if (!ride) return;
    saveBusy = true;
    saveErr = "";
    try {
      ride = await api.updateRide(ride.id, {
        name: editName.trim() || null,
        type: editType || null,
        bike_id: editBikeId === "" ? null : Number(editBikeId),
      });
      editing = false;
    } catch (e: any) {
      saveErr = e?.message ?? String(e);
    } finally {
      saveBusy = false;
    }
  }

  async function deleteRide() {
    if (!ride) return;
    if (!confirm(`Fahrt „${ride.name ?? ride.id}“ wirklich löschen? Dies kann nicht rückgängig gemacht werden.`)) return;
    try {
      await api.deleteRide(ride.id);
      navigate("/", { replace: true });
    } catch (e: any) {
      error = e?.message ?? String(e);
    }
  }

  async function load() {
    error = "";
    try {
      ride = await api.ride(id);
      const fields: StreamField[] = ["power", "heart_rate", "speed", "altitude", "cadence", "temperature"];
      // n_points = 0 -> backend returns every recorded sample (typically 1 Hz).
      streams = await api.streams(id, fields, 0);
      bikes = await api.bikes();
    } catch (e: any) {
      error = e.message ?? String(e);
    }
  }

  onMount(load);

  // Raw series
  $: t = streams?.t ?? [];
  $: powerRaw = (streams?.power ?? []) as (number | null)[];
  $: hrRaw = (streams?.heart_rate ?? []) as (number | null)[];
  $: speedRawMs = (streams?.speed ?? []) as (number | null)[];
  $: altitudeRaw = (streams?.altitude ?? []) as (number | null)[];
  $: cadenceRaw = (streams?.cadence ?? []) as (number | null)[];
  $: temperatureRaw = (streams?.temperature ?? []) as (number | null)[];

  // Pause mask derived from raw speed (seconds).
  $: pauseMask = $settings.hidePauses && speedRawMs.length
    ? buildPauseMask(speedRawMs, t, $settings.pauseThresholdS, $settings.pauseSpeedMs)
    : undefined;

  // Filtered series for charts + recomputed stats.
  $: power = applyStreamFilter(powerRaw, t, {
    excludeZero: $settings.excludeZeroPower,
    pauseMask,
  });
  $: hr = applyStreamFilter(hrRaw, t, { pauseMask });
  $: speedMs = applyStreamFilter(speedRawMs, t, { pauseMask });
  $: speedKmh = speedMs.map((v) => (v == null ? null : v * 3.6));
  $: altitude = applyStreamFilter(altitudeRaw, t, { pauseMask });
  $: cadence = applyStreamFilter(cadenceRaw, t, {
    excludeZero: $settings.excludeZeroCadence,
    pauseMask,
  });
  $: temperature = applyStreamFilter(temperatureRaw, t, { pauseMask });

  // Live stats from filtered streams.
  $: powerStats = { avg: mean(power), max: maxOf(power), np: normalizedPower(power, t) };
  $: hrStats = { avg: mean(hr), max: maxOf(hr), min: minOf(hr) };
  $: speedStats = { avg: mean(speedMs), max: maxOf(speedMs) };
  $: cadStats = { avg: mean(cadence), max: maxOf(cadence) };
  $: tempStats = { avg: mean(temperature), max: maxOf(temperature), min: minOf(temperature) };
  $: hasTemp = tempStats.avg != null;

  // Calorie estimate. Prefer power-based (more accurate); fallback to HR (Keytel 2005).
  $: kcalPower = ride?.has_power ? kcalFromPower(powerRaw, t) : null;
  $: kcalHR = (kcalPower == null && ride?.has_hr)
    ? kcalFromHR(hrRaw, t, $settings.weightKg, $settings.ageYears, $settings.sex)
    : null;
  $: kcal = kcalPower ?? kcalHR;
  $: kcalSource = kcalPower != null ? "Power" : (kcalHR != null ? "HR·Keytel" : null);

  $: syncKey = `ride-${id}`;

  function hasAny(arr: (number | null)[]): boolean {
    return arr.some((v) => v != null);
  }
</script>

<a href="/" on:click|preventDefault={() => history.back()}>← Zurück</a>

{#if error}<div class="error">{error}</div>{/if}

{#if ride}
  <header class="ride-header">
    {#if editing}
      <div class="edit-form">
        <label class="row">
          <span>Name</span>
          <input type="text" bind:value={editName} placeholder="Fahrtname" />
        </label>
        <label class="row">
          <span>Typ</span>
          <select bind:value={editType}>
            {#each ACTIVITY_TYPES as t}<option value={t}>{t}</option>{/each}
          </select>
        </label>
        <label class="row">
          <span>Rad</span>
          <select bind:value={editBikeId}>
            <option value="">– keines –</option>
            {#each bikes as b}<option value={b.id}>{b.name}</option>{/each}
          </select>
        </label>
        {#if saveErr}<div class="error inline">{saveErr}</div>{/if}
        <div class="edit-actions">
          <button type="button" on:click={() => (editing = false)} disabled={saveBusy}>Abbrechen</button>
          <button type="button" class="primary" on:click={saveEdit} disabled={saveBusy}>
            {saveBusy ? "Speichere…" : "Speichern"}
          </button>
        </div>
      </div>
    {:else}
      <div class="title-row">
        <h2>{ride.name ?? "Fahrt"}</h2>
        <div class="head-actions">
          <button type="button" on:click={beginEdit} title="Bearbeiten"><Pencil size={14} /> Bearbeiten</button>
          <button type="button" class="danger" on:click={deleteRide} title="Löschen"><Trash2 size={14} /> Löschen</button>
        </div>
      </div>
      <div class="meta">
        <span>{fmtDate(ride.start_time)}</span>
        {#if ride.bike_name}<span class="bike-meta">· <BikeIcon size={14} /> {ride.bike_name}</span>{/if}
        {#if ride.type}<span>· {ride.type}</span>{/if}
      </div>
    {/if}
  </header>

  <div class="cards">
    <div class="card">
      <div class="card-title">Distanz</div>
      <div class="card-value">{fmtKm(ride.distance_m)}</div>
      <div class="card-sub">Höhenmeter: {fmtNum(ride.elevation_gain_m, 0, " m")}</div>
    </div>
    <div class="card">
      <div class="card-title">Dauer</div>
      <div class="card-value">{fmtDuration(ride.moving_s)}</div>
      <div class="card-sub">Gesamt: {fmtDuration(ride.elapsed_s)}</div>
    </div>
    <div class="card">
      <div class="card-title">Speed</div>
      <div class="card-value">⌀ {fmtKmh(speedStats.avg ?? ride.avg_speed_ms)}</div>
      <div class="card-sub">max {fmtKmh(speedStats.max ?? ride.max_speed_ms)}</div>
    </div>
    {#if ride.has_power}
      <div class="card power">
        <div class="card-title">Power</div>
        <div class="card-value">⌀ {fmtNum(powerStats.avg ?? ride.avg_power, 0, " W")}</div>
        <div class="card-sub">
          NP {fmtNum(powerStats.np ?? ride.np_power, 0, " W")} · max {fmtNum(powerStats.max ?? ride.max_power, 0, " W")}
        </div>
      </div>
    {/if}
    {#if ride.has_hr}
      <div class="card hr">
        <div class="card-title">Herzfrequenz</div>
        <div class="card-value">⌀ {fmtNum(hrStats.avg ?? ride.avg_hr, 0, " bpm")}</div>
        <div class="card-sub">
          min {fmtNum(hrStats.min, 0, " bpm")} · max {fmtNum(hrStats.max ?? ride.max_hr, 0, " bpm")}
        </div>
      </div>
    {/if}
    {#if ride.has_cadence}
      <div class="card cad">
        <div class="card-title">Trittfrequenz</div>
        <div class="card-value">⌀ {fmtNum(cadStats.avg ?? ride.avg_cadence, 0, " rpm")}</div>
        <div class="card-sub">max {fmtNum(cadStats.max ?? ride.max_cadence, 0, " rpm")}</div>
      </div>
    {/if}
    {#if hasTemp}
      <div class="card temp">
        <div class="card-title">Temperatur</div>
        <div class="card-value">⌀ {fmtNum(tempStats.avg, 1, " °C")}</div>
        <div class="card-sub">
          min {fmtNum(tempStats.min, 1, " °C")} · max {fmtNum(tempStats.max, 1, " °C")}
        </div>
      </div>
    {/if}
    {#if kcal != null}
      <div class="card kcal">
        <div class="card-title">Kalorien</div>
        <div class="card-value">{fmtNum(kcal, 0, " kcal")}</div>
        <div class="card-sub">{kcalSource === "Power" ? "aus Power (η = 0,24)" : "aus HR (Keytel 2005)"}</div>
      </div>
    {/if}
  </div>

  <section class="map-row" class:has-bests={ride.has_power}>
    <div class="map-block">
      <RouteMap activityId={ride.id} hasGeo={ride.has_geo === 1} />
    </div>
    {#if ride.has_power}
      <aside class="bests-side">
        <PowerBestsTable activityId={ride.id} title="Power-Bestwerte" />
      </aside>
    {/if}
  </section>

  {#if streams}
    <div class="charts">
      {#if hasAny(altitude)}
        <StreamChart label="Höhe" unit="m" color="#fc5200" xs={t} ys={altitude} {syncKey} />
      {/if}
      {#if hasAny(speedKmh)}
        <StreamChart label="Geschwindigkeit" unit="km/h" color="#fc5200" xs={t} ys={speedKmh} {syncKey} valueDigits={1} />
      {/if}
      {#if hasAny(power)}
        <StreamChart label="Power" unit="W" color="#fc5200" xs={t} ys={power} {syncKey} />
      {/if}
      {#if hasAny(hr)}
        <StreamChart label="Herzfrequenz" unit="bpm" color="#fc5200" xs={t} ys={hr} {syncKey} />
      {/if}
      {#if hasAny(cadence)}
        <StreamChart label="Trittfrequenz" unit="rpm" color="#fc5200" xs={t} ys={cadence} {syncKey} />
      {/if}
      {#if hasAny(temperature)}
        <StreamChart label="Temperatur" unit="°C" color="#fc5200" xs={t} ys={temperature} {syncKey} valueDigits={1} />
      {/if}
    </div>
  {/if}
{:else if !error}
  <p class="muted">Lade…</p>
{/if}

<style>
  .ride-header { margin-top: 12px; }
  .ride-header h2 { margin: 0 0 4px; }
  .title-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .title-row h2 { flex: 1; }
  .head-actions { display: flex; gap: 8px; }
  .head-actions button { display: inline-flex; align-items: center; gap: 6px; }
  .head-actions .danger { color: #ef4444; border-color: #ef4444; }
  .head-actions .danger:hover { background: rgba(239, 68, 68, 0.1); }
  .edit-form {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 14px;
    display: grid;
    gap: 8px;
    max-width: 480px;
  }
  .edit-form .row { display: grid; grid-template-columns: 70px 1fr; gap: 8px; align-items: center; font-size: 13px; }
  .edit-form .row span { color: var(--muted); }
  .edit-form input, .edit-form select { width: 100%; box-sizing: border-box; }
  .edit-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px; }
  .edit-actions .primary { background: var(--accent); color: white; border-color: var(--accent); }
  .error.inline { margin: 0; font-size: 12px; }
  .meta { color: var(--muted); font-size: 14px; }
  .meta .bike-meta { display: inline-flex; align-items: center; gap: 4px; }
  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 12px;
    margin: 16px 0;
  }
  .card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 14px;
  }
  .card.power { border-left: 3px solid var(--power); }
  .card.hr    { border-left: 3px solid var(--hr); }
  .card.cad   { border-left: 3px solid var(--cad); }
  .card-title { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }
  .card-value { font-size: 22px; font-weight: 600; margin-top: 4px; }
  .card-sub   { font-size: 12px; color: var(--muted); margin-top: 2px; }
  .charts { display: flex; flex-direction: column; gap: 18px; margin-top: 24px; }
  .map-row {
    margin-top: 24px;
    display: grid;
    grid-template-columns: 1fr;
    gap: 16px;
    align-items: stretch;
  }
  .map-row.has-bests {
    grid-template-columns: minmax(0, 1fr) 280px;
  }
  .map-block { display: flex; flex-direction: column; }
  .map-block h3 { margin: 0 0 8px; }
  .map-block :global(.map-wrap) {
    flex: 1;
    display: flex;
    flex-direction: column;
  }
  .map-block :global(.map) { flex: 1; min-height: 480px; }
  .bests-side { min-width: 0; display: flex; }
  .bests-side :global(.bests) {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .bests-side :global(.bests table) { flex: 1; }
  @media (max-width: 900px) {
    .map-row.has-bests { grid-template-columns: 1fr; }
  }
  .muted { color: var(--muted); }
  .error { color: #ef4444; padding: 8px; border: 1px solid #ef4444; border-radius: 6px; margin: 8px 0; }
</style>
