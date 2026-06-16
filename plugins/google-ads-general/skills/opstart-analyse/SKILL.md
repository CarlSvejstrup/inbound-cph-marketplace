---
name: opstart-analyse
description: Kør opstarts-analysen for en ny Google Ads-kunde - gå hele Inbounds Analysearbejdet-tjekliste (Search) igennem mod kontoen og aflever en .docx opstartsrapport i kundens Drive-mappe. Verificerer de 35 punkter READ-ONLY via Google Ads MCP - annonceudvidelser, annoncetekster + ad strength, konverteringstracking, kampagneindstillinger (display select/search partners fra, geo/sprog, individuelt budget), struktur + navngivning, keywords/matchtyper/search terms/brand-ekskludering/QS, budstrategier, remarketinglister + audiences - giver hvert punkt status (OK / kan forbedres / kritisk / mangler data) med det faktiske tal bag. Skriver ALDRIG til kontoen. Slår kundens Drive-mappe + Ads-ID op i vault clients/*.md; findes mappen ikke, stopper den og spørger (en separat make-workflow opretter mappen). Brug når brugeren siger "kør opstartsanalyse", "analyser den nye konto", "opstarts-tjekliste på [klient]", "gennemgå den nye kunde", "analysearbejdet for [klient]", "ny kunde-analyse", eller starter en ny Google Ads-kunde op. Svarer på dansk.
---

# opstart-analyse

Gå **Analysearbejdet (Search)** igennem for en ny Google Ads-kunde og aflever en `.docx`
opstartsrapport i kundens Drive-mappe. Dette er **onboarding-lagets** analyse-skill: en
struktur- og hygiejne-gennemgang af en netop overdraget konto, ikke en performance-audit
(det er `ads-audit-report` i `google-ads-general`) og ikke en optimering af en kørende konto
(det er `google-ads-optimization`).

Hele forløbet og alt output er på **dansk**.

## Hvorfor skillet er formet sådan (læs én gang)

1. **Read-only mod kontoen, altid.** En frisk overdragelse er det mest følsomme øjeblik i en
   kunderelation. Skillet rører ALDRIG kontoen, ingen mutate, intet API-push. Det læser og
   afleverer en `.docx`. Den eneste eksterne write er .docx'en til Drive, og den er gated
   (human-in-the-loop: vis mappe + filnavn, vent på eksplicit `ja`, upload så). Pausede kampagner
   er bevidste, flag dem aldrig.

2. **Struktur- og hygiejne-dom, ikke performance-dom.** På opstart er der ofte slet ingen
   historik. Døm aldrig en asset eller et keyword på CTR/CVR ved opstart. Hvor et punkt kræver
   data der ikke findes endnu, er svaret `Mangler data (ny konto)`, ikke et fabrikeret fund.
   Det er ærligt og det er det rigtige signal til specialisten.

3. **Tjeklisten er en reference-fil, ikke hardcodet.** De 35 punkter, deres MCP-verifikationsvej
   og doms-reglerne bor i `references/analysearbejdet.md`, ordret fra Inbounds ClickUp. Juster ét
   punkt der, uden at røre orkestreringen. (Når ClickUp-MCP kobles på, bliver den live-kilden,
   reference-filen er broen indtil da.)

4. **Kundemappen ejes af et separat make-workflow.** Findes mappen ikke når skillet kører,
   **stop og spørg**, opret den aldrig selv (det fragmenterer kundens Drive). Mappe + Ads-ID
   slås op i vault `clients/*.md`.

## Forudsætninger

- **Google Ads MCP** (read-only). Ikke tilgængelig → sig det og stop.
- **Drive-connector** (Cowork's indbyggede) til den afsluttende .docx-upload.
- **Python 3 + pip** — `lib/build_docx.py` self-bootstrapper `python-docx`.
- Vault `clients/*.md` for `drive_folder` + `google_ads_id` (slå op, gæt aldrig).

## Trin 0 — Kontekst

**Skrive-gate:** den eneste eksterne write er .docx'en til Drive — gated bag eksplicit bekræftelse
(vis mappe + filnavn, vent på `ja`, upload så). **Read-only mod Google Ads, altid** — ingen mutate,
intet API-push. **Læs `references/analysearbejdet.md`** , det er tjeklistens fulde tekst +
verifikationsveje + doms-regler. Du orkestrerer herfra.

**Sprog: alt på dansk** , intake, statusbeskeder, .docx, næste skridt. Skift kun til engelsk hvis
brugeren skriver engelsk.

## Trin 1 — Intake (ét `AskUserQuestion`-kald)

Udled så meget som muligt fra samtalen først, saml resten i ét kald:

1. **Klient + `customer_id`** , bekræft hvis nævnt. Ellers: slå klienten op i vault `clients/*.md`
   (kebab-case filnavn, fx `dantaxi4x48-com.md`) og læs `google_ads_id` fra frontmatter. Kan du
   ikke matche: kør `list_accessible_accounts`, find bedste navne-match, bekræft. Sidste udvej:
   bed om ID manuelt.
2. **Analysegrundlag** , default **Struktur-gennemgang** (ren opsætnings-/hygiejne-tjek, virker
   uden historik). Tilbyd også `Med 90-dages data hvor det findes` for konti der allerede har
   kørt lidt. Til Quality Score bruges altid `LAST_90_DAYS` (men `LAST_90_DAYS` er IKKE et gyldigt
   GAQL date-literal i en `WHERE`-clause, kun til `get_quality_score_audit(date_range=...)`, brug
   `BETWEEN '<YYYY-MM-DD>' AND '<YYYY-MM-DD>'` til alt andet).
3. **Gem-destination** , default kundens Drive-mappe (slå `drive_folder` op i klient-noten).
   Tilbyd også `Kun lokalt (.docx)`. Drive = ekstern write → bekræft én gang før upload.

**Mappe-tjek (kritisk):** når Drive er valgt, verificér at kundemappen findes (`search_files` på
`drive_folder` eller på klientnavnet under root-mappen). **Findes den ikke:** stop og spørg ,
"Kundemappen for [klient] findes ikke i Drive endnu. Skal make-workflowet (mappe-opsætning) køre
først, eller vil du give mig mappe-ID'et manuelt? Jeg opretter den ikke selv." Opret ALDRIG mappen.

**ClickUp-tjek (flag, men fortsæt , modsat Drive):** hvis ClickUp-MCP er tilgængelig, slå op om
kunden er oprettet (`clickup_search` på klientnavnet i Kundespace, eller om der findes en
"Opstartscheckliste: Analysearbejdet (Search)"-task i kundens folder). **Findes kunden ikke i
ClickUp:** flag det tydeligt ("⚠️ [klient] er ikke oprettet i ClickUp endnu , opret kunden via
skabelonen når du får tid") men **kør analysen alligevel** og aflevér .docx'en. Forskellen fra
Drive: analysen kører på Ads-kontoen, som findes uanset ClickUp, og .docx'en er selvbærende. En
manglende Drive-mappe blokerer (intet sted at gemme); en manglende ClickUp-kunde gør ikke (det er
kun et sted at krydse af bagefter). I v1 skriver skillet aldrig til ClickUp , det er en ren
read/flag. (ClickUp-struktur + sti-mønster: se project-noten `research/clickup-onboarding-mcp-capability.md`.)

## Trin 2 — Phase 0: byg virksomhedsprofilen (én sub-agent, før verifikationen)

Flere tjekpunkter er kun meningsfulde mod hvad klienten faktisk sælger , annoncetekst-relevans
(punkt 13-14), keyword-dækning (28), geo/sprog-korrekthed (21), brand-ekskludering (29). Så **én
kort offering-sub-agent kører først** og bygger grundsandheden:

1. Hent landingsside-URL'erne (RSA `final_urls` via en hurtig `ad_group_ad`-pull) og **scrap dem**
   (Firecrawl / connector) for hvad de sælger + til hvem + marked/sprog + brand-varianter.
2. Udled fra konto-signaler , kampagne-/ad-group-navne + eksisterende RSA-headlines.
3. Returnér en kompakt dansk profil: hvad de sælger, hvem, geografi/sprog, brand-varianter, og
   hvad der IKKE er en del af tilbuddet (out-of-scope). **Fallback:** scrape fejler/tynd → kun
   konto-signaler, og SIG det , fabrikér aldrig et tilbud.

Profilen gives ind i de verifikations-sub-agenter nedenfor der har brug for den (modul C, E-geo,
G). De rent strukturelle moduler (A extensions, B adgang, D tracking-config, F struktur, H
bidding-type, I lister) behøver den ikke.

## Trin 3 — Verificér de 9 moduler (sub-agenter, parallelt)

De ni modulgrupper i `references/analysearbejdet.md` (A-I) er **uafhængige** , kør dem parallelt
som sub-agenter for kontekst-isolation (rå GAQL-svar fylder ikke main-loopet; hver sub-agent
returnerer kun struktureret JSON for sine punkter). Grupper gerne 2-3 små moduler per sub-agent for
at holde antallet nede (fx A+B sammen, E alene, G alene), men hold tunge moduler (C annoncetekster,
G keywords) hver for sig.

Hver sub-agent får: `customer_id`, analysegrundlaget, de relevante punkter + GAQL fra
`references/analysearbejdet.md`, virksomhedsprofilen (hvor relevant), og besked om at:
- (a) køre de oplyste GAQL-queries via `run_custom_gaql` + de nævnte MCP-værktøjer (`get_ad_extensions`,
  `get_ad_performance`, `get_quality_score_audit`, `get_keyword_performance`, `get_search_terms_report`,
  `get_age_gender_performance`, `get_account_details`) , **kun ENABLED kampagner i tællinger**, pausede ekskluderes,
- (b) for hvert punkt afgøre `status` (`ok`/`warn`/`critical`/`no_data`) efter doms-reglen i
  reference-filen,
- (c) skrive en kort dansk `finding` med det **faktiske tal/navn bag** (fx "3 af 7 kampagner har
  <4 sitelinks: Brand, Generisk-DK, Lufthavn"), aldrig en påstand uden data,
- (c2) **lokalisere hvert fund** , når et punkt peger på noget konkret (en stavefejl, en POOR
  annonce, en tom ad group, en kampagne med forkert indstilling), SKAL sub-agenten fange HVOR det
  er i et `evidence`-array: kampagne › ad group › annonce/asset › den nøjagtige streng. Det er
  forskellen på "der er en stavefejl" (ubrugeligt) og "kampagne X › ad group Aalborg › headline
  'Bestil taxi til Aaborg'" (handlingsbart). Skriv `evidence` som hele, færdige strenge , de gives
  videre ORDRET (se Trin 4),
- (c3) **gå i dybden hvor det fortjener det** , for tunge moduler (især C annoncetekster, G keywords)
  må sub-agenten fylde det valgfrie `details`-felt (længere dansk prosa: fordelinger, per-ad-group-
  opdeling, eksempler). Og hvor en fuld gennemgang sprænger en opstartsrapport (fx per-annonce RSA-
  hygiejne på hundredvis af annoncer), sæt et `pointer`-felt der henviser til det rette dybde-skill
  (`optimering-loop` / `annonce-optimering`) , MED forbehollet at de skills kræver at kontoen har
  kørt et stykke tid (på en helt ny konto er der ikke data nok). `pointer` ERSTATTER ikke et reelt
  fund , giv altid top-N det værste først (fx "5 ad groups på POOR: [navne]"), DERNÆST pointeren.
- (d) returnere præcis denne form (det `build_docx.py` læser , `details`/`evidence`/`pointer` er
  valgfri og udelades for korte punkter):
  ```json
  {"key": "C", "title": "Modul C — Annoncetekster (ad copy)",
   "items": [{"n": 13, "punkt": "<ordret fra reference>", "status": "warn",
              "finding": "<kort dansk konstatering m. tal>",
              "details": "<valgfri længere prosa: fordeling, per-ad-group, eksempler>",
              "evidence": ["Kampagne 'IC | GSN | Hele DK' › ad group 'Aalborg' › headline 'Bestil taxi til Aaborg' → skal være 'Aalborg'"],
              "pointer": "<valgfri: for fuld dybde kør optimering-loop (kræver kørselshistorik)>"}]}
  ```

**GAQL-gotchas (fra live-test 2026-06-10, giv dem videre):**
- `product_link.data_partner.*` / `.google_ads.*` / `.merchant_center.*` kan IKKE selectes sammen
  (`PROHIBITED_FIELD_COMBINATION`). Hent `product_link.type` + `product_link_id` alene.
- `customer`-ressourcen giver én række; tracking-status er `customer.conversion_tracking_setting.conversion_tracking_status`.
- Tom svar ≠ "findes ikke aktivt" på en frisk konto, det betyder ofte bare ingen historik → `no_data`.

## Trin 4 — Saml findings + byg .docx

Saml de ni modul-objekter + offering-noter til ét findings-objekt:

- `client`, `customer_id`, `window` (analysegrundlaget), `generated` (dagens dato , du sætter den,
  scriptet kalder aldrig en ur-funktion).
- `headline_findings`: 3-5 vigtigste fund, dansk, prioritér `critical` > `warn`. Skriv dem skarpt
  og konkret (et tal, en konsekvens). Dette er den ENESTE redaktionelle vurdering du sender ind ,
  overbliks-tallene (OK/kan forbedres/kritisk/mangler data) beregner scriptet selv fra punkternes
  `status`, så båndet aldrig kan modsige rækkerne.
- `modules`: de ni objekter i rækkefølge A-I. **Giv sub-agenternes `evidence`/`details`/`pointer`
  videre ORDRET , omskriv eller komprimér dem ALDRIG i samlingen.** (Dette er en reel fejl-fælde:
  i første live-kørsel skrev søgeterm-agenten "stavefejl … i annoncegruppen Aalborg", men ved
  hånd-samling blev "i annoncegruppen Aalborg" væk , så fundet kunne ikke handles på. Lokationen
  blev altså indsamlet og derefter tabt i samlingen. Kopiér felterne 1:1.) Du må stramme `finding`-
  prosaen let, men `evidence` er adresser , de skal stå præcist.
- `sources`: de MCP-værktøjer + URLs der faktisk blev kaldt.

Byg dokumentet:
```bash
python3 ${CLAUDE_SKILL_DIR}/lib/build_docx.py --in <findings.json> \
  --out "Opstartsanalyse - <klient> - <YYYY-MM-DD>.docx"
```
Scriptet validerer findings-objektet (fejler højlydt på ugyldig status eller tomme moduler) og
skriver en Inbound-stylet .docx i **to lag**:
1. **Tjekliste / indholdsfortegnelse** øverst , alle 35 punkter med **TO checkbokse pr. punkt**:
   - **Agent**-kolonne (udfyldt af scriptet): `✓` = agenten behandlede punktet (status
     `ok`/`warn`/`critical`), `☐` = kunne ikke vurderes (`no_data`).
   - **Ekspert**-kolonne (altid tom `☐`): til at specialisten sætter flueben i hånden, når de har
     gennemgået agentens fund. Agenten foreslår, eksperten bekræfter , samme human-in-the-loop som
     når ClickUp-subtasken får sit rigtige flueben af et menneske, bare inde i dokumentet.
   Plus en "Agenten har behandlet X af 35 punkter"-linje. Det spejler ClickUp-subtask-listen inde i
   dokumentet, så specialisten ser dækningen på ét blik. Dommen står IKKE her.
2. **Detaljer per modul** nedenfor , status (farvet) + det konkrete fund per punkt.
Foruden titel, overbliksbånd (de fire status-tal, beregnet af scriptet) og datakilde-footer.

**Agent-fluebenet = "gjort", ikke "OK".** Et kritisk fund vises som ✓ i Agent-kolonnen (agenten
behandlede det) og som rødt `Kritisk` i detaljen. Det er bevidst , tjeklisten beviser dækning,
detaljen bærer dommen. Et punkt får kun `☐` i Agent-kolonnen hvis du sætter `status: no_data`
(ingen historik/adgang). Ekspert-kolonnen er ALTID tom , den udfyldes manuelt.

## Trin 5 — Aflever (gated write) + næste skridt

1. **Gem.** Drive = ekstern write → følg approval-pattern: vis resolveret mappe + filnavn,
   "Proposed upload to Drive `<mappe>` , confirm to upload, edit to revise, or say skip." Vent på
   eksplicit ja. Lokalt = ingen gate. Til Drive-upload: brug connectorens `create_file` med
   `contentMimeType: application/vnd.openxmlformats-officedocument.wordprocessingml.document`,
   `disableConversionToGoogleType: true` og `parentId` = kundemappens ID (så det bliver en ægte
   .docx-fil, ikke konverteret til Google Doc).
2. **Kort dansk opsummering** i chatten: N kritiske, M kan-forbedres, hvad der mangler data.
   De vigtigste 3 fund i klartekst.
3. **Næste skridt:** de kritiske/forbedrings-punkter er råstoffet til den grundlæggende
   optimeringsplan, kunden præsenteres for (ClickUps "Det kundevendte"). For en fuld per-annonce
   RSA-gennemgang: henvis til `optimering-loop` / `annonce-optimering` (kræver kørselshistorik).
4. **`## Datakilder`** , de MCP-værktøjer + evt. URLs der faktisk blev læst.

## Hård sandheds-grænse

- **Skriv aldrig til kontoen.** Kun en .docx. Ingen mutate, intet API-push.
- **Opret aldrig kundemappen.** Findes den ikke → stop og spørg.
- **Overclaim ikke.** På en frisk konto er “Mangler data” et ærligt og korrekt svar; fabrikér
  aldrig et fund for at fylde tjeklisten. Status er struktur/hygiejne, ikke performance.
- **Pausede kampagner flages aldrig som negativt fund** , de er bevidste.

## Vedligehold

- Tjeklistens indhold (punkter, GAQL, doms-regler) bor KUN i `references/analysearbejdet.md` ,
  én kilde. Skal et punkt ændres eller tilføjes, gør det der.
- `.docx`-layoutet bor i `lib/build_docx.py` (self-bootstrapper python-docx). Findings-skemaet er
  dokumenteret i docstringen øverst , ret begge steder hvis kontrakten ændres.
- ClickUp-MCP er endnu ikke koblet på. Når den er, læs den live-tjekliste og tik punkter af i
  stedet for at antage reference-filen er hele sandheden , men behold reference-filen som fallback.
