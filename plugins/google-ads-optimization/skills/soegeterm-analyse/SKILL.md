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

## Trin 1 — Intake (ét `AskUserQuestion`-kald)

Udled så meget som muligt fra samtalen først. Saml i ét kald:

1. **Klient + `customer_id`** — bekræft hvis nævnt; ellers `list_accessible_accounts` → find id'et →
   bekræft. (Klientnoter ligger i vault `clients/*.md`.)
2. **Analysevindue** — default **sidste 90 dage**. Vis `Sidste 90 dage (Anbefalet)`, `Sidste 30 dage`,
   `Andet`. `get_search_terms_report` tager et `date_range`; for 90 dage / >30 dage send
   `BETWEEN '<YYYY-MM-DD>' AND '<YYYY-MM-DD>'` (rå `LAST_90_DAYS` afvises af API'et — beregn datoerne).
3. **Scope** — `Hele kontoen` eller `Specifik kampagne`. Specifik → brug `campaign_id` på rapporten
   (færre rækker, hurtigere, og ofte det brugeren faktisk vil). 
4. **Hvilken konvertering tæller** — på lead-gen-konti er der ofte flere conversion actions (formular,
   **opkald**, nyhedsbrev, PDF). Spørg "tæller alle konverteringer, eller kun de primære (leads/opkald)?"
   Det ændrer direkte hvad der er en vinder og hvad der er spild. Hvis brugeren ikke ved det: antag
   alle, men SKRIV forbeholdet i outputtet.
5. **Gem** — `Lokalt (.xlsx)` (default) eller `Drive (klientens mappe)`. Drive = ekstern write →
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

```python
# get_search_terms_report(customer_id, date_range, campaign_id?, limit) -> rapport-rækker
import slim   # lib/slim.py
res = slim.slim(report_rows)          # spend_floor=0 default; sæt kun et gulv på en KÆMPE konto
terms = res["terms"]                  # rene slanke rækker, sorteret efter cost
```

`get_search_terms_report` er præ-aggregeret, fortæller **selv** om termen allerede er et keyword
(`already_keyword`), og er let — ingen `resource_name`-pløre, intet 2.500-rækkers keyword-map, ingen
cost-bånd-shuffling. For en almindelig konto: læg HELE `terms` i kontekst. Kun hvis listen er enorm,
sæt et spend-gulv (og `dropped_below_floor` rapporterer hvor mange — aldrig en tavs trunkering).

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

## Trin 5 — Byg listen + aflever

```bash
python3 ${CLAUDE_SKILL_DIR}/lib/build_list.py --in <judged.json> \
  --out "Søgeterm-analyse - <klient> - <YYYY-MM-DD>.xlsx"
```

`judged.json` = `{client, account_id, period, scope, conversion_note, today, terms:[...]}` hvor hver
term er en slank række + `verdict` + `reason`. `conversion_note` SKAL bære opkald-forbeholdet hvis
konverteringer ikke kun er primære/leads.

Output = **ÉN fane**, alle termer på ét blad, hele rækken farvet efter dom, lille farve-legende +
kontekst øverst, sorteret efter cost. Det er sådan en Google Ads-ekspert selv læser en
søgeterm-rapport — ikke faner at hoppe mellem.

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

## Til konvertering (valgfrit)

Den flade liste er en menneske-leverance, ikke et Editor-import-format. Vil ad-teamet have
Editor-CSV'er ud af de NEGATIV- og VINDER-domme, er det et separat skridt via `editor-csv-export` —
men det er bevidst IKKE en del af denne skill. Denne skill leverer dommen; mennesket beslutter.

## Maintenance

- `lib/slim.py` — den ENESTE deterministiske del: slanker rapporten, regner CTR/CPA, opdager
  `already_keyword`, håndterer både MCP-rapport-shape og rå GAQL (micros→DKK). Ingen vurdering.
- `lib/build_list.py` — bygger den ene farvekodede .xlsx. Renderer kun modellens domme; dømmer intet.
- Bevidst INGEN: `sweep.py`, keyword-map-pull, offering-token-overlap, sub-agent-fan-out, fil-shuffling.
  Hvis du fristes til at lægge vurdering i kode igen: lad være — det var præcis fejlen.
