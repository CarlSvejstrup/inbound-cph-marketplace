---
name: inb-ads-rsa-copy
description: Skriver Google Ads RSA-annoncetekster ud fra en landingsside, keyword-data og intake og leverer dem som Editor-klare .xlsx-ark med live tegntælling og rød over-længde-farve, hvor claims altid skal stamme fra landingssiden eller bekræftet intake og aldrig opfindes, i modsætning til inb-ads-rsa-hygiene som diagnosticerer levende annoncer og skriver ingen tekst.
---

# inb-ads-rsa-copy

Lav Google Ads-annoncetekster (Responsive Search Ads) ud fra en kundes landingsside, en udvidet intake og keyword-data fra Google Ads MCP, og aflever dem i et regneark som kunden kan gennemse og rette med live tegntælling + rød farvekode. Hele forløbet og alt output er på dansk.

**Vigtigt om Editor-import (rettet 2026-06-03):** Google Ads Editor importerer IKKE .xlsx-filer (`support.google.com/google-ads/editor/answer/56368`: "Google Ads Editor doesn't import XLS files"). Arket her er **menneske-review/redigerings-laget** (live `=LEN()` + rød farve så kundens for lange rettelser fanges), IKKE selve import-filen. Editors rigtige import-stier er: (1) **File import** af en CSV (eller Unicode-tekst `.txt`) i Editors kolonne-skema, eller (2) **"Make multiple changes" → paste** af tab-separerede rækker. Hvilken sti ads-teamet bruger er uafklaret — fuld detalje i `references/sheet-and-editor-contract.md`.

Det slow, skilled arbejde er landingsside-analysen + copywriting under hårde tegngrænser; risikoen er at kunden retter en headline for lang og den sniger sig over-længde tilbage. Skillen automatiserer copywriting og leverer et ark med live tegntælling + rød farve så over-længde fanges i det øjeblik kunden taster. Bygget om en udvidet intake, et valgfrit trin der **lærer budskab af kundens egne top-performende annoncer** (Trin 2.5), og de testede skrive-regler i `../../shared/headline-craft.md`.

## When to use

Trigger-fraser: "lav annoncetekster", "RSA til", "annonce-ark", "responsive search ad", "tekster til [klient]", "annoncetekster ud fra landingsside".

## How it works (kort — fuld detalje i reference)

Et **nyt ark bygges fra bunden hver kørsel** (ingen kloning, ingen celle-redigering). `sheet_layout.py` er single source of truth for layout + `=LEN()`-formler + røde CF-regler; `fill-sheet.py` læser `ads.json`, bygger arket friskt for N rækker, skriver kun tekstceller og validerer per RSA. Én kørsel = 1 RSA (én række) eller flere RSA'er (én række hver) i samme ad group. Kører i **Cowork** (Drive-connector) og **lokalt** — ingen `gws`, ingen Sheets API; scripts self-bootstrapper `openpyxl`.

**Arkitektur, kolonne-kontrakt, multi-row `ads.json`-format og Editor-import-detaljen bor i `references/sheet-and-editor-contract.md`.** Læs den hvis du skal ændre layoutet, forstå multi-row-formatet eller forklare Editor-stien. Kort om det vigtigste:

- **Arket er menneske-review-laget, ikke import-filen.** Google Ads Editor importerer IKKE .xlsx (answer 56368). Editor får teksten via (a) File-import af en CSV i Editor-skemaet eller (b) paste via "Make multiple changes". Hvilken sti ads-teamet bruger er uafklaret — se reference-filen.
- **Kolonnenavne spejler Editors felt-navne** (`Campaign`, `Ad Group`, `Headline 1`, …), plus review-only kolonner `LEN`, `Vinkel`, `Hypotese`. Kun Editor-skema-kolonnerne tages med i en import-CSV; review-kolonnerne bliver i arket.
- **Multi-row:** gentag `Campaign` + `Ad Group` på flere rækker → flere RSA'er i samme ad group. `fill-sheet.py` tager to `ads.json`-former (single top-level, eller en `ads`-liste der arver top-niveau-felter). Antal + vinkler vælges i intake (Trin 1, Kald 1, spørgsmål 4) — default 1.

## Hard limits (Google rejects over-length, it does not truncate)

| Field | Max chars |
|---|---|
| Headline (x15) | 30 |
| Description (x4) | 90 |
| Path (x2) | 15 |

## Trin 0 — Hent klient-kontekst (AI Context) FØRST

Kør `../../shared/client-context-intake.md` som allerførste trin på en navngiven klient — før intake, scrape og alt andet. Det er en læsning (aldrig gated), men obligatorisk: sådan arver du ID'er, kontakter, hårde rammer, navngivningskonvention, budstrategi-norm, KPI'er og pausede-kampagners-intention i stedet for at starte blindt. Den fil holder også Stage-tjekket, delte-Drive-mappe-reglen og fallback når en klient endnu ikke har en AI Context-fil.

**Load-bearing for denne skill:** den vigtigste del i AI Context-filen er klientens **brand voice / tone** — annonceteksterne i Trin 4 skal følge den stemme der står dér, ikke en gættet tone.

**Når `inb-ads-rsa-copy` kaldes som under-trin af en anden skill (`inb-ads-campaign-build`, `inb-ads-rsa-hygiene`) er AI Context allerede i kontekst** — spring opslaget over; kør det kun standalone på en navngiven klient.

## Trin 0.5 — Sprog + write-gate

At gemme filen (til Drive eller lokalt) er en ekstern write — gated bag eksplicit bekræftelse.

**Sprog: alt foregår på dansk** — spørgsmål i intake, statusbeskeder, output-tabellen og næste-skridt. Skift kun til engelsk hvis brugeren skriver til dig på engelsk eller udtrykkeligt beder om det. Selve annonceteksterne skrives også på dansk (se Trin 4).

## Hard rule — brug ALTID AskUserQuestion til intake, men hold antal kald lavt

Hvert intake-felt skal spørges via `AskUserQuestion` med konkrete forslag som options. Gæt aldrig værdier. Har du et logisk default, vis det som **første option** med `(Anbefalet)` i label — brugeren kan altid vælge "Other" og skrive sin egen værdi.

**Saml relaterede felter i ÉT kald.** `AskUserQuestion` tager op til 4 spørgsmål ad gangen. Mål: hele intaken på 3-4 kald i alt, ikke 10+ separate — vi vil fange afvigelser fra Inbounds navngivningskonvention (fx pMax i stedet for GSN) før arket genereres, uden at trætte brugeren med enkeltspørgsmål.

## Trin 1 — Intake (få AskUserQuestion-kald, mange felter per kald)

Udled så meget som muligt fra samtalen og landingssiden FØR du spørger. Hvis Carl allerede har sagt klientnavn og URL i samme besked, spring dem over eller bekræft dem som første option `(Anbefalet)` i det første kald.

### Kald 1 — Identitet, kampagnetype, sprog og antal RSA'er (1 AskUserQuestion, op til 4 spørgsmål)

Saml i samme kald:
1. **Klient + URL** — kun hvis ikke allerede klart fra samtalen. Ellers spring over.
2. **Kampagnetype** (altid spørg):
   - Search / Shopping / pMax  — `IC | NETVÆRK | Målretning | Kampagnenavn | Eventuelt`
   - Display / YouTube / Demand Gen — `IC | FORMAT | KAMPAGNENAVN | MÅLRETNING`
   - Audience — `YYYY-MD - IC - Audience type - Audience navn`
3. **Annoncetekst-sprog** (altid spørg): hvilket sprog skal selve annonceteksterne skrives på? Vis som options `Dansk (Anbefalet)`, `Engelsk`, `Svensk`, `Norsk`, "Other". Default dansk. Dette styrer KUN annonceteksterne; samtalen kører fortsat på dansk medmindre brugeren skriver på engelsk. Hvis landingssiden viser sig at være på et andet sprog end det valgte, nævn uoverensstemmelsen for brugeren før du skriver teksterne — gæt ikke.

4. **Antal RSA'er + vinkler** (altid spørg): hvor mange RSA'er til dette ad group, og hvilke led-vinkler? `AskUserQuestion` med `multiSelect: true`. Vis disse options i denne rækkefølge:
   - `1 RSA (Anbefalet)` — én stærk annonce, hele 9-vinkel-mixet. Default. Vælges denne, ignorér resten.
   - `Features` — leder med produkt-/ydelse-spec.
   - `Benefits` — leder med udbytte/resultat.
   - `Trust signals` — leder med social proof / trust-tal.
   - `Clear call-to-action` — leder med tilbud / urgency / handling.

   Brugeren vælger enten `1 RSA` ELLER 2-4 af vinkel-options'ene (én RSA per valgt vinkel). Forklar i spørgsmålsteksten at hver valgt vinkel bliver til én komplet RSA der *leder* med den vinkel men stadig bærer hele mixet (ikke en mono-tematisk annonce — se Trin 4). Default-vinkel-sæt hvis brugeren vil have flere men ikke specificerer: **Features, Benefits, Trust signals, Clear CTA** (de første N af den rækkefølge). Begrundelse: best practice er 2-3 distinkte RSA'er per ad group, men Google er drevet mod 1-2 høj-Ad-Strength annoncer frem for 3 tynde — derfor er 1 default.

   **Gap-brief-tilstand (lukker loopet fra `inb-ads-rsa-hygiene`):** hvis brugeren starter kørslen med et gap-brief — typisk indsat manuelt fra en tidligere `inb-ads-rsa-hygiene`-kørsel — skal det *forvælge* dette spørgsmål i stedet for at spørge fra bunden. Gap-brief'et er en liste af manglende vinkler per ad group (se "Gap-brief-kontrakt" nedenfor). Behandling:
   - Lav én challenger-RSA per manglende vinkel, ledet af den vinkel. Vis det forvalgte sæt som options med `(Anbefalet — fra gap-brief)` så brugeren kan bekræfte eller justere.
   - Sæt hver challengers `vinkel`-felt (Trin 4 / ark-kolonnen) til den manglende vinkel den fylder, og skriv i `hypotese` at den lukker et gap fundet i optimerings-kørslen (fx "Challenger: fylder manglende urgency-vinkel fra inb-ads-rsa-hygiene").
   - **Gap-brief'et forvælger KUN dette vinkel-spørgsmål.** Resten af intaken kører som normalt: landingssiden scrapes stadig (Trin 2), USP/trust/tilbud spørges stadig (Kald 4), og reglerne i `../../shared/headline-craft.md` gælder stadig — en challenger har lige så meget brug for fuldt copy-kontekst som en frisk annonce.

### Gap-brief-kontrakt (delt med `inb-ads-rsa-hygiene`)

`inb-ads-rsa-hygiene` *producerer* dette; `inb-ads-rsa-copy` *forbruger* det. Samme form i begge skills. **Medium: brugeren indsætter det manuelt** i chatten når kørslen starter — vi parser hverken xlsx-fanen eller `analysis.json`. Det holder de to Cowork-kørsler løst koblet, selvom begge skills nu er søster-skills i samme plugin (`inbound-ads`) og der ikke længere er noget krav om at installere flere plugins for at lukke loopet.

Formen er en liste per ad group:
```
- Ad group: <navn> | Manglende vinkler: <vinkel1>, <vinkel2> | Forslag: <kort tekst>
```
Vinkel-navnene er fra vinkel-taksonomien i `../../shared/headline-craft.md` (benefit, trust, urgency, CTA, feature, keyword-led, brand, location, garanti). Hvis brugeren indsætter noget der ligner men ikke matcher, map til den nærmeste taksonomi-vinkel og nævn det.

### Kald 2 — Navngivnings-felter komprimeret (1 AskUserQuestion, 2-4 spørgsmål)

Spørg i ét kald om de specifikke felter der hører til den valgte kampagnetype. Brug det kortest mulige feltsæt:

- **Search/Shopping/pMax:** netværk + målretning + produkt-/tema-navn + (valgfri) eventuelt-tilføjelse. 3-4 spørgsmål.
- **Display/YT/DG:** format + kampagnenavn + målretning. 3 spørgsmål.
- **Audience:** dato-format (med/uden ledende nul) + audience type + audience navn. 3 spørgsmål.

Hvert spørgsmål har konkrete options fra "Navngivnings-skabelon"-sektionen nedenfor — brugeren kan altid vælge "Other".

### Kald 3 — Bekræft samlet kampagnenavn (1 AskUserQuestion, 1 spørgsmål)

Saml svarene fra kald 1-2 til en streng efter den valgte skabelon. Vis den som første option `(Anbefalet)` — brugeren bekræfter eller skriver et frit alternativ via "Other".

Eksempel:
> Forslag: `IC | GSN | Generic | Alarmsystemer`. Bekræft, eller skriv en anden.

Ad group-navnet spørges IKKE — default er tom. Vil Carl sætte en, kan han sige det i bekræftelses-svaret eller efterfølgende.

### Mellemtrin — scrape landingssiden FØR kald 4

Kør Trin 2 (web_fetch af landingssiden) NU, før du sender kald 4, så du kan vise konkrete options fra siden i stedet for friform-tekst.

### Kald 4 — Tekst-inputs (1 AskUserQuestion, 4 spørgsmål)

Dette er det tunge kald — det henter alt der driver kvaliteten af annonceteksterne, og er forskellen mellem generiske annoncetekster og annoncetekster der konverterer. Spørg om alle fire i ÉT kald. Hvert spørgsmål viser 3-4 konkrete options fra scrapen som første options, "Other" som sidste.

1. **USP + tilbud** — top USP fra landingssiden + om der er et aktivt tilbud. Foreslå konkrete USP'er fra scrape som options. Hvis tilbud: brugeren skriver tilbudstekst + udløbsdato i "Other". Begrund: uden USP defaulter headlines til generisk; udløbne tilbud i annonceteksterne giver auto-disapproval.

2. **Trust-tal** — vælg fra options foreslået ud fra scrape ("4.8 stjerner fra 2.300 anmeldelser", "Foretrukket af 50.000+ danskere", "Etableret 1998", "(ingen tal tilgængelige)"). Find aldrig på tal — kun det der står på siden eller brugeren bekræfter.

3. **Brand voice + banned words** — vælg tone (`Formel`, `Venlig og direkte`, `Teknisk og præcis`, `Energisk og inspirerende`) og om der er ord vi IKKE må bruge. Default banned words: `(ingen)`.

4. **Top-keywords + kontoadgang** — to scenarier:
   - **Google Ads MCP tilgængelig:** spørg om (eller udled fra konteksten) klientens `customer_id`. Hent top 10-20 keywords for kontoen (rangeret efter impressions/conversions) FØR du sender kaldet, og vis dem som options. Brugeren vælger 3-5. **Samme `customer_id` genbruges i Trin 2.5** til at lære af kundens top-annoncer — spørg kun én gang.
   - **MCP IKKE tilgængelig:** vis "(brug landingssidens hovedtermer)" som første option, og lad brugeren skrive 3-5 keywords manuelt via "Other" hvis hen har en Search Terms-eksport. Trin 2.5 springes da også over.

   Begrundelse: top-keyword skal stå i mindst 3 headlines for Google's relevans-score (se `../../shared/headline-craft.md`). Dette samme MCP+`customer_id`-check afgør også om Trin 2.5 kører — ét check, én konto, ét spørgsmål.

### Bekræft scope (1 tekstbesked, ingen AskUserQuestion)

Saml svarene og vis dem som en kort liste til brugeren før du går til Trin 2:
- Klient, URL, kampagnenavn
- Antal RSA'er + valgte led-vinkler (fx "3 RSA'er: Features, Benefits, Trust signals")
- Top-USP, tilbud, trust-tal, voice, banned words, top-keywords

Vent på "OK" / "go" / lignende kort bekræftelse. Retter brugeren noget: opdater og bekræft igen.

**Gem-destination spørges IKKE.** Skillet leverer ALTID begge formater:
1. Skriver `.xlsx` lokalt i cwd (eller den sti brugeren har implicit i kontexten).
2. Uploader samme fil til Drive via connector — destinationen er klientens kendte mappe under `${user_config.inbound_root_folder_id}` hvis den kan resolves fra klientnavnet, ellers brugerens Drive-rod med en kommentar om at den kan flyttes.

Begge gemninger er eksterne writes — bed om eksplicit bekræftelse én gang, som dækker begge.

## Navngivnings-skabelon — byg kampagnenavnet

De fulde felt-værdier og eksempler per kampagnetype (Search/Shopping/pMax, Display/YT/DG, Audience) bor i `references/naming-and-angle-templates.md`, Del 1. Slå den op når du bygger navnet i Kald 2-3. Metode uændret: saml svarene efter den skabelon der matcher kampagnetypen, og vis ALTID resultatet via et `AskUserQuestion` med strengen som første option `(Anbefalet)` — brugeren kan overstyre.

## Trin 2 — Analyser landingssiden

Hent URL'en med `web_fetch`. Udtræk konkret, ordret fra siden (hver linje fodrer et option-sæt i Kald 4):
- **Produkt/ydelse** — hvad sælger de.
- **USP-kandidater** — hvad gør de anderledes.
- **Tone of voice** — formel, venlig, teknisk, energisk.
- **CTA'er på siden** — hvilke handlinger styrer de mod ("Få et tilbud", "Bestil demo", "Køb nu").
- **Trust-signaler med tal** — anmeldelses-score + antal, kunde-antal, år etableret, certificeringer, awards.
- **Pris/tilbud** — hvis et aktivt tilbud står på siden.
- **Brandnavn og logo-tekst.**
- **Sidens sprog** — det sprog brugeren valgte i Kald 1 styrer annonceteksterne. Afviger sidens sprog fra det valgte, nævn det for brugeren før du skriver teksterne — gæt ikke, og skift ikke sprog på egen hånd.

Hvis siden ikke kan hentes: sig det og stop. Vi opfinder ikke claims.

## Trin 2.5 — Lær af kundens top-annoncer (valgfrit — kun hvis konto + MCP)

**Kør kun dette trin hvis Google Ads MCP er tilgængelig OG du har et `customer_id`** (samme check som Kald 4, spørgsmål 4). Hvis ikke — ny kunde uden historik, eller ingen MCP — **spring trinet over** og gå direkte til Trin 3. Landingssiden + branchestudierne i `../../shared/headline-craft.md` bærer da teksterne, hvilket er helt fint for nye kunder.

### Hvorfor dette trin findes

Keyword-data (Kald 4) fortæller dig *hvilke ord* der søges på. Dette trin fortæller dig *hvordan netop denne kunde formulerer sig når annoncerne faktisk virker.* Branchestudierne i `../../shared/headline-craft.md` er generiske; kundens egne vindere er kunde-specifikke. De to lag supplerer hinanden.

### Hent kun de vindende, aktive annoncer (GAQL — ikke get_ad_performance)

Brug `run_custom_gaql`, ikke `get_ad_performance` — den sidste har ingen status-filter og kan blande **pausede** annoncer ind, og Inbounds hårde regel er at pausede kampagner/annoncer er bevidste og **aldrig** må vurderes på performance. GAQL giver ENABLED-filter + sortering i ét kald:

```sql
SELECT
  campaign.name,
  ad_group.name,
  ad_group_ad.ad.responsive_search_ad.headlines,
  ad_group_ad.ad.responsive_search_ad.descriptions,
  metrics.ctr,
  metrics.conversions,
  metrics.cost_micros
FROM ad_group_ad
WHERE campaign.status = 'ENABLED'
  AND ad_group_ad.status = 'ENABLED'
  AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
  AND segments.date DURING LAST_90_DAYS
ORDER BY metrics.conversions DESC, metrics.ctr DESC
LIMIT 15
```

- Sorter på `conversions` først, så `ctr` — vinderne er dem der konverterer, ikke bare dem der får klik.
- Har kontoen for få konverteringer til at sortere meningsfuldt (lav-volumen konto), fald tilbage til `ORDER BY metrics.ctr DESC`. Nævn det i dit svar.
- Returnerer forespørgslen intet (ny konto, ingen RSA-historik): spring resten af trinet over, sig det til brugeren, og kør på landingssiden alene.

### Udled en kunde-specifik stilguide — kun BUDSKAB, aldrig formatering

Læs de hentede top-annoncers headlines + descriptions og udled **det semantiske lag**:
- Hvilke **USP'er og hooks** går igen i vinderne? (fx "gratis levering", "døgnvagt", "30 års erfaring")
- Hvilken **benefit-framing** bruger de? (resultat-orienteret vs. feature-orienteret)
- Hvilket **CTA-sprog** virker? (fx "Bestil tilbud" vs. "Se priser")
- Hvilke **emner/temaer** vender kunden tilbage til?

Skriv det op som en kort kunde-stilguide (4-6 bullets) i dit svar, så brugeren ser hvad du lærte.

### FIREWALL — budskab supplerer, formatering arver du ALDRIG

Dette er den vigtigste regel i trinnet. Kundens top-annoncer er valgt på performance, ikke på håndværk — de kan udmærket være skrevet i Title Case, presset alle op i 27-30 tegn, keyword-stuffede, eller bruge superlativer der i dag giver disapproval, og **stadig** være top-performere historisk.

- Du arver kundens **budskaber, USP-vægtning, hooks, tone og CTA-formuleringer** (det semantiske lag).
- Du arver **ALDRIG** kundens casing, længde-fordeling, keyword-tæthed, struktur eller eventuelle forbudte ord.
- **`../../shared/headline-craft.md` og scriptets gates vinder hver eneste konflikt.** Sentence case, mindst 4 korte headlines, ingen næsten-ens linjer, ingen banned words, descriptions mod 61-70 tegn, hårde tegngrænser — alt det står over kundens stilguide. Er kundens vindere Title Case, skriver du stadig Sentence case; er deres vindere alle 30 tegn, skriver du stadig 4-5 korte.

Skriv eksplicit i dit svar: "Lærte budskab fra X top-annoncer; formatering følger headline-craft.md (ikke kundens)."

### Datakilde

Tilføj senere i output (Trin 7) at top-annonce-analysen brugte Google Ads MCP (`run_custom_gaql`) på `customer_id`, og hvor mange annoncer den lærte fra.

## Trin 3 — Læs skrive-reglerne

**FØR du skriver annonceteksterne:** læs `../../shared/headline-craft.md`. Den indeholder angle-fordelingen, længde-variation-målene, Sentence case-reglen, keyword-tilstedeværelse, 2026 disapproval-forbud, description-fordelingen og kvalitets-check-listen — testet på millioner af annoncer, og den vinder ved enhver konflikt med Trin 4 nedenfor.

## Trin 4 — Generer annoncetekster

Producer **20-25 headline-kandidater**, derefter vælg de 15 bedste der opfylder angle-fordelingen fra `../../shared/headline-craft.md`. Plus **4 descriptions** og **2 paths**. (Hårde grænser: se tabellen øverst — 30/90/15.)

**Regler (uddybet i `../../shared/headline-craft.md`):**
- **Kunde-stilguide fra Trin 2.5 (hvis den blev kørt):** læn dig på de budskaber, USP'er, hooks og CTA-formuleringer du udledte — kun det semantiske lag, formatering følger stadig `../../shared/headline-craft.md` (firewall-reglen i Trin 2.5).
- Kun claims der står på landingssiden eller blev bekræftet i intake (USP-hierarki, trust-tal). Ingen opfundne tal, garantier eller priser.
- **Sentence case overalt** — ikke Title Case.
- **Top-keyword** (fra Google Ads MCP eller manuelt intake) skal stå i **mindst 3 headlines**.
- **Længde-variation (HÅRD gate):** mindst **4 af de 15 headlines under 20 tegn**. `fill-sheet.py` afviser arket hvis ikke. Bland korte (<20), mellem (20-26) og lange (27-30) — den hyppigste fejl er at hele sættet ender presset op i 21-30, så skriv bevidst 4-5 korte.
- **Ingen næsten-ens headlines:** to headlines må ikke sige det samme med andre ord. Tre+ der deler samme åbning afvises af scriptet. Trust/akkreditering er særligt udsat — saml ikke fire varianter af "akkrediteret af X".
- **Banned words** fra intake: scan teksten — ingen optræden.
- **Sproget:** det sprog brugeren valgte i Kald 1 (default dansk). Skift ikke sprog ud fra landingssiden.
- **Længde-selvtjek:** for hver streng, tæl tegn, og ret over-længde inden du går videre — `fill-sheet.py` afviser også, men det er hurtigere at fange her.

### Obligatorisk vinkel-audit — udfyld FØR du skriver `ads.json`

Vinkel-mixet kan ikke tjekkes mekanisk af scriptet (det er semantisk), så **du** skal selv dokumentere det. **Udfyld vinkel-audit-tabellen fra `references/naming-and-angle-templates.md` (Del 2) og skriv den ud i dit svar før arket bygges.** Mål-kolonnen er consumer-defaulten fra `../../shared/headline-craft.md`; "Faktisk" er dit sæt.

- **Enhver afvigelse skal have en grund på én linje** — ellers retter du sættet. Målene bøjer sig efter branchen (se "Vinkel-mix pr. branche" i `../../shared/headline-craft.md`); en afvigelse uden grund er en fejl, ikke en stil.
- **Auditen køres PER RSA:** N annoncer → N audit-tabeller (én per annonce), hver skal selvstændigt opfylde mixet og længde-variationen.

Gennemgå kvalitets-check-listen fra `../../shared/headline-craft.md` før du skriver `ads.json`.

### Flere RSA'er i samme ad group (styret af Kald 1, spørgsmål 4)

**Antallet og vinklerne er allerede valgt af brugeren** i intake (Kald 1, spørgsmål 4). Du beslutter det ikke selv her. Hver led-vinkel brugeren valgte (Features / Benefits / Trust signals / Clear CTA) bliver til én komplet RSA der leder med den vinkel. Valgte brugeren `1 RSA`, laver du kun én — spring resten af denne sektion over.

Forstå hvad "distinkt vinkel" betyder her — det er den nemmeste regel at læse forkert:

> **Distinkt vinkel = distinkt LED/vægtning og formulering, IKKE en mono-tematisk annonce.**

Hver RSA er stadig et **komplet 15-headline-sæt med hele 9-vinkel-mixet ovenfor**. Forskellen mellem RSA'erne er hvilken vinkel der *leder* og hvilke ord der bruges — ikke at den ene kun har features og den anden kun trust. Mapping fra brugerens valg i Kald 1 til led-vinkel:

| Bruger valgte | RSA leder med | Stadig med (hele mixet) |
|---|---|---|
| **Features** | Produkt-/ydelse-spec | + benefit, trust, CTA, keyword-led, … |
| **Benefits** | Udbytte / resultat | + feature, trust, CTA, keyword-led, … |
| **Trust signals** | Social proof / trust-tal (omformuleret) | + benefit, feature, CTA, keyword-led, … |
| **Clear CTA** | Tilbud / urgency / handling | + benefit, feature, trust, keyword-led, … |

**Hvorfor ikke mono-tematiske RSA'er:** en RSA der KUN er trust-headlines ville (a) dumpe vinkel-auditen ovenfor, og (b) trippe `fill-sheet.py`'s næsten-ens-gate (3+ headlines der deler de første 12 tegn afvises). `../../shared/headline-craft.md` og scriptets gates vinder hver konflikt her også — lav *fuldt udfyldte* RSA'er der hver især består auditen (én audit-tabel per RSA, jf. Trin 4-auditen), ikke tynde tema-annoncer.

Skriv teksten til en `ads.json`. Brug det kampagnenavn brugeren bekræftede i intake (Trin 1, Kald 3).

**Én RSA (default):**
```json
{
  "campaign": "IC | GSN | Generic | Alarmsystemer",
  "ad_group": "",
  "headlines": ["...", "... (op til 15)"],
  "descriptions": ["...", "... (op til 4)"],
  "paths": ["...", "..."],
  "final_url": "https://...",
  "final_mobile_url": "",
  "vinkel": "Trust + tryghed",
  "hypotese": "Akkreditering er købsargumentet i compliance-segmentet"
}
```

**Flere RSA'er (samme ad group, én række per annonce):** `campaign`/`ad_group`/`final_url` på top-niveau arves af hver annonce. Hver RSA bør have sin egen `vinkel` + `hypotese` (den led-vinkel den blev bygget på i vinkel-auditen).
```json
{
  "campaign": "IC | GSN | Generic | Alarmsystemer",
  "ad_group": "Alarmsystemer",
  "final_url": "https://...",
  "ads": [
    { "headlines": ["...15..."], "descriptions": ["...4..."], "paths": ["...", "..."], "vinkel": "Trust", "hypotese": "..." },
    { "headlines": ["...15..."], "descriptions": ["...4..."], "paths": ["...", "..."], "vinkel": "Tilbud + CTA", "hypotese": "..." }
  ]
}
```

**`vinkel` + `hypotese` (valgfri, men anbefalet):** den overordnede led-vinkel og hypotesen bag annoncen. De lander i de to sidste kolonner i arket (`Vinkel`, `Hypotese`), EFTER `Final mobile URL`, og hører til menneske-review-laget — de tages IKKE med i import-CSV'en (kun Editor-skema-kolonner). De dokumenterer og kobler til `inb-ads-rsa-hygiene`s vinkel-gap-brief. Skriv dem fra vinkel-auditen (Trin 4), så rationalet følger med arket.

## Trin 5 — Byg arket

```bash
python3 ${CLAUDE_SKILL_DIR}/fill-sheet.py \
  --ads ads.json \
  --out "RSA - <klient> - <YYYY-MM-DD>.xlsx"
```

Scriptet afviser arket i to tilfælde (begge tjekkes **per RSA** — fejl labelles "RSA 2, Headline 4: …" ved flere annoncer):
- **Exit 1 — for lange felter** (over Googles hårde grænse). Ikke til forhandling: ret teksten og kør igen.
- **Exit 2 — kvalitets-gate fejlet** (færre end 4 korte headlines, eller næsten-ens headlines). Normalt en reel fejl — ret teksten og kør igen. Kun ved en bevidst, begrundet undtagelse: kør igen med `--allow-quality-warnings` og forklar brugeren hvorfor i dit svar. Override aldrig stiltiende.

Output er en `.xlsx` med teksterne i datarækkerne (række 2 for én RSA, rækker 2..N+1 for N RSA'er), live LEN-formler per række, røde farveregler per række og auto-tilpassede kolonne-bredder — klar til kunde-review.

## Trin 6 — Gem (write — gated)

Skillet leverer ALTID begge formater. Bed om eksplicit bekræftelse én gang før du skriver — den dækker både lokal-fil og Drive-upload.

**Lokal:** `fill-sheet.py` har allerede skrevet `.xlsx` til disk i Trin 5 (default cwd). Det er den ene af de to leverancer — ingen ekstra handling.

**Drive:** upload samme `.xlsx` via Drive-connector `create_file`:
- `title`: `RSA - <klient> - <YYYY-MM-DD>`
- `parentId`: klientens kendte mappe under `${user_config.inbound_root_folder_id}` hvis den kan resolves fra klientnavnet; ellers brugerens Drive-rod (nævn det i output så brugeren ved at filen kan flyttes).
- `contentMimeType`: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- `base64Content`: base64 af `.xlsx`-filen

Filen lander som en redigerbar Office-mode-fil i Drive. `=LEN()`-formler regner live, og farvereglerne virker — bekræftet ved test.

## Trin 7 — Output

Lever:
1. **Lokal sti** til `.xlsx`-filen på disken.
2. **Drive-link** til samme fil uploadet via connector.
3. **En tabel** med alle 19 strenge + tegnantal, så brugeren ser alt er sikkert.
4. **Næste skridt (manuelt, human-in-the-loop):** del .xlsx'en med kunden til review (skillen deler IKKE selv). Efter kundens rettelser går teksten ind i Google Ads Editor — men IKKE som .xlsx (det kan Editor ikke importere). Enten (a) eksportér de godkendte rækker til en CSV i Editors kolonne-skema og brug File-import, eller (b) kopiér rækkerne (kun Editor-kolonnerne) ind via "Make multiple changes" → paste. Nævn at .xlsx'en er review-laget, ikke import-filen.
5. **Datakilder** (kort linje): landingsside (web_fetch) + om Trin 2.5 kørte (Google Ads MCP `run_custom_gaql`, antal top-annoncer lært fra) eller blev sprunget over (ny kunde / ingen MCP).

Del aldrig filen med kunden automatisk. Send aldrig nogen mail. Præsenter linket — Carl/brugeren videresender.

## Eksempel-output

```
Annonce-ark klar: RSA - Nordkap Friluft - 2026-05-27
Lokal: /Users/carl/work/RSA - Nordkap Friluft - 2026-05-27.xlsx
Drive: https://docs.google.com/.../<file id>

| # | Headline | Tegn |
|---|---|---|
| 1 | Gratis fragt over 499 kr | 24 |
| 2 | Friluftsudstyr i topkvalitet | 28 |
| ... | ... | ... |

| # | Description | Tegn |
|---|---|---|
| 1 | Stort udvalg af telte, soveposer og rygsække til enhver tur. Hurtig levering. | 78 |
| ... | ... | ... |

Paths: friluft (7) udstyr (6) | Final URL: https://nordkapfriluft.dk/outdoor

Alle felter inden for grænsen. LEN-formler + conditional formatting aktiv — kundens for lange rettelser bliver røde live.
Næste: del .xlsx'en med kunden til review. Til Editor: eksportér godkendte rækker til CSV (Editor-skema) og File-import, ELLER paste rækkerne via "Make multiple changes". Editor importerer ikke .xlsx direkte.
```

## Maintenance

- Layout + template-regen: layoutet bor ÉT sted (`sheet_layout.py`); regenerer `template.xlsx` med `build-template.py` kun når layoutet ændrer sig. Fuld maintenance-note i `references/sheet-and-editor-contract.md`.
- Skrive-reglerne i `../../shared/headline-craft.md` skal re-checkes hvis Google ændrer disapproval-policy eller Ad Strength-vægtning. Kilder med tal-driven evidens (Optmyzr-studiet) må ikke være over 12 måneder gamle uden ny verifikation.
