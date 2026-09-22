---
name: Section print sheets
overview: Keep the full-programme print, with each day on its own pages. On the Sections tab, print only the selected chip — plenary talks from the plenary chip, or that section’s oral talks alone.
todos:
  - id: section-sheet
    content: "Branch renderPrint: plenary chip prints section P only; a numbered section prints its oral sittings only, days as .p-day"
    status: completed
  - id: day-pages
    content: Wrap full-programme days and posters in .p-day so each starts on its own page
    status: completed
  - id: print-css-label
    content: Page-break CSS, page counter, and Sections footer label
    status: completed
  - id: coffee-room
    content: Set every coffee-break block room to 235ц and rebuild so timeline and print show the assembly hall
    status: completed
isProject: false
---

# Per-section print, days on their own pages

The footer print button and Ctrl+P both call `renderPrint()` in [site/app.js](site/app.js). Today that is either the landscape overview or the entire programme in one continuous flow. Day headings (`h2`) do not start a new page, so a page range cannot isolate one day.

## Behaviour

- **Schedule overview:** unchanged landscape sheet.
- **Any other view except Sections:** full programme, as now, plus posters. Each day, and the poster list, is wrapped in `<section class="p-day">`. Later days use `break-before: page`, so day 1 shares the title page and every following day starts on a fresh page. A day that runs long keeps exclusive pages; the next day never begins mid-page. Print preview page numbers are the range to enter in the dialog.
- **Sections tab:** only the chip that is selected. Plenary and section orals stay apart, because a chair needs their own sittings and because they are in different rooms (plenary and anniversary talks are in the assembly hall; each section sitting has its own room).
  - Chip `P` ([`#view=sections&section=P`](http://nucleus.togudv.ru/timetable/#view=sections&section=P)): blocks with `section === 'P'` only — the plenary tab (plenary, anniversary, and sponsor talks that already live on that chip). No section orals.
  - Chip `1`–`7`: blocks with `type === 'section'` and `section ===` that id only. No plenary, anniversary, or sponsor talks, even when a speaker or chair also has a talk on the plenary tab.
  - Header is the section number and title (or “Пленарные доклады”), chairs for a numbered section (`sittingChairs`), and the sitting room from `roomOf(b)` — not a shared plenary room. Body matches the on-screen section view: days, then sittings (time, room, sitting chair), then talks (number, start, title, speaker, organisation). Cancelled and moved talks keep a short status mark. Each day of that sheet is its own `.p-day`, so a chair prints one day by page range. Posters stay off this sheet.

The on-screen filter is already `b.section === s.id`. The print uses that same split and does not add talks from other block types.

Switching section chips does not need a new button. `beforeprint` already rebuilds the sheet from the current selection. The footer label becomes “Печать секции” / “Print section” while `state.view === 'sections'` (`setView` already calls `renderFooter`).

## Coffee breaks

All 10 `break` blocks in [site/data.js](site/data.js) have no room. The timeline only prints a room when `roomOf(b)` is set ([renderBlock](site/app.js)), so coffee shows as a title alone. Print uses `roomLabel`, which falls back to “уточняется” / “to be confirmed”.

Set **Аудитория** to `235ц` on every `перерыв` row in `data/programme.xlsx`, then `python tools/build.py`. [tools/common.py](tools/common.py) already expands that code to `235ц, Актовый зал` / `235ц, Assembly Hall`. No display change: the timeline meta line, the full-programme print, and the section sheets all read the same block room. Lunch rows stay without a room.

Note the same rule in one line of [README.md](README.md) and [data/inconsistencies.md](data/inconsistencies.md), next to the existing “always `235ц`” list.

## Layout

In [site/app.css](site/app.css), under the existing print rules:

- `.print-root .p-day + .p-day { break-before: page; }`
- Detail `@page` keeps the current margins and adds a page counter (`@bottom-center { content: counter(page); }`) via `setPrintPage`, so ranges are visible in the preview. Overview stays a single landscape page without that counter.

## Check

Open the Sections tab, select a section that meets on more than one day, emulate print, and confirm the print root lists only that section’s oral talks (no plenary ids) and each later day has `break-before: page`. Select the plenary chip and confirm the sheet lists only section `P` (assembly hall), with no section orals. Repeat for the full programme: day 2 and posters start a new page; the overview sheet stays one landscape page. On the timeline and in the full-programme print, each coffee break shows `235ц, Актовый зал` / `235ц, Assembly Hall`, not “to be confirmed”.
