---
name: Russian count plurals
overview: Add a small Russian (and English) plural helper in app.js so counted nouns after numbers use the correct form — including 11–14 as many — for talks, posters, plenary items, parallel sections, and time slots.
todos:
  - id: plural-helper
    content: Add ruPluralCat + counted() and form tables in app.js
    status: completed
  - id: wire-counts
    content: Use counted() for talks, posters, plenary, parallel sections, slots
    status: completed
  - id: verify
    content: Bump cache; browser-check S2/S7/S5, posters, day summary, EN
    status: completed
isProject: false
---

# Russian plural forms for counted nouns

Do this in [`site/app.js`](site/app.js) only. The site is static JS; **do not add pymorphy3**. The rule you gave is the CLDR Russian `one` / `few` / `many` split and is enough for these words.

## Helper

Next to `t()` (~line 344):

```js
function ruPluralCat(n) {
  const n100 = Math.abs(n) % 100, n10 = n100 % 10;
  if (n100 >= 11 && n100 <= 14) return 'many';
  if (n10 === 1) return 'one';
  if (n10 >= 2 && n10 <= 4) return 'few';
  return 'many';
}
function counted(n, forms) {
  const f = forms[state.lang] || forms.ru;
  const word = state.lang === 'ru' ? f[ruPluralCat(n)] : (n === 1 ? f.one : f.other);
  return `${n} ${word}`;
}
```

Store forms once (not as `t('talks')` flat strings):

- talks: ru `доклад / доклада / докладов`, en `talk / talks`
- posters: ru `постер / постера / постеров`, en `poster / posters`
- plenary (short day-summary): ru `пленарный / пленарных / пленарных`, en `plenary talk / plenary talks`
- parallel sections: ru `параллельная секция / параллельные секции / параллельных секций`, en `parallel section / parallel sections`
- slots (the parenthetical in `daySummary`): ru `слот / слота / слотов`, en `slot / slots`

Leave `t('talk')` = «Доклад» for labels. Leave `noTalks` («Нет докладов») and `starredCount` («отмечено» — not this noun pattern).

## Call sites

Replace `` `${n} ${t('…')}` `` with `counted(n, FORMS.…)`:

- Sections hero: [`viewSections`](site/app.js) `talkCount` + `t('talks')` — this is the **24 / 33 докладов** bug (section 7 has 24 talks, section 2 has 33)
- Posters: timeline row, posters page subtitle, per-section group (`t('posterCount')`)
- [`daySummary`](site/app.js): `plenaryCount`, `parallel`, and the hardcoded `` `${sectionSlots} ${state.lang === 'ru' ? 'слота' : 'slots'}` ``

Keep `t('talks')` / `t('posterCount')` only if something else still needs a standalone genitive; otherwise drop those keys.

English gains `1 talk` vs `27 talks` in the same helper.

## Check

Bump `app.js?v=` in [`site/index.html`](site/index.html) (24 → 25) and `CACHE` in [`site/sw.js`](site/sw.js). No `build.py`, no FTP.

In the browser: section 2 hero **33 доклада**, section 7 **24 доклада**, section 5 **9 докладов**, posters **48 постеров**; switch EN and confirm `33 talks`. Filter a poster section with 1–4 items if any exist. Monday day summary: parallel sections + slot parenthesis.