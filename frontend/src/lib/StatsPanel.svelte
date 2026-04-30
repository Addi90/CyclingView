<script lang="ts">
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { api, type OverallStats } from "./api";
  import { fmtKm, fmtDuration, fmtNum, fmtDateShort } from "./format";

  let stats: OverallStats | null = null;
  let error = "";

  onMount(async () => {
    try {
      stats = await api.stats();
    } catch (e: any) {
      error = e?.message ?? String(e);
    }
  });
</script>

{#if error}
  <p class="error">Stats: {error}</p>
{:else if !stats}
  <p class="muted small">Lade Stats…</p>
{:else}
  <h3>Allzeit</h3>
  <dl class="stat-list">
    <dt>Fahrten</dt><dd>{stats.totals.rides}</dd>
    <dt>Distanz</dt><dd>{fmtKm(stats.totals.distance_m, 0)}</dd>
    <dt>Fahrzeit</dt><dd>{fmtDuration(stats.totals.moving_s)}</dd>
    <dt>Höhenmeter</dt><dd>{fmtNum(stats.totals.elevation_gain_m, 0, " m")}</dd>
  </dl>

  {#if stats.longest_distance}
    <p class="muted small">
      🏁 Längste Strecke:
      <Link to={`/rides/${stats.longest_distance.id}`}>
        {fmtKm(stats.longest_distance.distance_m, 1)}
      </Link>
      <br />
      <span class="dim">{fmtDateShort(stats.longest_distance.start_time)}</span>
    </p>
  {/if}
  {#if stats.longest_duration && stats.longest_duration.id !== stats.longest_distance?.id}
    <p class="muted small">
      ⏱ Längste Dauer:
      <Link to={`/rides/${stats.longest_duration.id}`}>
        {fmtDuration(stats.longest_duration.moving_s)}
      </Link>
      <br />
      <span class="dim">{fmtDateShort(stats.longest_duration.start_time)}</span>
    </p>
  {/if}

  {#if stats.per_year.length}
    <details open>
      <summary>Pro Jahr</summary>
      <table class="ystats">
        <thead><tr><th>Jahr</th><th>Fahrten</th><th>km</th><th>Zeit</th></tr></thead>
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
    <details>
      <summary>Pro Rad</summary>
      <table class="ystats">
        <thead><tr><th>Rad</th><th>Fahrten</th><th>km</th></tr></thead>
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
              <td>– ohne –</td>
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
  }
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
