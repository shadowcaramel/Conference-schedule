# Programme editor

A local programme editor for one responsible person. It edits `data/*.json` through `tools/dataio.py`, checks it with the same rules as `tools/validate.py`, and publishes a pull request into `dev`. The records it edits are described in [docs/data-model.md](data-model.md). The editor sits on that pipeline and does not replace it.

The interface talks to storage through an adapter. Stage 1 has only the local adapter. A server adapter can replace it later without changing the forms, the timetable view, or the validation display.

## Decisions

The editor runs on the responsible person's own computer, with Python and Node installed. Stage 1 is local only: no hosting and no login.

Publishing is always a pull request into `dev`. CI validates and builds before GitHub Pages changes.

Moving talks is form-based in v1. The editor picks a session and a position, or moves a talk up and down. Drag and drop comes later.

Stage 1 has one user. There are no roles and no locking.

English comes first. The editor shows a text field for each language in `conference.languages`, in that order. The list is `["en", "ru"]`.

The editor is a React app, built with Vite and TypeScript. React is used because the libraries the design skills recommend (Sonner, Radix or Base UI, and dnd-kit later) target React. The public site is unchanged; porting it is a separate later project.

Design follows [emilkowalski/skills](https://github.com/emilkowalski/skills), mainly `emil-design-eng` (motion and visual detail), `pick-ui-library` (library choice), and `review-animations`. UI work starts by installing them with `npx skills@latest add emilkowalski/skills`. They are committed into `.cursor/skills/` only if the repository licence allows it.

Docs, the editor interface, commit messages, and pull request text are in English first. Russian follows where a second language is offered.

Importing corrections from a spreadsheet is out of scope.

## Layout

`editor/` is the React app. `npm run build` writes `editor/dist/`, which is git-ignored.

`tools/edit.py` is a standard-library HTTP server on `127.0.0.1`. It serves `editor/dist/` and a small JSON API: read all data, save one record, delete one record, validate, build a preview, and publish. Every write goes through `dataio`.

Validation calls the `tools/validate.py` code directly, so the editor and CI share one set of rules.

Preview runs `tools/build.py` into a temporary folder and serves the real site with the draft data.

Publish creates a branch, commits the changed `data/` files, pushes, and opens a pull request into `dev` with `gh pr create` on the responsible person's machine. Where `gh` is not available, it prints the compare URL instead.

CI on pull requests into `dev` also builds the editor and runs its tests.

## Requirements

### Must have in v1

Every entity is edited through a form: conference, tracks, rooms, sessions, contributions, people, organizations, changes, and resources. The editor does not show raw JSON.

The timetable is a grid of days by rooms, with sessions as blocks. Clicking a block shows its talks in running order with computed clock times, so the effect of a start pin is visible.

Moves and reordering are form-based. A talk moves to another session and position from a form, talks inside a session move with up and down buttons, and a whole session moves by editing its time or room.

Contributions without a session appear in an unscheduled list. Each one has a schedule action.

Reference fields choose a person, organization, room, or track by typing a name. A person can be created inline. An id is never typed by hand.

Multilingual fields sit side by side in `conference.languages` order (English, then Russian). A text missing in any conference language is a warning.

Validation uses the rules of `tools/validate.py` and runs as the record is edited. Errors and warnings appear on the record and in one list that jumps to it. A draft with errors can be saved. Publishing is blocked until the errors are gone.

Cancelling, moving, or retiming a talk offers a prefilled changes-feed entry in each conference language. The entry can be edited or skipped.

New records get generated ids. Existing ids are read-only, because visitor stars and `#my=` links depend on them. Deleting a referenced record is blocked, and the editor lists what points at it. Deleting a contribution warns that stars will lose it and offers "cancelled" instead.

Before publishing, the editor shows a plain summary ("3 talks moved, 1 cancelled, 2 names corrected") and the file diff, then publishes as a pull request.

Preview opens the real site with the draft data in a new tab.

Undo covers at least the last several edits in the session.

### Should have

Search covers talks, people, and organizations.

A duplicate-person check flags likely duplicates (the same family name and initials) and can merge them, updating every reference.

Publish status shows the pull request's CI result and, after merge, the Pages deployment.

### Later

Drag and drop in the timetable, including from the unscheduled list.

A server adapter adds accounts and roles (section chairs edit their own section, an administrator publishes), an audit log, and concurrent editing.

Editing from any browser without a local server, through a GitHub-backed adapter, with Pyodide running `validate.py` in the browser so there is one copy of the rules.

Speaker self-service corrections with approval.

Call for papers, review, speaker emails when a slot moves, file storage for slides and video, and several conferences.

An export of frab schedule JSON, so existing mobile schedule apps can read the programme.

## Non-functional

The local server listens on `127.0.0.1` only. No token is written into the repository.

Every save goes through `dataio`, so Git diffs stay one line per field.

The editor is for a desktop browser. Phone editing is not a v1 goal.

Forms and buttons are keyboard-accessible. Motion is short and purposeful, following the design skills, and it respects `prefers-reduced-motion`.
