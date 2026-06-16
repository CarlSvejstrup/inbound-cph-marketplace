#!/usr/bin/env python3
"""Slim a Google Ads search-terms report down to the few fields a human judgement needs.

THE PHILOSOPHY (decided with Carl 2026-06-16, after the optimering-loop sweep got too heavy):

    The hard part of a search-terms analysis was never the data volume — a 200-term account
    is a few thousand tokens. The hard part is JUDGEMENT (is this our city? do people call on
    this term? is this a competitor name?). Judgement belongs to the model, with the right
    context and rules — NOT to a deterministic script. So this module does the ONE thing a
    script should: take the report, throw away the bytes that don't help a human decide, and
    hand back a small clean list. No classification, no offering-overlap, no keyword-map join,
    no sweep. The model reads the whole slim list and judges it in one pass.

This is the deliberate opposite of optimering-loop/lib/sweep.py: that module made the calls in
code (and mis-flagged on-offering local traffic as waste because "0 conversions" is wrong on a
lead-gen account where people phone). Here the script only SLIMS; the model JUDGES.

Input: rows from the MCP `get_search_terms_report` tool (preferred — already pre-aggregated and
already carries the "already a keyword?" status) OR raw `search_term_view` GAQL rows (fallback).
Both shapes are accepted; the heavy `resource_name` strings that bloated the old GAQL path are
dropped here, before anything reaches context.

Output: a list of flat dicts, one per term, sorted by cost desc:
    {term, ad_group, campaign, clicks, impressions, cost_dkk, conversions, ctr_pct, cpa_dkk,
     already_keyword (bool|None), keyword_match_type (str|None)}
The model adds `verdict` + `reason` per row downstream; this module never sets them.
"""
from __future__ import annotations

import re

# Spend floor is OPTIONAL and only to tame a huge account. For a typical ~200-term account leave
# it at 0 — the whole point is that the model can read every term. The floor never makes a
# judgement; it only drops rows too small to be worth a human's eyes when the list is enormous.
DEFAULT_SPEND_FLOOR_DKK = 0


def _num(v) -> float:
    """Metrics arrive as int/float/str/None across the report + GAQL shapes; coerce safely."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _ctr(clicks, impressions):
    c, i = _num(clicks), _num(impressions)
    return round(c / i * 100, 1) if i else ""


def _cpa(cost_dkk, conversions):
    cost, conv = _num(cost_dkk), _num(conversions)
    return round(cost / conv, 0) if conv else ""


def _name(raw: dict, *keys) -> str:
    """First non-empty value across the given keys. A key may resolve to a flat string (report
    shape: 'campaign_name') OR a nested {name: ...} object (GAQL shape: 'campaign'). Returns ''."""
    for k in keys:
        v = raw.get(k)
        if isinstance(v, dict):
            v = v.get("name")
        if v:
            return str(v)
    return ""


def _looks_like_micros(cost_raw, cost_field_name) -> bool:
    """Raw GAQL returns cost in micros (cost_micros); the MCP report returns DKK already.
    Decide by field name first, fall back to magnitude (a single search term costing > 1e5
    'currency units' is implausible; that's micros)."""
    if cost_field_name and "micros" in cost_field_name:
        return True
    return _num(cost_raw) > 100_000


def _one_row(raw: dict) -> dict | None:
    """Normalise ONE report/GAQL row into the slim shape. Returns None if it carries no term.

    Accepts three field conventions seen in practice:
      - MCP get_search_terms_report: flat keys (search_term/query, campaign_name, ad_group_name,
        clicks, impressions, cost/cost_micros, conversions, status/added/keyword_status).
      - raw search_term_view GAQL: nested under search_term_view / campaign / ad_group / metrics.
      - already-lowercased flat dicts (our own fixtures).
    """
    # --- term ---
    term = (raw.get("search_term") or raw.get("query") or raw.get("searchTerm")
            or raw.get("search_term_view", {}).get("search_term") or raw.get("term") or "")
    term = str(term).strip()
    if not term:
        return None

    # --- identity --- (flat report keys win; fall back to nested GAQL objects)
    campaign = _name(raw, "campaign_name", "campaignName", "campaign")
    ad_group = _name(raw, "ad_group_name", "adGroupName", "ad_group")

    # --- metrics (report shape is flat; GAQL is under "metrics") ---
    m = raw.get("metrics", raw)
    clicks = int(_num(m.get("clicks")))
    impressions = int(_num(m.get("impressions")))
    conversions = round(_num(m.get("conversions")), 1)
    # cost: report gives "cost" in DKK; GAQL gives "cost_micros".
    cost_field = "cost_micros" if ("cost_micros" in m or "costMicros" in m) else "cost"
    cost_raw = m.get("cost_micros", m.get("costMicros", m.get("cost", m.get("cost_dkk", 0))))
    cost_dkk = _num(cost_raw)
    if _looks_like_micros(cost_raw, cost_field):
        cost_dkk = cost_dkk / 1_000_000
    cost_dkk = round(cost_dkk, 2)

    # --- already-a-keyword status (the report carries this; GAQL does not) ---
    # The MCP report marks terms that have been added as keywords. Field name varies, so probe a
    # few; "status" == "ADDED" / added==True / a non-empty added_keyword all mean "already a kw".
    already = None
    match_type = raw.get("keyword_match_type") or raw.get("match_type") or None
    status = str(raw.get("status") or raw.get("search_term_status") or raw.get("keyword_status") or "").upper()
    if raw.get("added") is True or raw.get("is_keyword") is True or status in {"ADDED", "ADDED_EXCLUDED"}:
        already = True
    elif raw.get("added") is False or raw.get("is_keyword") is False or status in {"NONE", "UNKNOWN", "NOT_ADDED"}:
        already = False
    # status "EXCLUDED" means it's already a NEGATIVE — also "don't suggest as new".
    if status in {"EXCLUDED", "ADDED_EXCLUDED"}:
        already = True

    return {
        "term": term,
        "ad_group": str(ad_group or ""),
        "campaign": str(campaign or ""),
        "clicks": clicks,
        "impressions": impressions,
        "cost_dkk": cost_dkk,
        "conversions": conversions,
        "ctr_pct": _ctr(clicks, impressions),
        "cpa_dkk": _cpa(cost_dkk, conversions),
        "already_keyword": already,
        "keyword_match_type": match_type,
    }


def slim(report_rows: list, spend_floor_dkk: float = DEFAULT_SPEND_FLOOR_DKK) -> dict:
    """Slim the report to the judgement-relevant fields. Returns:
        {"terms": [...slim dicts sorted by cost desc...],
         "dropped_below_floor": int,        # how many rows the floor removed (0 if floor=0)
         "total_terms_in_report": int}
    The model reads `terms` in full. `dropped_below_floor` is surfaced so a non-zero floor is
    never a silent truncation (Carl's no-silent-caps rule)."""
    out, dropped = [], 0
    for raw in report_rows or []:
        row = _one_row(raw if isinstance(raw, dict) else {})
        if row is None:
            continue
        if spend_floor_dkk and row["cost_dkk"] < spend_floor_dkk:
            dropped += 1
            continue
        out.append(row)
    out.sort(key=lambda r: -r["cost_dkk"])
    return {
        "terms": out,
        "dropped_below_floor": dropped,
        "total_terms_in_report": len([r for r in (report_rows or []) if isinstance(r, dict)]),
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path
    ap = argparse.ArgumentParser(description="Slim a get_search_terms_report dump to judgement fields.")
    ap.add_argument("--in", dest="inp", required=True, help="JSON file: a list of report rows (or {results:[...]})")
    ap.add_argument("--out", required=True, help="output JSON path for the slim list")
    ap.add_argument("--spend-floor", type=float, default=DEFAULT_SPEND_FLOOR_DKK,
                    help="optional DKK floor; only to tame a huge account (default 0 = keep all)")
    args = ap.parse_args()
    payload = json.loads(Path(args.inp).read_text())
    rows = payload.get("results", payload) if isinstance(payload, dict) else payload
    result = slim(rows, args.spend_floor)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Slimmed {result['total_terms_in_report']} report rows -> {len(result['terms'])} terms "
          f"({result['dropped_below_floor']} dropped below {args.spend_floor} DKK floor). Wrote {args.out}")
