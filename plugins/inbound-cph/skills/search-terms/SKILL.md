---
name: search-terms
description: Run a focused Google Ads search terms analysis for one client and deliver a colour-coded spreadsheet (eight tabs) that classifies every term as relevant, winner-to-promote, mis-placed, irrelevant, or borderline, grounds the calls in the client's scraped offering, and hands back an import-ready negative-keyword list. Read-only against Google Ads; builds a fresh .xlsx and saves to Drive or locally (runs in Cowork). Use when the user says "search term analyse", "soegetermer for [klient]", "find spild i [klient]", "negative keyword kandidater", "hvilke soegetermer konverterer", or "analyser search terms".
---

# search-terms

Produce an action-oriented search terms analysis for one Google Ads account and deliver it as a colour-coded Google Sheet. The deep, single-purpose version of the keyword module in `ads-audit`: one job, done thoroughly, output as a worklist the ads team can act on.

Read-only against Google Ads. The skill analyses and recommends. It never writes negative keywords back to the account. The ads team applies changes manually in Google Ads / Editor.

Full design rationale lives in `SPEC.md` in this folder. This file is the runnable contract.

## When to use

Trigger phrases: "search term analyse", "soegetermer for [klient]", "find spild", "negative keyword kandidater", "hvilke soegetermer konverterer", "analyser search terms", "soegeterm-rapport".

## Context (read before anything else)

A **keyword** is what you bid on. A **search term** is what the user actually typed, matched to a keyword via match types and Google close variants (`NEAR_PHRASE`, `NEAR_EXACT`, `BROAD`). The search terms report is where spend leaks. We sort every term into one of five classifications (taxonomy field-tested by an Inbound user, plus VINDER):

1. **RELEVANT** - matches the client's offering, sitting in the right place -> keep, and consider adding as an explicit keyword.
2. **VINDER** - converts well and is not yet its own exact keyword -> promote to an exact keyword so we control bid and quality. (The one action the user's original template did not separate out.)
3. **FORKERT_PLACERET** - the term already exists as a keyword in a *different* ad group, so it is stealing traffic from where it should land -> add as a negative in the current ad group and let the right keyword serve it.
4. **IRRELEVANT** - wrong intent for this client (a service/word the client does not offer, competitor, off-category) -> add as a negative keyword.
5. **GRAENSE** - generic or ambiguous -> flag for manual review rather than force a bucket.

Two principles carried from the user's template:
- **Classification is grounded in the client's actual offering** (scraped from the landing page), so every IRRELEVANT call is auditable: a human can read what the client sells and see why a term does not fit.
- The deliverable includes an **import-ready negatives list** ("Anbefalede negatives"): negative keyword, match type, level (ad group / campaign / account), wasted budget, reason. This is the bridge from analysis to action in Google Ads Editor.

Negatives can live at three levels (ad group / campaign / account-shared list). We suggest a level per blocked term, always as a recommendation.

## Trin 0 - Kontekst

Read `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` first - it holds the write-gate rules and the language policy. Read `${CLAUDE_PLUGIN_ROOT}/context/drive-map.md` to find the client's Drive working folder (where the sheet should land).

The Drive upload is an external write, gated behind explicit confirmation. Everything against Google Ads is read-only.

## Trin 1 - Intake (one question at a time)

Ask each, wait for the answer before the next.

**1a. Klientnavn.** Match against `list_accessible_accounts` by account name. Present the match for confirmation: "Fandt [Kontonavn] (ID: XXXXXXXXXX) - er det den rigtige konto?" If no match, ask for the ID manually.

**1b. Datointerval.** Offer "Sidste 3 maaneder (standard)", "Sidste 30 dage", or custom. **Default LAST_90_DAYS** - search-term patterns need volume; the user's template used a 3-month window for good reason.

**1c. Landingsside / website.** Ask for the client's main URL. Used to ground classification in what the client actually offers (Trin 2c). If the user does not have it, fall back to asking them to describe the offering.

**1d. Taerskler (valgfrit).** Offer the defaults and let the user override:
- `SPEND_FLOOR` = 5 DKK (skip terms below this spend - matches the user's template filter)
- `WINNER_CPA_MULT` = 1.0 (winner if CPA <= account CPA)
- `WINNER_MIN_CONV` = 2 (fallback winner trigger when account CPA is unreliable)

Default = recommended. Most runs accept defaults; tune after the first real run.

**1e. Kontekst (valgfrit).** "Er der noget om kundens forretning vi skal vide? (Konkurrentnavne, ord der altid er spild, ad groups vi ved er forkert sat op?)"

Confirm scope, then: "Godt - jeg henter data nu."

## Trin 2 - Dataindhentning (read-only)

**2a. Search terms** via `run_custom_gaql`. GAQL (not the prebuilt tool) so we guarantee cost-desc ordering and pull match type + the triggering keyword:

```sql
SELECT
  search_term_view.search_term,
  campaign.id, campaign.name,
  ad_group.id, ad_group.name,
  segments.keyword.info.text, segments.keyword.info.match_type,
  segments.search_term_match_type,
  metrics.cost_micros, metrics.clicks, metrics.conversions,
  metrics.conversions_value, metrics.impressions, metrics.ctr
FROM search_term_view
WHERE segments.date DURING LAST_90_DAYS
  AND campaign.status = 'ENABLED'
ORDER BY metrics.cost_micros DESC
LIMIT 500
```

Swap the date range per intake (default 90 days). `campaign.status = 'ENABLED'` enforces the hard rule: paused campaigns are intentional and never analysed. Drop rows where cost < `SPEND_FLOOR`.

**2b. Existing keywords** (the whole keyword map, for the placement + winner cross-checks). Pull keyword text, match type, **and the ad group + campaign each lives in** via GAQL on `keyword_view`:

```sql
SELECT
  ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type,
  campaign.name, ad_group.name
FROM keyword_view
WHERE campaign.status = 'ENABLED' AND ad_group_criterion.status = 'ENABLED'
```

Build a map: `normalised_keyword -> [{campaign, ad_group, match_type}]`. This is what makes FORKERT_PLACERET detectable.

**2c. Client offering via Firecrawl.** Scrape the landing page / website from intake (same pattern as `ads-audit`). Extract what the client sells: products/services, target segments, destinations, key categories. This grounds the IRRELEVANT calls and fills the "Klientens udbud" block in Oversigt. If scraping fails, fall back to the offering the user described in intake; never invent it.

**2d. Account total search cost** for coverage reporting:

```sql
SELECT metrics.cost_micros FROM campaign
WHERE segments.date DURING LAST_90_DAYS
  AND campaign.status = 'ENABLED'
  AND campaign.advertising_channel_type = 'SEARCH'
```

Coverage % = (sum of pulled term cost) / (account search cost). Report it in Oversigt.

### Field rules (verified against live data)
- **Cost is micros.** DKK = `cost_micros / 1_000_000`.
- **Grain = one row per (term x campaign x ad_group x match_type).** Aggregate up to one row per term; keep the triggering keyword(s) + match type(s) as a comma-joined list so the row stays single but the detail survives.
- **`conversions_value` may be 0 while `conversions` > 0** (lead-gen accounts). CPA is the primary signal. Compute ROAS only if any term on the account has `conversions_value` > 0. Never compute ROAS on a zero-value account.
- **`metrics.ctr` is a fraction** (0.3529 = 35.29%). Multiply by 100 for the CTR (%) column.
- **`segments.keyword.info.text` / `.match_type`** give the triggering keyword + match (verified). `ORDER BY` fields must also appear in `SELECT` (GAQL rule).

## Trin 3 - Aggreger + klassificering

Group raw rows by `search_term`. Per term: sum cost/clicks/conversions/value/impressions; `cpa = cost/conversions` if conversions > 0 else null; `ctr` from totals; `matches` = list of {campaign, ad_group, keyword, match_type}; `n_campaigns`, `n_ad_groups` = distinct counts.

Account references (compute once):
- `account_conversions`, `account_cost`, `account_cpa = account_cost / account_conversions` (**reliable only if** `account_conversions >= 10`; else fall back and flag low-confidence in Oversigt).
- `account_has_value` = any term with value > 0.

Classify each term into exactly one bucket, in this priority order:

1. **FORKERT_PLACERET** - the term (normalised) exists as an ENABLED keyword in a **different** ad group than the one it served in here (from the 2b map). It is pulling traffic away from its correct home. Begrundelse names the other ad group(s) + match type, e.g. "Eksisterer allerede som keyword i [Kampagne > Ad group] (EXACT). Boer tilfoejes som negativ i den nuvaerende ad group." Suggested negative level = ad group.

2. **IRRELEVANT** - the term does not fit the client's offering (from 2c) or is clear off-intent (gratis, selv/DIY, jobs/stilling, brugt, wikipedia/forum, competitor). This is the LLM judgement, grounded in the scraped offering. Begrundelse names the offending token, e.g. "Indeholder 'studierejse' som DSC ikke tilbyder." Suggested level = account-shared list if generic, else campaign.

3. **VINDER** - converts well and is **not already its own exact keyword** for the ad group it served in: `conversions >= 1` AND `cpa <= account_cpa * WINNER_CPA_MULT` (reliable account_cpa) else `conversions >= WINNER_MIN_CONV`. Begrundelse: "Konverterer godt (X konv, CPA Y kr), ikke eget exact keyword - promover til exact." Record "Eksisterer som keyword?" (Nej / Ja, broad-phrase).

4. **RELEVANT** - matches the offering and is correctly placed (already an exact keyword, or simply on-intent and well-located). Begrundelse: "Core-soegning der matcher udbuddet, godt placeret."

5. **GRAENSE** - generic/ambiguous, cannot be confidently assigned (e.g. a broad head term that could be relevant or not). Begrundelse: "Generisk soegning - vurder manuelt." Honest bucket; do not force these.

A term that is both convertible and mis-placed is FORKERT_PLACERET (priority 1) - placement is the more actionable fix.

## Trin 4 - Anbefalede negatives (synthese)

Build the import-ready list from FORKERT_PLACERET + IRRELEVANT (and any GRAENSE the analysis confirms as waste). One row per recommended negative:
`Negative keyword | Anbefalet match type | Hvor (niveau) | Spildt budget (DKK) | Begrundelse`

- **Match type:** EXACT for placement fixes (block the precise term), PHRASE for generic-irrelevant tokens that should catch variants.
- **Hvor:** ad group for FORKERT_PLACERET; account/shared list for generic IRRELEVANT; campaign for client-specific irrelevant.
- **Spildt budget:** the term's spend over the window.
- Deduplicate by (negative, level). This tab is what the ads team imports into Editor.

## Trin 5 - Oversigt

Assemble the summary: account ID, period, scope, spend filter, the distribution table (count + spend per bucket with a TOTAL), the scraped client offering, and method notes (data source, micros conversion, that existing negatives were considered). This is the auditable cover sheet.

## Trin 6 - Byg arket (write - gated)

A fresh `.xlsx` is built each run by `build-sheet.py` (openpyxl) and saved to Drive via the connector, or locally. Mirrors rsa-copy: no `gws` CLI, no Sheets API, no remote clone, no 403 fallback. Tab colours, header fills, and the Spild cost colour-scale are baked into the `.xlsx` layer, so they survive upload to Drive and stay intact when opened as a Google Sheet. **Runs in Cowork and locally.**

**Destination:** client's Drive working folder from `context/drive-map.md` if known, else ask for a folder name/ID (maps under `${user_config.inbound_root_folder_id}`), else save locally.

Steps:

1. Write the analysis to a JSON file matching the schema in the header of `build-sheet.py`: client + account_id + period + scope + filter, `offering` (scraped), `method_notes`, `distribution` (count + spend per bucket), `rows` (every term once, each tagged with its `klassificering`), and `negatives` (the synthesised import list). The script routes rows into per-tab views by `klassificering` itself.
2. Build the workbook:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/search-terms/build-sheet.py \
     --in <analysis.json> \
     --out "Search Terms - <klient> - <YYYY-MM-DD>.xlsx"
   ```
3. **Drive (gated):** show destination folder + filename, confirm, then upload the `.xlsx` via the Drive connector `create_file` (same params as rsa-copy):
   - `title`: `Search Terms - <klient> - <YYYY-MM-DD>`
   - `parentId`: the folder from intake (or omit for root)
   - `contentMimeType`: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
   - `base64Content`: base64 of the `.xlsx`
   The file lands as an editable Office-mode file in Drive; it opens in Google Sheets with the eight tabs, blue headers, and per-bucket classification fills intact.
4. **Lokalt:** the `.xlsx` is already on disk at the `--out` path. Confirm the path.

Note column widths, header style, and classification fills come from `build-sheet.py`; if the layout changes, edit that script, not this file.

### Tabs (built by build-sheet.py)

| Fane | Indhold |
|---|---|
| Oversigt | konto-ID, periode, scope, filter, fordelingstabel (antal + spend pr. bucket + TOTAL), klientens udbud, metode-noter |
| Alle search terms | hver term een gang, klassificerings-kolonne farvet pr. bucket |
| Relevante (tilfoej keyword) | RELEVANT-termer |
| Vindere (promover til exact) | VINDER-termer |
| Forkert placeret | FORKERT_PLACERET-termer |
| Irrelevante (tilfoej negativ) | IRRELEVANT-termer |
| Graensetilfaelde | GRAENSE-termer |
| Anbefalede negatives | importklar negativ-liste |

### Kolonner

Term-faner (Alle + de fem klassificerings-faner) deler samme 13 kolonner:
`Search term | Match type | Kampagne | Ad group | Triggerende keyword | Keyword match type | Budget brugt (DKK) | Impressions | Klik | CTR (%) | Konverteringer | Klassificering | Begrundelse / Anbefaling`

Anbefalede negatives:
`Negative keyword | Anbefalet match type | Hvor (kampagne/konto-niveau) | Spildt budget (DKK) | Begrundelse`

Colour palette (baked into `build-sheet.py`, matches the user's template + VINDER): header #1F4E78 white bold; classification fills RELEVANT #C6EFCE, VINDER #A9D08E, FORKERT_PLACERET #FFEB9C, IRRELEVANT #FFC7CE, GRAENSE #D9E1F2.

## Trin 7 - Output

Deliver:
1. **Link to the sheet** (or the local `.xlsx` path if saved locally).
2. **Chat summary:** spend per bucket, antal vindere, antal anbefalede negatives + samlet spildt budget, coverage %, any low-confidence flags.
3. **Naeste skridt (manuelt, human-in-the-loop):** the ads team imports the Anbefalede-negatives tab into Editor, promotes Vindere as exact keywords, reviews Graensetilfaelde manually. The skill applies nothing automatically.

End with a `## Datakilder` section listing the MCP tools called (incl. Firecrawl for the landing page).

## Regler
- Read-only against Google Ads. Never write negatives back.
- Paused campaigns excluded at the query level. Never flag a paused campaign.
- CPA is the primary signal; ROAS only if the account has conversion value.
- Classification is grounded in the scraped offering; the suggested negative level is always a recommendation.
- Dansk for all finding text and sheet copy.
- No emojis. No em-dashes (use comma, colon, or restructure).
- Write-gate every external write (Drive upload): show what and where, confirm first. Never share the sheet with the client and never send mail; present the link, Carl forwards.
- Mark any missing or unreliable data explicitly. Never invent terms or metrics.
