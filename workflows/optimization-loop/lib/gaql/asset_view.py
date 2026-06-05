"""GAQL for the asset-hygiene diagnostic stage.

Lifted verbatim from plugins/google-ads-optimization/skills/annonce-optimering/SKILL.md
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
    """Distinct RSA ad ids per (campaign, ad_group) -> count for the <2 challenger flag."""
    return """
SELECT campaign.name, ad_group.name, ad_group_ad.ad.id
FROM ad_group_ad
WHERE campaign.status = 'ENABLED'
  AND ad_group_ad.status = 'ENABLED'
  AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
""".strip()
