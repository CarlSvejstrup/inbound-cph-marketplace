---
name: inb-ads-optimization-loop
description: Kører det samlede optimerings-loop på en live Google Ads-konto ved at diagnosticere søgetermer og negatives, RSA-asset-hygiejne og Quality Score parallelt og samle alt i én redigerbar Excel-workbook, uden nogensinde at skrive til kontoen selv.
---

# inb-ads-optimization-loop

Det samlede optimerings-loop for en live Google Ads-konto: én kommando diagnosticerer kontoen på
flere dimensioner og afleverer ÉN redigerbar Excel-workbook med konkrete forslag — negatives,
vinder-keywords at promovere, RSA-challengers. Eksperten retter workbooken, kan sende den til
kunden, og importerer den derefter manuelt i Google Ads Editor. Alt output er på dansk.

Dette er operate-laget (modsat `inb-ads-campaign-build`). Hvor `inb-ads-search-term-analyse` og
`inb-ads-rsa-hygiene` hver gør ÉN diagnose, kører dette skill dem sammen + Quality Score og samler
alt i den ene workbook, så eksperten ikke skal stykke tre regneark sammen i hånden.

Dette er **v1: diagnose → workbook**, ikke det fulde lukkede loop. En v2 measure-fase ("siden
sidst: hvad foreslog vi, hvad blev anvendt, flyttede det metrikken") kræver en run-persistens-model
(hvor gemmes en kørsels `recommendations.json` så næste kørsel kan sammenligne) — en separat
designbeslutning, ikke bygget endnu. Kald det "diagnose-loopet" over for brugeren, ikke "det fulde
loop".

## Arkitektur

En læse-skill der kører i main-loopet. De deterministiske dele bor i `lib/` (medfølger skillet):
`lib/gaql/*` bygger GAQL-strenge + normaliserer resultater; `lib/sweep.py` er den deterministiske
kandidat-sweep; `lib/review_workbook.py` bygger den ene `.xlsx`; `lib/classify/taxonomy.md` er den
delte klassifikations-taksonomi. MCP-kaldene og klassifikationen laver agenten (main-loop +
sub-agenter), ikke Python'en.

Kører på enhver maskine — eneste forudsætning er Python 3 + `pip` (review_workbook
self-bootstrapper openpyxl) og Google Ads MCP. Ingen `gws`, ingen Sheets-API.

## Trin 0 — Hent klient-kontekst (AI Context) FØRST

Før al anden handling: hent klientens AI Context-fil ind i konteksten. Det er en læsning (ikke
gatet), men obligatorisk — sådan arver du ID'er, kontakter, hårde rammer, navngivningskonvention,
budstrategi-norm, KPI'er og pausede-kampagners-intention i stedet for at starte blindt. Dette skill
orkestrerer sub-diagnoser (offering-brief + tre diagnose-sub-agenter): hent AI Context ÉN gang her
øverst — sub-agenterne arver den via deres prompt og skal ikke slå op igen.

1. **Identificér klienten.** Uklart hvilken klient → spørg før du fortsætter.
2. **Åbn master-klientindekset i Drive** via Drive-connectoren: `search_files` efter Google Doc'en
   `Inbound CPH — Google Ads klient-index (AI Context)` (id `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`,
   i "A - Kunder"-mappen). Læs den med `read_file_content`. Den mapper hver klient til Google Ads
   ID, HubSpot ID, ClickUp-mappe, Stage, Drive-mappe og AI Context-fil.
3. **Find klientens række** (match på navn/domæne/Ads-ID). Notér Stage (customer / lead /
   opportunity / "ikke tagget") — en ikke-`customer`-stage betyder en ikke-lukket konto; vægt
   anbefalinger derefter og antag aldrig en aktiv retainer. Delte mapper (Lime, Retriever/Infomedia,
   GSGroup, Nemco, Julemærket, PhoneAlone, DI) → vælg rækken for det specifikke marked/konto.
4. **Åbn klientens AI Context-`.md`** via Drive-linket i indeksrækken (`read_file_content`). Den
   indeholder driftsbriefen: ID'er, kontakter, hårde rammer, mål/KPI'er, navngivningskonvention,
   sådan-kører-vi-den, plus link til changelog/optimeringslog (læs den også hvis opgaven kræver
   ændringshistorik).
5. Først derefter starter det egentlige arbejde (Trin 0.5 og frem), med AI Context som ground truth
   for klient-fakta.

Ingen række i indekset eller ingen AI Context-fil endnu: sig det, fortsæt med det du kan samle
(Drive-mappe, Ads MCP), og flag hullet. Spring aldrig opslaget stille over.

## Trin 0.5 — Kontekst

Læs `references/headline-craft.md` (RSA-challenger-vinkler + tiebreakers; brug som variation, ikke
hårde <20-tegns-lofter; behold "ignorér Ad Strength"-holdningen). Klassifikations-reglerne står i
`lib/classify/taxonomy.md`.

Svar på dansk gennemgående — intake, statusbeskeder, workbook, næste-skridt. Skift kun til engelsk
hvis brugeren skriver engelsk.

Forudsætning: Google Ads MCP + et `customer_id`. Ikke tilgængelig → sig det og stop.

## Trin 1 — Intake (ét `AskUserQuestion`-kald)

Udled så meget som muligt fra samtalen først. Saml resten i ét kald:

1. **Klient + `customer_id`** — bekræft hvis nævnt; ellers `list_accessible_accounts` → find id'et
   → bekræft.
2. **Analysevindue** — default sidste 90 dage (mere data → færre under-signifikans-tilfælde). Vis
   `Sidste 90 dage (Anbefalet)`, `Sidste 30 dage`, `Andet`. `LAST_90_DAYS` er IKKE et gyldigt
   GAQL-literal — for 90 dage / >30 dage beregn `BETWEEN '<YYYY-MM-DD>' AND '<YYYY-MM-DD>'`.
   `lib/gaql/window_clause()` (søgetermer/asset) og `lib/gaql/quality_score.date_range_arg()` (QS)
   håndterer begge dette; brug dem, gæt aldrig literalet.
3. **Gem-destination** — `Drive (klientens mappe)`, `Lokalt (.xlsx)`, eller begge. Drive er en
   ekstern write → bekræft én gang før gem.

## Trin 1.5 — Phase 0: byg virksomhedsprofilen først

Klassifikation er meningsløs uden at vide hvad klienten faktisk sælger — taksonomien definerer
IRRELEVANT som "passer ikke klientens tilbud". Én offering-brief-sub-agent kører derfor først og
bygger grundsandheden, der fodres ind i alle tre diagnoser. Fuldt skema i
`references/offering-brief.md`; kort version:

1. **Hent landingsside-URL'erne** — kør `ad_group_ads_query` (eller `list_accessible_accounts` + en
   hurtig kampagne-pull) for ad-gruppernes `final_urls`, og scrap dem (Firecrawl,
   `firecrawl-scrape` / connector) for hvad klienten sælger + til hvem.
2. **Udled fra konto-signaler** — kampagne-/ad-group-navne + eksisterende RSA-headlines (hvad de
   allerede annoncerer). Krydstjek mod landingssiden; notér uoverensstemmelser.
3. **Skriv `offering.md`** til run-mappen efter skemaet i `references/offering-brief.md`: hvad de
   sælger, hvem, geografi/sprog, brand-varianter, ikke-en-del-af-tilbuddet (out-of-scope), og en
   maskinlæsbar `OFFERING_TOKENS:`-linje (offering-vokabularet, ikke out-of-scope-ord).

Scrape fejler/er tynd (JS-side, login) → fald tilbage til kun konto-signaler og skriv det i
`offering.md`s `Kilde`-linje. Fabrikér aldrig et tilbud.

`offering.md` er intern kontekst (ikke en workbook-fane), bygget frisk hver kørsel. Dens fulde
tekst gives ind i hver af de tre diagnose-sub-agenters prompt nedenfor.

## Trin 2 — Kør de tre diagnoser (én sub-agent hver, parallelt)

Spawn én sub-agent per diagnose — kontekst-isolation: rå GAQL-svar fylder ikke main-loopet, hver
sub-agent returnerer kun struktureret JSON. De tre er uafhængige — kør dem parallelt.

Deleger konto-læsningen til `ads-analyst`-agenten (Task-værktøjet). Alle tre diagnoser er rene
konto-læsninger, og `ads-analyst` er den genbrugelige read-worker: dispatch hver diagnose til
`ads-analyst` via Task, giv den `customer_id`, vinduet, `lib/`-stien og hele `offering.md` som
kontekst, og lad den køre GAQL-pullet + klassifikationen og returnere den strukturerede JSON.
`ads-analyst` skriver aldrig til kontoen. (Kører du sub-agenterne som generiske Task-agenter i
stedet, gælder samme kontrakt — `ads-analyst` er blot den navngivne, genbrugelige indpakning.)

Fremadrettet, endnu ikke aktivt: når det samtale-drevne re-spec med direkte HITL-gatede writes
lander (backlog), routes bekræftede konto-writes gennem `ads-writer`-agenten, som håndhæver
per-action-bekræftelse + budget-guardrailen. I dag skriver dette skill aldrig til kontoen — det
leverer stadig kun diagnose → workbook.

Hver sub-agent får: `customer_id`, vinduet, stien til dette skills `lib/`, hele `offering.md` som
kontekst (Phase 0-grundsandheden — den gør relevans-kald rigtige), og besked om at (a) hente
GAQL-strengen fra det rette `lib/gaql`-modul, (b) køre den via `run_custom_gaql` (kun ENABLED
kampagner — pausede ekskluderes bevidst og flages aldrig som negativt fund), (c) post-processe via
modulets normaliser, (d) returnere JSON.

- **Søgeterm-agent** → `SearchTermFindings`. GAQL: `lib/gaql/search_terms.py`
  (`search_terms_query`, `keyword_map_query`, `ad_group_ads_query`, `account_search_cost_query`).
  Kør først det deterministiske sweep — agenten må aldrig selv finde/tabe kandidater (det er
  rygraden, se `references/selection-spec.md`).

  **Token-loft på de tunge pulls:** `search_terms_query`, `keyword_map_query` og ad-dumpet
  returnerer for meget til at læse ind i konteksten (keyword-map'en alene var 1,7 MB / ~2500 rækker
  på DSC). Skriv hvert svar til en fil og processér fil-side (python/jq) — læs aldrig rå-rækkerne
  ind i agentens kontekst. `sweep` kører på de fil-indlæste rækker (keyword-map'en kan ikke
  snævres på rækker, da `sweep` skal bruge hele det aktive keyword-sæt til
  set-membership-tjekket — men den læses fil-side, aldrig i konteksten).

  ```python
  import sweep   # lib/sweep.py — IKKE 'select' (det skygger Pythons stdlib)
  offering_tokens = sweep.parse_offering_tokens(open("offering.md").read())  # fra Phase 0
  w   = sweep.sweep_winners(search_term_rows, keyword_map_rows, offering_tokens)  # {winners, review_winners, skipped}
  neg = sweep.sweep_negatives(search_term_rows, offering_tokens)  # [{band, thin_data, ...}]
  ov  = sweep.all_terms_overview(search_term_rows)                # alle >=5 DKK termer
  ```

  `offering_tokens` kommer fra `offering.md` (ikke håndholdt) — det forankrer både negative-bånd og
  vinder-udvælgelsen i det faktiske tilbud. Tom liste (scrape fejlede) → alle negative foreslås
  GUL, og alle vindere bliver promoverbare (kan ikke hævde off-offering uden et tilbud at måle mod).

  **Vindere er offering-grounded.** En konvertering på en lead-gen-konto er et lead, ikke bevis for
  at søge-intentionen matchede tilbuddet (folk lander og tilmelder sig noget andet). `sweep_winners`
  tjekker derfor hver ≥2-konv-kandidat mod offering-vokabularet:
  - `w["winners"]` (on-offering) → garanteret på "Nye keywords"-fanen (promoverbar).
  - `w["review_winners"]` (off-offering: har content-ord, rammer ikke tilbuddet) → fanen "Vindere
    til gennemgang" — synliggjort + flagget, aldrig auto-promoveret. Sådan kan en off-offering-
    destination (fx `zanzibar rejse`) aldrig usynligt blive et nyt keyword. Eksperten flytter en
    bekræftet over i hånden — flagget, ikke gatet, så intet kvalificerende tabes.
  - `w["skipped"]` (≥2 konv men allerede dækket) → "Sprunget over"-fanen med det dækkende keyword.

  `neg` er alle 0-konv ≥50 DKK-termer; scriptet foreslår en `band` (GROEN/GUL/ROED) ud fra
  offering-token-overlap (fler-ords-match + stopords-filter, så `new zealand` matcher som enhed og
  `rejse`/`unge` ikke støjer). Agentens rolle: op/nedgradér `band` med den rigere sprog-vurdering
  (`wikipedia` = info-søgning → GROEN; et reelt produkt → ROED) og log ændringen i
  `band_adjustment` (`script: GUL -> agent: GROEN (grund: ...)`). Tilføj `level` + en dansk `reason`
  per negativ. Tilføj eller fjern aldrig en kandidat — kun justér band + begrundelse.

  Agentens øvrige rolle: tildel hver overview-term en `bucket` (VINDER / RELEVANT /
  PLACEMENT_PROBLEM / IRRELEVANT / GRÆNSE) mod `lib/classify/taxonomy.md`, forankret i
  `offering.md` (inkl. out-of-scope-listen — en term der rammer den → konfident
  IRRELEVANT/GROEN). Sæt `low_confidence=true` hvis konto-konverteringer < 10.

  **Afstem vindere med buckets — obligatorisk, det er det der fanger `zanzibar højskole`.**
  Scriptets token-split er grov: en term der deler ét offering-ord (`zanzibar højskole` deler
  `højskole`) scorer PARTIAL og bliver en promoverbar vinder, fordi scriptet ikke kan se at
  destinationen er off-offering. Det er din bucket-vurdering der fanger det. Efter du har tildelt
  buckets, kør altid, før Trin 3:
  ```python
  bucket_by_term = { t["term"]: t["bucket"] for t in all_terms }   # din klassifikation
  w = sweep.reconcile_winners_with_buckets(w, bucket_by_term)       # demoterer IRRELEVANT/PLACEMENT-vindere
  ```
  Det flytter enhver vinder du buckede IRRELEVANT (off-offering) eller PLACEMENT_PROBLEM (forkert
  ad group) fra `winners` til `review_winners` med begrundelse — så ingen term kan stå som
  *promovér* på "Nye keywords" og som IRRELEVANT på "Alle søgetermer" i samme workbook.

  Returnér `w["winners"]`, `w["review_winners"]` (efter reconcile), `negatives`, `all_terms` (m.
  bucket), `skipped_winners`, `active_campaigns`, `low_confidence` — præcis de felter
  `review_workbook.build()` læser.

- **Asset-hygiejne-agent** → `AssetHygieneFindings`. GAQL: `lib/gaql/asset_view.py`
  (`asset_view_query`, `rsa_count_query`, `search_ad_groups_query`). Kun struktur: RSA-count per ad
  group (<2 → challenger-flag), dødvægt, vinkel-gap-brief. Aldrig CVR-dom.

  <2-RSA-flaget gælder kun SEARCH. `rsa_count_query` + `search_ad_groups_query` er begge scopet til
  `advertising_channel_type = 'SEARCH'`. Beregn manglende-RSA som `search_ad_groups_query`-sættet
  minus de ad groups `rsa_count_query` dækker med ≥2 RSA'er. Display/Video-målgruppe-ad-groups
  ("Combined segment", "Alle målgrupper") har 0 RSA som normal-tilstand — uden SEARCH-scopet ville
  de fejlagtigt se ud som challenger-kandidater (live-fund på DSC), og loopet ville generere RSA'er
  til ad groups hvor RSA ikke giver mening.

- **QS-agent** → `QualityScoreFindings`. Kald `get_quality_score_audit(date_range=...)` (brug
  `lib/gaql/quality_score.date_range_arg()` — `LAST_90_DAYS` virker ikke her), normalisér via
  `normalise_findings()`. Keyword-grain; landingsside er et flag, ikke en score. Returnér
  `quality_score` = `{average, total_keywords, worst:[...]}` (den verificerede `worst_keywords`-
  form) → bygger "Quality Score"-fanen (QS-cellen + komponent-labels farves, så en klynge af QS 1-2
  + BELOW_AVERAGE-landingsside springer i øjnene).

## Trin 3 — Saml + byg workbooken

Saml de tre fund + `active_campaigns` (de aktive kampagnenavne fra diagnoserne) til ét
findings-objekt og byg workbooken:

```bash
python3 ${CLAUDE_SKILL_DIR}/lib/review_workbook.py --in <findings.json> \
  --out "Optimering - <klient> - <YYYY-MM-DD>.xlsx"
```

Findings-objektet (fuldt skema i docstring i `review_workbook.py`):
- `negatives`: fra `sweep.sweep_negatives` (m. agent-justeret `band`, `band_adjustment`, `level`,
  `reason`). Niveau pr. term; konto-niveau udfoldes af builderen til per-kampagne-rækker — derfor
  skal `active_campaigns` med.
- `winners`: `sweep.sweep_winners(...)["winners"]` — on-offering vindere (builderen promoverer til
  `Exact`, `Paused`).
- `review_winners`: `...["review_winners"]` — off-offering ≥2-konv-termer (→ "Vindere til
  gennemgang"-fanen; aldrig auto-promoveret, eksperten flytter en bekræftet over).
- `skipped_winners`: `...["skipped"]` — ≥2-konv-termer der allerede er dækket (→ "Sprunget over").
- `all_terms`: `sweep.all_terms_overview(...)` m. agent-tildelt `bucket` per term (→
  overview-fanen).
- `quality_score`: `{average, total_keywords, worst:[...]}` fra QS-agenten (→
  "Quality Score"-fanen).
- `rsa_rows`: for hver SEARCH-ad-group med `challenger_flag` eller vinkel-hul, én ny challenger
  (headlines ≤15, descriptions ≤4, paths[2], final_url), forankret i `references/headline-craft.md`
  + asset-hygiejnens gap-brief. Respektér Editor-grænserne (headline ≤30, description ≤90, path
  ≤15) — drop/trim for-lange linjer. Status altid `Paused`, aldrig en in-place edit (det nulstiller
  RSA'ens læring — Beslutning 2026-06-09).

Workbooken har op til 8 faner: **Læs mig**, **Negative keywords** (konfidens-farvet 🟢/🟡/🔴 +
`Tynd data`-flag), **Nye keywords (vindere)**, **Vindere til gennemgang** (off-offering
konverterende termer — flagget, ikke auto-promoveret), **RSA challengers**, **Sprunget over** (de
dækkede ≥2-konv-termer + det dækkende keyword), **Alle søgetermer** (fuldt overblik over alle
≥5 DKK, farvet efter Gruppe/bucket), **Quality Score** (flaggede keywords, QS + komponent-labels
farvet). To farve-akser, bevidst forskellige: overview farver efter klassifikation (bucket),
negatives-fanen efter konfidens (hvor trygt at blokere). "Vindere til gennemgang" og
"Quality Score" vises kun når der er noget at vise.

Hver fane bærer den samme metrik-blok: `Budget brugt (DKK)` / `Impressions` / `Klik` / `CTR (%)` /
`Konverteringer` / `CPA (DKK)` — negatives-fanen kalder cost-kolonnen `Spildt budget (DKK)`. CTR og
CPA beregnes i builderen (`_metric_block`), så de er ens på tværs uden at skulle vedligeholdes per
fane. Farve-koderne (begge akser) forklares med farve-blokke på "Læs mig".

**Fire faner er rene referencefaner:** `Alle søgetermer`, `Sprunget over`, `Vindere til gennemgang`
og `Quality Score` er navngivet uden for Editors kolonne-vokabular, så en ekspert der importerer
fra workbooken ved de aldrig skal med — garantien for "kun overblik / kun gennemgang". Mørkeblå
kolonner (yderst til venstre) på de andre faner er Editor-felter (tages med ved import); lyseblå er
metadata (springes over, inkl. hele metrik-blokken + Konfidens/Tynd data).

## Trin 4 — Aflever + næste skridt

1. **Gem** workbooken. Lokalt-først er default (ingen gate): skriv `.xlsx` til disk. Drive er
   best-effort: workbooken kan uploades via Drive-connectorens `create_file` med `base64Content`
   (samme sti som `inb-ads-rsa-copy`) — men en stor multi-fane-workbook (~50 KB → ~65 KB base64) kan
   være for tung at relæe inline, så tilbyd Drive, og fald ved fejl/for stor tilbage til den lokale
   fil med en besked. Drive er ekstern write → bekræft først.
2. **Kort dansk opsummering:** N negatives (X DKK spild), M vindere at promovere, K ad groups uden
   challenger, QS-flag. Ærlige forbehold: `low_confidence` hvis sat; QS-LP er et flag, ikke en
   score; konto-niveau negatives er udfoldet (se Læs mig).
3. **Sådan bruger eksperten filen:** ret frit i workbooken → gem de relevante faner som CSV (eller
   indtast rækkerne direkte) → importér i Editor (Account → Import → From file) → gennemgå
   grøn/gul diff → Send. Intet er skrevet til kontoen af dette skill.
4. **`## Kilder`** — de MCP-værktøjer + evt. URLs der faktisk blev læst.

## Hårde regler

- **Skriv aldrig til kontoen.** Ingen mutate, intet API-push. Kun en workbook.
- **Overclaim ikke det lukkede loop.** Dette er v1 (diagnose → workbook); measure-fasen er v2 og
  kræver en run-persistens-beslutning. Sig "diagnose-loop", ikke "fuldt loop".
- **Significance-floors:** en vinder kræver ≥2 konverteringer; under 10 konverteringer på kontoen
  sættes `low_confidence`; RSA-asset-hygiejne dømmer aldrig en asset på CVR, kun struktur (dækning,
  dødvægt, vinkel-huller). En live-test (2026-05-29) viste per-asset CTR/CVR konfunderet og
  konverteringer på 0/1/2 under signifikans — alt der hævder mere end data kan bære, er en fejl.
- **En konvertering er et lead, ikke intentions-bevis.** På en lead-gen-konto validerer en
  konvertering volumen/signifikans, men ikke at søge-intentionen matchede tilbuddet. Derfor er
  vinder-udvælgelsen offering-grounded: ≥2 konv. + off-offering → "Vindere til gennemgang", ikke
  auto-promoveret. Significance-disciplinen dækker volumen; offering-grounding dækker
  attributions-validitet — to forskellige ting.
- **Konto-niveau negatives udfoldes.** Editor CSV har kun kampagne- og ad-group-niveau. Et fund på
  konto-niveau udfoldes til én `Campaign negative`-række per aktiv kampagne (samme
  blokeringseffekt, fuldt importérbart) + en note på "Læs mig"-fanen om delt-liste-alternativet.
- **Tidszone:** kontoens tidszone styrer dato-vinduet, og en dansk konto kan stå i fx
  America/Los_Angeles. Et 90-dages-vindue er derfor en anelse tidszone-følsomt i kanterne — nævn
  det hvis et tal ser ud til at ligge lige på en dag-grænse; jagt ikke en perfekt match.

## Maintenance

De deterministiske dele bor i `lib/` (medfølger skillet — Cowork-plugins er self-contained):
`lib/gaql/*` (query-strenge + normalisering), `lib/sweep.py` (den deterministiske kandidat-sweep —
vinder/negative/overview), `lib/review_workbook.py` (bygger .xlsx), `lib/classify/taxonomy.md`.
Selektions-designet (hvorfor scriptet ejer "intet glemmes", konfidens-banderne, de to farve-akser,
CSV-isoleringen) står i `references/selection-spec.md`; Phase 0-grundsandheden (offering-brief,
kilder, `offering.md`-skema, token-kontrakten) i `references/offering-brief.md` — læs dem før du
ændrer sweep-, offering- eller workbook-logik.

Navne-gotcha: modulet hedder `sweep.py`, ikke `select.py` — `select` skygger Pythons stdlib
`select`, som `subprocess` (i review_workbook) afhænger af, hvilket giver import-crash hvis de
deler proces.

`lib/*` er kopier harmoniseret med Editors bulk-import-vokabular (negatives taler samme
tab-04-vokabular; de nye kolonner — Konfidens/Klik/Tynd data/Agent-note — er alle metadata en
manuel import springer over; `Alle søgetermer` + `Sprunget over` er rene referencefaner, aldrig
importeret). Retter du workbook-kolonnerne, hold dem konsistente med `inb-ads-search-term-analyse`s
Editor-CSV-kontrakt (`lib/write_csv.py`) — de deler samme kolonne-vokabular.
