"""GAQL query builders for the optimization loop.

Every query string here was lifted verbatim from a skill SKILL.md whose field shapes
are already live-verified against real Inbound accounts. Do not re-invent field names;
re-verify against the API only if Google bumps the version.

Shared gotcha (verified live, reconfirmed 2026-05-29): GAQL has NO `LAST_90_DAYS`
literal. Only a few DURING literals work (LAST_30_DAYS, LAST_7_DAYS, LAST_14_DAYS,
TODAY, YESTERDAY). For anything else, compute a concrete BETWEEN range. `window_clause`
centralises that rule so every module uses one window everywhere.
"""
from __future__ import annotations

_DURING_LITERALS = {
    "LAST_30_DAYS", "LAST_7_DAYS", "LAST_14_DAYS",
    "TODAY", "YESTERDAY", "THIS_MONTH", "LAST_MONTH",
}


def window_clause(window) -> str:
    """Return a `segments.date` predicate for a window spec.

    window can be:
      - a string DURING literal that GAQL actually supports (e.g. "LAST_30_DAYS")
      - a (start, end) tuple/list of 'YYYY-MM-DD' strings -> BETWEEN
    Raises ValueError on an unsupported bare literal (e.g. "LAST_90_DAYS"), which is the
    exact mistake the skills document.
    """
    if isinstance(window, str):
        lit = window.strip().upper()
        if lit in _DURING_LITERALS:
            return f"segments.date DURING {lit}"
        raise ValueError(
            f"{window!r} is not a valid GAQL DURING literal. "
            f"For windows other than {sorted(_DURING_LITERALS)}, pass a (start, end) "
            f"'YYYY-MM-DD' tuple so we emit BETWEEN. (LAST_90_DAYS is NOT a literal.)"
        )
    if isinstance(window, (tuple, list)) and len(window) == 2:
        start, end = window
        return f"segments.date BETWEEN '{start}' AND '{end}'"
    raise ValueError(f"unsupported window spec: {window!r}")
