<script lang="ts">
  import { settings } from "./settings";
  import { t } from "./i18n";
</script>

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

<style>
  h4 {
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
  .inline input[type="number"] { width: 60px; }
</style>