#!/usr/bin/env python3
"""Fill the RSA layout with generated ad text and save a new file.

The skill calls this after it has generated and length-checked the ad text. The
sheet layout (column order, =LEN() formulas, red over-length conditional
formatting) comes from sheet_layout.py so it is identical to the committed
template. fill-sheet builds the layout fresh for exactly as many data rows as
there are RSAs, writes only the text cells (never the LEN cells), and saves a
fresh .xlsx. The formulas + formatting are wired per row.

Two ads.json shapes are accepted:

  Single RSA (v2 default, backward compatible):
    {
      "campaign": "IC | GSN | Generic |",   # optional
      "ad_group": "",                          # optional
      "headlines": ["...", ...],               # up to 15, each <= 30 chars
      "descriptions": ["...", ...],            # up to 4, each <= 90 chars
      "paths": ["...", "..."],                 # up to 2, each <= 15 chars
      "final_url": "https://...",
      "final_mobile_url": "",                  # optional
      "vinkel": "",                            # optional, Inbound-internal (ignored by Editor)
      "hypotese": ""                           # optional, Inbound-internal (ignored by Editor)
    }

  "vinkel" / "hypotese" are documentation only: the overall creative angle and
  the hypothesis behind this RSA. They land in the last two sheet columns, which
  Google Ads Editor ignores on import. Per RSA row.

  Multiple RSAs in one ad group (one Editor row per ad):
    {
      "campaign": "IC | GSN | Generic | Brandsikring",
      "ad_group": "Brandsikring",
      "ads": [
        { "headlines": [...], "descriptions": [...], "paths": [...],
          "final_url": "https://...", "final_mobile_url": "" },
        { ... },   # RSA 2: leads with trust, full 9-angle mix
        { ... }    # RSA 3: leads with offer/CTA, full 9-angle mix
      ]
    }

  In the multi shape, campaign / ad_group / final_url / final_mobile_url may be
  set once at the top level and inherited by every ad, or overridden per ad.
  Repeating campaign + ad_group across rows is exactly how Editor imports
  several RSAs into the same ad group.

Exits non-zero and prints the offending fields (labelled by RSA) if any string
exceeds its hard limit or fails a quality guardrail, so the skill never writes a
bad sheet. The --copy flag is kept as an alias for --ads (v1 compatibility).
"""
import argparse
import json
import sys
from pathlib import Path

from sheet_layout import autosize_columns, build_sheet, text_cell

LIMITS = {"headline": 30, "description": 90, "path": 15}

# --- Quality guardrails -----------------------------------------------------
# These are NOT Google limits. They encode the tested craft rules from
# references/headline-craft.md that the model is supposed to follow but can
# silently skip. They block the build by default; pass --allow-quality-warnings
# to override for a genuine edge case (and say why in the run).
MIN_SHORT_HEADLINES = 4        # rule: 4-5 headlines under 20 chars
SHORT_HEADLINE_MAX = 20        # "short" = strictly under 20 chars
DUP_PREFIX_LEN = 12            # near-duplicate detector: shared leading chars


def _ads_list(copy: dict) -> list:
    """Normalise either ads.json shape to a list of per-ad dicts.

    Single shape -> one ad. Multi shape ("ads": [...]) -> each ad, inheriting
    campaign / ad_group / final_url / final_mobile_url from the top level unless
    the ad overrides them.
    """
    if "ads" in copy:
        if not isinstance(copy["ads"], list) or not copy["ads"]:
            raise ValueError('"ads" must be a non-empty list')
        inherited = {k: copy[k] for k in
                     ("campaign", "ad_group", "final_url", "final_mobile_url")
                     if k in copy}
        return [{**inherited, **ad} for ad in copy["ads"]]
    return [copy]


def validate(ad: dict) -> list:
    """HARD limits. Google rejects over-length fields, so these always block
    and are never overridable."""
    errs = []
    for i, h in enumerate(ad.get("headlines", []), 1):
        if len(h) > LIMITS["headline"]:
            errs.append(f"Headline {i} ({len(h)} > 30): {h!r}")
    for i, d in enumerate(ad.get("descriptions", []), 1):
        if len(d) > LIMITS["description"]:
            errs.append(f"Description {i} ({len(d)} > 90): {d!r}")
    for i, p in enumerate(ad.get("paths", []), 1):
        if len(p) > LIMITS["path"]:
            errs.append(f"Path {i} ({len(p)} > 15): {p!r}")
    return errs


def quality_warnings(ad: dict) -> list:
    warns = []
    headlines = ad.get("headlines", [])

    # 1. Length variation — the universal, mechanically-checkable rule.
    #    The DBI set failed exactly here: 0 of 15 headlines were under 20 chars.
    if len(headlines) >= 8:  # only meaningful on a near-full set
        short = [h for h in headlines if len(h) < SHORT_HEADLINE_MAX]
        if len(short) < MIN_SHORT_HEADLINES:
            warns.append(
                f"Laengde-variation: kun {len(short)} af {len(headlines)} headlines "
                f"er under {SHORT_HEADLINE_MAX} tegn (kraever mindst {MIN_SHORT_HEADLINES}). "
                f"Optmyzr: korte headlines rammer ca. halv CPA. Tilfoej korte varianter."
            )

    # 2. Near-duplicate headlines — forbud list bans "naesten-identiske
    #    formuleringer". The DBI set had 4 near-identical accreditation lines.
    seen = {}
    for i, h in enumerate(headlines, 1):
        key = h.strip().lower()[:DUP_PREFIX_LEN]
        seen.setdefault(key, []).append(i)
    dup_groups = [idxs for idxs in seen.values() if len(idxs) >= 3]
    for idxs in dup_groups:
        nums = ", ".join(f"#{n}" for n in idxs)
        warns.append(
            f"Naesten-ens headlines ({nums}) deler de foerste {DUP_PREFIX_LEN} tegn. "
            f"Svaekker Ad Strength og daekker ikke nye soege-intentioner. Dedup til de 2-3 staerkeste."
        )

    return warns


def _write_ad(ws, ad: dict, row: int) -> None:
    """Write one RSA's text into the given data row. Only text cells are
    touched; the LEN formulas wired by build_sheet stay intact."""
    if ad.get("campaign"):
        ws[text_cell("Campaign", row)] = ad["campaign"]
    if ad.get("ad_group"):
        ws[text_cell("Ad Group", row)] = ad["ad_group"]

    for i, value in enumerate(ad.get("headlines", []), 1):
        ws[text_cell(f"Headline {i}", row)] = value
    for i, value in enumerate(ad.get("descriptions", []), 1):
        ws[text_cell(f"Description {i}", row)] = value
    for i, value in enumerate(ad.get("paths", []), 1):
        ws[text_cell(f"Path {i}", row)] = value
    if ad.get("final_url"):
        ws[text_cell("Final URL", row)] = ad["final_url"]
    if ad.get("final_mobile_url"):
        ws[text_cell("Final mobile URL", row)] = ad["final_mobile_url"]
    # Inbound-internal documentation columns (ignored by Editor on import).
    if ad.get("vinkel"):
        ws[text_cell("Vinkel", row)] = ad["vinkel"]
    if ad.get("hypotese"):
        ws[text_cell("Hypotese", row)] = ad["hypotese"]


def fill(ads: list, out: Path) -> None:
    wb, ws = build_sheet(n_rows=len(ads))
    for idx, ad in enumerate(ads):
        _write_ad(ws, ad, row=2 + idx)  # data rows start at 2
    autosize_columns(ws)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    # --ads is the canonical flag; --copy is the v1 alias.
    ap.add_argument("--ads", "--copy", dest="ads", required=True,
                    help="path to ads.json (the generated ad-text spec)")
    ap.add_argument("--out", required=True, help="output .xlsx path")
    ap.add_argument("--allow-quality-warnings", action="store_true",
                    help="proceed despite quality guardrail warnings (length variation, "
                         "near-duplicates). Use only for a genuine edge case and say why.")
    args = ap.parse_args()

    copy = json.loads(Path(args.ads).read_text())
    try:
        ads = _ads_list(copy)
    except ValueError as e:
        print(f"REFUSING TO WRITE - bad ads.json: {e}", file=sys.stderr)
        return 1

    multi = len(ads) > 1
    label = (lambda n: f"RSA {n}, ") if multi else (lambda n: "")

    # HARD limits — never overridable. Checked per RSA.
    hard_errs = []
    for n, ad in enumerate(ads, 1):
        hard_errs += [f"{label(n)}{e}" for e in validate(ad)]
    if hard_errs:
        print("REFUSING TO WRITE - over-length fields:", file=sys.stderr)
        for e in hard_errs:
            print("  " + e, file=sys.stderr)
        return 1

    # Quality guardrails — block by default, overridable with the flag. Per RSA.
    warns = []
    for n, ad in enumerate(ads, 1):
        warns += [f"{label(n)}{w}" for w in quality_warnings(ad)]
    if warns:
        if args.allow_quality_warnings:
            print("QUALITY WARNINGS (overridden via --allow-quality-warnings):", file=sys.stderr)
            for w in warns:
                print("  " + w, file=sys.stderr)
        else:
            print("REFUSING TO WRITE - quality guardrails failed:", file=sys.stderr)
            for w in warns:
                print("  " + w, file=sys.stderr)
            print("Ret teksten, eller koer igen med --allow-quality-warnings "
                  "hvis det er en bevidst undtagelse.", file=sys.stderr)
            return 2

    out = Path(args.out)
    fill(ads, out)
    n = len(ads)
    print(f"Wrote {out} ({n} RSA{'er' if n != 1 else ''}, "
          f"data row{'s' if n != 1 else ''} 2-{n + 1})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
