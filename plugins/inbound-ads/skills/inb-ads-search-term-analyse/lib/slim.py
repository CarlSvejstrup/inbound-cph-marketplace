#!/usr/bin/env python3
"""Slim a Google Ads search-terms pull down to the few fields a judgement needs.

THE PHILOSOPHY:

    A search-terms analysis is not a big-data problem — it is a JUDGEMENT problem (is this our
    city? do people call on this term? is this a competitor name?). Judgement belongs to the
    model, with the right context and rules — NOT to a deterministic script. So this module does
    the ONE thing a script should: take the rows, throw away the bytes that don't help a decision,
    and hand back a small clean list. No classification, no verdicts. The script SLIMS; the model
    (with the human, in conversation) JUDGES.

    Lightness is the other job. An unfiltered account can be 1000+ terms — far too much to read
    in context. The real lever against that is the SERVER-SIDE filter in the GAQL WHERE clause
    (see `where_predicate`), which shrinks the payload before it leaves the API. This module then
    compresses further: it drops the heavy `resource_name` strings and, optionally, AGGREGATES the
    same term that recurs across ad groups into one weighed row. Downstream, `digest.py` rolls the
    slim list into a compact insight brief so the ongoing conversation never carries raw rows.

Input: rows from the MCP `get_search_terms_report` tool (already pre-aggregated, carries the
"already a keyword?" status) OR raw `search_term_view` GAQL rows. Both shapes are accepted.

Output: a list of flat dicts, one per term, sorted by cost desc:
    {term, ad_group, campaign, clicks, impressions, cost_dkk, conversions, ctr_pct, cpa_dkk,
     already_keyword (bool|None), keyword_match_type, trigger_keyword, trigger_match_type}
"""
from __future__ import annotations

import re

# Spend floor is OPTIONAL and only to tame a huge account. For a typical ~200-term account leave
# it at 0 — the whole point is that the model can read every term. The floor never makes a
# judgement; it only drops rows too small to be worth a human's eyes when the list is enormous.
DEFAULT_SPEND_FLOOR_DKK = 0

# The RECOMMENDED default threshold for the heavy (>30-day GAQL) path: 50 kr of spend. Spend is
# what defines waste/winners, so a cost floor is the safe default (an impressions floor can drop a
# high-spend, low-impression term). The threshold is chosen at runtime via the intake question.
DEFAULT_COST_FLOOR_DKK = 50


def where_predicate(dimension: str, value) -> str:
    """Build the GAQL WHERE predicate for the runtime-chosen filter threshold. This is the
    EFFICIENT, server-side filter (it shrinks the payload before it leaves the API — that is what
    fixed the slow pull). The agent appends the returned string to the search_term_view query.

        where_predicate("cost", 50)         -> "metrics.cost_micros >= 50000000"
        where_predicate("impressions", 100) -> "metrics.impressions >= 100"
        where_predicate("all", None)        -> "metrics.cost_micros > 0"   (no floor, heavy)

    dimension: "cost" (DKK) | "impressions" | "all" (no threshold, just drop 0-spend).
    Cost is the recommended default; "all" is the heavy long-tail pull (warn the user).
    """
    dim = (dimension or "cost").strip().lower()
    if dim == "impressions":
        n = max(0, int(_num(value)))
        return f"metrics.impressions >= {n}"
    if dim in ("all", "none", "0"):
        return "metrics.cost_micros > 0"
    kr = _num(value) if value is not None else DEFAULT_COST_FLOOR_DKK
    return f"metrics.cost_micros >= {int(kr * 1_000_000)}"


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


def _id(raw: dict, *keys) -> str:
    """First non-empty ID across the given keys. A key may resolve to a flat string/number
    (report shape: 'campaign_id') OR a nested {id: ...} object (GAQL shape: 'campaign'). The MCP
    write tools (add_keywords / add_negative_keywords) target by ID, not name — so we keep these."""
    for k in keys:
        v = raw.get(k)
        if isinstance(v, dict):
            v = v.get("id")
        if v not in (None, ""):
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
    # IDs — needed by the MCP write tools (they target by id, not name).
    campaign_id = _id(raw, "campaign_id", "campaignId", "campaign")
    ad_group_id = _id(raw, "ad_group_id", "adGroupId", "ad_group")

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

    # --- already-a-keyword status ---
    # BOTH sources carry it, in different places:
    #   - MCP get_search_terms_report: flat `search_term_status` ("ADDED"/"NONE"/"EXCLUDED").
    #   - raw search_term_view GAQL: NESTED `search_term_view.status` (same values).
    # ADDED = already a keyword; EXCLUDED = already a negative; both mean "don't suggest as new".
    already = None
    match_type = raw.get("keyword_match_type") or raw.get("match_type") or None
    stv = raw.get("search_term_view", {}) if isinstance(raw.get("search_term_view"), dict) else {}
    status = str(raw.get("status") or raw.get("search_term_status") or raw.get("keyword_status")
                 or stv.get("status") or "").upper()
    if raw.get("added") is True or raw.get("is_keyword") is True or status in {"ADDED", "ADDED_EXCLUDED"}:
        already = True
    elif raw.get("added") is False or raw.get("is_keyword") is False or status in {"NONE", "UNKNOWN", "NOT_ADDED"}:
        already = False
    # status "EXCLUDED" means it's already a NEGATIVE — also "don't suggest as new".
    if status in {"EXCLUDED", "ADDED_EXCLUDED"}:
        already = True

    # --- triggering keyword (WHICH keyword matched this search term + its match type) ---
    # In raw search_term_view GAQL this comes from segments.keyword.info.{text,match_type} (verified
    # live). The flat MCP report doesn't carry it; flat keys probed too for forward-compat.
    seg_kw = {}
    seg = raw.get("segments", {})
    if isinstance(seg, dict):
        seg_kw = (seg.get("keyword", {}) or {}).get("info", {}) or {}
    trigger_keyword = (raw.get("trigger_keyword") or raw.get("triggering_keyword")
                       or seg_kw.get("text") or "")
    trigger_match_type = (raw.get("trigger_match_type") or seg_kw.get("match_type") or match_type or "")

    return {
        "term": term,
        "ad_group": str(ad_group or ""),
        "campaign": str(campaign or ""),
        "campaign_id": str(campaign_id or ""),
        "ad_group_id": str(ad_group_id or ""),
        "clicks": clicks,
        "impressions": impressions,
        "cost_dkk": cost_dkk,
        "conversions": conversions,
        "ctr_pct": _ctr(clicks, impressions),
        "cpa_dkk": _cpa(cost_dkk, conversions),
        "already_keyword": already,
        "keyword_match_type": match_type,
        # which keyword caught this term (and at what match type) — answers "what matched?"
        "trigger_keyword": str(trigger_keyword or ""),
        "trigger_match_type": str(trigger_match_type or ""),
    }


def aggregate_terms(rows: list) -> list:
    """Collapse rows that share the same search term into ONE weighed row.

    On the raw `search_term_view` GAQL path the same term shows up once per ad group / triggering
    keyword, so a naive per-row read both double-counts spend and fragments the judgement. We sum
    cost/clicks/impressions/conversions, recompute CTR/CPA on the totals, keep the term ADDED/
    EXCLUDED if it is so anywhere, and gather the distinct ad groups + triggering keywords that
    caught it (so "what matched, and where does it sit?" is still answerable). Idempotent: a report
    that is already one-row-per-term passes through unchanged.
    """
    by_term: dict[str, dict] = {}
    order: list[str] = []
    for r in rows or []:
        t = r.get("term", "")
        if not t:
            continue
        if t not in by_term:
            by_term[t] = {
                "term": t, "clicks": 0, "impressions": 0, "cost_dkk": 0.0, "conversions": 0.0,
                "already_keyword": None, "_ad_groups": [], "_campaigns": [],
                "_triggers": [], "keyword_match_type": r.get("keyword_match_type"),
                "campaign_id": "", "ad_group_id": "",
            }
            order.append(t)
        a = by_term[t]
        if not a["campaign_id"] and (r.get("campaign_id") or "").strip():
            a["campaign_id"] = str(r["campaign_id"]).strip()
        if not a["ad_group_id"] and (r.get("ad_group_id") or "").strip():
            a["ad_group_id"] = str(r["ad_group_id"]).strip()
        a["clicks"] += int(_num(r.get("clicks")))
        a["impressions"] += int(_num(r.get("impressions")))
        a["cost_dkk"] += _num(r.get("cost_dkk"))
        a["conversions"] += _num(r.get("conversions"))
        if r.get("already_keyword") is True:
            a["already_keyword"] = True
        elif r.get("already_keyword") is False and a["already_keyword"] is None:
            a["already_keyword"] = False
        for key, dest in (("ad_group", "_ad_groups"), ("campaign", "_campaigns"),
                          ("trigger_keyword", "_triggers")):
            v = (r.get(key) or "").strip()
            if v and v not in a[dest]:
                a[dest].append(v)
    out = []
    for t in order:
        a = by_term[t]
        cost = round(a["cost_dkk"], 2)
        conv = round(a["conversions"], 1)
        out.append({
            "term": t,
            "ad_group": a["_ad_groups"][0] if len(a["_ad_groups"]) == 1 else "; ".join(a["_ad_groups"]),
            "campaign": a["_campaigns"][0] if len(a["_campaigns"]) == 1 else "; ".join(a["_campaigns"]),
            "campaign_id": a["campaign_id"],
            "ad_group_id": a["ad_group_id"],
            "ad_group_count": len(a["_ad_groups"]),
            "clicks": a["clicks"],
            "impressions": a["impressions"],
            "cost_dkk": cost,
            "conversions": conv,
            "ctr_pct": _ctr(a["clicks"], a["impressions"]),
            "cpa_dkk": _cpa(cost, conv),
            "already_keyword": a["already_keyword"],
            "keyword_match_type": a["keyword_match_type"],
            "trigger_keyword": "; ".join(a["_triggers"]),
            "trigger_match_type": "",
        })
    out.sort(key=lambda r: -r["cost_dkk"])
    return out


def slim(report_rows: list, spend_floor_dkk: float = DEFAULT_SPEND_FLOOR_DKK,
         aggregate: bool = True) -> dict:
    """Slim the rows to the judgement-relevant fields. Returns:
        {"terms": [...slim dicts sorted by cost desc...],
         "dropped_below_floor": int,        # how many rows the floor removed (0 if floor=0)
         "rows_in": int,                    # raw rows seen
         "distinct_terms": int}             # terms after aggregation
    `aggregate=True` (default) collapses the same term across ad groups into one weighed row so
    each term is judged once — turn it off only if you deliberately want per-ad-group rows.
    `dropped_below_floor` is surfaced so a non-zero floor is never a silent truncation."""
    out, dropped = [], 0
    for raw in report_rows or []:
        row = _one_row(raw if isinstance(raw, dict) else {})
        if row is None:
            continue
        if spend_floor_dkk and row["cost_dkk"] < spend_floor_dkk:
            dropped += 1
            continue
        out.append(row)
    if aggregate:
        out = aggregate_terms(out)
    else:
        out.sort(key=lambda r: -r["cost_dkk"])
    return {
        "terms": out,
        "dropped_below_floor": dropped,
        "rows_in": len([r for r in (report_rows or []) if isinstance(r, dict)]),
        "distinct_terms": len(out),
        # kept for backwards compatibility with older callers
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
