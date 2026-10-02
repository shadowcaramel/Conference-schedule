# -*- coding: utf-8 -*-
"""Delete guards, duplicate people, and merge."""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from dataio import load_data, write_data
from edit import make_server
from programme_factory import base, bilingual


def _editor(tmp_path: Path):
    write_data(base(), tmp_path)
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>editor</title>", encoding="utf-8")
    httpd = make_server(tmp_path, dist, "127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
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


def test_delete_is_blocked_while_referenced(tmp_path: Path) -> None:
    httpd, folder = _editor(tmp_path)
    port = httpd.server_address[1]
    try:
        status, blocked = _request(port, "DELETE", "/api/records/rooms/R1")
        assert status == 409
        assert blocked["references"] == [{"kind": "sessions", "id": "B001", "field": "room_id"}]
        assert "R1" in [item["id"] for item in load_data(folder)["rooms"]]

        status, person = _request(port, "DELETE", "/api/records/people/PER-0001")
        assert status == 409
        assert {"kind": "contributions", "id": "C-01", "field": "authors.person_id"} in person["references"]

        status, conference = _request(port, "DELETE", "/api/records/conference/demo")
        assert status == 400
        assert "cannot be deleted" in conference["error"]
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_unreferenced_record_can_be_deleted(tmp_path: Path) -> None:
    httpd, folder = _editor(tmp_path)
    port = httpd.server_address[1]
    try:
        status, created = _request(port, "POST", "/api/records/rooms", {"label": {"ru": "Spare", "en": "Spare"}})
        assert status == 201
        room_id = created["record"]["id"]
        status, deleted = _request(port, "DELETE", f"/api/records/rooms/{room_id}")
        assert status == 200
        assert deleted["deleted"] == {"kind": "rooms", "id": room_id}
        assert room_id not in [item["id"] for item in load_data(folder)["rooms"]]
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_contribution_delete_offers_cancelled_until_forced(tmp_path: Path) -> None:
    httpd, folder = _editor(tmp_path)
    port = httpd.server_address[1]
    try:
        status, warned = _request(port, "DELETE", "/api/records/contributions/C-01")
        assert status == 409
        assert warned["offer"] == "cancelled"
        assert "stars" in warned["error"]
        assert {"kind": "sessions", "id": "B001", "field": "contribution_ids"} in warned["references"]
        assert [item["id"] for item in load_data(folder)["contributions"]] == ["C-01", "C-02"]

        status, forced = _request(port, "DELETE", "/api/records/contributions/C-01?force=1")
        assert status == 409
        assert forced["references"]

        status, created = _request(
            port,
            "POST",
            "/api/records/contributions",
            {
                "format": "oral",
                "title": "Loose talk",
                "authors": [{"person_id": "PER-0001", "affiliation_ids": [], "presenting": True}],
                "status": "ok",
            },
        )
        assert status == 201
        new_id = created["record"]["id"]
        status, still = _request(port, "DELETE", f"/api/records/contributions/{new_id}")
        assert status == 409
        assert still["offer"] == "cancelled"
        assert still["references"] == []
        status, gone = _request(port, "DELETE", f"/api/records/contributions/{new_id}?force=1")
        assert status == 200
        assert new_id not in [item["id"] for item in load_data(folder)["contributions"]]
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_duplicate_people_and_merge_rewrites_every_reference(tmp_path: Path) -> None:
    data = base()
    data["people"].append(
        {"id": "PER-0003", "family": "one", "given": "Alex", "email": "per-0003@example.org"}
    )
    data["sessions"][0]["chairs"] = [{"person_id": "PER-0003", "label": bilingual("One A.", "A. One")}]
    data["contributions"][1]["authors"][0]["person_id"] = "PER-0003"
    write_data(data, tmp_path)
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>editor</title>", encoding="utf-8")
    httpd = make_server(tmp_path, dist, "127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.server_address[1]
    try:
        status, groups = _request(port, "GET", "/api/duplicates")
        assert status == 200
        assert groups["groups"] == [{"family": "one", "initial": "a", "ids": ["PER-0001", "PER-0003"]}]

        status, merged = _request(port, "POST", "/api/people/merge", {"keep": "PER-0001", "drop": "PER-0003"})
        assert status == 200
        assert merged["rewritten"] == 2
        stored = load_data(tmp_path)
        ids = [item["id"] for item in stored["people"]]
        assert "PER-0003" not in ids
        assert stored["contributions"][1]["authors"][0]["person_id"] == "PER-0001"
        assert stored["sessions"][0]["chairs"][0]["person_id"] == "PER-0001"
        assert merged["diagnostics"]["errors"] == []
    finally:
        httpd.shutdown()
        httpd.server_close()
