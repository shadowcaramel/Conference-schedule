# -*- coding: utf-8 -*-
"""Moving talks, reordering, and undo."""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from dataio import load_data, write_data
from edit import make_server
from programme_factory import base


def _serve(tmp_path: Path):
    write_data(base(), tmp_path)
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>editor</title>", encoding="utf-8")
    httpd = make_server(tmp_path, dist, "127.0.0.1", 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, tmp_path


def _request(port: int, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"} if data is not None else {}
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    last_error: Exception | None = None
    for _ in range(30):
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            return exc.code, json.loads(raw) if raw else {}
        except urllib.error.URLError as exc:
            last_error = exc
            time.sleep(0.05)
    raise AssertionError(f"editor did not accept a connection: {last_error}")


def test_move_reorders_and_updates_both_sessions(tmp_path: Path) -> None:
    httpd, folder = _serve(tmp_path)
    port = httpd.server_address[1]
    try:
        status, moved = _request(
            port,
            "POST",
            "/api/schedule",
            {"contribution_id": "C-01", "session_id": "B002", "index": 0},
        )
        assert status == 200
        stored = load_data(folder)
        by_session = {item["id"]: item["contribution_ids"] for item in stored["sessions"]}
        assert by_session["B001"] == []
        assert by_session["B002"] == ["C-01", "C-02"]
        talks = {item["id"]: item for item in stored["contributions"]}
        assert talks["C-01"]["session_id"] == "B002"
        assert talks["C-01"]["order"] == 1
        assert talks["C-02"]["order"] == 2
        assert moved["placement"]["contributions"]["C-01"]["session_id"] == "B002"
        assert moved["undo"] == 1

        status, down = _request(port, "POST", "/api/reorder", {"contribution_id": "C-01", "direction": "down"})
        assert status == 200
        stored = load_data(folder)
        b002 = next(item for item in stored["sessions"] if item["id"] == "B002")
        assert b002["contribution_ids"] == ["C-02", "C-01"]

        status, edge = _request(port, "POST", "/api/reorder", {"contribution_id": "C-01", "direction": "down"})
        assert status == 409
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_unschedule_and_undo_several_edits(tmp_path: Path) -> None:
    httpd, folder = _serve(tmp_path)
    port = httpd.server_address[1]
    try:
        status, cleared = _request(port, "POST", "/api/schedule", {"contribution_id": "C-02", "session_id": ""})
        assert status == 200
        stored = load_data(folder)
        talk = next(item for item in stored["contributions"] if item["id"] == "C-02")
        assert "session_id" not in talk
        b002 = next(item for item in stored["sessions"] if item["id"] == "B002")
        assert b002["contribution_ids"] == []
        unscheduled = [
            item["id"]
            for item in cleared["contributions"]
            if not item.get("session_id")
        ]
        assert unscheduled == ["C-02"]

        status, before = _request(port, "GET", "/api/data")
        record = next(item for item in before["contributions"] if item["id"] == "C-01")
        record["title"] = "Renamed"
        status, saved = _request(port, "PUT", "/api/records/contributions/C-01", record)
        assert status == 200
        assert saved["undo"] == 2

        status, once = _request(port, "POST", "/api/undo")
        assert status == 200
        assert once["undo"] == 1
        assert next(item["title"] for item in load_data(folder)["contributions"] if item["id"] == "C-01") == "Title C-01"
        assert next(item for item in load_data(folder)["contributions"] if item["id"] == "C-02").get("session_id") is None

        status, twice = _request(port, "POST", "/api/undo")
        assert status == 200
        assert twice["undo"] == 0
        assert next(item for item in load_data(folder)["sessions"] if item["id"] == "B002")["contribution_ids"] == ["C-02"]

        status, empty = _request(port, "POST", "/api/undo")
        assert status == 409
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_session_time_and_room_change_placement(tmp_path: Path) -> None:
    httpd, _folder = _serve(tmp_path)
    port = httpd.server_address[1]
    try:
        status, payload = _request(port, "GET", "/api/data")
        session = next(item for item in payload["sessions"] if item["id"] == "B001")
        session["start"] = "12:15"
        session["end"] = "13:00"
        session["room_id"] = "R2"
        status, saved = _request(port, "PUT", "/api/records/sessions/B001", session)
        assert status == 200
        placed = saved["placement"]["sessions"]["B001"]
        assert placed["start"] == "12:15"
        assert placed["room_id"] == "R2"
        assert saved["placement"]["contributions"]["C-01"]["start"] == "12:15"
    finally:
        httpd.shutdown()
        httpd.server_close()
