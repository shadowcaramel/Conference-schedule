# -*- coding: utf-8 -*-
"""Prefilled changes-feed entries. Proposing does not write."""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
import time
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
    return httpd


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


def test_propose_change_is_bilingual_and_does_not_write(tmp_path: Path) -> None:
    httpd = _serve(tmp_path)
    port = httpd.server_address[1]
    original = (tmp_path / "changes.json").read_text(encoding="utf-8")
    try:
        status, cancelled = _request(
            port,
            "POST",
            "/api/changes/propose",
            {"kind": "cancelled", "contribution_id": "C-01"},
        )
        assert status == 200
        text = cancelled["proposal"]["text"]
        assert "Title C-01" in text["en"]
        assert "Отменён" in text["ru"]
        assert set(text) >= {"en", "ru"}

        status, moved = _request(
            port,
            "POST",
            "/api/changes/propose",
            {"kind": "moved", "contribution_id": "C-01"},
        )
        assert status == 200
        assert "Moved" in moved["proposal"]["text"]["en"]
        assert "10:00" in moved["proposal"]["text"]["en"]
        assert "Перенос" in moved["proposal"]["text"]["ru"]

        status, retimed = _request(
            port,
            "POST",
            "/api/changes/propose",
            {"kind": "retimed", "session_id": "B001", "previous_start": "09:00", "previous_end": "09:30"},
        )
        assert status == 200
        assert "09:00" in retimed["proposal"]["text"]["en"]
        assert "10:00" in retimed["proposal"]["text"]["en"]
        assert (tmp_path / "changes.json").read_text(encoding="utf-8") == original

        status, stored = _request(
            port,
            "POST",
            "/api/records/changes",
            {"at": cancelled["proposal"]["at"], "text": cancelled["proposal"]["text"]},
        )
        assert status == 201
        saved = load_data(tmp_path)["changes"]
        assert saved[0]["text"]["en"] == text["en"]
        assert saved[0]["text"]["ru"] == text["ru"]
    finally:
        httpd.shutdown()
        httpd.server_close()
