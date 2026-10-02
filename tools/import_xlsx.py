# -*- coding: utf-8 -*-
"""One-time import of data/programme.xlsx into data/*.json.

The workbook is not a live source. This script merges people and organizations,
matches chair lines to people, and writes data/import-report.md. Contribution
ids and block ids are copied, not invented: talks keep S1-08 / P-12 / POST-05,
and blocks stay B001–B084 in sheet order.

    python tools/import_xlsx.py
    python tools/import_xlsx.py --xlsx data/programme.xlsx --data data/
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA_DIR, ROOT, clean, fmt_time, parse_date, parse_time, utf8_stdout  # noqa: E402
from dataio import write_data  # noqa: E402

utf8_stdout()

SHEET_SETTINGS = "Настройки"
SHEET_SECTIONS = "Секции"
SHEET_BLOCKS = "Блоки"
SHEET_TALKS = "Доклады"
SHEET_POSTERS = "Постеры"
SHEET_CHANGES = "Изменения"

BLOCK_TYPES = {
    "пленарный": "plenary",
    "юбилейный": "jubilee",
    "спонсор": "sponsor",
    "секция": "section",
    "перерыв": "break",
    "обед": "lunch",
    "регистрация": "registration",
    "открытие": "opening",
    "закрытие": "closing",
    "постеры": "poster",
    "мероприятие": "social",
}

TALK_STATUSES = {
    "": "ok",
    "отменён": "cancelled",
    "отменен": "cancelled",
    "перенесён": "moved",
    "перенесен": "moved",
}

DEFAULT_DURATION = {"plenary": 30, "jubilee": 30, "sponsor": 15, "section": 15}

SESSION_TYPE_LABELS = {
    "plenary": {"ru": "Пленарный доклад", "en": "Plenary talk"},
    "jubilee": {"ru": "Юбилейный доклад", "en": "Anniversary talk"},
    "sponsor": {"ru": "Доклад спонсора", "en": "Sponsor talk"},
    "section": {"ru": "Секция", "en": "Section"},
    "break": {"ru": "Кофе-брейк", "en": "Coffee break"},
    "lunch": {"ru": "Обед", "en": "Lunch"},
    "registration": {"ru": "Регистрация", "en": "Registration"},
    "opening": {"ru": "Открытие", "en": "Opening"},
    "closing": {"ru": "Закрытие", "en": "Closing"},
    "poster": {"ru": "Постерная сессия", "en": "Poster session"},
    "social": {"ru": "Мероприятие", "en": "Social event"},
}

# Campus codes from the workbook. The site shows `label`, not the code.
# 144ц is a retired alias of the library and is not its own room.
LIBRARY_LABEL = {"ru": "Читальный зал библиотеки", "en": "Library reading hall"}
ROOM_TABLE = [
    ("235ц", {"ru": "235ц, Актовый зал", "en": "235ц, Assembly Hall"}, []),
    ("библиотека", LIBRARY_LABEL, ["144ц"]),
    ("117л", {"ru": "117л, Интеллектуальный центр", "en": "117л, Intellectual Center"}, []),
    ("315л", {"ru": "315л", "en": "315л"}, []),
    ("вестибюль", {"ru": "Вестибюль, 1 эт.", "en": "Central lobby, 1st floor"}, []),
    ("холл2", {"ru": "Коридор и холл 2-го этажа", "en": "Hallway, 2nd floor"}, []),
    ("причал", {"ru": "4-й причал, Речной вокзал", "en": "Pier 4, River Terminal"}, []),
    ("интурист", {"ru": "Ресторан «Интурист», Амурский бульвар, 2", "en": "Restaurant Inturist, Amursky Boulevard, 2"}, []),
]
ROOM_ALIAS = {"144ц": "библиотека"}

PLENARY_SECTION = "P"
_INITIAL = re.compile(r"^([A-Za-zА-Яа-яЁё])\.?$")


def norm_number(value) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return clean(value)


def as_date(value) -> str:
    parsed = parse_date(value)
    if parsed is None and clean(value):
        return ""
    return "" if parsed is None else parsed.isoformat()


def as_time(value) -> str:
    parsed = parse_time(value)
    return "" if parsed is None else fmt_time(parsed)


def read_table(wb, sheet: str, columns: list[str], errors: list[str]) -> list[dict]:
    if sheet not in wb.sheetnames:
        errors.append(f"Лист «{sheet}» не найден")
        return []
    rows = list(wb[sheet].iter_rows(values_only=True))
    if not rows:
        return []
    header = [clean(cell) for cell in rows[0]]
    index = {name: header.index(name) for name in columns if name in header}
    for name in columns:
        if name not in index:
            errors.append(f"Лист «{sheet}»: нет столбца «{name}»")
    out: list[dict] = []
    for row_number, row in enumerate(rows[1:], start=2):
        if row is None or all(cell is None or clean(cell) == "" for cell in row):
            continue
        rec = {"_row": row_number}
        for name in columns:
            i = index.get(name)
            rec[name] = row[i] if i is not None and i < len(row) else None
        out.append(rec)
    return out


def parse_talk_spec(spec: str) -> list[str]:
    spec = clean(spec)
    if not spec:
        return []
    out: list[str] = []
    for part in re.split(r"\s*[,;]\s*", spec):
        match = re.fullmatch(r"(\d+)\s*[-–—]\s*(\d+)", part)
        if match:
            start, end = int(match.group(1)), int(match.group(2))
            if end < start:
                start, end = end, start
            out.extend(str(n) for n in range(start, end + 1))
        elif part:
            out.append(part)
    return out


def person_key(family: str, given: str, patronymic: str) -> tuple[str, str, str]:
    return (family.casefold(), given.casefold(), patronymic.casefold())


def person_name(person: dict) -> str:
    parts = [person.get("family") or "", person.get("given") or ""]
    if person.get("patronymic"):
        parts.append(person["patronymic"])
    return " ".join(part for part in parts if part)


def parse_chair(text: str) -> tuple[str, list[str]]:
    """Return (surname, initials) from 'Д. Д. Тенамсов' or 'Тенамсов Д. Д.'."""
    surname: list[str] = []
    initials: list[str] = []
    for token in text.split():
        match = _INITIAL.match(token)
        if match:
            initials.append(match.group(1))
        else:
            surname.append(token)
    return " ".join(surname), initials


def initials_match(initials: list[str], person: dict) -> bool:
    given = person.get("given") or ""
    patronymic = person.get("patronymic") or ""
    if len(initials) == 1:
        return bool(given) and given[0].casefold() == initials[0].casefold()
    if len(initials) >= 2:
        return (
            bool(given)
            and bool(patronymic)
            and given[0].casefold() == initials[0].casefold()
            and patronymic[0].casefold() == initials[1].casefold()
        )
    return False


def room_id_for(code: str, rooms: list[dict], notes: list[str]) -> str:
    text = clean(code)
    if not text:
        return ""
    text = ROOM_ALIAS.get(text, text)
    known = {room["id"] for room in rooms}
    if text in known:
        return text
    # A longer cell that starts with a known code, matching the old expand_room.
    for room_id in sorted(known, key=len, reverse=True):
        if text == room_id or text.startswith(room_id):
            return room_id
    rooms.append({"id": text, "label": {"ru": text, "en": text}})
    notes.append(f"Unknown room code «{text}» stored with that text as both labels.")
    return text


def import_workbook(path: Path) -> tuple[dict, str]:
    errors: list[str] = []
    notes: list[str] = []
    wb = openpyxl.load_workbook(path, data_only=True)

    settings_rows = read_table(
        wb, SHEET_SETTINGS, ["Параметр", "Значение (RU)", "Значение (EN)", "Пояснение"], errors
    )
    raw_settings: dict[str, tuple[str, str]] = {}
    for rec in settings_rows:
        key = clean(rec["Параметр"])
        if key:
            raw_settings[key] = (clean(rec["Значение (RU)"]), clean(rec["Значение (EN)"]))

    def setting(key: str) -> dict:
        ru, en = raw_settings.get(key, ("", ""))
        return {"ru": ru, "en": en}

    def setting_plain(key: str) -> str:
        return raw_settings.get(key, ("", ""))[0]

    date_start = as_date(raw_settings.get("Дата начала", ("", ""))[0]) or setting_plain("Дата начала")
    date_end = as_date(raw_settings.get("Дата окончания", ("", ""))[0]) or setting_plain("Дата окончания")
    conference = {
        "id": "nucleus-2026",
        "title": setting("Название"),
        "short_title": setting("Краткое название"),
        "date_start": date_start,
        "date_end": date_end,
        "city": setting("Город"),
        "venue": setting("Место проведения"),
        "timezone": setting_plain("Часовой пояс") or "Asia/Vladivostok",
        "website": setting_plain("Сайт"),
        "contact": setting_plain("Контакт оргкомитета"),
        "footnote": setting("Сноска"),
        "languages": ["ru", "en"],
        "defaults": {"duration_min": dict(DEFAULT_DURATION)},
        "session_types": SESSION_TYPE_LABELS,
    }
    # The sheet also has «Смещение UTC». It is not stored: the build derives it
    # from `timezone`. Record the sheet value so the report can show it.
    sheet_offset = setting_plain("Смещение UTC")

    tracks = []
    track_ids: set[str] = set()
    for rec in read_table(
        wb,
        SHEET_SECTIONS,
        [
            "№",
            "Краткое название (RU)",
            "Краткое название (EN)",
            "Полное название (RU)",
            "Полное название (EN)",
            "Председатель (RU)",
            "Председатель (EN)",
            "Цвет",
            "Аудитория",
        ],
        errors,
    ):
        sid = norm_number(rec["№"])
        if not sid:
            errors.append(f"Секции, строка {rec['_row']}: пустой №")
            continue
        if sid in track_ids:
            errors.append(f"Секции, строка {rec['_row']}: № «{sid}» повторяется")
        track_ids.add(sid)
        tracks.append({
            "id": sid,
            "short": {"ru": clean(rec["Краткое название (RU)"]), "en": clean(rec["Краткое название (EN)"])},
            "full": {"ru": clean(rec["Полное название (RU)"]), "en": clean(rec["Полное название (EN)"])},
            "color": clean(rec["Цвет"]) or "slate",
        })
    if PLENARY_SECTION not in track_ids:
        notes.append(f"Sections sheet has no «{PLENARY_SECTION}» row; a plenary track was added.")
        tracks.append({
            "id": PLENARY_SECTION,
            "short": {"ru": "Пленарные доклады", "en": "Plenary talks"},
            "full": {"ru": "Пленарные доклады", "en": "Plenary talks"},
            "color": "slate",
        })
        track_ids.add(PLENARY_SECTION)

    rooms = [{"id": room_id, "label": dict(label), "aliases": list(aliases)} for room_id, label, aliases in ROOM_TABLE]

    people: dict[tuple[str, str, str], dict] = {}
    email_conflicts: list[str] = []

    def intern_person(family: str, given: str, patronymic: str, email: str, contrib_id: str | None) -> tuple[str, str, str]:
        key = person_key(family, given, patronymic)
        rec = people.get(key)
        if rec is None:
            people[key] = {
                "family": family,
                "given": given,
                "patronymic": patronymic,
                "email": email,
                "contrib_ids": [contrib_id] if contrib_id else [],
                "created_as_chair": contrib_id is None,
            }
            return key
        if email and rec["email"] and email.casefold() != rec["email"].casefold():
            email_conflicts.append(
                f"{person_name(rec)}: {rec['email']} and {email}"
                + (f" ({contrib_id})" if contrib_id else "")
            )
        elif email and not rec["email"]:
            rec["email"] = email
        if contrib_id:
            rec["contrib_ids"].append(contrib_id)
            rec["created_as_chair"] = False
        return key

    affiliations: dict[str, dict] = {}
    sponsors: dict[tuple[str, str, str, str], dict] = {}

    def intern_affiliation(text: str) -> str | None:
        if not text:
            return None
        affiliations.setdefault(text, {"name": text})
        return text

    def intern_sponsor(ru: str, en: str, url: str, logo: str) -> tuple[str, str, str, str] | None:
        if not (ru or en or url or logo):
            return None
        key = (ru, en, url, logo)
        sponsors.setdefault(key, {"ru": ru, "en": en, "url": url, "logo": logo})
        return key

    raw_talks: list[dict] = []
    by_section_number: dict[tuple[str, str], str] = {}
    for rec in read_table(
        wb,
        SHEET_TALKS,
        [
            "ID", "Секция", "№", "Фамилия", "Имя", "Отчество", "Организация", "Email",
            "Название", "Длительность (мин)", "Начало", "Статус", "Тематика",
            "Примечание (RU)", "Примечание (EN)", "Сайт", "Логотип", "Спонсор (RU)", "Спонсор (EN)",
        ],
        errors,
    ):
        tid = clean(rec["ID"])
        if not tid:
            errors.append(f"Доклады, строка {rec['_row']}: пустой ID")
            continue
        sec = norm_number(rec["Секция"])
        num = norm_number(rec["№"])
        if sec not in track_ids:
            errors.append(f"Доклады, строка {rec['_row']} ({tid}): неизвестная секция «{sec}»")
        if not num:
            errors.append(f"Доклады, строка {rec['_row']} ({tid}): пустой №")
        slot = (sec, num)
        if slot in by_section_number:
            errors.append(
                f"Доклады, строка {rec['_row']} ({tid}): в секции {sec} № {num} уже занят докладом {by_section_number[slot]}"
            )
        by_section_number[slot] = tid
        status_raw = clean(rec["Статус"]).lower()
        if status_raw not in TALK_STATUSES:
            notes.append(f"{tid}: unknown status «{status_raw}» stored as ok.")
            status_raw = ""
        duration = rec["Длительность (мин)"]
        duration_min: int | None
        if duration in (None, ""):
            duration_min = None
        else:
            try:
                duration_min = int(duration)
            except (TypeError, ValueError):
                errors.append(f"Доклады, строка {rec['_row']} ({tid}): длительность «{duration}» не число")
                duration_min = None
        pin = as_time(rec["Начало"])
        if rec["Начало"] not in (None, "") and not pin:
            errors.append(f"Доклады, строка {rec['_row']} ({tid}): не удалось разобрать «Начало»")
        family, given, patronymic = clean(rec["Фамилия"]), clean(rec["Имя"]), clean(rec["Отчество"])
        email = clean(rec["Email"])
        key = intern_person(family, given, patronymic, email, tid)
        org = intern_affiliation(clean(rec["Организация"]))
        sponsor = intern_sponsor(
            clean(rec["Спонсор (RU)"]), clean(rec["Спонсор (EN)"]), clean(rec["Сайт"]), clean(rec["Логотип"])
        )
        topic = norm_number(rec["Тематика"])
        raw_talks.append({
            "id": tid,
            "format": "oral",
            "track_id": sec,
            "number": num,
            "title": clean(rec["Название"]),
            "person_key": key,
            "affiliation": org,
            "duration_min": duration_min,
            "start": pin,
            "status": TALK_STATUSES.get(status_raw, "ok"),
            "topic_id": topic,
            "note": {"ru": clean(rec["Примечание (RU)"]), "en": clean(rec["Примечание (EN)"])},
            "sponsor_key": sponsor,
            "session_id": "",
            "order": None,
        })

    raw_posters: list[dict] = []
    for rec in read_table(
        wb,
        SHEET_POSTERS,
        [
            "ID", "Фамилия", "Имя", "Отчество", "Организация", "Email", "Название",
            "Секция", "№ стенда", "Статус", "Примечание (RU)", "Примечание (EN)",
        ],
        errors,
    ):
        pid = clean(rec["ID"])
        if not pid:
            errors.append(f"Постеры, строка {rec['_row']}: пустой ID")
            continue
        if any(talk["id"] == pid for talk in raw_talks) or any(poster["id"] == pid for poster in raw_posters):
            errors.append(f"Постеры, строка {rec['_row']}: ID «{pid}» уже используется")
            continue
        sec = norm_number(rec["Секция"])
        if sec and sec not in track_ids:
            notes.append(f"{pid}: poster track «{sec}» is not a known track.")
        status_raw = clean(rec["Статус"]).lower()
        if status_raw not in TALK_STATUSES:
            notes.append(f"{pid}: unknown status «{status_raw}» stored as ok.")
            status_raw = ""
        family, given, patronymic = clean(rec["Фамилия"]), clean(rec["Имя"]), clean(rec["Отчество"])
        key = intern_person(family, given, patronymic, clean(rec["Email"]), pid)
        raw_posters.append({
            "id": pid,
            "format": "poster",
            "track_id": sec,
            "title": clean(rec["Название"]),
            "person_key": key,
            "affiliation": intern_affiliation(clean(rec["Организация"])),
            "status": TALK_STATUSES.get(status_raw, "ok"),
            "note": {"ru": clean(rec["Примечание (RU)"]), "en": clean(rec["Примечание (EN)"])},
            "board": norm_number(rec["№ стенда"]),
            "session_id": "",
            "order": None,
            "sponsor_key": None,
            "duration_min": None,
            "start": "",
            "topic_id": "",
            "number": "",
        })

    raw_blocks: list[dict] = []
    placed: dict[str, str] = {}
    talks_by_id = {talk["id"]: talk for talk in raw_talks}
    for index, rec in enumerate(
        read_table(
            wb,
            SHEET_BLOCKS,
            [
                "Дата", "Начало", "Конец", "Тип", "Название (RU)", "Название (EN)", "Секция",
                "Доклады", "Аудитория", "Председатель (RU)", "Председатель (EN)",
                "Примечание (RU)", "Примечание (EN)",
            ],
            errors,
        ),
        start=1,
    ):
        row = rec["_row"]
        date = as_date(rec["Дата"])
        start = as_time(rec["Начало"])
        end = as_time(rec["Конец"])
        type_ru = clean(rec["Тип"]).lower()
        if not date:
            errors.append(f"Блоки, строка {row}: не удалось разобрать дату «{rec['Дата']}»")
            continue
        if not start or not end:
            errors.append(f"Блоки, строка {row}: не удалось разобрать время «{rec['Начало']}»–«{rec['Конец']}»")
            continue
        if type_ru not in BLOCK_TYPES:
            errors.append(f"Блоки, строка {row}: неизвестный тип «{type_ru}»")
            continue
        btype = BLOCK_TYPES[type_ru]
        sec = norm_number(rec["Секция"])
        if btype in ("plenary", "jubilee", "sponsor") and not sec:
            sec = PLENARY_SECTION
        if btype == "section" and not sec:
            errors.append(f"Блоки, строка {row}: у блока типа «секция» не указана секция")
            continue
        if sec and sec not in track_ids:
            errors.append(f"Блоки, строка {row}: неизвестная секция «{sec}»")
            continue
        block_id = f"B{index:03d}"
        talk_ids: list[str] = []
        for num in parse_talk_spec(clean(rec["Доклады"])):
            tid = by_section_number.get((sec, num))
            if tid is None:
                errors.append(f"Блоки, строка {row}: в секции {sec} нет доклада № {num}")
                continue
            if tid in placed:
                errors.append(f"Блоки, строка {row}: доклад {tid} уже стоит в блоке {placed[tid]}")
                continue
            placed[tid] = block_id
            talk_ids.append(tid)
            talk = talks_by_id[tid]
            if talk["duration_min"] is None:
                talk["duration_min"] = DEFAULT_DURATION.get(btype, 15)
        raw_blocks.append({
            "id": block_id,
            "date": date,
            "start": start,
            "end": end,
            "type": btype,
            "title": {"ru": clean(rec["Название (RU)"]), "en": clean(rec["Название (EN)"])},
            "track_id": sec,
            "room_code": clean(rec["Аудитория"]),
            "chair_ru": clean(rec["Председатель (RU)"]),
            "chair_en": clean(rec["Председатель (EN)"]),
            "note": {"ru": clean(rec["Примечание (RU)"]), "en": clean(rec["Примечание (EN)"])},
            "talk_ids": talk_ids,
            "_row": row,
        })

    poster_blocks = [block for block in raw_blocks if block["type"] == "poster"]
    if len(poster_blocks) != 1:
        errors.append(f"Expected one poster session, found {len(poster_blocks)}")
    poster_session_id = poster_blocks[0]["id"] if len(poster_blocks) == 1 else ""
    if poster_session_id:
        for order, poster in enumerate(raw_posters, start=1):
            poster["session_id"] = poster_session_id
            poster["order"] = order
        poster_blocks[0]["talk_ids"] = [poster["id"] for poster in raw_posters]

    for block in raw_blocks:
        if block["type"] == "poster":
            continue
        for order, tid in enumerate(block["talk_ids"], start=1):
            talk = talks_by_id[tid]
            talk["session_id"] = block["id"]
            talk["order"] = order
            if talk["duration_min"] is None:
                talk["duration_min"] = DEFAULT_DURATION.get(block["type"], 15)

    # Chairs: match initials + surname to a person, otherwise create one.
    chair_report: list[dict] = []
    for block in raw_blocks:
        ru, en = block["chair_ru"], block["chair_en"]
        if not ru and not en:
            block["chairs"] = []
            continue
        surname, initials = parse_chair(ru or en)
        hits = []
        if surname:
            hits = [
                person
                for person in people.values()
                if person["family"].casefold() == surname.casefold() and initials_match(initials, person)
            ]
        if len(hits) > 1:
            names = ", ".join(person_name(person) for person in hits)
            errors.append(f"{block['id']}: chair «{ru}» matches more than one person ({names})")
            block["chairs"] = []
            continue
        if len(hits) == 1:
            person = hits[0]
            kind = "matched" if person["contrib_ids"] else "matched (chair record)"
        else:
            given = f"{initials[0]}." if initials else surname
            patronymic = f"{initials[1]}." if len(initials) > 1 else ""
            key = intern_person(surname or ru, given, patronymic, "", None)
            person = people[key]
            person["created_as_chair"] = True
            kind = "created"
        block["chairs"] = [{
            "person_key": person_key(person["family"], person["given"], person["patronymic"]),
            "label": {"ru": ru, "en": en or ru},
        }]
        chair_report.append({
            "session_id": block["id"],
            "ru": ru,
            "en": en,
            "kind": kind,
            "person_key": person_key(person["family"], person["given"], person["patronymic"]),
        })

    if errors:
        raise SystemExit("Импорт остановлен:\n" + "\n".join(f"ОШИБКА: {msg}" for msg in errors))

    ordered_people = sorted(
        people.values(),
        key=lambda person: (
            person["family"].casefold(),
            person["given"].casefold(),
            (person.get("patronymic") or "").casefold(),
            (person.get("email") or "").casefold(),
        ),
    )
    key_to_id: dict[tuple[str, str, str], str] = {}
    people_out: list[dict] = []
    for index, person in enumerate(ordered_people, start=1):
        pid = f"PER-{index:04d}"
        key = person_key(person["family"], person["given"], person["patronymic"])
        key_to_id[key] = pid
        person["id"] = pid
        people_out.append({
            "id": pid,
            "family": person["family"],
            "given": person["given"],
            "patronymic": person["patronymic"],
            "email": person["email"],
        })

    org_rows: list[dict] = []
    for text in affiliations:
        org_rows.append({"name": text, "url": "", "logo": "", "_sort": text.casefold(), "_aff": text})
    for key, sponsor in sponsors.items():
        label = sponsor["ru"] or sponsor["en"]
        org_rows.append({
            "name": {"ru": sponsor["ru"], "en": sponsor["en"]},
            "url": sponsor["url"],
            "logo": sponsor["logo"],
            "_sort": label.casefold(),
            "_sponsor": key,
        })
    org_rows.sort(key=lambda org: org["_sort"])
    affil_ids: dict[str, str] = {}
    sponsor_ids: dict[tuple[str, str, str, str], str] = {}
    orgs_out: list[dict] = []
    for index, org in enumerate(org_rows, start=1):
        oid = f"ORG-{index:03d}"
        org["id"] = oid
        orgs_out.append({"id": oid, "name": org["name"], "url": org["url"], "logo": org["logo"]})
        if "_aff" in org:
            affil_ids[org["_aff"]] = oid
        if "_sponsor" in org:
            sponsor_ids[org["_sponsor"]] = oid

    def author_for(raw: dict) -> dict:
        return {
            "person_id": key_to_id[raw["person_key"]],
            "affiliation_ids": [affil_ids[raw["affiliation"]]] if raw.get("affiliation") else [],
            "presenting": True,
        }

    contributions: list[dict] = []
    for raw in raw_talks + raw_posters:
        rec = {
            "id": raw["id"],
            "format": raw["format"],
            "track_id": raw.get("track_id") or "",
            "session_id": raw.get("session_id") or "",
            "order": raw.get("order"),
            "number": raw.get("number") or "",
            "title": raw["title"],
            "authors": [author_for(raw)],
            "duration_min": raw.get("duration_min"),
            "start": raw.get("start") or "",
            "status": raw.get("status") or "ok",
            "topic_id": raw.get("topic_id") or "",
            "note": raw.get("note") or {},
            "board": raw.get("board") or "",
        }
        if raw.get("sponsor_key"):
            rec["sponsor_id"] = sponsor_ids[raw["sponsor_key"]]
        contributions.append(rec)

    sessions: list[dict] = []
    for block in raw_blocks:
        chairs = []
        for chair in block.get("chairs") or []:
            chairs.append({
                "person_id": key_to_id[chair["person_key"]],
                "label": chair["label"],
            })
        sessions.append({
            "id": block["id"],
            "date": block["date"],
            "start": block["start"],
            "end": block["end"],
            "type": block["type"],
            "title": block["title"],
            "track_id": block["track_id"],
            "room_id": room_id_for(block["room_code"], rooms, notes),
            "chairs": chairs,
            "contribution_ids": list(block["talk_ids"]),
            "note": block["note"],
        })

    changes = []
    raw_changes = []
    for rec in read_table(wb, SHEET_CHANGES, ["Дата/время", "Текст (RU)", "Текст (EN)"], errors):
        when = rec["Дата/время"]
        if isinstance(when, dt.datetime):
            stamp = when.strftime("%Y-%m-%dT%H:%M")
        elif isinstance(when, dt.date):
            stamp = when.isoformat()
        else:
            stamp = clean(when)
        text = {"ru": clean(rec["Текст (RU)"]), "en": clean(rec["Текст (EN)"])}
        if text["ru"] or text["en"]:
            raw_changes.append({"at": stamp, "text": text})
    raw_changes.sort(key=lambda change: change["at"])
    for index, change in enumerate(raw_changes, start=1):
        changes.append({"id": f"CHG-{index:03d}", "at": change["at"], "text": change["text"]})

    if errors:
        raise SystemExit("Импорт остановлен:\n" + "\n".join(f"ОШИБКА: {msg}" for msg in errors))

    data = {
        "conference": conference,
        "tracks": tracks,
        "rooms": rooms,
        "sessions": sessions,
        "contributions": contributions,
        "people": people_out,
        "organizations": orgs_out,
        "resources": [],
        "changes": changes,
    }
    try:
        source_label = path.resolve().relative_to(ROOT)
    except ValueError:
        source_label = path
    report = render_report(
        source_label,
        data,
        people,
        chair_report,
        key_to_id,
        email_conflicts,
        notes,
        sheet_offset,
    )
    return data, report


def render_report(
    source: Path,
    data: dict,
    people: dict,
    chair_report: list[dict],
    key_to_id: dict,
    email_conflicts: list[str],
    notes: list[str],
    sheet_offset: str,
) -> str:
    orals = [item for item in data["contributions"] if item["format"] == "oral"]
    posters = [item for item in data["contributions"] if item["format"] == "poster"]
    created = [person for person in people.values() if person.get("created_as_chair") and not person["contrib_ids"]]
    multi = [person for person in people.values() if len(person["contrib_ids"]) > 1]
    lines = [
        "# Import report",
        "",
        f"Converted `{source.as_posix()}` into `data/*.json`.",
        "Contribution ids and session ids were copied. Clock times were not edited.",
        f"The sheet’s UTC offset was `{sheet_offset or '—'}` and was not stored; the build derives it from `{data['conference']['timezone']}`.",
        "",
        "## Counts",
        "",
        f"- Tracks: {len(data['tracks'])}",
        f"- Rooms: {len(data['rooms'])}",
        f"- Sessions: {len(data['sessions'])}",
        f"- Contributions: {len(data['contributions'])} ({len(orals)} oral, {len(posters)} poster)",
        f"- People: {len(data['people'])} ({len(created)} created from an unmatched chair line)",
        f"- Organizations: {len(data['organizations'])}",
        f"- Changes: {len(data['changes'])}",
        f"- Resources: {len(data['resources'])}",
        "",
        "## Chair matches",
        "",
        "Each row is one sitting. `matched` means the surname and initials found an author. `created` means no author had that surname and initials, so a person was added (given name and patronymic are the initials). `matched (chair record)` is a later sitting that uses a person created earlier in this import.",
        "",
        "| Session | Chair (RU) | Chair (EN) | Result | Person | Stored name |",
        "|---|---|---|---|---|---|",
    ]
    for row in chair_report:
        person = people[row["person_key"]]
        lines.append(
            "| {session} | {ru} | {en} | {kind} | {pid} | {name} |".format(
                session=row["session_id"],
                ru=row["ru"].replace("|", "\\|"),
                en=(row["en"] or "").replace("|", "\\|"),
                kind=row["kind"],
                pid=key_to_id[row["person_key"]],
                name=person_name(person).replace("|", "\\|"),
            )
        )
    lines += ["", "## People created for chairs", ""]
    if not created:
        lines.append("None.")
    else:
        for person in sorted(created, key=lambda item: item["id"]):
            labels = sorted({
                (row["ru"], row["en"])
                for row in chair_report
                if row["person_key"] == person_key(person["family"], person["given"], person["patronymic"])
            })
            shown = "; ".join(f"{ru} / {en}" for ru, en in labels)
            lines.append(f"- `{person['id']}` {person_name(person)} — {shown}")
    lines += ["", "## People with more than one contribution", ""]
    if not multi:
        lines.append("None.")
    else:
        for person in sorted(multi, key=lambda item: item["id"]):
            ids = ", ".join(person["contrib_ids"])
            lines.append(f"- `{person['id']}` {person_name(person)}: {ids}")
    lines += ["", "## Organizations", ""]
    for org in data["organizations"]:
        name = org["name"]
        if isinstance(name, dict):
            shown = f"{name.get('ru', '')} / {name.get('en', '')}"
        else:
            shown = name
        extra = ""
        if org.get("url") or org.get("logo"):
            extra = f" — {org.get('url', '')} {org.get('logo', '')}".rstrip()
        lines.append(f"- `{org['id']}` {shown}{extra}")
    if email_conflicts:
        lines += ["", "## Email conflicts (same name, different email)", ""]
        lines.extend(f"- {item}" for item in email_conflicts)
    if notes:
        lines += ["", "## Notes", ""]
        lines.extend(f"- {item}" for item in notes)
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Convert programme.xlsx into data/*.json.")
    parser.add_argument("--xlsx", type=Path, default=DATA_DIR / "programme.xlsx")
    parser.add_argument("--data", type=Path, default=DATA_DIR)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)
    if not args.xlsx.is_file():
        print(f"Не найден {args.xlsx}")
        return 1
    data, report = import_workbook(args.xlsx)
    write_data(data, args.data)
    report_path = args.report or (args.data / "import-report.md")
    report_path.write_text(report, encoding="utf-8", newline="\n")
    print(f"Записано: {args.data}")
    print(f"Отчёт: {report_path}")
    print(
        f"Секций-треков: {len(data['tracks'])}, залов: {len(data['rooms'])}, "
        f"сессий: {len(data['sessions'])}, вкладов: {len(data['contributions'])}, "
        f"людей: {len(data['people'])}, организаций: {len(data['organizations'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
