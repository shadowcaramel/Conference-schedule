# -*- coding: utf-8 -*-
"""One-time migration: original committee workbook -> normalized data/programme.xlsx.

Usage:
    python tools/migrate.py [path/to/original.xlsx] [--force]

Reads the hand-made workbook (TimeTable grid, "Plenary talks v2", seven section
sheets, poster sheet), uses the *section sheets* as ground truth for talks and
their day/slot, uses the grid only for breaks, plenary slots and social events,
and writes a clean, bilingual, one-row-per-record workbook that build.py consumes.

Everything that required a judgement call is written to data/migration-report.md.
Run once; afterwards edit data/programme.xlsx by hand and never re-run (it would
overwrite manual edits) unless you pass --force.
"""
from __future__ import annotations

import datetime as dt
import re
import sys
from collections import defaultdict
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

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
    PLENARY_SECTION,
    PROGRAMME_XLSX,
    SHEET_BLOCKS,
    SHEET_CHANGES,
    SHEET_POSTERS,
    SHEET_SECTIONS,
    SHEET_SETTINGS,
    SHEET_TALKS,
    clean,
    fmt_time,
    from_minutes,
    minutes,
    parse_time,
    utf8_stdout,
)

utf8_stdout()

ORIGINAL_DEFAULT = DATA_DIR / "original" / "TimeTable&Programm (1).xlsx"
REPORT_PATH = DATA_DIR / "migration-report.md"

YEAR = 2026
MONTHS_RU = {
    "янв": 1, "фев": 2, "мар": 3, "апр": 4, "мая": 5, "май": 5, "июн": 6,
    "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12,
}

# --------------------------------------------------------------------------- reference data
SECTIONS = [
    # №, short RU, short EN, full RU, full EN, chair RU, chair EN, colour hue name
    ("1", "Структура ядра", "Nuclear structure",
     "Экспериментальные и теоретические исследования свойств атомных ядер",
     "Experimental and theoretical studies of the properties of atomic nuclei",
     "Чувильский Ю. М.", "Yu. M. Tchuvil'sky", "blue"),
    ("2", "Ядерные реакции", "Nuclear reactions",
     "Экспериментальные и теоретические исследования ядерных реакций",
     "Experimental and theoretical studies of nuclear reactions",
     "Сидорчук С. И.", "S. I. Sidorchuk", "green"),
    ("3", "Методы и технологии", "Methods and technologies",
     "Современные ядерно-физические методы, технологии и установки",
     "Modern nuclear-physics methods, technologies and facilities",
     "Жеребчевский В. И.", "V. I. Zherebchevsky", "orange"),
    ("4", "HEP", "HEP",
     "Релятивистская ядерная физика, физика элементарных частиц и физика высоких энергий",
     "Relativistic nuclear physics, particle physics and high-energy physics",
     "Ким В. Т.", "V. T. Kim", "red"),
    ("5", "FBS", "FBS",
     "Физика малочастичных систем",
     "Physics of few-body systems",
     "Яковлев С. Л.", "S. L. Yakovlev", "purple"),
    ("6", "Астрофизика", "Astrophysics",
     "Ядерная астрофизика и физика нейтрино",
     "Nuclear astrophysics and neutrino physics",
     "Наумов В. А.", "V. A. Naumov", "teal"),
    ("7", "Ядерная медицина", "Nuclear medicine",
     "Ядерная медицина, радиационная терапия и радиоэкология",
     "Nuclear medicine, radiation therapy and radioecology",
     "Черняев А. П.", "A. P. Chernyaev", "pink"),
    (PLENARY_SECTION, "Пленарные доклады", "Plenary talks",
     "Пленарные доклады", "Plenary talks", "", "", "slate"),
]

SECTION_SHEETS = {
    "1": "1 Структура", "2": "2 Реакции", "3": "3 Методы", "4": "4 HEP",
    "5": "5 FBS", "6": "6 Астрофизика", "7": "7 Медицина",
}

# Plenary-sheet section tag -> section number
PLENARY_TOPIC = {
    "1_Structure": "1", "2_Reaction": "2", "3_Methods": "3", "4_HEP": "4",
    "5_FBS": "5", "6_Astrophys.": "6", "7_Nucl.medicine": "7",
}

# Poster sheet section labels -> number
POSTER_SECTION = {
    "1. Структура": "1", "2. Реакции": "2", "3. Методы": "3", "4. HEP": "4",
    "5. FBS": "5", "6. Астрофизика": "6", "7. Медицина": "7",
}

# Names of blocks in the grid -> (type, RU, EN)
GRID_LABELS = [
    (re.compile(r"^регистрация", re.I), "регистрация", "Регистрация участников", "Registration"),
    (re.compile(r"^открытие", re.I), "открытие", "Открытие конференции", "Opening ceremony"),
    (re.compile(r"^закрыт+ие", re.I), "закрытие", "Закрытие конференции", "Closing ceremony"),
    (re.compile(r"^кофе", re.I), "перерыв", "Кофе-брейк", "Coffee break"),
    (re.compile(r"^обед", re.I), "обед", "Обед", "Lunch"),
    (re.compile(r"^постер", re.I), "постеры", "Постерная сессия", "Poster session"),
    (re.compile(r"^экскурсия", re.I), "мероприятие", "Экскурсия на теплоходе по Амуру", "Boat excursion on the Amur River"),
    (re.compile(r"^фуршет", re.I), "мероприятие", "Фуршет (welcome party)", "Welcome party"),
    (re.compile(r"^концерт", re.I), "мероприятие", "Концерт", "Concert"),
    (re.compile(r"^банкет", re.I), "мероприятие", "Банкет", "Conference dinner"),
]
RE_PLENARY = re.compile(r"^пленарный доклад\s*(\d+)", re.I)
RE_JUBILEE = re.compile(r"^юбилейный доклад\s*(.+)$", re.I)
RE_SPONSOR = re.compile(r"^доклад спонсора\s*(\d+)", re.I)
RE_SECTION = re.compile(r"^секция\s*(\d+)\s*(?:\(\s*(\d+)\s*-\s*(\d+)\s*\))?", re.I)

# Word parts (letters/digits only, compared upper-case) that must stay upper-case when a
# shouty title is converted to sentence case.
ACRONYMS = {
    "NICA", "SPD", "BM@N", "MPD", "HEP", "GERDA", "LEGEND", "JUNO", "STAR", "QCD", "CVC",
    "CKM", "СКМ", "ENDF", "NCSM", "SS", "HORSE", "CZT", "DT", "SU", "MNT", "GDR",
    "ARFIM", "NOSU", "FLAP", "ARIADNA", "SRC", "JINR", "ОИЯИ", "НИИЯФ", "МГУ", "ИЯИ", "РАН",
    "ЛЯР", "ПИК", "ВВЭР", "КТ", "ЯЭУ", "АЭС", "CAEN", "PYTHIA", "PHQMD", "HYDJET", "TAO", "NUGEN",
    "GVD", "SPS", "AA", "TPC", "РАДЭКС", "СИ", "ФЭУ", "ОЧГ", "ЭГП", "ADS", "ВНИИЭФ", "ВНИИА",
    "ПИЯФ", "НИЦ", "КИ", "ИФВЭ", "ТОГУ", "ДВФУ", "МИФИ", "ТПУ", "ВГУ", "PET", "ПЭТ", "ЯМР",
    "МРТ", "БНЗТ", "BNCT", "HGND", "MC", "DGFRS", "SHE", "УНК", "ИТЭФ", "ЛЯП", "ЛФВЭ", "LHC",
    "CERN", "ЦЕРН", "ATLAS", "CMS", "ALICE", "MRI", "СПАСЧАРМ", "АКУЛИНА", "ВНИИЭФ", "ИЯФ",
    "США", "РФ", "СССР", "ЯЭ", "ЛТ", "GEANT", "MPI", "CPU", "GPU", "ML", "AI", "ИИ", "DNA", "ДНК",
    "PWR", "BWR", "ВВЭР", "РБМК", "БН", "МОХ", "MOX", "ITER", "ИТЭР", "PIK", "SND", "BES", "BESIII",
    "KEK", "RIKEN", "GSI", "FAIR", "GANIL", "SPIRAL", "ISOL", "RIB", "NN", "NNN", "QED", "QCD",
    "EOS", "УРС", "МК", "СВЧ", "ВЧ", "ИК", "УФ", "РЗЭ", "ОЯТ", "РАО", "ЯТЦ", "ЗЯТЦ", "ГХК",
}
# Canonical spelling for whole tokens or word parts (compared upper-case).
CANONICAL = {
    "HPGE": "HPGe", "CSI": "CsI", "PURE": "pure", "BAIKAL": "Baikal", "CDZNSES": "CdZnSeS",
    "ZNS": "ZnS", "MEV": "MeV", "GEV": "GeV", "TEV": "TeV", "KEV": "keV", "AGEV": "AGeV",
    "МЭВ": "МэВ", "ГЭВ": "ГэВ", "КЭВ": "кэВ", "ТЭВ": "ТэВ", "URQMD": "UrQMD", "EPOS4": "EPOS4",
    "NEUCBOT": "NeuCBOT", "SIC": "SiC", "SI": "Si", "LI": "Li", "СПБГУ": "СПбГУ", "LN2": "LN2",
    "ПРО-ТОНОВ": "протонов", "ПО-СЛЕ": "после", "ПО-ЛУВЫВЕДЕНИЯ": "полувыведения",
    "ОТКРЫ-ТЫХ": "открытых", "PRO-TOTYPES": "prototypes", "АТ-МОСФЕРНЫХ": "атмосферных",
    "МНГО-ДЕТЕКТОРНЫХ": "многодетекторных", "ГАММА_КВАНТОВ": "гамма-квантов",
    # proper nouns
    "WIGNER’S": "Wigner’s", "WIGNER'S": "Wigner's", "WIGNER": "Wigner", "GAMOW": "Gamow",
    "TELLER": "Teller", "SKYRME": "Skyrme", "VAN": "Van", "DER": "der", "WAALS": "Waals",
    "NILSSON": "Nilsson", "WOODS": "Woods", "SAXON": "Saxon", "RUSSIA": "Russia", "TSALLIS": "Tsallis",
    "GLAUBER": "Glauber", "PAULI": "Pauli", "NIKIFOROV": "Nikiforov", "UVAROV": "Uvarov",
    "FEYNMAN": "Feynman", "HOYLE": "Hoyle", "HIGGS": "Higgs", "CHERENKOV": "Cherenkov",
    "COULOMB": "Coulomb", "BOREXINO": "Borexino", "COMPTON": "Compton", "MONTE": "Monte",
    "CARLO": "Carlo", "SCHRÖDINGER": "Schrödinger", "DIRAC": "Dirac", "FERMI": "Fermi",
    "BOSE": "Bose", "EINSTEIN": "Einstein", "LORENTZ": "Lorentz", "JACOBI": "Jacobi",
    "АБЕЛЯ": "Абеля", "НИЛЬСОНА": "Нильсона", "ВУДСА": "Вудса", "САКСОНА": "Саксона",
    "ГАМОВА": "Гамова", "ТЕЛЛЕРА": "Теллера", "ХОЙЛА": "Хойла", "ГЛАУБЕРА": "Глаубера",
    "ШРЕДИНГЕРА": "Шредингера", "ДИРАКА": "Дирака", "КУЛОНА": "Кулона", "ЧЕРЕНКОВА": "Черенкова",
    "ЛАУЭ": "Лауэ", "РОССИИ": "России", "РОССИЯ": "Россия", "БАЙКАЛ": "Байкал", "АМУР": "Амур",
    "ХАБАРОВСК": "Хабаровск", "ДУБНА": "Дубна", "ДУБНЕ": "Дубне", "ЯКУТИЯ": "Якутия",
}
GREEK = set("αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ")
CYRILLIC_SINGLE_LOWER = set("ИВСКОУАЯЖ")  # prepositions / conjunctions typed in caps
WORD_RE = re.compile(r"([^\W_]+(?:[’'@][^\W_]+)*)", re.U)

# --------------------------------------------------------------------------- report


class Report:
    def __init__(self) -> None:
        self.sections: dict[str, list[str]] = defaultdict(list)

    def add(self, section: str, text: str) -> None:
        self.sections[section].append(text)

    def write(self, path: Path) -> None:
        lines = ["# Отчёт о миграции программы", "",
                 f"Создан: {dt.datetime.now():%d.%m.%Y %H:%M}", "",
                 "Ниже перечислено всё, что потребовало решения при переносе данных из исходной книги "
                 "в `data/programme.xlsx`. Проверьте каждый пункт и при необходимости исправьте "
                 "значения прямо в `programme.xlsx`.", ""]
        for title, items in self.sections.items():
            lines.append(f"## {title}")
            lines.append("")
            lines.extend(f"- {item}" for item in items)
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")


report = Report()

# --------------------------------------------------------------------------- title case


def _is_shouty(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 8:
        return False
    upper = sum(1 for c in letters if c.isupper())
    return upper / len(letters) >= 0.75


def _has_deliberate_lower(word: str) -> bool:
    """True if the author typed a lower-case Latin/Cyrillic letter (Pu, mZr, Ft, √sNN)."""
    return any(ch.islower() and ch not in GREEK for ch in word)


def _fix_word(word: str, quoted: bool, standalone: bool = False) -> tuple[str, bool]:
    """Return (fixed word, was_lowercased) for a single letters/digits run.

    ``standalone`` is True when the word is the whole whitespace-delimited token, which is
    the only case where a single capital letter can be an article/preposition (A, И, В).
    """
    up = word.upper()
    if up in CANONICAL:
        return CANONICAL[up], False
    if _has_deliberate_lower(word):
        return word, False
    if any(ch.isdigit() for ch in word):
        # 197AU -> 197Au, 282NH -> 282Nh (mass number + element symbol)
        m = re.fullmatch(r"(\d+)([A-Z])([A-Z]?)", word)
        if m:
            return m.group(1) + m.group(2) + m.group(3).lower(), False
        return word, False
    if up in ACRONYMS:
        return word, False
    if len(word) == 1:
        if quoted or not standalone:
            return word, False  # symbols: K, N, Z, X, S-factor, B(E2), A=6, У-70
        if word in CYRILLIC_SINGLE_LOWER or word == "A":
            return word.lower(), True
        return word, False
    return word.lower(), True


def _fix_token(token: str) -> tuple[str, bool]:
    """Fix one whitespace-delimited token; returns (text, first_word_lowercased)."""
    up = token.upper()
    if up in CANONICAL:
        return CANONICAL[up], False
    # strip trailing/leading punctuation for whole-token lookups like «BAIKAL-GVD:»
    core = token.strip(":;,.!?«»\"“”()[]")
    if core and core.upper() in CANONICAL:
        return token.replace(core, CANONICAL[core.upper()]), False
    parts = WORD_RE.split(token)
    out: list[str] = []
    first_lowered: bool | None = None
    prev_sep = ""
    for i, part in enumerate(parts):
        if i % 2 == 0:  # separator
            prev_sep = part
            out.append(part)
            continue
        quoted = any(q in prev_sep for q in "«\"“'")
        standalone = part == token.strip(":;,.!?«»\"“”()[]")
        fixed, lowered = _fix_word(part, quoted, standalone)
        if first_lowered is None:
            first_lowered = lowered
        out.append(fixed)
    return "".join(out), bool(first_lowered)


def sentence_case(title: str) -> tuple[str, bool]:
    """Convert an ALL-CAPS title to sentence case, protecting acronyms and formulae."""
    if not _is_shouty(title):
        return title, False
    tokens = title.split(" ")
    out: list[str] = []
    first_word_lowered = False
    for idx, tok in enumerate(tokens):
        fixed, lowered = _fix_token(tok)
        if idx == 0:
            first_word_lowered = lowered
        out.append(fixed)
    text = " ".join(out)
    # capitalise the first letter of the sentence, but only if we lower-cased that word
    # ourselves (never touch a preserved symbol such as "pN ..." or "3-3 ...")
    if first_word_lowered:
        for i, ch in enumerate(text):
            if ch.isalpha():
                text = text[:i] + ch.upper() + text[i + 1:]
                break
    # capitalise after a full stop when followed by a lower-case letter
    text = re.sub(r"(\.\s+)([a-zа-яё])", lambda m: m.group(1) + m.group(2).upper(), text)
    return text, text != title


# --------------------------------------------------------------------------- original parsers


def parse_day_header(text: str) -> dt.date | None:
    """'21 сент., понедельник' -> date(2026, 9, 21)."""
    m = re.match(r"^\s*(\d{1,2})\s+([а-яё]+)", text, re.I)
    if not m:
        return None
    day = int(m.group(1))
    mon = m.group(2).lower()[:3]
    month = MONTHS_RU.get(mon)
    if not month:
        return None
    return dt.date(YEAR, month, day)


def parse_time_range(text: str) -> tuple[dt.time | None, dt.time | None]:
    """'16:15--18:00' / '16:15--' -> (start, end)."""
    parts = re.split(r"\s*-{1,2}\s*|\s*—\s*", clean(text))
    start = parse_time(parts[0]) if parts and parts[0] else None
    end = parse_time(parts[1]) if len(parts) > 1 and parts[1] else None
    return start, end


def read_sections(wb) -> tuple[list[dict], list[dict]]:
    """Returns (talks, blocks) from the seven section sheets."""
    talks: list[dict] = []
    blocks: list[dict] = []
    for sec_no, sheet_name in SECTION_SHEETS.items():
        ws = wb[sheet_name]
        current: dict | None = None
        seen_numbers: set[int] = set()
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
            a, b, c, d, e = (clean(row[i].value) if i < len(row) else "" for i in range(5))
            date = parse_day_header(a)
            if date:
                start, end = parse_time_range(c)
                if start is None:
                    report.add("Блоки секций без времени начала",
                               f"Секция {sec_no}, {a}: не удалось разобрать время «{c}» — блок пропущен")
                    current = None
                    continue
                if end is None:
                    end = dt.time(18, 0)
                    report.add("Блоки секций без времени окончания",
                               f"Секция {sec_no}, {date:%d.%m} {fmt_time(start)}: в исходнике «{c}», "
                               f"окончание принято 18:00 (как у параллельных секций)")
                current = {"date": date, "start": start, "end": end, "section": sec_no,
                           "numbers": [], "sheet": sheet_name}
                blocks.append(current)
                continue
            if re.fullmatch(r"\d+(\.0)?", a):
                number = int(float(a))
                if current is None:
                    report.add("Доклады вне блоков", f"Секция {sec_no}: доклад №{number} ({c}) стоит до первого заголовка дня — пропущен")
                    continue
                if number in seen_numbers:
                    report.add("Дублирующиеся номера докладов", f"Секция {sec_no}: номер {number} встречается дважды ({c})")
                seen_numbers.add(number)
                title, changed = sentence_case(d)
                if changed:
                    report.add("Заголовки, переведённые из ВЕРХНЕГО РЕГИСТРА (проверьте аббревиатуры)",
                               f"S{sec_no}-{number:02d}: «{d}» → «{title}»")
                talks.append({
                    "id": f"S{sec_no}-{number:02d}", "section": sec_no, "number": number,
                    "last": c, "first": b, "org": e, "title": title, "duration": None,
                    "status": "", "topic": "", "note_ru": "", "note_en": "",
                })
                current["numbers"].append(number)
        # gaps in numbering
        nums = sorted(seen_numbers)
        if nums and nums != list(range(1, nums[-1] + 1)):
            missing = sorted(set(range(1, nums[-1] + 1)) - seen_numbers)
            report.add("Пропуски в нумерации", f"Секция {sec_no}: отсутствуют номера {missing}")
    return talks, blocks


def read_plenary(wb) -> tuple[list[dict], dict[tuple[dt.date, str], list[str]]]:
    """Returns plenary/jubilee/sponsor talks and the per-day ordered list of numbers.

    Rows are numbered sequentially across days in the order they appear, which is
    exactly how the grid refers to them ("пленарный доклад 12").
    """
    ws = wb["Plenary talks v2"]
    talks: list[dict] = []
    current_date: dt.date | None = None
    plenary_counter = 0
    jubilee_counter = 0
    sponsor_counter = 0
    weekday_names = {"понедельник": 0, "вторник": 1, "среда": 2, "четверг": 3, "пятница": 4, "суббота": 5}
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
        vals = [clean(cell.value) for cell in row] + [""] * 8
        a, b, c, d, e = vals[:5]
        # day header: B = weekday, C = dd.mm
        if b.lower() in weekday_names and re.match(r"^\d{1,2}\.\d{1,2}$", c):
            dd, mm = c.split(".")
            current_date = dt.date(YEAR, int(mm), int(dd))
            continue
        if current_date is None:
            continue
        m = re.match(r"^(\d+)\s*мин", a)
        if not m:
            filled = [v for v in (a, b, c, d, e) if v]
            is_header = b == "First name" or a in ("открытие", "закрытие")
            if len(filled) >= 2 and not is_header:
                report.add("Пропущенные строки на листе пленарных докладов",
                           f"{current_date:%d.%m}: «{' | '.join(filled)[:110]}» — нет длительности в колонке A "
                           f"(черновая/перенесённая запись), не перенесена")
            continue
        duration = int(m.group(1))
        kind = e.strip()
        if kind == "Jub":
            jubilee_counter += 1
            number, tid, btype, topic = f"Ю{jubilee_counter}", f"P-J{jubilee_counter}", "юбилейный", ""
        elif kind == "sponsor":
            sponsor_counter += 1
            number, tid, btype, topic = f"С{sponsor_counter}", f"P-S{sponsor_counter}", "спонсор", ""
        else:
            plenary_counter += 1
            number, tid, btype, topic = str(plenary_counter), f"P-{plenary_counter:02d}", "пленарный", PLENARY_TOPIC.get(kind, "")
            if kind and kind not in PLENARY_TOPIC:
                report.add("Неизвестная тематика пленарного доклада", f"{tid}: «{kind}»")
        title, changed = sentence_case(d)
        if changed:
            report.add("Заголовки, переведённые из ВЕРХНЕГО РЕГИСТРА (проверьте аббревиатуры)",
                       f"{tid}: «{d}» → «{title}»")
        talks.append({
            "id": tid, "section": PLENARY_SECTION, "number": number, "last": c, "first": b,
            "org": "", "title": title, "duration": duration, "status": "", "topic": topic,
            "note_ru": "", "note_en": "", "kind": btype, "date": current_date,
        })
    return talks, {}


def read_posters(wb) -> list[dict]:
    ws = wb["Постерная секция"]
    posters: list[dict] = []
    n = 0
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
        vals = [clean(cell.value) for cell in row] + [""] * 8
        first, last, title, section, extra = vals[:5]
        if not title or first == "First name" or first.startswith("Стендовые"):
            continue
        n += 1
        sec = POSTER_SECTION.get(section, "")
        if not sec:
            report.add("Постеры с нераспознанной секцией", f"POST-{n:02d} «{title[:50]}…»: «{section}»")
        new_title, changed = sentence_case(title)
        if changed:
            report.add("Заголовки, переведённые из ВЕРХНЕГО РЕГИСТРА (проверьте аббревиатуры)",
                       f"POST-{n:02d}: «{title}» → «{new_title}»")
        note = f"Соавтор/пометка в исходнике: {extra}" if extra else ""
        posters.append({"id": f"POST-{n:02d}", "last": last, "first": first, "org": "",
                        "title": new_title, "section": sec, "board": "", "status": "",
                        "note_ru": note, "note_en": ""})
    return posters


# --------------------------------------------------------------------------- grid parser


def read_grid(wb) -> list[dict]:
    """Parse the merged-cell TimeTable grid into raw blocks (date, start, end, text)."""
    ws = wb["TimeTable"]
    # 1. day columns from row 2 (merged ranges with dates)
    day_of_col: dict[int, dt.date] = {}
    for rng in ws.merged_cells.ranges:
        if rng.min_row == 2:
            text = clean(ws.cell(2, rng.min_col).value)
            m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})", text)
            if m:
                date = dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                for col in range(rng.min_col, rng.max_col + 1):
                    day_of_col[col] = date
    # 2. time labels in column A
    labelled: dict[int, int] = {}
    for r in range(3, ws.max_row + 1):
        t = parse_time(ws.cell(r, 1).value)
        if t is not None:
            labelled[r] = minutes(t)
    rows_sorted = sorted(labelled)

    def row_time(r: int) -> int | None:
        if r in labelled:
            return labelled[r]
        prev = [x for x in rows_sorted if x < r]
        nxt = [x for x in rows_sorted if x > r]
        if not prev:
            return None
        if not nxt:
            # below the last label: extrapolate with the slope of the last interval
            if len(prev) < 2:
                return None
            r0, r1 = prev[-2], prev[-1]
            slope = (labelled[r1] - labelled[r0]) / (r1 - r0)
            return round(labelled[r1] + slope * (r - r1))
        r0, r1 = prev[-1], nxt[0]
        return round(labelled[r0] + (labelled[r1] - labelled[r0]) * (r - r0) / (r1 - r0))

    blocks: list[dict] = []
    max_grid_row = max(rows_sorted) + 6
    for rng in ws.merged_cells.ranges:
        if rng.min_col == 1 or rng.min_row < 8 or rng.min_row > max_grid_row:
            continue
        text = clean(ws.cell(rng.min_row, rng.min_col).value)
        if not text:
            continue
        date = day_of_col.get(rng.min_col)
        if date is None:
            continue
        start = row_time(rng.min_row)
        end = row_time(rng.max_row + 1)
        if start is None or end is None:
            report.add("Грид: блоки без времени", f"{rng}: «{text}»")
            continue
        blocks.append({"date": date, "start": from_minutes(start), "end": from_minutes(end),
                       "text": text, "range": str(rng), "cols": rng.max_col - rng.min_col + 1})
    blocks.sort(key=lambda b: (b["date"], minutes(b["start"]), b["range"]))
    return blocks


# --------------------------------------------------------------------------- assemble


def build_blocks(grid: list[dict], section_blocks: list[dict], plenary: list[dict]) -> list[dict]:
    out: list[dict] = []
    plenary_by_number = {t["number"]: t for t in plenary}
    grid_section_ranges: dict[tuple, tuple[int, int] | None] = {}

    for g in grid:
        text = g["text"]
        m = RE_SECTION.match(text)
        if m:
            key = (g["date"], minutes(g["start"]), m.group(1))
            grid_section_ranges[key] = (int(m.group(2)), int(m.group(3))) if m.group(2) else None
            continue
        m = RE_PLENARY.match(text)
        if m:
            number = m.group(1)
            talk = plenary_by_number.get(number)
            if not talk:
                report.add("Грид: пленарные доклады без записи на листе Plenary", f"{g['date']:%d.%m} {fmt_time(g['start'])}: «{text}»")
            out.append(dict(date=g["date"], start=g["start"], end=g["end"], type="пленарный",
                            ru="Пленарный доклад", en="Plenary talk", section=PLENARY_SECTION,
                            talks=number, room="", note_ru="", note_en=""))
            continue
        m = RE_JUBILEE.match(text)
        if m:
            who = m.group(1).strip()
            # order of jubilee talks in the sheet: НИИЯФ (Ю1) then ОИЯИ (Ю2)
            number = "Ю1" if "НИИЯФ" in who.upper() else "Ю2"
            out.append(dict(date=g["date"], start=g["start"], end=g["end"], type="юбилейный",
                            ru="Юбилейный доклад", en="Anniversary talk", section=PLENARY_SECTION,
                            talks=number, room="", note_ru="", note_en=""))
            continue
        m = RE_SPONSOR.match(text)
        if m:
            out.append(dict(date=g["date"], start=g["start"], end=g["end"], type="спонсор",
                            ru="Доклад спонсора", en="Sponsor talk", section=PLENARY_SECTION,
                            talks=f"С{m.group(1)}", room="", note_ru="", note_en=""))
            continue
        matched = False
        for rx, btype, ru, en in GRID_LABELS:
            if rx.search(text):
                start, end = g["start"], g["end"]
                note_ru = note_en = ""
                if btype == "постеры":
                    # The grid only has a scribble "Постеры" in the middle of the Wednesday
                    # afternoon; take the free slot after the coffee break.
                    start, end = dt.time(16, 45), dt.time(18, 0)
                    note_ru, note_en = "Время уточняется", "Time to be confirmed"
                    report.add("Постерная сессия",
                               f"В гриде пометка «Постеры» стоит в {g['date']:%d.%m} около {fmt_time(g['start'])} без границ; "
                               f"принято 16:45–18:00 (свободное окно после кофе-брейка). Проверьте.")
                if text.lower() != ru.lower() and text.lower() not in ("кофе-брейк", "обед", "обед.", "фуршет", "концерт", "банкет", "регистрация", "открытие", "экскурсия на теплоходе"):
                    report.add("Опечатки в гриде (исправлены автоматически)", f"«{text}» → «{ru}»")
                out.append(dict(date=g["date"], start=start, end=end, type=btype, ru=ru, en=en,
                                section="", talks="", room="", note_ru=note_ru, note_en=note_en))
                matched = True
                break
        if not matched:
            report.add("Грид: нераспознанные подписи (не перенесены)", f"{g['date']:%d.%m} {fmt_time(g['start'])}–{fmt_time(g['end'])} [{g['range']}]: «{text}»")

    # section blocks from the section sheets (ground truth)
    for sb in section_blocks:
        nums = sorted(sb["numbers"])
        if not nums:
            report.add("Пустые блоки секций", f"Секция {sb['section']} {sb['date']:%d.%m} {fmt_time(sb['start'])}: под заголовком дня нет докладов — блок пропущен")
            continue
        contiguous = nums == list(range(nums[0], nums[-1] + 1))
        talks_spec = f"{nums[0]}-{nums[-1]}" if contiguous else ",".join(map(str, nums))
        if not contiguous:
            report.add("Непоследовательные номера в блоке", f"Секция {sb['section']} {sb['date']:%d.%m} {fmt_time(sb['start'])}: {nums}")
        key = (sb["date"], minutes(sb["start"]), sb["section"])
        if key not in grid_section_ranges:
            # tolerate sloppy placement in the grid (same day + section, start within 45 min)
            near = [k for k in grid_section_ranges
                    if k[0] == sb["date"] and k[2] == sb["section"] and abs(k[1] - minutes(sb["start"])) <= 45]
            if near:
                key = near[0]
                report.add("Расхождения грид ↔ лист секции (взят лист секции)",
                           f"Секция {sb['section']} {sb['date']:%d.%m}: в гриде блок стоит в {fmt_time(from_minutes(key[1]))}, "
                           f"на листе секции {fmt_time(sb['start'])}")
        if key in grid_section_ranges:
            gr = grid_section_ranges.pop(key)
            if gr and gr != (nums[0], nums[-1]):
                report.add("Расхождения грид ↔ лист секции (взят лист секции)",
                           f"Секция {sb['section']} {sb['date']:%d.%m} {fmt_time(sb['start'])}: в гриде ({gr[0]}–{gr[1]}), "
                           f"на листе секции {nums[0]}–{nums[-1]}")
        else:
            report.add("Блоки секций, которых нет в гриде", f"Секция {sb['section']} {sb['date']:%d.%m} {fmt_time(sb['start'])}–{fmt_time(sb['end'])} (доклады {talks_spec})")
        out.append(dict(date=sb["date"], start=sb["start"], end=sb["end"], type="секция",
                        ru="", en="", section=sb["section"], talks=talks_spec, room="", note_ru="", note_en=""))
    for key, gr in grid_section_ranges.items():
        date, start_min, sec = key
        rng = f"({gr[0]}–{gr[1]})" if gr else "(без диапазона докладов)"
        report.add("Блоки в гриде, которых нет на листах секций (не перенесены)",
                   f"Секция {sec} {date:%d.%m} {fmt_time(from_minutes(start_min))} {rng}")

    # plenary talks never placed
    placed = {b["talks"] for b in out if b["section"] == PLENARY_SECTION}
    for t in plenary:
        if t["number"] not in placed:
            report.add("Пленарные доклады без слота в гриде", f"{t['id']} {t['last']}: «{t['title'][:60]}»")

    out.sort(key=lambda b: (b["date"], minutes(b["start"]), b["type"] != "секция", str(b["section"]).zfill(2)))
    return out


# --------------------------------------------------------------------------- write


def style_header(ws, ncols: int, widths: list[int]) -> None:
    fill = PatternFill("solid", fgColor="1F2937")
    for c in range(1, ncols + 1):
        cell = ws.cell(1, c)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(c)].width = widths[c - 1] if c - 1 < len(widths) else 14
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 30


def write_workbook(path: Path, talks: list[dict], plenary: list[dict], blocks: list[dict], posters: list[dict]) -> None:
    wb = openpyxl.Workbook()

    # Настройки
    ws = wb.active
    ws.title = SHEET_SETTINGS
    ws.append(COLS_SETTINGS)
    settings = [
        ("Название", "ЯДРО-2026 — Международная конференция по физике", "NUCLEUS-2026 — International Conference on Physics", "Заголовок сайта"),
        ("Краткое название", "ЯДРО-2026", "NUCLEUS-2026", "Заголовок вкладки браузера, файлов .ics"),
        ("Дата начала", "2026-09-21", "", "ГГГГ-ММ-ДД"),
        ("Дата окончания", "2026-09-26", "", "ГГГГ-ММ-ДД"),
        ("Город", "Хабаровск", "Khabarovsk", ""),
        ("Место проведения", "Тихоокеанский государственный университет", "Pacific National University", ""),
        ("Часовой пояс", "Asia/Vladivostok", "", "IANA-идентификатор; используется для отметки «сейчас»"),
        ("Смещение UTC", "+10:00", "", "Для файлов календаря (.ics)"),
        ("Сайт", "http://nucleus.togudv.ru/", "", ""),
        ("Контакт оргкомитета", "", "", "E-mail или телефон; показывается в подвале"),
        ("Сноска", "Время указано местное (Хабаровск, UTC+10). Программа может уточняться.",
         "All times are local (Khabarovsk, UTC+10). The programme is subject to change.", "Показывается под расписанием"),
    ]
    for row in settings:
        ws.append(list(row))
    style_header(ws, len(COLS_SETTINGS), [24, 60, 60, 48])

    # Секции
    ws = wb.create_sheet(SHEET_SECTIONS)
    ws.append(COLS_SECTIONS)
    for s in SECTIONS:
        ws.append([s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7], ""])
    style_header(ws, len(COLS_SECTIONS), [6, 24, 24, 60, 60, 22, 22, 10, 16])

    # Блоки
    ws = wb.create_sheet(SHEET_BLOCKS)
    ws.append(COLS_BLOCKS)
    for b in blocks:
        ws.append([b["date"], b["start"], b["end"], b["type"], b["ru"], b["en"], b["section"],
                   b["talks"], b["room"], b["note_ru"], b["note_en"]])
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        row[0].number_format = "DD.MM.YYYY"
        row[1].number_format = "HH:MM"
        row[2].number_format = "HH:MM"
    style_header(ws, len(COLS_BLOCKS), [12, 8, 8, 14, 32, 32, 8, 10, 14, 30, 30])
    dv = DataValidation(type="list", formula1='"' + ",".join(BLOCK_TYPES) + '"', allow_blank=False)
    dv.error = "Выберите тип из списка"
    ws.add_data_validation(dv)
    dv.add(f"D2:D{max(ws.max_row, 2) + 200}")

    # Доклады
    ws = wb.create_sheet(SHEET_TALKS)
    ws.append(COLS_TALKS)
    for t in plenary + talks:
        ws.append([t["id"], t["section"], t["number"], t["last"], t["first"], t["org"], "", t["title"],
                   t["duration"], "", t["status"], t["topic"], t["note_ru"], t["note_en"]])
    style_header(ws, len(COLS_TALKS), [9, 8, 6, 20, 24, 18, 22, 80, 12, 8, 12, 10, 24, 24])
    dv = DataValidation(type="list", formula1='"отменён,перенесён"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"K2:K{max(ws.max_row, 2) + 300}")
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        row[7].alignment = Alignment(wrap_text=True, vertical="top")

    # Постеры
    ws = wb.create_sheet(SHEET_POSTERS)
    ws.append(COLS_POSTERS)
    for p in posters:
        ws.append([p["id"], p["last"], p["first"], p["org"], "", p["title"], p["section"], p["board"],
                   p.get("status", ""), p["note_ru"], p["note_en"]])
    style_header(ws, len(COLS_POSTERS), [10, 20, 24, 18, 22, 80, 8, 10, 12, 30, 30])
    dv_post = DataValidation(type="list", formula1='"отменён,перенесён"', allow_blank=True)
    ws.add_data_validation(dv_post)
    dv_post.add(f"I2:I{max(ws.max_row, 2) + 200}")
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        row[5].alignment = Alignment(wrap_text=True, vertical="top")

    # Изменения
    ws = wb.create_sheet(SHEET_CHANGES)
    ws.append(COLS_CHANGES)
    ws.append([dt.datetime.now().replace(second=0, microsecond=0),
               "Опубликована предварительная программа.", "Preliminary programme published."])
    ws.cell(2, 1).number_format = "DD.MM.YYYY HH:MM"
    style_header(ws, len(COLS_CHANGES), [18, 60, 60])

    wb.save(path)


# --------------------------------------------------------------------------- main


def main(argv: list[str]) -> int:
    force = "--force" in argv
    args = [a for a in argv if not a.startswith("--")]
    original = Path(args[0]) if args else ORIGINAL_DEFAULT
    if not original.exists():
        print(f"Исходная книга не найдена: {original}")
        return 1
    if PROGRAMME_XLSX.exists() and not force:
        print(f"{PROGRAMME_XLSX} уже существует. Миграция выполняется один раз; "
              f"чтобы перезаписать (потеряв ручные правки!), запустите с --force.")
        return 1

    wb = openpyxl.load_workbook(original, data_only=True)
    talks, section_blocks = read_sections(wb)
    plenary, _ = read_plenary(wb)
    posters = read_posters(wb)
    grid = read_grid(wb)
    blocks = build_blocks(grid, section_blocks, plenary)

    # duplicate speakers across sections (same last name + same title)
    seen: dict[tuple[str, str], str] = {}
    for t in talks:
        key = (t["last"].lower(), t["title"].lower())
        if key in seen:
            report.add("Один и тот же доклад в двух секциях", f"{seen[key]} и {t['id']}: {t['last']} — «{t['title'][:60]}»")
        else:
            seen[key] = t["id"]

    write_workbook(PROGRAMME_XLSX, talks, plenary, blocks, posters)

    report.add("Итого перенесено", f"Секционных докладов: {len(talks)}")
    report.add("Итого перенесено", f"Пленарных/юбилейных/спонсорских: {len(plenary)} "
               f"({sum(1 for t in plenary if t['kind']=='пленарный')} / {sum(1 for t in plenary if t['kind']=='юбилейный')} / {sum(1 for t in plenary if t['kind']=='спонсор')})")
    report.add("Итого перенесено", f"Постеров: {len(posters)}")
    report.add("Итого перенесено", f"Блоков расписания: {len(blocks)}")
    report.write(REPORT_PATH)

    print(f"Записано: {PROGRAMME_XLSX}")
    print(f"Отчёт:    {REPORT_PATH}")
    print()
    for title, items in report.sections.items():
        print(f"== {title} ({len(items)})")
        for item in items[:12]:
            print(f"   - {item}")
        if len(items) > 12:
            print(f"   … ещё {len(items) - 12}, см. отчёт")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
