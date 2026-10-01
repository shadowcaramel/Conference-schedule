# -*- coding: utf-8 -*-
"""Clock times and the site payload derived from data/*.json.

Contributions store order, duration, and an optional start pin. Start and end
clock times are computed here for validation messages and for site/data.js.
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from common import fmt_time, from_minutes, minutes, parse_time


def utc_offset(timezone: str, on: dt.date) -> str:
    """Offset of an IANA time zone on a given date, as ``+10:00``."""
    aware = dt.datetime(on.year, on.month, on.day, 12, 0, tzinfo=ZoneInfo(timezone))
    total = int(aware.utcoffset().total_seconds())
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    hours, mins = divmod(total // 60, 60)
    return f"{sign}{hours:02d}:{mins:02d}"


def clock_minutes(value: str) -> int | None:
    parsed = parse_time(value)
    if parsed is None:
        return None
    return minutes(parsed)


def bilingual_fill(value: object) -> dict[str, str]:
    """Match the old workbook reader: an empty side is copied from the other."""
    if isinstance(value, str):
        return {"ru": value, "en": value}
    if not isinstance(value, dict):
        return {"ru": "", "en": ""}
    ru = value.get("ru") or ""
    en = value.get("en") or ""
    return {"ru": ru or en, "en": en or ru}


def compact_value(value: object, key: str | None = None) -> object:
    """Drop empty strings, empty bilingual objects, and default status=ok."""
    if isinstance(value, dict):
        out: dict = {}
        for item_key, item in value.items():
            compacted = compact_value(item, key=item_key)
            if compacted is None:
                continue
            out[item_key] = compacted
        if not out:
            return None
        if set(out) <= {"ru", "en"} and not out.get("ru") and not out.get("en"):
            return None
        return out
    if isinstance(value, list):
        return [compact_value(item) for item in value]
    if value is None or value == "":
        return None
    if key == "status" and value == "ok":
        return None
    return value


def _index(records: list) -> dict[str, dict]:
    return {rec["id"]: rec for rec in records if isinstance(rec, dict) and rec.get("id")}


def _duration(contrib: dict, session_type: str, defaults: dict) -> int:
    if contrib.get("duration_min"):
        return int(contrib["duration_min"])
    table = defaults.get("duration_min") or {}
    return int(table.get(session_type) or table.get("section") or 15)


def place(data: dict) -> dict:
    """Computed contribution slots and the end time the site will show.

    Section sessions use the packed end of their talks. Other sessions keep
    the stored end, even when talks run past it.
    """
    conference = data.get("conference") or {}
    defaults = conference.get("defaults") or {}
    sessions = [rec for rec in data.get("sessions") or [] if isinstance(rec, dict)]
    contributions = _index(data.get("contributions") or [])
    session_out: dict[str, dict] = {}
    contrib_out: dict[str, dict] = {}

    for session in sessions:
        sid = session.get("id")
        if not sid:
            continue
        start_min = clock_minutes(session.get("start") or "")
        stated_min = clock_minutes(session.get("end") or "")
        cursor = start_min if start_min is not None else 0
        packed = cursor
        oral_ids = []
        for cid in session.get("contribution_ids") or []:
            contrib = contributions.get(cid)
            if contrib is None or contrib.get("format") == "poster":
                continue
            oral_ids.append(cid)
            dur = _duration(contrib, session.get("type") or "", defaults)
            pin = clock_minutes(contrib["start"]) if contrib.get("start") else None
            if pin is not None:
                cursor = pin
            end_min = cursor + dur
            contrib_out[cid] = {
                "date": session.get("date") or "",
                "start": fmt_time(from_minutes(cursor)),
                "end": fmt_time(from_minutes(end_min)),
                "session_id": sid,
                "duration": dur,
                "format": "oral",
            }
            packed = max(packed, end_min)
            cursor = end_min
        if stated_min is None:
            effective = packed
        elif session.get("type") == "section" and oral_ids and start_min is not None:
            effective = packed
        else:
            effective = stated_min
        session_out[sid] = {
            "date": session.get("date") or "",
            "start": session.get("start") or "",
            "stated_end": session.get("end") or "",
            "effective_end": fmt_time(from_minutes(effective)) if effective is not None else "",
            "packed_end": fmt_time(from_minutes(packed)) if oral_ids and start_min is not None else "",
            "type": session.get("type") or "",
            "track_id": session.get("track_id") or "",
            "room_id": session.get("room_id") or "",
        }

    for contrib in contributions.values():
        if contrib.get("format") != "poster":
            continue
        info = session_out.get(contrib.get("session_id") or "")
        if not info:
            continue
        contrib_out[contrib["id"]] = {
            "date": info["date"],
            "start": info["start"],
            "end": info["effective_end"],
            "session_id": contrib.get("session_id") or "",
            "duration": None,
            "format": "poster",
        }
    return {"sessions": session_out, "contributions": contrib_out}


def _presenting_author(contrib: dict) -> dict | None:
    authors = contrib.get("authors") or []
    for author in authors:
        if author.get("presenting"):
            return author
    return authors[0] if authors else None


def _org_text(org: dict | None) -> str:
    if not org:
        return ""
    name = org.get("name")
    if isinstance(name, str):
        return name
    if isinstance(name, dict):
        return name.get("ru") or name.get("en") or ""
    return ""


def _sponsor_name(org: dict | None) -> dict[str, str]:
    if not org:
        return {"ru": "", "en": ""}
    return bilingual_fill(org.get("name"))


def assemble(data: dict, *, generated_at: str | None = None) -> dict:
    """The object assigned to ``window.PROGRAMME``, before it is wrapped in JS."""
    conference = data["conference"]
    placed = place(data)
    people = _index(data.get("people") or [])
    orgs = _index(data.get("organizations") or [])
    contribs = _index(data.get("contributions") or [])
    rooms = _index(data.get("rooms") or [])
    on = dt.date.fromisoformat(conference["date_start"])
    settings = {
        "title": bilingual_fill(conference.get("title")),
        "shortTitle": bilingual_fill(conference.get("short_title")),
        "dateStart": conference["date_start"],
        "dateEnd": conference["date_end"],
        "city": bilingual_fill(conference.get("city")),
        "venue": bilingual_fill(conference.get("venue")),
        "timezone": conference["timezone"],
        "utcOffset": utc_offset(conference["timezone"], on),
        "website": conference.get("website") or "",
        "contact": conference.get("contact") or "",
        "footnote": bilingual_fill(conference.get("footnote")),
    }

    sections = []
    for track in sorted(data.get("tracks") or [], key=lambda rec: rec.get("id") or ""):
        sections.append({
            "id": track["id"],
            "short": bilingual_fill(track.get("short")),
            "full": bilingual_fill(track.get("full")),
            "color": track.get("color") or "slate",
        })

    blocks = []
    for session in data.get("sessions") or []:
        info = placed["sessions"].get(session["id"])
        if info is None:
            continue
        if session.get("title"):
            title = bilingual_fill(session["title"])
        elif session.get("type") == "section":
            title = {"ru": "", "en": ""}
        else:
            labels = (conference.get("session_types") or {}).get(session.get("type") or "")
            title = bilingual_fill(labels or {"ru": session.get("type") or "", "en": session.get("type") or ""})
        room: object = ""
        if session.get("room_id") and session["room_id"] in rooms:
            room = bilingual_fill(rooms[session["room_id"]].get("label"))
        chairs = session.get("chairs") or []
        if len(chairs) == 1:
            chair = bilingual_fill(chairs[0].get("label"))
        elif chairs:
            filled = [bilingual_fill(item.get("label")) for item in chairs]
            chair = {"ru": ", ".join(item["ru"] for item in filled), "en": ", ".join(item["en"] for item in filled)}
        else:
            chair = {"ru": "", "en": ""}
        talk_ids = []
        for cid in session.get("contribution_ids") or []:
            contrib = contribs.get(cid)
            if contrib and contrib.get("format") != "poster":
                talk_ids.append(cid)
        blocks.append({
            "id": session["id"],
            "date": session.get("date") or "",
            "start": session.get("start") or "",
            "end": info["effective_end"],
            "type": session.get("type") or "",
            "title": title,
            "section": session.get("track_id") or "",
            "talks": talk_ids,
            "room": room,
            "chair": chair,
            "note": bilingual_fill(session.get("note")) if session.get("note") else {"ru": "", "en": ""},
        })
    blocks.sort(key=lambda block: (
        block["date"],
        block["start"],
        block["type"] != "section",
        (block.get("section") or "").zfill(2),
    ))

    talks: dict[str, dict] = {}
    for contrib in data.get("contributions") or []:
        if contrib.get("format") == "poster":
            continue
        author = _presenting_author(contrib) or {}
        person = people.get(author.get("person_id") or "", {})
        org_names = [_org_text(orgs.get(oid)) for oid in author.get("affiliation_ids") or []]
        sponsor = orgs.get(contrib["sponsor_id"]) if contrib.get("sponsor_id") else None
        slot = placed["contributions"].get(contrib["id"])
        title = contrib.get("title")
        if isinstance(title, dict):
            filled = bilingual_fill(title)
            title = filled["ru"] or filled["en"]
        talks[contrib["id"]] = {
            "id": contrib["id"],
            "section": contrib.get("track_id") or "",
            "number": contrib.get("number") or "",
            "last": person.get("family") or "",
            "first": person.get("given") or "",
            "middle": person.get("patronymic") or "",
            "org": ", ".join(name for name in org_names if name),
            "email": person.get("email") or "",
            "title": title or "",
            "duration": slot["duration"] if slot else _duration(contrib, "section", conference.get("defaults") or {}),
            "status": contrib.get("status") or "ok",
            "topic": contrib.get("topic_id") or "",
            "note": bilingual_fill(contrib.get("note")) if contrib.get("note") else {"ru": "", "en": ""},
            "url": (sponsor or {}).get("url") or "",
            "logo": (sponsor or {}).get("logo") or "",
            "sponsorName": _sponsor_name(sponsor),
            "date": slot["date"] if slot else None,
            "start": slot["start"] if slot else None,
            "end": slot["end"] if slot else None,
            "blockId": slot["session_id"] if slot else None,
        }

    posters = []
    seen: set[str] = set()

    def add_poster(contrib: dict) -> None:
        if contrib["id"] in seen:
            return
        seen.add(contrib["id"])
        author = _presenting_author(contrib) or {}
        person = people.get(author.get("person_id") or "", {})
        org_names = [_org_text(orgs.get(oid)) for oid in author.get("affiliation_ids") or []]
        posters.append({
            "id": contrib["id"],
            "last": person.get("family") or "",
            "first": person.get("given") or "",
            "middle": person.get("patronymic") or "",
            "org": ", ".join(name for name in org_names if name),
            "email": person.get("email") or "",
            "title": contrib.get("title") if isinstance(contrib.get("title"), str) else "",
            "section": contrib.get("track_id") or "",
            "board": contrib.get("board") or "",
            "status": contrib.get("status") or "ok",
            "note": bilingual_fill(contrib.get("note")) if contrib.get("note") else {"ru": "", "en": ""},
        })

    for session in data.get("sessions") or []:
        for cid in session.get("contribution_ids") or []:
            contrib = contribs.get(cid)
            if contrib and contrib.get("format") == "poster":
                add_poster(contrib)
    for contrib in data.get("contributions") or []:
        if contrib.get("format") == "poster":
            add_poster(contrib)

    changes = []
    for change in sorted(data.get("changes") or [], key=lambda rec: rec.get("at") or "", reverse=True):
        text = bilingual_fill(change.get("text"))
        if text["ru"] or text["en"]:
            changes.append({"at": change.get("at") or "", "text": text})

    days = []
    seen_days: set[str] = set()
    for block in blocks:
        if block["date"] not in seen_days:
            seen_days.add(block["date"])
            days.append({"date": block["date"]})

    if generated_at is None:
        generated_at = dt.datetime.now().astimezone().replace(microsecond=0).isoformat()
    return compact_value({
        "generatedAt": generated_at,
        "settings": settings,
        "sections": sections,
        "days": days,
        "blocks": blocks,
        "talks": talks,
        "posters": posters,
        "changes": changes,
    })
