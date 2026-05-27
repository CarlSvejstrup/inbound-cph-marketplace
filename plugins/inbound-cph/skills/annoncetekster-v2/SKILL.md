---
name: annoncetekster-v2
description: Lav Google Ads Responsive Search Ad-tekster i høj kvalitet fra en kundes landingsside, med keyword-data fra Google Ads MCP og udvidet intake (USP, tilbud, trust-tal, brand voice). Aflever et Google Ads Editor-klart regneark navngivet efter Inbounds konvention. Brug når brugeren siger "lav annoncetekster", "RSA til [klient]", "annonce-ark", "responsive search ad", "tekster ud fra landingsside", eller beder om højere kvalitet end annoncetekster v1. Svarer på dansk.
---

# annoncetekster-v2

Lav Google Ads-annoncetekster (Responsive Search Ads) ud fra en kundes landingsside, en udvidet intake og keyword-data fra Google Ads MCP, og aflever dem i et regneark der kan importeres direkte i Google Ads Editor. Hele forløbet og alt output er på dansk.

**v2 vs v1:** v1 (`annoncetekster`) skriver annoncetekster ud fra landingsside + kampagnenavn. v2 tilføjer fem ekstra intake-felter (USP-hierarki, aktivt tilbud + udløb, trust-tal, brand voice/banned words, top-keywords fra MCP) og håndhæver skrive-reglerne fra `references/headline-craft.md` (angle-taxonomi, Sentence case, længde-variation, 2026 disapproval-policy). Bruges når kvaliteten af annonceteksterne skal være højere end v1's generiske default.

## Why this skill exists

The ads team turns a client's landing page into RSA ad copy, fills a sheet, sends it to the client for review, then imports the corrected sheet into Google Ads Editor. The slow, skilled part is the landing-page analysis + copywriting under hard character limits. The risky part is the client editing a headline too long and it sneaking back over-length. This skill automates the copywriting and ships a sheet with live char-count + red color-code so over-length text is caught the moment the client types it.

## When to use

Trigger phrases: "lav annoncetekster", "RSA til", "annonce-ark", "responsive search ad", "tekster til [klient]", "annoncetekster ud fra landingsside".

## How it works (architecture — read once)

A **new file is built from scratch every run** from a bundled `.xlsx` template — there is no cloning of any remote sheet and no cell-editing of an existing file.

- The template lives at `${CLAUDE_PLUGIN_ROOT}/skills/annoncetekster-v2/template.xlsx`. It holds the full Google Ads Editor column layout, a live `=LEN()` formula beside every text field, and red conditional-formatting rules (headline LEN > 30, description LEN > 90, path LEN > 15). Because these live in the `.xlsx` layer (not in CSV values), they survive upload to Drive and stay live when the client edits the sheet. Verified: uploading a filled `.xlsx` via the Drive connector keeps `=LEN()` computing.
- `build-template.py` regenerates `template.xlsx` deterministically (openpyxl). Run it only when the layout changes; the committed `template.xlsx` is the artifact the skill uses.
- `fill-sheet.py` loads the template, writes only the text cells (never the LEN cells), validates every string against its limit, and saves a new `.xlsx`.

This runs in **Cowork** (Drive connector) and **locally** (write file to disk) — no `gws` CLI, no Sheets API.

**Runs on any machine.** The only prerequisite is Python 3 with `pip`. Both scripts self-bootstrap: if `openpyxl` is missing they `pip install` it on first run, so there is no manual setup step. No checked-in virtualenv, no machine-specific paths, no external account auth. If saving to Drive, the Drive connector must be available (Cowork has it); if saving locally, nothing beyond Python is needed.

## Hard limits (Google rejects over-length, it does not truncate)

| Field | Max chars |
|---|---|
| Headline (x15) | 30 |
| Description (x4) | 90 |
| Path (x2) | 15 |

## Column contract (baked into template.xlsx)

This IS the Google Ads Editor import schema. Header row 1, single data row 2. Every text column is followed by a `LEN` column. Pre-seeded: `Ad type = "Responsive search ad"`. `Campaign`-cellen overskrives ved hver kørsel med det navn brugeren bekræfter i Trin 1.

```
Campaign | Ad Group | Ad type | Labels |
Headline 1 | LEN | ... | Headline 15 | LEN |
Description 1 | LEN | ... | Description 4 | LEN |
Path 1 | LEN | Path 2 | LEN |
Final URL | Final mobile URL
```

## Trin 0 — Kontekst

Læs `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` før noget andet. Den indeholder write-gate-reglerne og sprogpolitikken. At gemme filen (til Drive eller lokalt) er en ekstern write — gated bag eksplicit bekræftelse.

**Sprog: alt foregår på dansk** — spørgsmål i intake, statusbeskeder, output-tabellen og næste-skridt. Skift kun til engelsk hvis brugeren skriver til dig på engelsk eller udtrykkeligt beder om det. Selve annonceteksterne skrives også på dansk (se Trin 4).

## Hard rule — brug ALTID AskUserQuestion til intake

Hvert intake-felt (klientnavn, landingsside, netværk/format, målretning, kampagnenavn, ad group, gem-destination) skal spørges via `AskUserQuestion` med konkrete forslag som options. Gæt aldrig værdier. Hvis du har et logisk default, vis det som **første option** med `(Anbefalet)` i label — brugeren kan altid vælge "Other" og skrive sin egen værdi.

Grunden: vi vil bygge muskelhukommelse om Inbounds navngivningskonvention og fange afvigelser (fx pMax i stedet for GSN, brand-kampagne i stedet for generic) før arket genereres. Friform-input giver inkonsistente kampagnenavne som senere skal renses i Editor.

## Trin 1 — Intake (eet AskUserQuestion ad gangen)

Spørg i denne rækkefølge. Hvert trin er et separat `AskUserQuestion`-kald.

### A. Identitet og kampagne-navn
1. **Klientnavn** — fri tekst via AskUserQuestion (én option `(Anbefalet)` hvis konteksten allerede har et klientnavn fra samtalen, ellers bare "Other"). Bruges i fil-titlen og som `Eventuelt`-feltet i kampagnenavnet.
2. **Landingsside-URL** — fri tekst. Hvis brugeren har nævnt en URL tidligere i samtalen, foreslå den som første option.
3. **Kampagnetype** — bestemmer hvilken navngivningsskabelon der bruges. Options:
   - Search / Shopping / pMax  — skabelon: `IC | NETVÆRK | Målretning | Kampagnenavn | Eventuelt`
   - Display / YouTube / Demand Gen — skabelon: `IC | FORMAT | KAMPAGNENAVN | MÅLRETNING`
   - Audience — skabelon: `YYYY-MD - IC - Audience type - Audience navn`
4. **Netværk / Format** — afhænger af kampagnetype (se "Navngivnings-skabelon" nedenfor).
5. **Målretning** — afhænger af kampagnetype.
6. **Kampagnenavn / produkt** — det specifikke produkt eller tema (fx "Alarmsystemer", "Bliv grønnere sammen", "Gratis introforløb").
7. **Eventuelt** (kun Search/Shopping/pMax, valgfrit) — fx brandnavn "Securitas". Vis "(ingen)" som første option.
8. **Foreslået kampagnenavn** — saml svarene til en streng efter den valgte skabelon, og vis den som første option `(Anbefalet)` i et sidste `AskUserQuestion`. Brugeren bekræfter eller skriver et frit alternativ via "Other".
9. **Ad group-navn** (valgfrit) — default tom (første option: `(tom)`).

### B. Tekst-inputs (v2 — driver headline-kvaliteten)

Disse fem felter er årsagen til at v2 eksisterer. Spring dem ALDRIG over — de er forskellen mellem generiske annoncetekster og annoncetekster der konverterer.

10. **USP-hierarki** — bed brugeren rangere klientens top-3 differentiators. Foreslå options ud fra landingsside-scrape (Trin 2) hvis du allerede har scrapet den; ellers be brugeren skrive dem. Hvis kun een USP er klar: spørg om en sekundær og tertiær. Begrund: uden et rangeret USP-hierarki defaulter alle 15 headlines til generelle benefits.

11. **Aktivt tilbud + udløbsdato** — options:
    - "Ja, der er et tilbud" → følg op med tilbudstekst + udløbsdato.
    - "Nej, ingen aktiv promo" → skip urgency-angle i Trin 4.
    Begrund: udløbne tilbud i annonceteksterne = auto-disapproval. Aktiv promo driver urgency-headline + evt. countdown customizer i Editor.

12. **Trust-tal** — specifikke tal vi må bruge: kunde-antal, år i branchen, anmeldelses-score, certificeringer, awards. Options foreslået ud fra landingsside hvis muligt ("4.8 stjerner fra 2.300 anmeldelser", "Foretrukket af 50.000+ danskere", "Etableret 1998"). Hvis ingen tal: spørg om de findes på Trustpilot eller andetsteds — vi må IKKE finde på tal.

13. **Brand voice + banned words** — to delspørgsmål:
    - **Tone:** options som "Formel", "Venlig og direkte", "Teknisk og præcis", "Energisk og inspirerende".
    - **Banned words:** ord vi IKKE må bruge (fx konkurrent-brands, juridisk problematiske ord, ord klienten har bedt om at undgå). Default option: "(ingen)".

14. **Top-keywords fra Google Ads MCP** — to scenarier:
    - **MCP er tilgængelig** (brugeren har Google Ads MCP koblet på): spørg om Ads-konto-ID (eller foreslå konto baseret på klientnavn). Brug MCP til at hente top 10-20 keywords for kontoen, rangeret efter impressions eller conversions. Vis dem som options — brugeren vælger de 3-5 top-keywords der skal stå i annonceteksterne. Begrund: top-keyword skal stå i mindst 3 headlines for Google's relevans-score.
    - **MCP er IKKE tilgængelig** på denne bruger: be brugeren manuelt skrive 3-5 top-keywords (eller liste fra et Search Terms-eksport). Vis "(brug landingssidens hovedtermer)" som default-option hvis brugeren ikke har keyword-data.

Bekræft det samlede scope (klient, URL, kampagnenavn, USP-hierarki, tilbud, trust-tal, voice, keywords) i én tekstbesked før du går til Trin 2.

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

Scrape URL'en med Firecrawl. Udtræk konkret:
- **Produkt/ydelse** — hvad sælger de.
- **USP-kandidater** — hvad gør de anderledes (bruges til intake-spørgsmål 10).
- **Tone of voice** — formel, venlig, teknisk, energisk (bruges til intake-spørgsmål 13).
- **CTA'er på siden** — hvilke handlinger styrer de mod ("Få et tilbud", "Bestil demo", "Køb nu").
- **Trust-signaler med tal** — anmeldelses-score + antal, kunde-antal, år etableret, certificeringer, awards (bruges til intake-spørgsmål 12).
- **Pris/tilbud** — hvis et aktivt tilbud står på siden (bruges til intake-spørgsmål 11).
- **Brandnavn og logo-tekst.**
- **Sidens sprog** — hvis ikke dansk, matcher annonceteksterne sidens sprog.

Hvis siden ikke kan hentes: sig det og stop. Vi opfinder ikke claims.

Hvis du allerede har scrapet siden FØR Trin 1's USP/trust/tilbud-spørgsmål: brug scrapen til at foreslå konkrete options i `AskUserQuestion` i stedet for friform-svar. Det er hele pointen med v2.

## Trin 3 — Læs skrive-reglerne

**FØR du skriver annonceteksterne:** læs `${CLAUDE_PLUGIN_ROOT}/skills/annoncetekster-v2/references/headline-craft.md`. Den indeholder:

- Den faste 15-headline angle-fordeling (brand+keyword, keyword-led, benefit, feature, social proof, urgency, CTA, garanti, location).
- Længde-variation-mål (4-5 korte, 6-7 mellem, 3-4 lange).
- Sentence case-reglen (3.7× CPA-forskel — det er ikke smag).
- Keyword-tilstedeværelse-kravet (top-keyword i ≥3 headlines).
- 2026 disapproval-forbud (emojis, superlativer uden bevis, "klik her", konkurrent-brands).
- Description-fordelingen (benefit+CTA / feature+proof / trust+garanti / urgency+benefit).
- Kvalitets-check-listen du gennemgår før arket bygges.

Disse regler er testet på millioner af annoncer. Følg dem.

## Trin 4 — Generer annoncetekster

Producer **20-25 headline-kandidater**, derefter vælg de 15 bedste der opfylder angle-fordelingen fra reference-filen. Plus **4 descriptions** og **2 paths**.

Hårde grænser: headlines ≤ 30 tegn, descriptions ≤ 90, paths ≤ 15.

**Regler (uddybet i `references/headline-craft.md`):**
- Kun claims der står på landingssiden eller blev bekræftet i intake (USP-hierarki, trust-tal). Ingen opfundne tal, garantier eller priser.
- **Sentence case overalt** — ikke Title Case.
- **Top-keyword** (fra Google Ads MCP eller manuelt intake) skal stå i **mindst 3 headlines**.
- **Længde-variation:** bland korte (<20), mellem (20-26) og lange (27-30).
- **Banned words** fra intake: scan teksten — ingen optræden.
- **Sproget:** dansk medmindre landingssiden er på et andet sprog.
- **Længde-selvtjek:** for hver streng, tæl tegn. Ret over-længde INDEN du går videre. `fill-sheet.py` afviser også, men det er hurtigere at fange her.

Gennemgå kvalitets-check-listen fra reference-filen før du skriver `ads.json`.

Skriv teksten til en `ads.json`. Brug det kampagnenavn brugeren bekræftede i intake (Trin 1, punkt 8):
```json
{
  "campaign": "IC | GSN | Generic | Alarmsystemer",
  "ad_group": "",
  "headlines": ["...", "... (op til 15)"],
  "descriptions": ["...", "... (op til 4)"],
  "paths": ["...", "..."],
  "final_url": "https://...",
  "final_mobile_url": ""
}
```

## Trin 5 — Byg arket

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/annoncetekster-v2/fill-sheet.py \
  --ads ads.json \
  --out "RSA - <klient> - <YYYY-MM-DD>.xlsx"
```

Hvis scriptet afviser pga. for lange felter: ret teksten og kør igen. Output er en `.xlsx` med teksterne i række 2, live LEN-formler, røde farveregler og auto-tilpassede kolonne-bredder — klar til kunde-review.

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

- Regenerer template: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/annoncetekster-v2/build-template.py` (kun når kolonnelayout ændrer sig).
- `fill-sheet.py` og `build-template.py` deler kolonne-kortet implicit; hvis du ændrer layoutet i `build-template.py`, opdater celle-listerne i `fill-sheet.py` tilsvarende.
- Skrive-reglerne i `references/headline-craft.md` skal re-checkes hvis Google ændrer disapproval-policy eller Ad Strength-vægtning. Kilder med tal-driven evidens (Optmyzr-studiet) må ikke være over 12 måneder gamle uden ny verifikation.
