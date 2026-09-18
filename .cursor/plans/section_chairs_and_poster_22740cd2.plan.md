---
name: Section chairs and poster
overview: Fill per-sitting chairs on all 23 section blocks, show unique shortened chairs in the Sections hero and the sitting chair on each day/time card (Schedule already has the slot), clear the poster “time TBC” note, and move Maltsev’s S3 oral to posters.
todos:
  - id: xlsx-chairs
    content: Write shortened RU/EN chairs on all 23 section rows in Блоки; clear poster B052 notes
    status: completed
  - id: maltsev-poster
    content: Move S3-07 to POST-48; shrink S3 Monday block to 1-6 / 16:15-17:45; add Изменения row
    status: completed
  - id: sections-ui
    content: "Sections hero: unique chairs; sitting sechead + Schedule cards use chairOf(b); i18n plural"
    status: completed
  - id: docs-build-verify
    content: README + inconsistencies; build.py; bump cache; browser-check Sections/Schedule/Posters; no FTP
    status: completed
isProject: false
---

# Section chairs, poster note, Maltsev oral→poster

Source of truth stays [`data/programme.xlsx`](data/programme.xlsx) (`Блоки` chairs, not `Секции`). Then `python tools/build.py`. No FTP.

## Verification (cross-check)

Matched against current section blocks in [`site/data.js`](site/data.js). **Every oral section sitting gets a chair.** No Thursday section sittings exist; S3 has no Wednesday oral (poster session that afternoon); S4 has no Monday; S5/S6 only Wednesday.

Times below are **from the book**. One user time differs (called out). After Maltsev moves, S3 Monday shrinks (also called out). Store chairs already shortened: `И. Н. Изосимов` / `I. N. Izosimov` (same initials-first style as English plenary chairs). `Секции → Председатель` stays empty.

**Section 1 — Структура ядра**

- Mon 21 Sep **16:15–18:00** (библиотека, B016, №1–7) — **И. Н. Изосимов** / I. N. Izosimov — speaker `S1-08`
- Tue 22 Sep **14:00–15:45** (библиотека, B029, №8–14) — **И. А. Мазур** / I. A. Mazur — speaker `S1-04` (not A. I. Mazur)
- Wed 23 Sep **14:00–16:00** (библиотека, B047, №15–22) — **Д. М. Родкин** / D. M. Rodkin — speaker `P-32`. User wrote 14:00–16:15; book is 16:00 (8×15 min). Keep 16:00.
- Fri 25 Sep **14:00–15:15** (235ц, B071, №23–27) — **О. А. Рубцова** / O. A. Rubtsova — speaker `S1-01`

Hero: И. Н. Изосимов, И. А. Мазур, Д. М. Родкин, О. А. Рубцова

**Section 2 — Ядерные реакции**

- Mon 21 Sep **16:15–18:00** (235ц, B017) — **И. А. Митропольский** / I. A. Mitropolsky — speaker `S1-11`
- Tue 22 Sep **14:00–15:30** (B030) and **16:15–17:45** (B034) — **А. С. Демьянова** / A. S. Demyanova — speaker `S2-02` (same chair on both sittings)
- Wed 23 Sep **14:00–15:45** (B048) — **Д. Е. Любашевский** / D. E. Lyubashevsky — speaker `P-26` / `S2-21`
- Fri 25 Sep **16:15–18:00** (B072) — **М. А. Науменко** / M. A. Naumenko — speaker `S2-25` (programme name is Latin Mikhail Alekseyevich Naumenko)

Hero: И. А. Митропольский, А. С. Демьянова, Д. Е. Любашевский, М. А. Науменко

**Section 3 — Методы и технологии**

- Mon 21 Sep **16:15–18:00** today (117л, B018, №1–7) — **А. А. Дзюба** / A. A. Dzyuba — speaker `P-31`. After Maltsev: talks №1–6, end **17:45**; Dzyuba remains chair.
- Tue 22 Sep **16:15–18:00** (библиотека, B035) — **В. И. Жеребчевский** / V. I. Zherebchevsky — speaker `P-03`; already a Wednesday plenary chair under this EN spelling
- Fri 25 Sep **14:00–15:45** (B073) and **16:15–17:45** (B076) — **А. В. Канцырев** / A. V. Kantsyrev — speaker `S3-03`

Hero: А. А. Дзюба, В. И. Жеребчевский, А. В. Канцырев

**Section 4 — HEP**

- Tue 22 Sep **14:00–15:45** (117л, B031) — **Г. А. Феофилов** / G. A. Feofilov — speaker `S4-18`
- Tue 22 Sep **16:15–17:30** (B036) — **Д. Прохорова** / D. Prokhorova — speaker `S4-19` (Latin Daria, no patronym)
- Fri 25 Sep **14:00–15:45** (B074) and **16:15–18:00** (B077) — **А. А. Зайцев** / A. A. Zaitsev — speaker `S4-11` (Andrey; not Sergey/Alexander Zaitsev in S5)

Hero: Г. А. Феофилов, Д. Прохорова, А. А. Зайцев

**Section 5 — FBS**

- Wed 23 Sep **14:00–16:15** (117л, B049) — **А. И. Мазур** / A. I. Mazur — not a speaker; already Saturday 09:00 plenary chair; keep as given (org committee)

Hero: А. И. Мазур

**Section 6 — Астрофизика**

- Wed 23 Sep **14:00–16:00** (315л, B050) — **А. С. Чепурнов** / A. S. Chepurnov — speaker `P-28`

Hero: А. С. Чепурнов

**Section 7 — Ядерная медицина**

- Mon 21 Sep **16:15–18:00** (315л, B019) — **В. О. Сабуров** / V. O. Saburov — speaker `S7-19`
- Tue 22 Sep **14:00–15:45** (B032) — **О. В. Белов** / O. V. Belov — speaker `P-11`
- Tue 22 Sep **16:15–18:00** (B037) — **А. П. Черняев** / A. P. Chernyaev — speaker `P-13`; already a Wednesday plenary chair
- Fri 25 Sep **14:00–14:45** (B078) — **С. Мамаева** / S. Mamaeva — speaker `S7-10` (Саргылана, no patronym in the book)

Hero: В. О. Сабуров, О. В. Белов, А. П. Черняев, С. Мамаева

**Unchaired oral section blocks:** none.

## Data edits (`programme.xlsx`)

Fill `Блоки → Председатель (RU)/(EN)` on the 23 `тип=секция` rows above (match date + start + section). Leave plenary chair strings as they are (`Мазур А. И.` on Saturday, etc.).

**Poster note:** block B052 (Wed 23 Sep 16:45–18:00, `холл2`) has `Примечание` RU «Время уточняется» / EN «Time to be confirmed». The Posters subtitle in [`site/app.js`](site/app.js) `viewPosters()` concatenates date, room, **and `L(posterBlock.note)`**, which is why that line appears. Clear both note cells. Time 16:45–18:00 stays.

**Maltsev oral → poster**

- Talk `S3-07`: «Особенности изучения свойств пучков тяжёлых ионов высоких энергий», Николай Александрович Мальцев, Mon 17:45–18:00, hall 117л.
- Copy speaker/title/org/email/section onto **Постеры** as **`POST-48`** (do not reuse `S3-07`; starred IDs would otherwise point at the wrong kind of item).
- Delete the `S3-07` row from **Доклады**.
- B018 `Доклады` `1-7` → `1-6`; `Конец` `18:00` → `17:45` so the sheet matches packed talks (otherwise `build.py` already rewrites the site end and warns).
- Do not renumber S3 Tuesday/Friday talks.

**Изменения:** one feed row (Maltsev moved to posters; section chairs published; poster session time confirmed). Update [`README.md`](README.md) (block chairs now used for sections) and the chairs note in [`data/inconsistencies.md`](data/inconsistencies.md).

## Sections / Schedule UI ([`site/app.js`](site/app.js))

Chairs are already on each block after the rebuild (`chairOf`). Today the Sections hero and Schedule cards still read **section**.chair (empty → «уточняется»).

**Sections hero** (`.section-hero`): unique `L(b.chair)` over that section’s `type==='section'` blocks, first-seen chronological order. Label `Председатель` / `Chair` if one name, `Председатели` / `Chairs` if several. For **P**, do not dump every plenary sitting chair into the hero (too long); those sittings already have per-block chairs.

**Day/time card** (the block under the hero): keep `.sechead` (time + room) and add the **sitting** chair via `chairOf(b)`. Show the header whenever there is a chair or a room (today it already appears because rooms are filled). Same shortened string as in Excel.

**Schedule** parallel cards: only swap `chairLabel(s)` → `chairOf(b)` in `renderSectionCard` (~line 2441). Layout unchanged. Talk detail and print already prefer `b.chair`.

Bump `app.js`/`app.css` `?v=` in [`site/index.html`](site/index.html) and `CACHE` in [`site/sw.js`](site/sw.js).

## Check locally (no deploy)

`python tools/build.py`, then `python -m http.server 8080 --directory site`:

- Sections 1–7: hero name list; each sitting shows its own chair; S5 is A. I. Mazur not I. A. Mazur.
- Schedule Tuesday 14:00: four different chairs on the four cards.
- Posters header: Wednesday 16:45–18:00, hallway, 48 posters — **no** “Time to be confirmed”.
- Maltsev is a poster, not last talk of S3 Monday; S3 Monday ends 17:45.
- RU/EN switch on chair strings.
