---
name: Haptic scroll logos
overview: Unlock scroll haptics after the first real tap (Chrome blocks vibrate until then), tick each talk/poster card while scrolling Sections and Posters, and skip sponsor logos on iOS/Android cards while keeping them in the detail sheet.
todos:
  - id: arm-haptics
    content: Arm vibrate on first pointerup/click (sticky user activation); do not expect tap-free first scroll
    status: completed
  - id: list-scroll-ticks
    content: Generalize slot observer to tick .talk on Sections and .poster on Posters; stable ids; reconnect after poster list rebuild
    status: completed
  - id: hide-mobile-logos
    content: Skip sponsorLogo() on iOS/Android cards via isIos/isAndroid; keep detail sponsor-tile; bump ?v= to 13
    status: completed
  - id: verify-ui
    content: Check logos by UA (hidden on iOS/Android cards, visible in details and on desktop); note phone-only haptic check
    status: in_progress
isProject: false
---

# Scroll haptics unlock, list ticks, mobile logos

## Why the first timeline scroll is silent

This is not a missing observer. [`observeSlots()`](site/app.js) already attaches on first paint. Chrome’s Vibration API requires **sticky user activation**: `navigator.vibrate()` is ignored until the user taps something. A scroll/fling does not count. Tapping Sections (or any control) grants activation, so when you return to the timeline the same observer finally produces ticks.

We cannot make a **tap-free** first scroll vibrate — the browser blocks it. We can arm as soon as any finger-up/click counts as a gesture, including a tap on empty chrome, not only a tab.

In [`site/app.js`](site/app.js):

- Add a capture, passive `pointerup` + `click` listener that calls `navigator.vibrate(0)` once `navigator.userActivation.hasBeenActive` (or the vibrate call itself) succeeds.
- Do not arm from `touchmove` / scroll.
- Keep existing `canHaptic()` guards (off on desktop / fine pointer / reduced motion).

After a tap anywhere, timeline slot ticks and the new list ticks should work for the rest of the session.

## Scroll ticks on Sections and Posters

Generalize the slot observer instead of a third copy. Reuse the same band (`rootMargin: '-18% 0px -70% 0px'`), 80 ms cooldown, and “skip the first intersection” flag.

- Timeline: `.slot` (unchanged)
- Sections: `#main .talk` (each talk row)
- Posters: `#main .poster` (each poster card)

Poster cards today have `dataset.talk` but no `id`; the observer currently bails on empty `id`. Use `target.id || target.dataset.talk` as the key, and give posters `id: t-${p.id}` like talks.

Call the generalized observer:

- from the existing timeline `requestAnimationFrame` in `viewSchedule`
- at the end of `viewSections`
- after `renderPosterList()` (including search/filter rebuilds)

Disconnect it in `renderMain()` the same way `slotObserver` is disconnected now.

Fast flings stay throttled by `HAPTIC_COOLDOWN_MS` so a dense talk list does not turn into a buzz.

## Skip sponsor logos on mobile clients

Do not use a width media query. Phones in landscape and tablets would still need CSS exceptions; UA detection is the existing install path (`isIos()` / `isAndroid()` in [`site/app.js`](site/app.js)).

```js
const isMobileClient = () => isIos() || isAndroid();
```

In `renderPlenary`, omit `sponsorLogo(talk)` when `isMobileClient()` is true (do not insert the `<img>` at all — no extra CSS, no unused downloads). `sponsorTile()` in the detail sheet stays as it is.

A narrow desktop window still shows card logos; an Android/iPhone (any orientation) does not. iPad is treated as iOS, same as install hints.

Bump cache: [`site/index.html`](site/index.html) `app.css` / `app.js` `?v=` 12 → 13 (JS change).

## Verify

- Phone UA (or DevTools device mode with a mobile UA): timeline sponsor cards have no logo; open the talk and confirm the detail tile still shows it.
- Desktop UA: cards still show the logo even if the window is narrow.
- Header/tabs/search still work after the arming listener.
- Haptic feel (first scroll vs after a tap; sections/posters per card) needs Chrome on the phone — desktop will not vibrate.
