# -*- coding: utf-8 -*-
"""Small in-memory programmes for validator tests."""
from __future__ import annotations


def bilingual(ru: str, en: str | None = None) -> dict:
    return {"ru": ru, "en": en if en is not None else ru}


def conference() -> dict:
    return {
        "id": "demo",
        "title": bilingual("Демо", "Demo"),
        "short_title": bilingual("Демо", "Demo"),
        "date_start": "2026-09-21",
        "date_end": "2026-09-22",
        "city": bilingual("Город", "City"),
        "venue": bilingual("Зал", "Hall"),
        "timezone": "Asia/Vladivostok",
        "footnote": bilingual("Сноска", "Note"),
        "languages": ["ru", "en"],
        "defaults": {"duration_min": {"plenary": 30, "jubilee": 30, "sponsor": 15, "section": 15}},
        "session_types": {
            "section": bilingual("Секция", "Section"),
            "plenary": bilingual("Пленарный", "Plenary"),
            "poster": bilingual("Постеры", "Posters"),
        },
    }


def track(track_id: str) -> dict:
    return {
        "id": track_id,
        "short": bilingual(f"Трек {track_id}", f"Track {track_id}"),
        "full": bilingual(f"Трек {track_id}", f"Track {track_id}"),
        "color": "blue",
    }


def room(room_id: str) -> dict:
    return {"id": room_id, "label": bilingual(room_id, room_id)}


def person(person_id: str, family: str, given: str) -> dict:
    return {"id": person_id, "family": family, "given": given, "email": f"{person_id.lower()}@example.org"}


def author(person_id: str) -> dict:
    return {"person_id": person_id, "affiliation_ids": ["ORG-001"], "presenting": True}


def contribution(cid: str, *, session: str, order: int, track_id: str, person_id: str, duration: int = 30, number: str = "1") -> dict:
    return {
        "id": cid,
        "format": "oral",
        "track_id": track_id,
        "session_id": session,
        "order": order,
        "number": number,
        "title": f"Title {cid}",
        "authors": [author(person_id)],
        "duration_min": duration,
        "status": "ok",
    }


def session(sid: str, *, start: str, end: str, track_id: str, room_id: str, talks: list[str], date: str = "2026-09-21", chairs: list | None = None) -> dict:
    rec = {
        "id": sid,
        "date": date,
        "start": start,
        "end": end,
        "type": "section",
        "title": bilingual(sid, sid),
        "track_id": track_id,
        "room_id": room_id,
        "contribution_ids": talks,
    }
    if chairs:
        rec["chairs"] = chairs
    return rec


def base() -> dict:
    return {
        "conference": conference(),
        "tracks": [track("1"), track("2")],
        "rooms": [room("R1"), room("R2")],
        "people": [person("PER-0001", "One", "Ann"), person("PER-0002", "Two", "Bob")],
        "organizations": [{"id": "ORG-001", "name": "Lab"}],
        "sessions": [
            session("B001", start="10:00", end="10:30", track_id="1", room_id="R1", talks=["C-01"]),
            session("B002", start="11:00", end="11:30", track_id="2", room_id="R2", talks=["C-02"]),
        ],
        "contributions": [
            contribution("C-01", session="B001", order=1, track_id="1", person_id="PER-0001"),
            contribution("C-02", session="B002", order=1, track_id="2", person_id="PER-0002", number="2"),
        ],
        "resources": [],
        "changes": [],
    }


def overlap_programme() -> dict:
    """Room overlap, track overlap, and one person in two talks at once."""
    data = base()
    data["sessions"] = [
        session(
            "B001", start="10:00", end="11:00", track_id="1", room_id="R1", talks=["C-01"],
            chairs=[{"person_id": "PER-0001", "label": bilingual("One A.", "A. One")}],
        ),
        session("B002", start="10:30", end="11:30", track_id="1", room_id="R2", talks=["C-02"]),
        session("B003", start="14:00", end="15:00", track_id="2", room_id="R1", talks=["C-03"]),
        session("B004", start="14:30", end="15:30", track_id="2", room_id="R1", talks=["C-04"]),
    ]
    data["contributions"] = [
        contribution("C-01", session="B001", order=1, track_id="1", person_id="PER-0001", duration=60),
        contribution("C-02", session="B002", order=1, track_id="1", person_id="PER-0001", duration=60, number="2"),
        contribution("C-03", session="B003", order=1, track_id="2", person_id="PER-0002", duration=60, number="3"),
        contribution("C-04", session="B004", order=1, track_id="2", person_id="PER-0002", duration=60, number="4"),
    ]
    return data
