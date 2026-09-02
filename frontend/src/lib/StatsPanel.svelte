<script lang="ts">
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { api, type OverallStats } from "./api";
  import { fmtKm, fmtDuration, fmtNum, fmtDateShort } from "./format";
  import { t } from "./i18n";

  let stats: OverallStats | null = null;
  let error = "";
  /** Bump to force a re-fetch (e.g. after a ride upload). 0 = initial mount only. */
  export let reloadKey = 0;

  /** Year filter for the per-bike table. 0 = all-time (default). */
  let bikeYear = 0;
  let bikeYearLoaded = 0;
  let bikeOpen = true; // expanded per default
  let bikeLoading = false;

  async function load() {
    if (bikeYear !== 0) bikeLoading = true;
    try {
      stats = await api.stats(bikeYear || undefined);
      bikeYearLoaded = bikeYear;
    } catch (e: any) {
      error = e?.message ?? String(e);
    } finally {
      bikeLoading = false;
    }
  }

  onMount(load);
  $: if (reloadKey > 0) load();
  $: if (bikeYear !== bikeYearLoaded) load();
  $: if (bikeYear !== 0) bikeOpen = true;
</script>

{#if error}
  <p class="error">Stats: {error}</p>
{:else if !stats}
  <p class="muted small">{$t("stats.loading")}</p>
{:else}
  <h3>{$t("stats.alltime")}</h3>
  <dl class="stat-list">
    <dt>{$t("stats.rides")}</dt><dd>{stats.totals.rides}</dd>
    <dt>{$t("stats.distance")}</dt><dd>{fmtKm(stats.totals.distance_m, 0)}</dd>
    <dt>{$t("stats.duration")}</dt><dd>{fmtDuration(stats.totals.moving_s)}</dd>
    <dt>{$t("stats.elevation")}</dt><dd>{fmtNum(stats.totals.elevation_gain_m, 0, " m")}</dd>
  </dl>

  {#if stats.longest_distance}
    <p class="muted small">
      {$t("stats.longest.distance")}
      <Link to={`/rides/${stats.longest_distance.id}`}>
        {fmtKm(stats.longest_distance.distance_m, 1)}
      </Link>
      <br />
      <span class="dim">{fmtDateShort(stats.longest_distance.start_time)}</span>
    </p>
  {/if}
  {#if stats.longest_duration && stats.longest_duration.id !== stats.longest_distance?.id}
    <p class="muted small">
      {$t("stats.longest.duration")}
      <Link to={`/rides/${stats.longest_duration.id}`}>
        {fmtDuration(stats.longest_duration.moving_s)}
      </Link>
      <br />
      <span class="dim">{fmtDateShort(stats.longest_duration.start_time)}</span>
    </p>
  {/if}

  {#if stats.per_year.length}
    <details open>
      <summary>{$t("stats.per_year")}</summary>
      <table class="ystats">
        <thead><tr><th>{$t("stats.year")}</th><th>{$t("stats.rides")}</th><th>km</th><th>{$t("rides.col.duration")}</th></tr></thead>
        <tbody>
          {#each stats.per_year as y}
            <tr>
              <td>{y.year}</td>
              <td>{y.rides}</td>
              <td>{(y.distance_m / 1000).toFixed(0)}</td>
              <td>{fmtDuration(y.moving_s)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </details>
  {/if}

  {#if stats.per_bike.length}
    <details bind:open={bikeOpen}>
      <summary>
        <span>{$t("stats.per_bike")}</span>
        {#if stats.per_year.length}
          <select class="year-select" bind:value={bikeYear} aria-label={$t("stats.year")}>
            <option value={0}>{$t("stats.alltime")}</option>
            {#each stats.per_year as y}
              <option value={Number(y.year)}>{y.year}</option>
            {/each}
          </select>
        {/if}
      </summary>
      <table class="ystats" class:loading={bikeLoading}>
        <thead><tr><th>{$t("stats.bike")}</th><th>{$t("stats.rides")}</th><th>km</th></tr></thead>
        <tbody>
          {#each stats.per_bike as b}
            <tr>
              <td title={b.bike_name}>{b.bike_name}</td>
              <td>{b.rides}</td>
              <td>{(b.distance_m / 1000).toFixed(0)}</td>
            </tr>
          {/each}
          {#if stats.unassigned.rides > 0}
            <tr class="dim">
              <td>{$t("stats.unassigned")}</td>
              <td>{stats.unassigned.rides}</td>
              <td>{(stats.unassigned.distance_m / 1000).toFixed(0)}</td>
            </tr>
          {/if}
        </tbody>
      </table>
    </details>
  {/if}
{/if}

<style>
  h3 { margin: 0 0 8px; }
  .stat-list {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 4px 12px;
    margin: 0 0 12px;
    font-size: 13px;
  }
  .stat-list dt { color: var(--muted); }
  .stat-list dd { margin: 0; font-weight: 500; text-align: right; }
  .small { font-size: 12px; }
  .muted { color: var(--muted); margin: 6px 0; }
  .dim { color: var(--muted); font-size: 11px; }
  .error { color: #ef4444; font-size: 12px; }
  details { margin-top: 12px; }
  details summary {
    cursor: pointer;
    font-size: 13px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 6px;
    /* flex + custom ::before arrow: the native ::marker jumps to its own
       line as soon as the summary holds block-level children. */
    display: flex;
    align-items: center;
    gap: 8px;
    list-style: none;
  }
  details summary::-webkit-details-marker { display: none; }
  details summary::before {
    content: "▸";
    flex: none;
    font-size: 11px;
    transition: transform 0.12s;
  }
  details[open] > summary::before { transform: rotate(90deg); }
  .year-select {
    margin-left: auto; /* push to the right edge of the summary */
    font-size: 11px;
    font-family: inherit;
    color: var(--text);
    background: var(--panel-2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 2px 6px;
    min-height: 24px;
    text-transform: none;
    letter-spacing: normal;
  }
  table.ystats.loading th, table.ystats.loading td { opacity: 0.4; }
  table.ystats {
    width: 100%;
    font-size: 12px;
    border-collapse: collapse;
  }
  table.ystats th, table.ystats td {
    text-align: right;
    padding: 2px 4px;
    border-bottom: 1px solid var(--border);
  }
  table.ystats th:first-child, table.ystats td:first-child { text-align: left; }
  table.ystats td { white-space: nowrap; max-width: 110px; overflow: hidden; text-overflow: ellipsis; }
  table.ystats tr.dim td { color: var(--muted); }
</style>
