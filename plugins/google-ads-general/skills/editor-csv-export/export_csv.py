#!/usr/bin/env python3
"""Convert a confirmed Google Ads review workbook into Google Ads Editor import CSVs.

The SHARED workbook->CSV converter for BOTH workflows. Editor imports CSV only, never .xlsx
(support.google.com/google-ads/editor/answer/30564), so each workflow ships a human-editable
Excel for review and THIS converter drops the confirmed Excel to the flat per-entity CSVs
Editor imports. It reads two workbook dialects on one contract (it just recognizes both):
  - SETUP    (google-ads-setup):     campaign-build assembler workbook — a full new campaign
             (Campaign settings, Ad groups, Keywords, Negatives, RSAs, Assets).
  - OPTIMIZE (optimization-loop):    review_workbook — a subset (Negative keywords, promoted
             winner Keywords, RSA challengers); no campaign settings / ad groups / assets.
Both workbooks speak the SAME per-entity Editor vocabulary (harmonized 2026-06-09), so the same
builders run on either — one converter, no fork. It lives in google-ads-general precisely because
it serves both setup and optimization (Cowork can't share the .py cross-plugin, so a per-plugin
copy would guarantee drift).

Pure transform: reads ONE local .xlsx, writes ONE local .zip bundling up to 6 Editor CSVs. No
Google Ads API call, no push, no external read/write. The human unzips and imports the CSVs in
Editor (Account > Import > From file) after review. The CSVs are named with a numeric prefix
(1-campaigns.csv ... 6-negatives.csv) so the extracted bundle sorts into Editor's import order.

Read the workbook BY HEADER NAME, never by column index — Editor headers are case- and
space-insensitive (answer 57747: `daily budget` == `DailyBudget`), and reading by name makes the
converter immune to any column reordering the styling pass introduced. Each tab's header row is
ALWAYS row 1 (the assembler styles cells, never inserts a banner row above the data).

Target CSV schema = §5 of the assembler-contract.md. It is NOT re-derived from Google's public
docs because those deliberately punt the full per-column list to "the next article" — §5 traces
to Ian's real skeleton, which is the best current authority. Genuinely-unverified column names
(structured-snippet header, the negative Type literals, the <Account-level> literal) are FLAGGED,
not asserted as verified: the honest acceptance test is one real Editor import, not doc-reading.

Two hard guards RE-RUN here (assembler-contract §6) because a human can edit the confirmed Excel
between sign-off and conversion:
  1. No positive keyword may be blank/Broad — only Exact or Phrase. Refuse to write keywords.csv.
  2. Recompute LEN against 30/90/15 — refuse to write ads.csv if any RSA field is over-length.

Negatives-non-flatten (assembler-contract §2, highest-risk rule): negatives.csv reads tab-04
client-specific rows ONLY. It SKIPS the "[SHARED LIST APPLIED BY REFERENCE ...]" line (that is a
reference marker, not an Editor row) and NEVER reads tab 05 (monitor-first candidates must not be
committed). The 277-term shared list is attached by reference in Editor manually, never as CSV
rows.
"""
import argparse
import csv
import json
import os
import re
import sys
import tempfile
import zipfile

# openpyxl bootstrap: reuse the RSA layout's installer if reachable, else pip-install inline.
try:
    import openpyxl  # noqa: F401
except ImportError:  # pragma: no cover - environment bootstrap
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "openpyxl"])
import openpyxl  # noqa: E402

# Hard Editor limits (RSA). Kept in sync with responsive-search-ads/sheet_layout.py FIELDS; the
# converter lives in a different plugin so it cannot import that module at runtime (cross-plugin
# path is not resolvable in Cowork) — these three integers are the only duplicated constants, and
# they are Google-fixed, not an Inbound choice.
HEADLINE_LIMIT = 30
DESCRIPTION_LIMIT = 90
PATH_LIMIT = 15

SHARED_LIST_MARKER = "[SHARED LIST APPLIED BY REFERENCE"  # tab-04 reference line prefix to skip
ACCOUNT_LEVEL_LITERAL = "<Account-level>"  # Editor's account-level asset marker (answer 56368)


# --------------------------------------------------------------------------- workbook reading
def _norm(h):
    """Editor's header equivalence: case- and space-insensitive (answer 57747)."""
    return "".join(str(h or "").split()).lower()


def read_tab(wb, *name_options):
    """Return (headers, rows-as-dicts) for the first sheet whose title matches any option.
    Match on the trailing name ('01 Campaign settings' -> matches 'campaign settings'),
    tolerant of the numeric prefix. Header row is row 1."""
    wanted = {_norm(o) for o in name_options}
    target = None
    for ws in wb.worksheets:
        title = ws.title
        # Strip any leading run of digits + whitespace ('01 Campaign settings', '1 Foo',
        # '10  Bar') so matching is robust to the assembler's NN-prefix naming convention.
        stripped = re.sub(r"^\d+\s*", "", title)
        if _norm(title) in wanted or _norm(stripped) in wanted:
            target = ws
            break
    if target is None:
        return None, []
    rows_iter = target.iter_rows(values_only=True)
    try:
        header = list(next(rows_iter))
    except StopIteration:
        return [], []
    headers = [str(h) if h is not None else "" for h in header]
    out = []
    for row in rows_iter:
        if row is None or all(c is None or str(c).strip() == "" for c in row):
            continue
        out.append({headers[i]: row[i] for i in range(len(headers)) if i < len(row)})
    return headers, out


def get(row, *header_options, default=""):
    """Fetch a cell from a row dict by any header spelling (normalized match)."""
    norm_map = {_norm(k): k for k in row}
    for opt in header_options:
        k = norm_map.get(_norm(opt))
        if k is not None:
            v = row[k]
            return "" if v is None else v
    return default


def _s(v):
    return "" if v is None else str(v).strip()


# --------------------------------------------------------------------------- guards (re-run)
def guard_keywords(kw_rows):
    bad = []
    for r in kw_rows:
        mt = _s(get(r, "Match type")).lower()
        if mt not in ("exact", "phrase"):
            bad.append(f"{_s(get(r,'Ad group'))} / '{_s(get(r,'Keyword'))}' -> '{mt or '(blank)'}'")
    if bad:
        raise SystemExit(
            "STOP: positive keyword rows with blank/Broad match type in the confirmed workbook "
            "(a human edit between sign-off and conversion would create Broad keywords on import, "
            "violating the no-Broad lock). Fix tab 03 and re-run:\n  " + "\n  ".join(bad)
        )


def guard_rsa_lengths(rsa_rows):
    over = []
    for r in rsa_rows:
        for i in range(1, 16):
            t = _s(get(r, f"Headline {i}"))
            if len(t) > HEADLINE_LIMIT:
                over.append(f"{_s(get(r,'Ad group'))} Headline {i} ({len(t)}>{HEADLINE_LIMIT}): {t}")
        for i in range(1, 5):
            t = _s(get(r, f"Description {i}"))
            if len(t) > DESCRIPTION_LIMIT:
                over.append(f"{_s(get(r,'Ad group'))} Description {i} ({len(t)}>{DESCRIPTION_LIMIT}): {t}")
        for i in range(1, 3):
            t = _s(get(r, f"Path {i}"))
            if len(t) > PATH_LIMIT:
                over.append(f"{_s(get(r,'Ad group'))} Path {i} ({len(t)}>{PATH_LIMIT}): {t}")
    if over:
        raise SystemExit(
            "STOP: RSA field(s) over the hard Editor limit in the confirmed workbook (a human "
            "edit after sign-off pushed a field over-length; it would auto-disapprove on import). "
            "Fix tab 06 and re-run:\n  " + "\n  ".join(over)
        )


# --------------------------------------------------------------------------- CSV writers
def _write_csv(path, fieldnames, rows):
    # UTF-8 with BOM so Editor + Excel both read Danish æ/ø/å correctly on Windows.
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _display_negative(text, match_type):
    """Editor expects the negative keyword in bracket/quote form for its match type."""
    mt = (match_type or "").strip().lower()
    if mt == "exact":
        return f"[{text}]"
    if mt == "phrase":
        return f'"{text}"'
    return text  # broad negatives are bare


def build_campaigns(settings_rows):
    out = []
    for r in settings_rows:
        nets = _s(get(r, "Networks"))
        # Remap the workbook's human network string to Editor's value.
        editor_nets = "Google search"
        if "search partners" in nets.lower():
            editor_nets = "Google search;Search partners"
        if "display" in nets.lower():
            editor_nets += ";Display Network"
        out.append({
            "Campaign": _s(get(r, "Campaign")),
            "Campaign type": _s(get(r, "Campaign type")) or "Search",
            "Budget": _s(get(r, "Daily budget (DKK)", "Daily budget")),
            "Bid strategy type": _s(get(r, "Bidding strategy", "Bid strategy type")),
            "Networks": editor_nets,
            "Language targeting": _s(get(r, "Languages", "Language targeting")),
            "Campaign status": "Paused",  # paused-until-QA, always
        })
    return out


def build_adgroups(ag_rows):
    out = []
    for r in ag_rows:
        out.append({
            "Campaign": _s(get(r, "Campaign")),
            "Ad group": _s(get(r, "Ad group")),
            "Max CPC": _s(get(r, "Max CPC")),  # blank = let strategy decide
            "Ad group status": "Enabled",
        })
    return out


def build_keywords(kw_rows):
    out = []
    for r in kw_rows:
        out.append({
            "Campaign": _s(get(r, "Campaign")),
            "Ad group": _s(get(r, "Ad group")),
            "Keyword": _s(get(r, "Keyword")),
            "Match type": _s(get(r, "Match type")).capitalize(),  # Exact / Phrase
            "Status": "Paused",
        })
    return out


def build_negatives(neg_rows):
    """Client-specific rows ONLY. Skip the shared-list reference line. Never reads tab 05."""
    out = []
    for r in neg_rows:
        text = _s(get(r, "Negative keyword"))
        if not text or text.startswith(SHARED_LIST_MARKER) or _s(get(r, "Level")).startswith("(shared"):
            continue  # the 277 are attached by reference in Editor, never a CSV row
        level = _s(get(r, "Level")).lower()
        out.append({
            "Campaign": _s(get(r, "Campaign")),
            "Ad group": "" if level == "campaign" else _s(get(r, "Ad group")),
            "Keyword": _display_negative(text, _s(get(r, "Match type")) or "broad"),
            "Type": "Campaign negative" if level == "campaign" else "Negative",
        })
    return out


def build_ads(rsa_rows):
    fields = (["Campaign", "Ad group", "Ad type", "Final URL", "Path 1", "Path 2"]
              + [f"Headline {i}" for i in range(1, 16)]
              + [f"Description {i}" for i in range(1, 5)])
    # #Original passthrough (the optimization-loop's distinguishing need; answer 57747).
    # The campaign-build assembler is all net-new and carries no #Original. The optimization
    # loop EDITS live RSAs, so its workbook may carry `<Column>#Original` columns holding the
    # current live value — Editor uses them to match the edit to the existing ad and edit it
    # IN PLACE instead of creating a duplicate. Preserve any such column verbatim; dropping it
    # would turn an edit into a duplicate. Discover them from the actual rows (present only
    # when an edit row exists) and append after the fixed fields.
    orig_fields = []
    for r in rsa_rows:
        for k in r:
            ks = str(k)
            if ks.endswith("#Original") and ks not in orig_fields:
                orig_fields.append(ks)
    fields = fields + orig_fields
    out = []
    for r in rsa_rows:
        row = {
            "Campaign": _s(get(r, "Campaign")),
            "Ad group": _s(get(r, "Ad group")),
            "Ad type": "Responsive search ad",
            "Final URL": _s(get(r, "Final URL")),
            "Path 1": _s(get(r, "Path 1")),
            "Path 2": _s(get(r, "Path 2")),
        }
        for i in range(1, 16):
            row[f"Headline {i}"] = _s(get(r, f"Headline {i}"))
        for i in range(1, 5):
            row[f"Description {i}"] = _s(get(r, f"Description {i}"))
        # Preserve #Original cells verbatim (exact-key match, not the normalized get()).
        for of in orig_fields:
            row[of] = _s(r.get(of, ""))
        out.append(row)
    return fields, out


def build_assets(asset_rows):
    out = []
    for r in asset_rows:
        level = _s(get(r, "Level")).lower()
        campaign = ACCOUNT_LEVEL_LITERAL if level == "account" else _s(get(r, "Campaign"))
        atype = _s(get(r, "Asset type")).lower()
        base = {
            "Campaign": campaign,
            "Ad group": "",  # campaign/account-level only in v1
            "Sitelink text": "",
            "Final URL": "",
            "Description line 1": "",
            "Description line 2": "",
            "Callout text": "",
            # UNVERIFIED Editor header name for the snippet header — see SKILL "UNVERIFIED".
            "Header": "",
            "Snippet values": "",
        }
        if atype.startswith("sitelink"):
            base.update({
                "Sitelink text": _s(get(r, "Sitelink text")),
                "Final URL": _s(get(r, "Final URL")),
                "Description line 1": _s(get(r, "Description line 1")),
                "Description line 2": _s(get(r, "Description line 2")),
            })
        elif atype.startswith("callout"):
            base["Callout text"] = _s(get(r, "Callout text"))
        elif "snippet" in atype:
            base["Header"] = _s(get(r, "Snippet header"))
            base["Snippet values"] = _s(get(r, "Snippet values"))
        out.append(base)
    return out


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(
        description="Confirmed review workbook -> Editor CSVs (setup assembler OR optimization-loop).")
    ap.add_argument("--workbook", required=True,
                    help="the confirmed .xlsx (campaign-build assembler or optimization-loop review_workbook)")
    ap.add_argument("--outdir", required=True, help="directory to write the CSVs into")
    args = ap.parse_args()

    if not os.path.exists(args.workbook):
        raise SystemExit(f"STOP: workbook not found: {args.workbook}")
    os.makedirs(args.outdir, exist_ok=True)

    wb = openpyxl.load_workbook(args.workbook, read_only=True, data_only=True)

    # Two known workbook dialects feed this converter (it stays a pure transform, it just
    # recognizes both): (a) the campaign-build ASSEMBLER workbook (tabs "01 Campaign settings",
    # "02 Ad groups", "03 Keywords", "06 RSAs", ...) — a full net-new campaign; (b) the
    # optimization-LOOP review workbook (tabs "Negative keywords", "Nye keywords (vindere)",
    # "RSA challengers") — a subset: only negatives, promoted-winner keywords, and RSA
    # challengers/edits, never campaign settings or ad groups. read_tab matches any alias.
    _, settings = read_tab(wb, "Campaign settings", "Campaign setting")
    _, agroups = read_tab(wb, "Ad groups", "Ad group")
    _, keywords = read_tab(wb, "Keywords", "Keyword", "Nye keywords (vindere)")
    _, negatives = read_tab(wb, "Negative keywords", "Negatives")
    _, rsas = read_tab(wb, "RSAs", "RSA", "RSA challengers")
    _, assets = read_tab(wb, "Assets", "Asset")

    # Require at least one recognized entity tab (works for both the full assembler workbook
    # and the optimization-loop subset). Campaign settings is no longer mandatory.
    if not any([settings, agroups, keywords, negatives, rsas, assets]):
        raise SystemExit(
            "STOP: workbook has no recognized entity tab (Campaign settings / Ad groups / "
            "Keywords / Negative keywords / RSAs / Assets). Is this an assembler or "
            "optimization-loop workbook?"
        )

    # The deliverable is ONE zip named after the workbook. Compute its path now and clear any
    # stale copy from a previous run into the same outdir, BEFORE the guards. That way a guard
    # failure (below) leaves no zip for this workbook in outdir — the "no importable bundle from a
    # flawed workbook" guarantee holds even when re-running into a dirty outdir that still holds an
    # earlier (now out-of-date) good run's zip.
    base = os.path.splitext(os.path.basename(args.workbook))[0]
    zip_path = os.path.join(args.outdir, f"{base} - editor-csv.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)

    # Re-run the two hard guards at this boundary (a human may have edited the Excel).
    # These run BEFORE any write — if either fires, no .zip is produced and we exit non-zero,
    # so a flawed workbook can never sail into an importable bundle.
    guard_keywords(keywords)
    guard_rsa_lengths(rsas)

    # Build the CSVs into a throwaway temp dir, then bundle them into ONE .zip in --outdir.
    # Writing to a temp dir first lets _write_csv stay untouched (BOM-correct utf-8-sig bytes),
    # and the zip copies those exact bytes verbatim — no re-encoding, so Danish æ/ø/å survive.
    # The numeric arcname prefix (1-campaigns ... 6-negatives) makes the extracted bundle sort
    # into Editor's documented import order, so the human imports top-to-bottom without guessing.
    entities = [
        ("1-campaigns.csv", build_campaigns(settings),
         ["Campaign", "Campaign type", "Budget", "Bid strategy type",
          "Networks", "Language targeting", "Campaign status"]),
        ("2-adgroups.csv", build_adgroups(agroups),
         ["Campaign", "Ad group", "Max CPC", "Ad group status"]),
        ("3-keywords.csv", build_keywords(keywords),
         ["Campaign", "Ad group", "Keyword", "Match type", "Status"]),
        ("5-assets.csv", build_assets(assets),
         ["Campaign", "Ad group", "Sitelink text", "Final URL",
          "Description line 1", "Description line 2", "Callout text",
          "Header", "Snippet values"]),
        ("6-negatives.csv", build_negatives(negatives),
         ["Campaign", "Ad group", "Keyword", "Type"]),
    ]
    # ads.csv (slot 4) carries dynamic #Original passthrough fields, so its header is built per-run.
    ads_fields, ads_rows = build_ads(rsas)

    written = []  # (arcname, row count) — what's inside the zip, retained in the JSON summary

    with tempfile.TemporaryDirectory() as tmp:
        staged = []  # (arcname, temp path)
        for arcname, rows, fieldnames in entities:
            if rows:
                tmp_path = os.path.join(tmp, arcname)
                _write_csv(tmp_path, fieldnames, rows)
                staged.append((arcname, tmp_path))
                written.append((arcname, len(rows)))
        if ads_rows:
            tmp_path = os.path.join(tmp, "4-ads.csv")
            _write_csv(tmp_path, ads_fields, ads_rows)
            staged.append(("4-ads.csv", tmp_path))
            written.append(("4-ads.csv", len(ads_rows)))

        # Stable, import-order zip member order regardless of dialect (loop workbooks skip slots).
        staged.sort(key=lambda s: s[0])
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for arcname, tmp_path in staged:
                zf.write(tmp_path, arcname=arcname)

    print(json.dumps({
        "workbook": args.workbook,
        "outdir": args.outdir,
        "zip": zip_path,
        "files": [{"name": name, "rows": n} for name, n in sorted(written)],
        "note": "ONE .zip bundling the Editor CSVs. Unzip, then import in Editor (Account > Import "
                "> From file) in order: campaigns > adgroups > keywords > ads > assets > negatives "
                "(the numeric filename prefix already sorts them this way), Check Changes after "
                "each. The 277-term shared negative list is NOT in any CSV — attach it by reference "
                "in Editor. Snippet header CSV column ('Header') is UNVERIFIED — confirm via one "
                "Editor round-trip. Nothing was pushed to any account.",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
