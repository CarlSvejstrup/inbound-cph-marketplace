#!/usr/bin/env python3
"""
score_placements.py — Tier 1 deterministic risk scoring for Google Ads Display placements.

This is the ONLY deterministic part of inb-ads-display-placement-audit. It never judges intent or
writes prose — it computes one additive 0-100 risk score per placement from cheap local
signals (bundled blocklist, TLD, gambling keyword, app-network type) and sorts placements into
three bands. Everything past that (the middle "unsure" band, the final ranked report, the
human-facing reasoning) is the model's job, not this script's.

Signals were narrowed on 2026-07-03 (after a live DBI run flagged bt.dk, proff.no and
mentedidactica.com as "usikker") by dropping "zero conversions at spend" and "CTR anomaly"
entirely — both are NORMAL Display behavior for a large, legitimate site, so they fired
constantly on sites with nothing wrong with them.

**2026-07-04 re-widen: false negatives cost more than false positives here.** The user reported
the narrowed script was now letting real junk through as "low" — explicit direction: recall
matters more than precision, it is fine (expected, even) for the "usikker" pile to catch some
legitimate sites as long as real junk stops disappearing into "low" unreviewed. Two changes:

1. `zero_conv_at_spend` is back, but as a WEAK, NEVER-ALONE-DECISIVE tiebreaker (weight 8, see
   WEIGHT_ZERO_CONV_AT_SPEND) — it nudges a placement that already has some other reason to look
   twice, it cannot by itself move a signal-free placement out of "low" (see score_placement: it
   only applies on top of an existing site-identity signal, mirroring how the hard-exclusion
   keyword/TLD signals already work). This is deliberately NOT the same mechanism that caused the
   bt.dk/proff.no false positives — those fired standalone, at high enough weight to reach
   "usikker" on their own with nothing else backing them up.
2. `--high-threshold` default lowered 70 -> 50 so combinations of existing signals (e.g. risky TLD
   + gambling keyword, or blocklist + zero-conv tiebreaker) reach "high" more easily.

Common, obviously-legitimate Danish/Nordic sites are still expected to land in "low" or "usikure"
as they did before — this widening does not touch the hard-exclusion allowlist logic
(`_TLD_ALLOWLIST` in hard_exclusion_patterns.py exempts .dk/.se/.no/.fi/.de/.uk) and the model is
still expected to apply judgment before recommending removal of anything that reads as an
established Danish media/business site, per SKILL.md.

Banding stays recall-biased on top of this: "low" means ZERO signals matched. Any placement with a
real signal lands in "unsure" rather than being silently cleared — see band_for_score() for the
live-test failure that drove this (a real Danish gambling site scored under the old numeric
low-threshold and disappeared). There is deliberately no --low-threshold flag.

The report layer (SKILL.md Trin 5) sorts and prioritizes by SPEND, not by score — cost-first, so
the expert's attention goes where the money is, not where the algorithm is most excited.

Usage:
    python3 score_placements.py --in placements.json --out scored.json \
        [--high-threshold 50] [--tier3-cap 20]

Input JSON schema (placements.json):
{
  "currency": "DKK",
  "already_excluded": ["domain-already-on-a-negative-list.com", ...],
  "placements": [
    {
      "display_name": "www.example.com",
      "domain": "example.com",
      "placement_type": "WEBSITE" | "MOBILE_APPLICATION" | "YOUTUBE_CHANNEL" | "YOUTUBE_VIDEO",
      "campaign_name": "...",
      "campaign_channel_type": "DISPLAY" | "PERFORMANCE_MAX",
      "impressions": 0,
      "clicks": 0,
      "cost_micros": 0,
      "conversions": 0.0
    }, ...
  ]
}

Output JSON schema (scored.json): same placements, each with an added "score" block:
{
  ...original fields...,
  "score": {
    "total": 0-100,
    "band": "hard_exclusion" | "high" | "unsure" | "low",
    "signals": ["blocklist:gambling", "risky_tld:.top", ...],
    "already_excluded": true/false,
    "hard_exclusion_reason": "hard_domain_list" | "hard_keyword" | "hard_foreign_tld" |
                              "hard_non_latin_script"   (only present when band == "hard_exclusion")
    "hard_exclusion_category": "gaming_portal" | "kids" | "mfa_quiz" | ... | the matched
                                 keyword/TLD/script name   (only present when band == "hard_exclusion")
  }
}
Placements already on an existing negative list are still scored (for transparency) but
flagged already_excluded=true — the skill must never re-propose them. already_excluded takes
priority over hard-exclusion matching (no point re-deriving a reason for something already gone).

hard_exclusion is Inbound's OWN standing exclusion list (references/hard_exclusions.tsv +
hard_exclusion_patterns.py), sourced from their internally-used keyword/domain/TLD/script filters
(2026-07-03). It is a separate, harder tier than the "high" score band: a hard_exclusion match
bypasses scoring and the web-search step entirely and goes straight to "anbefales fjernet" in the
report, because it reflects a client-confirmed rule, not this skill's own probabilistic judgment.
"""

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REFERENCES_DIR = SCRIPT_DIR.parent / "references"
JUNK_DOMAINS_PATH = REFERENCES_DIR / "junk_domains.tsv"
HARD_EXCLUSIONS_PATH = REFERENCES_DIR / "hard_exclusions.tsv"

sys.path.insert(0, str(REFERENCES_DIR))
import hard_exclusion_patterns as hard_patterns  # noqa: E402

RISKY_TLDS = {
    ".top", ".xyz", ".icu", ".club", ".online", ".cfd", ".sbs",
    ".bond", ".win", ".rest", ".mom", ".cn",
}

# Verified gap (2026-07-01, live test against a real account): community DNS blocklists
# (Blocklist Project, Steven Black) are built to catch casino/betting BRANDS and largely miss
# legitimate-looking lottery-result / betting-result sites (e.g. a national lottery's own
# results page) because those aren't "malicious" from a DNS-blocklist maintainer's point of
# view. A live Dantaxi placement on euro-jackpot.net and danskelotto.com scored 0 on blocklist
# match alone. This is a cheap, low-precision backstop for that specific blind spot — it will
# have false positives (a placement that happens to contain "bet" as a substring of an
# unrelated word), so it carries a light weight and the SKILL.md tells the model to sanity-check
# domain names by eye regardless of what the script scores.
# Verified gap (2026-07-01, live re-test on Dantaxi): the first version of this pattern was
# English-only and missed spil2vind.dk ("spil" = Danish for play/gamble, "2vind" = "to win") —
# a genuine Danish gambling site, on an account whose whole client base is Danish/Nordic.
# A junk-placement classifier for a Danish agency has to carry Danish gambling vocabulary as a
# first-class signal, not an afterthought — this is not a nice-to-have localization detail.
GAMBLING_KEYWORD_PATTERN = re.compile(
    r"(lotto|jackpot|casino|betting|sportsbook|poker|bingo|wager|odds\b|bet365|"
    r"spilleautomat|gambling|slots?\b|"
    r"spil[0-9]|spillemaskine|odds[0-9]|tips(bladet)?|"
    r"vind(er)?millionen|spilafhaengig)",
    re.IGNORECASE,
)
WEIGHT_GAMBLING_KEYWORD_IN_NAME = 15

# Additive weights. Site-identity signals (2026-07-03 redesign) — all about the SITE, none about
# performance. A site is either recognizably junk (blocklist/TLD/keyword) or structurally riskier
# (app network); how it performed on Display is not evidence of either, on its own.
WEIGHT_BLOCKLIST = 70          # a direct hit is close to decisive on its own
WEIGHT_RISKY_TLD = 20
WEIGHT_APP_NETWORK = 15        # lowered from 20 — real signal, but shouldn't alone read as "junk"

# Re-added 2026-07-04 as a WEAK TIEBREAKER ONLY — never fires unless at least one site-identity
# signal above already fired. This is the deliberate difference from the version removed
# 2026-07-03: that version applied to every placement standalone (any spend + zero conversions),
# which is why it caught bt.dk/proff.no/mentedidactica.com — large, legitimate sites where low
# Display conversion is simply normal. Gating it behind "only on top of an existing signal" keeps
# it from ever being the sole reason a clean site gets flagged, while still nudging an
# already-suspicious placement (e.g. risky TLD alone, previously a borderline "usikure" case)
# a bit further up the score, and giving the "high" band an easier path to trigger on combined
# weak signals now that --high-threshold defaults lower (see module docstring).
WEIGHT_ZERO_CONV_AT_SPEND = 8
ZERO_CONV_SPEND_FLOOR_MICROS = 5_000_000  # 5 currency units; below this, spend is too noisy to read


def load_domain_list(path, label, has_header=False):
    """Returns {domain: category}. Missing file degrades to empty dict, never crashes."""
    if not path.exists():
        print(f"WARNING: {path} not found — {label} signal disabled", file=sys.stderr)
        return {}
    domains = {}
    with open(path, encoding="utf-8") as f:
        if has_header:
            next(f, None)
        for line in f:
            line = line.rstrip("\n")
            if not line or "\t" not in line:
                continue
            domain, category = line.split("\t", 1)
            domains[domain.strip().lower()] = category.strip()
    return domains


def load_junk_domains():
    return load_domain_list(JUNK_DOMAINS_PATH, "blocklist")


def load_hard_exclusion_domains():
    return load_domain_list(HARD_EXCLUSIONS_PATH, "hard-exclusion", has_header=True)


def root_domain_candidates(domain):
    """
    A placement's 'domain' field is often a subdomain or full path host
    (e.g. m.17track.net, top.poiy.online). Blocklists are keyed on registrable
    domains. Generate candidates from most-specific to least-specific so a
    blocklist hit on the registrable domain still matches a subdomain placement.
    """
    domain = domain.lower().strip().rstrip(".")
    parts = domain.split(".")
    candidates = []
    for i in range(len(parts) - 1):
        candidates.append(".".join(parts[i:]))
    return candidates or [domain]


def check_blocklist(domain, junk_domains):
    for candidate in root_domain_candidates(domain):
        if candidate in junk_domains:
            return junk_domains[candidate]
    return None


def check_risky_tld(domain):
    domain = domain.lower()
    for tld in RISKY_TLDS:
        if domain.endswith(tld):
            return tld
    return None


def check_hard_exclusion(domain, display_name, hard_exclusion_domains):
    """
    Returns a (reason_code, category) tuple if this placement matches Inbound's own standing
    exclusion list (references/hard_exclusions.tsv + hard_exclusion_patterns.py), else None.
    This is a CLIENT-CONFIRMED list, not this skill's own heuristic — a match here bypasses
    scoring entirely (see band_for_score) rather than adding to a score, because Inbound has
    already decided these categories are unwanted, independent of any individual placement's
    performance or context.
    """
    for candidate in root_domain_candidates(domain):
        if candidate in hard_exclusion_domains:
            return ("hard_domain_list", hard_exclusion_domains[candidate])

    combined = f"{domain} {display_name or ''}"
    kw = hard_patterns.matches_keyword(combined)
    if kw:
        return ("hard_keyword", kw)

    tld = hard_patterns.matches_foreign_tld(domain)
    if tld:
        return ("hard_foreign_tld", tld)

    script = hard_patterns.matches_non_latin_script(combined)
    if script:
        return ("hard_non_latin_script", script)

    return None


def score_placement(p, junk_domains):
    signals = []
    score = 0

    domain = p.get("domain") or p.get("display_name") or ""
    placement_type = p.get("placement_type", "")

    # Signal 1: blocklist match (heavy weight, often decisive alone)
    category = check_blocklist(domain, junk_domains)
    if category:
        score += WEIGHT_BLOCKLIST
        signals.append(f"blocklist:{category}")

    # Signal 2: risky TLD
    tld = check_risky_tld(domain)
    if tld:
        score += WEIGHT_RISKY_TLD
        signals.append(f"risky_tld:{tld}")

    # Signal 2b: gambling/betting keyword literally in the domain name — cheap backstop for
    # the verified blocklist blind spot on lottery/betting-result sites (see comment above).
    if not category and GAMBLING_KEYWORD_PATTERN.search(domain):
        score += WEIGHT_GAMBLING_KEYWORD_IN_NAME
        signals.append("gambling_keyword_in_domain")

    # Signal 3: mobile app network traffic — structural risk regardless of individual site quality
    if placement_type == "MOBILE_APPLICATION":
        score += WEIGHT_APP_NETWORK
        signals.append("app_network_traffic")

    # Signal 4 (tiebreaker ONLY, re-added 2026-07-04): zero conversions despite real spend.
    # Deliberately gated on `signals` already being non-empty — this must never be the sole
    # reason a placement gets flagged (that was the exact bt.dk/proff.no failure mode). It only
    # nudges a placement that already has a site-identity reason to look twice.
    cost_micros = p.get("cost_micros", 0) or 0
    conversions = p.get("conversions", 0) or 0
    if signals and cost_micros >= ZERO_CONV_SPEND_FLOOR_MICROS and conversions == 0:
        score += WEIGHT_ZERO_CONV_AT_SPEND
        signals.append("zero_conv_at_spend_tiebreaker")

    score = min(score, 100)
    return score, signals


def band_for_score(score, signals, high_threshold, hard_exclusion=None):
    """
    Banding is recall-biased by design (explicit user direction, 2026-07-01): a placement with
    ANY signal at all — even a single weak one — must NOT land in "low" silently. Better a large
    "unsure" pile the expert skims and dismisses than a real junk placement disappearing because
    no single signal alone crossed a numeric line. Only a placement with ZERO signals (nothing
    matched at all) auto-clears to "low" — there's genuinely nothing to review.

    This came directly out of a live-test miss: spil2vind.dk (a real Danish gambling site) hit
    the gambling-keyword signal but its total score (15) was under the old low_threshold (30), so
    it silently cleared into "low" with no human ever looking at it. There is deliberately no
    "low_threshold" parameter anymore — a single flimsy signal downgrades confidence (it's
    "unsure", not "high"), it does not disappear the placement.

    A hard_exclusion match (2026-07-03: Inbound's own standing exclusion list) always wins over
    everything else, regardless of score — it is a client-confirmed rule, not a heuristic, so
    there is nothing left to weigh it against.
    """
    if hard_exclusion:
        return "hard_exclusion"
    if score >= high_threshold:
        return "high"
    if not signals:
        return "low"
    return "unsure"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--in", dest="infile", required=True, help="Input placements JSON")
    parser.add_argument("--out", dest="outfile", required=True, help="Output scored JSON")
    parser.add_argument("--high-threshold", type=int, default=50,
                         help="Score >= this -> auto-flag as junk, no network lookup needed (default "
                              "50, lowered from 70 on 2026-07-04 per explicit user direction to widen "
                              "recall — false negatives cost more than false positives here)")
    parser.add_argument("--tier3-cap", type=int, default=20,
                         help="Max number of 'unsure' placements (ranked by spend) the skill should "
                              "resolve via a live web search; everything beyond this cap is left as "
                              "'needs manual review' rather than skipped silently (default 20). This "
                              "script does not call the web itself — it just marks which placements "
                              "qualify for that step. The report layer still shows every unsure "
                              "placement, capped or not; only the web-search step is capped.")
    args = parser.parse_args()

    with open(args.infile, encoding="utf-8") as f:
        data = json.load(f)

    junk_domains = load_junk_domains()
    hard_exclusion_domains = load_hard_exclusion_domains()
    already_excluded = set(d.lower() for d in data.get("already_excluded", []))

    scored = []
    for p in data.get("placements", []):
        domain = (p.get("domain") or p.get("display_name") or "").lower()
        display_name = p.get("display_name") or ""
        is_excluded = any(candidate in already_excluded for candidate in root_domain_candidates(domain))

        hard_hit = None
        if not is_excluded:
            hard_hit = check_hard_exclusion(domain, display_name, hard_exclusion_domains)

        score, signals = score_placement(p, junk_domains)
        band = band_for_score(score, signals, args.high_threshold, hard_exclusion=hard_hit)

        p_out = dict(p)
        p_out["score"] = {
            "total": score,
            "band": band,
            "signals": signals,
            "already_excluded": is_excluded,
        }
        if hard_hit:
            p_out["score"]["hard_exclusion_reason"] = hard_hit[0]
            p_out["score"]["hard_exclusion_category"] = hard_hit[1]
        scored.append(p_out)

    # Rank the "unsure" band by SPEND, cost-first (2026-07-03 direction): the expert's — and the
    # web-search budget's — attention should go where the money is, not where the score happens to
    # be highest. A gambling-keyword or blocklist hit still always qualifies regardless of rank
    # (see SKILL.md Trin 4 override) — this ordering only decides who else gets the remaining slots.
    unsure = [p for p in scored if p["score"]["band"] == "unsure" and not p["score"]["already_excluded"]]
    unsure.sort(key=lambda p: p.get("cost_micros", 0), reverse=True)
    for i, p in enumerate(unsure):
        p["score"]["tier3_eligible"] = i < args.tier3_cap
        p["score"]["tier3_rank"] = i + 1

    summary = {
        "total_placements": len(scored),
        "hard_exclusion_band": sum(1 for p in scored if p["score"]["band"] == "hard_exclusion"),
        "high_band": sum(1 for p in scored if p["score"]["band"] == "high"),
        "unsure_band": len(unsure),
        "unsure_eligible_for_lookup": min(len(unsure), args.tier3_cap),
        "unsure_needs_manual_review": max(0, len(unsure) - args.tier3_cap),
        "low_band": sum(1 for p in scored if p["score"]["band"] == "low"),
        "already_excluded_count": sum(1 for p in scored if p["score"]["already_excluded"]),
        "thresholds": {
            "high": args.high_threshold,
            "tier3_cap": args.tier3_cap,
        },
    }

    with open(args.outfile, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "placements": scored}, f, indent=2, ensure_ascii=False)

    print(f"Scored {summary['total_placements']} placements -> {args.outfile}", file=sys.stderr)
    print(f"  hard_exclusion={summary['hard_exclusion_band']} high={summary['high_band']} "
          f"unsure={summary['unsure_band']} "
          f"(eligible for lookup: {summary['unsure_eligible_for_lookup']}, "
          f"needs manual review: {summary['unsure_needs_manual_review']}) "
          f"low={summary['low_band']} already_excluded={summary['already_excluded_count']}", file=sys.stderr)


if __name__ == "__main__":
    main()
