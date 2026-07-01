#!/usr/bin/env python3
"""
score_placements.py — Tier 1 deterministic risk scoring for Google Ads Display placements.

This is the ONLY deterministic part of display-placement-audit. It never judges intent or
writes prose — it computes one additive 0-100 risk score per placement from cheap local
signals (bundled blocklist, TLD, account performance data, network type) and sorts
placements into three bands. Everything past that (the middle "unsure" band, the final
ranked report, the human-facing reasoning) is the model's job, not this script's.

Usage:
    python3 score_placements.py --in placements.json --out scored.json \
        [--high-threshold 70] [--low-threshold 30] [--tier3-cap 20] \
        [--zero-conv-floor 100]

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
    "band": "high" | "unsure" | "low",
    "signals": ["blocklist:gambling", "risky_tld:.top", "zero_conv_at_spend", ...],
    "already_excluded": true/false
  }
}
Placements already on an existing negative list are still scored (for transparency) but
flagged already_excluded=true — the skill must never re-propose them.
"""

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
JUNK_DOMAINS_PATH = SCRIPT_DIR.parent / "references" / "junk_domains.tsv"

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

# Additive weights. Tuned to be directionally right, not precisely calibrated —
# expected to be adjusted over time as the skill is used against real accounts.
WEIGHT_BLOCKLIST = 70          # a direct hit is close to decisive on its own
WEIGHT_RISKY_TLD = 20
WEIGHT_ZERO_CONV_AT_SPEND = 25
WEIGHT_CTR_TOO_LOW = 15
WEIGHT_CTR_TOO_HIGH = 15
WEIGHT_APP_NETWORK = 20
WEIGHT_NO_CONVERSION_TRACKING_SIGNAL = 0  # reserved, not used yet (see SKILL.md limitations)

CTR_LOW_IMPRESSION_FLOOR = 500       # need enough volume for a CTR anomaly to mean anything
CTR_TOO_LOW_THRESHOLD = 0.0005       # 0.05% CTR at high volume — classic MFA/bot-fill signature
CTR_TOO_HIGH_MIN_CLICKS = 5
CTR_TOO_HIGH_THRESHOLD = 0.15        # 15%+ CTR is not organic for GDN display


def load_junk_domains():
    """Returns {domain: category}. Missing file degrades to empty dict, never crashes."""
    if not JUNK_DOMAINS_PATH.exists():
        print(f"WARNING: {JUNK_DOMAINS_PATH} not found — blocklist signal disabled", file=sys.stderr)
        return {}
    domains = {}
    with open(JUNK_DOMAINS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or "\t" not in line:
                continue
            domain, category = line.split("\t", 1)
            domains[domain.strip().lower()] = category.strip()
    return domains


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


def score_placement(p, junk_domains, zero_conv_floor_micros):
    signals = []
    score = 0

    domain = p.get("domain") or p.get("display_name", "")
    impressions = p.get("impressions", 0) or 0
    clicks = p.get("clicks", 0) or 0
    cost_micros = p.get("cost_micros", 0) or 0
    conversions = p.get("conversions", 0) or 0
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

    # Signal 3: zero conversions at meaningful spend
    if cost_micros >= zero_conv_floor_micros and conversions == 0:
        score += WEIGHT_ZERO_CONV_AT_SPEND
        signals.append("zero_conv_at_spend")

    # Signal 4: CTR anomaly (only meaningful at real volume)
    if impressions >= CTR_LOW_IMPRESSION_FLOOR:
        ctr = (clicks / impressions) if impressions else 0
        if ctr < CTR_TOO_LOW_THRESHOLD:
            score += WEIGHT_CTR_TOO_LOW
            signals.append("ctr_too_low")
        elif clicks >= CTR_TOO_HIGH_MIN_CLICKS and ctr > CTR_TOO_HIGH_THRESHOLD:
            score += WEIGHT_CTR_TOO_HIGH
            signals.append("ctr_too_high")

    # Signal 5: mobile app network traffic — structural risk regardless of individual site quality
    if placement_type == "MOBILE_APPLICATION":
        score += WEIGHT_APP_NETWORK
        signals.append("app_network_traffic")

    score = min(score, 100)
    return score, signals


def band_for_score(score, high_threshold, low_threshold):
    if score >= high_threshold:
        return "high"
    if score < low_threshold:
        return "low"
    return "unsure"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--in", dest="infile", required=True, help="Input placements JSON")
    parser.add_argument("--out", dest="outfile", required=True, help="Output scored JSON")
    parser.add_argument("--high-threshold", type=int, default=70,
                         help="Score >= this -> auto-flag as junk, no network lookup needed (default 70)")
    parser.add_argument("--low-threshold", type=int, default=30,
                         help="Score < this -> auto-clear, no network lookup needed (default 30)")
    parser.add_argument("--tier3-cap", type=int, default=20,
                         help="Max number of 'unsure' placements (ranked by spend) the skill should "
                              "resolve via a live web search; everything beyond this cap is left as "
                              "'needs manual review' (default 20). This script does not call the web "
                              "itself — it just marks which placements qualify for that step.")
    parser.add_argument("--zero-conv-floor", type=float, default=20.0,
                         help="Spend floor (account currency units) above which a zero-conversion "
                              "placement is flagged. Default 20 (e.g. 20 DKK) — deliberately low, "
                              "because GDN junk is usually many small-spend placements rather than "
                              "one big-spend one (verified against a live account: a real gambling "
                              "placement had ~13 DKK spend / 0 conversions over 30 days). Tune up "
                              "for high-volume/high-AOV accounts where 20 is noise-level.")
    args = parser.parse_args()

    with open(args.infile, encoding="utf-8") as f:
        data = json.load(f)

    junk_domains = load_junk_domains()
    zero_conv_floor_micros = args.zero_conv_floor * 1_000_000
    already_excluded = set(d.lower() for d in data.get("already_excluded", []))

    scored = []
    for p in data.get("placements", []):
        domain = (p.get("domain") or p.get("display_name", "")).lower()
        score, signals = score_placement(p, junk_domains, zero_conv_floor_micros)
        band = band_for_score(score, args.high_threshold, args.low_threshold)
        is_excluded = any(candidate in already_excluded for candidate in root_domain_candidates(domain))

        p_out = dict(p)
        p_out["score"] = {
            "total": score,
            "band": band,
            "signals": signals,
            "already_excluded": is_excluded,
        }
        scored.append(p_out)

    # Rank the "unsure" band by spend so the skill knows which top-N qualify for tier-3 lookup
    unsure = [p for p in scored if p["score"]["band"] == "unsure" and not p["score"]["already_excluded"]]
    unsure.sort(key=lambda p: p.get("cost_micros", 0), reverse=True)
    for i, p in enumerate(unsure):
        p["score"]["tier3_eligible"] = i < args.tier3_cap
        p["score"]["tier3_rank"] = i + 1

    summary = {
        "total_placements": len(scored),
        "high_band": sum(1 for p in scored if p["score"]["band"] == "high"),
        "unsure_band": len(unsure),
        "unsure_eligible_for_lookup": min(len(unsure), args.tier3_cap),
        "unsure_needs_manual_review": max(0, len(unsure) - args.tier3_cap),
        "low_band": sum(1 for p in scored if p["score"]["band"] == "low"),
        "already_excluded_count": sum(1 for p in scored if p["score"]["already_excluded"]),
        "thresholds": {
            "high": args.high_threshold,
            "low": args.low_threshold,
            "tier3_cap": args.tier3_cap,
            "zero_conv_floor": args.zero_conv_floor,
        },
    }

    with open(args.outfile, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "placements": scored}, f, indent=2, ensure_ascii=False)

    print(f"Scored {summary['total_placements']} placements -> {args.outfile}", file=sys.stderr)
    print(f"  high={summary['high_band']} unsure={summary['unsure_band']} "
          f"(eligible for lookup: {summary['unsure_eligible_for_lookup']}, "
          f"needs manual review: {summary['unsure_needs_manual_review']}) "
          f"low={summary['low_band']} already_excluded={summary['already_excluded_count']}", file=sys.stderr)


if __name__ == "__main__":
    main()
