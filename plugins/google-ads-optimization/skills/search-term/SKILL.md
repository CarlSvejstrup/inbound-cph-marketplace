---
name: search-term
description: Samtale-drevet søgeterm-gennemgang af én LIVE Google Ads-konto. Samme strukturerede intake som soegeterm-analyse (klient + customer_id, vindue, scope, tærskel, hvilke konverteringer tæller) + samme slim/n-gram-motor. MEN i stedet for en statisk liste FØRER den en samtale om fundene (n-gram, match-type/struktur, tracking-anomalier, konkurrent/off-offering + egne observationer) og I beslutter SAMMEN hvilke negatives og nye keywords der skal med. Når I er enige, skriver den beslutningerne direkte ud i Google Ads Editor-import-klare CSV'er (flere filer → én zip). Read-only mod Google Ads, skriver ALDRIG til kontoen. 0 konverteringer er IKKE bevis for spild på konti hvor folk ringer. Brug når brugeren siger "search term", "søgeterm-samtale", "lad os gå søgetermerne igennem sammen", "diskutér søgetermerne", "find negatives og keywords og lav CSV'er", eller vil tale sig frem til beslutningerne frem for en færdig liste. Svarer på dansk.
---

# search-term

Én konto. Samme skarpe intake som soegeterm-analyse — men derefter en **samtale**, ikke en rapport.
Du graver de interessante fund frem, lægger dem på bordet ("hey, kig på det her"), og I beslutter
**sammen** hvad der skal ske. Til sidst skriver du de aftalte beslutninger direkte ud i Google Ads
Editor-import-klare CSV'er. Read-only mod Google Ads — altid.

## Forskellen fra soegeterm-analyse (læs dette)

`soegeterm-analyse` dømmer hele listen i ét hug og afleverer én farvekodet .xlsx med live FILTER-faner.
Den er god når brugeren vil have det færdige overblik.

**Denne skill er til når brugeren vil TÆNKE HØJT med dig.** Samme data, samme slim+ngram-motor, men:
- Du dømmer ikke alt på forhånd og afleverer. Du **bringer fund op løbende** og spørger.
- Samtalen må gerne være lang. Det er meningen. I borer i de termer der faktisk er i tvivl.
- Du må og skal **bringe dine egne observationer** — ikke kun de deterministiske n-gram/regel-fund.
  Hvis noget falder dig ind som agent ("det er sært at X koster mest men aldrig konverterer, og Y
  ligner et brand vi ikke ejer"), så sig det.
- Outputtet er **CSV(er) direkte til Editor**, bygget af det I blev enige om — ikke en .xlsx med
  formler. (Det omgår hele FILTER-formel-problematikken: vi skriver statiske rækker, intet live.)

## Forudsætning

Google Ads MCP + et `customer_id`. Ingen MCP → sig det og stop. Svar på dansk (engelsk hvis brugeren
skriver engelsk).

## Trin 0 — Hent klient-kontekst (AI Context) FØRST

Før al anden handling på en navngiven klient — og FØR du henter søgeterm-rapporten fra Google Ads
MCP — skal du hente klientens AI Context-fil ind i din kontekst. Det er en læsning (aldrig gated),
men obligatorisk: sådan arver du alt Inbound ved om klienten (ID'er, kontakter, hårde rammer,
navngivningskonvention, budstrategi-norm, KPI'er, pausede-kampagner-intention) i stedet for at gå
søgetermerne igennem blindt.

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
   samtalen og CSV-output støtter sig til: hvordan negativer/navngivning skal se ud, budstrategi-normen,
   og hvilke rammer der ikke må brydes — så de negatives og nye keywords I bliver enige om (Trin 5→6)
   flugter med klientens faktiske opsætning frem for et gæt. AI Context linker også til changelog/
   optimeringslog (læs changelog-doc'et hvis opgaven kræver ændringshistorik — den holdes separat).
5. **Først derefter** bruger du `customer_id` til at hente søgeterm-rapporten og starter samtalen
   (Trin 1→6), med AI Context som ground truth for klient-fakta.

Har klienten ingen række i indekset eller ingen AI Context-fil endnu: sig det, og fortsæt med den
kontekst du kan samle (Drive-mappe, Ads MCP) — men flag hullet. Spring aldrig opslaget stille over.

## Trin 1 — Intake (ét `AskUserQuestion`-kald) — IDENTISK med soegeterm-analyse

Udled så meget som muligt fra samtalen først. Saml i ét kald:

1. **Klient + `customer_id`** — bekræft hvis nævnt; ellers `list_accessible_accounts` → find id'et →
   bekræft. (Klientnoter ligger i vault `clients/*.md` — læs frontmatteren: `google_ads_id`,
   `responsible`, tracking-noter, hårde rammer.)
2. **Analysevindue** — default **sidste 90 dage**. `Sidste 90 dage (Anbefalet)`, `Sidste 30 dage`,
   `Andet`. **VIGTIGT (verificeret live):** `get_search_terms_report`s `date_range` går ind i en
   `DURING`-operator og accepterer KUN Googles dato-literaler (`LAST_30_DAYS`, `LAST_14_DAYS`,
   `LAST_7_DAYS`, `THIS_MONTH`, `LAST_MONTH`). Både `BETWEEN '...'` OG `LAST_90_DAYS` afvises. Så
   vinduet bestemmer kilden (Trin 3): **≤30 dage → `get_search_terms_report`**; **>30 dage / custom
   (inkl. 90 dage) → `run_custom_gaql` på `search_term_view`** med `WHERE segments.date BETWEEN`.
3. **Scope** — `Hele kontoen` eller `Specifik kampagne` (→ `campaign_id` på rapporten).
4. **Filter-tærskel** (kun på `run_custom_gaql`-vejen). DYNAMISK — byg WHERE med
   `slim.where_predicate(dim, value)`:
   - `Forbrug ≥ 50 kr (anbefalet)` — default; `cost`/50.
   - `Forbrug ≥ andet beløb` — `cost`/<beløb>.
   - `Impressions ≥ N` — `impressions`/N (advar: kan tabe høj-forbrugs/lav-visnings-term).
   - `Alt (ingen tærskel)` — `all`; tung lang hale, advar.
   Rapportér altid "trak X termer (tærskel: …)" så et loft aldrig er tavst.
5. **Hvilken konvertering tæller** — formular / **opkald** / nyhedsbrev / PDF? "Alle, eller kun de
   primære (leads/opkald)?" Ændrer direkte hvad der er vinder vs. spild. Ved tvivl: antag alle, men
   skriv forbeholdet ind i samtalen og i et evt. resumé.

(Bemærk: ingen "gem som"-spørgsmål her — outputtet er CSV efter samtalen, se Trin 6.)

## Trin 2 — Forstå tilbuddet BILLIGT (forside + ad groups)

Som soegeterm-analyse. Du skal kunne kende "vores by / vores ydelse" fra "ikke vores tilbud":
1. **Forsiden** — ét `firecrawl-scrape` af klientens forside. Hvad sælger de, hvilke ydelser.
2. **Ad group-navnene** — de staver geografien + ydelses-opdelingen (`IC | GSN | Hellerup` →
   `MR-helkropsscanning`). Strukturen besvarer ofte "er den her term en del af tilbuddet?".

Skriv 3-5 linjers forståelse til dig selv. Fabrikér aldrig et tilbud; hvis scrape fejler, brug ad
group-navnene og sig det i samtalen.

## Trin 3 — Hent + slank (FØR kontekst)

Identisk motor med soegeterm-analyse — `lib/slim.py` håndterer begge shapes (fladt rapport-felt OG
nested `search_term_view.status`; cost i DKK ELLER micros).

**≤30 dage — `get_search_terms_report`:**
```python
import slim
res = slim.slim(report_rows); terms = res["terms"]
```

**>30 dage / custom — `run_custom_gaql`** (rapporten kan ikke; se Trin 1):
```sql
SELECT search_term_view.search_term, search_term_view.status,
       segments.keyword.info.text, segments.keyword.info.match_type,
       campaign.name, ad_group.name,
       metrics.impressions, metrics.clicks, metrics.cost_micros,
       metrics.conversions, metrics.conversions_value
FROM search_term_view
WHERE segments.date BETWEEN '<start>' AND '<slut>'
  AND <FILTER-PRÆDIKAT>                 -- slim.where_predicate(dim, value)
ORDER BY metrics.cost_micros DESC
LIMIT 1000
```
Svaret er for stort til kontekst (resource_name-strenge). **Læs det ALDRIG i kontekst** — gem til en
fil, kør `slim.slim()` på filen (fil-side). Samme term optræder i flere ad groups på
`search_term_view`; **aggregér per term** (sum cost/klik/konv, behold status, saml trigger-keywords)
før du vurderer, så hver term vejes én gang. **Rapportér altid "trak X af Y termer"** (slim har
`dropped_below_floor`).

## Trin 4 — Find de interessante fund (det du bringer til samtalen)

Dette er hjertet. Du laver IKKE en endelig dom her — du **forbereder samtalen**. Kør de faste
analyser OG tilføj dine egne observationer. Nogle ting skal ALTID med; resten er din ekspert-næse.

**Altid med (de faste linser):**
- **N-gram-mønstre** — kør `ngram.analyse(slim_terms)` (helst på det UFILTREREDE sæt, fil-side).
  Den aggregerer cost/klik/konv på tværs af alle termer der indeholder hvert 1/2/3-gram → systemiske
  temaer enkelt-termer skjuler (`helkropsscanning` = 13 termer / 3.697 kr / 0 konv; `hvad koster` =
  pris-research; `gratis` = spild-tema). Tag de stærkeste med op.
- **Match-type + struktur** — hvert keyword/match-type der trigger en term (`segments.keyword.info`).
  Hvor lækker brede matches? Hvilke termer sidder i den forkerte ad group (intentionen passer ikke
  ad-teksten)? Ad groups uden dækning?
- **Tracking/konvertering-anomalier** — høj-klik + 0-konv på on-offering termer (calls-only-historien
  — folk ringer, det er IKKE spild). Pris-intent der ikke konverterer. De "hey, kig her"-fund der
  kræver menneske-dom, ikke et filter.
- **Konkurrent + off-offering** — konkurrentnavne, forkert-intent (`gratis`/`job`/`DIY`/`selv`/
  `uddannelse`), ydelser kunden ikke sælger. De klare negativ-kandidater.

**Også med (din agent-næse):** Bring det op der falder DIG ind. Et sært cost/konv-forhold, en term
der ligner et brand I ikke ejer, en stavevariant der spildes på, en geo udenfor dækningen, en
sæson-ting, et mønster på tværs af kampagner. Det er præcis den slags en samtale er til for. Vær
konkret og vis tallet.

**De rigtige regler (samme som soegeterm-analyse — de retter det den gamle pipeline fik galt):**
- **0 konverteringer er IKKE bevis for spild.** På konti hvor folk **ringer**, spores opkald ofte
  ikke. Lokal term med spend + klik + 0 attribueret konv = sandsynligvis "folk ringede", ikke spild.
- **On-offering lokal geo bliver ALDRIG en NEGATIV.** Er termen en by/ydelse klienten dækker, er det
  kernetrafik — uanset attribuerede konv.
- **NEGATIV kræver et POSITIVT tegn på irrelevans** (off-offering, forkert intention, konkurrent,
  anden branche), ikke bare fravær af konvertering.
- **VINDER kræver reelt udækket (`already_keyword=False`) OG fornuftig signifikans.** 2 konv på en
  bittesmå landsby er støj. Ved tvivl → tag den op i samtalen, ikke som færdig vinder.
- **Lille tal ≠ signifikant.** Vær ærlig om hvad data ikke kan bære.

## Trin 5 — Samtalen (det er HER skillen adskiller sig)

Du har nu fundene. Før en rigtig samtale — ikke en aflevering:

1. **Åbn med det vigtigste mønster, ikke en liste.** Fx: "Det største jeg ser: hele
   `helkropsscanning`-klyngen koster 3.700 kr og har 0 sporede konverteringer. Men I sporer kun
   opkald, så det er nok ikke spild — det er folk der ringer. Skal vi lade den stå og hellere tjekke
   call-tracking, eller vil du have den med som noget at kigge på?"
2. **Tag fundene i prioriteret rækkefølge** (mest spend / mest systemisk først). For hvert: vis
   termen + tallet + din læsning + **et konkret forslag** ("jeg ville gøre `naya kardiologi` til en
   phrase-negativ på kontoniveau — det er en konkurrentklinik, ikke jer"). Spørg om brugeren er enig,
   vil justere match-type/level/keyword, eller droppe det.
3. **Inviter brugerens viden ind.** Brugeren ved ting du ikke gør (er `mommy makeover` en ydelse de
   tilbyder? dækker de Randers nu?). Spørg når en dom afhænger af det.
4. **Foreslå BREDERE keywords hvor det giver mening.** Søgeterm `helkropsscanning pris` → negativ/
   keyword `helkropsscanning` (fang hele pris-familien med ét ord). Søgeterm `naya kardiologi og mr
   scanning` → negativ `naya kardiologi` (fang konkurrentnavnet, ikke den eksakte streng).
5. **Hold styr på beslutningerne undervejs.** Efter hver enighed, noter kort hvad der ryger i hvilken
   bunke (negativ vs. nyt keyword, med match-type + level/placering). Opsummer løbende hvis samtalen
   bliver lang.
6. **Brug `AskUserQuestion` til skarpe valg** (match-type, level, behold/drop), men almindelig
   dialog til det åbne. Tving ikke alt ind i multiple choice — det er en samtale.

Bliv i Trin 5 så længe det tager. Gå først videre når brugeren siger "det er nok" / "skriv dem ud" /
I har været hele den interessante del igennem.

## Trin 6 — Skriv beslutningerne direkte til CSV

Når I er enige, byg en `decisions.json` af det aftalte og kør writeren. INGEN .xlsx, INGEN FILTER —
rene statiske rækker i Editor-import-format.

```bash
python3 ${CLAUDE_SKILL_DIR}/lib/write_csv.py --in <decisions.json> \
  --outdir ~/Downloads --slug "Søgeterm - <klient> - <YYYY-MM-DD>"
```

`decisions.json`:
```json
{
  "client": "Capio", "account_id": "4636067288",
  "negatives": [
    {"keyword": "naya kardiologi", "match_type": "phrase", "level": "account"},
    {"keyword": "mommy makeover",  "match_type": "phrase", "level": "campaign",
     "campaign": "IC | GSN | Aarhus"}
  ],
  "new_keywords": [
    {"keyword": "helkropsscanning aarhus", "match_type": "exact",
     "campaign": "IC | GSN | Aarhus", "ad_group": "MR-helkropsscanning"}
  ]
}
```

**Felt-kontrakt (writeren håndhæver det — den ABORTERER hellere end at sende en knækket import):**
- **negatives[]:** `keyword` (det ord der tilføjes — gerne bredere end søgetermet), `match_type`
  (`exact`/`phrase`/`broad`), `level` (`campaign` default / `ad_group` / `account`), `campaign`
  (kræves ved campaign+ad_group), `ad_group` (kræves ved ad_group), ELLER `list_name` for en delt
  negativliste (så bruges negativliste-skemaet i stedet). En negativ uden et mål → abort.
- **new_keywords[]:** `keyword`, `match_type` (**kun `exact`/`phrase` — aldrig Broad/blank**, ellers
  abort), `campaign` + `ad_group` (kræves begge). Skrives med `Status=Paused` (champion-challenger).

**Output:** `negative keywords.csv` og/eller `nye keywords.csv`. **Mere end én fil → de bundtes i én
`.zip`; præcis én fil → den bare CSV.** Writeren printer stien/erne som JSON. Begge CSV'er er
UTF-8-med-BOM (Æ Ø Å overlever i Editor + Excel på Windows) og i Editors bulk-upload-format —
brugeren importerer direkte. Read-only herfra og ud; mennesket trykker Send i Editor.

**Aflever desuden en kort opsummering i chatten:** hvad I blev enige om (X negatives, Y nye
keywords), de vigtigste mønstre I så, og ærlige forbehold (opkald-attribution, små tal, ting der
skal verificeres i kontoen som call-tracking eller en ydelse).

`## Kilder` — de MCP-værktøjer + URL'er der faktisk blev brugt.

## Valgfrit — .xlsx-overblik

Hvis brugeren OGSÅ vil have det farvekodede overblik (ikke kun CSV'erne til import), så kør
soegeterm-analyses `lib/build_list.py` på en `judged.json` bygget af de samme domme. Det er
sekundært — CSV er den primære leverance her. (Lav det kun hvis brugeren beder om det.)

## Hård sandheds-grænse

- **Skriv aldrig til kontoen.** Read-only. Ingen negatives/keywords pushes; ingen API-mutation.
  Ad-teamet importerer selv CSV'erne i Google Ads Editor og trykker Send.
- **0 konv ≠ spild.** Den vigtigste regel. Brug ALDRIG "0 konv" alene til at kalde noget negativt på
  en calls-only-konto.
- **Lille tal ≠ signifikant.** Vær ærlig; foretræk "lad os tage den op" frem for et forkert kald.
- **Skriv kun det I blev enige om.** decisions.json afspejler samtalen — digt aldrig en negativ eller
  et keyword brugeren ikke sagde ja til.
- **Æ Ø Å altid** i alt output — aldrig ASCII-translitteration.

## Maintenance

- `lib/slim.py` + `lib/ngram.py` — kopier af soegeterm-analyses motor (slank + n-gram). Hold dem i
  sync hvis motoren ændres dér; ingen vurdering i nogen af dem.
- `lib/write_csv.py` — den ENESTE skill-specifikke kode: renderer de aftalte beslutninger til
  Editor-CSV. Kolonne-kontrakterne spejler `google-ads-general/editor-csv-export/export_csv.py`
  (de verificerede Editor-skemaer). Ingen vurdering — hvis du frister til at klassificere en term
  her, lad være: det hører til i samtalen.
- Bevidst INGEN: live FILTER-formler, .xlsx som primær-output, sweep, keyword-map-pull.
