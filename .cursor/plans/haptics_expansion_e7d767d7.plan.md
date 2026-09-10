---
name: Haptics expansion
overview: Make selection ticks as strong as the favourite pulse (18 ms), collapse haptics to a code-only on/off (scroll ticks included when on), add ticks to more taps, and remove the header switch.
todos:
  - id: duration-and-mode
    content: Bump tick/success pulses to 18 ms; replace three-way mode with HAPTICS_ON boolean kill switch
    status: completed
  - id: hide-header-switch
    content: "Remove #btn-haptics markup, CSS, i18n, and applyHapticsControl/cycleHaptics wiring"
    status: completed
  - id: broader-ticks
    content: Add user-initiated ticks for openDetail, speaker chips, lang/theme/font, layout, chips, expand, changes, overview cells
    status: completed
  - id: verify-ui
    content: Confirm the header control is gone in the browser; note Android-only haptic feel check
    status: completed
isProject: false
---

# Stronger, broader haptics (no header switch)

The Web Vibration API still cannot set amplitude. On a vivo X200 Ultra the 12 ms `tick` is too short to feel like the 18 ms favourite pulse, so we treat **duration as the strength knob** and keep the waveform crisp.

## Strength

In [`site/app.js`](site/app.js), raise the light pulse to match favourite:

```js
const HAPTIC_PATTERNS = {
  tick: 18,
  confirm: 18,
  success: [18, 40, 18],
  warn: [18, 40, 18, 40, 28],
};
```

`tick` vs `confirm` stay as separate kinds (selection vs starring) but will feel the same on device. Do not lengthen further — that would trade the crispness you like for a buzz.

## On/off kill switch (no selection vs scroll)

Drop the three-way mode (`selection` / `scroll` / `off`) and `HAPTIC_MODES` cycling. Haptics are either on or off:

```js
const HAPTICS_ON = true; // set false in a later update to disable for everyone
```

- When on: taps **and** timeline slot-scroll ticks (what used to be “Haptics: scroll”).
- When off: `canHaptic()` returns false and `observeSlots()` does not attach.
- A later update flips `HAPTICS_ON` to `false` for everyone.
- Stop reading/writing `nucleus2026:haptics` so leftover `'off'` / `'selection'` / `'scroll'` from the old button cannot stick. Remove `state.haptics`.
- Keep `canHaptic()`, `haptic()`, cooldown, `prefers-reduced-motion`, visibility, and “no desktop / fine pointer” guards as they are.

`observeSlots()` currently bails unless `state.haptics === 'scroll'`; change that to the same on/off gate as taps (`HAPTICS_ON` plus the existing device/visibility checks).

## Hide the header switch

- Remove `#btn-haptics` from [`site/index.html`](site/index.html).
- Remove `applyHapticsControl`, `cycleHaptics`, `canShowHapticsControl`, the click listener, and the matchMedia hooks that only existed to show/hide the button.
- Drop unused CSS (`#btn-haptics`, `.ctl-icon.is-off`) in [`site/app.css`](site/app.css) and unused i18n keys (`hapticsDays` / `hapticsScroll` / `hapticsOff`). The vibrate icon can stay in `ICONS` unused, or go if nothing else references it.

## Broader ticks (user-initiated only)

Add `haptic('tick')` on taps that currently have no feedback. Prefer **one call in the shared handler** so list/poster/overview rows do not double-fire.

| Interaction | Where |
|---|---|
| Open talk / poster sheet | `openDetail` — only when the user tapped/keyed; **not** on boot or hash restore (`if (openTalkId) openDetail(...)`) |
| Speaker chip in search index | `name-chip` onclick in `speakerIndex` |
| Language | `#btn-lang` listener |
| Theme / font | existing chrome listeners (same family of header taps) |
| Timeline / overview layout | `setLayout` (today silent) |
| Overview cell pick | `activateOverviewCell` |
| Section / poster / timeline filter chips | chip `onclick`s |
| Expand/collapse talks | mobile `sechead`, slot collapse, `toggleAll` — skip extra tick when desktop `sechead` already calls `setView` (that path already ticks) |
| Changes sheet | `openChanges` |

Leave as they are: `setView` / `setDay` / favourite `confirm`+`warn` / copy-link `success` / scroll observers.

Do **not** haptic: search typing, sheet close (system back already clicks), print/export, install banner.

## Verify

- Local: confirm the vibrate button is gone from the top bar (phone-width and desktop) via the browser tools on `site/index.html`.
- Haptic strength and new taps cannot be judged in a desktop browser; they need Chrome on Android. After the change, check: day pill, slot scroll, open a talk, speaker chip, RU/EN, star (should still match the talk-open tick).
