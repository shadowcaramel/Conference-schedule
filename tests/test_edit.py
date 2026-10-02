# -*- coding: utf-8 -*-
"""HTTP API for the local editor: save, validate, and id safety."""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from dataio import check_data, load_data, write_data
from edit import check_host, make_server
from programme_factory import base
from schedule import place


@pytest.fixture
def editor(tmp_path: Path):
    write_data(base(), tmp_path)
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>editor</title>", encoding="utf-8")
    httpd = make_server(tmp_path, dist, "127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd.server_address[1], tmp_path
    finally:
        httpd.shutdown()
        httpd.server_close()


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


def _contribution(payload: dict, ident: str = "C-01") -> dict:
    return next(item for item in payload["contributions"] if item["id"] == ident)


def test_get_data_placement_matches_schedule(editor) -> None:
    port, folder = editor
    status, payload = _request(port, "GET", "/api/data")
    assert status == 200
    assert payload["placement"] == place(load_data(folder))
    slot = payload["placement"]["contributions"]["C-01"]
    assert slot["start"] == "10:00"
    assert slot["end"] == "10:30"
    assert payload["diagnostics"]["errors"] == []


def test_save_writes_through_dataio_and_keeps_errors(editor) -> None:
    port, folder = editor
    status, before = _request(port, "GET", "/api/data")
    assert status == 200
    record = dict(_contribution(before))
    record["title"] = "Renamed talk"
    record["authors"] = [
        {"person_id": "PER-9999", "affiliation_ids": ["ORG-001"], "presenting": True}
    ]
    status, saved = _request(port, "PUT", "/api/records/contributions/C-01", record)
    assert status == 200
    assert saved["record"]["id"] == "C-01"
    assert saved["record"]["title"] == "Renamed talk"
    assert any("unknown person PER-9999" in msg for msg in saved["diagnostics"]["errors"])
    assert any("C-01" in msg for msg in saved["for_record"]["errors"])
    assert check_data(folder) == []
    stored = load_data(folder)
    assert _contribution(stored)["title"] == "Renamed talk"
    assert _contribution(stored, "C-02")["title"] == "Title C-02"


def test_validate_draft_does_not_write(editor) -> None:
    port, folder = editor
    original = (folder / "contributions.json").read_text(encoding="utf-8")
    status, before = _request(port, "GET", "/api/data")
    record = dict(_contribution(before))
    record["title"] = {"ru": "Название", "en": ""}
    status, report = _request(
        port,
        "POST",
        "/api/validate",
        {"kind": "contributions", "record": record},
    )
    assert status == 200
    assert any("missing English title" in msg for msg in report["for_record"]["warnings"])
    assert (folder / "contributions.json").read_text(encoding="utf-8") == original


def test_existing_ids_are_read_only(editor) -> None:
    port, folder = editor
    status, before = _request(port, "GET", "/api/data")
    record = dict(_contribution(before))
    record["id"] = "C-99"
    status, rejected = _request(port, "PUT", "/api/records/contributions/C-01", record)
    assert status == 400
    assert "read-only" in rejected["error"]
    status, missing = _request(port, "PUT", "/api/records/contributions/C-99", {
        "id": "C-99",
        "format": "oral",
        "title": "Nope",
        "authors": [{"person_id": "PER-0001", "affiliation_ids": [], "presenting": True}],
        "status": "ok",
    })
    assert status == 404
    ids = [item["id"] for item in load_data(folder)["contributions"]]
    assert ids == ["C-01", "C-02"]
    status, client_id = _request(port, "POST", "/api/records/contributions", {
        "id": "HACK",
        "format": "oral",
        "title": "Nope",
        "authors": [{"person_id": "PER-0001", "affiliation_ids": [], "presenting": True}],
        "status": "ok",
    })
    assert status == 400
    assert "generates" in client_id["error"]
    assert [item["id"] for item in load_data(folder)["contributions"]] == ["C-01", "C-02"]


def test_new_records_get_generated_ids(editor) -> None:
    port, folder = editor
    body = {
        "format": "oral",
        "title": "Added talk",
        "authors": [{"person_id": "PER-0001", "affiliation_ids": ["ORG-001"], "presenting": True}],
        "status": "ok",
    }
    status, first = _request(port, "POST", "/api/records/contributions", body)
    status_b, second = _request(port, "POST", "/api/records/contributions", dict(body, title="Another"))
    assert status == 201
    assert status_b == 201
    assert first["record"]["id"] == "C-0003"
    assert second["record"]["id"] == "C-0004"
    assert check_data(folder) == []
    stored_ids = [item["id"] for item in load_data(folder)["contributions"]]
    assert stored_ids == ["C-0003", "C-0004", "C-01", "C-02"]


def test_server_refuses_a_public_bind() -> None:
    with pytest.raises(SystemExit):
        check_host("0.0.0.0")
    with pytest.raises(SystemExit):
        make_server(Path("."), Path("."), "0.0.0.0", 0)


def test_editor_page_is_served(editor) -> None:
    port, _folder = editor
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=10) as response:
        assert response.status == 200
        assert b"editor" in response.read()
