---
name: Overview timeline polish
overview: Tighten Overview chips and times (S1 labels, day-focus fade, unclipped pick ring, wrapping boat title, left-aligned cells, one-line heading), and sort the Timeline day summary in chronological order.
todos:
  - id: ov-cells
    content: "Overview: S1 chips, left-align, wrap/hyphen labels, unclip pick ring"
    status: completed
  - id: ov-fade
    content: "Day-focus: fade irrelevant start/end times in place (no rerender pop)"
    status: completed
  - id: ov-head
    content: One-line Overview heading; taller grid and larger time type
    status: completed
  - id: summary-verify
    content: "daySummary: chronological parts; rebuild dist and check Friday fade, Saturday ring, Monday summary"
    status: completed
isProject: false
---

# Overview chips, times, and Timeline summary

Work in [`site/app.js`](site/app.js) and [`site/app.css`](site/app.css). Rebuild `dist/`. No spreadsheet edits.

## 1.1 Section chips: `S1 · …`

In `renderOverviewCell`, chips currently use the full word:

```1150:1150:site/app.js
s ? `${t('section')} ${s.id} · ${L(s.short)}` : `${t('section')} ${b.section}`
```

Use `S${id}` (same in RU/EN): `S1 · Nuclear structure`. Timeline, now-card, and print Timeline stay “Section 1”. Overview print clones the live chips, so it picks this up.

## 1.2 Day focus: fade unused times (no pop)

Week ticks stay (rows stay proportional). When `state.overviewFocus` is a day, keep a start/end label only if that clock is a **start or end of that day’s bands**. Friday then loses Monday `08:00`, Thursday `15:00`, Welcome `18:30`, etc.

`renderMain()` on every day click rebuilds the grid, so labels would pop. For Overview `setDay`, skip `renderMain()` and mutate the live grid:

- Toggle `.is-day-focus` / `.is-focus` on cells (same as today)
- Collect `data-start`/`data-end` from `.overview-cell[data-day=focus]`
- Toggle `.is-idle` on each `.t-start` / `.t-end` independently

CSS: `opacity` + `transition` on `.t-start`/`.t-end` (`var(--dur)` / `--ease`). `.is-idle { opacity: 0 }`. Do not `display: none`. Reduced-motion already collapses transitions.

Print clone already strips focus; also strip `.is-idle` so the PDF keeps the full time axis.

## 1.3 Picked ring clipped on Saturday

`.overview-cell.is-picked` uses `box-shadow: 0 0 0 2px`. Saturday is the last column; [`.overview-wrap`](site/app.css) is `overflow-x: auto; overflow-y: hidden`, so the 2px ring is cut on the right (screenshot).

Give the wrap `padding: 3px` (and a matching negative margin if the grid shift is visible) so the ring has room on all sides. Keep the outer ring; do not switch to inset.

## 1.4 Hyphenate long Overview titles

`.overview-label` is `white-space: nowrap; text-overflow: ellipsis`, so Boat becomes `Boat excursion on…` even in a tall cell.

For cells that are not coffee/lunch, allow wrap: `white-space: normal; overflow-wrap: break-word; hyphens: auto` (`html[lang]` is already `en`/`ru`). Short break rows stay nowrap so 30 min coffee does not try to wrap inside 23px.

## 1.5 Left-align all Overview cells

Remove `justify-content: center; text-align: center` from `.overview-cell.plenary-band`. Flex default is left; keep `align-items: center` for vertical centering of icon + text.

## 1.6 One-line heading, larger times

Replace Overview’s two-line head (`h1` Overview + `p` Schedule) with one title, same pattern as Timeline’s dim suffix:

`Overview · Schedule` (`page-title` + `.dim`).

Use the saved height: `.overview` `42rem` → `48rem`, and bump time type from `0.62`/`0.56rem` toward `0.72`/`0.64rem` so both lines still fit a 30 min row.

## 2.1 Timeline day summary in time order

[`daySummary`](site/app.js) always prepends plenary count, then section count, then socials — so Monday is `7 plenary talks · 4 parallel sections · Registration · …`.

Walk that day’s blocks by `start`. Emit each of registration / opening / closing / social / poster when it occurs. Emit the plenary count once at the first plenary/jubilee, and the parallel-sections count once at the first section. Still omit coffee/lunch. Expected Monday: `Registration · Opening ceremony · 7 plenary talks · 4 parallel sections · Welcome party`.

## Verify

- Overview chips read `S1 · …`; plenary/coffee/social left-aligned; Boat wraps with hyphens, not ellipsis
- Saturday plenary pick: full 2px ring visible on the right
- Click Friday (or Saturday): unused times fade out; click again: they fade back; grid rows do not jump
- Overview heading is one line; time labels read larger
- Timeline Monday summary starts with Registration
- `python tools/build.py`