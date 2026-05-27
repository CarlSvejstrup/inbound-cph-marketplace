#!/usr/bin/env python3
"""Build the search-terms analysis workbook (.xlsx) for the search-terms skill.

Takes the classified analysis as a JSON file and emits a multi-sheet, colour-coded
.xlsx: Overblik, Spild, Vindere, Irrelevante, Nye emner, Raadata. Tab colours,
header fills, and a cost colour-scale on the Spild tab are baked into the .xlsx
layer, so they survive upload to Drive via the connector and need no Sheets API
or gws CLI. Runs in Cowork and locally.

Input JSON schema (all keys optional except where noted; missing lists render empty):
{
  "client": "KFH kloak ApS",
  "date_range": "LAST_30_DAYS",
  "coverage_pct": 94,                       // pulled term cost / account search cost
  "account_cpa": 78.4,                       // null if unreliable
  "account_cpa_reliable": true,
  "low_confidence_flags": ["Kontoen har faa konverteringer ..."],
  "totals": {"spild_kr": 1234.5, "n_spild": 12, "n_vindere": 7,
             "n_irrelevante": 4, "n_nye_emner": 3, "n_terms": 320},
  "top_findings": ["...", "..."],
  "spild":       [{"term","cost","clicks","conv","impr","match_types",
                   "campaigns","niveau","begrundelse"}],
  "irrelevante": [ same shape as spild ],
  "vindere":     [{"term","cost","conv","cpa","account_cpa","campaign",
                   "exists_as_keyword","anbefaling"}],
  "nye_emner":   [{"tema","terms","cost","conv","forslag"}],
  "raadata":     [{"term","cost","clicks","conv","conv_value","impr","cpa",
                   "match_types","campaigns","ad_groups","bucket"}]
}

Run:
  python3 build-sheet.py --in analysis.json --out "Search terms - <klient> - <dato>.xlsx"
"""
import argparse
import json
from pathlib import Path

import openpyxl
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# Inbound palette (matches ads-audit score chips where it overlaps).
RED = "E05252"
GREEN = "3DB069"
ORANGE = "F5A623"
BLUE = "4A90D9"
GREY = "9B9B9B"
NAVY = "1F2A44"
WHITE = "FFFFFF"

HEADER_FONT = Font(bold=True, color=WHITE)
WRAP = Alignment(wrap_text=True, vertical="top")


def _fill(hex_color):
    return PatternFill(start_color=hex_color, end_color=hex_color, fill_type="solid")


def _write_table(ws, headers, rows, header_hex):
    """Write a header row (filled + bold white) then data rows. rows = list of lists."""
    fill = _fill(header_hex)
    for c, head in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=c, value=head)
        cell.fill = fill
        cell.font = HEADER_FONT
        cell.alignment = WRAP
    for r, row in enumerate(rows, start=2):
        for c, val in enumerate(row, start=1):
            ws.cell(row=r, column=c, value=val).alignment = WRAP
    # Reasonable column widths.
    for c in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(c)].width = 22
    ws.freeze_panes = "A2"


def _round(v):
    return round(v, 2) if isinstance(v, (int, float)) else v


def build(data, out_path):
    wb = openpyxl.Workbook()

    # --- Overblik ---
    ws = wb.active
    ws.title = "Overblik"
    t = data.get("totals", {})
    rows = [
        ["Klient", data.get("client", "")],
        ["Datointerval", data.get("date_range", "")],
        ["Coverage (pulled cost / konto search cost)", f"{data.get('coverage_pct', '')}%"],
        ["Konto-CPA (kr)", _round(data.get("account_cpa")) if data.get("account_cpa_reliable") else "ikke paalidelig (faa konv)"],
        ["", ""],
        ["Samlet spild (kr)", _round(t.get("spild_kr"))],
        ["Antal spild-termer", t.get("n_spild")],
        ["Antal vindere", t.get("n_vindere")],
        ["Antal irrelevante", t.get("n_irrelevante")],
        ["Antal nye emner", t.get("n_nye_emner")],
        ["Antal soegetermer i alt", t.get("n_terms")],
    ]
    _write_table(ws, ["Maal", "Vaerdi"], rows, NAVY)
    r = len(rows) + 3
    ws.cell(row=r, column=1, value="Top findings").font = Font(bold=True)
    for i, f in enumerate(data.get("top_findings", []), start=r + 1):
        ws.cell(row=i, column=1, value=f).alignment = WRAP
    flags = data.get("low_confidence_flags", [])
    if flags:
        fr = r + len(data.get("top_findings", [])) + 2
        ws.cell(row=fr, column=1, value="Low-confidence flags").font = Font(bold=True, color=RED)
        for i, f in enumerate(flags, start=fr + 1):
            ws.cell(row=i, column=1, value=f).alignment = WRAP
    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["B"].width = 30

    # --- Spild ---
    ws = wb.create_sheet("Spild")
    ws.sheet_properties.tabColor = RED
    headers = ["Soegeterm", "Cost (kr)", "Klik", "Konv", "Impr", "Match types",
               "Kampagne(r)", "Foreslaaet niveau (forslag)", "Begrundelse"]
    rows = [[x.get("term"), _round(x.get("cost")), x.get("clicks"), x.get("conv"),
             x.get("impr"), x.get("match_types"), x.get("campaigns"),
             x.get("niveau"), x.get("begrundelse")] for x in data.get("spild", [])]
    _write_table(ws, headers, rows, RED)
    if rows:
        rng = f"B2:B{len(rows) + 1}"  # cost colour-scale
        ws.conditional_formatting.add(rng, ColorScaleRule(
            start_type="min", start_color="FCE4E4",
            end_type="max", end_color=RED))

    # --- Vindere ---
    ws = wb.create_sheet("Vindere")
    ws.sheet_properties.tabColor = GREEN
    headers = ["Soegeterm", "Cost (kr)", "Konv", "CPA (kr)", "Konto-CPA",
               "Kampagne", "Eksisterer som keyword?", "Anbefaling"]
    rows = [[x.get("term"), _round(x.get("cost")), x.get("conv"), _round(x.get("cpa")),
             _round(x.get("account_cpa")), x.get("campaign"),
             x.get("exists_as_keyword"), x.get("anbefaling")] for x in data.get("vindere", [])]
    _write_table(ws, headers, rows, GREEN)

    # --- Irrelevante ---
    ws = wb.create_sheet("Irrelevante")
    ws.sheet_properties.tabColor = ORANGE
    headers = ["Soegeterm", "Cost (kr)", "Klik", "Konv", "Impr", "Match types",
               "Kampagne(r)", "Foreslaaet niveau (forslag)", "Begrundelse"]
    rows = [[x.get("term"), _round(x.get("cost")), x.get("clicks"), x.get("conv"),
             x.get("impr"), x.get("match_types"), x.get("campaigns"),
             x.get("niveau"), x.get("begrundelse")] for x in data.get("irrelevante", [])]
    _write_table(ws, headers, rows, ORANGE)

    # --- Nye emner ---
    ws = wb.create_sheet("Nye emner")
    ws.sheet_properties.tabColor = BLUE
    headers = ["Tema", "Soegetermer i temaet", "Samlet cost (kr)", "Samlet konv", "Forslag"]
    rows = [[x.get("tema"), x.get("terms"), _round(x.get("cost")), x.get("conv"),
             x.get("forslag")] for x in data.get("nye_emner", [])]
    _write_table(ws, headers, rows, BLUE)

    # --- Raadata ---
    ws = wb.create_sheet("Raadata")
    ws.sheet_properties.tabColor = GREY
    headers = ["Soegeterm", "Cost (kr)", "Klik", "Konv", "Konv-vaerdi", "Impr", "CPA",
               "Match types", "Kampagne(r)", "Annoncegruppe(r)", "Bucket"]
    rows = [[x.get("term"), _round(x.get("cost")), x.get("clicks"), x.get("conv"),
             _round(x.get("conv_value")), x.get("impr"), _round(x.get("cpa")),
             x.get("match_types"), x.get("campaigns"), x.get("ad_groups"),
             x.get("bucket")] for x in data.get("raadata", [])]
    _write_table(ws, headers, rows, GREY)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="analysis JSON path")
    ap.add_argument("--out", dest="out", required=True, help="output .xlsx path")
    args = ap.parse_args()
    data = json.loads(Path(args.inp).read_text(encoding="utf-8"))
    path = build(data, args.out)
    print(path)


if __name__ == "__main__":
    main()
