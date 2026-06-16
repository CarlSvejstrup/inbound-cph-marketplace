#!/usr/bin/env python3
"""Build the søgeterm-analyse deliverable: ONE flat colour-coded list (.xlsx).

Carl's call (2026-06-16): not the optimering-loop 8-tab workbook. ONE sheet, every term on one
blade, coloured by the model's verdict, with a short Danish reason — the way a Google Ads expert
actually reads a search-terms report. No overview/QS/skipped tabs. A small legend up top so the
colours are self-explanatory, and real Æ Ø Å throughout.

Input: the model's judged terms (slim rows + a `verdict` + `reason` the model added). Output: one
styled .xlsx. This builder makes NO judgement — it only renders what the model decided.

The five verdicts (the model assigns exactly one per term):
    VINDER       — converts / strong intent, not yet its own keyword -> promote
    RELEVANT     — on-offering, already well covered -> leave it
    NEGATIV      — should be blocked (off-offering, wrong intent, junk)
    FORKERT_PLACERET — relevant but in the wrong ad group / match -> restructure
    GRAENSE      — borderline, needs a human eye
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _ensure_openpyxl():
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "openpyxl"], check=True)


_ensure_openpyxl()
import openpyxl  # noqa: E402
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

NAVY = "1F2A44"
NAVY_TEXT = "FFFFFF"
BAND = "F4F6FA"
HEADER_FILL = PatternFill(start_color=NAVY, end_color=NAVY, fill_type="solid")
HEADER_FONT = Font(bold=True, color=NAVY_TEXT, size=11)
TITLE_FONT = Font(bold=True, size=14, color=NAVY)
BODY_FONT = Font(size=11, color="1F2A44")
_THIN = Side(style="thin", color="D6DBE6")
BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
HEAD_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
WRAP = Alignment(horizontal="left", vertical="top", wrap_text=True)
TOP = Alignment(horizontal="left", vertical="top")

# One verdict -> one fill. Same pastel language as the rest of the suite so it reads consistently.
VERDICT_FILL = {
    "VINDER":           "D6EFD6",   # green
    "RELEVANT":         "D6E4F5",   # blue
    "FORKERT_PLACERET": "FCE4C8",   # orange
    "NEGATIV":          "F6D6D6",   # red
    "GRAENSE":          "E6E6E6",   # grey
}
VERDICT_LABEL = {
    "VINDER": "VINDER — konverterer / stærk intention, endnu ikke eget keyword → promovér",
    "RELEVANT": "RELEVANT — passer tilbuddet, allerede godt dækket → lad den være",
    "FORKERT_PLACERET": "FORKERT PLACERET — relevant, men forkert ad group / match → omstrukturér",
    "NEGATIV": "NEGATIV — bør blokeres (uden for tilbuddet, forkert intention, junk)",
    "GRAENSE": "GRÆNSE — grænsetilfælde, kræver et menneskeligt skøn",
}

# Main-sheet columns. Match type + Level sit on the main sheet so the auto-derived Negativ/Vinder
# sheets (and the future editor-csv-export bridge) have every Editor field they need without a
# second pass. Dom is the column the human edits; the two derived sheets FILTER on it.
COLUMNS = ["Søgeterm", "Kampagne", "Ad group", "Triggerende keyword", "Keyword match type",
           "Budget brugt (DKK)", "Impressions", "Klik", "CTR (%)", "Konverteringer", "CPA (DKK)",
           "Match type", "Level", "Allerede keyword?", "Dom", "Begrundelse"]
WRAP_COLS = {"Begrundelse"}
DOM_COL = "Dom"   # the column the derived sheets filter on


def _fill(hexv):
    return PatternFill(start_color=hexv, end_color=hexv, fill_type="solid")


def _already(v):
    if v is True:
        return "ja"
    if v is False:
        return "nej"
    return ""


def _filter_sheet(wb, title, src_title, data_first, data_last, verdict, col_map, constants=None):
    """Create a sheet whose rows are a live Google-Sheets FILTER of the main sheet, keeping only
    rows where the main sheet's Dom column == `verdict`. Updates automatically when the user edits
    Dom in Google Sheets (the chosen edit surface).

    title:     sheet name — use editor-csv-export's exact alias so the CSV bridge needs no rework.
    src_title: the main sheet's title (quoted in the formula).
    col_map:   [(editor_header, src_col_letter_or_None), ...] mapping main columns -> Editor names.
               A None src means the column is a constant (see constants).
    constants: {editor_header: literal} for non-column columns (e.g. Status="Paused").

    Each column gets ONE FILTER() in row 2 that spills down. The Dom condition column on the main
    sheet is fixed (column M = 13 in COLUMNS). A constant column uses the SAME filter shape so it
    spills to identical height: FILTER(IF(<dom range>=v, "Paused", ), <dom range>=v).
    """
    constants = constants or {}
    ws = wb.create_sheet(title)
    sq = src_title.replace("'", "''")           # escape single quotes for the sheet ref
    dom_col = get_column_letter(COLUMNS.index(DOM_COL) + 1)   # main-sheet Dom column letter
    dom_rng = f"'{sq}'!{dom_col}{data_first}:{dom_col}{data_last}"
    cond = f'{dom_rng}="{verdict}"'

    # A short note above the table so a human opening the sheet understands it is auto-derived.
    ws["A1"] = (f"Auto-genereret fra 'Søgetermer' (Dom = {verdict}). Ret Dom på hovedfanen, "
                f"så opdaterer denne sig selv i Google Sheets.")
    ws["A1"].font = Font(italic=True, size=10, color="606060")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(len(col_map), 2))

    header_row = 2
    for c, (hdr, _src) in enumerate(col_map, start=1):
        cell = ws.cell(row=header_row, column=c, value=hdr)
        cell.fill = HEADER_FILL; cell.font = HEADER_FONT
        cell.alignment = HEAD_ALIGN; cell.border = BORDER
    ws.row_dimensions[header_row].height = 22

    formula_row = header_row + 1
    for c, (hdr, src) in enumerate(col_map, start=1):
        letter = get_column_letter(c)
        if src is None:                          # constant column, spilled to match height
            lit = constants.get(hdr, "")
            f = f'=FILTER(IF({cond},"{lit}",),{cond})'
        else:
            src_rng = f"'{sq}'!{src}{data_first}:{src}{data_last}"
            f = f'=FILTER({src_rng},{cond})'
        ws.cell(row=formula_row, column=c, value=f)

    widths = [26, 16, 22, 30, 14]
    for i in range(1, len(col_map) + 1):
        ws.column_dimensions[get_column_letter(i)].width = widths[i - 1] if i - 1 < len(widths) else 18
    ws.freeze_panes = ws.cell(row=formula_row, column=1).coordinate
    return ws


def build(data, out_path):
    """data = {client, account_id, period, today, scope, conversion_note, terms:[...]}
    Each term: slim fields + verdict + reason (+ optional match-type display)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Søgetermer"

    client = data.get("client", "")
    terms = data.get("terms", [])

    # --- header band: title + context + legend, then the table. Row 1..N are meta, table follows.
    ws["A1"] = f"Søgeterm-analyse — {client}"
    ws["A1"].font = TITLE_FONT
    meta = [
        f"Konto: {data.get('account_id','')}    Periode: {data.get('period','')}    "
        f"Scope: {data.get('scope','hele kontoen')}    Genereret: {data.get('today','')}",
    ]
    if data.get("conversion_note"):
        meta.append(data["conversion_note"])
    meta.append("")
    meta.append("Farvekoder (dom pr. række):")
    r = 2
    for line in meta:
        ws.cell(row=r, column=1, value=line).font = BODY_FONT
        r += 1
    # legend swatches
    for key in ["VINDER", "RELEVANT", "FORKERT_PLACERET", "NEGATIV", "GRAENSE"]:
        sw = ws.cell(row=r, column=1, value="")
        sw.fill = _fill(VERDICT_FILL[key]); sw.border = BORDER
        lab = ws.cell(row=r, column=2, value=VERDICT_LABEL[key]); lab.font = BODY_FONT
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
        r += 1
    r += 1  # spacer

    # --- table header ---
    header_row = r
    for c, h in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=header_row, column=c, value=h)
        cell.fill = HEADER_FILL; cell.font = HEADER_FONT
        cell.alignment = HEAD_ALIGN; cell.border = BORDER
    ws.row_dimensions[header_row].height = 26

    # --- rows, whole-row coloured by verdict ---
    wrap_idx = {i for i, h in enumerate(COLUMNS, start=1) if h in WRAP_COLS}
    for i, t in enumerate(terms):
        rr = header_row + 1 + i
        verdict = str(t.get("verdict", "")).upper()
        fill = VERDICT_FILL.get(verdict)
        row_vals = {
            "Søgeterm": t.get("term", ""),
            "Kampagne": t.get("campaign", ""),
            "Ad group": t.get("ad_group", ""),
            "Triggerende keyword": t.get("trigger_keyword", ""),
            "Keyword match type": t.get("trigger_match_type", ""),
            "Budget brugt (DKK)": t.get("cost_dkk", ""),
            "Impressions": t.get("impressions", ""),
            "Klik": t.get("clicks", ""),
            "CTR (%)": t.get("ctr_pct", ""),
            "Konverteringer": t.get("conversions", ""),
            "CPA (DKK)": t.get("cpa_dkk", ""),
            # Editor-bound fields for the derived sheets + the future CSV bridge. Defaults are
            # sensible and editable: negatives default to Phrase + campaign level; a promoted
            # winner defaults to Exact. The agent may override per term in the judged JSON.
            "Match type": t.get("match_type") or ("Exact" if verdict == "VINDER" else "Phrase"),
            "Level": t.get("level") or ("ad_group" if verdict == "VINDER" else "campaign"),
            "Allerede keyword?": _already(t.get("already_keyword")),
            "Dom": verdict,
            "Begrundelse": t.get("reason", ""),
        }
        for c, h in enumerate(COLUMNS, start=1):
            cell = ws.cell(row=rr, column=c, value=row_vals[h])
            cell.border = BORDER
            cell.alignment = WRAP if c in wrap_idx else TOP
            if fill:
                cell.fill = _fill(fill)
            elif rr % 2 == 1:
                cell.fill = _fill(BAND)

    # --- widths + freeze the table header + autofilter over the table ---
    last = header_row + len(terms)
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1).coordinate
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(COLUMNS))}{max(last, header_row)}"
    widths = [30, 22, 18, 24, 14, 14, 10, 7, 8, 12, 9, 11, 10, 13, 14, 46]
    for i in range(1, len(COLUMNS) + 1):
        ws.column_dimensions[get_column_letter(i)].width = widths[i - 1] if i - 1 < len(widths) else 16

    # --- the two auto-derived sheets (Sheets FILTER on the Dom column) ---
    # Named EXACTLY as editor-csv-export's tab aliases so the CSV bridge is zero-rework later, and
    # carrying the Editor column contract. Live FILTER() = they update when the user edits Dom in
    # Google Sheets. NOTE: openpyxl cannot READ a spilled FILTER result (formulas aren't evaluated
    # offline) — so the CSV bridge must RE-MATERIALISE these from the edited Dom column at export
    # time, reading the main sheet's hand-typed Dom cells (which openpyxl CAN read). That keeps the
    # sheet live for the human AND correct for the converter; it is not a silent trap.
    # Source column letters are derived from COLUMNS so they stay correct if the layout changes.
    def _col(name):
        return get_column_letter(COLUMNS.index(name) + 1)
    data_first = header_row + 1
    data_last = header_row + len(terms)
    _filter_sheet(
        wb, "Negative keywords", ws.title, data_first, data_last, "NEGATIV",
        # (display header, source column letter on the main sheet) — maps main cols -> Editor names
        [("Campaign", _col("Kampagne")), ("Level", _col("Level")), ("Ad group", _col("Ad group")),
         ("Negative keyword", _col("Søgeterm")), ("Match type", _col("Match type"))],
    )
    _filter_sheet(
        wb, "Nye keywords (vindere)", ws.title, data_first, data_last, "VINDER",
        [("Campaign", _col("Kampagne")), ("Ad group", _col("Ad group")), ("Keyword", _col("Søgeterm")),
         ("Match type", _col("Match type")), ("Status", None)],  # Status constant ("Paused")
        constants={"Status": "Paused"},
    )

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return out_path


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser(description="Build the flat colour-coded søgeterm list (.xlsx).")
    ap.add_argument("--in", dest="inp", required=True, help="judged-terms JSON")
    ap.add_argument("--out", required=True, help="output .xlsx path")
    args = ap.parse_args()
    build(json.loads(Path(args.inp).read_text()), args.out)
    print(f"Wrote {args.out}")
