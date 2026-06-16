#!/usr/bin/env python3
"""N-gram performance analysis for the search-terms list.

The technique (Carl asked for it explicitly): tokenise every search term into 1-, 2-, and 3-word
phrases, then AGGREGATE the performance metrics (cost, clicks, conversions) across EVERY term that
contains each n-gram. This surfaces SYSTEMIC patterns that per-term analysis misses — especially in
the long tail a spend floor would drop:

    "gratis" appears in 40 terms × ~5 kr each = 200 kr, 0 conversions  -> block ONE n-gram, not 40 terms
    "pris"   appears in 60 terms, strong conversions                   -> a winning theme

This is the deliberate complement to the cost floor: the floor makes the expensive HEAD fast; the
n-gram view recovers the cheap TAIL's signal by summing it. So run this on the UNFILTERED set when
you can (file-side, never in context) — that is where the tail's patterns live.

Pure functions, no I/O. The SCRIPT owns the aggregation ("nothing forgotten"); the AGENT judges
which n-grams are systemic waste vs winners (same split as the rest of the skill).

Cost is DKK here (the slim rows already converted micros->DKK). Reuses the generic stoplist so
function words (og/til/i/for) don't dominate the 1-grams.
"""
from __future__ import annotations

import re

# Generic words that carry no offering/intent signal — drop them from 1-grams so they don't swamp
# the table. Mirrors sweep.GENERIC_STOPWORDS (Danish + a few English), kept local so ngram.py is
# self-contained (Cowork plugins ship standalone).
STOPWORDS = {
    "og", "til", "i", "for", "med", "den", "det", "en", "et", "af", "på", "er", "som", "der",
    "the", "a", "to", "of", "and", "for", "in", "on", "is",
    "rejse", "rejser", "pris", "priser",  # NOTE: 'pris' is borderline — keep as a 1-gram? see below
}
# 'pris'/'priser' ARE meaningful in PPC (price-shoppers), so DON'T stop them — remove from the set.
STOPWORDS -= {"pris", "priser"}

# Defaults — tune per account size.
MAX_N = 3                 # 1-, 2-, 3-grams
MIN_TERM_COUNT = 2        # an n-gram must appear in >= this many DISTINCT terms to be worth a row
                          # (a 1-of-1 n-gram is just the term itself — no aggregation value)


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _words(term: str) -> list:
    """Lowercase content words of a term (Danish letters kept), function words dropped for 1-grams."""
    toks = [t for t in re.split(r"[^0-9a-zæøåA-ZÆØÅ]+", str(term or "").lower()) if t]
    return toks


def _ngrams_of(words: list, max_n: int) -> set:
    """The SET of 1..max_n-word phrases in a term (a set, so a term counts once per distinct n-gram).
    1-grams drop stopwords; multi-word grams keep all words (a phrase like 'gratis tilbud' is fine)."""
    grams = set()
    for w in words:
        if w not in STOPWORDS and len(w) > 1:
            grams.add(w)                                  # 1-gram (content words only)
    for size in range(2, min(max_n, len(words)) + 1):
        for i in range(len(words) - size + 1):
            grams.add(" ".join(words[i:i + size]))        # 2-/3-grams (verbatim)
    return grams


def analyse(slim_terms: list, max_n: int = MAX_N, min_term_count: int = MIN_TERM_COUNT) -> list:
    """Aggregate metrics across every term containing each n-gram.

    slim_terms: rows from slim.slim()["terms"] (term, cost_dkk, clicks, impressions, conversions).
    Returns a list of dicts sorted by total cost desc:
        {ngram, words (1|2|3), term_count, cost_dkk, clicks, impressions, conversions,
         cpa_dkk, ctr_pct, conv_rate_pct, example_terms (up to 3)}
    The agent reads this and marks systemic waste (high cost, 0 conv across many terms) vs systemic
    winners (strong conv across many terms). Only n-grams in >= min_term_count distinct terms appear
    (a 1-term n-gram carries no cross-term signal)."""
    agg = {}
    for row in slim_terms or []:
        term = row.get("term", "")
        words = _words(term)
        cost = _num(row.get("cost_dkk"))
        clicks = int(_num(row.get("clicks")))
        impr = int(_num(row.get("impressions")))
        conv = _num(row.get("conversions"))
        for g in _ngrams_of(words, max_n):
            a = agg.setdefault(g, {"ngram": g, "words": len(g.split()), "term_count": 0,
                                   "cost_dkk": 0.0, "clicks": 0, "impressions": 0,
                                   "conversions": 0.0, "_terms": []})
            a["term_count"] += 1
            a["cost_dkk"] += cost
            a["clicks"] += clicks
            a["impressions"] += impr
            a["conversions"] += conv
            if len(a["_terms"]) < 3:
                a["_terms"].append(term)

    out = []
    for a in agg.values():
        if a["term_count"] < min_term_count:
            continue
        cost = round(a["cost_dkk"], 2)
        conv = round(a["conversions"], 1)
        out.append({
            "ngram": a["ngram"],
            "words": a["words"],
            "term_count": a["term_count"],
            "cost_dkk": cost,
            "clicks": a["clicks"],
            "impressions": a["impressions"],
            "conversions": conv,
            "cpa_dkk": round(cost / conv, 0) if conv else "",
            "ctr_pct": round(a["clicks"] / a["impressions"] * 100, 1) if a["impressions"] else "",
            "conv_rate_pct": round(conv / a["clicks"] * 100, 1) if a["clicks"] else "",
            "example_terms": ", ".join(a["_terms"]),
        })
    out.sort(key=lambda x: -x["cost_dkk"])
    return out


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path
    ap = argparse.ArgumentParser(description="N-gram performance analysis over a slim search-terms list.")
    ap.add_argument("--in", dest="inp", required=True, help="JSON: slim.slim() output OR a list of slim rows")
    ap.add_argument("--out", required=True, help="output JSON path for the n-gram table")
    ap.add_argument("--max-n", type=int, default=MAX_N)
    ap.add_argument("--min-terms", type=int, default=MIN_TERM_COUNT)
    args = ap.parse_args()
    payload = json.loads(Path(args.inp).read_text())
    terms = payload.get("terms", payload) if isinstance(payload, dict) else payload
    res = analyse(terms, args.max_n, args.min_terms)
    Path(args.out).write_text(json.dumps(res, ensure_ascii=False, indent=2))
    print(f"Analysed {len(terms)} terms -> {len(res)} n-grams (>= {args.min_terms} terms each). Wrote {args.out}")
