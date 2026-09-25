"""
Builds the Excel workbook deliverable: raw source tables + model output +
a Summary tab driven by live SUMIFS formulas (not hardcoded numbers), so it
recalculates if anyone tweaks an assumption cell.
"""
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OUT_PATH = Path(__file__).parent.parent / "docs" / "tomato_PHL_dataset.xlsx"

FONT_NAME = "Arial"
HEADER_FILL = PatternFill(start_color="1F4E3D", end_color="1F4E3D", fill_type="solid")
HEADER_FONT = Font(name=FONT_NAME, bold=True, color="FFFFFF")
TITLE_FONT = Font(name=FONT_NAME, bold=True, size=14)
BASE_FONT = Font(name=FONT_NAME, size=10)


def _number_format_for(col_name: str):
    name = col_name.lower()
    if "naira" in name or "price" in name:
        return "#,##0"
    if "tonnes" in name:
        return "#,##0.0"
    if "pct" in name and "tonnes" not in name:
        return '0.0"%"'
    return None


def write_df_sheet(wb, sheet_name, df, note=None):
    # NOTE: data always starts at row 2 (header row 1), regardless of `note`,
    # because Summary-tab formulas hardcode that row offset. A note, if given,
    # is written to a cell comment on A1 instead of an extra row, so it never
    # shifts the data range out from under those formulas.
    ws = wb.create_sheet(sheet_name)
    start_row = 1
    if note:
        from openpyxl.comments import Comment
        ws.cell(row=1, column=1).comment = Comment(note, "Olumide")

    for j, col in enumerate(df.columns, start=1):
        c = ws.cell(row=start_row, column=j, value=col)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = Alignment(wrap_text=True, vertical="center")

    number_formats = {col: _number_format_for(col) for col in df.columns}

    for i, row in enumerate(df.itertuples(index=False), start=start_row + 1):
        for j, (col, val) in enumerate(zip(df.columns, row), start=1):
            # Booleans were displaying as raw =TRUE()/=FALSE() formulas in Excel -
            # write them as plain Yes/No text instead, which is what a reader expects.
            if isinstance(val, (bool,)):
                val = "Yes" if val else "No"
            cell = ws.cell(row=i, column=j, value=val)
            cell.font = BASE_FONT
            fmt = number_formats.get(col)
            if fmt:
                cell.number_format = fmt

    for j, col in enumerate(df.columns, start=1):
        fmt = number_formats.get(col)
        if fmt:
            # Numbers with comma separators need more room than the raw digit
            # count suggests (e.g. 178236364680 -> "178,236,364,680" is 15 chars,
            # not 12) - so nothing shows as ##### or scientific.
            width = 18
        else:
            width = min(
                max(len(str(col)), df[col].astype(str).map(len).max() if len(df) else 10) + 2,
                60,
            )
        ws.column_dimensions[get_column_letter(j)].width = width

    ws.freeze_panes = ws.cell(row=start_row + 1, column=1).coordinate
    return ws, start_row


def build():
    sources = pd.read_csv(DATA_DIR / "sources.csv")
    production = pd.read_csv(DATA_DIR / "state_production_estimates.csv")
    stages = pd.read_csv(DATA_DIR / "stage_loss_benchmarks.csv")
    prices = pd.read_csv(DATA_DIR / "state_prices_naira_per_kg.csv")
    model = pd.read_csv(DATA_DIR / "tomato_loss_model_output.csv")

    wb = Workbook()
    wb.remove(wb.active)

    # --- Cover / README sheet ---
    ws = wb.create_sheet("README")
    ws.column_dimensions["A"].width = 100
    lines = [
        ("Nigeria Tomato Post-Harvest Loss Model", TITLE_FONT),
        ("Kano to Lagos corridor case study, compiled by Joseph Olumide", BASE_FONT),
        ("", BASE_FONT),
        ("How this workbook is put together", HEADER_FONT),
        ("Sources has every published figure I used, with a citation and a URL, so you can check any number", BASE_FONT),
        ("against where it actually came from.", BASE_FONT),
        ("State_Production, Stage_Loss_Benchmarks, and State_Prices are the raw tables everything else is built on.", BASE_FONT),
        ("Where a value is a genuine analyst estimate rather than an official figure, the notes column says so plainly.", BASE_FONT),
        ("Model_Output is the full calculation, tonnes and naira lost by state and stage, baseline versus the", BASE_FONT),
        ("cold-chain scenario.", BASE_FONT),
        ("Summary pulls the headline numbers together using live formulas, not typed-in totals, so if you change an", BASE_FONT),
        ("assumption upstream and rerun the Python model (scripts/model_losses.py), everything here updates itself.", BASE_FONT),
        ("", BASE_FONT),
        ("The short version of the methodology", HEADER_FONT),
        ("There's no single official Nigerian dataset that breaks tomato loss down by state and by supply-chain stage", BASE_FONT),
        ("in naira terms, so this workbook builds one. It combines a published national loss rate (45%), a published", BASE_FONT),
        ("stage-share breakdown of that loss (38/34/28%), NBS state-level prices, and an estimated state production", BASE_FONT),
        ("split, since no authoritative per-state tonnage series exists publicly. Every number traces back to", BASE_FONT),
        ("something, and every estimate is flagged as one. Full detail is in README.md in the project folder.", BASE_FONT),
    ]
    for i, (text, font) in enumerate(lines, start=1):
        c = ws.cell(row=i, column=1, value=text)
        c.font = font

    # Create Summary right after README so the tab order reads sensibly from
    # the start (README, Summary, then the raw data tables). It gets
    # populated further down, once the other sheets exist for it to reference.
    summary_ws = wb.create_sheet("Summary")
    summary_ws.column_dimensions["A"].width = 40
    summary_ws.column_dimensions["B"].width = 22

    write_df_sheet(wb, "Sources", sources, "Every published figure used in this model, with a citation and a URL")
    write_df_sheet(wb, "State_Production", production, "How national production splits across states. See the estimate_basis column for how each figure was worked out")
    write_df_sheet(wb, "Stage_Loss_Benchmarks", stages, "Loss share by supply-chain stage, based on a 2025 Nigerian postharvest study")
    write_df_sheet(wb, "State_Prices", prices, "State tomato prices in naira per kg, anchored to NBS data for June 2024")
    write_df_sheet(wb, "Model_Output", model, "The full calculation: tonnes and naira lost by state and stage, baseline versus the cold-chain scenario")

    # --- Populate the Summary sheet with live formulas referencing Model_Output ---
    ws = summary_ws

    data_last_row = len(model) + 1  # header is row 1, so data runs from row 2 to this row

    ws["A1"] = "Nigeria Tomato PHL - Headline Summary (live formulas)"
    ws["A1"].font = TITLE_FONT

    rows = [
        ("Total annual production (tonnes, corridor states modeled)",
         "=SUM(State_Production!E2:E10)"),
        ("Total tonnes lost (baseline)", f"=SUM(Model_Output!G2:G{data_last_row})"),
        ("Overall loss rate (%)", "=B3/B2"),
        ("Total value lost - baseline (NGN)", f"=SUM(Model_Output!H2:H{data_last_row})"),
        ("Total value lost - with cold-chain fix (NGN)", f"=SUM(Model_Output!K2:K{data_last_row})"),
        ("Total NGN saved per year with cold-chain fix", f"=SUM(Model_Output!M2:M{data_last_row})"),
        ("Cold-chain intervention effect size used", "30% loss reduction (Source S8: Ohagwu et al. 2021)"),
    ]
    for i, (label, formula) in enumerate(rows, start=2):
        ws.cell(row=i, column=1, value=label).font = BASE_FONT
        c = ws.cell(row=i, column=2, value=formula)
        c.font = BASE_FONT
        if "NGN" in label or "value" in label.lower() or "saved" in label.lower():
            c.number_format = '#,##0'
        if "rate" in label.lower():
            c.number_format = '0.0%'

    ws["A10"] = "Loss by stage (baseline, NGN) - use for stacked bar chart"
    ws["A10"].font = HEADER_FONT
    stage_names = stages["stage"].tolist()
    ws.cell(row=11, column=1, value="Stage").font = HEADER_FONT
    ws.cell(row=11, column=2, value="Naira Lost").font = HEADER_FONT
    for i, stage in enumerate(stage_names, start=12):
        ws.cell(row=i, column=1, value=stage).font = BASE_FONT
        formula = f'=SUMIFS(Model_Output!H2:H{data_last_row},Model_Output!D2:D{data_last_row},A{i})'
        c = ws.cell(row=i, column=2, value=formula)
        c.number_format = '#,##0'

    start_state_row = 12 + len(stage_names) + 2
    ws.cell(row=start_state_row - 1, column=1, value="Loss by state (baseline, NGN) - use for bar/map chart").font = HEADER_FONT
    ws.cell(row=start_state_row, column=1, value="State").font = HEADER_FONT
    ws.cell(row=start_state_row, column=2, value="Naira Lost").font = HEADER_FONT
    state_names = production["state"].tolist()
    for i, state in enumerate(state_names, start=start_state_row + 1):
        ws.cell(row=i, column=1, value=state).font = BASE_FONT
        formula = f'=SUMIFS(Model_Output!H2:H{data_last_row},Model_Output!A2:A{data_last_row},A{i})'
        c = ws.cell(row=i, column=2, value=formula)
        c.number_format = '#,##0'

    wb.save(OUT_PATH)
    print(f"Workbook written to {OUT_PATH}")
    print(
        "Next: run this file through the xlsx skill's recalc.py to populate cached "
        "formula values, then re-run scripts/fix_widths_after_recalc.py, since "
        "LibreOffice's recalculation step is known to drop column widths on some "
        "numeric columns as a side effect of resaving."
    )


if __name__ == "__main__":
    build()
