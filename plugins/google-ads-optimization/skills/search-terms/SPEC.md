# search-terms skill spec

Design doc for the search-terms analysis skill. **As of v0.7.0, SKILL.md + build-sheet.py are the source of truth**; this file is the original design rationale (the GAQL/micros/grain verification and threshold reasoning below still hold). Where this file's *taxonomy* disagrees with SKILL.md, SKILL.md wins.

## v0.7.0 revision (read this first)

The original taxonomy below (Spild / Vinder / Irrelevant / Nyt emne) was superseded after a user produced a field-tested template (Dansk Studie Center). The shipped taxonomy is now five buckets, grounded in the client's scraped offering:

- **RELEVANT** - matches offering, correctly placed.
- **VINDER** - converts well, not yet an exact keyword -> promote (our addition to the user's template).
- **PLACEMENT_PROBLEM** (was FORKERT_PLACERET in v0.7) - the term is relevant but lands in the wrong place. Two sub-types: **struktur** (already a keyword in another production ad group, stealing traffic) and **intent** (ad-group's ads/LP do not address the search intent even though the term is on-category). The intent half was added in v0.8 after the user pointed out that DSC's "Grupperejser" ad group in campaign 2 pointed to the front page, not a grupperejse-LP - exactly the kind of mismatch struktur alone misses.
- **IRRELEVANT** - not part of the client's offering / off-intent -> negative.
- **GRAENSE** - generic/ambiguous -> manual review.

Output is an eight-tab `.xlsx` (Oversigt, Alle search terms, the five per-bucket tabs, Anbefalede negatives) built by `build-sheet.py`, matching the user's layout + colours. The "Anbefalede negatives" tab is an import-ready list. Default window is 90 days. The kept-from-our-version pieces: aggregation per term, ENABLED-only filter, CPA + low-confidence handling. See SKILL.md for the runnable contract.

## Purpose

Run a focused, action-oriented search terms analysis for one Google Ads client and deliver a colour-coded spreadsheet that tells the ads team exactly what to do: which terms to keep, promote, re-place, or block.

This is the deep, single-purpose version of the "Keywords & negative keywords" module in `ads-audit-report`. ads-audit-report gives a broad diagnosis across 12 modules; this skill does one thing thoroughly and hands back a worklist, not a slide deck.

Read-only against Google Ads. The skill never writes negatives back to the account. It analyses and recommends. The ads team applies changes manually in Google Ads / Editor. (Matches the human-in-the-loop hard rule.)

## What a search terms analysis is (context)

- **Keyword** = the word you bid on (e.g. `+kloak`, `"tv inspektion"`).
- **Search term** = what the user actually typed, which matched a keyword via broad/phrase/exact + close variants.

Because of match types and Google close variants (`NEAR_PHRASE`, `NEAR_EXACT`, `BROAD`), one keyword triggers many search terms. The search terms report is the only place you see the user's real words, and it is where spend leaks. The four things we look for:

1. **Waste** - cost, zero conversions. Block as a negative keyword.
2. **Winner** - converts at good CPA, not yet its own keyword. Promote to an exact keyword so you control bid and quality.
3. **Irrelevant / intent-mismatch** - technically related but wrong intent (`gratis`, `jobs hos`, `DIY`, `brugt`, competitor names). Block, usually on a shared list.
4. **New theme** - a cluster of terms with no keyword coverage. Expansion opportunity (new ad group / keywords).

### Negative keyword levels (why "Foreslaaet niveau" exists)

Negatives can live at three levels:
- **Ad group** - blocks the term only in one ad group (fine elsewhere).
- **Campaign** - blocks across the whole campaign.
- **Shared list / account** - one list of universal junk (`gratis`, `jobs`, `wikipedia`) attached to many campaigns.

We infer a suggested level. This is a recommendation, not ground truth, and is labelled as such:
- Term wasted in **one** campaign only -> suggest **campaign** level.
- Term flagged generic-irrelevant by the LLM (`gratis`/`jobs`/`DIY`) -> suggest **shared list**.
- Term wasted in one ad group but fine in another -> suggest **ad group** level.

## Data source and field shape (verified against live data 2026-05-27)

Pull via `run_custom_gaql` against `search_term_view`, not the prebuilt `get_search_terms_report`, because GAQL lets us guarantee `ORDER BY cost desc` (so we capture spend-heavy terms first, not an arbitrary 200) and pull `search_term_match_type`.

```sql
SELECT
  search_term_view.search_term,
  campaign.id, campaign.name,
  ad_group.id, ad_group.name,
  segments.search_term_match_type,
  metrics.cost_micros, metrics.clicks, metrics.conversions,
  metrics.conversions_value, metrics.impressions
FROM search_term_view
WHERE segments.date DURING LAST_30_DAYS
  AND campaign.status = 'ENABLED'
ORDER BY metrics.cost_micros DESC
LIMIT 500
```

Verified facts about the response:
- **Cost is in micros.** DKK = `cost_micros / 1_000_000`.
- **Grain = one row per (search_term x campaign x ad_group x match_type).** Same term can appear multiple times. We aggregate up to one row per term (per the term-grain decision) and keep the list of matches.
- **`ORDER BY metrics.cost_micros DESC` works** - confirmed, so the LIMIT captures the costliest terms.
- **`conversions_value` may be 0 even when `conversions` > 0** (KFH kloak is like this - lead-gen account with no revenue value set). So **CPA is the primary winner/waste signal; ROAS/value is only used when `conversions_value` > 0 somewhere on the account.** Never compute ROAS on a zero-value account.
- `campaign.status = 'ENABLED'` in the WHERE clause enforces the hard rule: paused campaigns are intentional, never analysed.

### Limit / completeness

Default `LIMIT 500`. Because rows are cost-desc, the top of the list is the spend that matters. Report in the sheet overview how much total cost the pulled terms represent vs the account's total search cost for the window (one extra `run_custom_gaql` for `SELECT metrics.cost_micros FROM campaign WHERE ...`), so the user knows the coverage (e.g. "these 500 terms = 94% of search spend"). If coverage is low on a huge account, offer to raise the limit.

## Aggregation (one row per term)

Group all raw rows by `search_term`. For each term:
- `cost` = sum of cost_micros / 1e6
- `clicks` = sum
- `conversions` = sum
- `conversions_value` = sum
- `impressions` = sum
- `cpa` = cost / conversions if conversions > 0 else null
- `matches` = list of {campaign_name, ad_group_name, match_type}
- `n_campaigns` = distinct campaign count across matches
- `match_types` = distinct set (flag if any of NEAR_PHRASE / NEAR_EXACT / BROAD present - close-variant matches are where waste tends to live)

## Classification

### Account-level reference numbers (compute once)
- `account_conversions` = sum of conversions across all pulled terms.
- `account_cost` = sum of cost.
- `account_cpa` = account_cost / account_conversions, **only if** account_conversions >= a minimum sample (say >= 10 conversions). If below that, `account_cpa` is treated as unreliable and the rules fall back to absolute floors.
- `account_has_value` = true if any term has conversions_value > 0.

### Rule pass (deterministic, runs on every term)

Constants (defaults, overridable at intake):
- `ABS_WASTE_FLOOR` = 150 DKK (a term costing less than this with 0 conv is noise, not worth a negative).
- `MIN_CLICKS_WASTE` = 8 (alternative trigger: lots of clicks, no conv, even if cheap).
- `WINNER_CPA_MULT` = 1.0 (winner if its CPA is at or below account CPA).
- `LLM_MIN_COST` = 80 DKK (don't spend tokens classifying sub-80-kr noise).

Buckets:

1. **Waste** if `conversions == 0` AND (
   `cost >= max(account_cpa, ABS_WASTE_FLOOR)` if account_cpa reliable,
   else `cost >= ABS_WASTE_FLOOR`
   OR `clicks >= MIN_CLICKS_WASTE`
   ).
   Degenerate-account guard: if account has 0 conversions everywhere (brand-new account), waste relies purely on the floor + click rule. Flagged in overview as low-confidence.

2. **Winner** if `conversions >= 1` AND `cpa <= account_cpa * WINNER_CPA_MULT` (account_cpa reliable) AND the term is **not already an exact keyword** (see keyword cross-check). If account_cpa unreliable, winner = `conversions >= 2` (any term pulling multiple conversions is worth promoting).

3. **Neutral** otherwise. Neutral terms with `cost >= LLM_MIN_COST` go to the LLM pass.

### Keyword cross-check (for winners)

Pull existing keywords once via `get_keyword_performance(customer_id, LAST_30_DAYS, limit=500)` (or GAQL on `keyword_view` if more are needed). Normalise (lowercase, strip match-type punctuation). A winner that already exists as an EXACT keyword is **not** a promote candidate (downgrade to Neutral) - we already control it. A winner matching only as broad/phrase is a real promote candidate.

### LLM pass (intent, runs only on Neutral terms with cost >= LLM_MIN_COST)

Predicate for sending to the LLM: `bucket == Neutral AND cost >= LLM_MIN_COST`. This keeps the LLM off both the rule-decided terms and the long tail of cheap noise.

For each such term, classify intent given the client's business (from intake context + campaign names):
- **Irrelevant** - wrong intent for this advertiser: `gratis`, `selv`/`DIY`, `jobs`/`stilling`, `brugt`, `wikipedia`/`forum`, named competitors, clearly off-category. -> red bucket, suggested level = shared list (generic) or campaign (specific).
- **New theme** - relevant intent but a topic with no current keyword coverage. -> blue bucket.
- **Keep neutral** - relevant, already covered, just low volume. -> stays grey.

LLM output per term must be: `{bucket, suggested_level, one_line_reason}`. The reason is shown in the sheet so the human can sanity-check.

## Suggested level logic

| Condition | Suggested level |
|---|---|
| Waste/irrelevant, hit only 1 campaign | Campaign |
| Generic-irrelevant (LLM: gratis/jobs/DIY/competitor) | Shared list |
| Wasted in 1 ad group, converts/relevant in another | Ad group |
| Hit multiple campaigns, all waste | Shared list |

Always render with a "(forslag)" suffix in the sheet header so it's clearly a recommendation.

## Output: colour-coded .xlsx via Drive connector

Built fresh each run by an openpyxl script (`build-sheet.py`), uploaded via the Drive connector `create_file` (base64), or saved locally. This mirrors the **newer** rsa-copy mechanic (xlsx + connector), not the older gws path: tab colours, header fills, and the cost colour-scale are baked into the .xlsx layer, so they survive upload and stay intact when opened in Google Sheets (the file lands as an editable Office-mode file, same as rsa-copy). No `gws` CLI, no Sheets API, no remote clone, **no 403 problem** (the auth fragility that hit rsa-copy's gws path is sidestepped entirely). Runs in Cowork and locally.

### Runtime requirements
- openpyxl (Python) to build the workbook.
- Drive connector to upload (optional - can save locally instead).

**Destination:** client's Drive working folder if known (from `context/drive-map.md`), else ask for a folder, else local disk.

### Sheet structure (tabs)

| Tab | Rows | Tab colour | Header colour |
|---|---|---|---|
| Overblik | totals, spild i kr, count per bucket, coverage %, top-5 findings, low-confidence flags | none | dark navy |
| Spild (negativ) | waste terms, cost desc | red | red |
| Vindere (promover) | winner terms not already exact, CPA asc | green | green |
| Irrelevante | LLM-flagged intent-mismatch | orange | orange |
| Nye emner | LLM-flagged new themes, grouped | blue | blue |
| Raadata | all terms, all metrics, all matches | grey | grey |

### Columns per action tab

Spild / Irrelevante:
`Soegeterm | Cost (kr) | Klik | Konv | Impr | Match types | Kampagne(r) | Foreslaaet niveau (forslag) | Begrundelse`

Vindere:
`Soegeterm | Cost (kr) | Konv | CPA (kr) | Konto-CPA | Kampagne | Eksisterer som keyword? | Anbefaling`

Nye emner:
`Tema | Soegetermer i temaet | Samlet cost | Samlet konv | Forslag`

Raadata:
`Soegeterm | Cost (kr) | Klik | Konv | Konv-vaerdi | Impr | CPA | Match types | Kampagne(r) | Annoncegruppe(r) | Bucket`

### Colour coding mechanics (openpyxl, baked into the .xlsx)

All applied by `build-sheet.py`:
1. **Tab colours** - `ws.sheet_properties.tabColor` per sheet (red/green/orange/blue/grey).
2. **Header fill + bold white** - `PatternFill` + `Font(bold, white)` on row 1 of each tab.
3. **Cost colour-scale (Spild)** - `ColorScaleRule` on the Cost column so the heaviest waste reads darkest.

Because these live in the .xlsx layer (not in CSV values), they survive the Drive upload and render in the resulting Google Sheet. No fallback path needed - if the Drive connector is unavailable, the same .xlsx is simply saved locally.

## Skill flow (maps to SKILL.md steps)

- **Trin 0 - Kontekst:** read `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` (write-gate + language). Read `context/drive-map.md` for the client folder.
- **Trin 1 - Intake (one question at a time):**
  1. Client name -> match against `list_accessible_accounts`, confirm "Fandt [navn] (ID: X) - rigtig konto?".
  2. Date range (default LAST_30_DAYS; offer 90).
  3. Optional: override thresholds (ABS_WASTE_FLOOR, WINNER_CPA_MULT) - default = recommended.
  4. Optional context: anything about the business that helps intent classification.
- **Trin 2 - Pull data:** the GAQL query above + keyword cross-check + account total cost. Note coverage %.
- **Trin 3 - Aggregate + rule pass.**
- **Trin 4 - LLM intent pass** on the Neutral-and-costly subset.
- **Trin 5 - Suggested level.**
- **Trin 6 - Build sheet (write, gated):** show the destination path + tab list, confirm, create file via Drive connector, write tabs via gws. 403 -> fallback.
- **Trin 7 - Output:** sheet link + a short chat summary (spild i kr, n waste, n winners, n new themes, coverage %, any low-confidence flags). Datakilder section listing MCP tools called.

## Rules
- Read-only against Google Ads. Never write negatives back.
- Paused campaigns excluded at the query level. Never flag a paused campaign.
- CPA primary; ROAS only if the account has conversion value.
- Suggested level is always labelled a recommendation.
- Danish copy, no emojis, no em-dashes.
- Write-gate every external write (Drive create, gws cell writes): show what + where, confirm first.
- End with a Datakilder section listing the MCP tools used.

## Open questions to confirm before build
- Default thresholds (150 kr floor, 8 clicks, 80 kr LLM min) - sane starting points, tune after first real run with Rikke.
- Whether the client Drive folder is reliably in `context/drive-map.md`; if not, sheets land in root and Carl moves them.
