"""Change-history pull + bulk-collapse for the measure phase (Phase 0).

LIVE-VERIFIED against DSC (3069826320) on 2026-06-05 via `get_change_history`.
The loop's measure agent calls get_change_history(customer_id, lookback_days, limit);
this module documents the verified shape and provides the bulk-collapse the
`ads-changelog` skill established.

HARD CONSTRAINT (from ads-changelog, reconfirmed): change history reaches only ~30
days back. lookback_days must be <= 29 (30 raises START_DATE_TOO_OLD on the raw
change_event resource). Consequence the loop must honour: the loop's cadence has to be
<= 29 days, or this "what was applied" source goes blind. The SPEC sets cadence at
every 3-4 weeks for exactly this reason. An empty window means "no changes in the
window", NOT "account inactive".

Verified get_change_history response shape (per row):
{
  "timestamp": "2026-06-05 05:01:37.107871",
  "resource_type": "CAMPAIGN_BUDGET",     # CAMPAIGN | AD_GROUP | AD_GROUP_AD | AD_GROUP_CRITERION | CAMPAIGN_BUDGET | ...
  "operation": "UPDATE",                   # CREATE | UPDATE | REMOVE
  "user_email": "rkj@inboundcph.dk",       # who (incl. external agencies / Google recs)
  "client_type": "GOOGLE_ADS_WEB_CLIENT",
  "changed_fields": "amountMicros",
  "campaign_name": "...",
  "ad_group_name": ""                        # "" for campaign-level changes
}

BULK NOISE (verified vividly on DSC): one Editor upload writes many rows with the SAME
timestamp (e.g. 561 negative keywords = 1 paste, not 561 actions). DSC's window showed
~46 CAMPAIGN_BUDGET UPDATE rows clustered at a handful of identical timestamps from
three users. Raw counting overstates the work ~20x on bulk days. Always collapse on
(timestamp, user, resource_type, operation) and report one action.
"""
from __future__ import annotations

from collections import defaultdict

# lookback hard ceiling (raw resource is ~30 days; stay one under).
MAX_LOOKBACK_DAYS = 29


def safe_lookback(days: int) -> int:
    """Clamp a requested lookback to the verified <=29-day ceiling."""
    return min(int(days), MAX_LOOKBACK_DAYS)


def collapse(changes: list[dict]) -> list[dict]:
    """Collapse raw change rows into one action per (timestamp, user, resource, op).

    Returns a list of collapsed actions, newest first:
      { "date": "YYYY-MM-DD", "timestamp", "user_email", "resource_type",
        "operation", "count": N, "campaigns": [unique campaign names],
        "ad_groups": [unique non-empty ad group names], "changed_fields": [unique] }
    `count` is how many raw rows collapsed in (the bulk size). The consumer renders e.g.
    "rkj@ updated CAMPAIGN_BUDGET on 6 campaigns" instead of 6 separate lines.
    """
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for c in changes:
        key = (
            c.get("timestamp"),
            c.get("user_email"),
            c.get("resource_type"),
            c.get("operation"),
        )
        groups[key].append(c)

    collapsed = []
    for (ts, user, rtype, op), rows in groups.items():
        campaigns = sorted({r.get("campaign_name") for r in rows if r.get("campaign_name")})
        ad_groups = sorted({r.get("ad_group_name") for r in rows if r.get("ad_group_name")})
        fields = sorted({r.get("changed_fields") for r in rows if r.get("changed_fields")})
        collapsed.append({
            "date": (ts or "")[:10],
            "timestamp": ts,
            "user_email": user,
            "resource_type": rtype,
            "operation": op,
            "count": len(rows),
            "campaigns": campaigns,
            "ad_groups": ad_groups,
            "changed_fields": fields,
        })
    collapsed.sort(key=lambda a: a.get("timestamp") or "", reverse=True)
    return collapsed


def affected_ad_groups(collapsed: list[dict]) -> list[dict]:
    """Distinct (campaign, ad_group) pairs touched, for the before/after metric pull.

    Campaign-level-only changes (ad_groups empty) yield (campaign, None) so the metric
    pull can compare at campaign grain. This is what feeds source 3 of the measure phase
    (the two-window metrics delta), which is a SEPARATE pull not bound by the 29-day limit.
    """
    pairs = set()
    for a in collapsed:
        camps = a.get("campaigns") or []
        ags = a.get("ad_groups") or []
        if ags:
            for c in camps:
                for g in ags:
                    pairs.add((c, g))
        else:
            for c in camps:
                pairs.add((c, None))
    return [{"campaign": c, "ad_group": g} for (c, g) in sorted(pairs, key=lambda p: (p[0] or "", p[1] or ""))]
