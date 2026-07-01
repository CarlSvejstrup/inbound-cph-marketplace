# Editor-CSV-export contract

Single source of truth for how `editor-csv-export` converts a **confirmed** Google Ads review
workbook into Google Ads Editor import CSVs. It reads **two dialects on one contract** (§Two
dialects): the `campaign-build` `assembler` workbook (full new campaign) and the
optimization-loop review workbook (a subset). If SKILL.md and this file disagree, this file wins.

Pure transform: ONE local `.xlsx` in → ONE local `.zip` out, bundling up to 6 `.csv` (numbered
`1-campaigns.csv` … `6-negatives.csv` so the extracted bundle sorts into Editor's import order).
No Google Ads API call, no push, no external read/write.

## Authority of the target schema (read this first)

The CSV target schema below is **§5 of the assembler-contract** (`campaign-build/references/
assembler-contract.md`), which traces to Ian's real campaign skeleton. It is
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

## Packaging: ONE .zip, numbered members

The converter writes a single `<workbook-name> - editor-csv.zip` into `--outdir` and leaves no
loose CSVs beside it. Inside, each CSV is named with a numeric prefix matching Editor's import
order: `1-campaigns.csv`, `2-adgroups.csv`, `3-keywords.csv`, `4-ads.csv`, `5-assets.csv`,
`6-negatives.csv`. So when the human extracts the bundle, the files sort top-to-bottom into the
exact order Editor needs them imported — the bundle is self-documenting.

- The CSVs are built into a temp dir with the unchanged `utf-8-sig` writer, then `zipfile` copies
  those exact bytes into the archive — the BOM (Danish æ/ø/å, load-bearing) is preserved verbatim,
  no re-encoding.
- A loop dialect with only 3 entity tabs yields a 3-member zip (e.g. `3`, `4`, `6`); gaps in the
  numbering are harmless and the order still holds.
- Any stale zip for this workbook in `--outdir` is removed BEFORE the guards run; the guards
  (§Two hard guards) then run before any write, so if either fires NO zip for this workbook is left
  behind and the process exits non-zero. A flawed workbook never reaches an importable bundle —
  even on a re-run into a dirty outdir that still holds an earlier good run's zip.
- The JSON summary on stdout points at the `.zip` and retains the per-CSV row counts.

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

## Two dialects (the converter reads BOTH on this one contract)

The converter is a pure transform that recognizes two workbook shapes. `read_tab` matches tab
names by alias (tolerant of the `NN ` numeric prefix), so both hit the same writers. At least ONE
recognized entity tab is required — campaign settings is NOT mandatory (the loop workbook has none).

| Dialect | Source | Tabs | What converts |
|---|---|---|---|
| **assembler** | `campaign-build` assembler | `01 Campaign settings`, `02 Ad groups`, `03 Keywords`, `04 Negative keywords`, `06 RSAs`, `07 Assets` | all 6 CSVs (full new campaign, net-new) |
| **optimization-loop** | `workflows/optimization-loop` review workbook | `Negative keywords`, `Nye keywords (vindere)`, `RSA challengers` | negatives + keywords + ads only |

Tab-name aliases the converter accepts for the loop dialect: `Nye keywords (vindere)` → keywords,
`RSA challengers` → ads, `Negative keywords` → negatives (matches both dialects already).

**The loop dialect shares the §"6 CSVs" mapping unchanged** — its negatives tab was deliberately
given the same `Campaign / Level / Ad group / Negative keyword / Match type` vocabulary as the
assembler's tab 04, so the Type-derivation works identically. Loop-specific facts the converter
must honor:

- **`#Original` passthrough.** Any `<Column>#Original` column in the workbook is preserved
  VERBATIM in the matching CSV (discovered from the actual rows, appended after the fixed fields).
  Editor uses it to edit an existing entity in place instead of creating a duplicate (answer
  57747). Correct for genuinely-editable entities (a keyword's bid/URL). **Harmless when absent.**
- **RSAs are NET-NEW only (loop builder rule, not a converter rule).** The loop never emits an RSA
  edit row — editing a live RSA resets its learning and Editor CSV can't reliably match an RSA. So
  in practice the loop's ads.csv carries zero `#Original`. The converter's passthrough stays
  general (it would carry `#Original` if a future editable-entity tab used it) but never fires for
  the loop's RSAs.
- **Account-level negatives are pre-fanned by the loop builder.** Editor CSV has no account level;
  the loop builder fans an account-level finding out to one `Level=campaign` row per active
  campaign BEFORE the workbook is written. The converter sees only campaign/ad-group rows and
  needs no special logic — what-you-see-in-the-workbook-is-what-imports.

## Smoke-test invariants (run before declaring done)

**Assembler dialect** — run the assembler on a golden input set, then this converter on the output:
1. ONE `.zip` written in `--outdir` (no loose CSVs); its 6 members named `1-campaigns.csv` …
   `6-negatives.csv` and listed in that sorted order; every member carries the UTF-8 BOM; æ/ø/å survive.
2. negatives.csv contains ONLY client-specific rows — no `[SHARED LIST ...]` line, no monitor
   candidate, no enumeration of the 277.
3. campaigns.csv: status `Paused`, numeric budget present, networks remapped.
4. keywords.csv: only Exact/Phrase, status `Paused`.
5. assets.csv: account-level rows carry the literal `<Account-level>` in Campaign; snippet values
   semicolon-joined.
6. Feed an over-length headline → guard fires, NO zip for this workbook left in `--outdir`, non-zero exit.
7. Feed a Broad/blank positive keyword → guard fires, NO zip left, non-zero exit.
   (Bonus: run a good workbook into an outdir, then re-run the SAME workbook with a guard-failing
   edit → the earlier zip is gone, confirming the pre-guard cleanup.)

**Loop dialect** — run `review_workbook.py` on a synthetic findings set, then this converter:
8. The zip carries only the 3 loop CSVs (`3-keywords.csv`, `4-ads.csv`, `6-negatives.csv`) — no
   campaigns/adgroups/assets members.
9. An account-level negative fans out to one `Campaign negative` row per active campaign.
10. ads.csv carries NO `#Original` columns (loop RSAs are all net-new), even if the findings
    carried legacy `is_edit`/`original` (the builder ignores them).
11. The same two guards (§Two hard guards) fire on the loop workbook's keyword/RSA tabs too.
