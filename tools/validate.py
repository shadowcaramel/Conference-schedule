# -*- coding: utf-8 -*-
"""Validate data/*.json: JSON Schema, canonical form, then cross-record rules.

Errors fail the process. Warnings are printed and do not.

    python tools/validate.py
    python tools/validate.py --data data/
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA_DIR, ROOT, utf8_stdout  # noqa: E402
from dataio import FILES, check_data, load_data  # noqa: E402
from schedule import clock_minutes, place  # noqa: E402

utf8_stdout()

SCHEMA_DIR = ROOT / "schema"
SCHEMA_FILE = {
    "conference": "conference.schema.json",
    "tracks": "track.schema.json",
    "rooms": "room.schema.json",
    "sessions": "session.schema.json",
    "contributions": "contribution.schema.json",
    "people": "person.schema.json",
    "organizations": "organization.schema.json",
    "resources": "resource.schema.json",
    "changes": "change.schema.json",
}


class Diag:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def _registry() -> Registry:
    resources = []
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def _records(data: dict, kind: str) -> list[dict]:
    value = data.get(kind)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _ids(records: list[dict]) -> dict[str, dict]:
    return {rec["id"]: rec for rec in records if isinstance(rec.get("id"), str)}


def _parse_date(value: object) -> dt.date | None:
    if not isinstance(value, str):
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def _overlaps(date_a: str, start_a: str, end_a: str, date_b: str, start_b: str, end_b: str) -> bool:
    return bool(date_a) and date_a == date_b and start_a < end_b and start_b < end_a


def _span(date: str, start: str, end: str) -> str:
    return f"{date} {start}–{end}"


def validate_schema(data: dict, diag: Diag) -> None:
    registry = _registry()
    checker = Draft202012Validator.FORMAT_CHECKER
    for kind, filename in FILES.items():
        schema = json.loads((SCHEMA_DIR / SCHEMA_FILE[kind]).read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, registry=registry, format_checker=checker)
        for error in validator.iter_errors(data.get(kind)):
            where = error.json_path or "$"
            diag.error(f"{filename}: {where}: {error.message}")


def validate_rules(data: dict, diag: Diag) -> None:
    conference = data.get("conference") if isinstance(data.get("conference"), dict) else {}
    tracks = _ids(_records(data, "tracks"))
    rooms = _ids(_records(data, "rooms"))
    sessions = _records(data, "sessions")
    session_by_id = _ids(sessions)
    contributions = _records(data, "contributions")
    contrib_by_id = _ids(contributions)
    people = _ids(_records(data, "people"))
    orgs = _ids(_records(data, "organizations"))

    def unique(kind: str, records: list[dict]) -> None:
        seen: dict[str, int] = {}
        for index, rec in enumerate(records):
            ident = rec.get("id")
            if not isinstance(ident, str) or not ident:
                diag.error(f"{kind}: record {index + 1} has no id")
                continue
            if ident in seen:
                diag.error(f"{kind}: duplicate id {ident}")
            seen[ident] = index

    unique("tracks", _records(data, "tracks"))
    unique("rooms", _records(data, "rooms"))
    unique("sessions", sessions)
    unique("contributions", contributions)
    unique("people", _records(data, "people"))
    unique("organizations", _records(data, "organizations"))
    unique("resources", _records(data, "resources"))
    unique("changes", _records(data, "changes"))

    tz_name = conference.get("timezone")
    if isinstance(tz_name, str) and tz_name:
        try:
            ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            diag.error(f"conference: unknown time zone {tz_name}")
    date_start = _parse_date(conference.get("date_start"))
    date_end = _parse_date(conference.get("date_end"))
    if isinstance(conference.get("date_start"), str) and date_start is None:
        diag.error(f"conference: invalid date_start {conference.get('date_start')}")
    if isinstance(conference.get("date_end"), str) and date_end is None:
        diag.error(f"conference: invalid date_end {conference.get('date_end')}")
    if date_start and date_end and date_end < date_start:
        diag.error("conference: date_end is before date_start")

    def missing_english(where: str, value: object) -> None:
        if isinstance(value, dict) and not (value.get("en") or "").strip():
            diag.warn(f"{where}: missing English title")

    missing_english("conference.title", conference.get("title"))
    missing_english("conference.short_title", conference.get("short_title"))
    for track in tracks.values():
        missing_english(f"track {track['id']} short", track.get("short"))
        missing_english(f"track {track['id']} full", track.get("full"))

    listed: dict[str, list[str]] = defaultdict(list)
    for session in sessions:
        sid = session.get("id")
        if not isinstance(sid, str):
            continue
        seen_in_session: set[str] = set()
        for cid in session.get("contribution_ids") or []:
            if not isinstance(cid, str):
                diag.error(f"{sid}: contribution id is not a string")
                continue
            if cid in seen_in_session:
                diag.error(f"{sid}: contribution {cid} is listed twice")
            seen_in_session.add(cid)
            listed[cid].append(sid)
            if cid not in contrib_by_id:
                diag.error(f"{sid}: unknown contribution {cid}")
        track_id = session.get("track_id")
        if track_id and track_id not in tracks:
            diag.error(f"{sid}: unknown track {track_id}")
        room_id = session.get("room_id")
        if room_id and room_id not in rooms:
            diag.error(f"{sid}: unknown room {room_id}")
        for chair in session.get("chairs") or []:
            if isinstance(chair, dict) and chair.get("person_id") not in people:
                diag.error(f"{sid}: unknown chair {chair.get('person_id')}")
        if session.get("title"):
            missing_english(f"session {sid}", session.get("title"))
        day = _parse_date(session.get("date"))
        if isinstance(session.get("date"), str) and day is None:
            diag.error(f"{sid}: invalid date {session.get('date')}")
        elif day and date_start and date_end and (day < date_start or day > date_end):
            diag.error(f"{sid}: {session.get('date')} is outside the conference dates")
        start_min = clock_minutes(session.get("start") or "")
        end_min = clock_minutes(session.get("end") or "")
        if session.get("start") and start_min is None:
            diag.error(f"{sid}: invalid start {session.get('start')}")
        if session.get("end") and end_min is None:
            diag.error(f"{sid}: invalid end {session.get('end')}")
        if start_min is not None and end_min is not None and end_min <= start_min:
            diag.error(f"{sid}: {session.get('start')}–{session.get('end')} does not end after it starts")

    orders: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for contrib in contributions:
        cid = contrib.get("id")
        if not isinstance(cid, str):
            continue
        title = contrib.get("title")
        if isinstance(title, dict):
            missing_english(f"contribution {cid}", title)
        elif isinstance(title, str) and not title.strip():
            diag.warn(f"contribution {cid}: missing title")
        track_id = contrib.get("track_id")
        if track_id and track_id not in tracks:
            diag.error(f"{cid}: unknown track {track_id}")
        if contrib.get("topic_id") and contrib["topic_id"] not in tracks:
            diag.error(f"{cid}: unknown topic {contrib['topic_id']}")
        if contrib.get("sponsor_id") and contrib["sponsor_id"] not in orgs:
            diag.error(f"{cid}: unknown sponsor {contrib['sponsor_id']}")
        for author in contrib.get("authors") or []:
            if not isinstance(author, dict):
                continue
            if author.get("person_id") not in people:
                diag.error(f"{cid}: unknown person {author.get('person_id')}")
            for oid in author.get("affiliation_ids") or []:
                if oid not in orgs:
                    diag.error(f"{cid}: unknown organization {oid}")
        sid = contrib.get("session_id")
        if not sid:
            diag.warn(f"contribution {cid} is not in a session")
        elif sid not in session_by_id:
            diag.error(f"{cid}: unknown session {sid}")
        else:
            id_list = session_by_id[sid].get("contribution_ids") or []
            if cid not in id_list:
                diag.error(f"{cid}: session_id is {sid} but that session does not list it")
            elif contrib.get("order") != id_list.index(cid) + 1:
                diag.error(
                    f"{cid}: order {contrib.get('order')} does not match its place "
                    f"in {sid} (expected {id_list.index(cid) + 1})"
                )
            session_track = session_by_id[sid].get("track_id")
            if (
                contrib.get("format") == "oral"
                and track_id
                and session_track
                and track_id != session_track
            ):
                diag.error(f"{cid}: track {track_id} does not match session {sid} track {session_track}")
            if isinstance(contrib.get("order"), int):
                orders[sid].append((contrib["order"], cid))
        hosts = listed.get(cid, [])
        if len(hosts) > 1:
            diag.error(f"{cid}: listed in more than one session ({', '.join(hosts)})")
        session = session_by_id.get(sid) if isinstance(sid, str) else None
        if session and contrib.get("format") == "poster" and session.get("type") != "poster":
            diag.error(f"{cid}: poster is in {sid}, which is type {session.get('type')} rather than poster")
        if session and contrib.get("format") == "oral" and session.get("type") == "poster":
            diag.error(f"{cid}: oral contribution is in poster session {sid}")

    for sid, pairs in orders.items():
        seen_order: dict[int, str] = {}
        for order, cid in pairs:
            if order in seen_order:
                diag.error(f"{sid}: duplicate order {order} ({seen_order[order]} and {cid})")
            seen_order[order] = cid

    for resource in _records(data, "resources"):
        cid = resource.get("contribution_id")
        if cid and cid not in contrib_by_id:
            diag.error(f"{resource.get('id')}: unknown contribution {cid}")

    placed = place(data)
    for session in sessions:
        sid = session.get("id")
        info = placed["sessions"].get(sid)
        if not info or not info.get("packed_end"):
            continue
        packed = info["packed_end"]
        stated = info["stated_end"]
        if info["type"] == "section" and packed != stated:
            relation = "before" if packed < stated else "after"
            diag.warn(
                f"Session {sid} {info['date']}: contributions end at {packed}, "
                f"{relation} the stated end {stated}"
            )
        elif info["type"] != "section" and packed > stated:
            diag.warn(
                f"Session {sid} {info['date']}: contributions end at {packed}, "
                f"after the stated end {stated}"
            )

    session_rows = []
    for session in sessions:
        sid = session.get("id")
        info = placed["sessions"].get(sid) or {}
        start_min = clock_minutes(session.get("start") or "")
        end_min = clock_minutes(session.get("end") or "")
        if start_min is None or end_min is None or end_min <= start_min:
            continue
        if not info.get("start") or not info.get("effective_end") or not (info["start"] < info["effective_end"]):
            continue
        session_rows.append((session, info))

    for index, (session, info) in enumerate(session_rows):
        for other, other_info in session_rows[index + 1:]:
            if not _overlaps(info["date"], info["start"], info["effective_end"], other_info["date"], other_info["start"], other_info["effective_end"]):
                continue
            if info["room_id"] and info["room_id"] == other_info["room_id"]:
                diag.error(
                    f"Room {info['room_id']} {info['date']}: "
                    f"{session['id']} {info['start']}–{info['effective_end']} overlaps "
                    f"{other['id']} {other_info['start']}–{other_info['effective_end']}"
                )
            if info["track_id"] and info["track_id"] == other_info["track_id"]:
                diag.error(
                    f"Track {info['track_id']} {info['date']}: "
                    f"{session['id']} {info['start']}–{info['effective_end']} overlaps "
                    f"{other['id']} {other_info['start']}–{other_info['effective_end']}"
                )

    by_person: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for contrib in contributions:
        slot = placed["contributions"].get(contrib.get("id"))
        if not slot or not slot.get("start") or not slot.get("end"):
            continue
        for author in contrib.get("authors") or []:
            if not isinstance(author, dict) or not author.get("presenting", True):
                continue
            pid = author.get("person_id")
            if isinstance(pid, str):
                by_person[pid].append((contrib["id"], slot))

    for pid, slots in by_person.items():
        person = people.get(pid) or {}
        name = " ".join(part for part in (person.get("family"), person.get("given")) if part)
        for i, (cid, slot) in enumerate(slots):
            for other_id, other in slots[i + 1:]:
                if _overlaps(slot["date"], slot["start"], slot["end"], other["date"], other["start"], other["end"]):
                    diag.warn(
                        f"Person {pid} {name}: {cid} {_span(slot['date'], slot['start'], slot['end'])} "
                        f"overlaps {other_id} {_span(other['date'], other['start'], other['end'])}"
                    )

    for session, info in session_rows:
        for chair in session.get("chairs") or []:
            if not isinstance(chair, dict):
                continue
            pid = chair.get("person_id")
            for cid, slot in by_person.get(pid, []):
                if slot.get("session_id") == session.get("id"):
                    # Speaking in the sitting you chair is the usual case.
                    continue
                if _overlaps(info["date"], info["start"], info["effective_end"], slot["date"], slot["start"], slot["end"]):
                    diag.warn(
                        f"Chair {pid} of {session['id']} {_span(info['date'], info['start'], info['effective_end'])} "
                        f"is also presenting {cid} {_span(slot['date'], slot['start'], slot['end'])}"
                    )


def validate_data(data: dict, diag: Diag | None = None) -> Diag:
    diag = diag or Diag()
    validate_schema(data, diag)
    validate_rules(data, diag)
    return diag


def validate_dir(data_dir: Path, diag: Diag | None = None) -> Diag:
    diag = diag or Diag()
    for msg in check_data(data_dir):
        diag.error(msg)
    try:
        data = load_data(data_dir)
    except (OSError, json.JSONDecodeError) as exc:
        diag.error(str(exc))
        return diag
    return validate_data(data, diag)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate the programme JSON.")
    parser.add_argument("--data", type=Path, default=DATA_DIR)
    args = parser.parse_args(argv)
    diag = validate_dir(args.data)
    for msg in diag.warnings:
        print(f"ПРЕДУПРЕЖДЕНИЕ: {msg}")
    for msg in diag.errors:
        print(f"ОШИБКА: {msg}")
    print(f"\nОшибок: {len(diag.errors)}, предупреждений: {len(diag.warnings)}.")
    if diag.errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
