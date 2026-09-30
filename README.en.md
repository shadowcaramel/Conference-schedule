[По-русски](README.md)

# NUCLEUS-2026 / ЯДРО-2026

A conference programme you open in a browser. Days, parallel sections, search, and a personal shortlist. The interface is Russian and English. There is no server and no account.

The conference itself ran at [nucleus.togudv.ru/timetable](http://nucleus.togudv.ru/timetable/). Branch `dev` is not uploaded there. That URL stays the programme from the week of the meeting. The snapshot is tag [NUCLEUS-2026](https://github.com/shadowcaramel/Conference-schedule/releases/tag/NUCLEUS-2026) on `main`; the same commit also carries the tag `ЯДРО-2026`.

Two ways to open it:

- `site/index.html` is the site. Double-click the file, or put the `site/` folder on any web server.
- `dist/nucleus2026-programme.html` is the same site packed into one file, for email or an iframe. `python tools/build.py` produces it.

This branch is published to [GitHub Pages](https://shadowcaramel.github.io/Conference-schedule/) on every push to `dev`, from the `site/` folder. Until a later edit, that page still shows the real meeting: names, venue maps, sponsor marks.

## What you can do with it

Walk the days. On a wide screen, parallel sections sit in a grid; on a phone they stack as cards. Section programmes, posters, search, and a speaker index are all in the page.

«Моё» is a star list kept in this browser only. Move it to another phone with Share (`#my=S1-08,P-12,…`) or an `.ics` file. Stars belong to the page address: marks made on `file://` or `http://` do not show up on `https://` of the same machine.

`?lang=en` opens the English interface immediately. Talk titles stay as they were typed in the workbook. There is a light and a dark theme, and three type sizes (A / A+ / A++). During the meeting days the header shows Now / Next in Khabarovsk time; `?now=2026-09-22T14:30` fakes the clock for layout checks. The footer prints the programme and can download the whole calendar. A short tour runs on the first visit; «?» in the header starts it again.

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

No QR code for the registration desk. No abstract PDFs. No server-side sync of «Моё» across phones (that would need a login). The build does not warn when one person has two talks at the same time; that shows up in the grid or in a search by surname.

The typeface is [Onest](https://fonts.google.com/specimen/Onest) ([simpals/onest](https://github.com/simpals/onest)), SIL Open Font License, files in `site/assets/fonts/`. Interface icons are inline [Lucide](https://lucide.dev/) SVGs.

## License

[GNU GPL version 3](LICENSE) (GPL-3.0).

## Editing the programme

`data/programme.xlsx` is the only source. The site does not read the old TimeTable grid. It is assembled from the talk list and the block list.

```text
data/programme.xlsx  →  python tools/build.py  →  site/data.js
                                               →  dist/nucleus2026-programme.html
```

After you save the workbook:

```text
python tools/build.py
```

Reload the browser. If Excel still has the file open, the build says so — save and close the workbook.

`python tools/build.py --check` validates and writes nothing.

The build warns when blocks of one section or one room overlap, and when the same surname-plus-title pair appears twice. It does not warn when one person is in two talks at once. Parallel sections are separate: a speaker may overlap a plenary and a section, or two halls, and `build.py` stays quiet.

Python 3.10+ and `openpyxl` (`pip install openpyxl`). Node is not required.

Nothing from this branch is uploaded to [nucleus.togudv.ru](http://nucleus.togudv.ru/timetable/). Look at the result locally, or on GitHub Pages.

Locally, open `site/index.html`, or:

```text
python -m http.server 8080 --directory site
```

then `http://127.0.0.1:8080/`.

GitHub Pages: [https://shadowcaramel.github.io/Conference-schedule/](https://shadowcaramel.github.io/Conference-schedule/). A push to `dev` updates it. After `python tools/build.py`, commit the changed files under `site/`.

The single-file build is `dist/nucleus2026-programme.html` (the font is already inside). A WordPress frame for the conference site, which is not this branch:

```html
<iframe
  src="http://nucleus.togudv.ru/timetable/"
  title="NUCLEUS-2026 programme"
  style="width:100%;min-height:80vh;border:0;border-radius:16px;"
></iframe>
<p><a href="http://nucleus.togudv.ru/timetable/?lang=en">English programme</a></p>
```

### Sheets in `programme.xlsx`

Do not rename the column headers. Rows can be added, removed, and reordered. An empty English cell is filled from the Russian one on the site, and the other way around.

**Settings.** Conference title, city, dates, time zone (`Asia/Vladivostok`), UTC offset (`+10:00`), website, contact, footnote under the timetable.

**Sections.** Number (`1`–`7`, `P` for plenaries), short and full titles in RU/EN. Leave the chair columns on this sheet empty. Sections 1–7 change room and chair from slot to slot; those belong on Blocks. Colour: `blue`, `green`, `orange`, `red`, `purple`, `teal`, `pink`, `slate`. Leave the default room empty.

**Blocks.** One row is one timetable slot.

| Column | What to write |
|---|---|
| Дата | `21.09.2026` or `2026-09-21` |
| Начало / Конец | `16:15` |
| Тип | one of: `пленарный`, `юбилейный`, `спонсор`, `секция`, `перерыв`, `обед`, `регистрация`, `открытие`, `закрытие`, `постеры`, `мероприятие` |
| Название (RU) / (EN) | coffee and lunch may be left blank; the usual labels are filled in |
| Секция | `1`–`7` or `P` |
| Доклады | a range `8-14`, a single `12`, a jubilee `Ю1`, a sponsor `С2`, or a list `1,3,5` |
| Аудитория | a room code: `235ц`, `библиотека`, `117л`, `315л`, `вестибюль`, `холл2`, `причал` (the boat), `интурист` (the dinner). The build expands them to full RU/EN labels. The old code `144ц` is read as the library and is not shown. Plenaries, opening, jubilee, sponsor, closing, concert, and coffee are `235ц`. Do not fill Sections → Аудитория: one section uses more than one room. |
| Председатель (RU)/(EN) | chair of this sitting, plenary or section. The Sections tab collects the distinct names into the section header and shows the chair of the specific slot on the day card. Initials and surname: `И. Н. Изосимов` / `I. N. Izosimov`. |
| Примечание | RU/EN |

A talk’s clock time inside a section is the block start plus the durations before it. To pin one talk, fill «Начало» on the Talks sheet.

**Talks**

| Column | Rule |
|---|---|
| **ID** | Stable key (`S1-08`, `P-12`, `P-J1`, `P-S2`). Do not change it: stars are stored under this id. When you reorder, change «№», not the ID. |
| Секция / № | Tie the talk to the «Доклады» field on a block |
| Фамилия, Имя, Отчество, Организация, Email, Название | as in the abstract, either language. Patronymic is its own column; leave it empty when there is none |
| Длительность (мин) | empty means 15 (section), 30 (plenary), 30 (jubilee), 15 (sponsor) |
| Начало | optional shift inside the block |
| Статус | empty / `отменён` / `перенесён` |
| Тематика | for plenaries: the section number the talk belongs to |
| Сайт | optional company URL (a sponsor talk becomes a linked tile) |
| Логотип | optional file name in `site/assets/sponsors/` (for example `gammatech.png`) |
| Спонсор (RU) / Спонсор (EN) | optional company name on the tile |

**Swap two talks.** The grid follows «№» and the block’s «Доклады» field, not the row order. Leave IDs alone.

1. On Talks, exchange «№» on the two rows. If they are in different sections, exchange «Секция» too.
2. If «Начало» is filled, exchange those cells or clear them. Otherwise the talk stays at the old time.
3. Leave Blocks alone while both numbers stay inside the same range (`8-14` and so on). To move a talk into another slot, its new «№» has to fall inside that block’s «Доклады» field.
4. Save and run `python tools/build.py`. Add a row on Changes if you want the audience to see it.

**Posters.** IDs like `POST-05` stay put. «№ стенда» can wait. Patronymic and status match the talks: empty / `отменён` / `перенесён`.

**Changes.** The on-site feed «Изменения в программе». Date, time, and text in RU/EN. Visitors see a badge until they open the feed.

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
