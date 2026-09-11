---
name: Keep scroll on lang
overview: Language switch rebuilds the whole page and then auto-scrolls to the selected day’s start. Skip that day jump, restore scroll after layout, and on Timeline re-anchor to the talk that was on screen so RU/EN reflow does not slide to the next card.
todos:
  - id: preserve-lang-scroll
    content: preserveScroll(renderAll) on lang; rAF Y restore; re-anchor visible slot; scrollToSlot behavior option
    status: completed
  - id: verify-lang-scroll
    content: EN/RU toggle on Kovalenko (desktop + SE) and Sections; rebuild dist
    status: completed
isProject: false
---

# Keep scroll position when switching language

Switching RU/EN runs `withTransition(renderAll)` in [`site/app.js`](site/app.js) (~line 1966). `renderAll` rebuilds the schedule. `viewSchedule` then always jumps to the selected day on the next frame unless `_skipScroll` is set:

```931:944:site/app.js
requestAnimationFrame(() => {
  ...
  if (state.day && !viewSchedule._skipScroll) {
    const chunk = document.querySelector(`.day-chunk[data-day="${state.day}"]`);
    if (chunk) chunk.scrollIntoView({ behavior: 'auto', block: 'start' });
  }
  viewSchedule._skipScroll = false;
});
```

That is the jump: mid-Tuesday plenary → Tuesday morning (or the top of the page). Filters, Expand all, and the now-tick already avoid it via `preserveScroll`. Language switch does not.

RU titles and dates are longer, so restoring raw `scrollY` alone can still land on the **next** talk after wrap. Re-anchor to the slot that was on screen.

## Change

In [`site/app.js`](site/app.js):

1. Lang button: `preserveScroll(renderAll)` instead of `withTransition(renderAll)`. Still toggle `state.lang` and `store.set('lang', …)`.

2. Extend `preserveScroll` (used only for in-place rebuilds):
   - Before `fn()`, record `window.scrollY` and the first `.slot` whose bottom is below the sticky date (same chrome idea as `scrollToSlot`).
   - Set `viewSchedule._skipScroll = true` so the day-start `scrollIntoView` does not run.
   - After `fn()`, restore `scrollY`, then `requestAnimationFrame` restore again (empty `#main` collapses the document and can clamp Y to 0 before layout).
   - If the saved slot id still exists, call `scrollToSlot(el, { behavior: 'auto' })` so the same talk sits under the date after reflow.

3. Give `scrollToSlot` an optional `behavior` (`auto` vs smooth). Lang restore must be instant; NOW-card clicks stay smooth.

No CSS, hash, or spreadsheet changes. Other views (Sections, etc.) keep pixel `scrollY` restore.

## Verify

From `?now=2026-09-22T11:05#view=schedule&day=2026-09-22`, jump to Коваленко, then toggle RU/EN (desktop and iPhone SE):

- Stay on plenary 9 (Коваленко), not Tuesday 09:00 and not Мочалов.
- Hash stays `#view=schedule&day=2026-09-22`.
- Sections: scroll mid-list, toggle language, do not jump to the top.

`python tools/build.py` (no FTP).
