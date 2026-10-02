# Programme data model

JSON in `data/` is the source of truth. `tools/build.py` reads it and writes `site/data.js` (`window.PROGRAMME`). The site (`site/app.js`) does not read the JSON files.

`site/data.js` is generated. Do not edit it by hand and do not commit it. A local preview needs one build first:

```text
python tools/build.py
```

Then open `site/index.html`, or serve the folder (`python -m http.server 8080 --directory site`).

## Files

| File | Shape | What it is |
|---|---|---|
| `data/conference.json` | one object | Titles, place, dates, time zone, languages, default durations, session-type labels |
| `data/tracks.json` | array | Thematic sections (`1`–`7`, `P`) |
| `data/rooms.json` | array | Rooms and the labels the site shows |
| `data/sessions.json` | array | Timed slots (today’s blocks `B001`–`B084`) |
| `data/contributions.json` | array | Talks and posters in one list |
| `data/people.json` | array | Authors and chairs |
| `data/organizations.json` | array | Affiliations and sponsors |
| `data/resources.json` | array | Slides, video, abstract, photo, poster file links. Empty until those exist |
| `data/changes.json` | array | The “changes” feed |

Each array is a list of records. Duplicate `id` values are an error (a JSON object would silently keep the last one, so these files are arrays).

Schemas are draft 2020-12, one file per entity, in `schema/`. `tools/validate.py` runs the schemas and then the cross-record rules. `tools/dataio.py` is the only writer. It sorts records by `id`, uses 2-space indent, writes UTF-8 without `\u` escapes, keeps a fixed key order, and ends with a newline. A file that is not in that form fails validation.

## Identifiers

Existing contribution ids stay as they are: `S1-08`, `P-12`, `P-J1`, `P-S1`, `POST-05`, and the rest. Visitors’ stars (`localStorage`) and `#my=` links store them. Session ids stay `B001`–`B084`. Renaming either kind breaks saved lists.

New records get opaque ids. Do not renumber a record to close a gap. The importer assigned people `PER-0001` upward and organizations `ORG-001` upward, in name order, once. Those ids are now part of the data. Track ids are the section numbers (`1`–`7`, `P`) because the site already uses them as `section`. Room ids are the campus codes (`235ц`, `библиотека`, `117л`, …). `144ц` is an alias of `библиотека`, not its own room.

## What is stored, and what is computed

A contribution stores its place in a session (`session_id`, `order`), `duration_min`, and an optional `start` pin. It does not store clock start and end. The build walks the session’s `contribution_ids`, applies durations and pins, and writes the clock times into `site/data.js` only.

For a `section` session the site’s end time is the end of the last talk when that differs from the stored `end`. Other session types keep the stored `end`. Validation messages use these computed times.

Days are not an entity. They are the sorted set of session dates. The conference stores `timezone` (IANA name, `Asia/Vladivostok`). The site still receives `utcOffset`; the build derives it from the time zone on `date_start`. The offset is not stored, so it cannot drift away from the zone.

Text that has two languages is `{ "ru": "…", "en": "…" }`. The language list is `conference.languages` (`["en", "ru"]`). A contribution title is usually one string, the title as it was written. A bilingual title is allowed when a translation exists.

Names are stored as written: `family`, `given`, `patronymic`. Patronymic and email may be absent.

## Entities

### Conference

`id`, `title`, `short_title`, `date_start`, `date_end`, `city`, `venue`, `timezone`, optional `website` and `contact`, `footnote`, `languages`, `defaults.duration_min` (`plenary` 30, `jubilee` 30, `sponsor` 15, `section` 15), and `session_types` (machine id to the default RU/EN label).

### Track

`id`, `short`, `full`, `color` (`blue`, `green`, `orange`, `red`, `purple`, `teal`, `pink`, `slate`). A session may point at a track. The colour and the titles are what the site calls a section.

### Room

`id`, `label` (RU/EN, the line the site shows), optional `aliases` (old codes that mean this room).

### Session

Any timed slot: section, plenary, jubilee, sponsor, break, lunch, registration, opening, closing, poster, social.

`id`, `date`, `start`, `end`, `type`, optional `title`, optional `track_id`, optional `room_id`, optional `chairs`, `contribution_ids` (order is the running order), optional `note`.

`chairs` is a list of `{ "person_id", "label" }`. `person_id` is the link. `label` is the bilingual line that was published for that sitting. The same person can be cited in more than one word order (`Вефасев Л. Д.` and `Л. Д. Вефасев`), and the English line is a transliteration, not `given`. The build prints `label` when it is present.

Plenary, jubilee, and sponsor are session types. They are not copied onto the contribution.

### Contribution

Talks and posters share this list.

`id`, `format` (`oral` or `poster`), optional `track_id`, optional `session_id`, optional `order`, optional `number` (the old «№»: `8`, `Ю1`, `С2`), `title`, `authors`, `duration_min` (omitted for posters; they have no slot of their own), optional `start` pin, `status` (`ok`, `cancelled`, `moved`), optional `topic_id` (a track, used by plenary talks), optional `note`, optional `sponsor_id`, optional `board` (posters).

`authors` is an ordered list of `{ "person_id", "affiliation_ids", "presenting" }`. Today each contribution has one presenting author. Several are allowed. The site still shows one name: the first author with `presenting: true`, or the first author if none is marked. Several `affiliation_ids` are joined with a comma for that one line.

A poster has `format: poster`, may have a `board`, and belongs to the poster session. The build still writes the site’s separate `posters` list, and it does not put poster ids into `block.talks`.

`sponsor_id` points at an organization that has `url` and `logo`. The build copies those onto the talk as `url`, `logo`, and `sponsorName`.

### Person

`id`, `family`, `given`, optional `patronymic`, optional `email`.

### Organization

`id`, `name` (a string, or bilingual when the two languages differ), optional `url`, optional `logo`. An affiliation string from the old sheet is one organization, even when the string itself contains a comma. Sponsors are organizations in this same file.

### Resource

`id`, `contribution_id`, `kind` (`slides`, `video`, `abstract`, `photo`, `poster`), `url`, optional `lang`. Binary files stay outside the repository. The URL is a link, not a blob.

### Change

`id`, `at` (`YYYY-MM-DD` or `YYYY-MM-DDThh:mm`), `text`. The site shows them newest first. The file itself is sorted by `id`.

## How a talk gets its clock time

Inside one session, in `contribution_ids` order, for each oral contribution:

1. Duration is `duration_min`, or `defaults.duration_min` for the session type, or 15.
2. If `start` is set, the cursor jumps to that clock time (the pin).
3. Otherwise the talk starts where the previous talk ended, or at the session start for the first talk.

Poster contributions do not take a slot inside that walk. For overlap checks, a poster occupies the whole poster session.

## Validation

Errors fail `tools/validate.py` and `tools/build.py`. Warnings are printed and do not fail the command.

Errors:

- Duplicate ids
- A reference to a missing track, room, session, person, organization, or contribution
- A contribution listed in more than one session, or a `session_id` that does not match `contribution_ids`
- Two contributions with the same `order` in one session
- A date, time, or time zone that does not parse
- A session whose `end` is not after `start`
- A session outside `date_start`…`date_end`
- A poster in a session that is not type `poster`, or an oral contribution in a poster session
- Two sessions in the same room whose times overlap
- Two sessions on the same track whose times overlap

The room and track checks used to be warnings. They are errors now. Touching at an endpoint (`10:00–10:30` and `10:30–11:00`) is not an overlap. Sessions with no room are not compared for room overlap. The times in the message are the computed ones, for example `Room 235ц 2026-09-22: B031 10:00–10:30 overlaps B034 10:20–10:50`.

Warnings:

- A section session whose talks end at a different time than the stored `end` (the site uses the talks), or any other session whose talks run past the stored `end`
- A contribution with no session
- A bilingual title whose English string is empty (conference title, track titles, session title, or a bilingual contribution title)
- One person listed on two contributions whose times overlap
- A chair of a session who is also presenting a contribution in a different session at that time. Speaking in the sitting they chair is not a warning.

People are matched on person id, so two contributions by the same person are visible even when the strings differ. Posters in one poster session overlap each other, because a poster has no clock time of its own.

## Editing

Edit the JSON, then run:

```text
python tools/validate.py
python tools/build.py
```

`python tools/build.py --check` validates and writes nothing. `python tools/build.py --data data/` reads that folder (a second conference can be a second folder).

Keep ids stable. To swap two talks, exchange their `order` (and `session_id` if they move) and the session’s `contribution_ids`. Do not exchange their `id` values.

`tools/import_xlsx.py` is the one-time converter from `programme.xlsx`. The workbook is not the live source. `data/import-report.md` lists every chair match from that conversion.

## Site output

`window.PROGRAMME` keeps the shape `site/app.js` already reads: `settings`, `sections`, `days`, `blocks`, `talks` (object keyed by id), `posters`, `changes`. Empty strings and `status: ok` are omitted. `generatedAt` is the build time. Keys in `talks` follow the old Доклады sheet: jubilees, plenary numbers 1–5, sponsor talks, the remaining plenaries, then section talks by id. The site looks each talk up by id.
