# Editor-CSV-export contract

Single source of truth for how `editor-csv-export` converts a **confirmed** campaign-build review
workbook (the `.xlsx` from the `google-ads-setup` `assembler` skill) into Google Ads Editor import
CSVs. If SKILL.md and this file disagree, this file wins.

Pure transform: ONE local `.xlsx` in → up to 6 local `.csv` out. No Google Ads API call, no push,
no external read/write.

## Authority of the target schema (read this first)

The CSV target schema below is **§5 of the assembler-contract** (`google-ads-setup/skills/
assembler/references/assembler-contract.md`), which traces to Ian's real campaign skeleton. It is
NOT re-derived from Google's public Editor docs: those deliberately punt the full per-column list
to "the next article" and the small models that summarize them conflate ad types (one summary
returned responsive-DISPLAY-ad columns `Short headline`/`Long headline` for what is an RSA — wrong;
RSA is `Headline 1-15` / `Description 1-4`). So:

- Build to §5 + emit the standard English header strings.
- The honest acceptance test is **one real Editor import**, not doc-reading. Never write
  "verified against Google docs" in the skill — it isn't.
- Genuinely-unverified column names are FLAGGED (see §UNVERIFIED), not asserted.

What the public docs DID confirm (and we rely on):
- Editor imports **CSV only, not .xlsx** (answer 30564) — the reason this skill exists.
- Headers are English, **case- and space-insensitive** (`daily budget` == `DailyBudget`) (57747).
  → read the workbook BY HEADER NAME, never by index.
- Account-level assets use the literal **`<Account-level>`** in the Campaign column (answer 56368).
- Multi-value cells separate values with **semicolons** (`en;de`) (answer 56368).
- Unicode encoding → we write **UTF-8 with BOM** (Danish æ/ø/å load-bearing).

## The 6 CSVs (column ← workbook cell). **Bold** = value transform, not a straight copy.

- **campaigns.csv** (tab 01): `Campaign`←Campaign, `Campaign type`←Campaign type,
  `Budget`←**Daily budget (DKK)** (the numeric cell, NOT the prose rationale),
  `Bid strategy type`←Bidding strategy, `Networks`←**remap** the human string
  (`Search` → `Google search`; `+ Search Partners` → `;Search partners`; `+ Display` →
  `;Display Network`), `Language targeting`←Languages, `Campaign status`←**`Paused`** (always —
  paused-until-QA).
- **adgroups.csv** (tab 02): `Campaign`, `Ad group`, `Max CPC`←Max CPC (blank = let the strategy
  decide), `Ad group status`←`Enabled`.
- **keywords.csv** (tab 03): `Campaign`, `Ad group`, `Keyword`, `Match type`←**Exact/Phrase,
  capitalized; NEVER blank, NEVER Broad** (guard §6.1), `Status`←**`Paused`**.
- **negatives.csv** (tab 04, **client-specific rows ONLY**): `Campaign`,
  `Ad group`←Ad group (blank when Level=campaign), `Keyword`←**bracket/quote form built from the
  Negative keyword + Match type** (`[exact]` / `"phrase"` / bare broad),
  `Type`←**`Campaign negative` when Level=campaign / `Negative` when Level=ad_group**.
- **ads.csv** (tab 06): `Campaign`, `Ad group`, `Ad type`←`Responsive search ad`, `Final URL`,
  `Path 1`, `Path 2`, `Headline 1-15`, `Description 1-4`. Drop Ad label / Test hypothesis.
- **assets.csv** (tab 07): `Campaign`←**`<Account-level>` literal when Level=account, else the
  campaign name**, `Ad group` (blank — campaign/account-level only in v1), `Sitelink text`,
  `Final URL`, `Description line 1`, `Description line 2`, `Callout text`, `Header`←Snippet header
  (UNVERIFIED name), `Snippet values`. One row per asset; only its type's columns are filled.

Tabs that NEVER become a CSV: 00 README, 05 Monitor negatives, 08 Launch QA, 09 Validation.

## Negatives-non-flatten (highest-risk rule)

`negatives.csv` reads tab-04 client-specific rows ONLY:
- **SKIP** the `[SHARED LIST APPLIED BY REFERENCE ...]` line (a reference marker, not an Editor
  row) and any row whose Level is `(shared list)`. The 277-term shared list is attached by
  reference in Editor manually (shared set id `6688642473`), NEVER as CSV rows.
- **NEVER read tab 05** (monitor-first candidates) — committing them is the over-blocking harm
  Phase 2 avoids. The converter only ever reads tab 04 for negatives, so tab 05 cannot leak.

If the 277 appear in a CSV, the rule is broken — stop.

## Two hard guards (RE-RUN at this boundary — contract §6 mirror)

A human can edit the confirmed Excel between sign-off and conversion. The assembler guarding its
inputs does NOT protect the converter's inputs. So both re-run here:

1. **No blank/Broad positive keyword.** Every tab-03 keyword must be Exact or Phrase. Any
   blank/Broad → refuse to write keywords.csv, report the rows, exit non-zero (NO CSV written).
2. **Recompute RSA LEN** against 30 (headline) / 90 (description) / 15 (path). Any over-length →
   refuse to write ads.csv, report the fields, exit non-zero.

The limits 30/90/15 are the ONLY duplicated constants. The assembler imports them from
`responsive-search-ads/sheet_layout.py`; cross-plugin import does not resolve in Cowork, so the
converter hardcodes the three Google-fixed integers (not an Inbound choice).

## UNVERIFIED / carried-forward (flagged, not resolved)

- **Structured-snippet header CSV column name** — we emit `Header`; it may be `Subject` or
  another Editor spelling. Resolve via ONE Editor round-trip (export a real account that has a
  snippet, read the actual header) before relying on it. If snippet import fails, fix only that
  one header cell.
- **Networks remap exact strings** — `Google search` / `Search partners` / `Display Network` are
  the likely Editor values; confirm on the same round-trip.
- **No live Editor import done yet** — the smoke test below tests the TRANSFORM (workbook → CSV
  shape), not that Editor accepts every header. That verification is the human's one real import.

## Smoke-test invariants (run before declaring done)

Run the assembler on a golden input set, then this converter on the output, verify:
1. 6 CSVs written; UTF-8 BOM; æ/ø/å survive.
2. negatives.csv contains ONLY client-specific rows — no `[SHARED LIST ...]` line, no monitor
   candidate, no enumeration of the 277.
3. campaigns.csv: status `Paused`, numeric budget present, networks remapped.
4. keywords.csv: only Exact/Phrase, status `Paused`.
5. assets.csv: account-level rows carry the literal `<Account-level>` in Campaign; snippet values
   semicolon-joined.
6. Feed an over-length headline → guard fires, NO CSV written, non-zero exit.
7. Feed a Broad/blank positive keyword → guard fires, NO CSV written, non-zero exit.
