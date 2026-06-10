#!/usr/bin/env python3
"""Deterministic candidate sweep for the optimization loop (negatives + new keywords).

The PRINCIPLE (decided with Carl 2026-06-09 — see references/selection-spec.md):

    The script owns "nothing is forgotten". The agent owns "how safe / how relevant".

Before this module, the agent both FOUND and JUDGED search terms, so a qualifying term could
vanish with no trace (a >=2-conv term that never showed up as a new keyword). This module makes
the FINDING deterministic: a script sweep over the search-term rows produces the complete
candidate set; the agent then annotates (confidence band override, reason) but can never silently
add or drop. Every candidate either lands in the workbook or carries a script-provable reason.

This runs INSIDE the search-term sub-agent (it consumes the rows the agent already pulled via
search_terms_query + the keyword map from keyword_map_query). Pure functions, no I/O, no GAQL.

Cost is micros in the raw GAQL rows: DKK = cost_micros / 1_000_000.
"""
from __future__ import annotations

import re

# --- Tunable constants (mirrored in references/selection-spec.md) ---
WINNER_MIN_CONV = 2            # a winner needs >= 2 conversions (inherited significance floor)
NEGATIVE_COST_FLOOR_DKK = 50   # a negative candidate needs >= 50 DKK wasted with 0 conversions
CLICK_CONF_FLOOR = 5           # clicks <= this => set the separate `thin_data` flag (NOT a colour)

# Relevance bands (the Negative tab colour axis — "how safe to block", agent may override).
BAND_GREEN = "GROEN"   # clearly off-offering -> safe to block
BAND_YELLOW = "GUL"    # loosely / partially related -> check
BAND_RED = "ROED"      # looks relevant to the offering -> probably should NOT be a negative

# Buckets (the overview tab colour axis — classification, agent-assigned).
BUCKET_WINNER = "VINDER"
BUCKET_RELEVANT = "RELEVANT"
BUCKET_PLACEMENT = "PLACEMENT_PROBLEM"
BUCKET_IRRELEVANT = "IRRELEVANT"
BUCKET_BORDERLINE = "GRAENSE"


# --------------------------------------------------------------------------- helpers
def _num(v) -> float:
    """GAQL metrics arrive as floats, ints, or numeric strings; coerce safely."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def normalise_term(text) -> str:
    """Normalise a search term / keyword for equality matching: lowercase, collapse
    whitespace, strip surrounding brackets/quotes (Editor's match-type display forms)."""
    s = str(text or "").strip().lower()
    s = s.strip('[]"').strip()          # [exact] / "phrase" display forms
    s = re.sub(r"\s+", " ", s)
    return s


def _tokens(text) -> set:
    """Word tokens of a string, for the offering-overlap hint. Danish letters kept."""
    return {t for t in re.split(r"[^0-9a-zæøåA-ZÆØÅ]+", str(text or "").lower()) if len(t) > 2}


def _row_metrics(row: dict) -> dict:
    """Pull the metrics + identity off a raw search_term_view GAQL row into a flat dict."""
    m = row.get("metrics", {})
    cost_dkk = round(_num(m.get("cost_micros")) / 1_000_000, 2)
    clicks = int(_num(m.get("clicks")))
    conv = _num(m.get("conversions"))
    return {
        "term": row.get("search_term_view", {}).get("search_term", ""),
        "campaign": row.get("campaign", {}).get("name", ""),
        "ad_group": row.get("ad_group", {}).get("name", ""),
        "cost_dkk": cost_dkk,
        "clicks": clicks,
        "conversions": round(conv, 1),
        "cpa_dkk": round(cost_dkk / conv, 0) if conv > 0 else None,
        "impressions": int(_num(m.get("impressions"))),
    }


def build_keyword_set(keyword_map_rows: list) -> set:
    """Normalised set of ALL existing ENABLED keyword texts (any match type), from
    keyword_map_query rows. Used for the new-keyword 'no match on any match type' filter."""
    out = set()
    for r in keyword_map_rows or []:
        kw = r.get("ad_group_criterion", {}).get("keyword", {}).get("text", "")
        if kw:
            out.add(normalise_term(kw))
    return out


def find_matching_keyword(term: str, keyword_map_rows: list):
    """Return the first existing keyword row whose text equals the term (normalised), or None.
    Used to NAME the covering keyword in the 'Sprunget over' explanation."""
    nt = normalise_term(term)
    for r in keyword_map_rows or []:
        kw = r.get("ad_group_criterion", {}).get("keyword", {})
        if normalise_term(kw.get("text", "")) == nt:
            return {
                "keyword": kw.get("text", ""),
                "match_type": kw.get("match_type", ""),
                "campaign": r.get("campaign", {}).get("name", ""),
                "ad_group": r.get("ad_group", {}).get("name", ""),
            }
    return None


# --------------------------------------------------------------------------- winners sweep
def sweep_winners(search_term_rows: list, keyword_map_rows: list) -> dict:
    """Deterministic new-keyword sweep.

    A term qualifies iff conversions >= WINNER_MIN_CONV AND it matches NO existing keyword on
    ANY match type. Returns {"winners": [...], "skipped": [...]} — skipped names the covering
    keyword so the 'Sprunget over' tab can explain exactly why a >=N-conv term fell off.
    """
    existing = build_keyword_set(keyword_map_rows)
    winners, skipped = [], []
    for row in search_term_rows or []:
        mx = _row_metrics(row)
        if mx["conversions"] < WINNER_MIN_CONV:
            continue
        match = find_matching_keyword(mx["term"], keyword_map_rows) if existing else None
        if match is not None:
            skipped.append({
                **mx,
                "skip_reason": "already_covered",
                "covered_by": match,
            })
            continue
        winners.append(mx)   # guaranteed on the Nye keywords tab
    winners.sort(key=lambda x: -x["conversions"])
    skipped.sort(key=lambda x: -x["conversions"])
    return {"winners": winners, "skipped": skipped}


# --------------------------------------------------------------------------- negatives sweep
def propose_band(term: str, offering_tokens: set) -> str:
    """Script's PROPOSED relevance band from literal offering-token overlap (a hint, never a
    gate — the agent up/downgrades with the richer language read). Precedence (evaluate in this
    order): strong overlap -> ROED; partial -> GUL; none -> GROEN."""
    ot = offering_tokens or set()
    if not ot:
        return BAND_YELLOW   # no offering context -> can't claim 'clearly off-offering'
    tt = _tokens(term)
    if not tt:
        return BAND_YELLOW
    overlap = tt & ot
    if not overlap:
        return BAND_GREEN                       # shares no word with the offering -> safe-looking
    if overlap == tt:
        return BAND_RED                         # every token is offering vocab -> looks relevant
    return BAND_YELLOW                           # partial overlap -> check


def sweep_negatives(search_term_rows: list, offering_tokens: set | None = None) -> list:
    """Deterministic negative-candidate sweep.

    A term qualifies iff conversions == 0 AND cost_dkk >= NEGATIVE_COST_FLOOR_DKK. Returns ONE
    list, each candidate with a script-proposed relevance band + a separate thin_data flag
    (clicks <= CLICK_CONF_FLOOR). NOTHING is auto-applied — the workbook surfaces every candidate
    for the human gate. Sorted by wasted cost desc.
    """
    out = []
    for row in search_term_rows or []:
        mx = _row_metrics(row)
        if mx["conversions"] != 0:
            continue
        if mx["cost_dkk"] < NEGATIVE_COST_FLOOR_DKK:
            continue
        out.append({
            **mx,
            "band": propose_band(mx["term"], offering_tokens),   # script proposal; agent may override
            "thin_data": mx["clicks"] <= CLICK_CONF_FLOOR,        # separate significance flag
        })
    out.sort(key=lambda x: -x["cost_dkk"])
    return out


# --------------------------------------------------------------------------- overview
def all_terms_overview(search_term_rows: list) -> list:
    """Every term in the pull (the query already floors at 5 DKK) as flat metric dicts, sorted
    by cost desc. The agent adds a `bucket` per row downstream; this just flattens + orders for
    the 'Alle søgetermer' reference tab (never a CSV)."""
    rows = [_row_metrics(r) for r in (search_term_rows or [])]
    rows.sort(key=lambda x: -x["cost_dkk"])
    return rows
