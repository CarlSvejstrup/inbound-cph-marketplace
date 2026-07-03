# Quality Score pull: shared contract

Read this before pulling or reporting Quality Score (QS) in any inbound-ads skill. This is the single source of truth for how QS is fetched, what grain it lives at, and what shape it returns. `inb-ads-quality-score`, `inb-ads-account-audit`, and `inb-ads-onboarding-analysis` all cite this file so the three call sites stay identical.

LIVE-VERIFIED against DSC (customer `3069826320`) on 2026-06-05 via the `get_quality_score_audit` MCP tool.

## How to pull it: the MCP tool, not raw GAQL

Fetch QS through the Google Ads MCP tool, not by hand-writing GAQL:

```
get_quality_score_audit(customer_id, date_range)
```

- `customer_id`: the client's Google Ads account ID (no dashes), from the client's AI Context / `clients/*.md` frontmatter.
- `date_range`: a GAQL date range. See the gotcha below.

The tool wraps the underlying `keyword_view` query internally; you do not write the GAQL. If you ever need the raw query for reference, it is `SELECT ad_group_criterion.quality_info.quality_score, .post_click_quality_score, .creative_quality_score, .search_predicted_ctr` from `keyword_view` filtered to enabled keywords, but the tool is the contract, GAQL is not.

## Date-range gotcha (the one that bites)

`LAST_90_DAYS` behaves differently depending on the layer:

- **As the MCP tool's `date_range=` argument: VALID.** `get_quality_score_audit(customer_id, date_range="LAST_90_DAYS")` works: the tool resolves the window internally. This is what `inb-ads-account-audit` and `inb-ads-onboarding-analysis` pass ("LAST_90_DAYS altid").
- **As a raw GAQL `DURING` literal: INVALID.** If you drop to hand-written GAQL, `DURING LAST_90_DAYS` raises `INVALID_VALUE_WITH_DURING_OPERATOR` (verified live 2026-06-05). The valid raw-GAQL literals stop at `LAST_30_DAYS`; for 90 days you must compute a concrete `BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'` window.

Rule: prefer the MCP tool and pass `LAST_90_DAYS` (QS wants volume, so a 90-day window beats 30). Only if you fall back to raw GAQL, never emit the bare `LAST_90_DAYS` literal; compute the `BETWEEN` dates instead. The `date_range_arg()` helper in `inb-ads-optimization-loop/lib/gaql/quality_score.py` enforces the strict raw-GAQL rule (it rejects `LAST_90_DAYS` and turns a `(start, end)` tuple into a `BETWEEN` clause); the `inb-ads-quality-score` skill may bundle its own copy of that module.

## Grain: QS is a KEYWORD score; landing page is a FLAG, not a score

CRITICAL, verified: **Quality Score lives at KEYWORD grain.** There is no native ad-group or campaign Quality Score, so never fabricate one. The tool returns the worst keywords (20 by default) each with an overall `quality_score` (1-10) plus three component labels:

- `creative_quality`: the ad-relevance / creative component.
- `landing_page_quality`: the post-click / landing-page component.
- `expected_ctr`: the expected click-through-rate component.

Each component is a **label**, not a number: `BELOW_AVERAGE | AVERAGE | ABOVE_AVERAGE`. In particular, **landing-page quality is a FLAG, not a numeric score**: the API never gives an "LP score". Report the client's underperforming landing pages as a flagged component on the affected keywords, with the keyword + ad group for context. Do not invent an "LP score %".

## Normalized output shape

Raw tool response (`get_quality_score_audit`):

```
{
  "total_keywords_with_qs": 286,
  "average_quality_score": 6.4,
  "distribution": { "1": 11, "2": 8, ..., "10": 31 },   # QS 1-10 -> keyword count
  "worst_keywords": [
    { "campaign_name", "ad_group_name", "keyword", "match_type",
      "quality_score": 1,
      "creative_quality":     "BELOW_AVERAGE|AVERAGE|ABOVE_AVERAGE",
      "landing_page_quality": "BELOW_AVERAGE|AVERAGE|ABOVE_AVERAGE",
      "expected_ctr":         "BELOW_AVERAGE|AVERAGE|ABOVE_AVERAGE",
      "impressions", "cost" }
  ]
}
```

Normalized shape (what `normalise_findings()` returns and what skills should render from):

```
{
  "average_quality_score": float,
  "spend_by_qs": [ {"qs": 1, "keyword_count": 11}, ... ],   # sorted 1..10, for the QS-distribution chart
  "flagged_keywords": [                                       # KEYWORD grain (verified)
     { "campaign", "ad_group", "keyword", "match_type", "quality_score",
       "creative_quality", "landing_page_quality", "expected_ctr",
       "impressions", "cost", "lp_below_average": bool }
  ]
}
```

- `spend_by_qs` is the QS 1-10 keyword-count distribution; feed it straight into the account-audit's inline SVG bar chart of QS distribution.
- `lp_below_average` is `true` exactly when `landing_page_quality == "BELOW_AVERAGE"`. It is a convenience flag for the one lever a skill can most directly act on, not a score.

## QS is a diagnostic signal: recommend-only

QS is read-only intelligence. The pull and everything derived from it (flagged keywords, LP flags, the distribution chart) is **recommend-only**: none of these skills ever writes to the account off the back of a QS finding.

Map each weak component to its lever, and state the lever as a recommendation:

- `creative_quality` BELOW_AVERAGE → tighter ad relevance / RSA rewrite (hand to `inb-ads-rsa-copy` or `inb-ads-rsa-hygiene`).
- `landing_page_quality` BELOW_AVERAGE → landing-page fix (a client-side change; recommend it).
- `expected_ctr` BELOW_AVERAGE → keyword / structure / bid work.

Any actual bid, keyword, or structural change that follows is a separate, explicit step and must go through the **`ads-writer` agent, HITL-confirmed per action**, never an autonomous write. Budget writes additionally wait on the budget-guardrail. QS itself only tells you where to look.
