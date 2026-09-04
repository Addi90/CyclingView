<script lang="ts">
  import { onMount } from "svelte";
  import { Plus, Trash2 } from "lucide-svelte";
  import { api, type Bike } from "./api";
  import { t } from "./i18n";

  let bikes: Bike[] = [];
  let bikesError = "";
  let newBike = { name: "", brand: "", model: "" };
  let bikeBusy = false;

  // The section (re)mounts whenever its host opens, so onMount is enough to
  // (re)load the list.
  async function loadBikes() {
    try {
      bikes = await api.bikes();
    } catch (e: any) {
      bikesError = e?.message ?? String(e);
    }
  }
  onMount(loadBikes);

  async function addBike() {
    if (!newBike.name.trim()) return;
    bikeBusy = true;
    bikesError = "";
    try {
      await api.createBike({
        name: newBike.name.trim(),
        brand: newBike.brand.trim() || undefined,
        model: newBike.model.trim() || undefined,
      });
      newBike = { name: "", brand: "", model: "" };
      await loadBikes();
    } catch (e: any) {
      bikesError = $t("settings.error").replace("{message}", e?.message ?? String(e));
    } finally {
      bikeBusy = false;
    }
  }

  async function removeBike(b: Bike) {
    if (!confirm($t("settings.bike.delete_confirm").replace("{name}", b.name))) return;
    bikesError = "";
    try {
      await api.deleteBike(b.id);
      await loadBikes();
    } catch (e: any) {
      bikesError = $t("settings.error").replace("{message}", e?.message ?? String(e));
    }
  }
</script>

<section>
  <h4>{$t("settings.bikes")}</h4>
  {#if bikesError}<small class="status error-text">{bikesError}</small>{/if}
  {#if bikes.length}
    <ul class="bike-list">
      {#each bikes as b}
        <li>
          <span class="bname">{b.name}</span>
          {#if b.brand || b.model}
            <small class="dim">{[b.brand, b.model].filter(Boolean).join(" ")}</small>
          {/if}
          <button type="button" class="del" on:click={() => removeBike(b)} title={$t("ride.delete")}>
            <Trash2 size={14} />
          </button>
        </li>
      {/each}
    </ul>
  {/if}
  <div class="add-bike">
    <input type="text" placeholder={$t("settings.bike.name")} bind:value={newBike.name} />
    <input type="text" placeholder={$t("settings.bike.brand")} bind:value={newBike.brand} />
    <input type="text" placeholder={$t("settings.bike.model")} bind:value={newBike.model} />
    <button type="button" on:click={addBike} disabled={bikeBusy || !newBike.name.trim()}>
      <Plus size={16} /> {$t("settings.bike.add")}
    </button>
  </div>
</section>

<style>
  h4 {
    margin: 0 0 8px;
    font-size: 12px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .status { display: block; color: var(--muted); margin-top: 4px; width: 100%; }
  .error-text { color: var(--hr); }
  .bike-list {
    list-style: none;
    padding: 0;
    margin: 0 0 8px;
  }
  .bike-list li {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    border-bottom: 1px solid var(--border);
    font-size: 13px;
  }
  .bike-list .bname { flex: 1; }
  .bike-list .dim { color: var(--muted); }
  .bike-list .del {
    background: transparent;
    border: none;
    color: var(--muted);
    cursor: pointer;
    padding: 2px 6px;
  }
  .bike-list .del:hover { color: var(--hr); }
  .add-bike {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
    margin-top: 4px;
  }
  .add-bike input { width: 100%; box-sizing: border-box; }
  .add-bike button { grid-column: 1 / -1; }
</style>