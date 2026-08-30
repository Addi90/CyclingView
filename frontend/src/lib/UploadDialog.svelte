<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import { Upload, X, Loader2, CheckCircle2, XCircle } from "lucide-svelte";
  import { api, type Bike } from "./api";
  import { t } from "./i18n";

  export let open = false;
  export let bikes: Bike[] = [];

  const dispatch = createEventDispatcher<{ uploaded: { count: number; failed: number } }>();

  type Status = "idle" | "uploading" | "done" | "error";
  interface QueueItem {
    id: number;
    file: File;
    name: string;
    bikeId: number | "";
    status: Status;
    error?: string;
  }

  let queue: QueueItem[] = [];
  let busy = false;
  let error = "";
  let dragging = false;
  let progress = 0;
  let total = 0;
  let nextId = 1;
  let fileInputEl: HTMLInputElement | null = null;

  const EXT_RE = /\.(fit|tcx|gpx)(\.gz)?$/i;

  $: doneCount = queue.filter((q) => q.status === "done").length;
  $: failedCount = queue.filter((q) => q.status === "error").length;

  function baseName(f: File) {
    return f.name.replace(EXT_RE, "");
  }

  function isRideFile(f: File) {
    return EXT_RE.test(f.name) || /\.gz$/i.test(f.name) || f.type === "application/gzip";
  }

  function addFiles(files: FileList | File[]) {
    const added: QueueItem[] = [];
    for (const f of Array.from(files)) {
      if (!isRideFile(f)) continue;
      const dup = queue.some((q) => q.file.name === f.name && q.file.size === f.size);
      if (dup) continue;
      added.push({ id: nextId++, file: f, name: baseName(f), bikeId: "", status: "idle" });
    }
    if (added.length) queue = [...queue, ...added];
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    dragging = false;
    if (e.dataTransfer?.files) addFiles(e.dataTransfer.files);
  }

  function onDragOver(e: DragEvent) {
    e.preventDefault();
    dragging = true;
  }

  function onDragLeave() {
    dragging = false;
  }

  function openBrowse() {
    fileInputEl?.click();
  }

  function onBrowse(e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.files?.length) addFiles(input.files);
    input.value = "";
  }

  function removeAt(id: number) {
    queue = queue.filter((q) => q.id !== id);
  }

  function clearAll() {
    if (busy) return;
    queue = [];
    error = "";
  }

  function setRow(id: number, patch: Partial<QueueItem>) {
    queue = queue.map((q) => (q.id === id ? { ...q, ...patch } : q));
  }

  function reset() {
    queue = [];
    error = "";
    busy = false;
    dragging = false;
    progress = 0;
    total = 0;
  }

  function close() {
    open = false;
    if (!busy) reset();
  }

  async function submit() {
    if (queue.length === 0) {
      error = $t("upload.error.no_file");
      return;
    }
    busy = true;
    error = "";
    const toUpload = queue.filter((q) => q.status !== "done");
    total = toUpload.length;
    progress = 0;
    let done = 0;
    let failed = 0;
    for (const q of toUpload) {
      setRow(q.id, { status: "uploading", error: undefined });
      try {
        await api.uploadRide(q.file, {
          name: q.name.trim() || undefined,
          bike_id: q.bikeId === "" ? null : Number(q.bikeId),
        });
        setRow(q.id, { status: "done" });
        done++;
      } catch (e: any) {
        setRow(q.id, { status: "error", error: e?.message ?? String(e) });
        failed++;
      }
      progress++;
    }
    busy = false;
    dispatch("uploaded", { count: done, failed });
    if (failed === 0) close();
  }
</script>

{#if open}
  <div
    class="backdrop"
    on:click|self={close}
    on:keydown={(e) => e.key === "Escape" && close()}
    role="dialog"
    aria-modal="true"
    tabindex="-1"
  >
    <div class="modal" role="document">
      <div class="head">
        <h3>{$t("upload.title")}</h3>
        {#if queue.length > 0 && !busy}
          <button type="button" class="link" on:click={clearAll}>{$t("upload.clear")}</button>
        {/if}
      </div>

      <div
        class="drop"
        class:dragging
        role="button"
        tabindex="0"
        aria-label={$t("upload.drop")}
        on:click={openBrowse}
        on:keydown={(e) => (e.key === "Enter" || e.key === " ") && openBrowse()}
        on:drop={onDrop}
        on:dragover={onDragOver}
        on:dragleave={onDragLeave}
      >
        <Upload size={20} />
        <span>{$t("upload.drop")}</span>
      </div>
      <input
        type="file"
        multiple
        accept=".fit,.tcx,.gpx,.gz,application/gzip"
        style="display:none"
        bind:this={fileInputEl}
        on:change={onBrowse}
      />

      {#if queue.length > 0}
        <div class="count-row">
          <span class="muted">{$t("upload.files_count").replace("{count}", String(queue.length))}</span>
          {#if busy}
            <span class="muted spin-wrap"><span class="spin"><Loader2 size={13} /></span> {$t("upload.progress").replace("{i}", String(progress)).replace("{n}", String(total))}</span>
          {/if}
        </div>
        <div class="rows">
          {#each queue as q (q.id)}
            <div class="row" class:done={q.status === "done"} class:error={q.status === "error"}>
              <div class="row-head">
                <span class="fname" title={q.file.name}>{q.file.name}</span>
                {#if q.status === "uploading"}
                  <span class="stat spin"><Loader2 size={14} /></span>
                {:else if q.status === "done"}
                  <span class="stat ok"><CheckCircle2 size={14} /></span>
                {:else if q.status === "error"}
                  <span class="stat err" title={q.error}><XCircle size={14} /></span>
                {/if}
                <button type="button" class="rm" title={$t("upload.remove")} on:click={() => removeAt(q.id)} disabled={busy}>
                  <X size={14} />
                </button>
              </div>
              <div class="row-fields">
                <input type="text" bind:value={q.name} placeholder={$t("upload.name_placeholder")} disabled={q.status === "uploading"} />
                <select bind:value={q.bikeId} disabled={q.status === "uploading"}>
                  <option value="">{$t("ride.bike.none")}</option>
                  {#each bikes as b}
                    <option value={b.id}>{b.name}</option>
                  {/each}
                </select>
              </div>
              {#if q.status === "error" && q.error}
                <div class="row-err">{q.error}</div>
              {/if}
            </div>
          {/each}
        </div>
      {/if}

      {#if !busy && doneCount + failedCount > 0}
        <div class="summary" class:has-error={failedCount > 0}>
          {$t("upload.summary").replace("{done}", String(doneCount)).replace("{failed}", String(failedCount))}
        </div>
      {/if}

      {#if error}<div class="error">{error}</div>{/if}

      <div class="actions">
        <button type="button" on:click={close} disabled={busy}>{$t("ride.cancel")}</button>
        <button type="button" class="primary" on:click={submit} disabled={busy || queue.length === 0}>
          {busy ? $t("upload.submitting") : $t("upload.submit")}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
  }
  .modal {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px 22px;
    width: min(560px, 94vw);
    max-height: 90vh;
    overflow: auto;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  }
  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .modal h3 { margin-top: 0; }
  .link {
    background: none;
    border: none;
    color: var(--muted);
    font-size: 12px;
    cursor: pointer;
  }
  .link:hover { color: var(--accent); }
  .drop {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    border: 1.5px dashed var(--border);
    border-radius: 8px;
    padding: 22px 16px;
    margin: 14px 0;
    color: var(--muted);
    font-size: 13px;
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
  }
  .drop:hover,
  .drop:focus-visible {
    border-color: var(--accent);
    color: var(--accent);
    outline: none;
  }
  .drop.dragging {
    border-color: var(--accent);
    background: rgba(252, 82, 0, 0.08);
    color: var(--accent);
  }
  .count-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }
  .muted { color: var(--muted); font-size: 12px; }
  .rows {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: 40vh;
    overflow-y: auto;
    margin-bottom: 8px;
  }
  .row {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 10px;
  }
  .row.done { border-color: rgba(34, 197, 94, 0.4); }
  .row.error { border-color: rgba(239, 68, 68, 0.5); }
  .row-head {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }
  .fname {
    flex: 1;
    font-size: 13px;
    color: var(--text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .stat { flex-shrink: 0; display: inline-flex; }
  .stat.ok { color: #22c55e; }
  .stat.err { color: #ef4444; }
  .rm {
    background: none;
    border: none;
    color: var(--muted);
    cursor: pointer;
    padding: 2px;
    display: inline-flex;
    flex-shrink: 0;
  }
  .rm:hover { color: #ef4444; }
  .rm:disabled { opacity: 0.4; cursor: not-allowed; }
  .row-fields {
    display: grid;
    grid-template-columns: 1fr 150px;
    gap: 8px;
  }
  .row-fields input,
  .row-fields select {
    width: 100%;
    font-size: 13px;
  }
  .row-err {
    color: #ef4444;
    font-size: 12px;
    margin-top: 6px;
  }
  .summary {
    font-size: 13px;
    color: #22c55e;
    margin: 8px 0;
  }
  .summary.has-error { color: #ef4444; }
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 16px;
  }
  .primary {
    background: var(--accent);
    color: white;
    border-color: var(--accent);
  }
  .primary:hover { filter: brightness(1.1); }
  .primary:disabled { opacity: 0.5; cursor: not-allowed; }
  .error {
    color: #ef4444;
    background: rgba(239, 68, 68, 0.1);
    padding: 8px;
    border-radius: 6px;
    font-size: 13px;
    margin-top: 8px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .spin { animation: spin 1s linear infinite; }
  @media (prefers-reduced-motion: reduce) {
    .spin { animation: none; }
  }
</style>