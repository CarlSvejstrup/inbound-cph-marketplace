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

COLUMNS = ["Søgeterm", "Kampagne", "Ad group", "Budget brugt (DKK)", "Impressions", "Klik",
           "CTR (%)", "Konverteringer", "CPA (DKK)", "Allerede keyword?", "Dom", "Begrundelse"]
WRAP_COLS = {"Begrundelse"}


def _fill(hexv):
    return PatternFill(start_color=hexv, end_color=hexv, fill_type="solid")


def _already(v):
    if v is True:
        return "ja"
    if v is False:
        return "nej"
    return ""


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
            "Budget brugt (DKK)": t.get("cost_dkk", ""),
            "Impressions": t.get("impressions", ""),
            "Klik": t.get("clicks", ""),
            "CTR (%)": t.get("ctr_pct", ""),
            "Konverteringer": t.get("conversions", ""),
            "CPA (DKK)": t.get("cpa_dkk", ""),
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
    widths = [30, 26, 22, 16, 12, 8, 9, 14, 10, 15, 16, 52]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

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
