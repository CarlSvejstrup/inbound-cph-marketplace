---
name: responsive-search-ads
description: Lav Google Ads Responsive Search Ad-tekster i høj kvalitet fra en kundes landingsside, med keyword-data fra Google Ads MCP og udvidet intake (USP, tilbud, trust-tal, brand voice). Kan lave 1 eller flere RSA'er per ad group i ét Editor-klart regneark, navngivet efter Inbounds konvention. Brug når brugeren siger "lav annoncetekster", "RSA til [klient]", "annonce-ark", "responsive search ad", "tekster ud fra landingsside", eller beder om annoncetekster til en Google Ads-kampagne. Svarer på dansk.
---

# responsive-search-ads

Lav Google Ads-annoncetekster (Responsive Search Ads) ud fra en kundes landingsside, en udvidet intake og keyword-data fra Google Ads MCP, og aflever dem i et regneark der kan importeres direkte i Google Ads Editor. Hele forløbet og alt output er på dansk.

## Why this skill exists

The ads team turns a client's landing page into RSA ad copy, fills a sheet, sends it to the client for review, then imports the corrected sheet into Google Ads Editor. The slow, skilled part is the landing-page analysis + copywriting under hard character limits. The risky part is the client editing a headline too long and it sneaking back over-length. This skill automates the copywriting and ships a sheet with live char-count + red color-code so over-length text is caught the moment the client types it.

Det er bygget op om en udvidet intake (USP-hierarki, aktivt tilbud + udløb, trust-tal, brand voice/banned words, top-keywords fra MCP), et valgfrit trin der **lærer budskab af kundens egne top-performende annoncer** (Trin 2.5 — kun aktive annoncer), og de testede skrive-regler i `references/headline-craft.md` (angle-taxonomi, Sentence case, længde-variation, 2026 disapproval-policy).

## When to use

Trigger-fraser: "lav annoncetekster", "RSA til", "annonce-ark", "responsive search ad", "tekster til [klient]", "annoncetekster ud fra landingsside".

## How it works (architecture — read once)

A **new file is built from scratch every run** — there is no cloning of any remote sheet and no cell-editing of an existing file.

- `sheet_layout.py` is the single source of truth for the layout: column order, the `=LEN()` formula beside every text field, and the red conditional-formatting rules (headline LEN > 30, description LEN > 90, path LEN > 15). `build_sheet(n_rows)` builds a workbook with header row 1 and `n_rows` data rows, each row pre-wired with its own LEN formulas and the CF range extended to cover all rows. Because these live in the `.xlsx` layer (not in CSV values), they survive upload to Drive and stay live when the client edits the sheet. Verified: uploading a filled `.xlsx` via the Drive connector keeps `=LEN()` computing.
- `build-template.py` regenerates the committed single-RSA `template.xlsx` (calls `build_sheet(1)`). It is a reference artifact + a quick smoke check; the skill does **not** load it at fill time — `fill-sheet.py` rebuilds the layout fresh for exactly as many rows as there are RSAs. Run `build-template.py` only when you want to inspect the empty layout.
- `fill-sheet.py` reads `ads.json`, calls `build_sheet(len(ads))`, writes only the text cells (never the LEN cells), validates every string per RSA, and saves a new `.xlsx`. One run can produce **1 RSA (one data row) or several RSAs (one row each) in the same ad group**.

This runs in **Cowork** (Drive connector) and **locally** (write file to disk) — no `gws` CLI, no Sheets API.

**Runs on any machine.** The only prerequisite is Python 3 with `pip`. Both scripts self-bootstrap: if `openpyxl` is missing they `pip install` it on first run, so there is no manual setup step. No checked-in virtualenv, no machine-specific paths, no external account auth. If saving to Drive, the Drive connector must be available (Cowork has it); if saving locally, nothing beyond Python is needed.

## Hard limits (Google rejects over-length, it does not truncate)

| Field | Max chars |
|---|---|
| Headline (x15) | 30 |
| Description (x4) | 90 |
| Path (x2) | 15 |

## Column contract (defined in sheet_layout.py)

This IS the Google Ads Editor import schema. Header row 1, then **one data row per RSA** (row 2 for a single ad; rows 2..N+1 for N ads). Every text column is followed by a `LEN` column. Pre-seeded on every data row: `Ad type = "Responsive search ad"`. `Campaign`-cellen overskrives ved hver kørsel med det navn brugeren bekræfter i Trin 1.

```
Campaign | Ad Group | Ad type | Labels |
Headline 1 | LEN | ... | Headline 15 | LEN |
Description 1 | LEN | ... | Description 4 | LEN |
Path 1 | LEN | Path 2 | LEN |
Final URL | Final mobile URL | Vinkel | Hypotese
```

`LEN`, `Vinkel` og `Hypotese` er IKKE Editor-felter. Editor matcher import-kolonner på navn og ignorerer ukendte overskrifter, så de tre forsvinder rent ved import og rører aldrig kontoen. `LEN` giver live tegntælling + rød farve til mennesket; `Vinkel`/`Hypotese` (de to sidste kolonner) dokumenterer annoncens led-vinkel + hypotese per RSA. De er bevidst navngivet så de ikke kolliderer med rigtige Editor-felter (undgå generiske navne som `Label`/`Comment`/`Status`).

### Flere RSA'er i samme ad group (multi-row)

Google Ads Editor importerer **én række per annonce**. Gentager man `Campaign` + `Ad Group` på flere rækker, lander de som flere RSA'er i samme ad group. Det er præcis sådan du leverer de 2-3 RSA'er per ad group som best practice anbefaler — ÉT ark, flere rækker, ikke flere filer.

`fill-sheet.py` accepterer derfor to `ads.json`-former:

- **Én RSA (default):** top-level `headlines`/`descriptions`/`paths` (uændret fra før).
- **Flere RSA'er:** `campaign`/`ad_group`/`final_url` på top-niveau + en `ads`-liste hvor hvert element er én RSA's tekst. Top-niveau-felterne arves af hver annonce medmindre annoncen selv overstyrer dem.

```json
{
  "campaign": "IC | GSN | Generic | Brandsikring",
  "ad_group": "Brandsikring",
  "final_url": "https://...",
  "ads": [
    { "headlines": ["...15..."], "descriptions": ["...4..."], "paths": ["...2..."] },
    { "headlines": ["...15..."], "descriptions": ["...4..."], "paths": ["...2..."] },
    { "headlines": ["...15..."], "descriptions": ["...4..."], "paths": ["...2..."] }
  ]
}
```

Hårde grænser og kvalitets-gates køres **per RSA**; fejl labelles med "RSA 2, Headline 4: …" så du ved hvilken annonce der skal rettes.

*Antallet af RSA'er og deres vinkler vælges af brugeren i intake (Trin 1, Kald 1, spørgsmål 4) — default 1. Selve vinkel-strategien står i Trin 4.*

## Trin 0 — Kontekst

Læs `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` før noget andet. Den indeholder write-gate-reglerne og sprogpolitikken. At gemme filen (til Drive eller lokalt) er en ekstern write — gated bag eksplicit bekræftelse.

**Sprog: alt foregår på dansk** — spørgsmål i intake, statusbeskeder, output-tabellen og næste-skridt. Skift kun til engelsk hvis brugeren skriver til dig på engelsk eller udtrykkeligt beder om det. Selve annonceteksterne skrives også på dansk (se Trin 4).

## Hard rule — brug ALTID AskUserQuestion til intake, men hold antal kald lavt

Hvert intake-felt skal spørges via `AskUserQuestion` med konkrete forslag som options. Gæt aldrig værdier. Hvis du har et logisk default, vis det som **første option** med `(Anbefalet)` i label — brugeren kan altid vælge "Other" og skrive sin egen værdi.

**Saml relaterede felter i ÉT kald.** `AskUserQuestion` tager op til 4 spørgsmål ad gangen — udnyt det. Mål: hele intaken på 3-4 kald i alt, ikke 10+ separate.

Grunden: vi vil bygge muskelhukommelse om Inbounds navngivningskonvention og fange afvigelser (fx pMax i stedet for GSN, brand-kampagne i stedet for generic) før arket genereres — uden at trætte brugeren med en lang kæde af enkeltspørgsmål.

## Trin 1 — Intake (få AskUserQuestion-kald, mange felter per kald)

Følg "Hard rule" ovenfor: saml relaterede felter, hold dig til 3-4 kald i alt. Udled så meget som muligt fra samtalen og landingssiden FØR du spørger. Hvis Carl allerede har sagt klientnavn og URL i samme besked, behøver du ikke spørge om dem — bekræft dem som første option `(Anbefalet)` i det første kald, eller spring dem helt over og gå direkte til kampagnetype.

### Kald 1 — Identitet, kampagnetype, sprog og antal RSA'er (1 AskUserQuestion, op til 4 spørgsmål)

Saml i samme kald:
1. **Klient + URL** — kun hvis ikke allerede klart fra samtalen. Ellers spring over.
2. **Kampagnetype** (altid spørg):
   - Search / Shopping / pMax  — `IC | NETVÆRK | Målretning | Kampagnenavn | Eventuelt`
   - Display / YouTube / Demand Gen — `IC | FORMAT | KAMPAGNENAVN | MÅLRETNING`
   - Audience — `YYYY-MD - IC - Audience type - Audience navn`
3. **Annoncetekst-sprog** (altid spørg): hvilket sprog skal selve annonceteksterne skrives på? Vis som options med `Dansk (Anbefalet)` som første, derefter `Engelsk`, `Svensk`, `Norsk` — og "Other" til alt andet. Default er **dansk**. Dette styrer KUN annonceteksterne; samtalen/intaken kører fortsat på dansk medmindre brugeren skriver på engelsk (se Trin 0). Hvis landingssiden senere viser sig at være på et andet sprog end det valgte, så nævn uoverensstemmelsen for brugeren før du skriver teksterne — gæt ikke.

4. **Antal RSA'er + vinkler** (altid spørg): hvor mange RSA'er til dette ad group, og hvilke led-vinkler? `AskUserQuestion` med `multiSelect: true`. Vis disse options i denne rækkefølge:
   - `1 RSA (Anbefalet)` — én stærk annonce, hele 9-vinkel-mixet. Default. Vælges denne, ignorér resten.
   - `Features` — leder med produkt-/ydelse-spec.
   - `Benefits` — leder med udbytte/resultat.
   - `Trust signals` — leder med social proof / trust-tal.
   - `Clear call-to-action` — leder med tilbud / urgency / handling.
   
   Brugeren vælger enten `1 RSA` ELLER 2-4 af vinkel-options'ene (én RSA per valgt vinkel). Forklar i spørgsmålsteksten at hver valgt vinkel bliver til én komplet RSA der *leder* med den vinkel men stadig bærer hele mixet (ikke en mono-tematisk annonce — se Trin 4). Default-vinkel-sættet hvis brugeren vil have flere men ikke specificerer hvilke: **Features, Benefits, Trust signals, Clear CTA** (vælg de første N af den rækkefølge). Begrund kort: best practice er 2-3 distinkte RSA'er per ad group, men Google er drevet mod 1-2 høj-Ad-Strength annoncer frem for 3 tynde — derfor er 1 default, og 2-3 kun når brugeren beder om det.

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

Ad group-navnet spørges IKKE — default er tom. Hvis Carl vil sætte en, kan han sige det i bekræftelses-svaret eller efterfølgende.

### Mellemtrin — scrape landingssiden FØR kald 4

Kør Trin 2 (Firecrawl-scrape af landingssiden) NU, før du sender kald 4. Pointen: vi vil vise konkrete options fra siden i stedet for friform-tekst, så brugeren kan klikke sig igennem. Uden scrape bliver kald 4 til 4 friform-spørgsmål og en dårligere oplevelse.

### Kald 4 — Tekst-inputs (1 AskUserQuestion, 4 spørgsmål)

Dette er det tunge kald — det henter alt der driver kvaliteten af annonceteksterne, og er forskellen mellem generiske annoncetekster og annoncetekster der konverterer. Spørg om alle fire i ÉT kald. Hvert spørgsmål viser 3-4 konkrete options fra scrapen som første options, "Other" som sidste.

De 4 spørgsmål i samme kald:

1. **USP + tilbud** — top USP fra landingssiden + om der er et aktivt tilbud. Foreslå konkrete USP'er fra scrape som options. Hvis tilbud: brugeren skriver tilbudstekst + udløbsdato i "Other". Begrund: uden USP defaulter headlines til generisk; udløbne tilbud i annonceteksterne giver auto-disapproval.

2. **Trust-tal** — vælg fra options foreslået ud fra scrape ("4.8 stjerner fra 2.300 anmeldelser", "Foretrukket af 50.000+ danskere", "Etableret 1998", "(ingen tal tilgængelige)"). Vi må IKKE finde på tal — kun det der står på siden eller brugeren bekræfter.

3. **Brand voice + banned words** — vælg tone (`Formel`, `Venlig og direkte`, `Teknisk og præcis`, `Energisk og inspirerende`) og om der er ord vi IKKE må bruge. Default banned words: `(ingen)`.

4. **Top-keywords + kontoadgang** — to scenarier:
   - **Google Ads MCP tilgængelig:** spørg om (eller udled fra konteksten) klientens `customer_id`. Hent top 10-20 keywords for kontoen (rangeret efter impressions/conversions) FØR du sender kaldet, og vis dem som options. Brugeren vælger 3-5. **Samme `customer_id` genbruges i Trin 2.5** til at lære af kundens top-annoncer — spørg kun én gang.
   - **MCP IKKE tilgængelig** på denne bruger: vis "(brug landingssidens hovedtermer)" som første option, og lad brugeren skrive 3-5 keywords manuelt via "Other" hvis hen har en Search Terms-eksport. Trin 2.5 springes da også over.

Begrund overordnet: top-keyword skal stå i mindst 3 headlines for Google's relevans-score (se `references/headline-craft.md`).

**Bemærk:** kontoadgangs-checket her (MCP + `customer_id`) er det samme der afgør om Trin 2.5 (lær af top-annoncer) kører. Ét check, én konto, ét spørgsmål — ikke to parallelle stier.

### Bekræft scope (1 tekstbesked, ingen AskUserQuestion)

Saml svarene og vis dem som en kort liste til brugeren før du går til Trin 2:
- Klient, URL, kampagnenavn
- Antal RSA'er + valgte led-vinkler (fx "3 RSA'er: Features, Benefits, Trust signals")
- Top-USP, tilbud, trust-tal, voice, banned words, top-keywords

Vent på "OK" / "go" / lignende kort bekræftelse. Hvis brugeren retter noget: opdater og bekræft igen.

**Gem-destination spørges IKKE.** Skillet leverer ALTID begge formater:
1. Skriver `.xlsx` lokalt i cwd (eller den sti brugeren har implicit i kontexten).
2. Uploader samme fil til Drive via connector — destinationen er klientens kendte mappe under `${user_config.inbound_root_folder_id}` hvis den kan resolves fra klientnavnet, ellers brugerens Drive-rod med en kommentar om at den kan flyttes.

Begge gemninger er stadig eksterne writes — bed om eksplicit bekræftelse en gang før du skriver dem (det dækker begge).

## Navngivnings-skabelon — byg kampagnenavnet

Saml svarene efter den skabelon som matcher kampagnetypen. Vis ALTID resultatet til brugeren via et `AskUserQuestion` med strengen som første option `(Anbefalet)` — brugeren kan overstyre.

### Search / Shopping / pMax
Skabelon: `IC | NETVÆRK | Målretning | Kampagnenavn | Eventuelt`

| Felt | Mulige værdier (vis som options) |
|---|---|
| NETVÆRK | `GSN` (Google Search Network), `Shopping`, `pMax` |
| Målretning | `Brand`, `Product`, `Generic`, `brand products` (kun Shopping) |
| Kampagnenavn | fri tekst (produkt/tema) |
| Eventuelt | fri tekst eller `(ingen)` — typisk brandnavn |

Eksempler:
- `IC | GSN | Brand | Securitas`
- `IC | GSN | Product | Alarmsystemer`
- `IC | GSN | Generic | Alarmsystemer`
- `IC | Shopping | Generic | Alarmsystemer`
- `IC | Shopping | brand products | Alarmsystemer`
- `IC | pMax | Generic | Alarmsystemer`

### Display / YouTube / Demand Gen
Skabelon: `IC | FORMAT | KAMPAGNENAVN | MÅLRETNING`

| Felt | Mulige værdier |
|---|---|
| FORMAT | `GDN` (Google Display Network), `YT` (YouTube), `DG` (Demand Gen) |
| KAMPAGNENAVN | fri tekst (kampagne/tema) |
| MÅLRETNING | `Reach`, `Retargeting`, `Awareness`, `Consideration`, `Conversion` (eller fri tekst via "Other") |

Eksempler:
- `IC | GDN | Webinarer | Reach`
- `IC | YT | Bliv grønnere sammen | Retargeting`
- `IC | DG | Gratis introforløb | Retargeting`

### Audience
Skabelon: `YYYY-MD - IC - Audience type - Audience navn`

| Felt | Værdi |
|---|---|
| YYYY-MD | Indeværende år + måned uden ledende nul (fx `2025-1`, ikke `2025-01`). Brug dagens dato som default. **Bemærk:** eksemplerne fra Inbound bruger `2025-01` med ledende nul — spørg brugeren om begge varianter via AskUserQuestion. |
| Audience type | `Custom Intent`, `Retargeting`, `Affinity`, `In-Market`, `Similar`, `Lookalike` (eller fri tekst) |
| Audience navn | fri tekst (fx "Søgninger på HR system", "Alle besøgende") |

Eksempler:
- `2025-01 - IC - Custom Intent - Søgninger på HR system`
- `2025-01 - IC - Retargeting - Alle besøgende`

## Trin 2 — Analyser landingssiden

Scrape URL'en med Firecrawl. Udtræk konkret (hver linje fodrer et option-sæt i Kald 4):
- **Produkt/ydelse** — hvad sælger de.
- **USP-kandidater** — hvad gør de anderledes.
- **Tone of voice** — formel, venlig, teknisk, energisk.
- **CTA'er på siden** — hvilke handlinger styrer de mod ("Få et tilbud", "Bestil demo", "Køb nu").
- **Trust-signaler med tal** — anmeldelses-score + antal, kunde-antal, år etableret, certificeringer, awards.
- **Pris/tilbud** — hvis et aktivt tilbud står på siden.
- **Brandnavn og logo-tekst.**
- **Sidens sprog** — det sprog brugeren valgte i Kald 1 styrer annonceteksterne. Hvis sidens sprog afviger fra det valgte: nævn det for brugeren før du skriver teksterne — gæt ikke, og skift ikke sprog på egen hånd.

Hvis siden ikke kan hentes: sig det og stop. Vi opfinder ikke claims.

## Trin 2.5 — Lær af kundens top-annoncer (valgfrit — kun hvis konto + MCP)

**Kør kun dette trin hvis Google Ads MCP er tilgængelig OG du har et `customer_id`** (samme check som Kald 4, spørgsmål 4). Hvis ikke — ny kunde uden historik, eller ingen MCP — **spring trinet over** og gå direkte til Trin 3. Landingssiden + branchestudierne i `references/headline-craft.md` bærer da teksterne. Det er det normale for nye kunder, og det er helt fint.

### Hvorfor dette trin findes

Keyword-data (Kald 4) fortæller dig *hvilke ord* der søges på. Dette trin fortæller dig noget andet: *hvordan netop denne kunde formulerer sig når annoncerne faktisk virker.* Branchestudierne i reference-filen er generiske; kundens egne vindere er kunde-specifikke. De to lag supplerer hinanden.

### Hent kun de vindende, aktive annoncer (GAQL — ikke get_ad_performance)

Brug `run_custom_gaql`, ikke `get_ad_performance`. Grunden: `get_ad_performance` har ingen status-filter og kan blande **pausede** annoncer ind. Inbounds hårde regel er at pausede kampagner/annoncer er bevidste og **aldrig** må vurderes på performance. GAQL giver ENABLED-filter + sortering i ét kald:

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
- Hvis kontoen har for få konverteringer til at sortere meningsfuldt (lav-volumen konto), fald tilbage til `ORDER BY metrics.ctr DESC`. Nævn det i dit svar.
- Hvis forespørgslen intet returnerer (ny konto, ingen RSA-historik): spring resten af trinet over, sig det til brugeren, og kør på landingssiden alene.

### Udled en kunde-specifik stilguide — kun BUDSKAB, aldrig formatering

Læs de hentede top-annoncers headlines + descriptions og udled **det semantiske lag**:
- Hvilke **USP'er og hooks** går igen i vinderne? (fx "gratis levering", "døgnvagt", "30 års erfaring")
- Hvilken **benefit-framing** bruger de? (resultat-orienteret vs. feature-orienteret)
- Hvilket **CTA-sprog** virker? (fx "Bestil tilbud" vs. "Se priser")
- Hvilke **emner/temaer** vender kunden tilbage til?

Skriv det op som en kort kunde-stilguide (4-6 bullets) i dit svar, så brugeren ser hvad du lærte.

### FIREWALL — budskab supplerer, formatering arver du ALDRIG

Dette er den vigtigste regel i trinnet. Kundens top-annoncer er valgt på performance, ikke på håndværk. De kan udmærket være skrevet i Title Case, presset alle op i 27-30 tegn, keyword-stuffede, eller bruge superlativer der i dag giver disapproval — og **stadig** være top-performere historisk.

Derfor, med hård præcedens:

- Du arver kundens **budskaber, USP-vægtning, hooks, tone og CTA-formuleringer** (det semantiske lag).
- Du arver **ALDRIG** kundens casing, længde-fordeling, keyword-tæthed, struktur eller eventuelle forbudte ord.
- **`references/headline-craft.md` og scriptets gates vinder hver eneste konflikt.** Sentence case, mindst 4 korte headlines, ingen næsten-ens linjer, ingen banned words, descriptions mod 61-70 tegn, hårde tegngrænser — alt det står over kundens stilguide. Hvis kundens vindere er Title Case, skriver du stadig Sentence case. Hvis deres vindere alle er 30 tegn, skriver du stadig 4-5 korte.

Skriv eksplicit i dit svar: "Lærte budskab fra X top-annoncer; formatering følger headline-craft.md (ikke kundens)." Så er det dokumenteret at firewall'en holdt.

### Datakilde

Tilføj senere i output (Trin 7) at top-annonce-analysen brugte Google Ads MCP (`run_custom_gaql`) på `customer_id`, og hvor mange annoncer den lærte fra.

## Trin 3 — Læs skrive-reglerne

**FØR du skriver annonceteksterne:** læs `${CLAUDE_PLUGIN_ROOT}/skills/responsive-search-ads/references/headline-craft.md`. Den indeholder angle-fordelingen, længde-variation-målene, Sentence case-reglen, keyword-tilstedeværelse, 2026 disapproval-forbud, description-fordelingen og kvalitets-check-listen — testet på millioner af annoncer. Trin 4 nedenfor er den korte huskeliste; reference-filen er den fulde begrundelse, og den vinder ved enhver konflikt.

## Trin 4 — Generer annoncetekster

Producer **20-25 headline-kandidater**, derefter vælg de 15 bedste der opfylder angle-fordelingen fra reference-filen. Plus **4 descriptions** og **2 paths**. (Hårde grænser: se tabellen øverst — 30/90/15.)

**Regler (uddybet i `references/headline-craft.md`):**
- **Kunde-stilguide fra Trin 2.5 (hvis den blev kørt):** læn dig på de budskaber, USP'er, hooks og CTA-formuleringer du udledte — men kun det semantiske lag. Formatering følger headline-craft.md, ikke kundens annoncer (se firewall-reglen i Trin 2.5).
- Kun claims der står på landingssiden eller blev bekræftet i intake (USP-hierarki, trust-tal). Ingen opfundne tal, garantier eller priser.
- **Sentence case overalt** — ikke Title Case.
- **Top-keyword** (fra Google Ads MCP eller manuelt intake) skal stå i **mindst 3 headlines**.
- **Længde-variation (HÅRD gate):** mindst **4 af de 15 headlines under 20 tegn**. `fill-sheet.py` afviser arket hvis ikke. Bland korte (<20), mellem (20-26) og lange (27-30). Dette er den hyppigste fejl — sættet ender med alt presset op i 21-30. Skriv bevidst 4-5 korte.
- **Ingen næsten-ens headlines:** to headlines må ikke sige det samme med andre ord. Tre+ der deler samme åbning afvises af scriptet. Trust/akkreditering er særligt udsat — saml ikke fire varianter af "akkrediteret af X".
- **Banned words** fra intake: scan teksten — ingen optræden.
- **Sproget:** det sprog brugeren valgte i Kald 1 (default dansk). Skift ikke sprog ud fra landingssiden — hvis der er uoverensstemmelse, spurgte du allerede i Trin 2.
- **Længde-selvtjek:** for hver streng, tæl tegn. Ret over-længde INDEN du går videre. `fill-sheet.py` afviser også, men det er hurtigere at fange her.

### Obligatorisk vinkel-audit — udfyld FØR du skriver `ads.json`

Vinkel-mixet kan ikke tjekkes mekanisk af scriptet (det er semantisk), så **du** skal selv dokumentere det. Skriv denne tabel ud i dit svar før arket bygges. Mål-kolonnen er fra reference-filen; "Faktisk" er dit sæt. **Enhver afvigelse skal have en grund på én linje** — ellers retter du sættet.

| Vinkel | Mål | Faktisk | Grund hvis afvigelse |
|---|---|---|---|
| Brand + keyword | 2 | ? | |
| Keyword-led | 3 | ? | |
| Benefit / udbytte | 3 | ? | |
| Feature / spec | 2 | ? | |
| Social proof / trust | 1 | ? | |
| Urgency | 0-1 | ? | |
| CTA (specifik) | 1 | ? | |
| Garanti / risiko | 1 | ? | |
| Location / segment | 1 | ? | |

Målene er en **consumer-default** (alarm-eksemplet). De bøjer sig efter branchen — se "Vinkel-mix pr. branche" i reference-filen. Eksempel på en legitim afvigelse: et B2B-compliance/certificerings-produkt (testinstitut, akkreditering) må gerne være trust-tungt (3 i stedet for 1) og udelade urgency/garanti — skriv da grunden, fx "trust-tungt: compliance-vertikal, akkreditering ER købsargumentet". En afvigelse uden grund er en fejl, ikke en stil.

Gennemgå kvalitets-check-listen fra reference-filen før du skriver `ads.json`.

### Flere RSA'er i samme ad group (styret af Kald 1, spørgsmål 4)

**Antallet og vinklerne er allerede valgt af brugeren** i intake (Kald 1, spørgsmål 4 — "Antal RSA'er + vinkler"). Du beslutter det IKKE selv her. Hver led-vinkel brugeren valgte (Features / Benefits / Trust signals / Clear CTA) bliver til én komplet RSA der leder med den vinkel. Valgte brugeren `1 RSA`, så laver du kun én — spring resten af denne sektion over.

Hvis brugeren bad om flere RSA'er, skal du forstå hvad "distinkt vinkel" faktisk betyder her — det er den nemmeste regel at læse forkert:

> **Distinkt vinkel = distinkt LED/vægtning og formulering, IKKE en mono-tematisk annonce.**

Hver RSA er stadig et **komplet 15-headline-sæt med hele 9-vinkel-mixet ovenfor**. Forskellen mellem RSA'erne er hvilken vinkel der *leder* og hvilke ord der bruges — ikke at den ene kun har features og den anden kun trust. Mapping fra brugerens valg i Kald 1 til led-vinkel:

| Bruger valgte | RSA leder med | Stadig med (hele mixet) |
|---|---|---|
| **Features** | Produkt-/ydelse-spec | + benefit, trust, CTA, keyword-led, … |
| **Benefits** | Udbytte / resultat | + feature, trust, CTA, keyword-led, … |
| **Trust signals** | Social proof / trust-tal (omformuleret) | + benefit, feature, CTA, keyword-led, … |
| **Clear CTA** | Tilbud / urgency / handling | + benefit, feature, trust, keyword-led, … |

**Hvorfor ikke mono-tematiske RSA'er:** en RSA der KUN er trust-headlines ville (a) dumpe vinkel-auditen ovenfor, og (b) trippe `fill-sheet.py`'s næsten-ens-gate (3+ headlines der deler de første 12 tegn afvises). Reference-filen og scriptets gates vinder hver konflikt — også her. Du laver *fuldt udfyldte* RSA'er der hver især består auditen, ikke tynde tema-annoncer.

**Vinkel-auditen køres PER RSA.** Med N RSA'er skriver du N audit-tabeller (én per annonce) i dit svar. Hver enkelt RSA skal selvstændigt opfylde mixet og længde-variationen — gatene tjekker hver række for sig.

Skriv teksten til en `ads.json`. Brug det kampagnenavn brugeren bekræftede i intake (Trin 1, punkt 8).

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

**Flere RSA'er (samme ad group, én række per annonce):** `campaign`/`ad_group`/`final_url` på top-niveau arves af hver annonce. Hver RSA bør have sin egen `vinkel` + `hypotese` (det er præcis den led-vinkel den blev bygget på i vinkel-auditen).
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

**`vinkel` + `hypotese` (valgfri, men anbefalet):** den overordnede led-vinkel og hypotesen bag annoncen. De lander i de to sidste kolonner i arket (`Vinkel`, `Hypotese`), EFTER `Final mobile URL`. Google Ads Editor matcher import-kolonner på navn og ignorerer ukendte overskrifter, så disse to felter forsvinder rent ved import og rører aldrig kontoen — de er kun til menneskets dokumentation og kobler til `annonce-optimering`s vinkel-gap-brief. Skriv dem fra vinkel-auditen (Trin 4), så rationalet følger med arket.

## Trin 5 — Byg arket

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/responsive-search-ads/fill-sheet.py \
  --ads ads.json \
  --out "RSA - <klient> - <YYYY-MM-DD>.xlsx"
```

Scriptet afviser arket i to tilfælde (begge tjekkes **per RSA** — fejl labelles "RSA 2, Headline 4: …" ved flere annoncer):
- **Exit 1 — for lange felter** (over Googles hårde grænse). Ikke til forhandling: ret teksten og kør igen.
- **Exit 2 — kvalitets-gate fejlet** (færre end 4 korte headlines, eller næsten-ens headlines). Det er normalt en reel fejl — ret teksten og kør igen. Kun hvis det er en bevidst, begrundet undtagelse: kør igen med `--allow-quality-warnings` og forklar brugeren hvorfor i dit svar. Override aldrig stiltiende.

Output er en `.xlsx` med teksterne i datarækkerne (række 2 for én RSA, rækker 2..N+1 for N RSA'er), live LEN-formler per række, røde farveregler per række og auto-tilpassede kolonne-bredder — klar til kunde-review.

## Trin 6 — Gem (write — gated)

Skillet leverer ALTID begge formater. Bed om eksplicit bekræftelse en gang før du skriver — den dækker både lokal-fil og Drive-upload.

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
4. **Næste skridt (manuelt, human-in-the-loop):** del filen med kunden til review (skillen deler IKKE selv), og efter kundens rettelser: importer arket i Google Ads Editor.
5. **Datakilder** (kort linje): landingsside (Firecrawl) + om Trin 2.5 kørte (Google Ads MCP `run_custom_gaql`, antal top-annoncer lært fra) eller blev sprunget over (ny kunde / ingen MCP).

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
Næste: del med kunden til review, importer derefter i Google Ads Editor.
```

## Maintenance

- Layoutet bor ÉT sted: `sheet_layout.py` (`FIELDS`, `COLUMNS`, `build_sheet`, `text_cell`, `autosize_columns`). `build-template.py` og `fill-sheet.py` importerer begge derfra — ret kun `sheet_layout.py`, så følger begge med automatisk. Ingen hardcodede celle-lister at holde i sync længere.
- Regenerer det committede single-RSA `template.xlsx` (reference + smoke test): `python3 ${CLAUDE_PLUGIN_ROOT}/skills/responsive-search-ads/build-template.py` (kun når layoutet ændrer sig). Skillen loader IKKE filen ved kørsel — `fill-sheet.py` bygger layoutet friskt for N rækker.
- Skrive-reglerne i `references/headline-craft.md` skal re-checkes hvis Google ændrer disapproval-policy eller Ad Strength-vægtning. Kilder med tal-driven evidens (Optmyzr-studiet) må ikke være over 12 måneder gamle uden ny verifikation.
