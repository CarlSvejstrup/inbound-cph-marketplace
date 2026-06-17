---
name: soegeterm-analyse
description: Hurtig, skarp søgeterm-analyse af én LIVE Google Ads-konto. Henter den præ-aggregerede get_search_terms_report, slanker rækkerne FØR kontekst (kun de felter en vurdering kræver), og lader Claude dømme HELE listen i ét hug med korrekte regler - leverer ÉN flad farvekodet liste (.xlsx) hvor hver søgeterm er klassificeret VINDER / RELEVANT / FORKERT_PLACERET / NEGATIV / GRÆNSE med en kort dansk begrundelse. Ingen deterministisk sweep, intet keyword-map, ingen fil-dans. Forstår tilbuddet billigt (forside + ad group-navne) før den dømmer. Læser kun (read-only mod Google Ads, skriver ALDRIG til kontoen). VIGTIGT - 0 konverteringer er IKKE bevis for spild på konti hvor folk ringer. Brug når brugeren siger "søgeterm-analyse", "analysér søgetermer for [klient]", "find spild + vindere i søgetermerne", "hvilke negatives og nye keywords", eller vil have en hurtig søgeterm-dom uden hele optimerings-loopet. Svarer på dansk.
---

# soegeterm-analyse

Én konto, ét formål: dømme søgetermerne rigtigt og hurtigt, og aflevere ÉN flad farvekodet liste.

Dette er den **lette, korrekte** søgeterm-analyse. Den erstatter tankegangen i den gamle
`search-terms`-skill (rå GAQL + deterministisk sweep + 8 faner) og i `optimering-loop`s søgeterm-del.
De lavede vurderingen i kode og fejlflagede on-offering lokal-trafik som spild, fordi "0
konverteringer" er forkert på en konto hvor folk **ringer**. Her gør scriptet kun ÉN ting (slanker
rapporten); **Claude dømmer** med de rigtige regler. Read-only mod Google Ads — altid.

## Hvorfor den er bygget sådan (læs dette)

En søgeterm-analyse er IKKE et big-data-problem. En konto med ~200 termer er et par tusind tokens —
Claude kan have HELE listen i kontekst og dømme den i ét hug. Det svære er **vurderingen** (er det
vores by? ringer folk på den her term? er det et konkurrent-navn?), og vurdering hører til hos
modellen med den rigtige kontekst og de rigtige regler — ikke i et filter. Derfor:

- **Scriptet (`lib/slim.py`) slanker kun.** Det smider `resource_name`-skrald + ubrugelige kolonner
  væk FØR noget rammer kontekst, beholder {term, ad group, kampagne, klik, impressions, cost, konv,
  allerede-keyword?}, regner CTR/CPA, sorterer efter cost. Ingen klassifikation, intet keyword-map,
  ingen offering-token-overlap, intet sweep.
- **Modellen dømmer hele den slanke liste i ét pass.** Med tilbuddet + ad group-geografien + de
  korrekte regler nedenfor.

## Forudsætning

Google Ads MCP + et `customer_id`. Ingen MCP → sig det og stop. Svar på dansk (engelsk hvis brugeren
skriver engelsk).

## Trin 0 — Hent klient-kontekst (AI Context) FØRST

Før al anden handling på en navngiven klient — og FØR du henter søgeterm-rapporten fra Google Ads
MCP — skal du hente klientens AI Context-fil ind i din kontekst. Det er en læsning (aldrig gated),
men obligatorisk: sådan arver du alt Inbound ved om klienten (ID'er, kontakter, hårde rammer,
navngivningskonvention, budstrategi-norm, KPI'er, pausede-kampagner-intention) i stedet for at dømme
søgetermer blindt.

1. **Identificér klienten (kunden).** Tag den klient brugeren nævner (navn, domæne eller konto). Er
   det uklart, så spørg hvilken klient før du fortsætter.
2. **Åbn master-klientindekset i Drive** via Drive-connectoren: `search_files` efter Google Doc'en med
   titlen `Inbound CPH — Google Ads klient-index (AI Context)` (aktuelt id
   `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`, i "A - Kunder"-mappen). Læs den med
   `read_file_content`. Den mapper hver klient til Google Ads ID, HubSpot ID, ClickUp-mappe, **Stage**,
   Drive-mappe og **AI Context-fil**.
3. **Find klientens række** (match på navn/domæne/Ads-ID). Notér **Stage** (customer / lead /
   opportunity / "ikke tagget") — en ikke-`customer`-stage betyder en ikke-lukket konto; vægt
   anbefalinger derefter og antag aldrig en aktiv retainer. For delte mapper (Lime, Retriever/Infomedia,
   GSGroup, Nemco, Julemærket, PhoneAlone, DI) vælg rækken for det specifikke marked/konto.
4. **Åbn klientens AI Context-`.md`** via Drive-linket i indeksrækken (`read_file_content`) og tag den
   ind i din kontekst. Den indeholder driftsbriefen: ID'er, kontakter, hårde rammer (læs før du
   handler), mål/KPI'er, navngivningskonvention og sådan-kører-vi-den. Her bor netop de konventioner
   denne analyse støtter sig til: hvordan negativer/navngivning skal se ud, budstrategi-normen, og
   hvilke rammer der ikke må brydes — så `suggested_keyword`, Stage-vægtningen og dommene flugter med
   klientens faktiske opsætning frem for et gæt. AI Context linker også til changelog/optimeringslog
   (læs changelog-doc'et hvis opgaven kræver ændringshistorik — den holdes separat).
5. **Først derefter** bruger du `customer_id` til at hente søgeterm-rapporten (Trin 1→5), med AI
   Context som ground truth for klient-fakta.

Har klienten ingen række i indekset eller ingen AI Context-fil endnu: sig det, og fortsæt med den
kontekst du kan samle (Drive-mappe, Ads MCP) — men flag hullet. Spring aldrig opslaget stille over.

## Trin 1 — Intake (ét `AskUserQuestion`-kald)

Udled så meget som muligt fra samtalen først. Saml i ét kald:

1. **Klient + `customer_id`** — bekræft hvis nævnt; ellers `list_accessible_accounts` → find id'et →
   bekræft. (Klientnoter ligger i vault `clients/*.md`.)
2. **Analysevindue** — default **sidste 90 dage**. Vis `Sidste 90 dage (Anbefalet)`, `Sidste 30 dage`,
   `Andet`. **VIGTIGT (verificeret live):** `get_search_terms_report`s `date_range` går ind i en
   `DURING`-operator og accepterer KUN Googles dato-literaler (`LAST_30_DAYS`, `LAST_14_DAYS`,
   `LAST_7_DAYS`, `THIS_MONTH`, `LAST_MONTH`). Både `BETWEEN '...'` OG `LAST_90_DAYS` afvises af den.
   Så vinduet bestemmer kilden (se Trin 3): **≤30 dage → `get_search_terms_report`** (præ-aggregeret,
   fladt status-felt); **>30 dage / custom (inkl. 90 dage) → `run_custom_gaql` på `search_term_view`**
   med `WHERE segments.date BETWEEN '<start>' AND '<slut>'`.
3. **Scope** — `Hele kontoen` eller `Specifik kampagne`. Specifik → brug `campaign_id` på rapporten
   (færre rækker, hurtigere, og ofte det brugeren faktisk vil). 
4. **Filter-tærskel** (kun relevant på `run_custom_gaql`-vejen, >30 dage). Tærsklen er DYNAMISK —
   spørg hvilken dimension + værdi, og byg WHERE-prædikatet med `slim.where_predicate(dim, value)`:
   - `Forbrug ≥ 50 kr (anbefalet)` — default; `cost`/50. Forbrug definerer spild/vindere, så et
     cost-gulv er det sikre valg.
   - `Forbrug ≥ andet beløb` — `cost`/<beløb> hvis brugeren vil have et andet niveau.
   - `Impressions ≥ N` — `impressions`/N (fanger volumen-termer; men kan tabe en høj-forbrugs-term
     med få visninger — nævn det).
   - `Alt (ingen tærskel)` — `all`; den tunge lange hale. **Advar:** stort payload, langsommere.
   Rapportér altid "trak X termer (tærskel: …)" så valget er synligt.
5. **Hvilken konvertering tæller** — på lead-gen-konti er der ofte flere conversion actions (formular,
   **opkald**, nyhedsbrev, PDF). Spørg "tæller alle konverteringer, eller kun de primære (leads/opkald)?"
   Det ændrer direkte hvad der er en vinder og hvad der er spild. Hvis brugeren ikke ved det: antag
   alle, men SKRIV forbeholdet i outputtet.
6. **Gem** — `Lokalt (.xlsx)` (default) eller `Drive (klientens mappe)`. Drive = ekstern write →
   bekræft først; kan fejle på store filer, fald tilbage til lokalt.

## Trin 2 — Forstå tilbuddet BILLIGT (forside + ad groups)

Du skal vide nok til at kende forskel på "vores by" og "ikke vores tilbud" — ikke mere. To kilder,
begge billige:

1. **Forsiden** — ét scrape af klientens hjemmeside-forside (Firecrawl / `firecrawl-scrape`). Hvad
   sælger de (VVS? badeværelser? begge?), og hvilke ydelser. Ikke 6 sider — forsiden er nok.
2. **Ad group-navnene** — træk ad group-navnene (de står allerede i rapport-rækkerne, eller en hurtig
   `ad_group`-pull). De **staver geografien**: `VVS Århus`, `VVS Allerød`, `VVS Brønshøj` ER det
   geografiske tilbuds-kort. Så "er `vvs hellerup` en del af tilbuddet?" er som regel besvaret af
   strukturen — ikke et gæt.

Skriv 3-5 linjers forståelse til dig selv (hvad sælger de, hvilke byer/områder dækker de, hvilke
ydelser er IKKE en del af tilbuddet). Hvis scrape fejler: brug ad group-navnene alene og skriv det i
outputtets kontekst-linje. Fabrikér aldrig et tilbud.

## Trin 3 — Hent + slank (FØR kontekst)

Vælg kilde efter vinduet (se Trin 1). `slim.slim()` håndterer BEGGE shapes (fladt rapport-felt OG
nested `search_term_view.status`; cost i DKK ELLER micros), så resten er ens.

**≤30 dage — `get_search_terms_report`** (foretrukket: præ-aggregeret, fladt status, let):
```python
# get_search_terms_report(customer_id, date_range=LAST_30_DAYS, campaign_id?, limit)
import slim
res = slim.slim(report_rows)
terms = res["terms"]
```

**>30 dage / custom (inkl. default 90 dage) — `run_custom_gaql`** (rapporten kan ikke; se Trin 1):
```sql
SELECT search_term_view.search_term, search_term_view.status,
       segments.keyword.info.text, segments.keyword.info.match_type,  -- HVILKET keyword matchede
       campaign.name, ad_group.name,
       metrics.impressions, metrics.clicks, metrics.cost_micros,
       metrics.conversions, metrics.conversions_value
FROM search_term_view
WHERE segments.date BETWEEN '<start>' AND '<slut>'
  AND <FILTER-PRÆDIKAT>                 -- fra intake (Trin 1) via sweep-helper, se nedenfor
ORDER BY metrics.cost_micros DESC      -- de DYRESTE først (det er der spild + vindere bor)
LIMIT 1000                              -- loft; se note nedenfor
```
**`<FILTER-PRÆDIKAT>`** bygges af `slim.where_predicate(dimension, value)` ud fra brugerens valg i
Trin 1: `cost`/50 → `metrics.cost_micros >= 50000000` (default), `impressions`/N →
`metrics.impressions >= N`, `all` → `metrics.cost_micros > 0` (tung; advar). Filtrér ALTID
server-side (i WHERE) — det er DER hastigheden kommer fra; ikke client-side i slim.

**`segments.keyword.info.text` + `.match_type`** giver det TRIGGERENDE keyword pr. søgeterm (verificeret
live: `helkropsscanning` trigges af PHRASE-keywordet `helkrops mr scanning`). `slim` læser dem som
`trigger_keyword` + `trigger_match_type` → de bliver til kolonnerne **"Triggerende keyword"** +
**"Keyword match type"** på hovedfanen. (At tilføje `segments.keyword.*` segmenterer rækkerne pr.
keyword — det er den ønskede granularitet; aggregér pr. søgeterm hvis du vil have én række pr. term.)
**Hvorfor 50-kr-gulvet (det er fixet på "det der tog lang tid"):** rå GAQL på `search_term_view` er
tungt — uden gulv var Capios 90-dages-pull ~360k tegn / 500+ rækker, hvoraf 2/3 var lavvolumen-halé
med <5 klik (ren støj). `cost_micros >= 50000000` (50 kr) skærer halen FØR den forlader API'et →
markant mindre payload, hurtigere, og du taber intet handlingsbart (en term der har kostet <50 kr på
90 dage er hverken et spild-problem eller en vinder). Sænk kun gulvet hvis brugeren udtrykkeligt vil
have den lange hale med.

Svaret er stadig for stort til kontekst (resource_name-strenge). **Læs det ALDRIG i kontekst** — det
gemmes til en fil, og du kører `slim.slim()` på filen (fil-side), som smider skraldet væk og giver de
rene rækker. På `search_term_view` optræder samme term i flere ad groups; **aggregér per term** (sum
cost/klik/konv, behold status) før du dømmer, så hver term dømmes én gang.

**Loftet er IKKE tilfældigt — det er `ORDER BY cost DESC` + `LIMIT`, altså top-N efter forbrug.**
Spild og vindere ligger i de højest-forbrugende termer; en 0,10-kr-term kan hverken være. **Rapportér
altid "trak X af Y termer"** så et loft aldrig er tavst (slim har `dropped_below_floor` til spend-gulvet;
for GAQL-loftet: sammenlign LIMIT mod en hurtig `COUNT`-fornemmelse og nævn det hvis det bed). Et
**spend-gulv + højt loft** (fx top 1000 over ~5 kr) er bedre end et lavt loft: fanger alt der betyder
noget uden at slæbe halen med. Loftet skærer på COST, ikke på konverteringer — så på en enorm konto,
hæv loftet hellere end at risikere at en lav-cost-men-konverterende term falder udenfor.

## Trin 4 — Døm HELE listen i ét pass (det er her værdien er)

Giv hver term præcis ÉN `verdict` + en kort dansk `reason`. Dette er en vurdering, ikke et filter —
brug forsiden + ad group-geografien + sund Google Ads-fornuft. **De korrekte regler** (de retter
præcis det den gamle pipeline fik galt):

- **0 konverteringer er IKKE bevis for spild.** På konti hvor folk **ringer**, spores opkald ofte
  ikke. En lokal term med spend + klik + 0 attribuerede konv betyder sandsynligvis "folk ringede",
  ikke "spild". Brug ALDRIG "0 konv" alene til at kalde noget negativt.
- **On-offering lokal geo bliver ALDRIG en NEGATIV.** Hvis termen er en by/område klienten dækker
  (tjek ad group-geografien) og en ydelse de sælger, er det kernetrafik — uanset attribuerede konv.
  `vvs hellerup` for en VVS-virksomhed der dækker Hellerup = RELEVANT, aldrig NEGATIV.
- **NEGATIV kræver et POSITIVT tegn på irrelevans**, ikke fravær af konvertering: off-offering ydelse
  (sælger de ikke), forkert intention (`gratis`, `selv`, `DIY`, `job`, `løn`, `uddannelse`),
  konkurrent-/firmanavn der ikke er klienten, eller en anden branche. Skriv hvilket i `reason`.
- **VINDER kræver reelt udækket OG fornuftig signifikans.** `already_keyword=True` → ALDRIG en vinder
  (den findes allerede; sandsynligvis RELEVANT). Og vær striks på signifikans: 2 konverteringer på en
  bittesmå landsby (`thorsø vvs`) er støj, ikke en vinder — kræv enten flere konverteringer eller
  tydeligt volumen før du kalder noget VINDER. Ved tvivl → GRÆNSE, ikke VINDER.
- **FORKERT_PLACERET** = relevant og købsklar, men i den forkerte ad group eller på et for bredt match
  (intentionen passer ikke ad-teksten/landingssiden den ramte).
- **GRÆNSE** = reelt i tvivl. Brug den hellere end at gætte forkert.

De fem domme: **VINDER / RELEVANT / FORKERT_PLACERET / NEGATIV / GRÆNSE.**

**`suggested_keyword` (det keyword der faktisk tilføjes — behøver IKKE være = søgetermet).** For
NEGATIV + VINDER: sæt ALTID `suggested_keyword` til det keyword du vil tilføje. Tit er det BREDERE end
søgetermet — fx søgeterm `helkropsscanning pris` → foreslået keyword `helkropsscanning` (fang hele
pris-familien med ét negativ/keyword i stedet for den eksakte streng), eller søgeterm `naya kardiologi
og mr scanning` → negativ `naya kardiologi` (fang konkurrentnavnet, ikke den eksakte streng). Default =
søgetermet hvis du ikke sætter andet. Det er DENNE værdi der flyder over i Negativ/Vinder-fanerne, så
den SKAL have indhold på NEGATIV/VINDER. Sæt også `match_type` (Exact/Phrase/Broad) for det tilføjede
keyword.

**VIGTIGT — `already_keyword` blanker IKKE Negativ/Vinder.** På NEGATIV + VINDER vises `Foreslået
keyword` ALTID, også når `already_keyword=True`. Det er bevidst: en term bliver tit en negativ netop
fordi den allerede fanges (for bredt) af et keyword — fx blev `naya kardiologi og mr scanning` (status
ADDED, trigget af et MR-keyword) til en negativ, og hvis kolonnen blankes der, kommer negativ-fanen
tom ud (den fejl Carl fangede). For de andre domme (RELEVANT/FORKERT_PLACERET/GRÆNSE) blankes kolonnen
stadig når termen allerede er et keyword — der er intet at tilføje. `lib/build_list.py::_suggested_kw`
håndhæver dette; rør det ikke uden at læse hvorfor.

## Trin 4.5 — N-gram analyse (systemiske mønstre)

Kør `ngram.analyse(slim_terms)` (helst på det UFILTREREDE sæt — fil-side, aldrig i kontekst — for det
er i den lange hale mønstrene bor). Den tokeniserer hver term i 1/2/3-grams og **aggregerer cost/klik/
konv på tværs af ALLE termer der indeholder hvert n-gram**. Det afslører systemisk spild/vindere som
enkelt-termer skjuler:
```python
import ngram
ng = ngram.analyse(slim_terms)   # [{ngram, words, term_count, cost_dkk, conversions, ...}] sorteret efter cost
```
Verificeret på Capio: `helkropsscanning` optræder i **13 distinkte termer = 3.697 kr, 0 konv** → ÉT
systemisk fund (mod spredte sub-50-kr-rækker gulvet ellers smed væk); `hvad koster` = 0 konv =
pris-research-tema; `capio`/`hellerup` = systemiske vindere. Send `ng` med i `judged.json` som
`ngrams` → bygger **"N-gram analyse"-fanen** (rød = systemisk spild, grøn = systemisk vinder, med
farve-legende). **Komplementær til cost-gulvet:** gulvet gør den dyre top hurtig, n-grammet genfinder
halens signal. Lad de stærkeste n-grams informere række-dommen + `suggested_keyword` (et bevist
spild-n-gram som `gratis` → termer der indeholder det læner NEGATIV med `suggested_keyword` = n-grammet).

**SKRIV en kort analyse af n-grammene** (overordnet: hvilke temaer bløder, hvilke konverterer, hvad
er første handling) og send den med som `ngram_analysis` (en streng; adskil afsnit med blank linje).
Den rendres som en pæn **"Analyse"-boks** øverst på N-gram-fanen (navy bjælke + blødt panel, ét ombrudt
afsnit pr. blank-linje-blok). Det er her din ekspert-læsning af mønstrene lever — ikke kun tallene.

## Trin 5 — Byg listen + aflever

```bash
python3 ${CLAUDE_SKILL_DIR}/lib/build_list.py --in <judged.json> \
  --out "Søgeterm-analyse - <klient> - <YYYY-MM-DD>.xlsx"
```

`judged.json` = `{client, account_id, period, scope, conversion_note, today, terms:[...]}` hvor hver
term er en slank række + `verdict` + `reason` + valgfrit `suggested_keyword` (default = søgetermet) +
`match_type` (Exact/Phrase/Broad) + `level`. `conversion_note` SKAL bære opkald-forbeholdet hvis
konverteringer ikke kun er primære/leads.

Output = **tre faner**:
1. **`Søgetermer`** — hovedfanen: alle termer på ét blad, hele rækken farvet efter `Dom`-kolonnen,
   farve-legende + kontekst øverst, sorteret efter cost. Det er sådan en Google Ads-ekspert selv
   læser en søgeterm-rapport. Brugeren retter `Dom`-kolonnen direkte her.
2. **`Negative keywords`** + 3. **`Nye keywords (vindere)`** — **auto-genereret** via Google Sheets
   `FILTER()` på `Dom`-kolonnen (Dom=NEGATIV → negativ-fanen, Dom=VINDER → vinder-fanen). Retter
   brugeren en `GRÆNSE` til `NEGATIV` på hovedfanen, **opdaterer negativ-fanen sig selv** (i Google
   Sheets). De to faner matcher **Google Ads Editors RIGTIGE bulk-upload-skemaer** (Carls templates),
   med de PÅKRÆVEDE kolonner og faste værdier:
   - **Negative keywords** (negativ-LISTE bulk-upload): `Action`(Add) · `Customer ID` · `Negative
     keyword list name` · `Negative Keyword List ID` · `Negative keyword`(= Foreslået keyword) ·
     `Keyword or list`(keyword) · `Match type`. **`Negative keyword list name` er en placeholder
     `<INDSÆT NEGATIVLISTE-NAVN>`** — brugeren SKAL udfylde den (vi kan ikke kende listens navn; den
     fejler synligt ved import frem for at gætte). Brug enten list-navn ELLER list-ID, ikke begge.
   - **Nye keywords (vindere)** (tilføj-keyword): `Action`(Add) · `Keyword status`(Paused) ·
     `Campaign` · `Ad group` · `Keyword`(= Foreslået keyword) · `Match Type`.
   Begge trækker **Foreslået keyword** (ikke den rå søgeterm). Klar til Editor-import direkte.

**VIGTIGT om FILTER + CSV-broen:** `FILTER()` er live i Google Sheets (brugerens redigerings-flade),
men openpyxl/en offline-læser kan IKKE læse et spildt FILTER-resultat (formler evalueres ikke
offline). Så når CSV-broen bygges, skal den **re-materialisere** de to faner fra den redigerede
`Dom`-kolonne på hovedfanen (som openpyxl GODT kan læse) — ikke læse FILTER-fanerne direkte. Det
holder fanerne live for mennesket OG korrekte for konverteren. (Det er en bevidst kontrakt, ikke en
skjult fælde.)

Aflever desuden en **kort dom i chatten**: hovedmønstre (fx "systemisk: alle lokale geo-termer har 0
sporede konv → opkald spores ikke, tjek call-tracking"), de få vigtigste negatives (med spend), de få
ægte vindere, og ærlige forbehold (opkald-attribution, små tal). Ikke en rapport — en konklusion.

`## Kilder` — de MCP-værktøjer + URL'er der faktisk blev brugt.

## Hård sandheds-grænse

- **Skriv aldrig til kontoen.** Read-only. Ingen negatives/keywords pushes; ingen API-mutation.
  Ad-teamet anvender selv i Google Ads / Editor.
- **0 konv ≠ spild.** Den vigtigste regel. Den fejl gjorde den gamle pipeline farlig.
- **Lille tal ≠ signifikant.** Vær ærlig om hvad data ikke kan bære; foretræk GRÆNSE frem for et
  forkert kald.
- **Æ Ø Å altid** i alt output — aldrig ASCII-translitteration.

## Fra dom til Editor-import

`Søgetermer`-fanen er menneske-leverancen (læs + ret `Dom`). De to andre faner ER allerede Google
Ads Editors bulk-upload-format — så vejen til kontoen er direkte, INGEN `editor-csv-export` nødvendig:
1. Ret `Dom` på `Søgetermer` (+ evt. `Foreslået keyword` / `Match type`) i Google Sheets → Negativ/
   Vinder-fanerne opdaterer sig selv.
2. Udfyld `<INDSÆT NEGATIVLISTE-NAVN>` på negativ-fanen (hvilken delt negativliste skal ordene i).
3. Eksportér den relevante fane som CSV (File → Download → CSV i Sheets) og importér i Google Ads
   Editor (eller upload negativlisten direkte). Read-only herfra og ud — mennesket trykker Send.

(Den gamle `editor-csv-export` er til campaign-build/optimering-loop-workbooks; denne skill behøver
den ikke, fordi fanerne allerede er i import-format.)

## Maintenance

- `lib/slim.py` — den ENESTE deterministiske del: slanker rapporten, regner CTR/CPA, opdager
  `already_keyword`, håndterer både MCP-rapport-shape og rå GAQL (micros→DKK). Ingen vurdering.
- `lib/build_list.py` — bygger den ene farvekodede .xlsx. Renderer kun modellens domme; dømmer intet.
- Bevidst INGEN: `sweep.py`, keyword-map-pull, offering-token-overlap, sub-agent-fan-out, fil-shuffling.
  Hvis du fristes til at lægge vurdering i kode igen: lad være — det var præcis fejlen.
