#!/usr/bin/env python3
"""Build the annonce-optimering diagnostic workbook (.xlsx).

This skill is a POST-LAUNCH ASSET-HYGIENE diagnostic, not a profit classifier.
It was deliberately reshaped after a live test against real Inbound accounts
(2026-05-29) proved two things:

  1. Google's per-asset performance_label comes back NOT_APPLICABLE / PENDING on
     Inbound's accounts (too low volume) - never BEST/GOOD/LOW. So the label
     cannot be the primary signal.
  2. Per-asset CTR/CVR from ad_group_ad_asset_view is confounded: an RSA serves
     ~3 headlines + 2 descriptions per impression and the same click/conversion
     is attributed to EVERY served asset. Per-asset CVR therefore cannot carry a
     four-quadrant Winners/Hidden Gems/Money Pits/Losers matrix, and the
     conversion counts (0/1/2 per asset) are far below significance anyway.

So this workbook reports STRUCTURAL FACTS that hold without significance:
  - champion-challenger coverage (RSAs per ad group; <2 = build a challenger),
  - dead-weight assets (never-served / near-zero impressions = a coverage fact),
  - angle-coverage gaps per ad group (which angles have no served asset),
  - Google's label ONLY when it is BEST/GOOD/LOW (else "ikke nok data endnu"),
  - an optional CVR hint gated behind a hard significance floor (else
    "utilstraekkelig data").

The angle-gap output is the gap-brief fed back into annoncetekster-v2 to write
the next challenger headlines - that is where the build->operate->iterate loop
closes.

Colours, header style, freeze panes are baked into the .xlsx layer so they
survive upload to Drive and render when opened in Google Sheets. No gws /
Sheets API. Runs in Cowork and locally.

Input JSON schema (lists may be empty; missing keys render blank):
{
  "client": "Dansk Studie Center",
  "account_id": "3069826320",
  "period": "1. maj 2026 - 29. maj 2026",
  "scope": "Kun aktive Search-kampagner og aktive RSA'er",
  "min_impressions": 50,                 // the dead-weight / significance floor, surfaced in Oversigt
  "method_notes": ["Data via GAQL ad_group_ad_asset_view ...", ...],

  // Per ad group: RSA count + coverage flag (champion-challenger).
  "ad_groups": [
    {"kampagne": "...", "ad_group": "...", "rsa_count": 1,
     "challenger_flag": true,            // true when rsa_count < 2
     "manglende_vinkler": ["urgency", "CTA"]}   // angles with no served asset -> gap-brief
  ],

  // Per asset row (headline/description).
  "assets": [
    {"kampagne","ad_group","felt_type","tekst","vinkel",
     "impressions","clicks","cost",
     "google_label",          // shown only if BEST/GOOD/LOW; else rendered as the "ikke nok data" note
     "status",                // "DOEDVAEGT" | "AKTIV" | "FOR_NY"
     "cvr_hint",              // "" or a value only when significance floor passed; else "utilstraekkelig data"
     "anbefaling"}            // recommend-only text
  ],

  // Synthesised gap-brief for annoncetekster-v2 (angles missing a served asset, per ad group).
  "gap_brief": [
    {"kampagne","ad_group","manglende_vinkler","forslag"}
  ]
}

Run:
  python3 build-sheet.py --in analysis.json --out "Annonce-optimering - <klient> - <dato>.xlsx"
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def _ensure_openpyxl():
    """Import openpyxl, pip-installing it if missing, so this runs on any
    machine with Python 3 + pip (same self-bootstrap as the annoncetekster
    scripts)."""
    try:
        import openpyxl  # noqa: F401
        return
    except ImportError:
        pass
    print("openpyxl not found - installing...", file=sys.stderr)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "openpyxl>=3.1"],
        check=True,
    )


_ensure_openpyxl()
import openpyxl  # noqa: E402
from openpyxl.styles import Alignment, Font, PatternFill  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

HEADER_BG = "1F4E78"
HEADER_FG = "FFFFFF"
# Status colours: dead weight = red, active = green, too-new = blue.
STATUS_FILL = {
    "DOEDVAEGT": "FFC7CE",
    "AKTIV": "C6EFCE",
    "FOR_NY": "D9E1F2",
}
# Google label colours, only used when a real BEST/GOOD/LOW is present.
LABEL_FILL = {
    "BEST": "C6EFCE",
    "GOOD": "A9D08E",
    "LOW": "FFC7CE",
}
FLAG_FILL = "FFEB9C"  # yellow for challenger flags / missing angles

HEADER_FONT = Font(bold=True, color=HEADER_FG)
TITLE_FONT = Font(bold=True, size=16)
SECTION_FONT = Font(bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")

AG_HEADERS = [
    "Kampagne", "Ad group", "Antal aktive RSA", "Byg challenger?",
    "Manglende vinkler (gap-brief)",
]
AG_KEYS = ["kampagne", "ad_group", "rsa_count", "challenger_flag", "manglende_vinkler"]
AG_WIDTHS = [26, 24, 16, 16, 40]

ASSET_HEADERS = [
    "Kampagne", "Ad group", "Felt", "Tekst", "Vinkel",
    "Impressions", "Klik", "Spend (DKK)", "Google-label", "Status",
    "CVR-indikation", "Anbefaling",
]
ASSET_KEYS = [
    "kampagne", "ad_group", "felt_type", "tekst", "vinkel",
    "impressions", "clicks", "cost", "google_label", "status",
    "cvr_hint", "anbefaling",
]
ASSET_WIDTHS = [22, 22, 12, 40, 14, 12, 8, 12, 14, 12, 18, 50]

GAP_HEADERS = ["Kampagne", "Ad group", "Manglende vinkler", "Forslag til challenger"]
GAP_KEYS = ["kampagne", "ad_group", "manglende_vinkler", "forslag"]
GAP_WIDTHS = [24, 24, 30, 56]

LABEL_NOTE = "Google har ikke nok data endnu"
CVR_NOTE = "utilstraekkelig data"


def _fill(hex_color):
    return PatternFill(start_color=hex_color, end_color=hex_color, fill_type="solid")


def _round(v):
    return round(v, 2) if isinstance(v, (int, float)) else v


def _join(v):
    return ", ".join(v) if isinstance(v, (list, tuple)) else v


def _header_row(ws, headers, widths):
    fill = _fill(HEADER_BG)
    for c, head in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=c, value=head)
        cell.fill = fill
        cell.font = HEADER_FONT
        cell.alignment = WRAP
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"


def _oversigt(wb, data):
    ws = wb.active
    ws.title = "Oversigt"
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 60
    ws["A1"] = f"Annonce-optimering - {data.get('client', '')}"
    ws["A1"].font = TITLE_FONT
    meta = [
        ("Konto-ID:", data.get("account_id", "")),
        ("Periode:", data.get("period", "")),
        ("Scope:", data.get("scope", "Kun aktive Search-kampagner og aktive RSA'er")),
        ("Sample-floor (min. impressions):", data.get("min_impressions", "")),
    ]
    r = 2
    for label, val in meta:
        ws.cell(row=r, column=1, value=label).font = SECTION_FONT
        ws.cell(row=r, column=2, value=val)
        r += 1
    r += 1
    # What this report is / is NOT - honesty banner so no one mis-reads it.
    ws.cell(row=r, column=1, value="Hvad rapporten er").font = SECTION_FONT
    r += 1
    for line in [
        "Strukturel asset-hygiejne: RSA-daekning, doedvaegt-assets, vinkel-huller.",
        "Den doemmer IKKE assets paa konverteringsrate - per-asset CVR i Google er",
        "konfunderet (samme klik tilskrives alle serverede assets) og under signifikans.",
        "Google-label vises kun naar den er BEST/GOOD/LOW; ellers 'ikke nok data endnu'.",
        "Alt er anbefalinger - intet redigeres, pauses eller skrives til kontoen.",
    ]:
        ws.cell(row=r, column=1, value=line).alignment = WRAP
        r += 1
    r += 1
    notes = data.get("method_notes", [])
    if notes:
        ws.cell(row=r, column=1, value="Metode & noter").font = SECTION_FONT
        r += 1
        for line in notes:
            ws.cell(row=r, column=1, value=line).alignment = WRAP
            r += 1


def _ad_group_tab(wb, data):
    ws = wb.create_sheet("Ad group-daekning")
    _header_row(ws, AG_HEADERS, AG_WIDTHS)
    for r, row in enumerate(data.get("ad_groups", []), start=2):
        ws.cell(row=r, column=1, value=row.get("kampagne")).alignment = WRAP
        ws.cell(row=r, column=2, value=row.get("ad_group")).alignment = WRAP
        ws.cell(row=r, column=3, value=row.get("rsa_count"))
        flag = bool(row.get("challenger_flag"))
        fc = ws.cell(row=r, column=4, value="JA - byg challenger" if flag else "OK")
        if flag:
            fc.fill = _fill(FLAG_FILL)
        mc = ws.cell(row=r, column=5, value=_join(row.get("manglende_vinkler")))
        mc.alignment = WRAP
        if row.get("manglende_vinkler"):
            mc.fill = _fill(FLAG_FILL)


def _assets_tab(wb, data):
    ws = wb.create_sheet("Assets")
    _header_row(ws, ASSET_HEADERS, ASSET_WIDTHS)
    for r, row in enumerate(data.get("assets", []), start=2):
        for c, key in enumerate(ASSET_KEYS, start=1):
            val = row.get(key)
            if key == "cost":
                val = _round(val)
            if key == "google_label":
                # Only surface a real label; otherwise the honest note.
                val = val if val in LABEL_FILL else LABEL_NOTE
            if key == "cvr_hint" and not val:
                val = CVR_NOTE
            ws.cell(row=r, column=c, value=val).alignment = WRAP
        # Colour the Status cell (col 10).
        status = row.get("status")
        if status in STATUS_FILL:
            ws.cell(row=r, column=10).fill = _fill(STATUS_FILL[status])
        # Colour the Google-label cell (col 9) only when it is a real label.
        label = row.get("google_label")
        if label in LABEL_FILL:
            ws.cell(row=r, column=9).fill = _fill(LABEL_FILL[label])


def _gap_tab(wb, data):
    ws = wb.create_sheet("Gap-brief")
    _header_row(ws, GAP_HEADERS, GAP_WIDTHS)
    for r, row in enumerate(data.get("gap_brief", []), start=2):
        ws.cell(row=r, column=1, value=row.get("kampagne")).alignment = WRAP
        ws.cell(row=r, column=2, value=row.get("ad_group")).alignment = WRAP
        ws.cell(row=r, column=3, value=_join(row.get("manglende_vinkler"))).alignment = WRAP
        ws.cell(row=r, column=4, value=row.get("forslag")).alignment = WRAP


def build(data, out_path):
    wb = openpyxl.Workbook()
    _oversigt(wb, data)
    _ad_group_tab(wb, data)
    _assets_tab(wb, data)
    _gap_tab(wb, data)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="analysis JSON path")
    ap.add_argument("--out", dest="out", required=True, help="output .xlsx path")
    args = ap.parse_args()
    data = json.loads(Path(args.inp).read_text(encoding="utf-8"))
    print(build(data, args.out))


if __name__ == "__main__":
    main()
