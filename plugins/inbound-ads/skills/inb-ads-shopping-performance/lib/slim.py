#!/usr/bin/env python3
"""Slim + normalize a Shopping product/IS pull down to the few fields a judgement needs.

WHY THIS EXISTS
    The raw GAQL rows from shopping_performance_view carry two traps that will silently corrupt any
    naive parse (both observed live against Light-Point, 2026-07-16):

      1. MIXED TYPES in one row. cost_micros / impressions / clicks come back as STRINGS ("9632");
         conversions / conversions_value / all impression-share metrics come back as FLOATS (0.0).
         Summing them without casting either crashes or concatenates strings.
      2. EMPTY SEGMENT KEYS ARE OMITTED, not null. A product with no brand simply has no
         "product_brand" key in its segments block. Code that does row["segments"]["product_brand"]
         raises KeyError on exactly the rows that matter (sparse feeds).

    This module is the single choke point that casts every metric correctly and treats missing keys
    as empty strings. It also aggregates the same product_item_id across rows (a product can appear
    once per campaign) so downstream logic reasons about products, not row fragments.

NOT A JUDGE. It only reshapes. Every verdict happens in the conversation.

Usage (as a library, imported by digest.py):
    import slim
    products = slim.slim_products(raw_json)      # list[dict] with clean numeric fields
    campaigns = slim.slim_is(raw_is_json)         # list[dict] impression-share per campaign
"""
from __future__ import annotations

from typing import Any


def _rows(raw: Any) -> list[dict]:
    """Accept a bare list, {"results": [...]}, or {"result": "<json-string>"} and return the rows."""
    import json

    if isinstance(raw, str):
        raw = json.loads(raw)
    if isinstance(raw, dict):
        if "results" in raw:
            return raw["results"]
        if "result" in raw:
            inner = raw["result"]
            if isinstance(inner, str):
                inner = json.loads(inner)
            if isinstance(inner, dict) and "results" in inner:
                return inner["results"]
            return inner if isinstance(inner, list) else []
        # a single flat object
        return [raw]
    return raw if isinstance(raw, list) else []


def _f(v: Any) -> float:
    """Cast a metric that may be a JSON string OR float OR missing to float."""
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _i(v: Any) -> int:
    return int(_f(v))


def _seg(row: dict, key: str) -> str:
    """Read a segment value, returning '' if the key was omitted (empty) from the payload."""
    return (row.get("segments") or {}).get(key, "") or ""


def slim_products(raw: Any) -> list[dict]:
    """Normalize product rows and aggregate by product_item_id across campaigns.

    Returns one dict per product with clean numeric fields and derived ROAS/CPA.
    """
    agg: dict[str, dict] = {}
    for row in _rows(raw):
        m = row.get("metrics") or {}
        pid = _seg(row, "product_item_id")
        # Key on product_item_id when present; else fall back to title so rows without an id
        # (seen on some accounts) still aggregate instead of vanishing.
        title = _seg(row, "product_title")
        key = pid or title or "(uden id/titel)"

        rec = agg.setdefault(
            key,
            {
                "product_item_id": pid,
                "product_title": title,
                "product_brand": _seg(row, "product_brand"),
                "product_type_l1": _seg(row, "product_type_l1"),
                "custom_label_0": _seg(row, "product_custom_attribute0"),
                "custom_label_1": _seg(row, "product_custom_attribute1"),
                "campaigns": set(),
                "cost_micros": 0,
                "clicks": 0,
                "impressions": 0,
                "conversions": 0.0,
                "conversions_value": 0.0,
            },
        )
        # Backfill descriptive fields if the first row that created the record had them empty.
        for fld, seg in (
            ("product_title", "product_title"),
            ("product_brand", "product_brand"),
            ("product_type_l1", "product_type_l1"),
        ):
            if not rec[fld]:
                rec[fld] = _seg(row, seg)
        camp = (row.get("campaign") or {}).get("name", "")
        if camp:
            rec["campaigns"].add(camp)
        rec["cost_micros"] += _i(m.get("cost_micros"))
        rec["clicks"] += _i(m.get("clicks"))
        rec["impressions"] += _i(m.get("impressions"))
        rec["conversions"] += _f(m.get("conversions"))
        rec["conversions_value"] += _f(m.get("conversions_value"))

    out = []
    for rec in agg.values():
        rec["campaigns"] = sorted(rec["campaigns"])
        cost = rec["cost_micros"] / 1_000_000
        rec["cost"] = round(cost, 2)
        rec["roas"] = round(rec["conversions_value"] / cost, 2) if cost > 0 else 0.0
        rec["cpa"] = (
            round(cost / rec["conversions"], 2) if rec["conversions"] > 0 else None
        )
        out.append(rec)
    out.sort(key=lambda r: r["cost_micros"], reverse=True)
    return out


def slim_is(raw: Any) -> list[dict]:
    """Normalize campaign-level impression-share rows (pull B)."""
    out = []
    for row in _rows(raw):
        m = row.get("metrics") or {}
        c = row.get("campaign") or {}
        cost = _i(m.get("cost_micros")) / 1_000_000
        out.append(
            {
                "campaign": c.get("name", ""),
                "channel": c.get("advertising_channel_type", ""),
                "impression_share": _f(m.get("search_impression_share")),
                "budget_lost_is": _f(m.get("search_budget_lost_impression_share")),
                "rank_lost_is": _f(m.get("search_rank_lost_impression_share")),
                "cost": round(cost, 2),
                "conversions_value": _f(m.get("conversions_value")),
                "roas": round(_f(m.get("conversions_value")) / cost, 2) if cost > 0 else 0.0,
            }
        )
    out.sort(key=lambda r: r["cost"], reverse=True)
    return out
