# Kampagne-overblik template

The assembler emits a **`Kampagne overblik.md`** alongside the review workbook — one short,
precise lead document the operator reads first. It does two jobs and nothing else:
1. A concise **findings + decisions** summary (what the build chose and why).
2. A **bulk-upload / import** how-to.

Keep it tight. It is the human's at-a-glance brief, not a re-statement of the workbook. The
workbook is the detail; this is the cover sheet. The assembler fills the `{{...}}` slots from
the four input objects; the model writes the 1-line rationales (findings are semantic, not
mechanical).

The template the assembler renders:

```markdown
# Kampagne-overblik — {{client}}

**Konto:** {{account_id}} · **Kampagne:** `{{campaign}}` · **Dato:** {{date}}
**Status ved import:** Paused (aktivér først efter review + launch-QA)

## Beslutninger (hvad bygget valgte)
- **Struktur:** {{n_ad_groups}} ad groups, {{n_keywords}} keywords (Exact + udvalgt Phrase, ingen Broad). {{structure_rationale_one_line}}
- **Negativer:** delt MCC-liste "{{shared_neg_name}}" påført by-reference (id {{shared_neg_id}}) + {{n_client_negatives}} klient-specifikke. {{n_monitor}} monitor-first-kandidater (tilføj først efter search-terms-data).
- **Keywords:** tema-afledte{{semrush_note}} — validér volumen i Keyword Planner før aktivering.
- **Annoncer:** {{n_rsas}} RSA'er. {{rsa_note}}
- **Assets:** {{n_sitelinks}} sitelinks, {{n_callouts}} callouts, {{n_snippets}} structured snippets. {{assets_note}}
- **Budstrategi/budget:** {{bidding}} · {{budget_line}}

## Vigtigste fund / flag (læs før go-live)
{{findings_bullets}}   ← model writes 2-5 one-liners: ad-less ad groups (tab 08), over-length fields (tab 09), unconfirmed sitelink URLs omitted, snippet-header-column UNVERIFIED, tracking-gate, overlapping ad groups to pause, etc. Pull from the workbook's tab 08 + tab 09 + the input objects. If nothing notable: "Ingen blokerende fund — klar til review."

## Sådan importerer du (manuelt i Google Ads Editor)
1. Åbn **Google Ads Editor** og vælg kontoen ({{account_id}}).
2. Editor importerer CSV, ikke .xlsx — denne workbook er review-laget. Gem de relevante faner (01-07)
   som CSV fra Excel, eller indtast rækkerne direkte i Editor via **Account → Import → From file** per
   entitetstype (campaigns → ad groups → keywords → ads (RSA) → assets (sitelinks/callouts/snippets) →
   negative keywords), eller kør **Vej A** i `inb-ads-campaign-build` på den godkendte opsætning for at
   oprette kampagnen direkte via `ads-writer` i stedet.
3. Importér i denne rækkefølge, og kør **Check Changes** efter hver: campaigns → ad groups → keywords → ads (RSA) → assets (sitelinks/callouts/snippets) → negative keywords.
4. **Tilknyt den delte negativliste** "{{shared_neg_name}}" (id {{shared_neg_id}}) til kampagnen — den er IKKE i nogen import (den påføres by-reference).
5. **Manuelt efter import:** sæt sprog (Dansk), bekræft Denmark = Presence (ikke Presence-or-Interest), verificér leadgen-konverteringshandlingen.
6. Kør **Check Changes** — løs alle røde fejl. Verificér kampagnestatus = **Paused**. Først derefter Post Changes.

## Før go-live (launch-gate — fuld liste i workbook fane 08)
{{must_pass_gates}}   ← model pulls the Must-pass rows from tab 08: tracking fires, Presence-only geo, Search Partners/Display off, shared list attached, client negatives applied, ad-less ad groups resolved.

---
Genereret af campaign-build assembler. Workbook = detaljen; dette = forsiden. Intet er pushet til kontoen.
```

## Rules
- ONE lead doc. Do NOT also emit a separate `README_importvejledning.md` — fold the import
  steps into this overblik so there aren't two overlapping import docs.
- Keep findings to one-liners. If the model is writing paragraphs, it's duplicating the
  workbook — stop.
- The import steps describe the manual Editor path even though v1 of the assembler emits
  Excel-only: a human exports the relevant tabs to CSV (or keys them in directly) from the
  confirmed workbook, or runs Vej A on the approved setup instead. State that once (step 2),
  don't belabor it.
- `campaign-state` line is always **Paused** (the valid Editor status), per the
  campaign-settings default.
