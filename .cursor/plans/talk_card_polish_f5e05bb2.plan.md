---
name: Talk card polish
overview: Raise the title–presenter gap to 10px, let section titles wrap to two lines at equal header height, keep the show/hide control in one place (not a fifth column), and stick slot times in mid-viewport so they no longer cover the day heading.
todos:
  - id: gap-10
    content: Change .t-speaker padding-top from 8px to 10px
    status: completed
  - id: sec-name-wrap
    content: Allow .sec-name to wrap (max 2 lines); keep equal header height via existing stretch/subgrid
    status: completed
  - id: sticky-mid
    content: Stick .slot-time at mid-viewport; stop overlapping .day-chunk-head
    status: completed
  - id: toggle-place
    content: Keep show/hide in the top-right row (no extra column); offset .slot-time to the section headers
    status: completed
  - id: verify-ui
    content: Rebuild dist; check gap, wrapped headers, sticky time, toggle position, mobile/dark
    status: completed
isProject: false
---

# Talk cards, headers, sticky time, show/hide

All of this is CSS in [`site/app.css`](site/app.css) except the gap token already on `.t-speaker`. No FTP.

## 1. Title–presenter gap 8px to 10px

On `.talk .t-speaker`, change `padding-top: 8px` to `10px`. Keep it as padding inside the card (not `.parallel-grid` `row-gap`) so hover/`is-now` still fill the cell.

## 2. Section names wrap; headers share height

`.sechead .sec-name` is `white-space: nowrap` + ellipsis, so EN “Section 3 · Methods and technologies” and RU “Секция 7 · Ядерная медицина” clip.

- Drop `nowrap` / `text-overflow: ellipsis` / `inline-flex`.
- Allow wrapping, cap at two lines (`-webkit-line-clamp: 2` / `line-clamp: 2`).
- `overflow-wrap: break-word` so a long last word can split if needed.

Equal height is already there: collapsed cards share one grid row (`align-items: stretch`, `.sechead { height: 100% }`); expanded cards share the subgrid header track. A two-line name grows that row for every section in the slot.

## 3. Sticky time: mid-page, not on top of the day title

`.slot-time` uses `top: calc(var(--topbar-h) + var(--daybar-h) + 2.1rem)`. That 2.1rem is shorter than sticky [`.day-chunk-head`](site/app.css) (“Tuesday 22 September”), so the time rides up into the day title (screenshot 1).

Set sticky `top` to about **mid-viewport** (e.g. `45vh` / `45dvh`), so while you scroll a long parallel slot the time stays in the middle of the screen and never meets the day heading. At the start of the slot it still sits in normal flow next to the headers; sticky only engages after that point scrolls up to mid-view.

Update `.slot` `scroll-margin-top` so it no longer assumes the old `+ 2.1rem` pin.

## 4. Show talks stays where Hide talks is; time lines up with headers

Today the toggle moves:

- **Talks shown:** `.parallel` is one column — Hide talks is a row *above* the cards (`justify-self: end`). `.slot-time` is `align-self: start`, so the clock lines up with that button, not the headers (screenshot 3).
- **Talks hidden:** a second grid column is added for Show talks, squeezing the four headers (screenshot 2 vs 3).

Always use the Hide-talks layout at `min-width: 900px`: toggle on its own row above the cards, `justify-self: end`. Remove the collapsed-only `grid-template-columns: minmax(0, 1fr) auto` block (~lines 553–564). Show talks then occupies the same top-right slot as Hide talks; cards keep full width.

Align the clock with the **header row** in both states: `align-items: start` on `.slot:has(.parallel)` and a `margin-top` on `.slot-time` equal to the toggle row (button `min-height` 32px + `.slot-collapse` bottom margin + `.parallel` gap). Use a small CSS variable so the offset stays in one place.

Below 900px the toggle is already `display: none`; no change.

## Verify (local only)

`python tools/build.py`. Preview `site/index.html`. Do not FTP.

- Gap above presenter is clearly a bit larger than today.
- Monday 16:15, EN + RU: Section 3 / Секция 7 names wrap to two lines; all four headers in that slot are the same height (collapsed and expanded).
- Scroll an expanded slot: time stays mid-screen; day title (“Tuesday…”) is not covered.
- Toggle Show/Hide: button stays top-right of the cards; headers do not jump narrower; time stays level with the colored headers, not the button.
- Mobile stack, dark mode, plenary/poster cards unchanged.
