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


# Generic words that carry no offering signal — they appear in almost every travel/education
# search and would otherwise force spurious overlap (e.g. "rejse"/"unge" matching everything).
# Kept lowercase; extend as new noise surfaces. This is why offering overlap was noisy before.
GENERIC_STOPWORDS = {
    "rejse", "rejser", "rejsen", "tur", "ture", "unge", "ung", "for", "med", "til", "den",
    "det", "pris", "priser", "billig", "billige", "bedste", "gratis", "tilbud", "online",
    "danmark", "dansk", "danske", "info", "information",
}


def _tokens(text) -> set:
    """Word tokens of a string, for the offering-overlap hint. Danish letters kept, >2 chars,
    generic stopwords dropped (so 'rejse'/'unge' don't force overlap on everything)."""
    raw = {t for t in re.split(r"[^0-9a-zæøåA-ZÆØÅ]+", str(text or "").lower()) if len(t) > 2}
    return raw - GENERIC_STOPWORDS


def _ngrams(text, n_max=3) -> set:
    """All 1..n_max-word contiguous phrases of a string, lowercased and whitespace-collapsed.
    Lets a multi-word offering token like 'new zealand' / 'costa rica' / 'sri lanka' match a
    search term as a UNIT — single-word tokenisation alone never matched those (Carl's note)."""
    words = [w for w in re.split(r"\s+", normalise_term(text)) if w]
    grams = set()
    for size in range(1, min(n_max, len(words)) + 1):
        for i in range(len(words) - size + 1):
            grams.add(" ".join(words[i:i + size]))
    return grams


def offering_overlap(term: str, offering_tokens: set) -> dict:
    """Overlap between a search term and the offering vocabulary, used by BOTH the negative-band
    proposal and the winner offering-check (one shared notion of 'does this match the offering').

    Matches on two levels: (1) multi-word offering tokens (e.g. 'new zealand') matched as phrases
    via n-grams; (2) single content words (generic stopwords already stripped). Returns:
        {"matched": set(...), "content_tokens": set(...), "degree": "full"|"partial"|"none"}
    degree is over CONTENT tokens (stopwords ignored), so 'grupperejser bali' with bali on-offering
    reads as full, not partial-because-of-'rejser'.
    """
    ot = offering_tokens or set()
    content = _tokens(term)                      # single content words, stopwords removed
    if not ot or not content:
        return {"matched": set(), "content_tokens": content, "degree": "none" if ot else "unknown"}
    grams = _ngrams(term)                         # for multi-word offering tokens
    matched = set()
    for tok in ot:
        if " " in tok:                            # multi-word offering token -> phrase match
            if tok in grams:
                matched |= set(w for w in tok.split() if w not in GENERIC_STOPWORDS)
        elif tok in content:                      # single-word offering token
            matched.add(tok)
    if not matched:
        degree = "none"
    elif matched >= content:                      # every content word is offering vocab
        degree = "full"
    else:
        degree = "partial"
    return {"matched": matched, "content_tokens": content, "degree": degree}


def parse_offering_tokens(offering_md: str) -> set:
    """Extract the OFFERING_TOKENS set from a Phase 0 offering.md (see
    references/offering-brief.md). The brief carries a machine-readable line:

        OFFERING_TOKENS: hoejskole, højskole, grupperejse, bali, ...

    These ARE the offering vocabulary the negative-band proposal uses. Returns a normalised
    lowercase set; empty set if the line is absent (then sweep_negatives proposes GUL for all,
    since it can't claim 'clearly off-offering' without offering context). Robust to the line
    sitting inside an HTML comment block or carrying trailing whitespace/markers.
    """
    if not offering_md:
        return set()
    m = re.search(r"OFFERING_TOKENS\s*:\s*(.+)", offering_md, re.IGNORECASE)
    if not m:
        return set()
    raw = m.group(1).split("-->")[0].splitlines()[0]   # stop at a closing comment / line end
    return {t.strip().lower() for t in raw.split(",") if len(t.strip()) > 1}


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
def sweep_winners(search_term_rows: list, keyword_map_rows: list,
                  offering_tokens: set | None = None) -> dict:
    """Deterministic new-keyword sweep, OFFERING-GROUNDED.

    A term is a candidate iff conversions >= WINNER_MIN_CONV AND it matches NO existing keyword on
    ANY match type (the significance + novelty floor). But a conversion on a lead-gen account is a
    LEAD, not proof the search intent matched the offering — someone can land and sign up for
    something else (see references/selection-spec.md). So a candidate is THEN checked against the
    offering vocabulary (the same offering.md tokens the negative bands use):

      - on-offering (offering overlap none-but-has-no-content is treated on-offering; partial/full
        overlap) -> "winners": promotable on the Nye keywords tab.
      - off-offering (clear 'none' overlap WITH content tokens, and offering context exists)
        -> "review_winners": a converter-invisible review tab. Surfaced + flagged, NOT auto-
        promoted, so an off-offering destination like 'zanzibar højskole' can never silently
        become a new keyword. The agent confirms (move to keywords) or leaves it.

    This FLAGS, never GATES: nothing qualifying is dropped — every >=N-conv novel term lands on
    exactly one of three tabs (Nye keywords / review / Sprunget over) with a script-provable reason.
    With no offering context (empty tokens) everything stays a plain winner (can't claim off-offering).

    Returns {"winners": [...], "review_winners": [...], "skipped": [...]}.
    """
    existing = build_keyword_set(keyword_map_rows)
    ot = offering_tokens or set()
    winners, review, skipped = [], [], []
    for row in search_term_rows or []:
        mx = _row_metrics(row)
        if mx["conversions"] < WINNER_MIN_CONV:
            continue
        match = find_matching_keyword(mx["term"], keyword_map_rows) if existing else None
        if match is not None:
            skipped.append({**mx, "skip_reason": "already_covered", "covered_by": match})
            continue
        # Offering check (only meaningful when we actually have offering tokens).
        if ot:
            ov = offering_overlap(mx["term"], ot)
            # off-offering = has content words, none of which are offering vocab.
            if ov["degree"] == "none" and ov["content_tokens"]:
                review.append({
                    **mx,
                    "flag": "off_offering",
                    "offering_overlap": "",   # nothing matched
                })
                continue
        winners.append(mx)   # on-offering (or no offering context) -> promotable
    winners.sort(key=lambda x: -x["conversions"])
    review.sort(key=lambda x: -x["conversions"])
    skipped.sort(key=lambda x: -x["conversions"])
    return {"winners": winners, "review_winners": review, "skipped": skipped}


# --------------------------------------------------------------------------- negatives sweep
def propose_band(term: str, offering_tokens: set) -> str:
    """Script's PROPOSED relevance band from offering overlap (a hint, never a gate — the agent
    up/downgrades with the richer language read). Uses the shared offering_overlap() so the band
    benefits from n-gram + stopword handling. full overlap -> ROED; partial -> GUL; none -> GROEN;
    no offering context -> GUL (can't claim 'clearly off-offering')."""
    ot = offering_tokens or set()
    if not ot:
        return BAND_YELLOW
    ov = offering_overlap(term, ot)
    degree = ov["degree"]
    if degree == "none":
        return BAND_GREEN                       # shares no offering word -> safe-looking
    if degree == "full":
        return BAND_RED                         # every content word is offering vocab -> looks relevant
    return BAND_YELLOW                           # partial / unknown -> check


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
