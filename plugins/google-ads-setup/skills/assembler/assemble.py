#!/usr/bin/env python3
"""Phase-4 assembler for campaign-build.

Pure transform: merges the four upstream JSON shapes (campaign-strategy, structuring,
rsa manifest, assets) into Ian's 10-tab review workbook + per-entity Google Ads Editor
CSVs, then runs validation. NO Google Ads API push, no external reads/writes — it only
reads local JSON and writes local files.

Reuses the hard field limits (headline 30 / description 90 / path 15) and the LEN+red
conditional-formatting technique from responsive-search-ads/sheet_layout.py — there is one
source of truth for those, not a retyped copy here.

Two hard emit-time guards (defense-in-depth, see references/assembler-contract.md):
  1. Every positive keyword row must have an explicit Exact or Phrase match type. A blank /
     missing / Broad match type makes Editor create a Broad keyword, violating the locked
     "Exact + selected Phrase, no Broad" policy. The assembler REFUSES to emit keywords.csv
     if any row fails this.
  2. Tab 09 validation recomputes LEN + Pass independently against the imported limits, so a
     human edit between Phase 3 and assembly that pushes a field over-length is still caught.

The inherited 277-term MCC shared negative list is NEVER emitted as CSV rows — it is applied
by reference (a tab-08 launch-gate line). Only client-specific additions become negative rows.
Monitor-first candidates go to tab 05 only, never the committed negatives CSV.
"""
import argparse
import csv
import importlib.util
import json
import os
import sys

# --- import the RSA layout module for the limits + CF technique (single source of truth) ---
_HERE = os.path.dirname(os.path.abspath(__file__))
_RSA_LAYOUT = os.path.normpath(
    os.path.join(_HERE, "..", "responsive-search-ads", "sheet_layout.py")
)


def _load_rsa_layout():
    spec = importlib.util.spec_from_file_location("rsa_sheet_layout", _RSA_LAYOUT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_layout = _load_rsa_layout()  # also pip-installs openpyxl on first run via its bootstrap
import openpyxl  # noqa: E402
from openpyxl.formatting.rule import CellIsRule  # noqa: E402
from openpyxl.styles import Alignment, Font, PatternFill  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

# Hard limits derived from the RSA layout's FIELDS — never retyped. FIELDS entries are
# (header, limit-or-None); the limit on "Headline 1"/"Description 1"/"Path 1" is the cap.
_LIMITS = {h.split()[0]: lim for h, lim in _layout.FIELDS if lim is not None}
HEADLINE_LIMIT = _LIMITS["Headline"]      # 30
DESCRIPTION_LIMIT = _LIMITS["Description"]  # 90
PATH_LIMIT = _LIMITS["Path"]               # 15

SHARED_NEG_NAME = "Generelle negative søgeord"
SHARED_NEG_ID = "6688642473"
SHARED_NEG_MCC = "1138360630"

HEADER_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
RED_FILL = PatternFill(start_color="F4C7C3", end_color="F4C7C3", fill_type="solid")
HEADER_FONT = Font(bold=True)


# --------------------------------------------------------------------------- helpers
def _ag_name(ag):
    return ag.get("name") or ag.get("ad_group") or ""


def _write_header(ws, headers):
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center")


def _autosize(ws, max_width=60):
    for idx, col in enumerate(ws.iter_cols(min_row=1, max_row=ws.max_row), start=1):
        widest = 0
        for cell in col:
            v = cell.value
            if v is None or str(v).startswith("="):
                continue
            widest = max(widest, len(str(v)))
        ws.column_dimensions[get_column_letter(idx)].width = max(8, min(max_width, widest + 2))


def _display_form(text, match_type):
    mt = (match_type or "").strip().lower()
    if mt == "exact":
        return f"[{text}]"
    if mt == "phrase":
        return f'"{text}"'
    return text


# --------------------------------------------------------------------------- guards
def assert_campaign_consistent(strategy, structuring, rsa_manifest, assets):
    names = {
        "campaign-strategy": strategy.get("campaign"),
        "structuring": structuring.get("campaign"),
        "rsa manifest": rsa_manifest.get("campaign"),
        "assets": assets.get("campaign"),
    }
    present = {k: v for k, v in names.items() if v}
    distinct = set(present.values())
    if len(distinct) > 1:
        raise SystemExit(
            "STOP: campaign name disagrees across input shapes (the human paste between "
            f"phases desynced them): {present}. Reconcile before assembling."
        )


def guard_rsa_paths_and_join(structuring, rsa_manifest):
    """Fail-before-write: every rsa artifact's ads.json must exist, and every RSA ad_group
    must match a structuring ad-group name (else ads.csv references a non-existent ad group)."""
    missing = [a.get("ads_json") for a in rsa_manifest.get("rsa_artifacts", [])
               if not a.get("ads_json") or not os.path.exists(a.get("ads_json"))]
    if missing:
        raise SystemExit(
            "STOP: rsa manifest references ads.json file(s) that do not exist (moved file or a "
            "relative path run from the wrong cwd). Cannot assemble an ad-less campaign:\n  "
            + "\n  ".join(str(m) for m in missing)
        )
    known = {_ag_name(ag) for ag in structuring.get("ad_groups", [])}
    rsa_ags = set()
    orphans = []
    for art in rsa_manifest.get("rsa_artifacts", []):
        with open(art["ads_json"], encoding="utf-8") as f:
            ag = json.load(f).get("ad_group") or art.get("ad_group", "")
        if ag:
            rsa_ags.add(ag)
        if ag and ag not in known:
            orphans.append(ag)
    if orphans:
        # Hard-exit: ads.csv would reference an ad group adgroups.csv never creates.
        raise SystemExit(
            "STOP: RSA ad_group(s) do not match any structuring ad-group name (ads.csv would "
            f"reference an ad group adgroups.csv never creates): {sorted(set(orphans))}. "
            f"Known ad groups: {sorted(known)}."
        )
    # Reverse direction is NOT a hard error (operator may build keywords first, ads later):
    # a structuring ad group with no RSA ships as a keywords-only group. Surface it as a
    # Must-pass launch gate in tab 08 instead of silently shipping a non-functional group.
    return sorted(known - rsa_ags)  # ad-less ad groups


def guard_positive_match_types(structuring):
    """Guard 1: every positive keyword has an explicit Exact or Phrase. No blank/Broad."""
    bad = []
    for ag in structuring.get("ad_groups", []):
        for kw in ag.get("keywords", []):
            mt = (kw.get("match_type") or "").strip().lower()
            if mt not in ("exact", "phrase"):
                bad.append(f"{_ag_name(ag)} / '{kw.get('text')}' -> '{kw.get('match_type')}'")
    if bad:
        raise SystemExit(
            "STOP: positive keyword rows with blank/Broad match type (would create Broad "
            "keywords on import, violating the no-Broad lock). Fix in structuring:\n  "
            + "\n  ".join(bad)
        )


# --------------------------------------------------------------------------- workbook tabs
def tab_readme(wb, strategy, meta):
    ws = wb.active
    ws.title = "00 README"
    _write_header(ws, ["Field", "Value"])
    rows = [
        ("Deliverable", meta.get("deliverable", "Google Ads campaign skeleton (campaign-build)")),
        ("Date", meta.get("date", "")),
        ("Account", strategy.get("account_id", "")),
        ("Campaign", strategy.get("campaign", "")),
        ("Important launch gate", strategy.get("tracking_prerequisite", "")),
        ("Import note", "CSV files use English Editor headers (auto-map any install). "
                        "Editor imports CSV only, not .xlsx. No API push."),
    ]
    for r in rows:
        ws.append(list(r))
    _autosize(ws)


def tab_campaign_settings(wb, strategy):
    """Mirror Ian's tab 01 exactly: 19 horizontal columns, header row + one data row."""
    ws = wb.create_sheet("01 Campaign settings")
    nets = strategy.get("networks", {})
    budget = strategy.get("budget_recommendation") or {}
    net_str = "; ".join(
        n for n, on in [("Search", nets.get("search")),
                        ("Search Partners", nets.get("search_partners")),
                        ("Display", nets.get("display"))] if on
    )
    # (header, value) in Ian's exact column order.
    pairs = [
        ("Account ID", strategy.get("account_id", "")),
        ("Campaign", strategy.get("campaign", "")),
        ("Campaign type", strategy.get("campaign_type", "Search")),
        ("Campaign state", strategy.get("campaign_state", "Paused until launch QA is complete")),
        ("Goal", strategy.get("goal", "Leads")),
        ("Budget recommendation", budget.get("rationale") or str(budget.get("daily_dkk", ""))),
        ("Bidding strategy", strategy.get("bidding_strategy", "")),
        ("Primary conversion action", strategy.get("primary_conversion_action", "")),
        ("Do not optimize toward", strategy.get("do_not_optimize_toward", "")),
        ("Location", strategy.get("location", "")),
        ("Location option", strategy.get("location_option", "")),
        ("Languages", "; ".join(strategy.get("languages", []))),
        ("Networks", net_str),
        ("Ad rotation", strategy.get("ad_rotation", "")),
        ("Start match types", strategy.get("start_match_types", "")),
        ("AI Max for Search", strategy.get("ai_max_for_search", "")),
        ("Target CPA switch rule", strategy.get("target_cpa_switch_rule", "")),
        ("Ad schedule", strategy.get("ad_schedule", "")),
        ("Tracking prerequisite", strategy.get("tracking_prerequisite", "")),
    ]
    _write_header(ws, [h for h, _ in pairs])
    ws.append([str(v) for _, v in pairs])
    _autosize(ws, max_width=45)


def tab_ad_groups(wb, structuring):
    ws = wb.create_sheet("02 Ad groups")
    cols = ["Campaign", "Ad group", "Intent", "Main kw", "Supporting queries",
            "Final URL", "Path 1", "Path 2", "Primary angles"]
    _write_header(ws, cols)
    campaign = structuring.get("campaign", "")
    for ag in structuring.get("ad_groups", []):
        kws = ag.get("keywords", [])
        main_kw = kws[0].get("text", "") if kws else ""
        supporting = "; ".join(k.get("text", "") for k in kws[1:])
        paths = ag.get("paths", ["", ""])
        ws.append([
            campaign, _ag_name(ag), ag.get("theme", ""), main_kw, supporting,
            ag.get("landing_page_url", ""),
            paths[0] if len(paths) > 0 else "",
            paths[1] if len(paths) > 1 else "",
            "; ".join(ag.get("angles", [])),
        ])
    _autosize(ws)


def tab_keywords(wb, structuring):
    ws = wb.create_sheet("03 Keywords")
    cols = ["Campaign", "Ad group", "Keyword", "Match type", "Keyword display",
            "Final URL", "Status", "Notes"]
    _write_header(ws, cols)
    campaign = structuring.get("campaign", "")
    for ag in structuring.get("ad_groups", []):
        for kw in ag.get("keywords", []):
            mt = kw.get("match_type", "")
            ws.append([
                campaign, _ag_name(ag), kw.get("text", ""), mt,
                _display_form(kw.get("text", ""), mt),
                ag.get("landing_page_url", ""),
                "Enabled after launch QA",
                structuring.get("keyword_volume_disclaimer", ""),
            ])
    _autosize(ws)


def tab_negatives(wb, structuring):
    ws = wb.create_sheet("04 Negative keywords")
    cols = ["Campaign", "Negative keyword", "Match type", "Category", "Reason"]
    _write_header(ws, cols)
    campaign = structuring.get("campaign", "")
    negs = structuring.get("negatives", {})
    shared = negs.get("inherited_shared_list", {})
    # Reference line ONLY — the 277 terms are applied by reference, never enumerated here.
    if shared.get("apply_by_reference"):
        ws.append([
            campaign,
            f"[SHARED LIST APPLIED BY REFERENCE: '{shared.get('name', SHARED_NEG_NAME)}' "
            f"id {shared.get('shared_set_id', SHARED_NEG_ID)}]",
            "(shared list)", "Inherited MCC list",
            "Attached as a launch-gate step (tab 08), not enumerated. See MCC "
            f"{shared.get('mcc_customer_id', SHARED_NEG_MCC)}.",
        ])
    for n in negs.get("client_specific_additions", []):
        ws.append([
            campaign, n.get("text", ""), n.get("match_type", "broad"),
            n.get("category", ""), n.get("why", ""),
        ])
    _autosize(ws)


def tab_monitor(wb, structuring):
    ws = wb.create_sheet("05 Monitor negatives")
    _write_header(ws, ["Candidate negative", "Default action", "Reason"])
    for m in structuring.get("negatives", {}).get("monitor_first_candidates", []):
        ws.append([m.get("text", ""), "Monitor first", m.get("why", "")])
    _autosize(ws)


def _rsa_rows(rsa_manifest):
    """Yield (ad_group, ad_label, final_url, paths, hypothesis, headlines, descriptions)
    for every RSA across the manifest, reading each artifact's ads.json.

    Fail loud on a missing/unresolvable ads.json: a barrier that silently drops an RSA
    and still reports success is exactly the corruption Phase 4 exists to prevent. Resolve
    relative paths against the manifest's own dir is the caller's job; here we hard-error."""
    missing = [a.get("ads_json") for a in rsa_manifest.get("rsa_artifacts", [])
               if not a.get("ads_json") or not os.path.exists(a.get("ads_json"))]
    if missing:
        raise SystemExit(
            "STOP: rsa manifest references ads.json file(s) that do not exist (a moved file "
            "or a relative path run from the wrong cwd). Cannot assemble an ad-less campaign:\n  "
            + "\n  ".join(str(m) for m in missing)
        )
    for art in rsa_manifest.get("rsa_artifacts", []):
        ads_path = art.get("ads_json")
        with open(ads_path, encoding="utf-8") as f:
            data = json.load(f)
        ad_group = data.get("ad_group") or art.get("ad_group", "")
        final_url = data.get("final_url") or art.get("final_url", "")
        ads = data.get("ads") or [data]  # single-RSA form is the object itself
        for i, ad in enumerate(ads, start=1):
            # `or default` (not get(k, default)): a JSON null must also fall back, else
            # len(None) crashes the build after the guards have already passed.
            paths = ad.get("paths") or ["", ""]
            yield (
                ad_group,
                f"RSA {i}" + (f" - {ad.get('vinkel')}" if ad.get("vinkel") else ""),
                ad.get("final_url") or final_url,
                paths,
                ad.get("hypotese") or "",
                ad.get("headlines") or [],
                ad.get("descriptions") or [],
            )


def tab_rsas(wb, structuring, rsa_manifest):
    ws = wb.create_sheet("06 RSAs")
    cols = (["Campaign", "Ad group", "Ad label", "Ad type", "Final URL", "Path 1", "Path 2",
             "Test hypothesis"]
            + [f"Headline {i}" for i in range(1, 16)]
            + [f"Description {i}" for i in range(1, 5)])
    _write_header(ws, cols)
    campaign = structuring.get("campaign", "")
    for ag, label, url, paths, hyp, hls, descs in _rsa_rows(rsa_manifest):
        row = [campaign, ag, label, "Responsive search ad", url,
               paths[0] if len(paths) > 0 else "", paths[1] if len(paths) > 1 else "", hyp]
        row += [(hls[i] if i < len(hls) else "") for i in range(15)]
        row += [(descs[i] if i < len(descs) else "") for i in range(4)]
        ws.append(row)
    _autosize(ws, max_width=40)


def tab_assets(wb, assets):
    ws = wb.create_sheet("07 Assets")
    cols = ["Campaign", "Asset type", "Asset text", "Final URL",
            "Description line 1", "Description line 2"]
    _write_header(ws, cols)
    campaign = assets.get("campaign", "")
    for s in assets.get("sitelinks", []):
        if s.get("url_source") == "omitted-unconfirmed" or not s.get("final_url"):
            continue  # Firewall B: never ship a guessed/unconfirmed sitelink URL
        ws.append([campaign, "Sitelink", s.get("text", ""), s.get("final_url", ""),
                   s.get("desc_line_1", ""), s.get("desc_line_2", "")])
    for c in assets.get("callouts", []):
        ws.append([campaign, "Callout", c.get("text", ""), "", "", ""])
    for sn in assets.get("structured_snippets", []):
        ws.append([campaign, "Structured snippet", sn.get("header", ""),
                   "; ".join(sn.get("values", [])), "", ""])
    _autosize(ws)


def tab_launch_qa(wb, strategy, structuring, adless_ad_groups=None):
    ws = wb.create_sheet("08 Launch QA")
    _write_header(ws, ["Priority", "Check", "Owner", "Launch gate"])
    nets = strategy.get("networks", {})
    shared = structuring.get("negatives", {}).get("inherited_shared_list", {})
    rows = [
        ("Critical", strategy.get("tracking_prerequisite",
         "HubSpot form conversion fires into Google Ads"), "Tracking/analytics", "Must pass"),
        ("Critical", "Do not optimize toward " + (strategy.get("do_not_optimize_toward")
         or "the unverified conversion") + " until it registers correctly",
         "Tracking/analytics", "Must pass"),
        ("High", "Keyword Planner volume and CPC confirm the daily budget (keywords are "
         "theme-derived, not volume-ranked)", "Paid search", "Should pass"),
        ("High", f"Location targeting is Presence only ({strategy.get('location', '')})",
         "Paid search", "Must pass"),
        ("High", "Search Partners and Display Expansion are off", "Paid search", "Must pass"),
        ("High", f"Attach shared negative list '{shared.get('name', SHARED_NEG_NAME)}' "
         f"(id {shared.get('shared_set_id', SHARED_NEG_ID)}) to the campaign",
         "Paid search", "Must pass"),
        ("High", "All client-specific negatives applied before enabling ads",
         "Paid search", "Must pass"),
        ("Medium", "Final URLs and UTM convention approved (assembler does not emit UTMs yet)",
         "Paid search", "Should pass"),
        ("Medium", "Sitelinks reviewed; confirmed real URLs (none guessed)",
         "Paid search", "Should pass"),
        ("Medium", "Structured-snippet header column verified in Editor (round-trip)",
         "Paid search", "Should pass"),
        ("Post-launch", "Search terms reviewed after 7, 14 and 30 days",
         "Paid search", "Post-launch"),
    ]
    # An ad group with keywords but no RSA is non-functional (no ad serves). Not a hard
    # error (operator may add ads later), but it must NOT ship silently — surface it.
    if adless_ad_groups:
        rows.insert(0, (
            "Critical",
            "Ad group(s) have keywords but NO RSA — no ad will serve. Add an RSA or remove "
            f"the ad group before enabling: {', '.join(adless_ad_groups)}",
            "Paid search", "Must pass",
        ))
    for r in rows:
        ws.append(list(r))
    _autosize(ws)


def tab_validation(wb, rsa_manifest):
    """Guard 2: recompute LEN + Pass independently against the imported limits."""
    ws = wb.create_sheet("09 Validation")
    _write_header(ws, ["Area", "Ad group", "Ad label", "Field", "Text", "Length", "Limit", "Pass"])
    failures = 0
    for ag, label, _url, paths, _hyp, hls, descs in _rsa_rows(rsa_manifest):
        items = (
            [("RSA headline", f"Headline {i+1}", t, HEADLINE_LIMIT) for i, t in enumerate(hls)]
            + [("RSA description", f"Description {i+1}", t, DESCRIPTION_LIMIT)
               for i, t in enumerate(descs)]
            + [("Display path", f"Path {i+1}", t, PATH_LIMIT)
               for i, t in enumerate(paths)]
        )
        for area, field, text, limit in items:
            length = len(text or "")
            ok = length <= limit
            if not ok:
                failures += 1
            cell_row = ws.max_row + 1
            ws.append([area, ag, label, field, text, length, limit, ok])
            if not ok:
                ws.cell(row=cell_row, column=8).fill = RED_FILL
                ws.cell(row=cell_row, column=6).fill = RED_FILL
    _autosize(ws, max_width=50)
    return failures


# --------------------------------------------------------------------------- CSVs
def _write_csv(path, headers, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for r in rows:
            w.writerow(r)


def emit_csvs(outdir, strategy, structuring, rsa_manifest, assets):
    os.makedirs(outdir, exist_ok=True)
    campaign = strategy.get("campaign", "") or structuring.get("campaign", "")
    written = []

    # campaigns.csv
    nets = strategy.get("networks", {})
    net_str = ";".join([n for n, on in
                        [("Google Search", nets.get("search")), ("Display", nets.get("display"))]
                        if on])
    budget = (strategy.get("budget_recommendation") or {}).get("daily_dkk", "")
    p = os.path.join(outdir, "campaigns.csv")
    _write_csv(p, ["Campaign", "Campaign type", "Budget", "Bid strategy type", "Networks",
                   "Language targeting", "Campaign status"],
               [[campaign, strategy.get("campaign_type", "Search"), budget,
                 strategy.get("bidding_strategy", ""), net_str or "Google Search",
                 ";".join(strategy.get("languages", [])), "Paused"]])
    written.append(p)

    # adgroups.csv
    rows = [[campaign, _ag_name(ag), ag.get("max_cpc", ""), "Enabled"]
            for ag in structuring.get("ad_groups", [])]
    p = os.path.join(outdir, "adgroups.csv")
    _write_csv(p, ["Campaign", "Ad group", "Max CPC", "Ad group status"], rows)
    written.append(p)

    # keywords.csv — guard already passed (explicit Exact/Phrase on every row)
    rows = []
    for ag in structuring.get("ad_groups", []):
        for kw in ag.get("keywords", []):
            rows.append([campaign, _ag_name(ag), kw.get("text", ""),
                         kw.get("match_type", ""), "Paused"])
    p = os.path.join(outdir, "keywords.csv")
    _write_csv(p, ["Campaign", "Ad group", "Keyword", "Match type", "Status"], rows)
    written.append(p)

    # negatives.csv — client-specific additions ONLY. NEVER the 277, NEVER monitor candidates.
    rows = []
    for n in structuring.get("negatives", {}).get("client_specific_additions", []):
        level = n.get("level", "campaign")
        ag = "" if level == "campaign" else n.get("ad_group", "")
        type_val = "Campaign negative" if level == "campaign" else "Negative"
        # Carry match type via the keyword-text bracket/quote syntax so Editor does not
        # default the negative to Broad. Broad negatives stay bare (correct default).
        kw_text = _display_form(n.get("text", ""), n.get("match_type", "broad"))
        rows.append([campaign, ag, kw_text, type_val])
    p = os.path.join(outdir, "negatives.csv")
    _write_csv(p, ["Campaign", "Ad group", "Keyword", "Type"], rows)
    written.append(p)

    # ads.csv (RSA) — Editor RSA columns, drop LEN/Vinkel/Hypotese.
    # "Ad group" (lowercase g) to match Ian's skeleton + the other 5 CSVs. Editor
    # auto-map is case-insensitive (answer 57747), but stay internally consistent.
    cols = (["Campaign", "Ad group", "Ad type", "Final URL", "Path 1", "Path 2"]
            + [f"Headline {i}" for i in range(1, 16)]
            + [f"Description {i}" for i in range(1, 5)])
    rows = []
    for ag, _label, url, paths, _hyp, hls, descs in _rsa_rows(rsa_manifest):
        row = [campaign, ag, "Responsive search ad", url,
               paths[0] if len(paths) > 0 else "", paths[1] if len(paths) > 1 else ""]
        row += [(hls[i] if i < len(hls) else "") for i in range(15)]
        row += [(descs[i] if i < len(descs) else "") for i in range(4)]
        rows.append(row)
    p = os.path.join(outdir, "ads.csv")
    _write_csv(p, cols, rows)
    written.append(p)

    # assets.csv — sitelinks/callouts/snippets. Lead forms emit NO row. Snippet header col UNVERIFIED.
    cols = ["Campaign", "Ad group", "Sitelink text", "Final URL", "Description line 1",
            "Description line 2", "Callout text", "Snippet header (UNVERIFIED col)", "Snippet Values"]
    rows = []
    acamp = assets.get("campaign", "") or campaign
    # Attachment level: campaign -> Campaign filled, Ad group blank; account -> the literal
    # "<Account-level>" string in the Campaign column (verified, Editor answer 56368).
    level = assets.get("attachment_level", "campaign")
    camp_cell = "<Account-level>" if level == "account" else acamp
    for s in assets.get("sitelinks", []):
        if s.get("url_source") == "omitted-unconfirmed" or not s.get("final_url"):
            continue
        rows.append([camp_cell, "", s.get("text", ""), s.get("final_url", ""),
                     s.get("desc_line_1", ""), s.get("desc_line_2", ""), "", "", ""])
    for c in assets.get("callouts", []):
        rows.append([camp_cell, "", "", "", "", "", c.get("text", ""), "", ""])
    for sn in assets.get("structured_snippets", []):
        rows.append([camp_cell, "", "", "", "", "", "", sn.get("header", ""),
                     ";".join(sn.get("values", []))])
    p = os.path.join(outdir, "assets.csv")
    _write_csv(p, cols, rows)
    written.append(p)

    return written


# --------------------------------------------------------------------------- main
def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description="Phase-4 campaign-build assembler (pure transform, no API push).")
    ap.add_argument("--strategy", required=True, help="campaign-strategy.json")
    ap.add_argument("--structuring", required=True, help="structuring.json")
    ap.add_argument("--rsa", required=True, help="rsa manifest json")
    ap.add_argument("--assets", required=True, help="assets.json")
    ap.add_argument("--workbook", required=True, help="output .xlsx path")
    ap.add_argument("--csvdir", required=True, help="output dir for per-entity CSVs")
    ap.add_argument("--date", default="", help="deliverable date (passed in; script can't call now)")
    args = ap.parse_args()

    strategy = load_json(args.strategy)
    structuring = load_json(args.structuring)
    rsa_manifest = load_json(args.rsa)
    assets = load_json(args.assets)

    # Reconcile + guards FIRST (fail loud before writing anything).
    assert_campaign_consistent(strategy, structuring, rsa_manifest, assets)
    guard_positive_match_types(structuring)
    adless_ad_groups = guard_rsa_paths_and_join(structuring, rsa_manifest)

    # Build the 10-tab workbook.
    wb = openpyxl.Workbook()
    tab_readme(wb, strategy, {"date": args.date})
    tab_campaign_settings(wb, strategy)
    tab_ad_groups(wb, structuring)
    tab_keywords(wb, structuring)
    tab_negatives(wb, structuring)
    tab_monitor(wb, structuring)
    tab_rsas(wb, structuring, rsa_manifest)
    tab_assets(wb, assets)
    tab_launch_qa(wb, strategy, structuring, adless_ad_groups)
    failures = tab_validation(wb, rsa_manifest)
    wb.save(args.workbook)

    written = emit_csvs(args.csvdir, strategy, structuring, rsa_manifest, assets)

    print(json.dumps({
        "workbook": args.workbook,
        "csvs": written,
        "validation_failures": failures,
        "adless_ad_groups": adless_ad_groups,
        "note": "No API push. Human imports the CSVs into Editor after approval. "
                "Shared negative list 6688642473 applied by reference (tab 08), not in any CSV.",
    }, ensure_ascii=False, indent=2))

    if failures:
        print(f"\nWARNING: {failures} field(s) over the hard limit — see tab 09 Validation "
              "(red). Fix before import.", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
