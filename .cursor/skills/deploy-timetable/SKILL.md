---
name: deploy-timetable
description: >-
  Publishes the ЯДРО-2026 programme folder site/ to nucleus.togudv.ru over FTP.
  Use only when the user explicitly asks to publish, deploy, or upload the
  timetable to the conference server or FTP. Do not run after ordinary local
  edits, previews, or polish — those are tested locally first.
---

# Deploy timetable (on demand)

The live site is [http://nucleus.togudv.ru/timetable/](http://nucleus.togudv.ru/timetable/). Excel, `data/`, `tools/`, and git metadata never go on the FTP.

## When to run

- **Do** run when the user says publish / deploy / upload / выложить на сайт / залить на FTP.
- **Do not** run after routine code or Excel edits. They test locally: open `site/index.html`, or `python -m http.server 8080 --directory site`.
- If unsure, ask. Prefer `--dry-run` over uploading.

## How to deploy

1. If `data/programme.xlsx` changed and `site/data.js` is stale, rebuild first (`python tools/build.py` or pass `--build`).
2. Preview: `python tools/deploy.py --dry-run`
3. Upload: `python tools/deploy.py` (only files whose size differs). Use `--all` only if they ask to overwrite everything.
4. Confirm the live URL in the browser (schedule renders, RU/EN works, no missing CSS/JS).

Credentials come from gitignored `.ftp.env` (copy `.ftp.env.example`) or `FTP_HOST` / `FTP_USER` / `FTP_PASS`. Never print the password, never commit `.ftp.env`, never write the password into the repo.

Do not delete extra files on the server. Do not invent a different host, path, or protocol.
