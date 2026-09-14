# -*- coding: utf-8 -*-
"""Add sponsor columns/values on Доклады for P-S1..P-S3."""
from __future__ import annotations

import sys
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import COLS_TALKS, PROGRAMME_XLSX, SHEET_TALKS  # noqa: E402

SPONSORS = {
    "P-S1": {
        "Сайт": "https://gammatech.pro/",
        "Логотип": "gammatech.png",
        "Спонсор (RU)": "Гамматек",
        "Спонсор (EN)": "Gammatech",
    },
    "P-S2": {
        "Сайт": "https://edigitizer.ru/",
        "Логотип": "digitizer.svg",
        "Спонсор (RU)": "Диджитайзер",
        "Спонсор (EN)": "Digitizer",
    },
    "P-S3": {
        "Сайт": "https://spegroup.ru/",
        "Логотип": "spegroup.svg",
        "Спонсор (RU)": "Научное оборудование",
        "Спонсор (EN)": "Scientific Equipment",
    },
}

EXTRA = ["Сайт", "Логотип", "Спонсор (RU)", "Спонсор (EN)"]


def main() -> int:
    wb = openpyxl.load_workbook(PROGRAMME_XLSX)
    ws = wb[SHEET_TALKS]
    headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    # Ensure extra columns exist (append any missing)
    for col in EXTRA:
        if col not in headers:
            headers.append(col)
            ws.cell(1, len(headers), col)
    # Style new header cells like the rest
    fill = PatternFill("solid", fgColor="1F4E79")
    font = Font(color="FFFFFF", bold=True)
    for i, h in enumerate(headers, start=1):
        cell = ws.cell(1, i)
        if cell.value in EXTRA:
            cell.fill = fill
            cell.font = font
            cell.alignment = Alignment(wrap_text=True, vertical="center")
            ws.column_dimensions[get_column_letter(i)].width = {
                "Сайт": 28, "Логотип": 16, "Спонсор (RU)": 22, "Спонсор (EN)": 22
            }.get(cell.value, 18)
    col_index = {h: i for i, h in enumerate(headers, start=1)}
    id_col = col_index["ID"]
    updated = []
    for row in range(2, ws.max_row + 1):
        tid = ws.cell(row, id_col).value
        if tid not in SPONSORS:
            continue
        for key, val in SPONSORS[tid].items():
            ws.cell(row, col_index[key], val)
        updated.append(tid)
    # Sanity: COLS_TALKS matches workbook headers (order of known cols)
    missing = [c for c in COLS_TALKS if c not in headers]
    if missing:
        print("WARNING: workbook still missing", missing)
    wb.save(PROGRAMME_XLSX)
    print(f"Updated {PROGRAMME_XLSX.name}: {', '.join(updated)}")
    print("Headers now:", headers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
