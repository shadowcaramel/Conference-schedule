# -*- coding: utf-8 -*-
"""Shared constants for the ЯДРО-2026 programme tools (migrate.py / build.py).

The normalized workbook ``data/programme.xlsx`` is the single source of truth.
Everything here describes its layout so that both scripts agree on it.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PROGRAMME_XLSX = DATA_DIR / "programme.xlsx"
SITE_DIR = ROOT / "site"
DIST_DIR = ROOT / "dist"

# --------------------------------------------------------------------------- sheets
SHEET_SETTINGS = "Настройки"
SHEET_SECTIONS = "Секции"
SHEET_BLOCKS = "Блоки"
SHEET_TALKS = "Доклады"
SHEET_POSTERS = "Постеры"
SHEET_CHANGES = "Изменения"

# --------------------------------------------------------------------------- columns
COLS_SETTINGS = ["Параметр", "Значение (RU)", "Значение (EN)", "Пояснение"]

COLS_SECTIONS = [
    "№",
    "Краткое название (RU)",
    "Краткое название (EN)",
    "Полное название (RU)",
    "Полное название (EN)",
    "Председатель (RU)",
    "Председатель (EN)",
    "Цвет",
    "Аудитория",
]

COLS_BLOCKS = [
    "Дата",
    "Начало",
    "Конец",
    "Тип",
    "Название (RU)",
    "Название (EN)",
    "Секция",
    "Доклады",
    "Аудитория",
    "Председатель (RU)",
    "Председатель (EN)",
    "Примечание (RU)",
    "Примечание (EN)",
]

COLS_TALKS = [
    "ID",
    "Секция",
    "№",
    "Фамилия",
    "Имя",
    "Отчество",
    "Организация",
    "Email",
    "Название",
    "Длительность (мин)",
    "Начало",
    "Статус",
    "Тематика",
    "Примечание (RU)",
    "Примечание (EN)",
    "Сайт",
    "Логотип",
    "Спонсор (RU)",
    "Спонсор (EN)",
]

COLS_POSTERS = [
    "ID",
    "Фамилия",
    "Имя",
    "Отчество",
    "Организация",
    "Email",
    "Название",
    "Секция",
    "№ стенда",
    "Статус",
    "Примечание (RU)",
    "Примечание (EN)",
]

COLS_CHANGES = ["Дата/время", "Текст (RU)", "Текст (EN)"]

# --------------------------------------------------------------------------- vocabularies
# Block types: RU key used in the sheet -> (machine id, EN label, RU label)
BLOCK_TYPES = {
    "пленарный": ("plenary", "Plenary talk", "Пленарный доклад"),
    "юбилейный": ("jubilee", "Anniversary talk", "Юбилейный доклад"),
    "спонсор": ("sponsor", "Sponsor talk", "Доклад спонсора"),
    "секция": ("section", "Section", "Секция"),
    "перерыв": ("break", "Coffee break", "Кофе-брейк"),
    "обед": ("lunch", "Lunch", "Обед"),
    "регистрация": ("registration", "Registration", "Регистрация"),
    "открытие": ("opening", "Opening", "Открытие"),
    "закрытие": ("closing", "Closing", "Закрытие"),
    "постеры": ("poster", "Poster session", "Постерная сессия"),
    "мероприятие": ("social", "Social event", "Мероприятие"),
}

TALK_STATUSES = {
    "": "ok",
    "отменён": "cancelled",
    "отменен": "cancelled",
    "перенесён": "moved",
    "перенесен": "moved",
}

# Spreadsheet stores a short campus code; build.py expands it for the site.
# Hall numbers stay in Russian (ц/л) because that is what is on the signs.
# `144ц` is a retired alias of `библиотека` so leftover cells never print the old tag.
LIBRARY_ROOM = {"ru": "Читальный зал библиотеки", "en": "Library reading hall"}
ROOM_LABELS = {
    "235ц": {"ru": "235ц, Актовый зал", "en": "235ц, Assembly Hall"},
    "библиотека": LIBRARY_ROOM,
    "144ц": LIBRARY_ROOM,
    "117л": {"ru": "117л, Интеллектуальный центр", "en": "117л, Intellectual Center"},
    "315л": {"ru": "315л", "en": "315л"},
    "вестибюль": {"ru": "Вестибюль, 1 эт.", "en": "Central lobby, 1st floor"},
    "холл2": {"ru": "Коридор и холл 2-го этажа", "en": "Hallway, 2nd floor"},
    "причал": {"ru": "4-й причал, Речной вокзал", "en": "Pier 4, River Terminal"},
    "интурист": {"ru": "Ресторан «Интурист», Амурский бульвар, 2", "en": "Restaurant Inturist, Amursky Boulevard, 2"},
}

PLENARY_SECTION = "P"

DEFAULT_DURATION = {
    "plenary": 30,
    "jubilee": 30,
    "sponsor": 15,
    "section": 15,
}

# --------------------------------------------------------------------------- helpers


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
        minutes = int(round(float(value) * 24 * 60)) % (24 * 60)
        return dt.time(minutes // 60, minutes % 60)
    m = _TIME_RE.match(str(value))
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        if 0 <= h < 24 and 0 <= mi < 60:
            return dt.time(h, mi)
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


def expand_room(value) -> dict | str:
    """Turn a campus code (or already-expanded label) into a bilingual room dict.

    Empty cells stay ``""``. Unknown text is used as-is for both languages.
    """
    text = clean(value)
    if not text:
        return ""
    for code, labels in ROOM_LABELS.items():
        if text == code or text.startswith(code):
            return {"ru": labels["ru"], "en": labels["en"]}
    return {"ru": text, "en": text}


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
            r"const CACHE = 'nucleus2026-[^']+';",
            f"const CACHE = 'nucleus2026-{sw_tag}';",
            sw,
            count=1,
        )
        if n:
            sw_path.write_text(sw, encoding="utf-8", newline="\n")
    return tags
