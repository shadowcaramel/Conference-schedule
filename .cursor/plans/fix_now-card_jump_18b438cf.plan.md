---
name: Fix now-card jump
overview: NOW-card links scroll the target slot to the viewport top, under the sticky top bar, day bar, and date line, so the current plenary is hidden and the next talk looks selected. Offset the jump by that chrome so the chosen talk sits just below the date.
todos:
  - id: scroll-to-slot
    content: Add scrollToSlot helper + CSS .slot scroll-margin; wire NOW-item click
    status: completed
  - id: verify-now-jump
    content: Browser-check Kovalenko/Mochalov jumps at now=2026-09-22T11:05 on desktop and iPhone SE; rebuild dist
    status: completed
isProject: false
---

# Fix NOW-card jump landing on the next talk

The NOW chip for Коваленко (until 11:30 at `?now=2026-09-22T11:05`) already finds the right `.slot` (`id="slot-{start}{date}"` in [`site/app.js`](site/app.js)). The click handler then calls `scrollIntoView({ block: 'start' })` with **no** offset:

```1291:1291:site/app.js
return el('a', { class: 'now-item', href: `#slot-${b.start.replace(':', '')}-${b.date}`, ... onclick: (e) => { e.preventDefault(); const target = document.getElementById(...); if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' }); } },
```

`.slot` has no `scroll-margin-top`. Sticky chrome covers the slot once it is pinned to the top: `#topbar` (inner bar + day bar) plus [`.day-chunk-head`](site/app.css) (the date line). A plenary card is about that tall, so Коваленко ends up under the header and Мочалов is the first visible talk. Same one-slot overshoot for Мочалов → Белов.

Day jumps already pad for the top/day bars (`.day-chunk { scroll-margin-top: calc(var(--topbar-h) + var(--daybar-h) + 8px) }`). Slot jumps never got the extra date-line offset.

Language-switch scroll is **out of this pass** (keep position on RU/EN later).

## Change

In [`site/app.js`](site/app.js), add `scrollToSlot(el)` used by the NOW-item click:

- Measure `#topbar` bottom (day bar lives inside the header, so this is the real chrome height).
- Add the target day’s `.day-chunk-head` height (covers a wrapping RU date, not a fixed `2.1rem`).
- `window.scrollTo` so the slot top sits ~8px below that stack.
- Honor `prefers-reduced-motion`.
- Set `ignoreDayObs` for ~600ms so the day observer does not fight the smooth scroll.

Keep `preventDefault` so the `href` cannot replace `#view=schedule&day=…` with `#slot-…` (that would fire `hashchange` / `applyHash`).

In [`site/app.css`](site/app.css), give `.slot` a matching `scroll-margin-top` (same formula as `.slot-time` sticky top, plus 8px) so a native fragment scroll would also clear the date line.

Do not change slot ids, NOW matching, or Overview.

## Verify

Same URL: `?now=2026-09-22T11:05#view=schedule&day=2026-09-22`. On **both** desktop (≥720px) and **iPhone SE** (375×667; phone top bar is 72px and the date can wrap):

- NOW → Коваленко: Tuesday date stays stuck; plenary card for Коваленко is fully visible under it (title not clipped); Мочалов is the next card, not the first.
- NOW NEXT → Мочалов: lands on Мочалов, not Белов / Lunch.

Then `python tools/build.py` (no FTP).
