import { writable } from "svelte/store";

/**
 * Monotonic counter bumped whenever something asks for the upload dialog
 * (currently the mobile tab bar "+"). RidesList owns the dialog and opens
 * it when this changes, so the request works from any screen.
 */
export const uploadRequest = writable(0);