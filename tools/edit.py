# -*- coding: utf-8 -*-
"""Local programme editor.

A standard-library HTTP server bound to 127.0.0.1. It serves ``editor/dist``
and a small JSON API: read the programme, save one record, delete one record
when nothing still points at it, merge duplicate people, and validate. Every
write goes through ``dataio``. Validation calls ``validate.py`` directly.

Preview and publish are later slices. This server does not upload anything.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA_DIR, ROOT, utf8_stdout  # noqa: E402
from dataio import FILES, canonical_value, load_data, write_data  # noqa: E402
from schedule import place  # noqa: E402
from validate import validate_data  # noqa: E402

utf8_stdout()

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1"})
MAX_BODY = 1_000_000
UNDO_LIMIT = 20
DIST_DIR = ROOT / "editor" / "dist"

# Opaque ids for new records. Existing ids are never rewritten.
_ID_SHAPE: dict[str, tuple[str, int]] = {
    "tracks": ("T-", 2),
    "rooms": ("ROOM-", 3),
    "sessions": ("B", 3),
    "contributions": ("C-", 4),
    "people": ("PER-", 4),
    "organizations": ("ORG-", 3),
    "resources": ("RES-", 4),
    "changes": ("CHG-", 4),
}

_RECORD_PATH = re.compile(r"^/api/records/(?P<kind>[a-z]+)/(?P<rid>.+)$")
_CREATE_PATH = re.compile(r"^/api/records/(?P<kind>[a-z]+)$")


class EditError(Exception):
    def __init__(self, status: int, message: str, extra: dict | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.extra = extra or {}


def check_host(host: str) -> None:
    """Refuse any bind address that is not loopback."""
    if host not in LOOPBACK_HOSTS:
        raise SystemExit(
            f"The editor only listens on 127.0.0.1 (got {host})."
        )


def mentions(record_id: str, message: str) -> bool:
    """True when ``message`` cites ``record_id`` as its own token."""
    if not record_id:
        return False
    return bool(
        re.search(
            r"(?<![A-Za-z0-9-])" + re.escape(record_id) + r"(?![A-Za-z0-9-])",
            message,
        )
    )


def diagnostics_payload(data: dict, record_id: str | None = None) -> dict:
    diag = validate_data(data)
    payload: dict = {
        "diagnostics": {"errors": list(diag.errors), "warnings": list(diag.warnings)},
    }
    if record_id:
        payload["for_record"] = {
            "id": record_id,
            "errors": [msg for msg in diag.errors if mentions(record_id, msg)],
            "warnings": [msg for msg in diag.warnings if mentions(record_id, msg)],
        }
    return payload


def placement_payload(data: dict) -> dict:
    """Clock times from ``schedule.place``. The editor does not recompute them."""
    try:
        placed = place(data)
    except (TypeError, ValueError, KeyError):
        return {"sessions": {}, "contributions": {}}
    return placed


def read_programme(data_dir: Path) -> dict:
    data = load_data(data_dir)
    payload = dict(data)
    payload["placement"] = placement_payload(data)
    payload["diagnostics"] = diagnostics_payload(data)["diagnostics"]
    return payload


def generate_id(kind: str, existing: set[str]) -> str:
    prefix, width = _ID_SHAPE[kind]
    highest = 0
    for ident in existing:
        if not ident.startswith(prefix):
            continue
        tail = ident[len(prefix):]
        if tail.isdigit():
            highest = max(highest, int(tail))
    number = highest + 1
    while True:
        candidate = f"{prefix}{number:0{width}d}"
        if candidate not in existing:
            return candidate
        number += 1


def _existing_ids(records: list) -> set[str]:
    return {item["id"] for item in records if isinstance(item, dict) and isinstance(item.get("id"), str)}


def _canon_or_400(kind: str, value: object) -> None:
    try:
        canonical_value(kind, value)
    except (KeyError, TypeError, ValueError) as exc:
        raise EditError(400, f"record cannot be stored: {exc}") from exc


def update_record(data_dir: Path, kind: str, record_id: str, body: dict) -> dict:
    if kind not in FILES:
        raise EditError(404, f"unknown record type {kind}")
    if not isinstance(body, dict):
        raise EditError(400, "record must be an object")
    if "id" in body and body["id"] != record_id:
        raise EditError(400, "id is read-only")
    record = dict(body)
    record["id"] = record_id
    data = load_data(data_dir)
    if kind == "conference":
        current = data["conference"].get("id") if isinstance(data.get("conference"), dict) else None
        if current != record_id:
            raise EditError(404, "no conference record with that id")
        data["conference"] = record
        _canon_or_400(kind, data["conference"])
    else:
        items = data.get(kind)
        if not isinstance(items, list):
            raise EditError(400, f"{kind} is not a list")
        index = next((i for i, item in enumerate(items) if isinstance(item, dict) and item.get("id") == record_id), None)
        if index is None:
            raise EditError(404, f"no {kind} record {record_id}")
        items[index] = record
        _canon_or_400(kind, items)
    write_data(data, data_dir)
    stored = load_data(data_dir)
    saved = stored["conference"] if kind == "conference" else next(
        item for item in stored[kind] if item.get("id") == record_id
    )
    payload = {"record": saved, "placement": placement_payload(stored)}
    payload.update(diagnostics_payload(stored, record_id))
    return payload


def create_record(data_dir: Path, kind: str, body: dict) -> dict:
    if kind == "conference":
        raise EditError(400, "the conference record already exists")
    if kind not in _ID_SHAPE:
        raise EditError(404, f"unknown record type {kind}")
    if not isinstance(body, dict):
        raise EditError(400, "record must be an object")
    if body.get("id"):
        raise EditError(400, "do not send an id; the server generates one")
    data = load_data(data_dir)
    items = data.get(kind)
    if not isinstance(items, list):
        raise EditError(400, f"{kind} is not a list")
    record = dict(body)
    record["id"] = generate_id(kind, _existing_ids(items))
    items.append(record)
    _canon_or_400(kind, items)
    write_data(data, data_dir)
    stored = load_data(data_dir)
    saved = next(item for item in stored[kind] if item.get("id") == record["id"])
    payload = {"record": saved, "placement": placement_payload(stored)}
    payload.update(diagnostics_payload(stored, record["id"]))
    return payload


def _record_id(item: object) -> str | None:
    if isinstance(item, dict) and isinstance(item.get("id"), str):
        return item["id"]
    return None


def _add_ref(refs: list[dict], kind: str, ident: str | None, field: str) -> None:
    if ident:
        refs.append({"kind": kind, "id": ident, "field": field})


def find_references(data: dict, kind: str, record_id: str) -> list[dict]:
    """Records that still point at ``record_id``. Delete is blocked while this is non-empty."""
    refs: list[dict] = []
    contributions = data.get("contributions") if isinstance(data.get("contributions"), list) else []
    sessions = data.get("sessions") if isinstance(data.get("sessions"), list) else []
    resources = data.get("resources") if isinstance(data.get("resources"), list) else []

    if kind == "people":
        for contrib in contributions:
            cid = _record_id(contrib)
            authors = contrib.get("authors") if isinstance(contrib, dict) else None
            if any(isinstance(author, dict) and author.get("person_id") == record_id for author in authors or []):
                _add_ref(refs, "contributions", cid, "authors.person_id")
        for session in sessions:
            chairs = session.get("chairs") if isinstance(session, dict) else None
            if any(isinstance(chair, dict) and chair.get("person_id") == record_id for chair in chairs or []):
                _add_ref(refs, "sessions", _record_id(session), "chairs.person_id")
    elif kind == "organizations":
        for contrib in contributions:
            if not isinstance(contrib, dict):
                continue
            cid = _record_id(contrib)
            if contrib.get("sponsor_id") == record_id:
                _add_ref(refs, "contributions", cid, "sponsor_id")
            authors = contrib.get("authors") or []
            if any(
                isinstance(author, dict) and record_id in (author.get("affiliation_ids") or [])
                for author in authors
            ):
                _add_ref(refs, "contributions", cid, "authors.affiliation_ids")
    elif kind == "tracks":
        for session in sessions:
            if isinstance(session, dict) and session.get("track_id") == record_id:
                _add_ref(refs, "sessions", _record_id(session), "track_id")
        for contrib in contributions:
            if not isinstance(contrib, dict):
                continue
            cid = _record_id(contrib)
            if contrib.get("track_id") == record_id:
                _add_ref(refs, "contributions", cid, "track_id")
            if contrib.get("topic_id") == record_id:
                _add_ref(refs, "contributions", cid, "topic_id")
    elif kind == "rooms":
        for session in sessions:
            if isinstance(session, dict) and session.get("room_id") == record_id:
                _add_ref(refs, "sessions", _record_id(session), "room_id")
    elif kind == "sessions":
        for contrib in contributions:
            if isinstance(contrib, dict) and contrib.get("session_id") == record_id:
                _add_ref(refs, "contributions", _record_id(contrib), "session_id")
    elif kind == "contributions":
        for session in sessions:
            if isinstance(session, dict) and record_id in (session.get("contribution_ids") or []):
                _add_ref(refs, "sessions", _record_id(session), "contribution_ids")
        for resource in resources:
            if isinstance(resource, dict) and resource.get("contribution_id") == record_id:
                _add_ref(refs, "resources", _record_id(resource), "contribution_id")
    return refs


def _given_initial(given: object) -> str:
    if not isinstance(given, str):
        return ""
    text = given.strip()
    return text[:1].casefold() if text else ""


def duplicate_people(data: dict) -> dict:
    """People who share a family name and the same given-name initial."""
    people = data.get("people") if isinstance(data.get("people"), list) else []
    buckets: dict[tuple[str, str], list[str]] = {}
    for person in people:
        if not isinstance(person, dict) or not isinstance(person.get("id"), str):
            continue
        family = person.get("family") if isinstance(person.get("family"), str) else ""
        key = (family.strip().casefold(), _given_initial(person.get("given")))
        if not key[0]:
            continue
        buckets.setdefault(key, []).append(person["id"])
    groups = []
    for (family, initial), ids in sorted(buckets.items()):
        if len(ids) > 1:
            groups.append({"family": family, "initial": initial, "ids": ids})
    return {"groups": groups}


def _rewrite_person(data: dict, keep: str, drop: str) -> int:
    rewritten = 0
    for contrib in data.get("contributions") or []:
        if not isinstance(contrib, dict):
            continue
        for author in contrib.get("authors") or []:
            if isinstance(author, dict) and author.get("person_id") == drop:
                author["person_id"] = keep
                rewritten += 1
    for session in data.get("sessions") or []:
        if not isinstance(session, dict):
            continue
        for chair in session.get("chairs") or []:
            if isinstance(chair, dict) and chair.get("person_id") == drop:
                chair["person_id"] = keep
                rewritten += 1
    return rewritten


def merge_people(data_dir: Path, body: dict) -> dict:
    keep = body.get("keep")
    drop = body.get("drop")
    if not isinstance(keep, str) or not isinstance(drop, str) or not keep or not drop:
        raise EditError(400, "merge needs keep and drop person ids")
    if keep == drop:
        raise EditError(400, "keep and drop must be different people")
    data = load_data(data_dir)
    people = data.get("people")
    if not isinstance(people, list):
        raise EditError(400, "people is not a list")
    ids = _existing_ids(people)
    if keep not in ids or drop not in ids:
        raise EditError(404, "person not found")
    rewritten = _rewrite_person(data, keep, drop)
    data["people"] = [person for person in people if not (isinstance(person, dict) and person.get("id") == drop)]
    _canon_or_400("people", data["people"])
    _canon_or_400("contributions", data["contributions"])
    _canon_or_400("sessions", data["sessions"])
    write_data(data, data_dir)
    stored = load_data(data_dir)
    payload = {
        "kept": keep,
        "dropped": drop,
        "rewritten": rewritten,
        "placement": placement_payload(stored),
    }
    payload.update(diagnostics_payload(stored))
    return payload


def delete_record(data_dir: Path, kind: str, record_id: str, force: bool) -> dict:
    if kind == "conference":
        raise EditError(400, "the conference record cannot be deleted")
    if kind not in FILES:
        raise EditError(404, f"unknown record type {kind}")
    data = load_data(data_dir)
    items = data.get(kind)
    if not isinstance(items, list):
        raise EditError(400, f"{kind} is not a list")
    index = next((i for i, item in enumerate(items) if isinstance(item, dict) and item.get("id") == record_id), None)
    if index is None:
        raise EditError(404, f"no {kind} record {record_id}")
    refs = find_references(data, kind, record_id)
    if kind == "contributions":
        extra = {
            "references": refs,
            "offer": "cancelled",
        }
        message = (
            "Deleting this talk drops its id from visitor stars and #my= links. "
            "Mark it cancelled instead."
        )
        if refs:
            message += " Other records still point at it."
        if refs or not force:
            raise EditError(409, message, extra)
    elif refs:
        raise EditError(
            409,
            "This record is still referenced.",
            {"references": refs},
        )
    del items[index]
    _canon_or_400(kind, items)
    write_data(data, data_dir)
    stored = load_data(data_dir)
    payload = {"deleted": {"kind": kind, "id": record_id}, "placement": placement_payload(stored)}
    payload.update(diagnostics_payload(stored))
    return payload


def validate_request(data_dir: Path, body: dict) -> dict:
    """Validate the files, or a draft record substituted in memory. Never writes."""
    data = load_data(data_dir)
    record_id: str | None = None
    if body.get("kind") or body.get("record"):
        kind = body.get("kind")
        record = body.get("record")
        if kind not in FILES:
            raise EditError(400, "unknown record type")
        if not isinstance(record, dict):
            raise EditError(400, "record must be an object")
        if kind == "conference":
            current = data["conference"].get("id") if isinstance(data.get("conference"), dict) else None
            if record.get("id") and record.get("id") != current:
                raise EditError(400, "id is read-only")
            draft = dict(record)
            draft["id"] = current
            data["conference"] = draft
            record_id = current if isinstance(current, str) else None
        else:
            if not isinstance(record.get("id"), str) or not record["id"]:
                raise EditError(400, "a draft record needs its existing id")
            record_id = record["id"]
            items = data.get(kind)
            if not isinstance(items, list):
                raise EditError(400, f"{kind} is not a list")
            index = next((i for i, item in enumerate(items) if isinstance(item, dict) and item.get("id") == record_id), None)
            if index is None:
                items.append(record)
            else:
                items[index] = record
    return diagnostics_payload(data, record_id)


def _sync_orders(data: dict, session_ids: set[str]) -> None:
    by_id = {item.get("id"): item for item in data.get("contributions") or [] if isinstance(item, dict)}
    for session in data.get("sessions") or []:
        if not isinstance(session, dict) or session.get("id") not in session_ids:
            continue
        for index, cid in enumerate(session.get("contribution_ids") or []):
            talk = by_id.get(cid)
            if isinstance(talk, dict):
                talk["session_id"] = session["id"]
                talk["order"] = index + 1


def schedule_contribution(data_dir: Path, body: dict) -> dict:
    """Move a talk to a session and index, or clear its session to unschedule it."""
    cid = body.get("contribution_id")
    if not isinstance(cid, str) or not cid:
        raise EditError(400, "contribution_id is required")
    session_id = body.get("session_id") if body.get("session_id") is not None else ""
    if not isinstance(session_id, str):
        raise EditError(400, "session_id must be a string")
    data = load_data(data_dir)
    contribs = data.get("contributions")
    sessions = data.get("sessions")
    if not isinstance(contribs, list) or not isinstance(sessions, list):
        raise EditError(400, "programme lists are missing")
    contrib = next((item for item in contribs if isinstance(item, dict) and item.get("id") == cid), None)
    if contrib is None:
        raise EditError(404, f"no contributions record {cid}")
    touched: set[str] = set()
    for session in sessions:
        if not isinstance(session, dict):
            continue
        ids = list(session.get("contribution_ids") or [])
        if cid in ids:
            touched.add(session["id"])
            session["contribution_ids"] = [item for item in ids if item != cid]
    if session_id:
        dest = next((item for item in sessions if isinstance(item, dict) and item.get("id") == session_id), None)
        if dest is None:
            raise EditError(404, f"no sessions record {session_id}")
        ids = list(dest.get("contribution_ids") or [])
        if body.get("index") is None:
            index = len(ids)
        else:
            try:
                index = int(body["index"])
            except (TypeError, ValueError) as exc:
                raise EditError(400, "index must be an integer") from exc
        index = max(0, min(index, len(ids)))
        ids.insert(index, cid)
        dest["contribution_ids"] = ids
        touched.add(session_id)
        _sync_orders(data, touched)
    else:
        contrib["session_id"] = ""
        contrib["order"] = ""
        _sync_orders(data, touched)
    _canon_or_400("contributions", contribs)
    _canon_or_400("sessions", sessions)
    write_data(data, data_dir)
    return read_programme(data_dir)


def reorder_contribution(data_dir: Path, body: dict) -> dict:
    cid = body.get("contribution_id")
    direction = body.get("direction")
    if not isinstance(cid, str) or not cid:
        raise EditError(400, "contribution_id is required")
    if direction not in {"up", "down"}:
        raise EditError(400, "direction must be up or down")
    data = load_data(data_dir)
    host = None
    index = -1
    for session in data.get("sessions") or []:
        if not isinstance(session, dict):
            continue
        ids = list(session.get("contribution_ids") or [])
        if cid in ids:
            host = session
            index = ids.index(cid)
            break
    if host is None:
        raise EditError(409, "the talk is not in a session")
    new_index = index - 1 if direction == "up" else index + 1
    ids = host.get("contribution_ids") or []
    if new_index < 0 or new_index >= len(ids):
        raise EditError(409, "the talk is already at that end of the session")
    return schedule_contribution(
        data_dir,
        {"contribution_id": cid, "session_id": host["id"], "index": new_index},
    )


def _plain(value: object, lang: str, languages: list[str]) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        text = value.get(lang)
        if isinstance(text, str) and text.strip():
            return text
        for code in languages:
            alt = value.get(code)
            if isinstance(alt, str) and alt.strip():
                return alt
    return ""


def _change_sentence(kind: str, lang: str, title: str, detail: str, previous: str) -> str:
    if lang == "ru":
        if kind == "cancelled":
            return f"Отменён доклад «{title}»."
        if kind == "moved":
            return f"Перенос: «{title}» теперь {detail}."
        was = f" (было {previous})" if previous else ""
        return f"Новое время: «{title}» {detail}{was}."
    if kind == "cancelled":
        return f"Cancelled: {title}."
    if kind == "moved":
        return f"Moved: {title} is now {detail}."
    was = f" (was {previous})" if previous else ""
    return f"New time: {title} {detail}{was}."


def propose_change(data_dir: Path, body: dict) -> dict:
    """Prefill a changes-feed entry. This does not write."""
    kind = body.get("kind")
    if kind not in {"cancelled", "moved", "retimed"}:
        raise EditError(400, "kind must be cancelled, moved, or retimed")
    data = load_data(data_dir)
    conference = data.get("conference") if isinstance(data.get("conference"), dict) else {}
    languages = [code for code in (conference.get("languages") or []) if isinstance(code, str)] or ["en", "ru"]
    placed = placement_payload(data)
    cid = body.get("contribution_id")
    if isinstance(cid, str) and cid:
        contrib = next(
            (item for item in data.get("contributions") or [] if isinstance(item, dict) and item.get("id") == cid),
            None,
        )
        if contrib is None:
            raise EditError(404, f"no contributions record {cid}")
        slot = (placed.get("contributions") or {}).get(cid) or {}
        session_id = contrib.get("session_id") or ""
        session = next(
            (item for item in data.get("sessions") or [] if isinstance(item, dict) and item.get("id") == session_id),
            None,
        )
        texts = {}
        for lang in languages:
            talk_title = _plain(contrib.get("title"), lang, languages) or cid
            if kind == "cancelled":
                line_detail = ""
            elif kind == "moved":
                label = _plain(session.get("title"), lang, languages) if isinstance(session, dict) else ""
                when = slot.get("start") or ""
                line_detail = f"in {label or session_id or 'the programme'}"
                if lang == "ru":
                    line_detail = f"в секции «{label or session_id or 'программе'}»"
                if when:
                    line_detail += f" at {when}" if lang != "ru" else f" в {when}"
            else:
                when = slot.get("start") or body.get("start") or ""
                line_detail = f"starts at {when}" if when else "has a new time"
                if lang == "ru":
                    line_detail = f"начинается в {when}" if when else "получил новое время"
            prev = body.get("previous_start") if isinstance(body.get("previous_start"), str) else ""
            texts[lang] = _change_sentence(kind, lang, talk_title, line_detail, prev if kind == "retimed" else "")
    else:
        session_id = body.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            raise EditError(400, "a contribution_id or session_id is required")
        session = next(
            (item for item in data.get("sessions") or [] if isinstance(item, dict) and item.get("id") == session_id),
            None,
        )
        if session is None:
            raise EditError(404, f"no sessions record {session_id}")
        slot = (placed.get("sessions") or {}).get(session_id) or {}
        texts = {}
        prev_start = body.get("previous_start") if isinstance(body.get("previous_start"), str) else ""
        prev_end = body.get("previous_end") if isinstance(body.get("previous_end"), str) else ""
        previous = f"{prev_start}–{prev_end}" if prev_start or prev_end else ""
        for lang in languages:
            label = _plain(session.get("title"), lang, languages) or session_id
            start = slot.get("start") or session.get("start") or ""
            end = slot.get("effective_end") or session.get("end") or ""
            if lang == "ru":
                detail = f"теперь {start}–{end}"
            else:
                detail = f"now runs {start}–{end}"
            texts[lang] = _change_sentence("retimed", lang, label, detail, previous)
    if "ru" not in texts:
        texts["ru"] = texts.get("en", "")
    if "en" not in texts:
        texts["en"] = texts.get("ru", "")
    return {"proposal": {"at": date.today().isoformat(), "text": texts, "kind": kind}}


def make_server(data_dir: Path, dist_dir: Path, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    check_host(host)
    directory = Path(data_dir)
    assets = Path(dist_dir)

    class EditorHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args: object) -> None:
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            try:
                if path == "/api/data":
                    with self.server.lock:  # type: ignore[attr-defined]
                        payload = read_programme(directory)
                        payload["undo"] = len(self.server.undo)  # type: ignore[attr-defined]
                    self._send_json(200, payload)
                    return
                if path == "/api/undo":
                    with self.server.lock:  # type: ignore[attr-defined]
                        payload = {"undo": len(self.server.undo)}  # type: ignore[attr-defined]
                    self._send_json(200, payload)
                    return
                if path == "/api/validate":
                    with self.server.lock:  # type: ignore[attr-defined]
                        payload = validate_request(directory, {})
                    self._send_json(200, payload)
                    return
                if path == "/api/duplicates":
                    with self.server.lock:  # type: ignore[attr-defined]
                        payload = duplicate_people(load_data(directory))
                    self._send_json(200, payload)
                    return
                if path.startswith("/api/"):
                    raise EditError(404, "unknown API path")
                self._send_static(path)
            except EditError as exc:
                self._send_error(exc)

        def do_POST(self) -> None:  # noqa: N802
            self._route_write("POST")

        def do_PUT(self) -> None:  # noqa: N802
            self._route_write("PUT")

        def do_DELETE(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = unquote(parsed.path)
            force = parse_qs(parsed.query).get("force", ["0"])[0] in {"1", "true", "yes"}
            try:
                match = _RECORD_PATH.fullmatch(path)
                if not match:
                    raise EditError(404, "unknown API path")
                with self.server.lock:  # type: ignore[attr-defined]
                    payload = self._commit(lambda: delete_record(directory, match.group("kind"), match.group("rid"), force))
                self._send_json(200, payload)
            except EditError as exc:
                self._send_error(exc)

        def _route_write(self, method: str) -> None:
            path = unquote(self.path.split("?", 1)[0])
            try:
                body = self._read_json()
                with self.server.lock:  # type: ignore[attr-defined]
                    if path == "/api/validate" and method == "POST":
                        payload = validate_request(directory, body)
                        status = 200
                    elif path == "/api/changes/propose" and method == "POST":
                        payload = propose_change(directory, body)
                        status = 200
                    elif path == "/api/undo" and method == "POST":
                        payload = self._undo()
                        status = 200
                    elif path == "/api/schedule" and method == "POST":
                        payload = self._commit(lambda: schedule_contribution(directory, body))
                        status = 200
                    elif path == "/api/reorder" and method == "POST":
                        payload = self._commit(lambda: reorder_contribution(directory, body))
                        status = 200
                    elif path == "/api/people/merge" and method == "POST":
                        payload = self._commit(lambda: merge_people(directory, body))
                        status = 200
                    else:
                        created = _CREATE_PATH.fullmatch(path)
                        updated = _RECORD_PATH.fullmatch(path)
                        if method == "POST" and created:
                            payload = self._commit(lambda: create_record(directory, created.group("kind"), body))
                            status = 201
                        elif method == "PUT" and updated:
                            payload = self._commit(
                                lambda: update_record(
                                    directory,
                                    updated.group("kind"),
                                    updated.group("rid"),
                                    body,
                                )
                            )
                            status = 200
                        elif path.startswith("/api/"):
                            raise EditError(404, "unknown API path")
                        else:
                            raise EditError(405, "method not allowed")
                self._send_json(status, payload)
            except EditError as exc:
                self._send_error(exc)

        def _commit(self, fn):
            before = json.loads(json.dumps(load_data(directory)))
            payload = fn()
            stack = self.server.undo  # type: ignore[attr-defined]
            stack.append(before)
            if len(stack) > UNDO_LIMIT:
                del stack[:-UNDO_LIMIT]
            if isinstance(payload, dict):
                payload["undo"] = len(stack)
            return payload

        def _undo(self) -> dict:
            stack = self.server.undo  # type: ignore[attr-defined]
            if not stack:
                raise EditError(409, "nothing to undo")
            previous = stack.pop()
            write_data(previous, directory)
            payload = read_programme(directory)
            payload["undo"] = len(stack)
            return payload

        def _send_error(self, exc: EditError) -> None:
            payload = {"error": exc.message, **exc.extra}
            self._send_json(exc.status, payload)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length") or "0")
            if length < 0 or length > MAX_BODY:
                raise EditError(413, "body is too large")
            raw = self.rfile.read(length) if length else b""
            if not raw:
                return {}
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise EditError(400, "body is not JSON") from exc
            if not isinstance(parsed, dict):
                raise EditError(400, "body must be a JSON object")
            return parsed

        def _send_json(self, status: int, payload: dict) -> None:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def _send_static(self, url_path: str) -> None:
            rel = unquote(url_path)
            if rel.endswith("/"):
                rel += "index.html"
            if rel == "":
                rel = "/index.html"
            root = assets.resolve()
            candidate = (root / rel.lstrip("/")).resolve()
            if root != candidate and root not in candidate.parents:
                raise EditError(403, "path is outside the editor build")
            if candidate.is_file():
                self._send_file(candidate)
                return
            suffix = Path(rel).suffix
            index = root / "index.html"
            if not suffix and index.is_file():
                self._send_file(index)
                return
            message = (
                "The editor build is missing. From the repository root run: "
                "cd editor && npm install && npm run build"
            )
            raw = message.encode("utf-8")
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _send_file(self, path: Path) -> None:
            raw = path.read_bytes()
            mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            if mime.startswith("text/") or mime in {"application/javascript", "image/svg+xml"}:
                mime += "; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(raw)

    httpd = ThreadingHTTPServer((host, port), EditorHandler)
    httpd.lock = threading.Lock()  # type: ignore[attr-defined]
    httpd.undo = []  # type: ignore[attr-defined]
    return httpd


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the local programme editor on 127.0.0.1.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--data", type=Path, default=DATA_DIR)
    parser.add_argument("--dist", type=Path, default=DIST_DIR)
    args = parser.parse_args(argv)
    check_host(args.host)
    httpd = make_server(args.data, args.dist, args.host, args.port)
    host, port = httpd.server_address[:2]
    print(f"Programme editor at http://{host}:{port}/")
    print("Listening on loopback only. This process does not deploy.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
