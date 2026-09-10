---
name: Overview section panes
overview: Replace overflowing Overview section chips with one plenary-like cell split into equal colored S1/S2 panes, drop hyphenation, center cell contents, and shorten Opening/Closing/Welcome labels in Overview only.
todos:
  - id: sec-panes
    content: Render Overview sections as horizontal colored S# panes
    status: cancelled
  - id: align-hyphen
    content: Center Overview cell content; drop hyphenation
    status: cancelled
  - id: short-titles
    content: Overview-only short Opening/Closing/Welcome labels
    status: cancelled
  - id: verify-viewports
    content: Rebuild dist; desktop+mobile EN/RU clutter check
    status: cancelled
isProject: false
---

# Overview section panes and shorter labels

Work in [`site/app.js`](site/app.js) and [`site/app.css`](site/app.css). Rebuild `dist/`. No spreadsheet edits. Timeline titles stay long.

## 1. One section band, colored S# panes

`mergeDayBands` already groups consecutive section blocks into one cell. Overflow comes from stacked chips (`S1 · Nuclear structure` …) inside [`.overview-secs`](site/app.css) with `overflow: hidden` (screenshot: S6 clipped).

In `renderOverviewCell`, replace the chip stack with a **horizontal split** of equal panes (one unique section id each, existing order):

```html
<div class="overview-cell sections" aria-label="S1 Nuclear structure, S2 …">
  <div class="overview-sec-split">
    <span class="overview-sec-pane" data-color="blue">S1</span>
    …
  </div>
</div>
```

CSS: `.overview-sec-split` is `display: flex; flex: 1; gap: 2px; min-height: 0; border-radius: 6px; overflow: hidden`. Each pane `flex: 1`, `--sec-tint` / `--sec-text`, **centered** `S1`. Cell padding ~3px so the split reads as one block (like plenary), not four cards. Whole cell stays one click/highlight target.

`aria-label` keeps full short names for AT. Print clones the live grid.

## 2. Center block contents

With S# panes, center everything that is not a column header: `.overview-cell { justify-content: center; text-align: center }` (keep `align-items: center`). `.overview-cell.sections` stays `align-items: stretch` so panes fill the cell. Verify in browser vs left; ship center unless a type is clearly worse (coffee/lunch can stay centered too).

## 3. No hyphenation

Remove `.overview-cell:not(.kind-break):not(.kind-lunch) .overview-label` `hyphens` / `-webkit-hyphens`. Long social titles may still wrap on spaces (`white-space: normal; overflow-wrap: break-word`) in tall cells; no mid-word breaks. Coffee/lunch stay `nowrap`.

## 4. Overview-only short titles

`blockTitle` / spreadsheet strings stay for Timeline. Add `overviewBandLabel(band)` used only in Overview:

- `opening` → existing `BLOCK_TYPE_LABEL` **Opening** / **Открытие**
- `closing` → **Closing** / **Закрытие**
- social whose ru/en title matches `/фуршет|welcome party/i` → **Фуршет** (ru) / **Welcome party** (en)
- else `blockTitle` / plenary group label as now

Icon + shortened word must fit one line at ~390px column width (Overview still `min-width: 52rem` + horizontal scroll).

## Verify (desktop + phone, EN + RU)

- Monday/Friday afternoon: one section cell, 3–4 color panes, no clipped fifth chip; time axis unchanged
- Saturday: Opening/Closing (EN) and Открытие/Закрытие (RU) one line on desktop and ~390px-wide column
- Welcome: RU **Фуршет** one line; EN Welcome party
- Boat wraps on spaces, no hyphenation
- Plenary/section/coffee left-vs-center: confirm centered S# and plenary look even
- Pick-ring still unclipped on Saturday; day-focus time fade still works
- `python tools/build.py`