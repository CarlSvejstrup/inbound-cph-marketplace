# Assembler contract (Phase-4 barrier)

Single source of truth for how the `assembler` skill merges the four upstream output shapes
into Ian's 10-tab review workbook, runs QA/validation, and stops at the review artifact (NO API
push, NO CSV). All tab column shapes verified against Ian's skeleton
(`InboundCPH_AI-SEO_Google-Ads-kampagneskelet.xlsx`). If SKILL.md and this file disagree, this
file wins.

The assembler is a **pure transform**: 4 JSON shapes → ONE workbook. No external reads, no CSV,
no writes to any account.

**Excel-only (decision 2026-06-05).** The workbook is the client-confirmation artifact — often
the Excel sent to the client for sign-off. Editor CSVs are generated LATER, from the confirmed
Excel, by the separate `google-ads-general` converter skill. The assembler's job is therefore to
make the workbook a **lossless superset**: every field a CSV will need has a dedicated workbook
cell. §5 below is no longer something the assembler emits — it is the converter's target schema,
kept here so the workbook columns and the CSV columns stay traceable to each other.

---

## 1. The four input shapes (join key = `campaign`)

| Shape | From | Carries |
|---|---|---|
| `campaign-strategy.json` | Phase 1 campaign-strategy | campaign, type, goal, budget, bidding, geo, languages, networks, conversion action, tracking_prerequisite, match-type policy |
| `structuring.json` | Phase 2 structuring | ad_groups[] (name, temperature, landing_page_url, theme, keywords[{text,match_type}], angles[], keyword_seeds_for_rsa[]), negatives{inherited_shared_list, client_specific_additions, monitor_first_candidates}, keyword_volume_disclaimer, structure_rationale |
| rsa manifest (`rsa_artifacts`) | Phase 3 `05-rsa-copy` | per ad group: ad_group, ads_json path, n_rsas, final_url; each ads.json has headlines[15]/descriptions[4]/paths[2]/vinkel/hypotese per RSA |
| `assets.json` | Phase 3 assets | campaign, attachment_level, sitelinks[], callouts[], structured_snippets[], lead_form{csv_importable:false} |

**Reconcile FIRST.** All four share `campaign` — assert it matches across all four before
building; mismatch = stop and report (the human paste between phases can desync them). Ad
groups are joined by `name` across structuring + the rsa manifest.

---

## 2. The negatives object must NOT be flattened (highest-risk rule)

This is the Phase-2 "add to this, never re-dump" decision, enforced at assembly. structuring's
three negative tiers map to THREE DIFFERENT places — never collapse them:

| Tier | Goes to | NEVER goes to |
|---|---|---|
| `inherited_shared_list` (the 277) | tab 08 launch-gate line ("attach shared list 'Generelle negative søgeord' id 6688642473") + a reference line in tab 04 | enumerated anywhere. If the 277 appear as term rows, Phase 2 has regressed. The converter must also drop the tab-04 reference line (it is not an Editor row). |
| `client_specific_additions` | tab 04 rows (with `Level` + `Ad group` columns so the converter can derive Editor's Type) | — |
| `monitor_first_candidates` | tab 05 only | tab 04 (committing them is the over-blocking harm) — the converter reads tab 04 only, so tab 05 never reaches a CSV |

**Negative match types stay as-is** — broad is correct for negatives. Do NOT apply the
positive no-Broad lock to negatives. (Ian's own tab 04 happens to use Phrase per term; carry
whatever match_type the structuring object set.) The `Level` column (`campaign`/`ad_group`) +
`Ad group` column are what let the converter set Editor's `Type` (Campaign negative vs the
ad-group `Negative`) — they are load-bearing, not cosmetic.

---

## 3. Workbook is a lossless superset; the CSV boundary lives in the converter

The workbook intentionally carries EVERYTHING — both the Editor-schema fields and the
review-only metadata. It is the rich superset. The `google-ads-general` converter is where the
boundary is drawn: it reads the confirmed Excel and drops the workbook-only columns below,
keeping only verified Editor headers (§5).

| Object | Workbook-only metadata (converter DROPS) |
|---|---|
| assets | `grounded_in`, `url_source`, `header_column_unverified` |
| negatives | `why` / `Reason`, `Category` (but `Level` + `Ad group` are KEPT — they map to Editor's Type) |
| RSA | `vinkel`, `hypotese` (`Test hypothesis`), LEN columns |
| keywords | `Notes`, `Keyword display` |
| tab 09 | the whole tab (validation is review-only) |

The superset cells added so the converter is lossless (none of these existed before 2026-06-05):
**tab 02 `Max CPC`**, **tab 01 `Daily budget (DKK)`** (separate from the prose `Budget
rationale`), **tab 04 `Level` + `Ad group`**, **tab 07 `Level` + per-type columns**
(`Sitelink text` / `Callout text` / `Snippet header` / `Snippet values` no longer overloaded).

---

## 4. The 10-tab workbook (mirrors Ian's skeleton exactly)

| Tab | Content | Source |
|---|---|---|
| 00 README | Deliverable, Date, Account, Campaign, launch gate, workflow note | campaign-strategy + run meta |
| 01 Campaign settings | the tab-01 columns; budget is split into `Daily budget (DKK)` (numeric, for the converter) + `Budget rationale` (prose) | campaign-strategy.json |
| 02 Ad groups | Campaign, Ad group, Intent, Main kw, Supporting queries, Final URL, Path 1, Path 2, **Max CPC**, Primary angles | structuring ad_groups[] |
| 03 Keywords | Campaign, Ad group, Keyword, Match type, Keyword display, Final URL, Status, Notes | structuring keywords[] |
| 04 Negative keywords | Campaign, **Level**, **Ad group**, Negative keyword, Match type, Category, Reason | client_specific_additions + a shared-list reference line |
| 05 Monitor negatives | Candidate negative, Default action, Reason | monitor_first_candidates |
| 06 RSAs | Campaign, Ad group, Ad label, Ad type, Final URL, Path 1, Path 2, Test hypothesis, Headline 1-15, Description 1-4 | rsa manifest |
| 07 Assets | Campaign, **Level**, Asset type, Sitelink text, Final URL, Description line 1, Description line 2, Callout text, Snippet header, Snippet values | assets.json |
| 08 Launch QA | Priority, Check, Owner, Launch gate | campaign-strategy networks/tracking + the shared-list attach line |
| 09 Validation | Area, Ad group, Ad label, Field, Text, Length, Limit, Pass | recomputed from tab 06 |

`Keyword display` = the bracket/quote form ([exact] / "phrase") shown for human readability;
the CSV uses the explicit Match type column instead.

`Status` for keywords mirrors Ian's "Enabled after launch QA" (paused-until-QA model).

---

## 5. Per-entity Editor CSVs — the CONVERTER's target schema (not emitted here)

This is what the `google-ads-general` converter produces from the confirmed Excel. Kept here so
the workbook columns above stay traceable to the CSV columns. One CSV per entity type in v1
(Editor's flat namespace; entity = which cells populated). English headers auto-map on any
install (verified answer 57747). UTF-8 (Danish æ/ø/å load-bearing). Editor imports CSV only, not
.xlsx (answer 30564) — which is exactly why the converter exists.

Each bullet lists the CSV column → the workbook cell it reads. **Bold** = a value transform, not
a straight copy.

- **campaigns.csv** (from tab 01): `Campaign`←Campaign, `Campaign type`←Campaign type,
  `Budget`←**Daily budget (DKK)** (numeric cell, NOT the rationale), `Bid strategy type`←Bidding
  strategy, `Networks`←**Networks** (remap `Search; Search Partners; Display` → Editor's
  `Google Search;Display`), `Language targeting`←Languages, `Campaign status`←**`Paused`**
  (paused-until-QA). Budget > 0 is the only hard-required field.
- **adgroups.csv** (from tab 02): `Campaign`, `Ad group`, `Max CPC`←Max CPC (blank = let the
  strategy decide), `Ad group status`←`Enabled`.
- **keywords.csv** (from tab 03): `Campaign`, `Ad group`, `Keyword`, `Match type` (`Exact`/
  `Phrase` — NEVER blank, NEVER Broad; re-run guard §6.1), `Status`←**`Paused`**.
- **negatives.csv** (from tab 04, client-specific rows ONLY — skip the shared-list reference
  line): `Campaign`, `Ad group`←Ad group (blank when Level=campaign), `Keyword`←**bracket/quote
  form built from Negative keyword + Match type**, `Type`←**`Campaign negative` when
  Level=campaign / `Negative` when Level=ad_group**.
- **ads.csv (RSA)** (from tab 06): `Campaign`, `Ad group`, `Ad type`, `Headline 1-15`,
  `Description 1-4`, `Path 1-2`, `Final URL`. Drop Ad label / Test hypothesis.
- **assets.csv** (from tab 07): `Campaign`←**`<Account-level>` literal when Level=account, else
  the campaign name** (answer 56368), `Ad group` (blank=campaign-level), `Sitelink text`,
  `Final URL`, `Description line 1`, `Description line 2`, `Callout text`, `Snippet Values` +
  the snippet header column (UNVERIFIED name — see §7). Lead forms emit NO row.

---

## 6. Two hard emit-time guards (defense-in-depth)

1. **No blank/Broad positive keyword.** Every positive keyword row MUST have an explicit `Exact`
   or `Phrase`. If any row's match type is blank/missing/Broad, the assembler REFUSES to build
   and reports which rows. The silent-Broad trap caught at the boundary.
2. **Recompute tab 09 independently.** Do NOT trust fill-sheet's earlier gate. Recompute
   LEN + Pass for every headline (30) / description (90) / path (15) against the limit
   constants in `assemble.py`. Catches any human edit between Phase 3 and assembly. Any
   `Pass=False` row → flag prominently; the workbook still builds but the failure is loud.

Limits (30/90/15) are Google's externally-fixed RSA caps, declared as named constants
(`HEADLINE_LIMIT`/`DESCRIPTION_LIMIT`/`PATH_LIMIT`) in `assemble.py`. The script is
self-contained — it does NOT import `responsive-search-ads/sheet_layout.py` (decoupled: a
cross-skill dynamic import just to read three never-changing integers was needless coupling).
The same three values are mirrored in `sheet_layout.py` FIELDS; if Google ever changes a cap,
update both. The LEN+red-CF technique is reimplemented locally with openpyxl, not imported.

**Both guards MUST re-run in the converter.** A human can edit the confirmed Excel between
assembly and conversion — a Broad keyword or over-length headline introduced there would
otherwise sail straight into a CSV. The assembler guarding its inputs does not protect the
converter's inputs; the converter re-checks at its own boundary.

---

## 7. UNVERIFIED / carried-forward (flagged, not resolved here)

- **Structured-snippet header column name** (the CSV column, assets) — likely `Subject`/
  `Header`, UNVERIFIED. The workbook stores the snippet header value plainly in `Snippet header`;
  the UNVERIFIED part is what Editor's CSV header for it should be. The CONVERTER resolves this
  via an Editor round-trip before relying on it — do not hardcode it as certain there.
- **UTM tagging** — NOT written by the assembler yet (carried-forward gap, Peter's task
  breakdown). Tab 08 already carries Ian's "Final URLs and UTM convention approved" Should-pass
  gate, so the gap is covered AS A GATE even though the assembler doesn't emit UTMs. Source the
  template from Nur/Social later. Does NOT block Phase 4.
- **No live-Cowork end-to-end run** + **`05-rsa-copy` intake-injection assumption** (the
  reference injects per-ad-group intake into the `responsive-search-ads` skill) — both remain
  known unknowns (parked by Carl). The assembler smoke-test (below) tests the TRANSFORM, not the
  full live chain.

---

## 8. Smoke-test invariants (run the script against a golden reference before declaring done)

Golden reference = Ian's filled skeleton. Build a minimal set of the four input objects (or
derive from Ian's file), run the assembler, verify:
1. 10 tabs present with the correct headers (match Ian's tab names/columns).
2. The superset cells are present and populated: tab 02 `Max CPC`, tab 01 numeric
   `Daily budget (DKK)` (the number survives, not just the rationale), tab 04 `Level` +
   `Ad group`, tab 07 `Level` + per-type columns (snippet values NOT in the Final URL cell).
3. The 277 shared-list terms are NOT enumerated (only the single reference line in tab 04).
4. monitor_first_candidates appear in tab 05 only (the converter reads tab 04, so they can't
   leak to a CSV).
5. No blank/Broad positive keyword row (guard §6.1 fires if present).
6. Danish æ/ø/å survive in the workbook (UTF-8); account-level assets carry `Level=account`.
7. tab 09 Pass computes correctly against 30/90/15 (feed an over-length string → Pass=False).
