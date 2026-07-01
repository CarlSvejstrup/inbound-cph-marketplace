"""GAQL for the asset-hygiene diagnostic stage.

Lifted verbatim from plugins/inbound-ads/skills/annonce-optimering/SKILL.md
(Trin 2). Field shape verified live 2026-05-29. Two pulls:
  asset_view_query  - per-asset rows (headline/description) on ENABLED RSAs
  rsa_count_query   - distinct RSA ids per (campaign, ad_group) for champion-challenger

Verified field shape (live 2026-05-29):
  ad_group_ad_asset_view.field_type        = HEADLINE | DESCRIPTION
  ad_group_ad_asset_view.performance_label = usually NOT_APPLICABLE / PENDING on
    Inbound's low-volume accounts (rarely BEST/GOOD/LOW). NOT a primary signal - the
    skill reports structural facts, never a per-asset CVR judgement (confounded +
    sub-significance). We pull the label only for internal status logic, never to render.
  per-asset clicks/conversions/cost_micros/impressions all return. cost is micros.

Hard rule: ENABLED campaigns AND ENABLED ads only. Paused = intentional, excluded.
"""
from __future__ import annotations

from . import window_clause


def asset_view_query(window) -> str:
    return f"""
SELECT
  campaign.name,
  ad_group.name,
  ad_group_ad_asset_view.field_type,
  ad_group_ad_asset_view.performance_label,
  asset.text_asset.text,
  metrics.impressions,
  metrics.clicks,
  metrics.conversions,
  metrics.cost_micros
FROM ad_group_ad_asset_view
WHERE campaign.status = 'ENABLED'
  AND ad_group_ad.status = 'ENABLED'
  AND {window_clause(window)}
""".strip()


def rsa_count_query() -> str:
    """Distinct RSA ad ids per (campaign, ad_group) -> count for the <2 challenger flag.

    SCOPED TO SEARCH (advertising_channel_type = 'SEARCH'). The RSA challenger heuristic only
    makes sense on Search campaigns — Display/Video campaigns have audience/targeting ad groups
    ("Combined segment", "Alle målgrupper") where 0 RSA is normal and an RSA does not belong.
    Without this filter those 0-RSA ad groups read as challenger candidates and the loop would
    generate RSAs for ad groups where RSAs make no sense (live finding on DSC)."""
    return """
SELECT campaign.name, ad_group.name, ad_group_ad.ad.id
FROM ad_group_ad
WHERE campaign.status = 'ENABLED'
  AND ad_group_ad.status = 'ENABLED'
  AND campaign.advertising_channel_type = 'SEARCH'
  AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
""".strip()


def search_ad_groups_query() -> str:
    """All ENABLED ad groups on ENABLED SEARCH campaigns -> the DENOMINATOR for the <2-RSA flag.

    rsa_count_query (FROM ad_group_ad WHERE type=RSA) can only return ad groups that HAVE an RSA,
    so it can never surface an ad group with ZERO RSAs. To flag a Search ad group missing a
    challenger you need the full set of Search ad groups and subtract those the count query
    covered. This query is that full set, already scoped to SEARCH so Display/Video ad groups are
    never in the denominator. The agent computes: missing-RSA = (this set) - (ad groups in
    rsa_count_query with >=2 RSAs)."""
    return """
SELECT campaign.name, ad_group.name
FROM ad_group
WHERE campaign.status = 'ENABLED'
  AND ad_group.status = 'ENABLED'
  AND campaign.advertising_channel_type = 'SEARCH'
""".strip()
