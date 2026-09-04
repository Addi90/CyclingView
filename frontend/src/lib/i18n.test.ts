import { get } from "svelte/store";
import { describe, expect, it } from "vitest";
import { settings } from "./settings";
import { t } from "./i18n";

describe("t", () => {
  it("defaults to German", () => expect(get(t)("settings.title")).toBe("Einstellungen"));
  it("switches with the language setting", () => {
    settings.set({ ...get(settings), language: "en" });
    expect(get(t)("settings.title")).toBe("Settings");
    settings.set({ ...get(settings), language: "de" });
    expect(get(t)("settings.title")).toBe("Einstellungen");
  });
});
