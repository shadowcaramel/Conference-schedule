---
name: deploy-timetable
description: >-
  Refuses to publish this branch to nucleus.togudv.ru. The conference site
  already has the finished ЯДРО-2026 / NUCLEUS-2026 programme. Do not run
  tools/deploy.py for that host.
---

# Do not deploy this branch to the conference site

The live conference programme stays at [http://nucleus.togudv.ru/timetable/](http://nucleus.togudv.ru/timetable/). It is the tagged snapshot `NUCLEUS-2026` (same commit as `ЯДРО-2026`) on `main`.

`dev` is not uploaded there. If the user asks to publish, deploy, or upload the timetable to nucleus.togudv.ru or FTP, say so and stop. Do not run `python tools/deploy.py`. The script exits on its own when the target is that host.

Preview the site locally: open `site/index.html`, or `python -m http.server 8080 --directory site`. The public demo of this branch is GitHub Pages, updated by a push to `dev`.
