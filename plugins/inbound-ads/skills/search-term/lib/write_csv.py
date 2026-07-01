#!/usr/bin/env python3
"""Write the AGREED search-term decisions straight into Google Ads Editor import CSVs.

This is the deterministic tail of the conversational `search-term` skill. The CONVERSATION decides
WHAT goes in (which terms become negatives, which become new keywords, at what match type, at what
level); this script only renders those decisions into the exact CSV shapes Google Ads Editor's bulk
upload expects. No judgement here — if you find yourself wanting to classify a term in this file,
stop: that belongs in the conversation.

The column contracts mirror the sibling editor-csv-export/export_csv.py (the verified Editor
schemas) so the two skills stay consistent. Editor imports CSV only (not .xlsx).

INPUT: a decisions JSON ->
    {
      "client": "Capio", "account_id": "4636067288",
      "negatives": [
        {"keyword": "naya kardiologi", "match_type": "phrase",
         "level": "campaign"|"ad_group"|"account",   # default campaign
         "campaign": "IC | GSN | Hellerup",           # required unless level=account
         "ad_group": "MR-helkropsscanning",           # required only when level=ad_group
         "list_name": "<INDSÆT NEGATIVLISTE-NAVN>"}    # only when targeting a shared neg list
      ],
      "new_keywords": [
        {"keyword": "helkropsscanning aarhus", "match_type": "exact",
         "campaign": "IC | GSN | Aarhus", "ad_group": "MR-helkropsscanning"}
      ]
    }

OUTPUT: up to two CSVs (negatives.csv, new-keywords.csv). >1 file -> a .zip; exactly 1 -> the bare
CSV. Path(s) printed to stdout as JSON so the skill can hand them to the user.

HARD GUARDS (refuse rather than ship a broken import):
  - New positive keywords: match type MUST be Exact or Phrase, never Broad/blank (Inbound rule;
    mirrors export_csv build_keywords). A blank/Broad positive keyword aborts the file.
  - A negative needs a target: campaign (campaign/ad_group level) OR a list_name (shared-list
    upload) OR level=account. No target -> abort with a clear message, never a silent half-row.
  - Æ Ø Å preserved: UTF-8 with BOM (utf-8-sig) so Editor + Excel read Danish correctly on Windows.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import zipfile
from pathlib import Path

# --- limits / literals (mirror editor-csv-export so the two skills agree) -----------------------
ACCOUNT_LEVEL_LITERAL = "<Account-level>"   # Editor's literal for an account-level negative
VALID_POSITIVE_MATCH = {"exact", "phrase"}  # positives never Broad/blank (Inbound hard rule)
VALID_NEG_MATCH = {"exact", "phrase", "broad"}


def _s(v) -> str:
    return "" if v is None else str(v).strip()


def _cap(mt: str) -> str:
    """Editor wants 'Exact' / 'Phrase' / 'Broad' (capitalised)."""
    return _s(mt).capitalize()


def _display_negative(text: str, match_type: str) -> str:
    """Editor expects a negative keyword in bracket/quote form for its match type
    (mirrors export_csv._display_negative). Exact -> [kw]; Phrase -> "kw"; Broad -> bare."""
    mt = _s(match_type).lower()
    if mt == "exact":
        return f"[{text}]"
    if mt == "phrase":
        return f'"{text}"'
    return text


def _write_csv(path: str, fieldnames: list, rows: list) -> None:
    # utf-8-sig so Danish æ/ø/å survive in Editor + Excel on Windows.
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


# --------------------------------------------------------------------------- builders
def build_negative_rows(negatives: list) -> tuple[list, list]:
    """Return (fieldnames, rows) for the negatives CSV.

    Two shapes coexist in Editor and we pick per row by what the decision targets:
      - SHARED NEGATIVE LIST upload (a row carries `list_name`): the negative-list bulk template.
        Columns: Action, Negative keyword list name, Negative keyword, Match type.
      - CAMPAIGN / AD-GROUP / ACCOUNT negative (no list_name): the in-account negative template.
        Columns: Action, Campaign, Ad group, Keyword (bracketed), Type.
    To keep ONE clean file we emit the in-account shape by default, and the shared-list shape only
    if ANY row carries list_name (then ALL rows must, else we abort — mixing the two in one CSV
    confuses Editor's importer).
    """
    if not negatives:
        return [], []

    uses_list = [bool(_s(n.get("list_name"))) for n in negatives]
    if any(uses_list) and not all(uses_list):
        raise SystemExit("ABORT negatives: mix of shared-list and in-account negatives in one file. "
                         "Split them into two runs (a negative either goes on a shared list OR onto "
                         "a campaign/ad group, not ambiguously both).")

    if all(uses_list) and negatives:
        # shared negative-list bulk-upload template
        fields = ["Action", "Negative keyword list name", "Negative keyword", "Match type"]
        rows = []
        for n in negatives:
            kw = _s(n.get("keyword"))
            if not kw:
                raise SystemExit("ABORT negatives: a row has an empty keyword.")
            mt = _s(n.get("match_type")).lower() or "phrase"
            if mt not in VALID_NEG_MATCH:
                raise SystemExit(f"ABORT negatives: invalid match type '{mt}' for '{kw}'.")
            rows.append({
                "Action": "Add",
                "Negative keyword list name": _s(n.get("list_name")),
                "Negative keyword": _display_negative(kw, mt),
                "Match type": _cap(mt),
            })
        return fields, rows

    # in-account (campaign / ad group / account) negative template
    fields = ["Action", "Campaign", "Ad group", "Keyword", "Type"]
    rows = []
    for n in negatives:
        kw = _s(n.get("keyword"))
        if not kw:
            raise SystemExit("ABORT negatives: a row has an empty keyword.")
        mt = _s(n.get("match_type")).lower() or "phrase"
        if mt not in VALID_NEG_MATCH:
            raise SystemExit(f"ABORT negatives: invalid match type '{mt}' for '{kw}'.")
        level = _s(n.get("level")).lower() or "campaign"
        campaign = _s(n.get("campaign"))
        ad_group = _s(n.get("ad_group"))
        if level == "account":
            campaign = ACCOUNT_LEVEL_LITERAL
            ad_group = ""
            type_lit = "Campaign negative"
        elif level == "ad_group":
            if not campaign or not ad_group:
                raise SystemExit(f"ABORT negatives: ad-group negative '{kw}' needs both campaign + ad group.")
            type_lit = "Negative"
        else:  # campaign
            if not campaign:
                raise SystemExit(f"ABORT negatives: campaign negative '{kw}' needs a campaign name "
                                 "(or set level=account / give a list_name).")
            ad_group = ""
            type_lit = "Campaign negative"
        rows.append({
            "Action": "Add",
            "Campaign": campaign,
            "Ad group": ad_group,
            "Keyword": _display_negative(kw, mt),
            "Type": type_lit,
        })
    return fields, rows


def build_new_keyword_rows(new_keywords: list) -> tuple[list, list]:
    """Return (fieldnames, rows) for the new-keywords (winners) CSV. Added Paused (champion-
    challenger: never auto-enable a promoted term). Mirrors export_csv build_keywords + its
    no-Broad guard."""
    if not new_keywords:
        return [], []
    fields = ["Action", "Campaign", "Ad group", "Keyword", "Match type", "Status"]
    rows = []
    for k in new_keywords:
        kw = _s(k.get("keyword"))
        camp = _s(k.get("campaign"))
        ag = _s(k.get("ad_group"))
        mt = _s(k.get("match_type")).lower()
        if not kw:
            raise SystemExit("ABORT new keywords: a row has an empty keyword.")
        if mt not in VALID_POSITIVE_MATCH:
            raise SystemExit(f"ABORT new keywords: '{kw}' has match type '{mt or '(blank)'}'. "
                             "Positive keywords must be Exact or Phrase, never Broad/blank.")
        if not camp or not ag:
            raise SystemExit(f"ABORT new keywords: '{kw}' needs both a campaign and an ad group "
                             "(a new keyword has to land somewhere).")
        rows.append({
            "Action": "Add",
            "Campaign": camp,
            "Ad group": ag,
            "Keyword": kw,
            "Match type": _cap(mt),
            "Status": "Paused",
        })
    return fields, rows


# --------------------------------------------------------------------------- main
def run(decisions: dict, outdir: str, slug: str) -> dict:
    os.makedirs(outdir, exist_ok=True)
    written = []

    neg_fields, neg_rows = build_negative_rows(decisions.get("negatives") or [])
    if neg_rows:
        p = os.path.join(outdir, f"{slug} - negative keywords.csv")
        _write_csv(p, neg_fields, neg_rows)
        written.append(p)

    kw_fields, kw_rows = build_new_keyword_rows(decisions.get("new_keywords") or [])
    if kw_rows:
        p = os.path.join(outdir, f"{slug} - nye keywords.csv")
        _write_csv(p, kw_fields, kw_rows)
        written.append(p)

    if not written:
        raise SystemExit("Nothing to write: no negatives and no new keywords in the decisions. "
                         "The conversation must agree on at least one action before writing.")

    result = {"files": written, "negatives": len(neg_rows), "new_keywords": len(kw_rows)}

    # >1 file -> bundle into a zip; exactly 1 -> hand back the bare CSV.
    if len(written) > 1:
        zpath = os.path.join(outdir, f"{slug}.zip")
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for p in written:
                z.write(p, arcname=os.path.basename(p))
        result["bundle"] = zpath
        result["delivered"] = zpath
    else:
        result["delivered"] = written[0]
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Write agreed search-term decisions to Editor CSV(s).")
    ap.add_argument("--in", dest="inp", required=True, help="decisions JSON file")
    ap.add_argument("--outdir", default=os.path.expanduser("~/Downloads"), help="output directory")
    ap.add_argument("--slug", default=None, help="filename stem (default from client + today)")
    args = ap.parse_args()
    data = json.loads(Path(args.inp).read_text())
    slug = args.slug or f"Soegeterm - {_s(data.get('client')) or 'konto'}"
    out = run(data, args.outdir, slug)
    print(json.dumps(out, ensure_ascii=False, indent=2))
