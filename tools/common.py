# -*- coding: utf-8 -*-
"""Shared constants for the ЯДРО-2026 programme tools (migrate.py / build.py).

The normalized workbook ``data/programme.xlsx`` is the single source of truth.
Everything here describes its layout so that both scripts agree on it.
"""
from __future__ import annotations

import datetime as dt
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
    "Примечание (RU)",
    "Примечание (EN)",
]

COLS_TALKS = [
    "ID",
    "Секция",
    "№",
    "Фамилия",
    "Имя",
    "Организация",
    "Название",
    "Длительность (мин)",
    "Начало",
    "Статус",
    "Тематика",
    "Примечание (RU)",
    "Примечание (EN)",
]

COLS_POSTERS = [
    "ID",
    "Фамилия",
    "Имя",
    "Организация",
    "Название",
    "Секция",
    "№ стенда",
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

PLENARY_SECTION = "P"

DEFAULT_DURATION = {
    "plenary": 30,
    "jubilee": 20,
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


def fmt_time(t: dt.time | None) -> str:
    return "" if t is None else f"{t.hour:02d}:{t.minute:02d}"


def minutes(t: dt.time) -> int:
    return t.hour * 60 + t.minute


def from_minutes(m: int) -> dt.time:
    m %= 24 * 60
    return dt.time(m // 60, m % 60)
