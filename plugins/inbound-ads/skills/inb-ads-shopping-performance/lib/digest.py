#!/usr/bin/env python3
"""Roll a Shopping product + impression-share pull into a COMPACT Danish insight brief.

WHY THIS EXISTS
    A shopping_performance_view export is a long flat product table: id, title, cost, clicks, conv,
    value. That is data, not insight, and at hundreds of SKUs it will not fit in context. This
    script does the opposite of dumping the table: it reads the (server-side-filtered) rows
    FILE-SIDE and prints a small structured brief — the non-obvious patterns a sharp Shopping
    analyst leads a conversation with:

        - where the money concentrates, blended ROAS, and how much spend returned NOTHING
        - SPILD UDEN RETUR: products burning budget with zero conversions, ranked by spend
        - VINDERE: high-ROAS products worth pushing
        - IMPRESSION-SHARE HULLER: campaigns losing IS to BUDGET (raise budget) vs RANK (raise
          bid / fix feed relevance) — different actions, so the split matters
        - STRUKTUR/LABEL: is the catalogue actually segmented (product_type, custom labels), or is
          everything lumped so bidding cannot differentiate?

    The output is a few KB no matter the catalogue size. The model reads ONLY this brief and the
    top tables — never the raw rows — and leads the conversation from it.

NOT A JUDGE. Every grouping is a CONVERSATION STARTER surfaced with its number. The cardinal rule:
ZERO CONVERSIONS IS NOT PROOF OF WASTE on an account where people also buy offline or phone. A
core product with spend and no conversions is more likely a FEED or LANDING-PAGE signal than a
"pause it" case — and this skill cannot see the feed, so it must say "look in Merchant Center",
not "exclude". So "spild uden retur" is a thing to DISCUSS, never an auto-exclusion.

Usage:
    python3 digest.py --products <products.json> --is <is.json> --out <digest.json> [--top 20]
A human-readable Danish brief is printed to stdout (that is what the model should read).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slim as slim_mod  # noqa: E402


def _kr(v: float) -> str:
    return f"{v:,.0f} kr".replace(",", ".")


def _pct(v: float) -> str:
    return f"{v * 100:.0f} %"


def build(products: list[dict], campaigns: list[dict], top: int) -> dict:
    total_cost = sum(p["cost"] for p in products)
    total_val = sum(p["conversions_value"] for p in products)
    total_conv = sum(p["conversions"] for p in products)
    blended_roas = round(total_val / total_cost, 2) if total_cost > 0 else 0.0

    # Spild uden retur: spend > 0, conversions == 0. The headline conversation, NOT a verdict.
    waste = [p for p in products if p["cost"] > 0 and p["conversions"] == 0]
    waste.sort(key=lambda p: p["cost"], reverse=True)
    waste_cost = sum(p["cost"] for p in waste)

    # Vindere: products that convert, ranked by ROAS (only those with real value).
    winners = [p for p in products if p["conversions_value"] > 0]
    winners.sort(key=lambda p: p["roas"], reverse=True)

    # Impression-share huller: campaigns with meaningful loss, split by cause.
    budget_limited = sorted(
        [c for c in campaigns if c["budget_lost_is"] >= 0.10],
        key=lambda c: c["budget_lost_is"],
        reverse=True,
    )
    rank_limited = sorted(
        [c for c in campaigns if c["rank_lost_is"] >= 0.20],
        key=lambda c: c["rank_lost_is"],
        reverse=True,
    )

    # Struktur/label: how much of the catalogue actually carries a custom label / product_type.
    labelled = sum(1 for p in products if p["custom_label_0"])
    typed = sum(1 for p in products if p["product_type_l1"])
    n = len(products) or 1

    return {
        "overblik": {
            "produkter": len(products),
            "forbrug": total_cost,
            "konverteringer": round(total_conv, 1),
            "vaerdi": round(total_val, 0),
            "blended_roas": blended_roas,
            "forbrug_uden_retur": round(waste_cost, 0),
            "andel_forbrug_uden_retur": round(waste_cost / total_cost, 3) if total_cost else 0.0,
        },
        "top_forbrug": products[:top],
        "spild_uden_retur": waste[:top],
        "vindere": winners[:top],
        "is_budget_begraenset": budget_limited[:top],
        "is_rank_begraenset": rank_limited[:top],
        "struktur": {
            "andel_med_custom_label": round(labelled / n, 2),
            "andel_med_product_type": round(typed / n, 2),
        },
    }


def print_brief(d: dict, top: int) -> None:
    o = d["overblik"]
    p = print
    p("\n" + "=" * 78)
    p("SHOPPING-PERFORMANCE BRIEF (samtale-startere, ikke domme)")
    p("=" * 78)
    p(
        f"\nOverblik: {o['produkter']} produkter · forbrug {_kr(o['forbrug'])} · "
        f"{o['konverteringer']} konv · værdi {_kr(o['vaerdi'])} · blended ROAS {o['blended_roas']}"
    )
    p(
        f"  Forbrug uden retur: {_kr(o['forbrug_uden_retur'])} "
        f"({_pct(o['andel_forbrug_uden_retur'])} af alt forbrug)"
    )
    p("\n  MINDER: 0 konverteringer er IKKE bevis på spild. Kernevarer med forbrug og 0 konv er")
    p("  oftere et feed-/landingsside-signal (→ Merchant Center) end en 'pause den'-sag. Dette")
    p("  skill ser ikke feed'et. Alt nedenfor er noget vi TALER om.")

    def _tbl(title: str, rows: list[dict], cols: list[tuple[str, str]]) -> None:
        p(f"\n--- {title} (top {min(top, len(rows))} af {len(rows)}) ---")
        if not rows:
            p("  (ingen)")
            return
        for r in rows:
            parts = []
            for label, key in cols:
                v = r.get(key)
                if key in ("cost", "conversions_value", "vaerdi"):
                    v = _kr(v or 0)
                elif key in ("impression_share", "budget_lost_is", "rank_lost_is"):
                    v = _pct(v or 0)
                parts.append(f"{label}={v}")
            title_txt = (r.get("product_title") or r.get("campaign") or "").strip()
            p(f"  {title_txt[:48]:<48} " + " · ".join(parts))

    _tbl("SPILD UDEN RETUR (forbrug > 0, konv = 0)", d["spild_uden_retur"],
         [("forbrug", "cost"), ("klik", "clicks"), ("impr", "impressions")])
    _tbl("VINDERE (efter ROAS)", d["vindere"],
         [("ROAS", "roas"), ("forbrug", "cost"), ("værdi", "conversions_value")])
    _tbl("IS — BUDGET-BEGRÆNSET (hæv budget/bud)", d["is_budget_begraenset"],
         [("tabt-budget", "budget_lost_is"), ("IS", "impression_share"), ("forbrug", "cost")])
    _tbl("IS — RANK-BEGRÆNSET (hæv bud / bedre feed-titel)", d["is_rank_begraenset"],
         [("tabt-rank", "rank_lost_is"), ("IS", "impression_share"), ("forbrug", "cost")])

    s = d["struktur"]
    p(f"\n--- STRUKTUR/LABEL ---")
    p(f"  Andel produkter med custom_label_0: {_pct(s['andel_med_custom_label'])}")
    p(f"  Andel produkter med product_type:   {_pct(s['andel_med_product_type'])}")
    p("  (Lav andel = kataloget er ikke segmenteret → budgivning kan ikke skelne bestsellere,")
    p("   marginer eller sæson. Anbefal-kun; dette skill ændrer ikke struktur selv.)")
    p("\n" + "=" * 78 + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--products", required=True, help="raw pull A json (product performance)")
    ap.add_argument("--is", dest="is_file", required=False, help="raw pull B json (campaign IS)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()

    products = slim_mod.slim_products(json.loads(Path(args.products).read_text()))
    campaigns = slim_mod.slim_is(json.loads(Path(args.is_file).read_text())) if args.is_file else []

    d = build(products, campaigns, args.top)
    Path(args.out).write_text(json.dumps(d, ensure_ascii=False, indent=2))
    print_brief(d, args.top)


if __name__ == "__main__":
    main()
