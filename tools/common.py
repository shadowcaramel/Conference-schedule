# -*- coding: utf-8 -*-
"""Shared paths and time helpers for the programme tools.

Programme content lives in ``data/*.json``. Room labels, session-type labels,
and default durations live in those files, not here.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SITE_DIR = ROOT / "site"
DIST_DIR = ROOT / "dist"


def utf8_stdout() -> None:
    """Make print() safe for Cyrillic in Windows consoles."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover
        pass


def clean(value) -> str:
    """Normalise a cell to a trimmed string with single spaces (None -> '')."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).replace("\u00a0", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


_TIME_RE = re.compile(r"^\s*(\d{1,2})\s*:+\s*(\d{2})\s*$")


def parse_time(value) -> dt.time | None:
    """Accept datetime.time, datetime.datetime, Excel fraction, '16:15', '19::00'."""
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.time().replace(second=0, microsecond=0)
    if isinstance(value, dt.time):
        return value.replace(second=0, microsecond=0)
    if isinstance(value, (int, float)):
        minutes_in_day = int(round(float(value) * 24 * 60)) % (24 * 60)
        return dt.time(minutes_in_day // 60, minutes_in_day % 60)
    match = _TIME_RE.match(str(value))
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        if 0 <= hour < 24 and 0 <= minute < 60:
            return dt.time(hour, minute)
    return None


def parse_date(value) -> dt.date | None:
    """Accept datetime/date, '2026-09-21', '21.09.2026'."""
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    text = clean(value)
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def fmt_time(t: dt.time | None) -> str:
    return "" if t is None else f"{t.hour:02d}:{t.minute:02d}"


def minutes(t: dt.time) -> int:
    return t.hour * 60 + t.minute


def from_minutes(m: int) -> dt.time:
    m %= 24 * 60
    return dt.time(m // 60, m % 60)


def stamp_site_cache(site_dir: Path | None = None) -> dict[str, str]:
    """Put content hashes on app.css / app.js / data.js in index.html and bump sw.js CACHE.

    Phones otherwise keep a stale data.js for hours (no Cache-Control on the FTP host).
    The committed files do not carry these hashes; the build writes them.
    """
    site = site_dir or SITE_DIR
    tags: dict[str, str] = {}
    parts: list[str] = []
    for name in ("app.css", "app.js", "data.js"):
        path = site / name
        if not path.is_file():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:8]
        tags[name] = digest
        parts.append(digest)
    html_path = site / "index.html"
    if html_path.is_file() and tags:
        text = html_path.read_text(encoding="utf-8")
        for name, digest in tags.items():
            text = re.sub(
                rf'(href|src)="{re.escape(name)}(\?v=[^"]*)?"',
                rf'\1="{name}?v={digest}"',
                text,
            )
        html_path.write_text(text, encoding="utf-8", newline="\n")
    sw_path = site / "sw.js"
    if sw_path.is_file() and parts:
        sw_tag = hashlib.sha256("".join(parts).encode("ascii")).hexdigest()[:8]
        tags["sw"] = sw_tag
        sw = sw_path.read_text(encoding="utf-8")
        sw, n = re.subn(
            r"const CACHE = 'nucleus2026(?:-[^']*)?';",
            f"const CACHE = 'nucleus2026-{sw_tag}';",
            sw,
            count=1,
        )
        if n:
            sw_path.write_text(sw, encoding="utf-8", newline="\n")
    return tags
