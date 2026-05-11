<script lang="ts">
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { Plus } from "lucide-svelte";
  import { api, type Bike, type Ride } from "../lib/api";
  import { fmtKm, fmtKmh, fmtDuration, fmtNum, fmtDateShort } from "../lib/format";
  import UploadDialog from "../lib/UploadDialog.svelte";
  import StatsPanel from "../lib/StatsPanel.svelte";
  import PowerBestsTable from "../lib/PowerBestsTable.svelte";

  let bikes: Bike[] = [];
  let rides: Ride[] = [];
  let total = 0;
  let bikeFilter: number | "" = "";
  let dateFrom = "";
  let dateTo = "";
  let loading = false;
  let error = "";
  let uploadOpen = false;

  type SortKey =
    | "start_time" | "name" | "bike_name"
    | "distance_m" | "moving_s" | "avg_speed_ms"
    | "avg_power" | "np_power" | "avg_hr"
    | "elevation_gain_m";
  let sortKey: SortKey = "start_time";
  let sortDir: "asc" | "desc" = "desc";

  function setSort(k: SortKey) {
    if (sortKey === k) {
      sortDir = sortDir === "asc" ? "desc" : "asc";
    } else {
      sortKey = k;
      // Numeric/duration columns default to descending (largest first); text ascending.
      sortDir = (k === "name" || k === "bike_name") ? "asc" : "desc";
    }
  }

  $: sortedRides = (() => {
    const arr = rides.slice();
    const dir = sortDir === "asc" ? 1 : -1;
    arr.sort((a, b) => {
      const av: any = (a as any)[sortKey];
      const bv: any = (b as any)[sortKey];
      // Nulls last regardless of direction.
      const an = av == null;
      const bn = bv == null;
      if (an && bn) return 0;
      if (an) return 1;
      if (bn) return -1;
      if (typeof av === "string" && typeof bv === "string") {
        return av.localeCompare(bv) * dir;
      }
      return (av - bv) * dir;
    });
    return arr;
  })();

  async function load() {
    loading = true;
    error = "";
    try {
      const res = await api.rides({
        bike_id: bikeFilter === "" ? undefined : Number(bikeFilter),
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        limit: 500,
      });
      rides = res.items;
      total = res.total;
    } catch (e: any) {
      error = e.message ?? String(e);
    } finally {
      loading = false;
    }
  }

  onMount(async () => {
    bikes = await api.bikes();
    await load();
  });

  async function onUploaded() {
    await load();
  }
</script>

<div class="layout">
  <aside>
    <h3>Filter</h3>
    <label>
      Rad
      <select bind:value={bikeFilter} on:change={load}>
        <option value="">Alle</option>
        {#each bikes as b}
          <option value={b.id}>{b.name}</option>
        {/each}
      </select>
    </label>
    <label>
      Von
      <input type="date" bind:value={dateFrom} on:change={load} />
    </label>
    <label>
      Bis
      <input type="date" bind:value={dateTo} on:change={load} />
    </label>
    <p class="muted">{total} Fahrten</p>
    <button type="button" class="upload_action" on:click={() => (uploadOpen = true)}>
      <Plus size={16} /> Fahrt hochladen
    </button>
    <hr />
    <StatsPanel />

    <hr />
    <PowerBestsTable activityId={null} title="Power-Bestwerte" compact={true} />

    <hr />

  </aside>

  <section>
    {#if error}<div class="error">{error}</div>{/if}
    {#if loading}<p class="muted">Lade…</p>{/if}
    <div class="table-container">
      <table class="rides">
        <thead>
          <tr>
            <th class="sortable col-date" class:active={sortKey === "start_time"} on:click={() => setSort("start_time")}>
              Datum {sortKey === "start_time" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
            <th class="sortable col-bike" class:active={sortKey === "bike_name"} on:click={() => setSort("bike_name")}>
              Rad {sortKey === "bike_name" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
            <th class="sortable col-name" class:active={sortKey === "name"} on:click={() => setSort("name")}>
              Name {sortKey === "name" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
            <th class="sortable num col-dist" class:active={sortKey === "distance_m"} on:click={() => setSort("distance_m")}>
              Distanz {sortKey === "distance_m" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
            <th class="sortable num col-dur" class:active={sortKey === "moving_s"} on:click={() => setSort("moving_s")}>
              Dauer {sortKey === "moving_s" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
            <th class="sortable num col-speed" class:active={sortKey === "avg_speed_ms"} on:click={() => setSort("avg_speed_ms")}>
              ⌀ Speed {sortKey === "avg_speed_ms" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
            <th class="sortable num col-power" class:active={sortKey === "avg_power"} on:click={() => setSort("avg_power")}>
              ⌀ Power {sortKey === "avg_power" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
            <th class="sortable num col-np" class:active={sortKey === "np_power"} on:click={() => setSort("np_power")}>
              NP {sortKey === "np_power" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
            <th class="sortable num col-hr" class:active={sortKey === "avg_hr"} on:click={() => setSort("avg_hr")}>
              ⌀ HR {sortKey === "avg_hr" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
            <th class="sortable num col-elev" class:active={sortKey === "elevation_gain_m"} on:click={() => setSort("elevation_gain_m")}>
              ↑ Höhe {sortKey === "elevation_gain_m" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
          </tr>
        </thead>
        <tbody>
          {#each sortedRides as r}
            <tr>
              <td class="col-date"><Link to={`/rides/${r.id}`}>{fmtDateShort(r.start_time)}</Link></td>
              <td class="col-name"><Link to={`/rides/${r.id}`}>{r.name ?? "–"}</Link></td>
              <td class="num col-dist">{fmtKm(r.distance_m)}</td>
              <td class="col-bike">{r.bike_name ?? "–"}</td>
              <td class="num col-dur">{fmtDuration(r.moving_s ?? r.elapsed_s)}</td>
              <td class="num col-speed">{fmtKmh(r.avg_speed_ms)}</td>
              <td class="num col-power">{fmtNum(r.avg_power, 0, " W")}</td>
              <td class="num col-np">{fmtNum(r.np_power, 0, " W")}</td>
              <td class="num col-hr">{fmtNum(r.avg_hr, 0, " bpm")}</td>
              <td class="num col-elev">{fmtNum(r.elevation_gain_m, 0, " m")}</td>
            </tr>
          {/each}
        </tbody>
      </table>

    </div>
  </section>
</div>

<UploadDialog bind:open={uploadOpen} {bikes} on:uploaded={onUploaded} />

<style>
  .layout {
    display: grid;
    grid-template-columns: 260px 1fr;
    gap: 24px;
    align-items: start;
  }
  aside {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    height: fit-content;
    position: sticky;
    top: 64px;
    max-height: calc(100vh - 80px);
    overflow-y: auto;
  }

  @media (max-width: 800px) {
    .layout {
      grid-template-columns: 1fr;
      gap: 16px;
    }
    aside {
      order: 1;
      position: static;
      max-height: none;
      width: 100%;
      margin-bottom: 8px;
    }
    section {
      order: 2;
      width: 100%;
      overflow: hidden;
    }
    table.rides {
      min-width: 400px;
    }
    table.rides th, table.rides td {
      padding: 10px 8px;
    }
    table.rides .col-date { width: 85px; }
    table.rides .col-dist { width: 55px; }
    .col-name {
      max-width: 90px;
      word-wrap: break-word;
      overflow-wrap: break-word;
    }
    /* Hide less critical columns on small screens to fit Date, Name, Distance */
    .col-bike, .col-speed, .col-np, .col-hr, .col-elev {
      display: none;
    }
    table.rides .col-name {
      white-space: normal ;
    }
  }

  section {
    min-width: 0;
    width: 100%;
  }

  .table-container {
    width: 100%;
    overflow-x: auto;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    -webkit-overflow-scrolling: touch;
  }

  table.rides {
    width: 100%;
    border-collapse: collapse;
    min-width: 800px;
  }
  
  .col-name {
    max-width: 180px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  table.rides th, table.rides td {
    padding: 10px 12px;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  table.rides tr:last-child td { border-bottom: none; }

  aside h3 { margin-top: 0; }
  aside label { display: block; margin-bottom: 12px; font-size: 13px; color: var(--muted); }
  aside select, aside input { display: block; margin-top: 4px; width: 100%; }
  aside hr { border: none; border-top: 1px solid var(--border); margin: 16px 0 12px; }
  .action { width: 100%; margin-bottom: 8px; text-align: left; }
  .upload_action {
    width: 100%;
    background: transparent;
    border: 1px solid var(--accent);
    color: var(--accent);
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 16px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }
  .upload_action:hover { background: rgba(252, 82, 0, 0.1); }
  .small { font-size: 12px; }
  section > :global(.bests) { margin-bottom: 16px; }
  table.rides th.sortable {
    cursor: pointer;
    user-select: none;
    transition: color 0.15s, background 0.15s;
  }
  table.rides th.sortable:hover {
    color: var(--accent);
    background: rgba(252, 82, 0, 0.08);
  }
  table.rides th.active { color: var(--accent); }
  table.rides th.num, table.rides td.num { text-align: right; font-variant-numeric: tabular-nums; }
  .muted { color: var(--muted); font-size: 13px; }
  .error { color: #ef4444; padding: 8px; border: 1px solid #ef4444; border-radius: 6px; margin-bottom: 12px; }
</style>
