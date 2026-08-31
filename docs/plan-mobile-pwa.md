# Plan: Mobile PWA

**Goal:** make Cycling View comfortable on a phone in the saddle / at the desk, and
installable as a PWA. Desktop keeps the current layout untouched.

**Design system:** repo has no DESIGN.md, but `app.css` already defines a working
system (dark `#0f1115`/`#181c23`, Strava orange accent, field colours). We **reuse it**
(YAGNI applies to design systems) and extend it with mobile-specific tokens
(touch targets, pressed states, safe areas). No new colour, accent, or font.
Mobile rules follow the anti-slop mobile baseline: ≥44px targets, `:active` instead
of hover-only feedback, 16px body min (iOS zoom), safe-area insets.

---

## Phase 1 — PWA foundation (no UI changes)

1. **`frontend/public/manifest.webmanifest`** — name, `display: standalone`,
   `theme_color: #0f1115`, `background_color: #0f1115`, 192 + 512 icons
   (one generated SVG-rasterised icon is enough; bike glyph on dark bg, orange accent).
2. **Hand-rolled service worker (`public/sw.js`, ~40 lines)** — no new dependency:
   - App shell (JS/CSS/index.html): cache-first, versioned cache name, clean old versions on activate.
   - API (`/api/*`): network-only, never cached (data must stay fresh).
   - This gives: install prompt, app icon, launch screen, and **offline = last-loaded
     screens still work, API errors show as the existing `.error` div**. That is the
     honest scope; offline-first data sync is out of scope (would need backend changes).
3. **`index.html`** — link manifest, `<meta name="theme-color">`,
   `viewport` + `viewport-fit=cover`, apple-mobile-web-app-capable + status bar style.
4. **Register SW in `main.ts`** (`if ('serviceWorker' in navigator)`, prod only).
5. Install: rely on the browser-native install prompt (Chrome/Android + iOS "Add to
   Home Screen"). No custom `beforeinstallprompt` UI — YAGNI until we have one.

Backend: **nothing to change**. nginx serves `sw.js`/manifest from the SPA static dir.

## Phase 2 — Mobile layouts (breakpoint `max-width: 768px`, mobile styles only)

### 2a. RidesList — table → card list

The 10-column sortable table (min-width 800px + h-scroll + hidden columns) is the
least usable screen on a phone. Replace with, **below 768px only**:

- **Ride cards, one per row**: `name` (primary), `date · km · duration` (muted line),
  bike name if set. Tap anywhere → detail (whole card ≥44px, `<Link>`).
  `estimated_power` `*` stays next to nothing here (moves to detail).
- **Sort**: single compact `<select>` (Newest / Longest / Fastest / Power / HR / Elevation)
  above the list, reusing the existing `setSort` keys. Drop per-column sort on mobile —
  a select is thumb-friendly and covers the 6 sorts people actually want.
- **Filters**: bike + date range collapse into a "Filter" button that opens a
  **bottom sheet** (native-dialog styled: bottom-anchored panel, safe-area padding,
  3 fields + Apply). No sheet library — one ~60-line component with
  `transform: translateY(100%)` → `0`, used for filters *and* the delete confirm (see 2c).
- **StatsPanel + PowerBests**: below the list, in a `<details>`-style collapsible
  ("Stats" / "Power bests") so the ride list is the first thing on screen.

### 2b. RideDetail — stack, not grid

- **Stat cards**: `auto-fill minmax(180px,1fr)` → `minmax(150px, 1fr)` (2-up on phone),
  or horizontal scroll-snap row if 2-up feels cramped — decide by eye with real data.
  Keep the coloured left border per card (existing, works well, not a tell: it's a
  semantic field marker, not a gray border).
- **Charts**: this is the big one. Six stacked 180px charts with mouse-cursor scrub
  is unusable on touch.
  - **One primary chart** (Power if present, else HR, else Speed) rendered full-width.
  - **Field pill switcher** above it (Elev / Speed / Power / HR / Cad / Temp) —
    tapping swaps the chart's data. Reuses `StreamChart` as-is, just conditional render.
  - **Touch on the chart**: uPlot already handles touch scrub (`setCursor` fires on
    drag) → the synced hover time (map dot, HR zone legend) works with one finger.
    Add: drag-to-select stays (zoom), and a **"Reset zoom" pill** appears once a
    selection exists (sets `selectionRange` null + clears uPlot select). Double-tap
    = also clears, if cheap in uPlot; otherwise skip.
  - Below the primary chart: remaining charts stay stacked (they're there to be found,
    not to be touched constantly).
- **Map**: `min-height: 480px` → `280px` on mobile. MapLibre's native pinch/pan works;
  nothing else to change.
- **Zone cards**: `auto-fill` → horizontal scroll-snap row (they're glance data).
- **Edit form**: full-width, 16px inputs (it's already max-width 480px — fine as-is).
- **Back link**: fine as-is; make it ≥44px tall.

### 2c. Native `confirm()` → bottom sheet

`deleteRide()` uses browser `confirm()` — on iOS Safari this is a raw alert that
blocks the page and looks broken. Route through the Phase-2a bottom-sheet component:
"Delete {name}? [Cancel] [Delete]" (danger accent, ≥44px buttons).

## Phase 3 — State & token extensions

Add to `app.css` (all new, none off-system):

```css
:root {
  /* Mobile */
  --touch: 44px;                          /* min tap-target height */
  --safe-top: env(safe-area-inset-top);
  --safe-bottom: env(safe-area-inset-bottom);
}
button:active, a:active { opacity: 0.85; }          /* pressed feedback, replaces hover-only */
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
:disabled { opacity: 0.5; cursor: not-allowed; }
@media (min-width: 769px) { /* keep desktop hover as-is; don't regress it */ }
```

- Every button/input ≥44px tall below 768px (padding, not height where it'd break
  desktop). The round settings cog gets a 44px hit area (transparent padding).
- `tr:hover td` row highlight already degrades fine (no touch = no hover, no harm);
  keep it.
- **Audit before handoff**: `ux_audit` on the final CSS + pairs
  (`#e6e8ec` on `#181c23` body, `#98a2b3` on `#0f1115` muted, `#fc5200` on `#181c23`
  accent — orange on dark is the one pair to check carefully for APCA).

## Inventory (components + states we ship)

| Component | States |
|---|---|
| Ride card (new) | default / active / focus-visible |
| Sort select (new, mobile) | default / active / focus-visible / disabled |
| Bottom sheet (new: filter + confirm) | default / open / focus-trap-ish / active |
| Field pill switcher (new) | default / active / focus-visible |
| Reset-zoom pill (new) | default / active |
| Button (existing) | + `:active`, `:focus-visible`, `:disabled` |
| Cog / back link | 44px hit area |
| Everything else | unchanged |

## Explicit non-changes

- **No DESIGN.md rewrite**, no new accent/font/scale — existing tokens carry.
- **No bottom tab bar** — two screens + one dialog doesn't need it.
- **No light mode** — dark is the established look; adding a theme is a separate task.
- **No offline data layer** — network-only API, shell-offline. Backend untouched.
- **No new dependencies** — no `vite-plugin-pwa`, no sheet lib, no icon gen tool;
  hand-rolled manifest + SW, one rasterised icon.
- Desktop layout is bit-identical below the 768px breakpoint.

## Suggested order

1. Phase 1 (PWA plumbing) — independent, ships value alone (installable).
2. Phase 3 tokens + states — 1 file, `ux_audit` gate.
3. Phase 2a (list) → 2b (detail) → 2c (sheet reuse) — the actual comfort win.