import { writable } from "svelte/store";

/** Seconds since ride start that the user is hovering over (in any chart). */
export const hoverTime = writable<number | null>(null);
