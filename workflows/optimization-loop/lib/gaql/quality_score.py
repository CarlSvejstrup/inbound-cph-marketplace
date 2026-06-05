"""Quality Score diagnostic pull for the optimization loop.

LIVE-VERIFIED against DSC (3069826320) on 2026-06-05 via the
`get_quality_score_audit` MCP tool. This module documents the verified shape and
provides the normalisation the loop's QS agent uses; the actual fetch is the MCP
tool call (the loop's agent calls `get_quality_score_audit(customer_id, date_range)`).

CRITICAL GRAIN FACT (verified): Quality Score lives at KEYWORD grain. There is no
native ad-group Quality Score. The tool returns the 20 worst keywords with their
three component labels. So the loop reports flagged KEYWORDS (with the ad group they
sit in), never a fabricated "ad-group QS". This is the same grain discipline as the
search-term-vs-asset distinction in the critique.

Verified tool response shape (get_quality_score_audit):
{
  "total_keywords_with_qs": 286,
  "average_quality_score": 6.4,
  "distribution": { "1": 11, "2": 8, ..., "10": 31 },   # QS 1-10 -> keyword count
  "worst_keywords": [
    { "campaign_name", "ad_group_name", "keyword", "match_type",
      "quality_score": 1,                       # overall keyword QS, 1-10
      "creative_quality":     "BELOW_AVERAGE|AVERAGE|ABOVE_AVERAGE",
      "landing_page_quality": "BELOW_AVERAGE|AVERAGE|ABOVE_AVERAGE",
      "expected_ctr":         "BELOW_AVERAGE|AVERAGE|ABOVE_AVERAGE",
      "impressions", "cost" }
  ]
}

DATE LITERAL: the tool accepts a GAQL date range. LAST_90_DAYS is NOT a valid DURING
literal (verified: the tool raised INVALID_VALUE_WITH_DURING_OPERATOR on 2026-06-05).
Use LAST_30_DAYS or a concrete BETWEEN range. QS wants volume, so prefer a 30-day
literal or an explicit ~90-day BETWEEN window, never the bare LAST_90_DAYS literal.
"""
from __future__ import annotations

# The three QS components, as the API labels them.
COMPONENTS = ("creative_quality", "landing_page_quality", "expected_ctr")
_LABELS = {"BELOW_AVERAGE", "AVERAGE", "ABOVE_AVERAGE"}


def date_range_arg(window) -> str:
    """Return a valid date_range string for get_quality_score_audit.

    window: "LAST_30_DAYS" (or other valid literal) or a (start, end) tuple.
    Guards against the LAST_90_DAYS literal the tool rejects.
    """
    if isinstance(window, str):
        lit = window.strip().upper()
        if lit == "LAST_90_DAYS":
            raise ValueError(
                "LAST_90_DAYS is not a valid date literal for get_quality_score_audit "
                "(verified live). Pass a (start, end) tuple for a 90-day window, or use "
                "LAST_30_DAYS."
            )
        return lit
    if isinstance(window, (tuple, list)) and len(window) == 2:
        start, end = window
        return f"BETWEEN '{start}' AND '{end}'"
    raise ValueError(f"unsupported window spec: {window!r}")


def normalise_findings(audit: dict, lp_focus: bool = True) -> dict:
    """Turn a raw get_quality_score_audit response into the loop's QS contract.

    Returns:
      {
        "average_quality_score": float,
        "spend_by_qs": [ {"qs": 1, "keyword_count": 11} ],   # for the summary chart
        "flagged_keywords": [                                  # KEYWORD grain (verified)
           { "campaign", "ad_group", "keyword", "match_type", "quality_score",
             "creative_quality", "landing_page_quality", "expected_ctr",
             "impressions", "cost", "lp_below_average": bool }
        ]
      }
    lp_focus marks keywords whose landing_page_quality is BELOW_AVERAGE, because LP is
    the lever the loop can actually act on (creative -> RSA rewrite; expected_ctr ->
    keyword/structure). LP stays a FLAG + the keyword's context, never a numeric LP
    score the API does not provide.
    """
    dist = audit.get("distribution", {}) or {}
    spend_by_qs = [
        {"qs": int(qs), "keyword_count": int(n)}
        for qs, n in sorted(dist.items(), key=lambda kv: int(kv[0]))
    ]
    flagged = []
    for kw in audit.get("worst_keywords", []) or []:
        lp = kw.get("landing_page_quality")
        flagged.append({
            "campaign": kw.get("campaign_name"),
            "ad_group": kw.get("ad_group_name"),
            "keyword": kw.get("keyword"),
            "match_type": kw.get("match_type"),
            "quality_score": kw.get("quality_score"),
            "creative_quality": kw.get("creative_quality"),
            "landing_page_quality": lp,
            "expected_ctr": kw.get("expected_ctr"),
            "impressions": kw.get("impressions"),
            "cost": kw.get("cost"),
            "lp_below_average": (lp == "BELOW_AVERAGE"),
        })
    return {
        "average_quality_score": audit.get("average_quality_score"),
        "spend_by_qs": spend_by_qs,
        "flagged_keywords": flagged,
    }
