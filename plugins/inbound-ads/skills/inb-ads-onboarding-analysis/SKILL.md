---
name: inb-ads-onboarding-analysis
description: Kører Inbounds 35-punkts Analysearbejdet-tjekliste mod en ny Google Ads-kundes konto og afleverer en .docx opstartsrapport i kundens Drive-mappe, udelukkende read-only via Google Ads MCP uden nogensinde at skrive til kontoen selv. Brug til den indledende struktur- og hygiejnegennemgang af en netop overdraget konto, ikke løbende performance-audit eller optimering.
---

# inb-ads-onboarding-analysis

Gå **Analysearbejdet (Search)** igennem for en ny Google Ads-kunde og aflever en `.docx`
opstartsrapport i kundens Drive-mappe. Dette er **onboarding-lagets** analyse-skill: en
struktur- og hygiejne-gennemgang af en netop overdraget konto, ikke en performance-audit
(det er `inb-ads-account-audit`) og ikke en dyb enkelt-dimensions optimering af en kørende
konto (det er `inb-ads-search-term-analyse` / `inb-ads-rsa-hygiene` / `inb-ads-quality-score`).

Read-only mod kontoen, altid — ingen mutate, intet API-push. Den eneste eksterne write er
.docx'en til Drive, gated bag eksplicit bekræftelse. Dommen er struktur/hygiejne, ikke
performance: på opstart er der ofte ingen historik, så døm aldrig et fund på CTR/CVR — hvor
data mangler er svaret `Mangler data (ny konto)`, ikke et fabrikeret fund. Pausede kampagner
er bevidste og flages aldrig som negativt. De 35 punkter, deres MCP-verifikationsvej og
doms-reglerne bor ordret i `references/analysearbejdet.md` — én kilde, juster punkter der uden
at røre orkestreringen. Kundemappen ejes af et separat make-workflow: findes den ikke, stop og
spørg, opret den aldrig selv.

Hele forløbet og alt output er på **dansk**.

## Forudsætninger

- **Google Ads MCP** (read-only). Ikke tilgængelig → sig det og stop.
- **Drive-connector** (Cowork's indbyggede) til den afsluttende .docx-upload.
- **Python 3 + pip** — `lib/build_docx.py` self-bootstrapper `python-docx`.
- Vault `clients/*.md` for `drive_folder` + `google_ads_id` (slå op, gæt aldrig).

## Trin 0 — Hent klient-kontekst (AI Context) først

1. **Identificér klienten.** Uklart → spørg hvilken klient før du fortsætter.
2. **Åbn master-klientindekset i Drive** via Drive-connectoren: `search_files` efter Google Doc'en
   `Inbound CPH — Google Ads klient-index (AI Context)` (id
   `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`, i "A - Kunder"). Læs med `read_file_content`.
   Den mapper hver klient til Google Ads ID, HubSpot ID, ClickUp-mappe, Stage, Drive-mappe og
   AI Context-fil.
3. **Find klientens række** (match på navn/domæne/Ads-ID). For delte mapper (Lime,
   Retriever/Infomedia, GSGroup, Nemco, Julemærket, PhoneAlone, DI) vælg rækken for det
   specifikke marked/konto.
4. **Findes AI Context-filen, hent den** via Drive-linket (`read_file_content`): ID'er,
   kontakter, hårde rammer, mål/KPI'er, navngivningskonvention, sådan-kører-vi-den, og link til
   changelog (læs også det hvis opgaven kræver ændringshistorik).
5. **Findes ingen række eller AI Context-fil, er det forventet for en ny kunde** — fortsæt og
   flag det tydeligt ("[klient] har ingen AI Context-fil endnu — forventet for en ny kunde; jeg
   kører på det jeg kan samle fra Drive-mappen + Ads MCP"). Spring aldrig opslaget stille over.
6. Herefter starter det egentlige arbejde, med AI Context som ground truth hvor den findes.

**Sprog:** alt på dansk — intake, statusbeskeder, .docx, næste skridt. Skift kun til engelsk hvis
brugeren skriver engelsk. **Læs `references/analysearbejdet.md`** — det er tjeklistens fulde
tekst + verifikationsveje + doms-regler. Du orkestrerer herfra.

## Trin 1 — Intake (ét `AskUserQuestion`-kald)

Udled så meget som muligt fra samtalen først, saml resten i ét kald:

1. **Klient + `customer_id`** — bekræft hvis nævnt. Ellers: slå klienten op i vault
   `clients/*.md` (kebab-case filnavn, fx `dantaxi4x48-com.md`) og læs `google_ads_id` fra
   frontmatter. Kan du ikke matche: kør `list_accessible_accounts`, find bedste navne-match,
   bekræft. Sidste udvej: bed om ID manuelt.
2. **Analysegrundlag** — default **Struktur-gennemgang** (ren opsætnings-/hygiejne-tjek, virker
   uden historik). Tilbyd også `Med 90-dages data hvor det findes`. Til Quality Score bruges
   altid `LAST_90_DAYS` (kun gyldigt i `get_quality_score_audit(date_range=...)`, IKKE som GAQL
   `WHERE`-literal — brug der `BETWEEN '<YYYY-MM-DD>' AND '<YYYY-MM-DD>'`).
3. **Gem-destination** — default kundens Drive-mappe (slå `drive_folder` op i klient-noten).
   Tilbyd også `Kun lokalt (.docx)`. Drive = ekstern write → bekræft én gang før upload.

**Mappe-tjek:** når Drive er valgt, verificér at kundemappen findes (`search_files` på
`drive_folder` eller klientnavnet under root-mappen). Findes den ikke: stop og spørg —
"Kundemappen for [klient] findes ikke i Drive endnu. Skal make-workflowet (mappe-opsætning) køre
først, eller vil du give mig mappe-ID'et manuelt? Jeg opretter den ikke selv." Opret aldrig
mappen selv.

**ClickUp-tjek (flag, men fortsæt — modsat Drive):** hvis ClickUp-MCP er tilgængelig, slå op om
kunden er oprettet (`clickup_search` på klientnavnet i Kundespace, eller en "Opstartscheckliste:
Analysearbejdet (Search)"-task i kundens folder). Findes kunden ikke: flag det ("⚠️ [klient] er
ikke oprettet i ClickUp endnu — opret kunden via skabelonen når du får tid") men kør analysen
alligevel og aflevér .docx'en. En manglende Drive-mappe blokerer (intet sted at gemme); en
manglende ClickUp-kunde gør ikke (det er kun et sted at krydse af bagefter). Skillet skriver
aldrig til ClickUp i v1 — ren read/flag. (ClickUp-struktur: se project-noten
`research/clickup-onboarding-mcp-capability.md`.)

## Trin 2 — Phase 0: byg virksomhedsprofilen (én sub-agent, før verifikationen)

Flere tjekpunkter er kun meningsfulde mod hvad klienten faktisk sælger — annoncetekst-relevans
(punkt 13-14), keyword-dækning (28), geo/sprog-korrekthed (21), brand-ekskludering (29). Én kort
offering-sub-agent kører først og bygger grundsandheden:

1. Hent landingsside-URL'erne (RSA `final_urls` via en hurtig `ad_group_ad`-pull) og scrap dem
   (Firecrawl / connector) for hvad de sælger + til hvem + marked/sprog + brand-varianter.
2. Udled fra konto-signaler — kampagne-/ad-group-navne + eksisterende RSA-headlines.
3. Returnér en kompakt dansk profil: hvad de sælger, hvem, geografi/sprog, brand-varianter, og
   hvad der IKKE er en del af tilbuddet. Fejler scrape/for tyndt: brug kun konto-signaler og sig
   det — fabrikér aldrig et tilbud.

Profilen gives ind i de verifikations-sub-agenter nedenfor der har brug for den (modul C,
E-geo, G). De rent strukturelle moduler (A extensions, B adgang, D tracking-config, F struktur,
H bidding-type, I lister) behøver den ikke.

## Trin 3 — Verificér de 9 moduler (sub-agenter, parallelt)

De ni modulgrupper i `references/analysearbejdet.md` (A-I) er uafhængige — kør dem parallelt som
sub-agenter for kontekst-isolation (rå GAQL-svar fylder ikke main-loopet; hver sub-agent
returnerer kun struktureret JSON for sine punkter). Grupér gerne 2-3 små moduler per sub-agent
(fx A+B sammen, E alene, G alene), men hold tunge moduler (C annoncetekster, G keywords) hver
for sig.

Uddeleger konto-læsningen til `ads-analyst`-agenten (read-only) via Task-værktøjet — den henter
og vurderer kontodata og returnerer fund, skillet forbruger dem. Agenten bruger selv
`run_custom_gaql` + de nævnte MCP-værktøjer og skriver aldrig til kontoen.

Hver sub-agent får: `customer_id`, analysegrundlaget, de relevante punkter + GAQL fra
`references/analysearbejdet.md`, virksomhedsprofilen (hvor relevant), og besked om at:

- (a) køre de oplyste GAQL-queries via `run_custom_gaql` + de nævnte MCP-værktøjer
  (`get_ad_extensions`, `get_ad_performance`, `get_quality_score_audit`,
  `get_keyword_performance`, `get_search_terms_report`, `get_age_gender_performance`,
  `get_account_details`) — kun ENABLED kampagner i tællinger, pausede ekskluderes,
- (b) for hvert punkt afgøre `status` (`ok`/`warn`/`critical`/`no_data`) efter doms-reglen i
  reference-filen,
- (b2) sætte `kind` på hvert punkt — `"lookup"` for et faktuelt opslag (eksisterer en
  udvidelse? er display select slået fra? hvilke lister findes?) eller `"judgment"` for en
  vurdering (er teksten velskrevet? er broad kontrolleret? er strukturen fornuftig?). Kopiér
  `kind` fra reference-filens kolonne, gæt ikke. Det styrer .docx'ens Ekspert-boks: lookup-punkter
  får ingen (intet at efterse), judgment-punkter får én (eksperten bekræfter agentens skøn).
- (c) skrive en kort dansk `finding` med det faktiske tal/navn bag (fx "3 af 7 kampagner har
  <4 sitelinks: Brand, Generisk-DK, Lufthavn"), aldrig en påstand uden data,
- (c2) lokalisere hvert fund i et `evidence`-array — kampagne › ad group › annonce/asset › den
  nøjagtige streng — når punktet peger på noget konkret (en stavefejl, en POOR annonce, en tom ad
  group, en forkert indstilling). Det er forskellen på "der er en stavefejl" (ubrugeligt) og
  "kampagne X › ad group Aalborg › headline 'Bestil taxi til Aaborg'" (handlingsbart). Skriv
  `evidence` som hele, færdige strenge — de gives videre ORDRET (se Trin 4),
- (c3) gå i dybden hvor det fortjener det — for tunge moduler (især C annoncetekster, G
  keywords) må sub-agenten fylde det valgfrie `details`-felt (længere dansk prosa: fordelinger,
  per-ad-group-opdeling, eksempler). Hvor en fuld gennemgang sprænger en opstartsrapport (fx
  per-annonce RSA-hygiejne på hundredvis af annoncer), sæt et `pointer`-felt der henviser til det
  rette dybde-skill (`inb-ads-rsa-hygiene` / `inb-ads-search-term-analyse` / `inb-ads-quality-score`), med forbeholdet at de
  kræver kørselshistorik. `pointer` erstatter ikke et reelt fund — giv altid top-N det værste
  først (fx "5 ad groups på POOR: [navne]"), dernæst pointeren.
- (d) returnere præcis denne form (det `build_docx.py` læser — `details`/`evidence`/`pointer` er
  valgfri og udelades for korte punkter):
  ```json
  {"key": "C", "title": "Modul C — Annoncetekster (ad copy)",
   "items": [{"n": 13, "punkt": "<ordret fra reference>", "status": "warn",
              "kind": "judgment",
              "finding": "<kort dansk konstatering m. tal>",
              "details": "<valgfri længere prosa: fordeling, per-ad-group, eksempler>",
              "evidence": ["Kampagne 'IC | GSN | Hele DK' › ad group 'Aalborg' › headline 'Bestil taxi til Aaborg' → skal være 'Aalborg'"],
              "pointer": "<valgfri: for fuld dybde kør inb-ads-rsa-hygiene / inb-ads-quality-score (kræver kørselshistorik)>"}]}
  ```
  (`kind` er påkrævet — `lookup` eller `judgment`. Et lookup-punkt ser sådan ud:
  `{"n": 1, "punkt": "Sitelinks: min. 4 på hver kampagne", "status": "ok", "kind": "lookup", "finding": "..."}`.)

**GAQL-gotchas (fra live-test 2026-06-10, giv dem videre):**
- `product_link.data_partner.*` / `.google_ads.*` / `.merchant_center.*` kan IKKE selectes sammen
  (`PROHIBITED_FIELD_COMBINATION`). Hent `product_link.type` + `product_link_id` alene.
- `customer`-ressourcen giver én række; tracking-status er
  `customer.conversion_tracking_setting.conversion_tracking_status`.
- Tom svar ≠ "findes ikke aktivt" på en frisk konto — det betyder ofte bare ingen historik →
  `no_data`.

## Trin 4 — Saml findings + byg .docx

Saml de ni modul-objekter + offering-noter til ét findings-objekt:

- `client`, `customer_id`, `window` (analysegrundlaget), `generated` (dagens dato — du sætter
  den, scriptet kalder aldrig en ur-funktion).
- `headline_findings`: 3-5 vigtigste fund, dansk, prioritér `critical` > `warn`. Skarpt og
  konkret (et tal, en konsekvens). Dette er den eneste redaktionelle vurdering du sender ind —
  overbliks-tallene (OK/kan forbedres/kritisk/mangler data) beregner scriptet selv fra
  punkternes `status`, så båndet aldrig kan modsige rækkerne.
- `modules`: de ni objekter i rækkefølge A-I. Giv sub-agenternes `evidence`/`details`/`pointer`
  videre ORDRET — omskriv eller komprimér dem aldrig i samlingen. (Reel fejl-fælde fra
  live-kørsel 1: søgeterm-agenten skrev "stavefejl … i annoncegruppen Aalborg", men ved
  hånd-samling blev "i annoncegruppen Aalborg" væk, så fundet ikke kunne handles på. Kopiér
  felterne 1:1.) Du må stramme `finding`-prosaen let, men `evidence` er adresser og skal stå
  præcist.
- `sources`: de MCP-værktøjer + URLs der faktisk blev kaldt.

Byg dokumentet:
```bash
python3 ${CLAUDE_SKILL_DIR}/lib/build_docx.py --in <findings.json> \
  --out "Opstartsanalyse - <klient> - <YYYY-MM-DD>.docx"
```
Scriptet validerer findings-objektet (fejler højlydt på ugyldig status eller tomme moduler) og
skriver en Inbound-stylet .docx i to lag:

1. **Tjekliste / indholdsfortegnelse** øverst — alle 35 punkter med to checkbokse pr. punkt:
   - **Agent**-kolonne (udfyldt af scriptet): `✓` = agenten behandlede punktet (status
     `ok`/`warn`/`critical`), `☐` = kunne ikke vurderes (`no_data`).
   - **Ekspert**-kolonne (altid tom `☐`): specialisten sætter flueben i hånden efter gennemgang
     af agentens fund — samme human-in-the-loop som ClickUp-subtaskens rigtige flueben, bare
     inde i dokumentet.
   Plus en "Agenten har behandlet X af 35 punkter"-linje, som spejler ClickUp-subtask-listen.
   Dommen står ikke her.
2. **Detaljer per modul** nedenfor — status (farvet) + det konkrete fund per punkt.

Foruden titel, overbliksbånd (de fire status-tal, beregnet af scriptet) og datakilde-footer.

**Agent-fluebenet betyder "gjort", ikke "OK".** Et kritisk fund vises som ✓ i Agent-kolonnen
(agenten behandlede det) og som rødt `Kritisk` i detaljen — bevidst, tjeklisten beviser dækning,
detaljen bærer dommen. Et punkt får kun `☐` i Agent-kolonnen ved `status: no_data`. Ekspert-
kolonnen er altid tom og udfyldes manuelt.

## Trin 5 — Aflever (gated write) + næste skridt

1. **Gem.** Drive = ekstern write → vis resolveret mappe + filnavn, "Proposed upload to Drive
   `<mappe>` — confirm to upload, edit to revise, or say skip." Vent på eksplicit ja. Lokalt =
   ingen gate. Til Drive-upload: brug connectorens `create_file` med
   `contentMimeType: application/vnd.openxmlformats-officedocument.wordprocessingml.document`,
   `disableConversionToGoogleType: true` og `parentId` = kundemappens ID (så det bliver en ægte
   .docx-fil, ikke konverteret til Google Doc).
2. **Kort dansk opsummering** i chatten: N kritiske, M kan-forbedres, hvad der mangler data. De
   vigtigste 3 fund i klartekst.
3. **Næste skridt:** de kritiske/forbedrings-punkter er råstoffet til den grundlæggende
   optimeringsplan kunden præsenteres for (ClickUps "Det kundevendte"). For en fuld
   per-annonce RSA-gennemgang: henvis til `inb-ads-rsa-hygiene` / `inb-ads-search-term-analyse` / `inb-ads-quality-score`
   (kræver kørselshistorik).
4. **`## Datakilder`** — de MCP-værktøjer + evt. URLs der faktisk blev læst.

## Vedligehold

- Tjeklistens indhold (punkter, GAQL, doms-regler) bor kun i `references/analysearbejdet.md` —
  én kilde. Skal et punkt ændres eller tilføjes, gør det der.
- `.docx`-layoutet bor i `lib/build_docx.py` (self-bootstrapper python-docx). Findings-skemaet er
  dokumenteret i docstringen øverst — ret begge steder hvis kontrakten ændres.
- ClickUp-MCP er endnu ikke koblet på. Når den er, læs den live-tjekliste og tik punkter af i
  stedet for at antage reference-filen er hele sandheden — men behold reference-filen som
  fallback.
