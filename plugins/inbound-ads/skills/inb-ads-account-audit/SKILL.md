---
name: inb-ads-account-audit
description: Kør en fuld read-only Google Ads paid search-audit for én klient på tværs af op til 12 moduler (kontostruktur, tracking, keywords, quality score, målretning, feed, pMax og mere) og lever resultatet som et poleret HTML slide deck i Inbound-designsystemet plus renderet PDF, hvor enhver ekstern write kun sker efter eksplicit bekræftelse.
---

# inb-ads-account-audit

Producér en komplet paid search-audit for en Google Ads-konto og lever den som et professionelt slide deck. Alt mod Google Ads er read-only. Enhver ekstern write (Drive, fil, mail) er gated bag eksplicit bekræftelse — vis hvad og hvor, vent på "ja", skriv så. Alt på dansk (intake, statusbeskeder, slide-copy) medmindre brugeren skriver engelsk.

## 1. Hent klientkontekst først

Før al dataindhentning på en navngiven klient: hent klientens AI Context ind i din kontekst. Det er en fri læsning, men obligatorisk — sådan arver du ID'er, kontakter, hårde rammer, navngivningskonvention, budstrategi-norm, KPI'er og pausede-kampagner-intention i stedet for at starte blindt.

1. Identificér klienten (navn, domæne eller konto). Uklart → spørg før du fortsætter (kontobekræftelsen sker i trin 2a).
2. Åbn master-klientindekset i Drive via Drive-connectoren: `search_files` efter Google Doc'en `Inbound CPH — Google Ads klient-index (AI Context)` (id `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`, i "A - Kunder"). Læs den med `read_file_content`. Den mapper hver klient til Google Ads ID, HubSpot ID, ClickUp-mappe, Stage, Drive-mappe og AI Context-fil.
3. Find klientens række (match på navn/domæne/Ads-ID). Notér Stage (customer / lead / opportunity / ikke tagget) — en ikke-`customer`-stage betyder ingen lukket konto; antag aldrig en aktiv retainer. Delte mapper (Lime, Retriever/Infomedia, GSGroup, Nemco, Julemærket, PhoneAlone, DI) → vælg rækken for det specifikke marked/konto.
4. Åbn klientens AI Context-`.md` via Drive-linket (`read_file_content`). Den indeholder ID'er, kontakter, hårde rammer, mål/KPI'er, navngivningskonvention, og link til changelog/optimeringslog — læs også det hvis opgaven kræver ændringshistorik.
5. Derefter videre til intake i trin 2, med AI Context som ground truth for klient-fakta.

Ingen række i indekset eller ingen AI Context-fil: sig det, fortsæt med det du kan samle (Drive-mappe, Ads MCP), men flag hullet eksplicit — spring aldrig opslaget stille over.

## 2. Intake (ét spørgsmål ad gangen)

Vent på svar på hvert spørgsmål før du stiller det næste.

**2a. Klientnavn.** Slå stille mod `list_accessible_accounts` og find bedste match. Præsentér til bekræftelse: "Fandt [Kontonavn] (ID: XXXXXXXXXX) — er det den rigtige konto?" Intet match → bed om ID manuelt.

**2b. Datointerval.** Tre valg: "Sidste 30 dage (standard)", "Sidste 90 dage", "Brugerdefineret". Default `LAST_30_DAYS`. Quality score-data bruger altid `LAST_90_DAYS` uanset valg.

**2c. Audit-scope.** To varianter:
- **Stor** (alle 12 moduler): Kontostruktur, Tracking & bid management, Indstillinger, Kreativer & annoncetekster, Keywords & negative keywords, Quality score, Målretning & audiences, Landingsider, Feed & merchant center, pMax, Display & Demand Gen, YouTube
- **Afgrænset** (9 kernemoduler, ingen pMax/Display/YouTube): de første 9 ovenfor

Eller lad brugeren manuelt liste hvilke moduler der skal med/udelades.

**2d. Kontekst.** Ét valgfrit spørgsmål: "Er der noget vi skal vide om kontoen inden vi starter? (Ny konto, igangværende forandringer, specifikke fokusområder?)"

Når alle svar er indsamlet: bekræft scope og gå i gang. "Godt — jeg henter data nu. Det tager et øjeblik."

## 3. Dataindhentning

Uddelegér konto-læsningen til `ads-analyst`-agenten (read-only account analyst) via Task-værktøjet; den henter og vurderer kontodata og returnerer fund. Giv den det bekræftede `customer_id`, det valgte scope + datointerval, og AI Context'en fra trin 1; brug MCP-kaldene og GAQL-spørgsmålene nedenfor som kontrakten for hvad den skal trække per modul. Kald alle relevante MCP-værktøjer for det valgte scope, parallelt hvor muligt.

### MCP-kald per modul

| Modul | Værktøjer |
|---|---|
| Kontostruktur | `get_campaign_performance(ALL)` + `run_custom_gaql` (kampagnenavne, brand-split, STAG/SKAG-detektion) |
| Tracking & bid management | `run_account_health_audit` + `get_campaign_performance` (budstrategier) + `run_custom_gaql` (konverteringshandlinger og værdier) |
| Indstillinger | `run_custom_gaql` — search partners, display select, geo, sprog, DSA, IP-ekskluderinger, ACA-flag |
| Kreativer & annoncetekster | `get_ad_performance` + `get_disapproved_ads` + `get_ad_extensions` |
| Keywords & negative keywords | `get_keyword_performance` + `get_search_terms_report` + `run_custom_gaql` (delte negativlister) |
| Quality score | `get_quality_score_audit` (LAST_90_DAYS altid) |
| Målretning & audiences | `get_age_gender_performance` + `get_location_performance` + `run_custom_gaql` (audiences, observation/targeting-mode) |
| Landingsider | `get_ad_performance` (udtræk unikke final URLs) + web_fetch per URL (se trin 4) |
| Feed & merchant center | `run_custom_gaql` — shopping campaigns, merchant center-link, feed-status |
| pMax | `run_custom_gaql` — asset groups, audience signals, search themes, brand exclusions, asset-typer |
| Display & Demand Gen | `get_campaign_performance(DISPLAY/DEMAND_GEN)` + `run_custom_gaql` (placement-ekskluderinger, kreativtyper) |
| YouTube | `get_campaign_performance(VIDEO)` + `run_custom_gaql` (ad formats, frequency capping, retargeting-lister) |

### GAQL-hjælpespørgsmål

Til kontostruktur-detektion:
```sql
SELECT campaign.name, campaign.status, campaign.advertising_channel_type,
       campaign.bidding_strategy_type, ad_group.name
FROM ad_group
WHERE campaign.status != 'REMOVED'
ORDER BY campaign.name
```

Til konverteringshandlinger:
```sql
SELECT conversion_action.name, conversion_action.category,
       conversion_action.counting_type, conversion_action.value_settings.default_value,
       conversion_action.status
FROM conversion_action
WHERE conversion_action.status = 'ENABLED'
```

Til delte negativlister:
```sql
SELECT shared_set.name, shared_set.type, shared_set.member_count
FROM shared_set
WHERE shared_set.type = 'NEGATIVE_KEYWORDS'
```

Til audience-lister:
```sql
SELECT user_list.name, user_list.size_for_search,
       user_list.type, user_list.membership_status
FROM user_list
WHERE user_list.membership_status = 'OPEN'
```

## 4. Landingsider via web_fetch

Udtræk alle unikke final URLs fra `get_ad_performance`. Deduplikér, tag de 10 hyppigste. For hver URL, kald `web_fetch`:
- Check at siden loader (ingen fejl)
- Udtræk primære overskrift og CTA-tekst (ordret fra siden)
- Notér mobiloptimering (viewport meta til stede?)
- Vurdér relevans ift. tilsvarende annonce-overskrift

Flag landingssider-sektionen med manuel-review-banneret (§ i trin 6.3).

## 5. Scoring

For hvert modul: tildel en score 1-10 baseret på de indsamlede data.

**Scoreguide:**
- 8-10: Godt sat op, ingen eller ubetydelige problemer
- 5-7: Fungerende men med tydelige forbedringspunkter
- 3-4: Markante problemer der påvirker performance
- 1-2: Kritiske fejl eller mangler

**Vægtet overordnet score:**
- Tracking & bid management: 20%
- Kontostruktur: 15%
- Keywords & negative keywords: 15%
- Quality score: 15%
- Kreativer & annoncetekster: 10%
- Indstillinger: 10%
- Målretning & audiences: 10%
- Landingsider: 5%
- Øvrige (Feed, pMax, Display, YouTube): fordelt på resterende 0-20% afhængig af scope

**Score-chip farver:** 7-10 grøn (#3DB069), 4-6 gul (#F5C842), 1-3 rød (#E05252).

## 6. Slide deck-generering

Generér et komplet HTML-slide deck baseret på `template.html` i samme mappe. Udfyld alle slide-sektioner med faktiske data og analyserede findings.

### Slide-struktur

1. **Cover** — klientnavn, "Paid Search Audit", dato, Inbound-logo
2. **Primære takeaways** — 4 vigtigste findings, AI-syntetiseret
3. **Den store overblik** — overordnet score + alle inkluderede moduler med score-chips og én-linje-summering (lyst slide)
4. **Per-modul detalje-slides** (ét per inkluderet modul) — venstre mørkt panel (modulnavn + "Det kigger vi efter"-tjekliste med ikoner) + højre lyst panel (faktiske findings)
5. **Hvad gør konkurrenterne?** — altid en placeholder-slide med manuel-review-banner
6. **End card**

### 6.1 Findings per modul

For hvert modul: skriv 4-8 bullet-punkter baseret på de faktiske data, med ikon foran hvert punkt:
- Godt / best practice fulgt: `<span class="finding-icon ok">✓</span>`
- Ikke optimalt / kan forbedres: `<span class="finding-icon warn">~</span>`
- Kritisk problem: `<span class="finding-icon bad">✗</span>`
- Noget de bør overveje: `<span class="finding-icon tip">→</span>`

### 6.2 "Det kigger vi efter" per modul

Inkluder altid det relevante tjekliste-indhold i det mørke venstre panel:

**Kontostruktur:** Følger man en gængs anerkendt struktur (STAG, SKAG, Hagakure)? Giver strukturen mening ift. algoritmen/mennesket? Er strukturen konsistent? Er navngivningskonvention implementeret? Er brand og non-brand opdelt?

**Tracking & bid management:** Er relevante tracking-punkter opsat og virker de? Er tracking korrekt kategoriseret, opdelt i primary og secondary? Har konverteringerne fået tildelt værdier? Er budstrategier og budgetter implementeret korrekt? Er der tilstrækkelige konverteringer?

**Indstillinger:** Har man slået search partners og display select fra? Er der korrekt sprogmålretning? Er geografisk målretning korrekt? Er DSA sprogmålretning og site korrekt? Benytter kampagnerne account eller campaign goals? Er der opsat IP exclusions? Er automatically created assets slået fra?

**Kreativer & annoncetekster:** Indgår keywords i annoncer? Er annoncerne skrevet til mennesker først? Er de relevante og velproducerede? Er USP'er tydeligt repræsenteret? Er der stave-/grammatikfejl? Benyttes alle relevante komponenter og extensions? Er extensions og assets korrekt implementeret? Bruger man pinning og headlines korrekt ift. matchtyper?

**Keywords & negative keywords:** Er søgeordene af høj relevans? Har man implementeret matchtyper på en korrekt og forsvarlig måde? Er der implementeret udførlige negativlister og er de strukturerede? Har man håndteret search terms tilstrækkeligt? Er der overensstemmelse med landingssider og søgeord?

**Quality score:** Hvordan fordeler spend sig på quality score? Hvad er den gennemsnitlige quality score på tværs af kontoen? Hvad er de primære drivere bag en eventuel dårlig quality score?

**Målretning & audiences:** Er der overblik og struktur i målgrupperne? Er de sat meningsfyldt op? Benyttes en navngivningskonvention? Tager målretningen nødvendigt højde for geografi og demografi? Benyttes målgrupper effektivt i kontoen?

**Landingsider:** Er landingssiderne relevante for søgeordene? Er landingssiderne tilpasset til hvor brugerne er i købsrejsen? Er siden nem at navigere? Er sideindholdet relevant? Loader landingssiden hurtigt for mobilbrugere?

**Feed & merchant center:** Er feed-strukturen korrekt? Er merchant center korrekt forbundet? Er der feed-fejl eller suspenderede produkter?

**pMax:** Er asset groups struktureret logisk og tematisk? Benyttes audience signals og search themes meningsfyldt? Er budgettet allokeret efter performance? Er der klar sammenhæng mellem performance og ad strength? Hvad bruges af assets? Er brand exclusions implementeret?

**Display & Demand Gen:** Har man frasorteret irrelevante brugere (retargeting & demografisk)? Er der god hygiejne i placeringer? Er retargeting og reach korrekt opdelt? Benyttes dynamiske eller statiske kreativer? Er det visuelle udtryk i overensstemmelse med brand?

**YouTube:** Er kreativerne designet til YouTube? Undgår man de mest almindelige fejl (nattetimer, børneindhold, video partners)? Passer formaterne af kreativerne? Er kampagnen opsat på en måde der er let at evaluere performance? Gøres der brug af relevante funktioner (sequencing, skippable, retargeting, feed)?

### 6.3 Manuel-review-flag

```html
<div class="manual-flag">KRAEVER MANUEL GENNEMGANG</div>
```

Sæt den altid på: "Hvad gør konkurrenterne?", Landingsider, og Display/YouTube-slides hvis kreativ-vurdering går ud over strukturelle data.

### 6.4 Quality score chart

Quality score-sektionen skal indeholde et SVG-chart der viser spend-fordeling på QS 1-10. Byg det som inline SVG-stolpediagram i slide-HTML ud fra `get_quality_score_audit`-data.

## 7. Fil-output

1. Gem HTML-deck som `YYYY-MM-DD-<klient-slug>-ads-audit.html` i Inbound CPH-vault under `work/inbound-cph/operations/decks/`.
2. Kør PDF-renderer:
   ```bash
   node $(dirname "$0")/render-pdf.js <deck.html> <deck.pdf> <slideCount>
   ```
3. Rapportér begge stier til brugeren.

Write-gate: vis stier og filnavne før du skriver. Bekræft med brugeren: "Skriver til [sti] — bekræft for at gemme."

## Regler

- Skriv aldrig data du ikke har fra MCP eller web_fetch — marker manglende data eksplicit.
- Dansk som standard for alle finding-tekster og slide-copy.
- Ingen emojis i slides, kode eller kommentarer.
- Ingen em-streger (--) i slide-copy — brug komma, kolon eller omstrukturering.
- Logo altid embedded som base64, aldrig en ekstern filsti.
- Afslut med en `## Datakilder`-sektion i chatten der lister hvilke MCP-værktøjer der blev kaldt.
