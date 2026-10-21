---
date_created: 2026-10-20
date_modified: 2026-10-20
title: Design Language
description: The OC HQ design system — DaisyUI-based tokens, typography, spacing, components, and rules every page must follow
---

# OC HQ Design Language

This is the single source of truth for how OC HQ looks and feels. Every page,
component, and PR must follow it. When in doubt, prefer the simpler option that
matches this document — not personal taste.

**Direction:** clean, minimal SaaS — think Linear/Notion. Flat surfaces, subtle
borders, one accent color, comfortable density, no decoration for decoration's
sake.

## The rules in one paragraph

DaisyUI is the base. We ship two custom themes (`hq` light, `hq-dark`) built on
the cmyk palette, selected automatically via `prefers-color-scheme`. Pages never
write DaisyUI variant classes (`btn-primary`, `card`, `badge-success`, …)
directly — they compose `ui/` components (`$lib/components/ui`), which wrap
DaisyUI internally so we can restyle the whole app in one place. Everything is
styled with semantic tokens (`bg-base-100`, `text-base-content`,
`border-base-300`, …) — never raw hex, never arbitrary Tailwind color values.
Inter is the only font. Corners are ~8px. Icons are Lucide. Spacing stays on the
4px grid.

## Principles

1. **Clarity over personality.** This is an internal ops tool. Information wins.
2. **Semantic, not literal.** Colors and radii come from tokens, never values.
3. **One way to do each thing.** If a `ui/` component exists, use it. If it
   doesn't, extend `ui/` — don't freestyle in a page.
4. **Flat by default.** Borders separate surfaces; shadows are only for floating
   layers (menus, dialogs, toasts).
5. **Both themes, always.** Nothing ships that only works in light mode.

---

## Architecture

```
src/app.css                     <- theme definitions + design tokens (only place)
src/lib/components/ui/          <- the component library (shadcn-style API, DaisyUI inside)
src/lib/components/             <- app-specific composed components (sidebar, etc.)
src/routes/                     <- pages: ui components + layout utilities only
```

- **DaisyUI is the implementation, `ui/` is the API.** The `ui/` directory
  contains the component implementations themselves — the only place DaisyUI
  variant classes are written. Route and app
  code imports only from `ui/`. DaisyUI classes may be
  written inside `ui/` components and inside `app.css`. Route files and
  app-level components must not use DaisyUI color/size variant classes.
- **Allowed raw utilities in pages:** layout/spacing/typography utilities
  (`flex`, `grid`, `gap-*`, `p-*`, `text-sm`, `font-medium`, …) and DaisyUI
  utilities with no variants (`divider`, `join`, `skeleton` is via ui).
- **No new custom CSS classes.** The former `hq-*` and `ds-*` styling has been
  replaced by DaisyUI and semantic utilities. Feature-specific layout styles
  may stay scoped to the component that owns that layout.
- **Routes compose; they don't add new `<style>` blocks.** Existing specialized
  layouts are migrated as part of the route-by-route cleanup.

---

## Themes & color

We maintain two DaisyUI themes. Light is derived from **cmyk** with two fixes:
its purple `success` is remapped to green (purple success reads as an error in
an ops UI), and its oversized radii are brought down to our scale. Dark uses
stock `dark` surfaces but with primary/secondary/accent hue-shifted to match the
light theme's brand hues (stock dark's violet primary would read as a different
brand).

### Light theme — `hq` (default)

| Token             | Value (approx) | Usage                                                                       |
| ----------------- | -------------- | --------------------------------------------------------------------------- |
| `base-100`        | `#ffffff`      | cards, panels, popovers, sidebar                                            |
| `base-200`        | `#eeeeee`      | page background, subtle fills                                               |
| `base-300`        | `#dedede`      | borders, dividers, input outlines                                           |
| `base-content`    | `#161616`      | primary text                                                                |
| `primary`         | `#45aeee`      | primary actions, active states, links, focus                                |
| `primary-content` | `#020b13`      | text on primary                                                             |
| `secondary`       | `#e8488a`      | secondary emphasis — **use sparingly**                                      |
| `accent`          | `#fff234`      | highlight marks only (`<mark>`, kbd) — never backgrounds for large surfaces |
| `neutral`         | `#1a1a1a`      | dark neutral elements                                                       |
| `info`            | `#4ba8c0`      | informational alerts/badges                                                 |
| `success`         | `#3db95c`      | success states (custom: replaces cmyk purple)                               |
| `warning`         | `#ee8134`      | warnings                                                                    |
| `error`           | `#e93f33`      | errors, destructive actions                                                 |

### Dark theme — `hq-dark` (`prefersdark`)

| Token          | Value (approx) |
| -------------- | -------------- | ------------------------------- |
| `base-100`     | `#1d232a`      |
| `base-200`     | `#191e24`      |
| `base-300`     | `#15191e`      |
| `base-content` | `#ecf9ff`      |
| `primary`      | `#54b8f7`      | (cmyk blue, lifted for dark bg) |
| `secondary`    | `#fb5d9b`      | (cmyk pink, lifted for dark bg) |
| `accent`       | `#eee455`      | (cmyk yellow, softened)         |
| `success`      | `#00d390`      |
| `info`         | `#00bafe`      |
| `warning`      | `#fcb700`      |
| `error`        | `#ff627d`      |

### Color rules

- **Text:** `text-base-content` for primary text, `text-base-content/60` for
  secondary/meta text, `text-base-content/40` for placeholders/hints. Never
  `text-gray-*` or hex.
- **Surfaces:** page background `bg-base-200`; cards/panels/sidebar/topbar
  `bg-base-100` with `border-base-300` borders. Do not nest `base-100` on
  `base-100` without a border.
- **Primary is the only action color.** One `variant="primary"` button per
  view, at most one per card/section. Secondary actions use `outline` or
  `ghost`.
- **Status colors** (`success`, `warning`, `error`, `info`) appear only in
  badges, alerts, dots, and toasts — never as button colors, except
  `variant="destructive"` which renders a soft-error button.
- **Tints** (e.g., badge backgrounds, active nav) use opacity modifiers or
  `color-mix`: `bg-primary/10`, `bg-error/10`. Never invent a second hex.
- **Charts** map `chart-1..5` → `primary`, `success`, `warning`, `secondary`,
  `error` in that order.

### Reference implementation (target state of `app.css`)

```css
@plugin "daisyui" {
  themes:
    hq --default,
    hq-dark --prefersdark;
}

@plugin "daisyui/theme" {
  name: "hq";
  default: true;
  color-scheme: light;

  /* surfaces — cmyk */
  --color-base-100: oklch(100% 0 0);
  --color-base-200: oklch(95% 0 0);
  --color-base-300: oklch(90% 0 0);
  --color-base-content: oklch(20% 0 0);
  --color-primary: oklch(71.772% 0.133 239.443);
  --color-primary-content: oklch(14.354% 0.026 239.443);
  --color-secondary: oklch(64.476% 0.202 359.339);
  --color-secondary-content: oklch(12.895% 0.04 359.339);
  --color-accent: oklch(94.228% 0.189 105.306);
  --color-accent-content: oklch(18.845% 0.037 105.306);
  --color-neutral: oklch(21.778% 0 0);
  --color-neutral-content: oklch(84.355% 0 0);
  --color-info: oklch(68.475% 0.094 217.284);
  --color-info-content: oklch(13.695% 0.018 217.284);
  /* custom: green success instead of cmyk purple */
  --color-success: oklch(69.6% 0.171 148.3);
  --color-success-content: oklch(15% 0.04 150);
  --color-warning: oklch(71.236% 0.159 52.023);
  --color-warning-content: oklch(14.247% 0.031 52.023);
  --color-error: oklch(62.013% 0.208 28.717);
  --color-error-content: oklch(12.402% 0.041 28.717);
  --color-chart-1: var(--color-primary);
  --color-chart-2: var(--color-success);
  --color-chart-3: var(--color-warning);
  --color-chart-4: var(--color-secondary);
  --color-chart-5: var(--color-error);

  /* shape — see Radius */
  --radius-selector: 0.375rem;
  --radius-field: 0.5rem;
  --radius-box: 0.625rem;
  --border: 1px;
  --depth: 0;
  --noise: 0;
}

@plugin "daisyui/theme" {
  name: "hq-dark";
  prefersdark: true;
  color-scheme: dark;

  --color-base-100: oklch(25.33% 0.016 252.42);
  --color-base-200: oklch(23.26% 0.014 253.1);
  --color-base-300: oklch(21.15% 0.012 254.09);
  --color-base-content: oklch(97.807% 0.029 256.847);
  /* brand hues lifted from cmyk */
  --color-primary: oklch(75% 0.13 239.443);
  --color-primary-content: oklch(17% 0.03 239.443);
  --color-secondary: oklch(70% 0.2 359.339);
  --color-secondary-content: oklch(16% 0.04 359);
  --color-accent: oklch(90% 0.16 105.306);
  --color-accent-content: oklch(25% 0.04 105);
  --color-neutral: oklch(14% 0.005 285.823);
  --color-neutral-content: oklch(92% 0.004 286.32);
  --color-info: oklch(74% 0.16 232.661);
  --color-info-content: oklch(29% 0.066 243.157);
  --color-success: oklch(76% 0.177 163.223);
  --color-success-content: oklch(37% 0.077 168.94);
  --color-warning: oklch(82% 0.189 84.429);
  --color-warning-content: oklch(41% 0.112 45.904);
  --color-error: oklch(71% 0.194 13.428);
  --color-error-content: oklch(27% 0.105 12.094);
  --color-chart-1: var(--color-primary);
  --color-chart-2: var(--color-success);
  --color-chart-3: var(--color-warning);
  --color-chart-4: var(--color-secondary);
  --color-chart-5: var(--color-error);

  --radius-selector: 0.375rem;
  --radius-field: 0.5rem;
  --radius-box: 0.625rem;
  --border: 1px;
  --depth: 0;
  --noise: 0;
}
```

The old shadcn-style alias layer (`--background`, `--foreground`, `--card`,
`--muted`, `--sidebar-*`, …) is **removed**. Components reference DaisyUI tokens
directly (`bg-base-100`, `text-base-content/60`, `border-base-300`, …).

---

## Typography

**One family: Inter Variable** (`@fontsource-variable/inter`). It replaces both
Figtree and DM Sans — hierarchy comes from size/weight/color, not a second font.

| Level   | Size / leading       | Weight | Tracking        | Use                                    |
| ------- | -------------------- | ------ | --------------- | -------------------------------------- |
| Display | `text-3xl` (30/36)   | 700    | `-0.02em`       | Empty-state heroes only — rare         |
| H1      | `text-2xl` (24/32)   | 600    | `-0.015em`      | Page title — one per page              |
| H2      | `text-lg` (18/28)    | 600    | `-0.01em`       | Section titles                         |
| H3      | `text-base` (16/24)  | 600    | `0`             | Card titles, subsections               |
| Body    | `text-sm` (14/20)    | 400    | `0`             | **Default UI text**                    |
| Label   | `text-sm` (14/20)    | 500    | `0`             | Form labels, strong inline text        |
| Small   | `text-[13px]`        | 400    | `0`             | Descriptions, meta, timestamps         |
| Caption | `text-xs` (12/16)    | 600    | `+0.05em` upper | Overlines, table headers, group labels |
| Mono    | `text-sm` mono stack | 400    | `0`             | IDs, codes, ledger refs                |

Rules:

- Body text is `text-sm`. `text-base` is reserved for H3-level headings and
  long-form reading.
- Secondary text is always `text-base-content/60`, never a smaller gray hack.
- Table headers use Caption styling (`text-xs font-semibold uppercase
tracking-wider text-base-content/60`).
- Numbers in tables/financial data: `tabular-nums`.
- Mono stack: `ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace` — no
  shipped mono web font for now.
- Never set `font-family` outside `app.css`. Never use `font-extrabold`/`black`.
- Weights in use: 400, 500, 600, 700. Nothing else.

---

## Spacing, sizing & density

Density is **comfortable**: breathing room by default, compaction only where
data demands it.

- **4px grid.** Use Tailwind spacing steps only (`1,2,3,4,5,6,8,10,12,16,20,24`).
  No arbitrary `p-[13px]`-style values.
- **Page:** `max-w-[1440px] mx-auto px-6 py-6` (mobile: `px-4 py-4`). Sections
  separated by `gap-6`/`space-y-6`.
- **Page header:** H1 + optional description (Small, `/60`) + right-aligned
  actions, separated from content by `mb-6`.
- **Cards:** `p-5` default (`p-6` for feature cards), internal `gap-4`.
- **Forms:** fields stacked `gap-4`, field groups `gap-6`, label-to-input `gap-1.5`.
- **Control heights:** sizes follow one scale — `xs`/`sm`/`md`/`lg`/`xl`
  mapping to DaisyUI `btn-*`/`tabs-*` size classes. Default is `md` (~40px) for
  buttons/inputs. Use `sm` (~32px) only inside toolbars, table rows, and dense
  repeated controls. `xs`/`lg`/`xl` are for exceptional density/emphasis — ask
  first. Never mix sizes in the same row. Icon-only buttons add the `icon`
  prop (`btn-square`) instead of a separate size.
- **Tables:** default `table` (md). `table-sm` allowed for data-dense admin/log
  views. `table-xs` reserved for audit-ledger-level density — ask first.
- **Icon+text gap:** `gap-2` in buttons/nav items, `gap-1.5` in compact rows.

---

## Border radius

Medium (~8px), graded slightly by element size so small controls don't look
blobby. Defined once in the themes via `--radius-*` (DaisyUI) — never set
`rounded-*` values that disagree.

| Element                                  | Radius | Token               |
| ---------------------------------------- | ------ | ------------------- |
| Inputs, buttons, selects, badges, alerts | 8px    | `--radius-field`    |
| Cards, dialogs, dropdowns, panels        | 10px   | `--radius-box`      |
| Checkboxes, toggles, radios              | 6px    | `--radius-selector` |
| Avatars, dots, pill badges               | full   | `rounded-full`      |

Tailwind scale is mapped to match: `rounded-md`→6px, `rounded-lg`→8px,
`rounded-xl`→10px. Everything else on this list gets `rounded-full` or nothing.

---

## Elevation & borders

- **Flat surfaces.** Cards, panels, and the sidebar are separated by
  `border border-base-300` — **no shadows** on resting elements.
- **Floating layers only:** dropdowns/popovers/tooltips get `shadow-md`;
  dialogs and toasts get `shadow-xl`. That's the entire shadow vocabulary.
- No gradients, no glows, no `depth` effects (`--depth: 0` in both themes).
- Dividers: `border-base-300` or DaisyUI `divider` — never darker than base-300.

---

## Icons

- **Lucide only** via `@lucide/svelte`. No other icon sets, no inline SVGs, no
  emoji as UI icons.
- Sizes: `size-4` (16px) inside buttons, nav, inputs, dropdowns; `size-5`
  (20px) for standalone/header icons; `size-3.5` (14px) in compact table cells;
  `size-10` with `stroke-width={1.5}` for empty-state illustration.
- `stroke-width={2}` everywhere (1.5 only for large empty-state icons).
- Decorative icons get `aria-hidden="true"`; interactive icon-only buttons get
  an `aria-label` and use `variant="ghost" icon`.
- Icons inherit `currentColor` — tint with `text-*` classes, not `stroke` props.

---

## Components

All UI lives in `src/lib/components/ui/` with a shadcn-style compositional API
(`Card.Header`, `Table.Row`, …), implemented internally with DaisyUI classes.
When DaisyUI lacks a primitive (combobox, dialog behavior), the `ui/` component
builds it on native elements — that logic never leaks into pages.

### Standard variant taxonomy

| Variant       | Renders as (DaisyUI) | Use                                   |
| ------------- | -------------------- | ------------------------------------- |
| `primary`     | `btn-primary`        | The one main action                   |
| `secondary`   | `btn-secondary`-soft | Rare; only when two primaries compete |
| `outline`     | `btn-outline`        | Default secondary action              |
| `ghost`       | `btn-ghost`          | Tertiary, icon buttons, toolbars      |
| `destructive` | `btn-soft btn-error` | Delete/destructive — always soft      |
| `link`        | `btn-link`           | Inline text actions                   |

Sizes: `sm` | `md` (default) | `lg` | `icon` | `icon-sm`. No other names.

### Component notes

- **Button** — never a raw `<button>` or `btn` class in routes; always
  `ui/button`.
- **Inputs** — `ui/input`, `ui/textarea`, `ui/select`, `ui/checkbox`,
  `ui/switch` only. Always wrapped in `ui/field` (label + description + error).
- **Card** — `bg-base-100 border-base-300 rounded-xl` internally; padding from
  the spacing rules.
- **Table** — header row uses Caption styling; row hover `bg-base-200/50`;
  last column right-aligned for actions/numbers; numbers `tabular-nums`.
- **Badge** — soft variants only (`badge-soft badge-<color>`); status colors
  per the color rules.
- **Dialog** — `ui/dialog`; `max-w-lg` default, `max-w-2xl` for forms; footer
  buttons right-aligned (cancel `outline` left of confirm `primary`).
- **Dropdown/Popover** — `shadow-md`, `border-base-300`, item height 32px.
- **Toast/Alert** — `alert-soft`; one per event, auto-dismiss except errors.
- **Empty state** — `ui/empty`: icon (`size-10`, muted), H3 title, Small
  description, one primary action max.
- **Loading** — `ui/skeleton` matching the content's shape; `spinner` only for
  inline/button loading states. No full-page spinners.

### Migration targets (what dies in the refactor)

- `src/lib/components/design/` (`ds-*` components) → merged into `ui/`, deleted.
- `src/lib/components/native/` → flattened into `ui/` (components now live
  there directly).
- All `hq-*` classes in `app.css` and component `<style>` blocks → replaced by
  Tailwind utilities + DaisyUI tokens. `app.css` keeps only theme definitions
  and base-layer globals.

---

## App shell & layout

- **Sidebar:** fixed `w-60` (240px), `bg-base-100`, `border-r border-base-300`,
  `p-4`. Nav sections have a Caption overline, items are `h-9 rounded-md px-3
text-sm font-medium gap-2` with `size-4` icons. Active item:
  `bg-primary/10 text-primary font-semibold`; hover: `bg-base-200`.
- **Topbar:** `h-14` sticky, `bg-base-100/80 backdrop-blur`, `border-b
border-base-300`, `px-6`.
- **Content:** per the page rules in Spacing. Lists/tables get Card surfaces;
  dashboards use `grid gap-6` with `grid-cols-12`-style spans.
- **Responsive:** sidebar collapses below `lg`; pages must be usable at 360px.
- **Breadcrumbs:** `text-sm`, current page `text-base-content`, parents `/60`.

---

## States & motion

- **Hover:** background shift to `base-200` (or `/10` tint for colored items).
  No scale transforms on hover.
- **Focus:** global `:focus-visible` ring — `2px` outline in `primary` at ~50%
  opacity, `2px` offset. Never remove it without a replacement.
- **Active/pressed:** slightly darker tint (`base-300` or `/20`), no transform.
- **Disabled:** `disabled` attribute + DaisyUI's disabled styling — never
  hand-rolled `opacity-50` or `pointer-events-none` hacks.
- **Transitions:** `transition-colors` 150ms for hover/focus; overlays may add
  `duration-200` opacity/translate. No springs, no bounces, nothing >300ms.

---

## Dark mode

- Automatic via `prefers-color-scheme` (no toggle for now).
- Everything must pass in both themes. Before shipping a view, check it dark.
- Tints/overlays use opacity modifiers (`bg-base-content/5`), which adapt
  automatically — never light-only color-mixes.

---

## Do / Don't

| Do                                                    | Don't                                        |
| ----------------------------------------------------- | -------------------------------------------- |
| `ui/button` with `variant`/`size`                     | `<button class="btn btn-primary">` in routes |
| `bg-base-100`, `border-base-300`, `text-base-content` | `bg-white`, `text-gray-700`, any hex         |
| `text-base-content/60` for secondary text             | `text-gray-400` / opacity hacks on wrappers  |
| Tailwind spacing steps                                | arbitrary `p-[13px]` / magic margins         |
| `rounded-lg`/`rounded-xl`/`rounded-md` per the table  | `rounded-3xl`, `rounded-sm`, mixed radii     |
| `bg-primary/10` tinted fills                          | a second blue hex "that's close enough"      |
| Skeletons shaped like content                         | centered spinner as page loading state       |
| Lucide `size-4`/`stroke-width=2`                      | heroicons, inline SVG, emoji icons           |
| `ui/field` around every input                         | bare `<input>` + floating `<label>`          |
| One primary action per view                           | three `btn-primary` in a card footer         |

---

## Refactor checklist

1. Replace `@fontsource-variable/dm-sans` + `figtree` with
   `@fontsource-variable/inter`; set `--font-sans` in `@theme`.
2. Rewrite `app.css`: define `hq` + `hq-dark` themes, delete the shadcn alias
   layer and all `hq-*` classes.
3. Consolidate `native/` + `design/` → `ui/`; update all imports.
4. Rebuild the shell (sidebar/topbar/page) with Tailwind utilities.
5. Sweep every route: remove `<style>` blocks, hex/arbitrary colors, `ds-*`,
   `hq-*`, raw `btn`/`card`/`badge` classes → `ui/` components.
6. Type scale + table header (Caption) pass on every view.
7. Verify both themes on every route.
