# Assembler contract (Phase-4 barrier)

Single source of truth for how the `assembler` skill merges the four upstream output shapes
into Ian's 10-tab review workbook + per-entity Editor CSVs, runs QA/validation, and stops at
import artifacts (NO API push). All tab/CSV column shapes verified against Ian's skeleton
(`InboundCPH_AI-SEO_Google-Ads-kampagneskelet.xlsx`) and the Editor CSV research (2026-06-03).
If SKILL.md and this file disagree, this file wins.

The assembler is a **pure transform**: 4 JSON shapes → workbook + CSVs. No external reads, no
writes to any account.

---

## 1. The four input shapes (join key = `campaign`)

| Shape | From | Carries |
|---|---|---|
| `campaign-strategy.json` | Phase 1 campaign-strategy | campaign, type, goal, budget, bidding, geo, languages, networks, conversion action, tracking_prerequisite, match-type policy |
| `structuring.json` | Phase 2 structuring | ad_groups[] (name, temperature, landing_page_url, theme, keywords[{text,match_type}], angles[], keyword_seeds_for_rsa[]), negatives{inherited_shared_list, client_specific_additions, monitor_first_candidates}, keyword_volume_disclaimer, structure_rationale |
| rsa manifest (`rsa_artifacts`) | Phase 3 rsa-copywriter | per ad group: ad_group, ads_json path, xlsx, n_rsas, final_url; each ads.json has headlines[15]/descriptions[4]/paths[2]/vinkel/hypotese per RSA |
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
| `inherited_shared_list` (the 277) | tab 08 launch-gate line ("attach shared list 'Generelle negative søgeord' id 6688642473") + a reference line in tab 04 | ANY CSV row. If the 277 appear in a CSV, Phase 2 has regressed. |
| `client_specific_additions` | tab 04 rows + the committed-negatives CSV (Type=Campaign negative / Negative per level) | — |
| `monitor_first_candidates` | tab 05 only | the committed-negatives CSV (committing them is the over-blocking harm) |

**Negative match types stay as-is** — broad is correct for negatives. Do NOT apply the
positive no-Broad lock to negatives. (Ian's own tab 04 happens to use Phrase per term; carry
whatever match_type the structuring object set.)

---

## 3. CSV = Editor-schema columns ONLY; metadata stays in the workbook

Same clean boundary as the RSA sheet (LEN/Vinkel/Hypotese stay in .xlsx). Every input object
carries non-Editor metadata the CSV MUST DROP, kept in the workbook as documentation:

| Object | Workbook-only metadata (NOT in CSV) |
|---|---|
| assets | `grounded_in`, `url_source`, `header_column_unverified` |
| negatives | `why` / `Reason`, `Category` |
| RSA | `vinkel`, `hypotese` (`Test hypothesis`), LEN columns |
| keywords | `Notes`, `Keyword display` |
| tab 09 | `Pass`, `Length` (validation is review-only) |

The assembler is the ONE place this boundary is enforced. CSVs carry only verified Editor
headers (see §5).

---

## 4. The 10-tab workbook (mirrors Ian's skeleton exactly)

| Tab | Content | Source |
|---|---|---|
| 00 README | Deliverable, Date, Account, Campaign, launch gate, import note | campaign-strategy + run meta |
| 01 Campaign settings | the 19 tab-01 columns | campaign-strategy.json |
| 02 Ad groups | Campaign, Ad group, Intent, Main kw, Supporting queries, Final URL, Path 1, Path 2, Primary angles | structuring ad_groups[] |
| 03 Keywords | Campaign, Ad group, Keyword, Match type, Keyword display, Final URL, Status, Notes | structuring keywords[] |
| 04 Negative keywords | Campaign, Negative keyword, Match type, Category, Reason | client_specific_additions + a shared-list reference line |
| 05 Monitor negatives | Candidate negative, Default action, Reason | monitor_first_candidates |
| 06 RSAs | Campaign, Ad group, Ad label, Ad type, Final URL, Path 1, Path 2, Test hypothesis, Headline 1-15, Description 1-4 | rsa manifest |
| 07 Assets | Campaign, Asset type, Asset text, Final URL, Description line 1, Description line 2 | assets.json |
| 08 Launch QA | Priority, Check, Owner, Launch gate | campaign-strategy networks/tracking + the shared-list attach line |
| 09 Validation | Area, Ad group, Ad label, Field, Text, Length, Limit, Pass | recomputed from tab 06 |

`Keyword display` = the bracket/quote form ([exact] / "phrase") shown for human readability;
the CSV uses the explicit Match type column instead.

`Status` for keywords mirrors Ian's "Enabled after launch QA" (paused-until-QA model).

---

## 5. Per-entity Editor CSVs (verified schema, English headers)

One CSV per entity type in v1 (Editor's flat namespace; entity = which cells populated). English
headers auto-map on any install (verified answer 57747). UTF-8 (Danish æ/ø/å load-bearing).

- **campaigns.csv:** `Campaign`, `Campaign type`, `Budget`, `Bid strategy type`, `Networks`,
  `Language targeting`, `Campaign status`. (Budget > 0 is the only hard-required field.)
- **adgroups.csv:** `Campaign`, `Ad group`, `Max CPC`, `Ad group status`.
- **keywords.csv:** `Campaign`, `Ad group`, `Keyword`, `Match type` (`Exact`/`Phrase` —
  NEVER blank, NEVER bare), `Status`.
- **negatives.csv:** client-specific additions ONLY. `Campaign`, `Ad group` (blank for
  campaign-level), `Keyword`, `Type` (`Campaign negative` for campaign-level / `Negative` for
  ad-group-level). Match type via the keyword text syntax or the Type column — pick ONE.
- **ads.csv (RSA):** the Editor RSA columns (Campaign, Ad Group, Ad type, Headline 1-15,
  Description 1-4, Path 1-2, Final URL). Reuse the RSA column set from `sheet_layout.py` FIELDS
  (drop LEN/Vinkel/Hypotese).
- **assets.csv:** `Campaign`, `Ad group` (blank=campaign-level; `<Account-level>` literal for
  account-level), `Sitelink text`, `Final URL`, `Description line 1`, `Description line 2`,
  `Callout text`, `Snippet Values` + the snippet header column (UNVERIFIED name — see §7).
  Lead forms emit NO row.

---

## 6. Two hard emit-time guards (defense-in-depth)

1. **No blank/Broad positive keyword.** Every keywords.csv row MUST have an explicit `Exact`
   or `Phrase`. If any row's match type is blank/missing/Broad, the assembler REFUSES to emit
   the keyword CSV and reports which rows. This is the last gate before a human import — the
   silent-Broad trap caught at the boundary.
2. **Recompute tab 09 independently.** Do NOT trust fill-sheet's earlier gate. Recompute
   LEN + Pass for every headline (30) / description (90) / path (15) against the limits
   imported from `sheet_layout.py`. Catches any human edit between Phase 3 and assembly. Any
   `Pass=False` row → flag prominently; the workbook still builds but the failure is loud.

Limits (30/90/15) and the LEN+red-CF technique are IMPORTED from
`responsive-search-ads/sheet_layout.py` (FIELDS owns them) — never retype them here. Reuse the
limits + CF pattern, not `build_sheet` itself (it's RSA-specific).

---

## 7. UNVERIFIED / carried-forward (flagged, not resolved here)

- **Structured-snippet header column name** (assets) — likely `Subject`/`Header`, UNVERIFIED.
  Emit it in a clearly-labeled column + carry the `header_column_unverified` flag into a
  build-time Editor round-trip note in the output. Do not hardcode it as certain.
- **UTM tagging** — NOT written by the assembler yet (carried-forward gap, Peter's task
  breakdown). Tab 08 already carries Ian's "Final URLs and UTM convention approved" Should-pass
  gate, so the gap is covered AS A GATE even though the assembler doesn't emit UTMs. Source the
  template from Nur/Social later. Does NOT block Phase 4.
- **No live-Cowork end-to-end run** + **rsa-copywriter intake-injection assumption** — both
  remain known unknowns (parked by Carl). The assembler smoke-test (below) tests the TRANSFORM,
  not the full live chain.

---

## 8. Smoke-test invariants (run the script against a golden reference before declaring done)

Golden reference = Ian's filled skeleton. Build a minimal set of the four input objects (or
derive from Ian's file), run the assembler, verify:
1. 10 tabs present with the correct headers (match Ian's tab names/columns).
2. CSV columns match the verified Editor schema (§5).
3. The 277 shared-list terms appear in NO CSV (grep the negatives.csv).
4. monitor_first_candidates appear in NO committed-negatives CSV (tab 05 only).
5. No blank/Broad positive keyword row (guard §6.1 fires if present).
6. Danish æ/ø/å survive in workbook + CSV (UTF-8).
7. tab 09 Pass computes correctly against 30/90/15 (feed an over-length string → Pass=False).
