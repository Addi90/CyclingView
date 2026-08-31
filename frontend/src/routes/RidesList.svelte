<script lang="ts">
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { Plus, SlidersHorizontal } from "lucide-svelte";
  import { api, type Bike, type Ride } from "../lib/api";
  import { fmtKm, fmtKmh, fmtDuration, fmtNum, fmtDateShort } from "../lib/format";
  import { t } from "../lib/i18n";
  import UploadDialog from "../lib/UploadDialog.svelte";
  import StatsPanel from "../lib/StatsPanel.svelte";
  import PowerBestsTable from "../lib/PowerBestsTable.svelte";
  import BottomSheet from "../lib/BottomSheet.svelte";
  import { uploadRequest } from "../lib/upload";

  let bikes: Bike[] = [];
  let rides: Ride[] = [];
  let total = 0;
  let bikeFilter: number | "" = "";
  let dateFrom = "";
  let dateTo = "";
  let loading = false;
  let error = "";
  let uploadOpen = false;
  let filterOpen = false;

  // The mobile tab bar "plus" bumps this from App; opening the dialog here
  // makes the request work from any screen (RideDetail navigates to the
  // list first, and this also fires on the fresh mount).
  $: if ($uploadRequest > 0) uploadOpen = true;

  const SORT_KEYS = {
    start_time: true, name: true, bike_name: true,
    distance_m: true, moving_s: true, avg_speed_ms: true,
    avg_power: true, np_power: true, avg_hr: true, elevation_gain_m: true,
  } as const;
  // Mobile sort select value, e.g. "start_time:desc". Syncs with sortKey/sortDir
  // (the desktop th-sorters update it in turn).
  $: sortSel = `${sortKey}:${sortDir}`;
  function applySortSel() {
    const [k, d] = sortSel.split(":");
    if (k in SORT_KEYS && (d === "asc" || d === "desc")) {
      sortKey = k as SortKey;
      sortDir = d as "asc" | "desc";
    }
  }
  // Bumped after each upload: StatsPanel/PowerBestsTable watch `reloadKey`
  // and re-fetch (they otherwise only load once per page load).
  let refreshKey = 0;

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
    refreshKey++;
    await load();
  }
</script>

<div class="layout">
  <aside>
    <h3>{$t("rides.filter")}</h3>
    <label>
      {$t("rides.filter.bike")}
      <select bind:value={bikeFilter} on:change={load}>
        <option value="">{$t("rides.filter.all")}</option>
        {#each bikes as b}
          <option value={b.id}>{b.name}</option>
        {/each}
      </select>
    </label>
    <label>
      {$t("rides.filter.from")}
      <input type="date" bind:value={dateFrom} on:change={load} />
    </label>
    <label>
      {$t("rides.filter.to")}
      <input type="date" bind:value={dateTo} on:change={load} />
    </label>
    <p class="muted">{$t("rides.filter.count").replace("{count}", String(total))}</p>
    <button type="button" class="upload_action" on:click={() => (uploadOpen = true)}>
      <Plus size={16} /> {$t("rides.upload")}
    </button>
    <hr />
    <StatsPanel reloadKey={refreshKey} />

    <hr />
    <PowerBestsTable activityId={null} compact={true} reloadKey={refreshKey} />

    <hr />

  </aside>

  <section>
    {#if error}<div class="error">{error}</div>{/if}
    {#if loading}<p class="muted">{$t("common.loading")}</p>{/if}
    <div class="table-container">
      <table class="rides">
        <thead>
          <tr>
            <th class="sortable col-date" class:active={sortKey === "start_time"} on:click={() => setSort("start_time")}>
              {$t("rides.col.date")} {sortKey === "start_time" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
            <th class="sortable col-bike" class:active={sortKey === "bike_name"} on:click={() => setSort("bike_name")}>
              {$t("rides.col.bike")} {sortKey === "bike_name" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
            <th class="sortable col-name" class:active={sortKey === "name"} on:click={() => setSort("name")}>
              {$t("rides.col.name")} {sortKey === "name" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
            <th class="sortable num col-dist" class:active={sortKey === "distance_m"} on:click={() => setSort("distance_m")}>
              {$t("rides.col.distance")} {sortKey === "distance_m" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
            <th class="sortable num col-dur" class:active={sortKey === "moving_s"} on:click={() => setSort("moving_s")}>
              {$t("rides.col.duration")} {sortKey === "moving_s" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
            <th class="sortable num col-speed" class:active={sortKey === "avg_speed_ms"} on:click={() => setSort("avg_speed_ms")}>
              {$t("rides.col.speed")} {sortKey === "avg_speed_ms" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
            <th class="sortable num col-power" class:active={sortKey === "avg_power"} on:click={() => setSort("avg_power")}>
              {$t("rides.col.power")} {sortKey === "avg_power" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
            <th class="sortable num col-np" class:active={sortKey === "np_power"} on:click={() => setSort("np_power")}>
              {$t("rides.col.np")} {sortKey === "np_power" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
            <th class="sortable num col-hr" class:active={sortKey === "avg_hr"} on:click={() => setSort("avg_hr")}>
              {$t("rides.col.hr")} {sortKey === "avg_hr" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
            <th class="sortable num col-elev" class:active={sortKey === "elevation_gain_m"} on:click={() => setSort("elevation_gain_m")}>
              {$t("rides.col.elevation")} {sortKey === "elevation_gain_m" ? (sortDir === "asc" ? "↑" : "↓") : ""}
            </th>
          </tr>
        </thead>
        <tbody>
          {#each sortedRides as r}
            <tr>
              <td class="col-date"><Link to={`/rides/${r.id}`}>{fmtDateShort(r.start_time)}</Link></td>
              <td class="col-bike">{r.bike_name ?? "–"}</td>
              <td class="col-name"><Link to={`/rides/${r.id}`}>{r.name ?? "–"}</Link></td>
              <td class="num col-dist">{fmtKm(r.distance_m)}</td>
              <td class="num col-dur">{fmtDuration(r.moving_s ?? r.elapsed_s)}</td>
              <td class="num col-speed">{fmtKmh(r.avg_speed_ms)}</td>
              <td class="num col-power">
                {fmtNum(r.avg_power, 0, " W")}
                {#if r.estimated_power}
                  <span class="estimated" title={$t("ride.power.estimated")}>*</span>
                {/if}
              </td>
              <td class="num col-np">
                {fmtNum(r.np_power, 0, " W")}
                {#if r.estimated_power}
                  <span class="estimated" title={$t("ride.power.estimated")}>*</span>
                {/if}
              </td>
              <td class="num col-hr">{fmtNum(r.avg_hr, 0, " bpm")}</td>
              <td class="num col-elev">{fmtNum(r.elevation_gain_m, 0, " m")}</td>
            </tr>
          {/each}
        </tbody>
      </table>

    </div>
  </section>
</div>

<!-- Mobile (≤768px): card list instead of the wide table. -->
<div class="mobile-only">
  <div class="toolbar">
    <select
      class="sort"
      aria-label={$t("rides.sort")}
      bind:value={sortSel}
      on:change={applySortSel}
    >
      <option value="start_time:desc">{$t("rides.sort.newest")}</option>
      <option value="start_time:asc">{$t("rides.sort.oldest")}</option>
      <option value="distance_m:desc">{$t("rides.sort.distance")}</option>
      <option value="moving_s:desc">{$t("rides.sort.duration")}</option>
      <option value="avg_speed_ms:desc">{$t("rides.sort.speed")}</option>
      <option value="avg_power:desc">{$t("rides.sort.power")}</option>
      <option value="avg_hr:desc">{$t("rides.sort.hr")}</option>
      <option value="elevation_gain_m:desc">{$t("rides.sort.elevation")}</option>
    </select>
    <button type="button" on:click={() => (filterOpen = true)}>
      <SlidersHorizontal size={16} /> {$t("rides.filter")}
    </button>
    <button type="button" class="upload_action" on:click={() => (uploadOpen = true)}>
      <Plus size={16} /> {$t("rides.upload")}
    </button>
  </div>

  {#if error}<div class="error">{error}</div>{/if}
  {#if loading}<p class="muted">{$t("common.loading")}</p>{/if}

  <ul class="ride-cards">
    {#each sortedRides as r}
      <li>
        <Link to={`/rides/${r.id}`} class="ride-card">
          <div class="rc-top">
            <span class="rc-name">{r.name ?? "–"}</span>
            <span class="rc-date">{fmtDateShort(r.start_time)}</span>
          </div>
          <div class="rc-sub">
            {#if r.bike_name}<span>{r.bike_name}</span>{/if}
            <span>{fmtKm(r.distance_m)}</span>
            <span>{fmtDuration(r.moving_s ?? r.elapsed_s)}</span>
            {#if r.avg_power != null}
              <span>
                {fmtNum(r.avg_power, 0, " W")}
                {#if r.estimated_power}
                  <span class="estimated" title={$t("ride.power.estimated")}>*</span>
                {/if}
              </span>
            {/if}
          </div>
        </Link>
      </li>
    {/each}
  </ul>

  <details class="msection">
    <summary>{$t("stats.alltime")}</summary>
    <StatsPanel reloadKey={refreshKey} />
  </details>
  <details class="msection">
    <summary>{$t("power.bests.short")}</summary>
    <PowerBestsTable activityId={null} compact={true} reloadKey={refreshKey} />
  </details>
</div>

<BottomSheet bind:open={filterOpen} title={$t("rides.filter")}>
  <div class="sheet-fields">
    <label>
      {$t("rides.filter.bike")}
      <select bind:value={bikeFilter}>
        <option value="">{$t("rides.filter.all")}</option>
        {#each bikes as b}
          <option value={b.id}>{b.name}</option>
        {/each}
      </select>
    </label>
    <label>
      {$t("rides.filter.from")}
      <input type="date" bind:value={dateFrom} />
    </label>
    <label>
      {$t("rides.filter.to")}
      <input type="date" bind:value={dateTo} />
    </label>
    <button
      type="button"
      class="sheet-apply"
      on:click={() => {
        filterOpen = false;
        load();
      }}
    >
      {$t("rides.filter.apply")}
    </button>
  </div>
</BottomSheet>

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

  /* Mobile view swap: table layout hidden, card list shown (no JS media query). */
  .mobile-only { display: none; }
  @media (max-width: 768px) {
    .layout { display: none; }
    .mobile-only { display: block; }
  }

  .toolbar {
    display: grid;
    grid-template-columns: minmax(110px, 1.1fr) auto 1.4fr;
    gap: 8px;
    margin-bottom: 12px;
  }
  .toolbar .sort { width: 100%; }
  .toolbar .upload_action { display: inline-flex; }

  .ride-cards {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .ride-card {
    display: block;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 14px;
    color: var(--text);
    min-height: var(--touch);
  }
  .ride-card:active { background: var(--panel-2); }
  .rc-top {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 8px;
  }
  .rc-name {
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .rc-date { color: var(--muted); font-size: 13px; flex-shrink: 0; }
  .rc-sub {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    color: var(--muted);
    font-size: 13px;
    margin-top: 4px;
  }

  .msection {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-top: 12px;
    padding: 0 14px 12px;
  }
  .msection summary {
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    color: var(--muted);
    min-height: var(--touch);
    display: flex;
    align-items: center;
    user-select: none;
  }

  .sheet-fields { display: grid; gap: 12px; }
  .sheet-fields label { display: block; font-size: 13px; color: var(--muted); }
  .sheet-fields select, .sheet-fields input { width: 100%; margin-top: 4px; }
  .sheet-apply {
    background: var(--accent);
    border-color: var(--accent);
    /* Dark text on the orange: white would fail WCAG AA (3.3:1). */
    color: var(--bg);
    font-weight: 600;
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
  .estimated {
    color: var(--accent);
    cursor: help;
    margin-left: 2px;
    font-weight: bold;
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
  .error { color: var(--hr); padding: 8px; border: 1px solid var(--hr); border-radius: 6px; margin-bottom: 12px; }
</style>
