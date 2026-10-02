# -*- coding: utf-8 -*-
"""Canonical reader and writer for data/*.json.

Every tool that writes programme JSON uses this module. Records are sorted by
id, keys stay in a fixed order, and the bytes are UTF-8 with 2-space indent,
no \\u escapes, and a final newline. ``python tools/dataio.py --check`` fails
when a file is not in that form.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA_DIR, utf8_stdout  # noqa: E402

utf8_stdout()

# File stem -> filename. Conference is one object; the rest are arrays.
FILES: dict[str, str] = {
    "conference": "conference.json",
    "tracks": "tracks.json",
    "rooms": "rooms.json",
    "sessions": "sessions.json",
    "contributions": "contributions.json",
    "people": "people.json",
    "organizations": "organizations.json",
    "resources": "resources.json",
    "changes": "changes.json",
}

ARRAY_FILES = [name for name in FILES if name != "conference"]

SESSION_TYPE_ORDER = (
    "plenary",
    "jubilee",
    "sponsor",
    "section",
    "break",
    "lunch",
    "registration",
    "opening",
    "closing",
    "poster",
    "social",
)

DURATION_ORDER = ("plenary", "jubilee", "sponsor", "section")


def dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def bilingual(value: object) -> dict[str, str] | None:
    """Return ``{ru, en}`` or None when both sides are empty."""
    if not isinstance(value, dict):
        return None
    ru, en = _text(value.get("ru")), _text(value.get("en"))
    if not ru and not en:
        return None
    return {"ru": ru, "en": en}


def _keep(value: object) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _pick(record: dict, keys: tuple[str, ...], keep_empty: tuple[str, ...] = ()) -> dict:
    """Copy keys in order. Drop None, "", [], and {} unless the key is listed."""
    out: dict = {}
    for key in keys:
        if key not in record:
            continue
        value = record[key]
        if key not in keep_empty and not _keep(value):
            continue
        if value is None:
            continue
        out[key] = value
    return out


def canon_conference(raw: dict) -> dict:
    defaults = raw.get("defaults") or {}
    durations = defaults.get("duration_min") or {}
    duration_out = {key: durations[key] for key in DURATION_ORDER if key in durations}
    for key, value in durations.items():
        if key not in duration_out:
            duration_out[key] = value
    types_in = raw.get("session_types") or {}
    session_types = {key: bilingual(types_in[key]) for key in SESSION_TYPE_ORDER if key in types_in}
    for key, value in types_in.items():
        if key not in session_types:
            session_types[key] = bilingual(value)
    out = {
        "id": raw["id"],
        "title": bilingual(raw.get("title")),
        "short_title": bilingual(raw.get("short_title")),
        "date_start": raw["date_start"],
        "date_end": raw["date_end"],
        "city": bilingual(raw.get("city")),
        "venue": bilingual(raw.get("venue")),
        "timezone": raw["timezone"],
        "website": _text(raw.get("website")),
        "contact": _text(raw.get("contact")),
        "footnote": bilingual(raw.get("footnote")),
        "languages": list(raw.get("languages") or []),
        "defaults": {"duration_min": duration_out},
        "session_types": session_types,
    }
    return _pick(out, tuple(out.keys()))


def canon_track(raw: dict) -> dict:
    return _pick(
        {
            "id": raw["id"],
            "short": bilingual(raw.get("short")),
            "full": bilingual(raw.get("full")),
            "color": raw.get("color"),
        },
        ("id", "short", "full", "color"),
    )


def canon_room(raw: dict) -> dict:
    return _pick(
        {
            "id": raw["id"],
            "label": bilingual(raw.get("label")),
            "aliases": list(raw.get("aliases") or []),
        },
        ("id", "label", "aliases"),
    )


def canon_chair(raw: dict) -> dict:
    return _pick(
        {"person_id": raw["person_id"], "label": bilingual(raw.get("label"))},
        ("person_id", "label"),
    )


def canon_session(raw: dict) -> dict:
    chairs = [canon_chair(item) for item in (raw.get("chairs") or [])]
    return _pick(
        {
            "id": raw["id"],
            "date": raw["date"],
            "start": raw["start"],
            "end": raw["end"],
            "type": raw["type"],
            "title": bilingual(raw.get("title")),
            "track_id": raw.get("track_id") or "",
            "room_id": raw.get("room_id") or "",
            "chairs": chairs,
            "contribution_ids": list(raw.get("contribution_ids") or []),
            "note": bilingual(raw.get("note")),
        },
        (
            "id",
            "date",
            "start",
            "end",
            "type",
            "title",
            "track_id",
            "room_id",
            "chairs",
            "contribution_ids",
            "note",
        ),
        keep_empty=("contribution_ids",),
    )


def _canon_title(value: object) -> object:
    if isinstance(value, dict):
        return bilingual(value)
    return _text(value)


def canon_author(raw: dict) -> dict:
    return {
        "person_id": raw["person_id"],
        "affiliation_ids": list(raw.get("affiliation_ids") or []),
        "presenting": bool(raw.get("presenting", False)),
    }


def canon_contribution(raw: dict) -> dict:
    title = _canon_title(raw.get("title"))
    return _pick(
        {
            "id": raw["id"],
            "format": raw["format"],
            "track_id": raw.get("track_id") or "",
            "session_id": raw.get("session_id") or "",
            "order": raw.get("order"),
            "number": raw.get("number") or "",
            "title": title,
            "authors": [canon_author(item) for item in raw.get("authors") or []],
            "duration_min": raw.get("duration_min"),
            "start": raw.get("start") or "",
            "status": raw.get("status") or "",
            "topic_id": raw.get("topic_id") or "",
            "note": bilingual(raw.get("note")),
            "sponsor_id": raw.get("sponsor_id") or "",
            "board": raw.get("board") or "",
        },
        (
            "id",
            "format",
            "track_id",
            "session_id",
            "order",
            "number",
            "title",
            "authors",
            "duration_min",
            "start",
            "status",
            "topic_id",
            "note",
            "sponsor_id",
            "board",
        ),
    )


def canon_person(raw: dict) -> dict:
    return _pick(
        {
            "id": raw["id"],
            "family": raw.get("family") or "",
            "given": raw.get("given") or "",
            "patronymic": raw.get("patronymic") or "",
            "email": raw.get("email") or "",
        },
        ("id", "family", "given", "patronymic", "email"),
    )


def _canon_name(value: object) -> object:
    if isinstance(value, dict):
        return bilingual(value)
    return _text(value)


def canon_organization(raw: dict) -> dict:
    return _pick(
        {
            "id": raw["id"],
            "name": _canon_name(raw.get("name")),
            "url": raw.get("url") or "",
            "logo": raw.get("logo") or "",
        },
        ("id", "name", "url", "logo"),
    )


def canon_resource(raw: dict) -> dict:
    return _pick(
        {
            "id": raw["id"],
            "contribution_id": raw.get("contribution_id") or "",
            "kind": raw.get("kind") or "",
            "url": raw.get("url") or "",
            "lang": raw.get("lang") or "",
        },
        ("id", "contribution_id", "kind", "url", "lang"),
    )


def canon_change(raw: dict) -> dict:
    return _pick(
        {"id": raw["id"], "at": raw.get("at") or "", "text": bilingual(raw.get("text"))},
        ("id", "at", "text"),
    )


CANON = {
    "tracks": canon_track,
    "rooms": canon_room,
    "sessions": canon_session,
    "contributions": canon_contribution,
    "people": canon_person,
    "organizations": canon_organization,
    "resources": canon_resource,
    "changes": canon_change,
}


def _sort_records(records: list[dict]) -> list[dict]:
    return sorted(records, key=lambda rec: rec.get("id") or "")


def canonical_value(kind: str, parsed: object) -> object:
    if kind == "conference":
        if not isinstance(parsed, dict):
            raise TypeError("conference.json must be an object")
        return canon_conference(parsed)
    fn = CANON[kind]
    if not isinstance(parsed, list):
        raise TypeError(f"{FILES[kind]} must be an array")
    return _sort_records([fn(item) for item in parsed])


def load_data(data_dir: Path | None = None) -> dict:
    root = data_dir or DATA_DIR
    out: dict = {}
    for kind, filename in FILES.items():
        out[kind] = json.loads((root / filename).read_text(encoding="utf-8"))
    return out


def write_data(data: dict, data_dir: Path | None = None) -> None:
    root = data_dir or DATA_DIR
    root.mkdir(parents=True, exist_ok=True)
    for kind, filename in FILES.items():
        text = dumps(canonical_value(kind, data[kind]))
        (root / filename).write_text(text, encoding="utf-8", newline="\n")


def check_data(data_dir: Path | None = None) -> list[str]:
    """Return human-readable problems. Empty means every file is canonical."""
    root = data_dir or DATA_DIR
    errors: list[str] = []
    for kind, filename in FILES.items():
        path = root / filename
        if not path.is_file():
            errors.append(f"{filename} is missing")
            continue
        text = path.read_text(encoding="utf-8")
        try:
            parsed = json.loads(text)
            expected = dumps(canonical_value(kind, parsed))
        except (json.JSONDecodeError, TypeError, KeyError, ValueError) as exc:
            errors.append(f"{filename}: {exc}")
            continue
        if text != expected:
            errors.append(f"{filename} is not in canonical form (key order, id sort, or whitespace)")
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Check that data/*.json is in canonical form.")
    parser.add_argument("--data", type=Path, default=DATA_DIR)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    errors = check_data(args.data)
    for msg in errors:
        print(f"ОШИБКА: {msg}")
    if errors:
        print(f"\nФормат JSON: {len(errors)} файл(ов) не в каноническом виде.")
        return 1
    print(f"Формат JSON в порядке ({args.data}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
