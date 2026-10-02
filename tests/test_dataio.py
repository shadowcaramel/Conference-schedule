# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from dataio import check_data, write_data
from programme_factory import base


def test_round_trip_is_canonical(tmp_path: Path) -> None:
    write_data(base(), tmp_path)
    assert check_data(tmp_path) == []


def test_reordered_keys_fail_the_format_check(tmp_path: Path) -> None:
    write_data(base(), tmp_path)
    path = tmp_path / "rooms.json"
    rooms = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(rooms, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    errors = check_data(tmp_path)
    assert any("rooms.json" in msg for msg in errors)


def test_repository_data_is_canonical() -> None:
    assert check_data(Path("data")) == []
