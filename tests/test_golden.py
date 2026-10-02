# -*- coding: utf-8 -*-
"""The JSON build must reproduce the origin/dev site/data.js.

``generatedAt`` is the build clock. ``changes`` is the one placeholder in
``data/changes.json``. Everything else is compared as compact JSON bytes.
The fixture file itself is still a byte copy of that origin/dev ``site/data.js``.
"""
from __future__ import annotations

import json
from pathlib import Path

from build import build_programme, main, write_data_js
from common import ROOT

FIXTURE = ROOT / "tests" / "fixtures" / "golden" / "data.js"
PLACEHOLDER_CHANGES = [{
    "at": "2026-09-21T09:00",
    "text": {"ru": "Тестовое сообщение", "en": "Test message"},
}]


def load_programme(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    payload = text.split("window.PROGRAMME = ", 1)[1].strip()
    if payload.endswith(";"):
        payload = payload[:-1]
    return json.loads(payload)


def compact(model: dict) -> str:
    """The same encoding ``write_data_js`` uses for the programme object."""
    return json.dumps(model, ensure_ascii=False, separators=(",", ":"))


def split_changes(model: dict) -> tuple[str, list]:
    """Bytes before the final ``changes`` array, and that array.

    ``changes`` is the last key. The head is the rest of the programme,
    including the opening brace, so equal heads mean the files differ only
    in that array.
    """
    text = compact(model)
    head, sep, tail = text.rpartition(',"changes":')
    assert sep, "programme JSON has no changes key"
    assert tail.endswith("}")
    return head, json.loads(tail[:-1])


def test_json_build_matches_todays_data_js() -> None:
    expected = load_programme(FIXTURE)
    got = build_programme(ROOT / "data", generated_at=expected["generatedAt"])
    got_head, got_changes = split_changes(got)
    exp_head, _exp_changes = split_changes(expected)
    assert got_head == exp_head
    assert got_changes == PLACEHOLDER_CHANGES


def test_written_data_js_matches_apart_from_generated_at(tmp_path: Path) -> None:
    expected = load_programme(FIXTURE)
    model = build_programme(ROOT / "data", generated_at="2000-01-01T00:00:00+00:00")
    path = write_data_js(model, tmp_path)
    got = load_programme(path)
    assert got["generatedAt"] == "2000-01-01T00:00:00+00:00"
    got["generatedAt"] = expected["generatedAt"]
    got_head, got_changes = split_changes(got)
    exp_head, _exp_changes = split_changes(expected)
    assert got_head == exp_head
    assert got_changes == PLACEHOLDER_CHANGES


def test_check_does_not_fail_on_warnings() -> None:
    assert main(["--check", "--data", str(ROOT / "data")]) == 0


def test_app_js_is_unchanged_from_dev() -> None:
    """The front end is out of scope. This is the SHA-256 of site/app.js on origin/dev."""
    import hashlib
    digest = hashlib.sha256((ROOT / "site" / "app.js").read_bytes()).hexdigest()
    assert digest == "a1e0a7a8f21592e4cb27d58bb790493df95d66c724ae46372e603ae513349bbb"
