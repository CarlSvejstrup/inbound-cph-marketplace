#!/usr/bin/env python3
"""Roll a search-terms pull into a COMPACT insight brief — the light, conversational core.

WHY THIS EXISTS
    The standard Google Ads search-terms report is a long flat table: term, cost, clicks, conv.
    That is data, not insight, and at 1000+ terms it cannot fit in context. This script does the
    opposite of dumping the table: it reads the (already server-side-filtered) rows FILE-SIDE and
    prints a small structured brief — the interesting, non-obvious patterns a sharp PPC analyst
    would lead a conversation with:

        - where the money actually concentrates (Pareto), and how much spend has 0 conversions
        - SYSTEMIC themes (n-grams): a waste theme spread thin across 30 cheap terms that a
          per-term scan never notices; a winning theme that is only half-covered by keywords
        - INTENT lenses (price-shopper / question / likely-off-intent / competitor-ish): neutral
          lexical groupings that say "look here", NOT verdicts
        - match-type leakage (broad/phrase spend that converts nothing)
        - structure smell (one term bleeding across several ad groups)
        - uncovered winners (a term that converts but is not yet a keyword)

    The output is a few KB no matter the account size. The model reads ONLY this brief and the
    top-spend table — never the raw rows — and leads the conversation from it.

NOT A JUDGE. Every grouping here is a CONVERSATION STARTER, surfaced with its number. The model
plus the human decide. The cardinal rule still holds: 0 conversions is NOT proof of waste on an
account where people phone — so "zero-conv spend" and the off-intent lens are things to DISCUSS,
never auto-negatives.

Usage:
    python3 digest.py --in <rows.json> --out <digest.json> [--floor 0] [--top 20]
    # <rows.json> may be: a list of report/GAQL rows, {"results": [...]}, or slim.slim() output.
A human-readable brief is printed to stdout (that is what the model should read).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slim as slim_mod  # noqa: E402
import ngram as ngram_mod  # noqa: E402


# --- intent lenses: NEUTRAL lexical groupings, NOT verdicts ------------------------------------
# Each lens is "terms that contain any of these tokens/phrases". They exist to point the eye, so
# the conversation can ask the right question ("is the price cluster worth a dedicated ad group?",
# "is the gratis/job cluster genuinely off-offering?"). Tune per client; they never decide.
INTENT_LENSES = {
    "pris/research (prisjægere)": [
        "pris", "priser", "billig", "billigt", "billigste", "koster", "hvad koster", "tilbud",
        "rabat", "pristjek",
    ],
    "spørgsmål/research (hvad-hvordan)": [
        "hvad", "hvordan", "hvorfor", "hvilken", "hvilke", "hvornår", "kan man", "skal man",
    ],
    "muligt off-intent (gratis/selv/job/uddannelse)": [
        "gratis", "selv", "gør det selv", "diy", "job", "jobs", "stilling", "ledig", "løn",
        "kursus", "kurser", "uddannelse", "skole", "studie", "praktik", "brugt", "anmeldelse",
        "erfaring", "wiki", "wikipedia",
    ],
}


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _round(x, n=0):
    try:
        return round(float(x), n) if n else int(round(float(x)))
    except (TypeError, ValueError):
        return 0


def _term_row_view(t: dict) -> dict:
    """The compact per-term shape we put in tables (drops nothing a human needs, keeps it tiny)."""
    return {
        "term": t.get("term", ""),
        "cost_dkk": _round(t.get("cost_dkk"), 0),
        "clicks": int(_num(t.get("clicks"))),
        "conv": _round(t.get("conversions"), 1),
        "cpa_dkk": t.get("cpa_dkk", ""),
        "ad_group": t.get("ad_group", ""),
        "trigger": t.get("trigger_keyword", "") or t.get("keyword_match_type", "") or "",
        "already_kw": t.get("already_keyword"),
    }


def _has_token(term: str, tokens: list) -> bool:
    words = set(re.split(r"[^0-9a-zæøå]+", str(term or "").lower()))
    for tok in tokens:
        if " " in tok:
            if tok in str(term or "").lower():
                return True
        elif tok in words:
            return True
    return False


def build_digest(terms: list, ngrams: list, dropped_below_floor: int, top: int = 20,
                 leakage_rows: list | None = None) -> dict:
    n = len(terms)
    total_cost = sum(_num(t.get("cost_dkk")) for t in terms)
    total_conv = sum(_num(t.get("conversions")) for t in terms)
    total_clicks = sum(_num(t.get("clicks")) for t in terms)

    by_cost = sorted(terms, key=lambda t: -_num(t.get("cost_dkk")))
    top10_cost = sum(_num(t.get("cost_dkk")) for t in by_cost[:10])

    zero_conv = [t for t in terms if _num(t.get("conversions")) == 0]
    zero_conv_cost = sum(_num(t.get("cost_dkk")) for t in zero_conv)

    # --- themes from n-grams: waste candidates vs winner candidates -----------------------------
    # A "waste candidate" theme: real spend, spread across several terms, with little/no conv.
    # A "winner candidate" theme: converts across several terms AND is not fully covered yet.
    waste = [g for g in ngrams
             if g.get("term_count", 0) >= 2 and _num(g.get("cost_dkk")) >= 50
             and _num(g.get("conversions")) == 0]
    winners = [g for g in ngrams
               if g.get("term_count", 0) >= 2 and _num(g.get("conversions")) > 0
               and g.get("covered_share_pct", 100) < 100]
    waste.sort(key=lambda g: -_num(g.get("cost_dkk")))
    winners.sort(key=lambda g: (-_num(g.get("conversions")), -_num(g.get("cost_dkk"))))

    def _theme(g):
        return {
            "ngram": g.get("ngram"), "terms": g.get("term_count"),
            "cost_dkk": _round(g.get("cost_dkk"), 0), "conv": _round(g.get("conversions"), 1),
            "covered": g.get("covered_text", ""), "examples": g.get("example_terms", ""),
        }

    # --- intent lenses --------------------------------------------------------------------------
    lenses = []
    for label, tokens in INTENT_LENSES.items():
        hits = [t for t in terms if _has_token(t.get("term", ""), tokens)]
        if not hits:
            continue
        lenses.append({
            "lens": label,
            "terms": len(hits),
            "cost_dkk": _round(sum(_num(t.get("cost_dkk")) for t in hits), 0),
            "conv": _round(sum(_num(t.get("conversions")) for t in hits), 1),
            "examples": ", ".join(t.get("term", "") for t in sorted(
                hits, key=lambda x: -_num(x.get("cost_dkk")))[:5]),
        })
    lenses.sort(key=lambda x: -x["cost_dkk"])

    # --- match-type leakage ---------------------------------------------------------------------
    # Compute from per-row data when available (that is where match-type-level spend lives — a term
    # caught by both Broad and Phrase splits its cost correctly). Falls back to aggregated terms.
    mt = {}
    for t in (leakage_rows if leakage_rows is not None else terms):
        key = (t.get("trigger_match_type") or t.get("keyword_match_type") or "ukendt").lower()
        d = mt.setdefault(key, {"match_type": key, "terms": 0, "cost_dkk": 0.0, "conv": 0.0})
        d["terms"] += 1
        d["cost_dkk"] += _num(t.get("cost_dkk"))
        d["conv"] += _num(t.get("conversions"))
    leakage = sorted(
        ({**d, "cost_dkk": _round(d["cost_dkk"], 0), "conv": _round(d["conv"], 1)} for d in mt.values()),
        key=lambda x: -x["cost_dkk"])

    # --- structure smell: a term bleeding across several ad groups ------------------------------
    multi_ag = sorted(
        [t for t in terms if int(_num(t.get("ad_group_count", 1))) > 1],
        key=lambda t: -_num(t.get("cost_dkk")))[:top]

    # --- uncovered winners: converts but not yet a keyword --------------------------------------
    uncovered = sorted(
        [t for t in terms if _num(t.get("conversions")) > 0 and t.get("already_keyword") is False],
        key=lambda t: -_num(t.get("conversions")))[:top]

    return {
        "headline": {
            "distinct_terms": n,
            "spend_dkk": _round(total_cost, 0),
            "conversions": _round(total_conv, 1),
            "blended_cpa_dkk": _round(total_cost / total_conv, 0) if total_conv else "",
            "clicks": _round(total_clicks, 0),
            "top10_spend_share_pct": _round(top10_cost / total_cost * 100, 0) if total_cost else 0,
            "zero_conv_spend_dkk": _round(zero_conv_cost, 0),
            "zero_conv_spend_share_pct": _round(zero_conv_cost / total_cost * 100, 0) if total_cost else 0,
            "zero_conv_terms": len(zero_conv),
            "dropped_below_floor": dropped_below_floor,
        },
        "top_spend_terms": [_term_row_view(t) for t in by_cost[:top]],
        "waste_theme_candidates": [_theme(g) for g in waste[:12]],
        "winner_theme_candidates": [_theme(g) for g in winners[:12]],
        "intent_lenses": lenses,
        "match_type_leakage": leakage,
        "term_in_multiple_ad_groups": [_term_row_view(t) for t in multi_ag],
        "uncovered_winners": [_term_row_view(t) for t in uncovered],
    }


def _fmt_brief(d: dict) -> str:
    h = d["headline"]
    L = []
    L.append("# Søgeterm-brief (læs denne — ikke de rå rækker)")
    L.append("")
    L.append(f"**Overblik:** {h['distinct_terms']} termer · {h['spend_dkk']} kr forbrug · "
             f"{h['conversions']} konv · blended CPA {h['blended_cpa_dkk']} kr · "
             f"top-10 termer = {h['top10_spend_share_pct']}% af forbruget.")
    L.append(f"**0-konv forbrug:** {h['zero_conv_spend_dkk']} kr ({h['zero_conv_spend_share_pct']}%) "
             f"fordelt på {h['zero_conv_terms']} termer — HUSK: 0 konv ≠ spild når folk ringer. "
             f"Det er noget at *tale om*, ikke en dom.")
    if h["dropped_below_floor"]:
        L.append(f"_(Server-side filter / gulv fjernede {h['dropped_below_floor']} små rækker "
                 f"før de ramte kontekst.)_")
    L.append("")

    def table(title, rows, cols):
        if not rows:
            return
        L.append(f"## {title}")
        L.append("| " + " | ".join(c[0] for c in cols) + " |")
        L.append("|" + "|".join("---" for _ in cols) + "|")
        for r in rows:
            L.append("| " + " | ".join(str(r.get(c[1], "")) for c in cols) + " |")
        L.append("")

    table("Hvor pengene går (top forbrug)", d["top_spend_terms"],
          [("Term", "term"), ("Kr", "cost_dkk"), ("Klik", "clicks"), ("Konv", "conv"),
           ("CPA", "cpa_dkk"), ("Ad group", "ad_group"), ("Er kw?", "already_kw")])
    table("⚠️ Systemiske spild-temaer (n-gram, mange termer · 0 konv) — tal om dem", d["waste_theme_candidates"],
          [("N-gram", "ngram"), ("Termer", "terms"), ("Kr", "cost_dkk"), ("Konv", "conv"),
           ("Eksempler", "examples")])
    table("✅ Vinder-temaer (konverterer · ikke fuldt dækket) — kandidat til nye keywords", d["winner_theme_candidates"],
          [("N-gram", "ngram"), ("Termer", "terms"), ("Kr", "cost_dkk"), ("Konv", "conv"),
           ("Dækket", "covered"), ("Eksempler", "examples")])
    table("Intent-linser (neutrale grupperinger — pegepinde, ikke domme)", d["intent_lenses"],
          [("Linse", "lens"), ("Termer", "terms"), ("Kr", "cost_dkk"), ("Konv", "conv"),
           ("Eksempler", "examples")])
    table("Match-type-lækage (hvor fanger brede matches forbrug?)", d["match_type_leakage"],
          [("Match type", "match_type"), ("Termer", "terms"), ("Kr", "cost_dkk"), ("Konv", "conv")])
    table("Struktur-smell (samme term i flere ad groups)", d["term_in_multiple_ad_groups"],
          [("Term", "term"), ("Kr", "cost_dkk"), ("Konv", "conv"), ("Ad groups", "ad_group")])
    table("Udækkede vindere (konverterer, men ikke et keyword endnu)", d["uncovered_winners"],
          [("Term", "term"), ("Kr", "cost_dkk"), ("Konv", "conv"), ("Ad group", "ad_group")])

    L.append("> Alt ovenfor er **samtalestof**, ikke beslutninger. Tag temaerne i prioriteret "
             "rækkefølge, vis tallet, foreslå et træk, og bliv enige før noget skrives til CSV.")
    return "\n".join(L)


def run(rows_or_payload, floor: float = 0.0, top: int = 20) -> tuple[dict, str]:
    # Accept: slim output {"terms":[...]}, {"results":[...]}, or a bare list of rows.
    leakage_rows = None
    if isinstance(rows_or_payload, dict) and "terms" in rows_or_payload:
        terms = rows_or_payload["terms"]
        dropped = rows_or_payload.get("dropped_below_floor", 0)
    else:
        raw = (rows_or_payload.get("results", rows_or_payload)
               if isinstance(rows_or_payload, dict) else rows_or_payload)
        # per-row (un-aggregated) slim keeps match-type-level spend for the leakage table…
        per_row = slim_mod.slim(raw, spend_floor_dkk=floor, aggregate=False)
        leakage_rows = per_row["terms"]
        # …then aggregate the same rows so each term is judged once everywhere else.
        terms = slim_mod.aggregate_terms(leakage_rows)
        dropped = per_row["dropped_below_floor"]
    ngrams = ngram_mod.analyse(terms)
    digest = build_digest(terms, ngrams, dropped, top=top, leakage_rows=leakage_rows)
    return digest, _fmt_brief(digest)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Compact insight brief over a search-terms pull.")
    ap.add_argument("--in", dest="inp", required=True, help="rows JSON (report/GAQL rows, {results:[]}, or slim output)")
    ap.add_argument("--out", required=True, help="output JSON path for the machine-readable digest")
    ap.add_argument("--floor", type=float, default=0.0, help="extra DKK floor applied file-side (default 0; prefer the server-side WHERE filter)")
    ap.add_argument("--top", type=int, default=20, help="rows per table (default 20)")
    args = ap.parse_args()
    payload = json.loads(Path(args.inp).read_text())
    digest, brief = run(payload, floor=args.floor, top=args.top)
    Path(args.out).write_text(json.dumps(digest, ensure_ascii=False, indent=2))
    print(brief)
