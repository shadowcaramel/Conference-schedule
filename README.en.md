[По-русски](README.md)

# NUCLEUS-2026 / ЯДРО-2026

A conference programme you open in a browser. Days, parallel sections, search, and a personal shortlist. The interface is Russian and English. There is no server and no account.

The conference itself ran at [nucleus.togudv.ru/timetable](http://nucleus.togudv.ru/timetable/). Branch `dev` is not uploaded there. That URL stays the programme from the week of the meeting. The snapshot is tag [NUCLEUS-2026](https://github.com/shadowcaramel/Conference-schedule/releases/tag/NUCLEUS-2026) on `main`; the same commit also carries the tag `ЯДРО-2026`.

Open it after one build:

- Run `python tools/build.py` first. `site/data.js` is generated and is not in git. Without that step the page has no programme.
- `site/index.html` is the site. Double-click the file, or put the `site/` folder on any web server.
- `dist/nucleus2026-programme.html` is the same site packed into one file, for email or an iframe. The same command produces it.

This branch is published to [GitHub Pages](https://shadowcaramel.github.io/Conference-schedule/) from `dev`. A push validates the JSON, runs the tests, builds `site/data.js`, and only then deploys the `site/` folder. The `?v=` stamps in `index.html` and the cache name in `sw.js` are written by that build. Do not commit them.

## What you can do with it

Walk the days. On a wide screen, parallel sections sit in a grid; on a phone they stack as cards. Section programmes, posters, search, and a speaker index are all in the page.

«Моё» is a star list kept in this browser only. Move it to another phone with Share (`#my=S1-08,P-12,…`) or an `.ics` file. Stars belong to the page address: marks made on `file://` or `http://` do not show up on `https://` of the same machine.

`?lang=en` opens the English interface immediately. Talk titles stay as they were written in the JSON. There is a light and a dark theme, and three type sizes (A / A+ / A++). During the meeting days the header shows Now / Next in Khabarovsk time; `?now=2026-09-22T14:30` fakes the clock for layout checks. The footer prints the programme and can download the whole calendar. A short tour runs on the first visit; «?» in the header starts it again.

## Plain HTTP, and when the browser wants HTTPS

The conference URL is still plain HTTP, with no certificate. The timetable, search, stars, print, `.ics`, and maps do not care. They work on that URL as they are.

Other browser features care about a secure context, not about the letters `https` in the address bar. The code reads `window.isSecureContext`.

| How the page was opened | Secure context? | What you get |
|---|---|---|
| `https://…` (GitHub Pages, or nucleus.togudv.ru once it has a certificate) | yes | install, clipboard, and the rest of the browser APIs |
| `http://127.0.0.1:8080/` or `http://localhost:8080/` | yes | localhost counts as HTTPS, so you can test install and copy locally |
| `http://nucleus.togudv.ru/…` | no | no Clipboard API, no service worker, no system install |
| `site/index.html` opened as a file (`file://`) | no | same gap, and stars will not match the conference site |

**Home screen.** On HTTPS the page can be a real app: Chrome and Edge offer Install, the window has no address bar, and a copy remains if the network drops. On HTTP the browser cannot do that. A service worker and the `beforeinstallprompt` event both require a secure context, so `sw.js` is not registered there (registering it would only log an error). The footer button «На экран Домой» spells out the manual path instead: Safari → Share → Add to Home Screen; Chrome → ⋮ → Add to Home screen. The dialog says what that shortcut actually is: on HTTP it usually opens a browser tab, not its own window.

Try a full install on [GitHub Pages](https://shadowcaramel.github.io/Conference-schedule/). Locally, `python -m http.server 8080 --directory site` and open `http://127.0.0.1:8080/`.

The offline cache exists only after a real install, and it asks the network first. A fresh `data.js` beats yesterday’s copy. The cache is for when the network is gone.

**Copy a talk link.** «Ссылка на доклад», «Ссылка на событие», and the fallback under Share all copy a URL. On plain HTTP the modern clipboard API does not exist, so on the conference site the button first looked dead. The talk card is an open `<dialog>`. While it is open the rest of the page is inert, and the old `document.execCommand('copy')` fails if the hidden field is placed on `document.body` outside the dialog.

`copyText()` in `site/app.js` tries three things:

1. The clipboard API, when the page is a secure context (HTTPS or localhost).
2. A hidden field inside the open dialog, then `execCommand('copy')`. That is what works on the live HTTP site.
3. A `prompt` with the link, if the browser blocks both.

The «copied» toast is shown inside the same dialog. Outside it, the dialog would cover the message.

**Share my list.** `navigator.share` is also limited to a secure context. On HTTP the button in «Моё» copies the `#my=…` link with `copyText()` immediately. On a phone with HTTPS it offers the system share sheet first, and copies the link if that sheet is dismissed.

**A WordPress iframe.** This is not an HTTP quirk. A frame on someone else’s site will not offer install, and the parent page can deny clipboard access. The install hint includes «Открыть в новой вкладке». Copying a link is more reliable with the programme open on its own.

If the conference host later turns on HTTPS, the code can stay. The service worker will register, copying will use the clipboard API first, and Chrome will be able to install the app. Three consequences remain:

- stars made on **http://**nucleus… do not travel to **https://**nucleus… (the browser treats them as different sites, the same way `file://` and the website differ). People use Share, or star the talks again;
- replace `http://nucleus.togudv.ru/timetable/` in iframes and links with `https://…`;
- maps and sponsor sites are already `https://`, so they will not cause mixed content.

## Left out on purpose

No QR code for the registration desk. No abstract PDFs. No server-side sync of «Моё» across phones (that would need a login). A local editor for the JSON is described at the bottom of this file. It is not the public site, and it does not upload to the conference server. `tools/dataio.py` is still the form CI accepts.

The typeface is [Onest](https://fonts.google.com/specimen/Onest) ([simpals/onest](https://github.com/simpals/onest)), SIL Open Font License, files in `site/assets/fonts/`. Interface icons are inline [Lucide](https://lucide.dev/) SVGs.

## License

[GNU GPL version 3](LICENSE) (GPL-3.0).

## Editing the programme

`data/*.json` is the only source. Fields and id rules are in [docs/data-model.md](docs/data-model.md). The site still reads `window.PROGRAMME` from `site/data.js`. That file is built and is not committed.

```text
data/*.json  →  python tools/build.py  →  site/data.js
                                     →  dist/nucleus2026-programme.html
```

After you edit the JSON:

```text
python tools/build.py
```

Reload the browser. `python tools/build.py --check` validates and writes nothing. `python tools/validate.py` is the schema and the cross-record rules. `python tools/dataio.py --check` checks that the files are in the canonical form. The build takes `--data data/`, so a second conference is a second folder.

Python 3.10+ and the dependencies in `pyproject.toml` (`pip install ".[dev]"`). Node is not required.

Nothing from this branch is uploaded to [nucleus.togudv.ru](http://nucleus.togudv.ru/timetable/). Look at the result locally, after a build, or on GitHub Pages.

Locally, run `python tools/build.py`, then open `site/index.html`, or:

```text
python -m http.server 8080 --directory site
```

then `http://127.0.0.1:8080/`.

GitHub Pages: [https://shadowcaramel.github.io/Conference-schedule/](https://shadowcaramel.github.io/Conference-schedule/). A push to `dev` validates, tests, builds, and then deploys. Do not commit `site/data.js` or the `?v=` stamps.

The single-file build is `dist/nucleus2026-programme.html` (the font is already inside). A WordPress frame for the conference site, which is not this branch:

```html
<iframe
  src="http://nucleus.togudv.ru/timetable/"
  title="NUCLEUS-2026 programme"
  style="width:100%;min-height:80vh;border:0;border-radius:16px;"
></iframe>
<p><a href="http://nucleus.togudv.ru/timetable/?lang=en">English programme</a></p>
```

### Files in `data/`

| File | What it is |
|---|---|
| `conference.json` | Titles, city, dates, time zone, languages, default durations |
| `tracks.json` | Sections `1`–`7` and `P`: titles and colour |
| `rooms.json` | Rooms and the labels the site shows |
| `sessions.json` | Slots `B001`–`B084` |
| `contributions.json` | Talks and posters in one list |
| `people.json` | Authors and chairs |
| `organizations.json` | Affiliations and sponsors (`url`, `logo`) |
| `resources.json` | Links to slides and video. Empty for now. Binaries stay out of the repo |
| `changes.json` | The «Изменения в программе» feed |

Text in two languages is `{ "ru", "en" }`. A talk title is usually one string. A name is `family`, `given`, `patronymic`.

Clock times are not stored on a contribution. It has a place in a session (`session_id`, `order`), `duration_min`, and an optional `start` pin. The build computes the clock. The UTC offset is not stored either: it is derived from `timezone` (`Asia/Vladivostok`).

**Do not change ids.** `S1-08`, `P-12`, `P-J1`, `P-S1`, `POST-05`, and the other contribution ids are what stars and `#my=` links store. Session ids `B001`–`B084` stay too. New records get new ids. Do not renumber the old ones.

To swap two talks, exchange `order` and the session’s `contribution_ids`. Leave the contribution `id` values alone. To pin one talk inside a session, set `start`. A poster may grow a `board`. Status is `ok`, `cancelled`, or `moved`.

A session chair is a person id plus the `label` line that was published. The same person can be cited in more than one word order.

The Excel workbook is no longer the source. It stays on `main` and in the tag `NUCLEUS-2026`. `tools/import_xlsx.py` is the one-time converter. `data/import-report.md` lists every chair match.

### What fails the check

Errors stop the build and GitHub Pages. That includes two sessions in one room, or on one track, whose times overlap. Those used to be warnings. Touching at an endpoint (`10:00–10:30` and `10:30–11:00`) is not an overlap.

Warnings do not stop the build. A section whose talks end at a different time than the stored end. A contribution in no session. A bilingual title with an empty English string. One person on two contributions at overlapping times. A chair who is presenting in a different session at that time. Speaking in the sitting you chair is not a warning.

### Switches in `site/app.js`

Near the top of the file, flags for the whole site. They are not a visitor setting:

```js
const HAPTICS_ON = true; // vibration on a phone
const TOUR_ON = true;    // first-visit tour and the «?» button
const OVERVIEW_SECTION_SORT = 'room'; // grid: order of parallel sections
```

Set `HAPTICS_ON` or `TOUR_ON` to `false` to turn the feature off for everyone. You do not have to delete the code. Tour progress (`localStorage` key `nucleus2026:tour`) is kept. Turning `TOUR_ON` back on does not show the tour again to people who already finished it.

`OVERVIEW_SECTION_SORT` affects the Grid view and its printout only. The feed is unchanged.

- `'room'` (the default) — columns left to right: library → assembly hall → 117л → 315л.
- `'section'` — section numbers S1…S7.

## Editor

A local editor for one person, on this computer. It listens on `127.0.0.1` only. It does not deploy, and it does not upload to nucleus.togudv.ru.

Node and the Python tools are both required:

```text
cd editor
npm install
npm run build
cd ..
python tools/edit.py
```

Open http://127.0.0.1:8765/. The timetable lists a session’s talks in running order with the clock times from `tools/schedule.py`. Records opens a form for the conference, tracks, rooms, sessions, talks, people, organizations, resources, and changes. People, organizations, tracks, and rooms are chosen by name, and a person can be created from that picker. Search covers talks, people, and organizations. A talk moves to another session and position from the contribution form. Up and down reorder it inside the session. Talks without a session are listed as unscheduled, with a schedule action. Editing a session’s time or room updates the grid. Undo restores the last several edits. Cancelling, moving, or retiming a talk offers a changes-feed note in each conference language. The note can be edited or skipped. Review shows a short summary and the diff against `dev`. Preview opens the real site, built from the draft, in a new tab. Publish commits `data/` on a new branch and opens a pull request into `dev` with `gh`, or prints the compare URL when `gh` is missing. It stays disabled while validation reports errors, and it can show that pull request’s CI status. It does not upload to the conference server. Likely duplicate people (same family name and given-name initial) can be merged, which rewrites every reference. Delete is refused while something still points at the record, and the editor lists those links. Deleting a talk warns that visitor stars and `#my=` links will lose the id and offers “cancelled” instead. The timetable shows the first language in `conference.languages`; the header control cycles that list and remembers the choice in this browser. Language fields on the form stay side by side in that order. Ids are read-only. Errors and warnings come from `tools/validate.py` and can be saved; they show on the record and in the Checks list.

`npm run dev` in `editor/` proxies `/api` to the same Python server. Every save goes through `tools/dataio.py`. Pull requests into `dev` build the editor. GitHub Pages still publishes only the `site/` folder.
