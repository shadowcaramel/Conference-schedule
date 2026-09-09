# -*- coding: utf-8 -*-
"""Build the programme website from data/programme.xlsx.

Usage:
    python tools/build.py            # validate, write site/data.js and dist/<single-file>.html
    python tools/build.py --check    # validate only, write nothing

Exit code 1 on validation errors (nothing is written), 0 otherwise. Warnings never block.
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    BLOCK_TYPES,
    COLS_BLOCKS,
    COLS_CHANGES,
    COLS_POSTERS,
    COLS_SECTIONS,
    COLS_SETTINGS,
    COLS_TALKS,
    DATA_DIR,
    DEFAULT_DURATION,
    DIST_DIR,
    PLENARY_SECTION,
    PROGRAMME_XLSX,
    SHEET_BLOCKS,
    SHEET_CHANGES,
    SHEET_POSTERS,
    SHEET_SECTIONS,
    SHEET_SETTINGS,
    SHEET_TALKS,
    SITE_DIR,
    TALK_STATUSES,
    clean,
    fmt_time,
    from_minutes,
    minutes,
    parse_date,
    parse_time,
    utf8_stdout,
)

utf8_stdout()

SINGLE_FILE_NAME = "nucleus2026-programme.html"

# --------------------------------------------------------------------------- diagnostics


class Diag:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


diag = Diag()

# --------------------------------------------------------------------------- reading


def read_table(wb, sheet: str, expected_cols: list[str]) -> list[dict]:
    """Read a header+rows sheet into dicts keyed by the expected column names.

    Columns are matched by header text, so the editor may reorder or add columns.
    """
    if sheet not in wb.sheetnames:
        diag.error(f"Лист «{sheet}» не найден в книге")
        return []
    ws = wb[sheet]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    header = [clean(h) for h in rows[0]]
    index: dict[str, int] = {}
    for col in expected_cols:
        if col in header:
            index[col] = header.index(col)
        else:
            diag.warn(f"Лист «{sheet}»: нет столбца «{col}» — считается пустым")
    out: list[dict] = []
    for r, row in enumerate(rows[1:], start=2):
        if row is None or all(v is None or clean(v) == "" for v in row):
            continue
        rec = {"_row": r}
        for col in expected_cols:
            i = index.get(col)
            rec[col] = row[i] if i is not None and i < len(row) else None
        out.append(rec)
    return out


def bilingual(ru, en) -> dict:
    ru, en = clean(ru), clean(en)
    return {"ru": ru or en, "en": en or ru}


def parse_talk_spec(spec: str) -> list[str]:
    """'8-14' -> ['8'..'14']; '1,3,5' -> ['1','3','5']; '12' -> ['12']; 'Ю1' -> ['Ю1']."""
    spec = clean(spec)
    if not spec:
        return []
    out: list[str] = []
    for part in re.split(r"\s*[,;]\s*", spec):
        m = re.fullmatch(r"(\d+)\s*[-–—]\s*(\d+)", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if b < a:
                a, b = b, a
            out.extend(str(n) for n in range(a, b + 1))
        elif part:
            out.append(part)
    return out


def norm_number(value) -> str:
    """Talk numbers may be int, float or text ('Ю1')."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return clean(value)


# --------------------------------------------------------------------------- assemble


def build_model(wb) -> dict:
    # ---- settings
    settings_rows = read_table(wb, SHEET_SETTINGS, COLS_SETTINGS)
    raw_settings: dict[str, tuple[str, str]] = {}
    for rec in settings_rows:
        key = clean(rec["Параметр"])
        if key:
            raw_settings[key] = (clean(rec["Значение (RU)"]), clean(rec["Значение (EN)"]))

    def setting(key: str) -> dict:
        ru, en = raw_settings.get(key, ("", ""))
        return bilingual(ru, en)

    def setting_plain(key: str) -> str:
        return raw_settings.get(key, ("", ""))[0]

    settings = {
        "title": setting("Название"),
        "shortTitle": setting("Краткое название"),
        "dateStart": setting_plain("Дата начала"),
        "dateEnd": setting_plain("Дата окончания"),
        "city": setting("Город"),
        "venue": setting("Место проведения"),
        "timezone": setting_plain("Часовой пояс") or "Asia/Vladivostok",
        "utcOffset": setting_plain("Смещение UTC") or "+10:00",
        "website": setting_plain("Сайт"),
        "contact": setting_plain("Контакт оргкомитета"),
        "footnote": setting("Сноска"),
    }
    if not re.fullmatch(r"[+-]\d{2}:\d{2}", settings["utcOffset"]):
        diag.error(f"Настройки: «Смещение UTC» должно быть вида +10:00, сейчас «{settings['utcOffset']}»")

    # ---- sections
    sections: list[dict] = []
    section_ids: set[str] = set()
    for rec in read_table(wb, SHEET_SECTIONS, COLS_SECTIONS):
        sid = norm_number(rec["№"])
        if not sid:
            diag.error(f"Секции, строка {rec['_row']}: пустой №")
            continue
        if sid in section_ids:
            diag.error(f"Секции, строка {rec['_row']}: № «{sid}» повторяется")
        section_ids.add(sid)
        sections.append({
            "id": sid,
            "short": bilingual(rec["Краткое название (RU)"], rec["Краткое название (EN)"]),
            "full": bilingual(rec["Полное название (RU)"], rec["Полное название (EN)"]),
            "chair": bilingual(rec["Председатель (RU)"], rec["Председатель (EN)"]),
            "color": clean(rec["Цвет"]) or "slate",
            "room": clean(rec["Аудитория"]),
        })
        if not clean(rec["Краткое название (EN)"]):
            diag.warn(f"Секции: у секции {sid} нет английского краткого названия")
    if PLENARY_SECTION not in section_ids:
        diag.warn(f"Секции: нет строки «{PLENARY_SECTION}» для пленарных докладов — добавлена автоматически")
        sections.append({"id": PLENARY_SECTION, "short": {"ru": "Пленарные доклады", "en": "Plenary talks"},
                         "full": {"ru": "Пленарные доклады", "en": "Plenary talks"},
                         "chair": {"ru": "", "en": ""}, "color": "slate", "room": ""})
        section_ids.add(PLENARY_SECTION)

    # ---- talks
    talks: dict[str, dict] = {}
    by_section_number: dict[tuple[str, str], str] = {}
    for rec in read_table(wb, SHEET_TALKS, COLS_TALKS):
        tid = clean(rec["ID"])
        row = rec["_row"]
        if not tid:
            diag.error(f"Доклады, строка {row}: пустой ID (ID обязателен и не должен меняться)")
            continue
        if tid in talks:
            diag.error(f"Доклады, строка {row}: ID «{tid}» уже используется")
            continue
        sec = norm_number(rec["Секция"])
        num = norm_number(rec["№"])
        if sec not in section_ids:
            diag.error(f"Доклады, строка {row} ({tid}): неизвестная секция «{sec}»")
        if not num:
            diag.error(f"Доклады, строка {row} ({tid}): пустой №")
        key = (sec, num)
        if key in by_section_number:
            diag.error(f"Доклады, строка {row} ({tid}): в секции {sec} № {num} уже занят докладом {by_section_number[key]}")
        by_section_number[key] = tid
        title = clean(rec["Название"])
        if not title:
            diag.warn(f"Доклады, строка {row} ({tid}): пустое название")
        status_raw = clean(rec["Статус"]).lower()
        if status_raw not in TALK_STATUSES:
            diag.warn(f"Доклады, строка {row} ({tid}): неизвестный статус «{status_raw}» — игнорируется")
        duration = rec["Длительность (мин)"]
        try:
            duration = int(duration) if duration not in (None, "") else None
        except (TypeError, ValueError):
            diag.error(f"Доклады, строка {row} ({tid}): длительность «{duration}» не число")
            duration = None
        start_override = parse_time(rec["Начало"])
        if rec["Начало"] not in (None, "") and start_override is None:
            diag.error(f"Доклады, строка {row} ({tid}): не удалось разобрать «Начало» = «{rec['Начало']}»")
        topic = norm_number(rec["Тематика"])
        if topic and topic not in section_ids:
            diag.warn(f"Доклады, строка {row} ({tid}): тематика «{topic}» не соответствует ни одной секции")
        talks[tid] = {
            "id": tid, "section": sec, "number": num, "last": clean(rec["Фамилия"]),
            "first": clean(rec["Имя"]), "org": clean(rec["Организация"]), "email": clean(rec["Email"]),
            "title": title,
            "duration": duration, "startOverride": start_override,
            "status": TALK_STATUSES.get(status_raw, "ok"), "topic": topic,
            "note": bilingual(rec["Примечание (RU)"], rec["Примечание (EN)"]),
            # filled when placed
            "date": None, "start": None, "end": None, "blockId": None,
        }

    # duplicate speaker+title
    seen: dict[tuple[str, str], str] = {}
    for t in talks.values():
        k = (t["last"].lower(), t["title"].lower())
        if k in seen and t["title"]:
            diag.warn(f"Доклад «{t['title'][:50]}…» ({t['last']}) встречается дважды: {seen[k]} и {t['id']}")
        seen.setdefault(k, t["id"])

    # ---- blocks
    blocks: list[dict] = []
    placed: dict[str, str] = {}
    for i, rec in enumerate(read_table(wb, SHEET_BLOCKS, COLS_BLOCKS), start=1):
        row = rec["_row"]
        date = parse_date(rec["Дата"])
        start = parse_time(rec["Начало"])
        end = parse_time(rec["Конец"])
        btype_ru = clean(rec["Тип"]).lower()
        if date is None:
            diag.error(f"Блоки, строка {row}: не удалось разобрать дату «{rec['Дата']}»")
            continue
        if start is None or end is None:
            diag.error(f"Блоки, строка {row}: не удалось разобрать время «{rec['Начало']}»–«{rec['Конец']}»")
            continue
        if minutes(end) <= minutes(start):
            diag.error(f"Блоки, строка {row}: конец {fmt_time(end)} не позже начала {fmt_time(start)}")
            continue
        if btype_ru not in BLOCK_TYPES:
            diag.error(f"Блоки, строка {row}: неизвестный тип «{btype_ru}». Допустимо: {', '.join(BLOCK_TYPES)}")
            continue
        btype, en_default, ru_default = BLOCK_TYPES[btype_ru]
        sec = norm_number(rec["Секция"])
        if btype in ("plenary", "jubilee", "sponsor") and not sec:
            sec = PLENARY_SECTION
        if btype == "section" and not sec:
            diag.error(f"Блоки, строка {row}: у блока типа «секция» не указана секция")
            continue
        if sec and sec not in section_ids:
            diag.error(f"Блоки, строка {row}: неизвестная секция «{sec}»")
            continue
        block_id = f"B{i:03d}"
        talk_numbers = parse_talk_spec(rec["Доклады"])
        talk_ids: list[str] = []
        for num in talk_numbers:
            tid = by_section_number.get((sec, num))
            if tid is None:
                diag.error(f"Блоки, строка {row}: в секции {sec} нет доклада № {num}")
                continue
            if tid in placed:
                diag.error(f"Блоки, строка {row}: доклад {tid} уже стоит в блоке {placed[tid]}")
                continue
            placed[tid] = block_id
            talk_ids.append(tid)
        if btype in ("plenary", "jubilee", "sponsor", "section") and not talk_ids:
            diag.warn(f"Блоки, строка {row}: блок {date:%d.%m} {fmt_time(start)} типа «{btype_ru}» без докладов")
        room = clean(rec["Аудитория"])
        if not room and sec:
            room = next((s["room"] for s in sections if s["id"] == sec), "")
        title = bilingual(rec["Название (RU)"], rec["Название (EN)"])
        if not title["ru"]:
            if btype == "section":
                title = {"ru": "", "en": ""}  # derived from the section on the client
            else:
                title = {"ru": ru_default, "en": en_default}
        block = {
            "id": block_id, "date": date.isoformat(), "start": fmt_time(start), "end": fmt_time(end),
            "type": btype, "title": title, "section": sec, "talks": talk_ids, "room": room,
            "note": bilingual(rec["Примечание (RU)"], rec["Примечание (EN)"]),
        }
        blocks.append(block)

        # compute per-talk times
        cursor = minutes(start)
        total = 0
        for tid in talk_ids:
            t = talks[tid]
            dur = t["duration"] or DEFAULT_DURATION.get(btype, 15)
            t["duration"] = dur
            if t["startOverride"] is not None:
                cursor = minutes(t["startOverride"])
            t["date"] = date.isoformat()
            t["start"] = fmt_time(from_minutes(cursor))
            t["end"] = fmt_time(from_minutes(cursor + dur))
            t["blockId"] = block_id
            cursor += dur
            total += dur
        if talk_ids and cursor > minutes(end):
            diag.warn(f"Блоки, строка {row}: доклады блока {date:%d.%m} {fmt_time(start)}–{fmt_time(end)} "
                      f"(секция {sec}) заканчиваются в {fmt_time(from_minutes(cursor))}, позже конца блока")

    blocks.sort(key=lambda b: (b["date"], b["start"], b["type"] != "section", b["section"].zfill(2)))

    # overlaps: same section same time, same room same time
    for a_i, a in enumerate(blocks):
        for b in blocks[a_i + 1:]:
            if a["date"] != b["date"]:
                continue
            overlap = a["start"] < b["end"] and b["start"] < a["end"]
            if not overlap:
                continue
            if a["section"] and a["section"] == b["section"] and a["type"] == b["type"] == "section":
                diag.warn(f"Секция {a['section']} {a['date']}: блоки {a['start']}–{a['end']} и {b['start']}–{b['end']} пересекаются")
            if a["room"] and a["room"] == b["room"]:
                diag.warn(f"Аудитория «{a['room']}» {a['date']}: блоки {a['start']}–{a['end']} и {b['start']}–{b['end']} пересекаются")

    for t in talks.values():
        if t["blockId"] is None:
            diag.warn(f"Доклад {t['id']} ({t['last']}: «{t['title'][:40]}…») не поставлен ни в один блок — на сайте виден только в поиске")
        t.pop("startOverride", None)

    # ---- posters
    posters: list[dict] = []
    poster_ids: set[str] = set()
    for rec in read_table(wb, SHEET_POSTERS, COLS_POSTERS):
        pid = clean(rec["ID"])
        if not pid:
            diag.error(f"Постеры, строка {rec['_row']}: пустой ID")
            continue
        if pid in poster_ids or pid in talks:
            diag.error(f"Постеры, строка {rec['_row']}: ID «{pid}» уже используется")
            continue
        poster_ids.add(pid)
        sec = norm_number(rec["Секция"])
        if sec and sec not in section_ids:
            diag.warn(f"Постеры, строка {rec['_row']} ({pid}): неизвестная секция «{sec}»")
        posters.append({
            "id": pid, "last": clean(rec["Фамилия"]), "first": clean(rec["Имя"]), "org": clean(rec["Организация"]),
            "email": clean(rec["Email"]),
            "title": clean(rec["Название"]), "section": sec, "board": norm_number(rec["№ стенда"]),
            "note": bilingual(rec["Примечание (RU)"], rec["Примечание (EN)"]),
        })

    # ---- changes
    changes: list[dict] = []
    for rec in read_table(wb, SHEET_CHANGES, COLS_CHANGES):
        when = rec["Дата/время"]
        if isinstance(when, dt.datetime):
            stamp = when.strftime("%Y-%m-%dT%H:%M")
        elif isinstance(when, dt.date):
            stamp = when.isoformat()
        else:
            stamp = clean(when)
        text = bilingual(rec["Текст (RU)"], rec["Текст (EN)"])
        if text["ru"]:
            changes.append({"at": stamp, "text": text})
    changes.sort(key=lambda c: c["at"], reverse=True)

    # ---- days
    day_dates = sorted({b["date"] for b in blocks})
    days = [{"date": d, "blocks": [b["id"] for b in blocks if b["date"] == d]} for d in day_dates]

    counts = Counter(b["type"] for b in blocks)
    stats = {
        "sectionTalks": sum(1 for t in talks.values() if t["section"] != PLENARY_SECTION),
        "plenaryTalks": sum(1 for t in talks.values() if t["section"] == PLENARY_SECTION),
        "posters": len(posters),
        "blocks": len(blocks),
        "blockTypes": dict(counts),
    }

    return {
        "generatedAt": dt.datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "settings": settings,
        "sections": sections,
        "days": days,
        "blocks": blocks,
        "talks": talks,
        "posters": posters,
        "changes": changes,
        "stats": stats,
    }


# --------------------------------------------------------------------------- output


def write_data_js(model: dict) -> Path:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    path = SITE_DIR / "data.js"
    payload = json.dumps(model, ensure_ascii=False, separators=(",", ":"))
    # keep </script> from ever terminating the inline script in the single-file build
    payload = payload.replace("</", "<\\/")
    path.write_text("// Generated by tools/build.py — do not edit by hand.\n"
                    f"window.PROGRAMME = {payload};\n", encoding="utf-8")
    return path


def write_single_file(model: dict) -> Path | None:
    index = SITE_DIR / "index.html"
    if not index.exists():
        diag.warn("site/index.html пока нет — единый HTML-файл не собран")
        return None
    html = index.read_text(encoding="utf-8")

    def inline_css(match: re.Match) -> str:
        href = match.group(1)
        css_path = SITE_DIR / href
        if not css_path.exists():
            return match.group(0)
        css = css_path.read_text(encoding="utf-8")

        def font_to_data_uri(m: re.Match) -> str:
            rel = m.group(1).strip("'\"")
            fpath = (css_path.parent / rel).resolve()
            if not fpath.exists():
                return m.group(0)
            mime = "font/woff2" if fpath.suffix == ".woff2" else "font/woff"
            b64 = base64.b64encode(fpath.read_bytes()).decode("ascii")
            return f"url(data:{mime};base64,{b64})"

        css = re.sub(r"url\(([^)]+\.woff2?)\)", font_to_data_uri, css)
        return f"<style>\n{css}\n</style>"

    def inline_js(match: re.Match) -> str:
        src = match.group(1)
        js_path = SITE_DIR / src
        if not js_path.exists():
            return match.group(0)
        js = js_path.read_text(encoding="utf-8").replace("</script", "<\\/script")
        return f"<script>\n{js}\n</script>"

    html = re.sub(r'<link\s+rel="stylesheet"\s+href="([^"]+)"\s*/?>', inline_css, html)
    html = re.sub(r'<script\s+src="([^"]+)"\s*></script>', inline_js, html)
    # manifest / icons that only make sense when hosted as a folder
    html = re.sub(r'\s*<link\s+rel="manifest"[^>]*>', "", html)
    html = re.sub(r'\s*<link\s+rel="apple-touch-icon"[^>]*>', "", html)
    html = re.sub(r'\s*<link\s+rel="icon"[^>]*>', "", html)

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    out = DIST_DIR / SINGLE_FILE_NAME
    out.write_text(html, encoding="utf-8")
    return out


# --------------------------------------------------------------------------- main


def main(argv: list[str]) -> int:
    check_only = "--check" in argv
    src = PROGRAMME_XLSX
    alt = DATA_DIR / "_programme_update.xlsx"
    if alt.exists():
        try:
            import shutil
            shutil.copy2(alt, PROGRAMME_XLSX)
            alt.unlink()
            print(f"Применена отложенная правка книги → {PROGRAMME_XLSX}")
        except PermissionError:
            print("Файл programme.xlsx открыт в Excel — сборка идёт из data/_programme_update.xlsx "
                  "(закройте книгу и повторите, чтобы подменить оригинал).")
            src = alt
    if not src.exists():
        print(f"Не найден файл {PROGRAMME_XLSX}. Сначала выполните: python tools/migrate.py")
        return 1
    try:
        wb = openpyxl.load_workbook(src, data_only=True)
    except PermissionError:
        print("Файл programme.xlsx открыт в Excel и заблокирован. Закройте его (или сохраните копию) и повторите.")
        return 1
    model = build_model(wb)

    for w in diag.warnings:
        print(f"ПРЕДУПРЕЖДЕНИЕ: {w}")
    for e in diag.errors:
        print(f"ОШИБКА: {e}")
    s = model["stats"]
    print(f"\nДокладов в секциях: {s['sectionTalks']}, пленарных/юбилейных/спонсорских: {s['plenaryTalks']}, "
          f"постеров: {s['posters']}, блоков: {s['blocks']}, дней: {len(model['days'])}")
    if diag.errors:
        print(f"\nСборка остановлена: {len(diag.errors)} ошибок(и), {len(diag.warnings)} предупреждений. Исправьте programme.xlsx.")
        return 1
    if check_only:
        print(f"\nПроверка пройдена ({len(diag.warnings)} предупреждений).")
        return 0
    data_path = write_data_js(model)
    print(f"\nЗаписано: {data_path}")
    single = write_single_file(model)
    if single:
        size_kb = single.stat().st_size / 1024
        print(f"Записано: {single} ({size_kb:.0f} КБ)")
    print(f"Готово. Предупреждений: {len(diag.warnings)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
