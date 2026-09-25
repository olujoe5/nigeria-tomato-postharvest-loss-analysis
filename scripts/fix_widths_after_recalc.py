"""
Run this AFTER build_excel.py and AFTER the xlsx skill's recalc.py.

Why this exists: LibreOffice's recalculation step (used to populate cached
formula values so the workbook doesn't show blank cells before Excel
recalculates it) has a side effect of dropping the column-width setting on
some numeric columns when it resaves the file. This script puts those widths
back, and sets fullCalcOnLoad=True so Excel recalculates everything the
instant the file is opened, since this final save will itself drop the
cached formula values LibreOffice just computed.

Usage:
    python3 scripts/build_excel.py
    python3 /mnt/skills/public/xlsx/scripts/recalc.py docs/tomato_PHL_dataset.xlsx 60
    python3 scripts/fix_widths_after_recalc.py
"""
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.workbook.properties import CalcProperties

WORKBOOK_PATH = Path(__file__).parent.parent / "docs" / "tomato_PHL_dataset.xlsx"

MODEL_OUTPUT_WIDTHS = {
    "A": 14, "B": 15, "C": 18, "D": 60, "E": 13, "F": 18,
    "G": 18, "H": 18, "I": 20, "J": 18, "K": 18, "L": 18, "M": 18, "N": 18,
}
SUMMARY_WIDTHS = {"A": 40, "B": 22}


def fix():
    wb = load_workbook(WORKBOOK_PATH)

    for col, width in MODEL_OUTPUT_WIDTHS.items():
        wb["Model_Output"].column_dimensions[col].width = width
    for col, width in SUMMARY_WIDTHS.items():
        wb["Summary"].column_dimensions[col].width = width

    wb.calculation = CalcProperties(fullCalcOnLoad=True)
    wb.save(WORKBOOK_PATH)
    print(f"Widths reapplied and fullCalcOnLoad set on {WORKBOOK_PATH}")


if __name__ == "__main__":
    fix()
