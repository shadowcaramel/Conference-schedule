# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

from dataio import write_data
from programme_factory import base, bilingual, contribution, overlap_programme, session
from validate import validate_data, validate_dir

FIXTURE = Path("tests/fixtures/invalid")
ROOT_DATA = Path("data")


def _ids(messages: list[str], *needles: str) -> bool:
    return any(all(needle in msg for needle in needles) for msg in messages)


def test_valid_programme_has_no_findings() -> None:
    diag = validate_data(base())
    assert diag.errors == []
    assert diag.warnings == []


def test_overlap_fixture_reports_room_track_and_double_booking() -> None:
    diag = validate_dir(FIXTURE)
    assert _ids(diag.errors, "Room R1", "B003", "B004")
    assert _ids(diag.errors, "Track 1", "B001", "B002")
    assert not any(msg.startswith("Room") and "B001" in msg and "B002" in msg for msg in diag.errors)
    assert _ids(diag.warnings, "PER-0001", "C-01", "C-02")
    assert _ids(diag.warnings, "Chair PER-0001", "B001", "C-02")


def test_duplicate_ids_and_orders() -> None:
    data = base()
    data["contributions"].append(contribution(
        "C-01", session="B002", order=1, track_id="2", person_id="PER-0002", number="9",
    ))
    data["sessions"][1]["contribution_ids"] = ["C-01"]
    diag = validate_data(data)
    assert _ids(diag.errors, "duplicate id C-01")
    assert _ids(diag.errors, "more than one session")


def test_duplicate_order_inside_a_session() -> None:
    data = base()
    extra = contribution("C-03", session="B001", order=1, track_id="1", person_id="PER-0002", number="3")
    data["contributions"].append(extra)
    data["sessions"][0]["contribution_ids"] = ["C-01", "C-03"]
    diag = validate_data(data)
    assert _ids(diag.errors, "duplicate order 1", "C-01", "C-03")


def test_missing_references() -> None:
    data = base()
    data["contributions"][0]["authors"][0]["person_id"] = "PER-9999"
    data["contributions"][0]["authors"][0]["affiliation_ids"] = ["ORG-999"]
    data["sessions"][0]["room_id"] = "NO-SUCH-ROOM"
    data["sessions"][0]["track_id"] = "9"
    diag = validate_data(data)
    assert _ids(diag.errors, "unknown person PER-9999")
    assert _ids(diag.errors, "unknown organization ORG-999")
    assert _ids(diag.errors, "unknown room NO-SUCH-ROOM")
    assert _ids(diag.errors, "unknown track 9")


def test_session_time_and_date_rules() -> None:
    data = base()
    data["sessions"].append(session(
        "B003", start="12:00", end="11:00", track_id="1", room_id="R1", talks=[],
    ))
    data["sessions"].append(session(
        "B004", start="10:00", end="11:00", track_id="2", room_id="R2", talks=[], date="2026-10-01",
    ))
    data["conference"]["timezone"] = "Not/AZone"
    diag = validate_data(data)
    assert _ids(diag.errors, "B003", "does not end after it starts")
    assert _ids(diag.errors, "B004", "outside the conference")
    assert _ids(diag.errors, "unknown time zone")


def test_poster_and_oral_session_types() -> None:
    data = base()
    data["sessions"].append({
        "id": "B003",
        "date": "2026-09-21",
        "start": "16:00",
        "end": "17:00",
        "type": "poster",
        "room_id": "R2",
        "contribution_ids": ["P-01", "C-03"],
    })
    data["contributions"].append({
        "id": "P-01",
        "format": "poster",
        "track_id": "1",
        "session_id": "B001",
        "order": 2,
        "title": "Poster",
        "authors": data["contributions"][0]["authors"],
        "status": "ok",
    })
    data["sessions"][0]["contribution_ids"] = ["C-01", "P-01"]
    data["contributions"].append(contribution(
        "C-03", session="B003", order=2, track_id="1", person_id="PER-0002", number="8",
    ))
    # C-03's track is 1 but the poster session has no track; oral-in-poster is the error.
    data["contributions"][-1]["track_id"] = "1"
    diag = validate_data(data)
    assert _ids(diag.errors, "P-01", "rather than poster")
    assert _ids(diag.errors, "C-03", "poster session")


def test_warnings_for_time_title_and_chair() -> None:
    data = base()
    data["contributions"][0]["duration_min"] = 45
    data["tracks"][0]["short"] = bilingual("Трек", "")
    data["contributions"].append({
        "id": "C-09",
        "format": "oral",
        "track_id": "1",
        "title": "Unplaced",
        "authors": data["contributions"][0]["authors"],
        "duration_min": 15,
        "status": "ok",
    })
    data["sessions"][0]["chairs"] = [{"person_id": "PER-0002", "label": bilingual("Two B.", "B. Two")}]
    # Bob chairs B001 (10:00–10:30) and speaks in B002, which does not overlap.
    diag = validate_data(data)
    assert _ids(diag.warnings, "B001", "before the stated end") or _ids(diag.warnings, "B001", "after the stated end")
    assert _ids(diag.warnings, "track 1 short", "missing English title")
    assert _ids(diag.warnings, "C-09", "not in a session")
    assert not any("Chair PER-0002" in msg for msg in diag.warnings)

    data["sessions"][1]["start"] = "10:15"
    data["sessions"][1]["end"] = "10:45"
    diag = validate_data(data)
    assert _ids(diag.warnings, "Chair PER-0002", "B001", "C-02")


def test_current_programme_has_no_overlap_errors() -> None:
    diag = validate_dir(ROOT_DATA)
    assert diag.errors == []
    assert len(diag.warnings) == 10
    assert _ids(diag.warnings, "Session B034", "17:45", "18:00")
    assert _ids(diag.warnings, "Session B047", "16:00", "16:15")
    # Several posters by one person share the poster session. No two oral talks overlap.
    for left, right in (
        ("POST-02", "POST-03"),
        ("POST-02", "POST-04"),
        ("POST-03", "POST-04"),
        ("POST-05", "POST-06"),
        ("POST-31", "POST-32"),
        ("POST-31", "POST-33"),
        ("POST-32", "POST-33"),
        ("POST-38", "POST-39"),
    ):
        assert _ids(diag.warnings, left, right)
    assert not any(msg.startswith("Room ") or msg.startswith("Track ") for msg in diag.errors)
    assert not any("Chair " in msg for msg in diag.warnings)
