<script lang="ts">
  import { settings } from "./settings";
  import { t } from "./i18n";
</script>

<section>
  <h4>{$t("settings.profile")}</h4>

  <!-- Each field is a wrapping <label> so the text and the control are
       properly associated (a11y) and the whole row is a click target. -->
  <label class="field">
    <span class="flabel">{$t("settings.language")}</span>
    <span class="field-input">
      <select bind:value={$settings.language}>
        <option value="de">Deutsch</option>
        <option value="en">English</option>
      </select>
      <span class="unit"></span>
    </span>
  </label>

  <label class="field">
    <span class="flabel">{$t("settings.weight")}</span>
    <span class="field-input">
      <input type="number" min="20" max="200" step="0.1" bind:value={$settings.weightKg} />
      <span class="unit">kg</span>
    </span>
  </label>

  <label class="field">
    <span class="flabel">{$t("settings.age")}</span>
    <span class="field-input">
      <input type="number" min="10" max="120" step="1" bind:value={$settings.ageYears} />
      <span class="unit">{$t("settings.years")}</span>
    </span>
  </label>

  <label class="field">
    <span class="flabel">{$t("settings.sex")}</span>
    <span class="field-input">
      <select bind:value={$settings.sex}>
        <option value="male">{$t("settings.sex.male")}</option>
        <option value="female">{$t("settings.sex.female")}</option>
      </select>
      <span class="unit"></span>
    </span>
  </label>

  <label class="field">
    <span class="flabel">{$t("settings.maxHR")}</span>
    <span class="field-input">
      <input type="number" min="60" max="250" step="1" bind:value={$settings.maxHR} placeholder="z. B. 190" />
      <span class="unit">{$t("settings.bpm")}</span>
    </span>
  </label>

  <label class="field">
    <span class="flabel">{$t("settings.powerDisplay")}</span>
    <span class="field-input">
      <select bind:value={$settings.powerUnit}>
        <option value="W">Watt (W)</option>
        <option value="W/kg">W pro kg</option>
      </select>
      <span class="unit"></span>
    </span>
  </label>
</section>

<style>
  h4 {
    margin: 0 0 8px;
    font-size: 12px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .field {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 6px 0;
    border-bottom: 1px solid var(--border);
    cursor: pointer;
  }
  .field:last-child { border-bottom: none; }
  .flabel {
    font-size: 14px;
    flex-shrink: 0;
  }
  /* flex-basis 190px but shrinkable so narrow phones don't overflow. */
  .field-input {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    flex: 0 1 190px;
  }
  .field-input input, .field-input select {
    flex: 1;
    min-width: 0;
    text-align: right;
    box-sizing: border-box;
  }
  .unit {
    width: 45px;
    flex-shrink: 0;
    color: var(--muted);
    font-size: 13px;
    text-align: left;
    white-space: nowrap;
  }
</style>