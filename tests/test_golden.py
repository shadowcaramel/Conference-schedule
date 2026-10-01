# -*- coding: utf-8 -*-
"""The JSON build must reproduce today's site/data.js, apart from generatedAt."""
from __future__ import annotations

import json
from pathlib import Path

from build import build_programme, main, write_data_js
from common import ROOT

FIXTURE = ROOT / "tests" / "fixtures" / "golden" / "data.js"


def load_programme(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    payload = text.split("window.PROGRAMME = ", 1)[1].strip()
    if payload.endswith(";"):
        payload = payload[:-1]
    return json.loads(payload)


def test_json_build_matches_todays_data_js() -> None:
    expected = load_programme(FIXTURE)
    got = build_programme(ROOT / "data", generated_at=expected["generatedAt"])
    assert got == expected


def test_written_data_js_matches_apart_from_generated_at(tmp_path: Path) -> None:
    expected = load_programme(FIXTURE)
    model = build_programme(ROOT / "data", generated_at="2000-01-01T00:00:00+00:00")
    path = write_data_js(model, tmp_path)
    got = load_programme(path)
    assert got["generatedAt"] == "2000-01-01T00:00:00+00:00"
    got["generatedAt"] = expected["generatedAt"]
    assert got == expected


def test_check_does_not_fail_on_warnings() -> None:
    assert main(["--check", "--data", str(ROOT / "data")]) == 0


def test_app_js_is_unchanged_from_dev() -> None:
    """The front end is out of scope. This is the SHA-256 of site/app.js on origin/dev."""
    import hashlib
    digest = hashlib.sha256((ROOT / "site" / "app.js").read_bytes()).hexdigest()
    assert digest == "a1e0a7a8f21592e4cb27d58bb790493df95d66c724ae46372e603ae513349bbb"
