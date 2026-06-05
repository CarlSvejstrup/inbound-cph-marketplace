#!/usr/bin/env python3
"""Google Ads Editor CSV builders for the optimization loop's execution stage.

The skills produce review .xlsx; the loop produces Editor-import CSVs. These headers
are the SAME verified Editor schema the assembler uses (validated against Ian's skeleton
+ Editor CSV research 2026-06-03, see
plugins/google-ads-setup/skills/assembler/references/assembler-contract.md section 5):

  keywords.csv  : Campaign, Ad group, Keyword, Match type, Status
  negatives.csv : Campaign, Ad group, Keyword, Match type, Status

The RSA CSV is NOT built here - it is produced by the existing responsive-search-ads
builder via lib/builders/load.build_rsa (47-column Editor RSA shape, length-gated). One
source of truth; we do not re-implement the RSA columns.

Two locked rules carried from the critique + assembler contract:
  - Negatives are recommend-only and human-imported. Editor's green/yellow diff + the
    human's Post IS the approval. This builder writes a local file only.
  - The expansion CSV promotes proven winners to EXACT (control bid + quality). It does
    NOT "aggressively scale" - that judgement is the human's, on a winner that may rest
    on 2-3 conversions (significance discipline).

CSV cells use the explicit `Match type` column (Exact/Phrase), never keyword-text syntax
([kw] / "kw"), so we never double-encode match type (the assembler contract's "pick ONE").
"""
from __future__ import annotations

import csv
from pathlib import Path

KEYWORD_HEADERS = ["Campaign", "Ad group", "Keyword", "Match type", "Status"]
NEGATIVE_HEADERS = ["Campaign", "Ad group", "Keyword", "Match type", "Status"]

# Editor accepts these as the Match type column values.
_MATCH_TYPES = {"EXACT": "Exact", "PHRASE": "Phrase", "BROAD": "Broad"}


def _match_type(raw: str) -> str:
    return _MATCH_TYPES.get((raw or "").strip().upper(), raw or "")


def _write(path: str, headers: list[str], rows: list[list]) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for r in rows:
            w.writerow(r)
    return path


def build_negatives_csv(negatives: list[dict], out_path: str) -> str:
    """Build the negative-keyword Editor CSV from SearchTermFindings.negatives.

    Each negative: {keyword, match_type (EXACT|PHRASE), level (ad_group|campaign|account),
    campaign, ad_group}. Account-level negatives carry a blank Campaign + Ad group (the
    human attaches them to the shared list in Editor). Status = Enabled (a negative being
    active is the point; it is still human-imported, never API-pushed).

    Dedups by (keyword, match_type, campaign, ad_group) so a term flagged by two sources
    does not produce duplicate rows (the assembler-style guard).
    """
    seen = set()
    rows = []
    for n in negatives:
        campaign = n.get("campaign", "") if n.get("level") != "account" else ""
        ad_group = n.get("ad_group", "") if n.get("level") == "ad_group" else ""
        kw = n.get("keyword", "")
        mt = _match_type(n.get("match_type", ""))
        key = (kw, mt, campaign, ad_group or "")
        if key in seen:
            continue
        seen.add(key)
        rows.append([campaign, ad_group, kw, mt, "Enabled"])
    return _write(out_path, NEGATIVE_HEADERS, rows)


def build_keyword_expansion_csv(winners: list[dict], out_path: str) -> str:
    """Build the keyword-expansion Editor CSV from SearchTermFindings.winners.

    Promote proven winners to EXACT. Skip any winner already at exact (already_exact:true)
    - re-adding it is the contradiction the search-terms live test exposed. New keywords
    land Paused so the human reviews bid before they serve (no surprise spend on import).
    Dedups by (keyword, campaign, ad_group).
    """
    seen = set()
    rows = []
    for w in winners:
        if w.get("already_exact"):
            continue
        kw = w.get("term", "")
        campaign = w.get("campaign", "")
        ad_group = w.get("ad_group", "")
        key = (kw, campaign, ad_group)
        if key in seen:
            continue
        seen.add(key)
        rows.append([campaign, ad_group, kw, "Exact", "Paused"])
    return _write(out_path, KEYWORD_HEADERS, rows)
