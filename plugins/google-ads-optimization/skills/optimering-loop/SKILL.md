---
name: optimering-loop
description: Kør hele optimerings-loopet på en LIVE Google Ads-konto i ét hug - diagnosticer kontoen på tværs af flere dimensioner parallelt (søgetermer + negatives, RSA-asset-hygiejne, Quality Score) og saml fundene til ÉN redigerbar Excel-workbook eksperten retter og sender til kunden, hvorefter editor-csv-export laver Editor-CSV'erne. Læser kun aktive kampagner via Google Ads MCP, anbefaler kun (skriver ALDRIG til kontoen, pusher aldrig API'et). Significance-disciplin på Inbounds små danske konti: ingen statistisk sikkerhed data ikke kan bære. Alle RSA-forslag er NYE challengers (aldrig in-place edits - det nulstiller læring). Konto-niveau negatives udfoldes til per-kampagne-rækker. Brug når brugeren siger "kør optimerings-loop", "optimer kontoen", "fuld optimering af [klient]", "find alt vi kan forbedre", eller vil have hele diagnose-til-workbook-flowet på én gang. Svarer på dansk.
---

# optimering-loop

Det **samlede optimerings-loop** for en live Google Ads-konto: én kommando diagnosticerer kontoen
på flere dimensioner og afleverer ÉN redigerbar Excel-workbook med konkrete forslag — negatives,
vinder-keywords at promovere, og RSA-challengers. Eksperten retter workbooken, kan sende den til
kunden, og kører så `editor-csv-export` (i `google-ads-general`) der laver Editor-CSV'erne. Hele
forløbet og alt output er på dansk.

Dette er **operate-laget** (modsat campaign-build i `google-ads-setup`). Hvor `search-terms` og
`annonce-optimering` hver gør ÉN diagnose, kører dette skill dem sammen + Quality Score og samler
alt i den ene workbook — så eksperten ikke skal stykke tre regneark sammen i hånden.

## Hvorfor skillet er formet sådan (læs én gang — ikke til forhandling)

1. **Significance-disciplin er rygraden.** Inbounds konti er små danske annoncører. En live-test
   (2026-05-29) viste at per-asset CTR/CVR er konfunderet og at konverteringer på 0/1/2 er under
   signifikans. Derfor: en vinder-keyword kræver **≥2 konverteringer**; under 10 konverteringer på
   kontoen sættes et `low_confidence`-flag i Oversigt; RSA-asset-hygiejne dømmer **aldrig** en
   asset på CVR — kun struktur (dækning, dødvægt, vinkel-huller). Alt der hævder mere end data kan
   bære, er en fejl.

2. **Alle RSA-forslag er NYE challengers — aldrig in-place edits.** At redigere en live RSA's
   kreativ **nulstiller dens læring** (RSA'er er reelt immutable i Google Ads), og Google Ads
   Editors CSV kan ikke pålideligt matche en eksisterende RSA. Skillet emitterer derfor en frisk
   challenger (`Paused`); mennesket sætter den gamle annonce på pause når challengeren er bevist.
   (Beslutning 2026-06-09.)

3. **Konto-niveau negatives udfoldes.** Editor CSV har kun kampagne- og ad-group-niveau. Et fund
   på konto-niveau udfoldes til én `Campaign negative`-række per aktiv kampagne (samme blokerings-
   effekt, fuldt importérbart) + en note på "Laes mig"-fanen om delt-liste-alternativet.

4. **Læse-only, recommend-only.** Skillet rører ALDRIG kontoen — ingen mutate, intet API-push,
   ingen pause/rediger. Det afleverer en workbook. Mennesket importerer via Editor efter review.
   Human-in-the-loop på hver ekstern write er ikke til forhandling (repo-CLAUDE.md). Pausede
   kampagner/annoncer ekskluderes bevidst og flages ALDRIG som negativt fund.

## Hvad skillet gør (v1) — og hvad der er v2

**v1 (dette skill): diagnose → workbook.** Tre parallelle diagnoser + samling til workbooken:
- **Søgetermer + negatives** (`search-terms`-logik): klassificér hver term, find vinder-keywords
  (≥2 konv.) og spild-negatives, med significance-disciplin.
- **RSA-asset-hygiejne** (`annonce-optimering`-logik): tæl RSA per ad group (<2 → challenger-flag),
  find dødvægt, udled vinkel-huller. Kun struktur.
- **Quality Score**: keyword-grain (ingen fabrikeret ad-group-QS); landingsside er et flag, ikke
  en score.

**v2 (IKKE i dette skill endnu): measure-fasen** ("siden sidst": hvad foreslog vi, hvad blev
anvendt, flyttede det metrikken). Den kræver en run-persistens-model (hvor gemmes en kørsels
`recommendations.json` så næste kørsel kan sammenligne) — en separat designbeslutning, ikke en
oversættelse. v1 lukker IKKE loopet; det leverer diagnose-til-workbook. Sig det ærligt: dette er
"diagnose-loopet", ikke det fuldt lukkede measure-loop.

## How it works (arkitektur — læs én gang)

En **læse-skill** der kører i main-loopet. De deterministiske dele bor i `lib/` (medfølger
skillet): `lib/gaql/*` bygger GAQL-strenge + normaliserer resultater; `lib/review_workbook.py`
bygger den ene `.xlsx`; `lib/classify/taxonomy.md` er den delte klassifikations-taksonomi. Selve
MCP-kaldene og klassifikationen laver agenten (main-loop + sub-agenter), ikke Python'en.

**Kører på enhver maskine.** Eneste forudsætning er Python 3 + `pip` (review_workbook
self-bootstrapper openpyxl) og Google Ads MCP. Ingen `gws`, ingen Sheets-API.

## Trin 0 — Kontekst

Læs `references/headline-craft.md` (RSA-challenger-vinkler + tiebreakers; brug som VARIATION, ikke
hårde <20-tegns-lofter; behold "ignorér Ad Strength"-holdningen). Klassifikations-reglerne står i
`lib/classify/taxonomy.md`.

**Sprog: alt på dansk** — intake, statusbeskeder, workbook, næste-skridt. Skift kun til engelsk
hvis brugeren skriver engelsk.

**Forudsætning:** Google Ads MCP + et `customer_id`. Hvis MCP ikke er tilgængelig: sig det og stop.

## Trin 1 — Intake (ét `AskUserQuestion`-kald)

Udled så meget som muligt fra samtalen først. Saml i ét kald:

1. **Klient + `customer_id`** — bekræft hvis nævnt; ellers `list_accessible_accounts` → find id'et
   → bekræft. (Klientnoter ligger i vault `clients/*.md`, men spørg hvis i tvivl.)
2. **Analysevindue** — default **sidste 90 dage** (mere data → færre under-signifikans-tilfælde;
   bedre signal for optimering på Inbounds små konti). Vis `Sidste 90 dage (Anbefalet)`,
   `Sidste 30 dage`, `Andet`. **VIGTIGT:** `LAST_90_DAYS` er IKKE et gyldigt GAQL-literal — for
   90 dage / >30 dage beregn `BETWEEN '<YYYY-MM-DD>' AND '<YYYY-MM-DD>'`. `lib/gaql/window_clause()`
   (søgetermer/asset) og `lib/gaql/quality_score.date_range_arg()` (QS) håndterer begge dette; brug
   dem, gæt aldrig literalet.
3. **Gem-destination** — `Drive (klientens mappe)`, `Lokalt (.xlsx)`, eller begge. Drive = ekstern
   write → bekræft én gang før gem.

## Trin 2 — Kør de tre diagnoser (én sub-agent hver, parallelt)

Spawn **én sub-agent per diagnose** (kontekst-isolation: rå GAQL-svar fylder ikke main-loopet; hver
sub-agent returnerer kun struktureret JSON). De tre er uafhængige — kør dem parallelt.

Hver sub-agent får: `customer_id`, vinduet, stien til dette skills `lib/`, og besked om at (a) hente
GAQL-strengen fra det rette `lib/gaql`-modul, (b) køre den via `run_custom_gaql` (kun ENABLED
kampagner — pausede ekskluderes), (c) post-processe via modulets normaliser, (d) returnere JSON.

- **Søgeterm-agent** → `SearchTermFindings`. GAQL: `lib/gaql/search_terms.py`
  (`search_terms_query`, `keyword_map_query`, `ad_group_ads_query`, `account_search_cost_query`).
  **Kør FØRST det deterministiske sweep — agenten må aldrig selv finde/tabe kandidater** (det er
  rygraden, se `references/selection-spec.md`):
  ```python
  import sweep   # lib/sweep.py — IKKE 'select' (det skygger Pythons stdlib)
  w   = sweep.sweep_winners(search_term_rows, keyword_map_rows)   # {winners, skipped}
  neg = sweep.sweep_negatives(search_term_rows, offering_tokens)  # [{band, thin_data, ...}]
  ov  = sweep.all_terms_overview(search_term_rows)                # alle >=5 DKK termer
  ```
  - `w["winners"]` (≥2 konv + matcher INTET eksisterende keyword på nogen match type) er
    **garanteret** på "Nye keywords"-fanen. `w["skipped"]` (≥2 konv men allerede dækket) går på
    "Sprunget over"-fanen MED det dækkende keyword — så intet forsvinder usynligt.
  - `neg` er ALLE 0-konv ≥50 DKK-termer; scriptet foreslår en `band` (GROEN/GUL/ROED) ud fra
    offering-token-overlap. **Agentens rolle:** op/nedgradér `band` med den rigere sprog-vurdering
    (`wikipedia` = info-søgning → GROEN; et reelt produkt → ROED) og LOG ændringen i
    `band_adjustment` (`script: GUL -> agent: GROEN (grund: ...)`). Tilføj `level` + en dansk
    `reason` per negativ. Tilføj aldrig/fjern aldrig en kandidat — kun juster band + begrundelse.
  - **Agentens øvrige rolle:** tildel hver overview-term en `bucket` (VINDER / RELEVANT /
    PLACEMENT_PROBLEM / IRRELEVANT / GRÆNSE) mod `lib/classify/taxonomy.md`, forankret i det
    scrapede tilbud (offering). Sæt `low_confidence=true` hvis konto-konverteringer < 10.
  Returnér `winners`, `negatives`, `all_terms` (m. bucket), `skipped_winners`, `active_campaigns`,
  `low_confidence` — præcis de felter `review_workbook.build()` læser.
- **Asset-hygiejne-agent** → `AssetHygieneFindings`. GAQL: `lib/gaql/asset_view.py`
  (`asset_view_query`, `rsa_count_query`). Kun struktur: RSA-count per ad group (<2 →
  challenger-flag), dødvægt, vinkel-gap-brief. ALDRIG CVR-dom.
- **QS-agent** → `QualityScoreFindings`. Kald `get_quality_score_audit(date_range=...)` (brug
  `lib/gaql/quality_score.date_range_arg()` — `LAST_90_DAYS` virker IKKE her), normalisér via
  `normalise_findings()`. Keyword-grain; LP = flag, ikke score.

## Trin 3 — Saml + byg workbooken

Saml de tre fund + `active_campaigns` (de aktive kampagnenavne fra diagnoserne) til ét findings-
objekt og byg workbooken:

```bash
python3 ${CLAUDE_SKILL_DIR}/lib/review_workbook.py --in <findings.json> \
  --out "Optimering - <klient> - <YYYY-MM-DD>.xlsx"
```

Findings-objektet (se docstring i `review_workbook.py` for det fulde skema):
- `negatives`: fra `sweep.sweep_negatives` (m. agent-justeret `band`, `band_adjustment`, `level`,
  `reason`). Niveau pr. term; konto-niveau udfoldes af builderen til per-kampagne-rækker — derfor
  SKAL `active_campaigns` med.
- `winners`: `sweep.sweep_winners(...)["winners"]` (builderen promoverer til `Exact`, `Paused`).
- `skipped_winners`: `...["skipped"]` — ≥2-konv-termer der allerede er dækket (→ "Sprunget over").
- `all_terms`: `sweep.all_terms_overview(...)` m. agent-tildelt `bucket` per term (→ overview-fanen).
- `rsa_rows`: for hver ad group med `challenger_flag` eller vinkel-hul, ÉN **ny** challenger
  (headlines ≤15, descriptions ≤4, paths[2], final_url), forankret i `references/headline-craft.md`
  + asset-hygiejnens gap-brief. RESPEKTÉR Editor-grænserne (headline ≤30, description ≤90, path
  ≤15) — drop/trim for-lange linjer. Status altid `Paused`. ALDRIG en in-place edit.

Workbooken har **6 faner:** **Laes mig**, **Negative keywords** (Konfidens-farvet 🟢/🟡/🔴 +
`Tynd data`-flag), **Nye keywords (vindere)**, **RSA challengers**, **Sprunget over** (de dækkede
≥2-konv-termer + det dækkende keyword), **Alle søgetermer** (FULDT overblik over alle ≥5 DKK,
farvet efter `Gruppe`/bucket). To farve-akser, bevidst forskellige: overview farver efter
KLASSIFIKATION (bucket), negatives-fanen efter KONFIDENS (hvor trygt at blokere).

**To faner bliver ALDRIG til CSV:** `Alle søgetermer` + `Sprunget over` matcher ingen
`editor-csv-export`-alias → konverteren læser dem aldrig. Det er garantien for "kun overblik".
Mørkeblå kolonner på de andre faner = Editor-felter (konverteren beholder); lyseblå = metadata
(droppes, inkl. Konfidens/Klik/Tynd data).

## Trin 4 — Aflever + næste skridt

1. **Gem** workbooken (Drive = ekstern write → bekræft først; lokalt = ingen gate).
2. **Kort dansk opsummering:** N negatives (X DKK spild), M vindere at promovere, K ad groups uden
   challenger, QS-flag. Ærlige forbehold: `low_confidence` hvis sat; QS-LP = flag, ikke score;
   konto-niveau negatives er udfoldet (se Laes mig).
3. **Sådan bruger eksperten filen:** ret frit i workbooken → kør `editor-csv-export` (workbook →
   Editor-CSV) → importér CSV'erne i Editor (Account → Import → From file) → gennemgå grøn/gul diff
   → Send. Intet er skrevet til kontoen af dette skill.
4. **`## Kilder`** — de MCP-værktøjer + evt. URLs der faktisk blev læst.

## Hård sandheds-grænse

- **Skriv aldrig til kontoen.** Ingen mutate, intet API-push. Kun en workbook.
- **Overclaim ikke det lukkede loop.** Dette er v1 (diagnose → workbook); measure-fasen ("siden
  sidst") er v2 og kræver en run-persistens-beslutning. Sig "diagnose-loop", ikke "fuldt loop".
- **Significance-floors er ikke til forhandling** — ≥2 konv. for en vinder, `low_confidence` under
  10, ingen per-asset CVR-dom.

## Maintenance

- De deterministiske dele bor i `lib/` (medfølger skillet — Cowork-plugins er self-contained):
  `lib/gaql/*` (query-strenge + normalisering), `lib/sweep.py` (den deterministiske kandidat-sweep
  — vinder/negative/overview), `lib/review_workbook.py` (bygger .xlsx), `lib/classify/taxonomy.md`.
  Selektions-designet (hvorfor scriptet ejer "intet glemmes", konfidens-banderne, de to farve-akser,
  CSV-isoleringen) står i `references/selection-spec.md` — læs den før du ændrer sweep- eller
  workbook-logik.
- **Navne-gotcha:** modulet hedder `sweep.py`, IKKE `select.py` — `select` skygger Pythons stdlib
  `select` som `subprocess` (i review_workbook) afhænger af → import-crash hvis de deler proces.
- `lib/*` er **kopier** harmoniseret med `editor-csv-export`-kontrakten (negatives taler samme
  tab-04-vokabular; de nye kolonner — Konfidens/Klik/Tynd data/Agent-note — er alle metadata som
  konverteren dropper; `Alle søgetermer` + `Sprunget over` er alias-usynlige). Retter du
  workbook-kolonnerne, så opdatér også `editor-csv-export`-kontrakten — de er tæt koblede.
- Den lokale dev-harness (`workflows/optimization-loop/`, en Claude Code Workflow) var prototypen;
  DETTE skill er nu den kanoniske vej. Vedligehold ikke begge — workflow'en er kasserbar.
