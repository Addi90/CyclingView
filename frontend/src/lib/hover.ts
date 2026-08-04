import { writable } from "svelte/store";

/** Seconds since ride start that the user is hovering over (in any chart). */
export const hoverTime = writable<number | null>(null);

/** Time range selected via drag-to-select on a chart. */
export const selectionRange = writable<{ t0: number; t1: number } | null>(null);
