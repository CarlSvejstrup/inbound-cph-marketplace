#!/usr/bin/env python3
"""Generate template.xlsx for the annoncetekster skill.

Builds Inbound's Google Ads Editor RSA import layout as a real .xlsx so that
=LEN() formulas and red over-length conditional formatting are baked into the
file. The committed template is the single-RSA case (one data row); fill-sheet.py
rebuilds the layout from scratch for N rows when a run produces several RSAs, so
the layout logic itself lives in sheet_layout.py and both scripts share it.

Layout (row 1 = headers, row 2 = single data row):
  Campaign | Ad Group | Ad type | Labels |
  Headline 1 | LEN | ... | Headline 15 | LEN |
  Description 1 | LEN | ... | Description 4 | LEN |
  Path 1 | LEN | Path 2 | LEN |
  Final URL | Final mobile URL

Every text column is followed by a LEN column holding =LEN(<text cell>).
Conditional formatting turns a LEN cell red when it exceeds the field's limit
(headline 30, description 90, path 15).

Run: python3 build-template.py   ->  writes template.xlsx next to this script.
Deterministic: re-running reproduces the same file.
"""
from pathlib import Path

from sheet_layout import COLUMNS, build_sheet, text_cell


def build() -> None:
    """Build the single-row template and save it next to this script."""
    wb, _ws = build_sheet(n_rows=1)
    out = Path(__file__).with_name("template.xlsx")
    wb.save(out)


if __name__ == "__main__":
    build()
    print("Wrote template.xlsx (single RSA, data row 2)")
    print("Data-cell map (field -> A1, row 2):")
    for field in COLUMNS:
        print(f"  {field:18s} {text_cell(field, 2)}")
