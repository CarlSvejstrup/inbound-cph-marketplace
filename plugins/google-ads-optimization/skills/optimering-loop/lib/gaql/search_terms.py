"""GAQL for the search-term diagnostic stage.

Lifted verbatim from plugins/google-ads-optimization/_archive/search-terms/SKILL.md
(Trin 2). Field shapes verified live against a real account. Three pulls:
  search_terms_query    - the search_term_view pull (cost-desc, ENABLED, spend floor)
  keyword_map_query     - the keyword_view map for structural placement detection
  ad_group_ads_query    - each ad group's final URL + headlines for intent detection
  account_search_cost_query - total search cost for coverage reporting

Hard rule baked in: campaign.status = 'ENABLED' everywhere. Paused campaigns are
intentional and never analysed (Inbound rule).

Cost is micros: DKK = cost_micros / 1_000_000. metrics.ctr is a fraction (x100 for %).
"""
from __future__ import annotations

from . import window_clause

# Spend floor in micros: 5 DKK = 5_000_000 micros (the skill's SPEND_FLOOR default).
DEFAULT_SPEND_FLOOR_MICROS = 5_000_000


def search_terms_query(window, spend_floor_micros: int = DEFAULT_SPEND_FLOOR_MICROS,
                       limit: int = 500) -> str:
    return f"""
SELECT
  search_term_view.search_term,
  campaign.id, campaign.name,
  ad_group.id, ad_group.name,
  segments.keyword.info.text, segments.keyword.info.match_type,
  segments.search_term_match_type,
  metrics.cost_micros, metrics.clicks, metrics.conversions,
  metrics.conversions_value, metrics.impressions, metrics.ctr
FROM search_term_view
WHERE {window_clause(window)}
  AND campaign.status = 'ENABLED'
  AND metrics.cost_micros > {spend_floor_micros}
ORDER BY metrics.cost_micros DESC
LIMIT {limit}
""".strip()


def keyword_map_query() -> str:
    """The whole ENABLED keyword map (text + match type + ad group + campaign).

    Used to build normalised_keyword -> [{campaign, ad_group, match_type}] for the
    placement (struktur) cross-check. The consumer must filter test/duplicate campaigns
    (heuristic /w2m|test|vol 2/i) before trusting a 'canonical home' - see SKILL.md.
    """
    return """
SELECT
  ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type,
  campaign.name, ad_group.name
FROM keyword_view
WHERE campaign.status = 'ENABLED' AND ad_group_criterion.status = 'ENABLED'
""".strip()


def ad_group_ads_query() -> str:
    """Each ENABLED ad group's final URLs + RSA headlines, for intent-mismatch detection.

    Build (campaign, ad_group) -> {final_urls, headlines[top 6 unpinned]} downstream.
    """
    return """
SELECT campaign.name, ad_group.name,
       ad_group_ad.ad.final_urls,
       ad_group_ad.ad.responsive_search_ad.headlines
FROM ad_group_ad
WHERE campaign.status = 'ENABLED'
  AND ad_group_ad.status = 'ENABLED'
""".strip()


def account_search_cost_query(window) -> str:
    """Total ENABLED Search spend over the window, for coverage % in Oversigt."""
    return f"""
SELECT metrics.cost_micros FROM campaign
WHERE {window_clause(window)}
  AND campaign.status = 'ENABLED'
  AND campaign.advertising_channel_type = 'SEARCH'
""".strip()
