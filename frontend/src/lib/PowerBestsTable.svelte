<script lang="ts">
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { api, type PowerBest, type AllTimeBestEntry } from "./api";
  import { settings } from "./settings";
  import { fmtWindow, fmtPower } from "./power-format";
  import { fmtDateShort } from "./format";
  import { t } from "./i18n";
  import PillBar from "./PillBar.svelte";

  /** When set, show this ride's bests; otherwise the all-time leaderboard. */
  export let activityId: number | string | null = null;
  /** Compact mode hides the "Fahrt" column and truncates dates. */
  export let compact = false;
  /** Bump to force a re-fetch (e.g. after a ride upload). 0 = initial mount only. */
  export let reloadKey = 0;

  $: title = activityId ? $t("power.bests.mean_max") : $t("power.bests.all_time");

  let bests: PowerBest[] = [];
  let leaderboard: Record<string, AllTimeBestEntry[]> = {};
  let windowsS: number[] = [];
  let estimatedPower = 0;
  let error = "";
  let loading = false;

  async function load() {
    loading = true;
    error = "";
    try {
      if (activityId != null) {
        const res = await api.powerBestsForRide(activityId);
        bests = res.bests;
        windowsS = res.windows_s;
        estimatedPower = (res as any).estimated_power ?? 0;
      } else {
        const res = await api.powerBestsAllTime(1);
        leaderboard = res.leaderboard;
        windowsS = res.windows_s;
      }
    } catch (e: any) {
      error = e?.message ?? String(e);
    } finally {
      loading = false;
    }
  }

  onMount(load);
  $: if (activityId !== undefined) load();
  $: if (reloadKey > 0) load();

  function setPowerUnit(unit: "W" | "W/kg") {
    if ($settings.powerUnit === unit) return;
    settings.update((s) => ({ ...s, powerUnit: unit }));
  }

  // W / W-kg unit toggle options (values match settings.powerUnit).
  const unitOptions = [
    { label: "W/kg", value: "W/kg" },
    { label: "W", value: "W" },
  ];
</script>

<section class="bests">
  <header>
    <h3>{title}</h3>
    <div class="unit-toggle">
      <PillBar
        options={unitOptions}
        value={$settings.powerUnit}
        on:change={(e) => setPowerUnit(e.detail)}
        title={$t("power.bests.unit_title").replace("{unit}", $settings.powerUnit).replace("{weight}", String($settings.weightKg))}
      />
    </div>
  </header>

  {#if error}
    <p class="error">{error}</p>
  {:else if loading}
    <p class="muted small">{$t("common.loading")}</p>
  {:else if windowsS.length === 0 || (activityId == null && Object.keys(leaderboard).length === 0)}
    <p class="muted small">{$t("power.bests.no_data")}</p>
  {:else}
    <table>
      <thead>
        <tr>
          <th>{$t("power.bests.col.duration")}</th>
          <th class="powerUnit">{$settings.powerUnit}</th>
          {#if activityId == null && !compact}<th>{$t("power.bests.col.ride")}</th>{/if}
        </tr>
      </thead>
      <tbody>
        {#if activityId != null}
          {#each bests as b}
            <tr class:none={b.watts == null}>
              <td>{fmtWindow(b.window_s)}</td>
              <td class="num">
                {fmtPower(b.watts, $settings.weightKg, $settings.powerUnit)}
                {#if estimatedPower}
                  <span class="estimated" title={$t("ride.power.estimated")}>*</span>
                {/if}
              </td>
            </tr>
          {/each}
        {:else}
          {#each windowsS as w}
            {@const top = leaderboard[String(w)]?.[0]}
            <tr class:none={!top}>
              <td>{fmtWindow(w)}</td>
              <td class="num">
                {#if compact && top}
                  <Link to={`/rides/${top.activity_id}`}>
                    {fmtPower(top.watts, $settings.weightKg, $settings.powerUnit)}
                    {#if top.estimated_power}
                      <span class="estimated" title={$t("ride.power.estimated")}>*</span>
                    {/if}
                  </Link>
                {:else}
                  {fmtPower(top?.watts ?? null, $settings.weightKg, $settings.powerUnit)}
                  {#if top?.estimated_power}
                    <span class="estimated" title={$t("ride.power.estimated")}>*</span>
                  {/if}
                {/if}
              </td>
              {#if !compact}
                <td class="ride">
                  {#if top}
                    <Link to={`/rides/${top.activity_id}`}>{top.name ?? $t("power.bests.col.ride")}</Link>
                    <small class="dim">{fmtDateShort(top.start_time)}</small>
                  {:else}–{/if}
                </td>
              {/if}
            </tr>
          {/each}
        {/if}
      </tbody>
    </table>
  {/if}
</section>

<style>
  .bests {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 14px;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
  }
  h3 { margin: 0; font-size: 14px; }
  .unit-toggle {
    flex: none; /* don't shrink next to the h3 in narrow panels */
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  th, td {
    padding: 4px 6px;
    border-bottom: 1px solid var(--border);
    text-align: left;
  }
  th.powerUnit { text-align: right; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; font-weight: 500; }
  .estimated {
    color: var(--accent);
    cursor: help;
    margin-left: 2px;
    font-weight: bold;
  }
  td.ride { font-size: 12px; }
  td.ride small { display: block; }
  .dim { color: var(--muted); }
  .none td { color: var(--muted); }
  .muted { color: var(--muted); }
  .small { font-size: 12px; }
  .error { color: #ef4444; font-size: 12px; }
</style>
