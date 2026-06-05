---
name: ads-audit-report
description: Run a full Google Ads paid search audit for a client and output a polished HTML slide deck (dark-navy Inbound design system) plus a rendered PDF audit report. Use when the user says "lav en audit af [klient]", "kør en Google Ads audit", "lav en audit-rapport", "audit [klient]", "ads audit report", or asks for a paid search review.
---

# ads-audit-report

Produce a complete paid search audit for a Google Ads account and output it as a professional slide deck.

## When to use

Trigger phrases: "lav en audit", "kør en audit af", "paid search audit", "Google Ads audit", "gennemgaa kontoen", "lav en gennemgang af annoncer".

## Trin 0 — Kontekst

Laes `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` foer noget andet. Den indeholder write-gate-reglerne og sprogpolitikken.

## Trin 1 — Intake (konversation foer data)

Stil disse spoergsmaal eet ad gangen. Vent paa svar paa hvert spoergsmaal foer du stiller det naeste.

**1a. Klientnavn**
Bed om klientens navn. Slaas dernaest stille mod `list_accessible_accounts` og find den bedste match baseret paa kontonavn. Praesenter det fundne match til bekraeftelse: "Fandt [Kontonavn] (ID: XXXXXXXXXX) — er det den rigtige konto?" Hvis ingen match: bed brugeren opgive ID manuelt.

**1b. Datointerval**
Tilbyd tre valg: "Sidste 30 dage (standard)", "Sidste 90 dage", eller "Brugerdefineret". Default er LAST_30_DAYS. Til quality score data bruges altid LAST_90_DAYS uanset valg (behoever mere data).

**1c. Audit-scope**
Tilbyd to varianter:
- **Stor** (alle 12 moduler): Kontostruktur, Tracking & bid management, Indstillinger, Kreativer & annoncetekster, Keywords & negative keywords, Quality score, Maalretning & audiences, Landingsider, Feed & merchant center, pMax, Display & Demand Gen, YouTube
- **Afgranset** (9 kernemoduler, ingen pMax/Display/YouTube): de foerste 9 af ovenstaaende

Eller lad brugeren manuelt liste hvilke moduler der skal inkluderes/ekskluderes.

**1d. Kontekst**
Eet valgfrit spoergsmaal: "Er der noget vi skal vide om kontoen inden vi starter? (Ny konto, igangvaerende forandringer, specifikke fokusomraader?)"

Naar alle svar er indsamlet: bekraeft scope og gaak i gang. "Godt — jeg henter data nu. Det tager et oejeblik."

## Trin 2 — Dataindhentning

Kald alle relevante MCP-vaerktoejer for det valgte scope. Kald dem parallelt hvor muligt.

### MCP-kald per modul

| Modul | Vaerktoejer |
|---|---|
| Kontostruktur | `get_campaign_performance(ALL)` + `run_custom_gaql` (kampagnenavne, brand-split, STAG/SKAG-detektion) |
| Tracking & bid management | `run_account_health_audit` + `get_campaign_performance` (budstrategier) + `run_custom_gaql` (konverteringshandlinger og vaerdier) |
| Indstillinger | `run_custom_gaql` — search partners, display select, geo, sprog, DSA, IP-ekskluderinger, ACA-flag |
| Kreativer & annoncetekster | `get_ad_performance` + `get_disapproved_ads` + `get_ad_extensions` |
| Keywords & negative keywords | `get_keyword_performance` + `get_search_terms_report` + `run_custom_gaql` (delte negativlister) |
| Quality score | `get_quality_score_audit` (LAST_90_DAYS altid) |
| Maalretning & audiences | `get_age_gender_performance` + `get_location_performance` + `run_custom_gaql` (audiences, observation/targeting-mode) |
| Landingsider | `get_ad_performance` (udtaek unikke final URLs) + Firecrawl per URL (se Trin 3) |
| Feed & merchant center | `run_custom_gaql` — shopping campaigns, merchant center-link, feed-status |
| pMax | `run_custom_gaql` — asset groups, audience signals, search themes, brand exclusions, asset-typer |
| Display & Demand Gen | `get_campaign_performance(DISPLAY/DEMAND_GEN)` + `run_custom_gaql` (placement-ekskluderinger, kreativtyper) |
| YouTube | `get_campaign_performance(VIDEO)` + `run_custom_gaql` (ad formats, frequency capping, retargeting-lister) |

### GAQL-hjaelpespørgsmaal

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

## Trin 3 — Landingsider via Firecrawl

Udtaek alle unikke final URLs fra `get_ad_performance`. Deduplikaer og tag de 10 hyppigste. For hver URL:
- Check at siden loader (ingen fejl)
- Udtaek primaire overskrift og CTA-tekst
- Note om mobiloptimering (viewport meta tilstede?)
- Vurder relevans ift. tilsvarende annonce-overskrift

Flag landingssider-sektionen med manuel-review-banner (se Trin 5 §3).

## Trin 4 — Scoring

For hvert modul: tildel en score 1-10 baseret paa de indsamlede data.

**Scoreguide:**
- 8-10: Godt sat op, ingen eller ubetydelige problemer
- 5-7: Fungerende men med tydelige forbedringspunkter
- 3-4: Markante problemer der paavirker performance
- 1-2: Kritiske fejl eller mangler

**Vaegtet overordnet score:**
- Tracking & bid management: 20%
- Kontostruktur: 15%
- Keywords & negative keywords: 15%
- Quality score: 15%
- Kreativer & annoncetekster: 10%
- Indstillinger: 10%
- Maalretning & audiences: 10%
- Landingsider: 5%
- Oevrige (Feed, pMax, Display, YouTube): fordelt paa resterende 0-20% afhængig af scope

**Score-chip farver:**
- 7-10: groen (#3DB069)
- 4-6: gul (#F5C842)
- 1-3: roed (#E05252)

## Trin 5 — Slide deck-generering

Generer et komplet HTML-slide deck baseret paa `template.html` i samme mappe. Udfyld alle slide-sektioner med faktiske data og analyserede findings.

### Slide-struktur

1. **Cover** — klientnavn, "Paid Search Audit", dato, Inbound-logo
2. **Primaere takeaways** — 4 vigtigste findings, AI-syntetiseret
3. **Den store overblik** — overordnet score + alle inkluderede moduler med score-chips og een-linje-summering (lyst slide)
4. **Per-modul detalje-slides** (eet per inkluderet modul) — venstre mørkt panel (modulnavn + "Det kigger vi efter" tjekliste med ikoner) + hoeire lyst panel (faktiske findings)
5. **Hvad goer konkurrenterne?** — altid en placeholder-slide med manuel-review-banner
6. **End card**

### §1 — Findings per modul

For hvert modul: skriv 4-8 bullet-punkter baseret paa de faktiske data. Brug disse ikoner foer hvert punkt:
- Godt / best practice fulgt: `<span class="finding-icon ok">✓</span>`
- Ikke optimalt / kan forbedres: `<span class="finding-icon warn">~</span>`
- Kritisk problem: `<span class="finding-icon bad">✗</span>`
- Noget de boer overveje: `<span class="finding-icon tip">→</span>`

### §2 — "Det kigger vi efter" per modul

Inkluder altid det relevante tjekliste fra auditskabelonen i det moerke venstre panel. Se referencerne nedenfor.

**Kontostruktur:** Foelger man en gaengs anerkendt struktur (STAG, SKAG, Hagakure)? Giver strukturen mening ift. algoritmen/mennesket? Er strukturen konsistent? Er navngivningskonvention implementeret? Er brand og non-brand opdelt?

**Tracking & bid management:** Er relevante tracking-punkter opsat og virker de? Er tracking korrekt kategoriseret, opdelt i primary og secondary? Har konverteringerne faaet tildelt vaerdier? Er budstrategier og budgetter implementeret korrekt? Er der tilstraekkelige konverteringer?

**Indstillinger:** Har man slaet search partners og display select fra? Er der korrekt sprogmaalretning? Er geografisk maalretning korrekt? Er DSA sprogmaalretning og site korrekt? Benytter kampagnerne account eller campaign goals? Er der opsat IP exclusions? Er automatically created assets slaet fra?

**Kreativer & annoncetekster:** Indgaar keywords i annoncer? Er annoncerne skrevet til mennesker foerst? Er de relevante og velproducerede? Er USP'er tydeligt repraesenteret? Er der stave-/grammatikfejl? Benyttes alle relevante komponenter og extensions? Er extensions og assets korrekt implementeret? Bruger man pinning og headlines korrekt ift. matchtyper?

**Keywords & negative keywords:** Er søgeordene af høj relevans? Har man implementeret matchtyper paa en korrekt og forsvarlig maade? Er der implementeret udfoerlige negativlister og er de strukturerede? Har man haandteret search terms tilstraekkeligt? Er der overensstemmelse med landingssider og søgeord?

**Quality score:** Hvordan fordeler spend sig paa quality score? Hvad er den gennemsnitlige quality score paa tvaers af kontoen? Hvad er de primaere drivere bag en eventuel daarlig quality score?

**Maalretning & audiences:** Er der overblik og struktur i maalgrupperne? Er de sat meningsfyldt op? Benyttes en navngivningskonvention? Tager maalretningen nødvendigt hoejde for geografi og demografi? Benyttes maalgrupper effektivt i kontoen?

**Landingsider:** Er landingssiderne relevante for søgeordene? Er landingssiderne tilpasset til hvor brugerne er i koebsrejsen? Er siden nem at navigere? Er sideindholdet relevant? Loader landingssiden hurtigt for mobilbrugere?

**Feed & merchant center:** Er feed-strukturen korrekt? Er merchant center korrekt forbundet? Er der feed-fejl eller suspenderede produkter?

**pMax:** Er asset groups struktureret logisk og tematisk? Benyttes audience signals og search themes meningsfyldt? Er budgettet allokeret efter performance? Er der klar sammenhaeng mellem performance og ad strength? Hvad bruges af assets? Er brand exclusions implementeret?

**Display & Demand Gen:** Har man frasorteret irrelevante brugere (retargeting & demografisk)? Er der god hygiejne i placeringer? Er retargeting og reach korrekt opdelt? Benyttes dynamiske eller statiske kreativer? Er det visuelle udtryk i overensstemmelse med brand?

**YouTube:** Er kreativerne designet til YouTube? Undgaar man de mest almindelige fejl (nattetimer, boerneindhold, video partners)? Passer formaterne af kreativerne? Er kampagnen opsat paa en maade der er let at evaluere performance? Gøres der brug af relevante funktioner (sequencing, skippable, retargeting, feed)?

### §3 — Manuel-review-flag

Brug dette HTML-komponent paa slides med manuelle sektioner:

```html
<div class="manual-flag">KRAEVER MANUEL GENNEMGANG</div>
```

Altid paa: Hvad goer konkurrenterne?, samt Landingsider, Display/YouTube-slides hvis kreativ-vurdering gaar ud over strukturelle data.

### §4 — Quality score chart

Quality score-sektionen skal indeholde et SVG-chart der viser spend-fordeling paa QS 1-10. Brug `get_quality_score_audit`-data til at bygge et simpelt stolpediagram som inline SVG i slide-HTML.

## Trin 6 — Fil-output

1. Gem HTML-deck som `YYYY-MM-DD-<klient-slug>-ads-audit.html` i Inbound CPH-vault under `work/inbound-cph/operations/decks/`
2. Koor PDF-renderer:
   ```bash
   node $(dirname "$0")/render-pdf.js <deck.html> <deck.pdf> <slideCount>
   ```
3. Raporter begge stier til brugeren

**Write-gate:** Vis stier og filnavne foer du skriver. Bekraeft med brugeren: "Skriver til [sti] — bekraeft for at gemme."

## Regler

- Skriv aldrig data du ikke har fra MCP eller Firecrawl. Marker manglende data eksplicit.
- Dansk som standard for alle finding-tekster og slide-copy.
- Ingen emojis i slides, kode eller kommentarer.
- Ingen em-streger (--) i slide-copy. Brug komma, kolon eller omstruktuering.
- Logo altid embedded som base64 — aldrig en ekstern filsti.
- Afslut med en `## Datakilder`-sektion i chatten der lister hvilke MCP-vaerktoejer der blev kaldt.
