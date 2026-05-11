<script lang="ts">
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { api, type PowerBest, type AllTimeBestEntry } from "./api";
  import { settings } from "./settings";
  import { fmtWindow, fmtPower } from "./power-format";
  import { fmtDateShort } from "./format";
  import { t } from "./i18n";

  /** When set, show this ride's bests; otherwise the all-time leaderboard. */
  export let activityId: number | string | null = null;
  /** Compact mode hides the "Fahrt" column and truncates dates. */
  export let compact = false;

  $: title = activityId ? $t("power.bests.mean_max") : $t("power.bests.all_time");

  let bests: PowerBest[] = [];
  let leaderboard: Record<string, AllTimeBestEntry[]> = {};
  let windowsS: number[] = [];
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

  function togglePowerUnit() {
    settings.update((s) => ({ ...s, powerUnit: s.powerUnit === "W" ? "W/kg" : "W" }));
  }
</script>

<section class="bests">
  <header>
    <h3>{title}</h3>
    <button type="button" class="unit" on:click={togglePowerUnit}
      title={$t("power.bests.unit_title").replace("{unit}", $settings.powerUnit).replace("{weight}", String($settings.weightKg))}>
      {$settings.powerUnit}
    </button>
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
              <td class="num">{fmtPower(b.watts, $settings.weightKg, $settings.powerUnit)}</td>
            </tr>
          {/each}
        {:else}
          {#each windowsS as w}
            {@const top = leaderboard[String(w)]?.[0]}
            <tr class:none={!top}>
              <td>{fmtWindow(w)}</td>
              <td class="num">{fmtPower(top?.watts ?? null, $settings.weightKg, $settings.powerUnit)}</td>
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
  .unit {
    background: transparent;
    border: 1px solid var(--accent);
    color: var(--accent);
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 12px;
    cursor: pointer;
  }
  .unit:hover { background: rgba(252, 82, 0, 0.1); }
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
  td.ride { font-size: 12px; }
  td.ride small { display: block; }
  .dim { color: var(--muted); }
  .none td { color: var(--muted); }
  .muted { color: var(--muted); }
  .small { font-size: 12px; }
  .error { color: #ef4444; font-size: 12px; }
</style>
