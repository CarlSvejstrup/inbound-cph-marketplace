---
name: search-terms
description: Run a focused Google Ads search terms analysis for one client and deliver a colour-coded spreadsheet (six tabs: waste, winners, irrelevant, new themes, raw) that tells the ads team what to block, what to promote to keywords, and which themes to expand into. Read-only against Google Ads; builds a fresh .xlsx and saves to Drive or locally (runs in Cowork). Use when the user says "search term analyse", "soegetermer for [klient]", "find spild i [klient]", "negative keyword kandidater", "hvilke soegetermer konverterer", or "analyser search terms".
---

# search-terms

Produce an action-oriented search terms analysis for one Google Ads account and deliver it as a colour-coded Google Sheet. The deep, single-purpose version of the keyword module in `ads-audit`: one job, done thoroughly, output as a worklist the ads team can act on.

Read-only against Google Ads. The skill analyses and recommends. It never writes negative keywords back to the account. The ads team applies changes manually in Google Ads / Editor.

Full design rationale lives in `SPEC.md` in this folder. This file is the runnable contract.

## When to use

Trigger phrases: "search term analyse", "soegetermer for [klient]", "find spild", "negative keyword kandidater", "hvilke soegetermer konverterer", "analyser search terms", "soegeterm-rapport".

## Context (read before anything else)

A **keyword** is what you bid on. A **search term** is what the user actually typed, matched to a keyword via match types and Google close variants (`NEAR_PHRASE`, `NEAR_EXACT`, `BROAD`). The search terms report is where spend leaks. We sort terms into four actions:

1. **Spild** - cost, zero conversions -> block as a negative keyword.
2. **Vinder** - converts at good CPA, not yet its own keyword -> promote to an exact keyword.
3. **Irrelevant** - wrong intent (gratis, jobs, DIY, brugt, competitor) -> block, usually on a shared list.
4. **Nyt emne** - a cluster of terms with no keyword coverage -> expansion opportunity.

Negatives can live at three levels (ad group / campaign / shared list). We suggest a level per blocked term, always labelled as a recommendation.

## Trin 0 - Kontekst

Read `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` first - it holds the write-gate rules and the language policy. Read `${CLAUDE_PLUGIN_ROOT}/context/drive-map.md` to find the client's Drive working folder (where the sheet should land).

Every Drive file creation and every cell write is an external write. All are gated behind explicit confirmation.

## Trin 1 - Intake (one question at a time)

Ask each, wait for the answer before the next.

**1a. Klientnavn.** Match against `list_accessible_accounts` by account name. Present the match for confirmation: "Fandt [Kontonavn] (ID: XXXXXXXXXX) - er det den rigtige konto?" If no match, ask for the ID manually.

**1b. Datointerval.** Offer "Sidste 30 dage (standard)", "Sidste 90 dage", or custom. Default LAST_30_DAYS.

**1c. Taerskler (valgfrit).** Offer the defaults and let the user override:
- `ABS_WASTE_FLOOR` = 150 DKK (below this with 0 conv = noise, no negative)
- `MIN_CLICKS_WASTE` = 8 (alt trigger: many clicks, no conv, even if cheap)
- `WINNER_CPA_MULT` = 1.0 (winner if CPA <= account CPA)
- `LLM_MIN_COST` = 80 DKK (don't LLM-classify cheaper noise)

Default = recommended. Most runs accept defaults; tune after the first real run.

**1d. Kontekst (valgfrit).** "Er der noget om kundens forretning vi skal vide til at vurdere relevans? (Konkurrentnavne, ord der altid er spild, fokusomraader?)" This feeds the LLM intent pass.

Confirm scope, then: "Godt - jeg henter data nu."

## Trin 2 - Dataindhentning (read-only)

**2a. Search terms** via `run_custom_gaql`. GAQL (not the prebuilt tool) so we guarantee cost-desc ordering and pull match type:

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

Swap the date range per intake. `campaign.status = 'ENABLED'` enforces the hard rule: paused campaigns are intentional and never analysed.

**2b. Existing keywords** for the winner cross-check via `get_keyword_performance(customer_id, <range>, limit=500)`. Need keyword text + match type.

**2c. Account total search cost** for coverage reporting:

```sql
SELECT metrics.cost_micros FROM campaign
WHERE segments.date DURING LAST_30_DAYS
  AND campaign.status = 'ENABLED'
  AND campaign.advertising_channel_type = 'SEARCH'
```

Coverage % = (sum of pulled term cost) / (account search cost). Report it.

### Field rules (verified against live data)
- **Cost is micros.** DKK = `cost_micros / 1_000_000`.
- **Grain = one row per (term x campaign x ad_group x match_type).** Aggregate up to one row per term; keep the match list.
- **`conversions_value` may be 0 while `conversions` > 0** (lead-gen accounts). CPA is the primary signal. Compute ROAS only if any term on the account has `conversions_value` > 0. Never compute ROAS on a zero-value account.

## Trin 3 - Aggreger + regel-pass

Group raw rows by `search_term`. Per term: sum cost/clicks/conversions/value/impressions; `cpa = cost/conversions` if conversions > 0 else null; `matches` = list of {campaign, ad_group, match_type}; `n_campaigns` = distinct campaigns; flag if any match type is a close variant (NEAR_*/BROAD).

Account references (compute once):
- `account_conversions`, `account_cost`.
- `account_cpa = account_cost / account_conversions`, **reliable only if** `account_conversions >= 10`. Below that, fall back to absolute floors and flag low-confidence.
- `account_has_value` = any term with value > 0.

Buckets:

1. **Spild** if `conversions == 0` AND (
   `cost >= max(account_cpa, ABS_WASTE_FLOOR)` when account_cpa reliable, else `cost >= ABS_WASTE_FLOOR`
   OR `clicks >= MIN_CLICKS_WASTE` ).
   If the account has 0 conversions everywhere (new account): waste relies on floor + click rule only; flag low-confidence in Overblik.

2. **Vinder** if `conversions >= 1` AND `cpa <= account_cpa * WINNER_CPA_MULT` (reliable account_cpa) AND not already an exact keyword (Trin 3b). If account_cpa unreliable: winner = `conversions >= 2`.

3. **Neutral** otherwise. Neutral terms with `cost >= LLM_MIN_COST` go to Trin 4.

### Trin 3b - Keyword cross-check
Normalise existing keywords (lowercase, strip match-type punctuation). A winner already present as EXACT -> not a promote candidate (downgrade to Neutral; we control it). A winner matching only broad/phrase -> real promote candidate. Record "Eksisterer som keyword?" (Nej / Ja, broad-phrase / Ja, exact).

## Trin 4 - LLM intent-pass

Run only on terms where `bucket == Neutral AND cost >= LLM_MIN_COST`. For each, given the client's business (intake context + campaign names), classify:

- **Irrelevant** - wrong intent (gratis, selv/DIY, jobs/stilling, brugt, wikipedia/forum, competitor, off-category).
- **Nyt emne** - relevant intent, topic with no keyword coverage.
- **Keep neutral** - relevant, already covered, low volume.

Output per term: `{bucket, suggested_level, begrundelse}` (one Danish line). The begrundelse shows in the sheet so the human can sanity-check.

## Trin 5 - Foreslaaet niveau

| Condition | Niveau (forslag) |
|---|---|
| Spild/irrelevant, ramte kun 1 kampagne | Kampagne |
| Generisk-irrelevant (gratis/jobs/DIY/konkurrent) | Delt liste |
| Spild i 1 annoncegruppe, konverterer/relevant i en anden | Annoncegruppe |
| Ramte flere kampagner, alt spild | Delt liste |

Always render the column header as "Foreslaaet niveau (forslag)".

## Trin 6 - Byg arket (write - gated)

A fresh `.xlsx` is built each run by `build-sheet.py` (openpyxl) and saved to Drive via the connector, or locally. Mirrors rsa-copy: no `gws` CLI, no Sheets API, no remote clone, no 403 fallback. Tab colours, header fills, and the Spild cost colour-scale are baked into the `.xlsx` layer, so they survive upload to Drive and stay intact when opened as a Google Sheet. **Runs in Cowork and locally.**

**Destination:** client's Drive working folder from `context/drive-map.md` if known, else ask for a folder name/ID (maps under `${user_config.inbound_root_folder_id}`), else save locally.

Steps:

1. Write the classified analysis to a JSON file matching the schema in the header of `build-sheet.py` (the six buckets + Overblik totals + top findings + low-confidence flags).
2. Build the workbook:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/search-terms/build-sheet.py \
     --in <analysis.json> \
     --out "Search terms - <klient> - <YYYY-MM-DD>.xlsx"
   ```
3. **Drive (gated):** show destination folder + filename, confirm, then upload the `.xlsx` via the Drive connector `create_file` (same params as rsa-copy):
   - `title`: `Search terms - <klient> - <YYYY-MM-DD>`
   - `parentId`: the folder from intake (or omit for root)
   - `contentMimeType`: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
   - `base64Content`: base64 of the `.xlsx`
   The file lands as an editable Office-mode file in Drive; it opens in Google Sheets with the six coloured tabs and the cost colour-scale intact.
4. **Lokalt:** the `.xlsx` is already on disk at the `--out` path. Confirm the path.

Note the column widths and tab colours come from `build-sheet.py`; if the layout changes, edit that script, not this file.

### Tabs (built by build-sheet.py)

| Fane | Indhold | Tab-farve |
|---|---|---|
| Overblik | totaler, spild i kr, antal pr. bucket, coverage %, top-5 findings, low-confidence flags | ingen |
| Spild | spild-termer, cost desc | roed |
| Vindere | vindere ikke allerede exact, CPA asc | groen |
| Irrelevante | LLM intent-mismatch | orange |
| Nye emner | LLM nye temaer, grupperet | blaa |
| Raadata | alle termer, alle metrics, alle matches | graa |

### Kolonner

Spild / Irrelevante:
`Soegeterm | Cost (kr) | Klik | Konv | Impr | Match types | Kampagne(r) | Foreslaaet niveau (forslag) | Begrundelse`

Vindere:
`Soegeterm | Cost (kr) | Konv | CPA (kr) | Konto-CPA | Kampagne | Eksisterer som keyword? | Anbefaling`

Nye emner:
`Tema | Soegetermer i temaet | Samlet cost | Samlet konv | Forslag`

Raadata:
`Soegeterm | Cost (kr) | Klik | Konv | Konv-vaerdi | Impr | CPA | Match types | Kampagne(r) | Annoncegruppe(r) | Bucket`

Colour palette (baked into `build-sheet.py`, reuses ads-audit chips where they overlap): red #E05252, green #3DB069, orange #F5A623, blue #4A90D9, grey #9B9B9B, navy #1F2A44.

## Trin 7 - Output

Deliver:
1. **Link to the sheet** (or the local `.xlsx` path if saved locally).
2. **Chat summary:** spild i kr, antal spild-termer, antal vindere, antal nye emner, coverage %, any low-confidence flags.
3. **Naeste skridt (manuelt, human-in-the-loop):** the ads team reviews the Spild tab and adds negatives at the suggested level, promotes Vindere as exact keywords, considers Nye emner as new ad groups. The skill applies nothing automatically.

End with a `## Datakilder` section listing the MCP tools called.

## Regler
- Read-only against Google Ads. Never write negatives back.
- Paused campaigns excluded at the query level. Never flag a paused campaign.
- CPA is the primary signal; ROAS only if the account has conversion value.
- Foreslaaet niveau is always a recommendation, labelled "(forslag)".
- Dansk for all finding text and sheet copy.
- No emojis. No em-dashes (use comma, colon, or restructure).
- Write-gate every external write (Drive upload): show what and where, confirm first. Never share the sheet with the client and never send mail; present the link, Carl forwards.
- Mark any missing or unreliable data explicitly. Never invent terms or metrics.
