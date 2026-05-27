---
name: annoncetekster
description: Lav Google Ads-annoncetekster (Responsive Search Ads) ud fra en kundes landingsside og aflever dem i et Google Ads Editor-klart regneark, med kampagnenavn bygget efter Inbounds navngivningskonvention (IC | NETVÆRK | Maalretning | Kampagnenavn | Eventuelt for Search/Shopping/pMax, IC | FORMAT | KAMPAGNENAVN | MÅLRETNING for Display/YT/DG, YYYY-MD - IC - Audience type - Audience navn for Audiences). Analyserer landingssiden, skriver 15 overskrifter + 4 beskrivelser + 2 stier inden for Googles tegngraenser, og bygger en frisk .xlsx fra en indbygget skabelon med live tegntaelling og roede advarsler naar en tekst bliver for lang. Bruger ALTID AskUserQuestion til intake med forslag baseret paa konventionen — brugeren kan overstyre. Gemmer i Drive (brugeren vaelger mappen) eller lokalt. Svarer altid paa dansk. Brug naar brugeren siger "lav annoncetekster til [kunde]", "RSA til [landingsside]", "lav et annonce-ark", "responsive search ad", eller "tekster ud fra landingsside".
---

# annoncetekster

Lav Google Ads-annoncetekster (Responsive Search Ads) ud fra en kundes landingsside, og aflever dem i et regneark der kan importeres direkte i Google Ads Editor. Hele forloebet og alt output er paa dansk.

## Why this skill exists

The ads team turns a client's landing page into RSA ad copy, fills a sheet, sends it to the client for review, then imports the corrected sheet into Google Ads Editor. The slow, skilled part is the landing-page analysis + copywriting under hard character limits. The risky part is the client editing a headline too long and it sneaking back over-length. This skill automates the copywriting and ships a sheet with live char-count + red color-code so over-length text is caught the moment the client types it.

## When to use

Trigger phrases: "lav annoncetekster", "RSA til", "annonce-ark", "responsive search ad", "tekster til [klient]", "annoncetekster ud fra landingsside".

## How it works (architecture — read once)

A **new file is built from scratch every run** from a bundled `.xlsx` template — there is no cloning of any remote sheet and no cell-editing of an existing file.

- The template lives at `${CLAUDE_PLUGIN_ROOT}/skills/rsa-copy/template.xlsx`. It holds the full Google Ads Editor column layout, a live `=LEN()` formula beside every text field, and red conditional-formatting rules (headline LEN > 30, description LEN > 90, path LEN > 15). Because these live in the `.xlsx` layer (not in CSV values), they survive upload to Drive and stay live when the client edits the sheet. Verified: uploading a filled `.xlsx` via the Drive connector keeps `=LEN()` computing.
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

This IS the Google Ads Editor import schema. Header row 1, single data row 2. Every text column is followed by a `LEN` column. Pre-seeded: `Ad type = "Responsive search ad"`. `Campaign`-cellen overskrives ved hver koersel med det navn brugeren bekraefter i Trin 1.

```
Campaign | Ad Group | Ad type | Labels |
Headline 1 | LEN | ... | Headline 15 | LEN |
Description 1 | LEN | ... | Description 4 | LEN |
Path 1 | LEN | Path 2 | LEN |
Final URL | Final mobile URL
```

## Trin 0 — Kontekst

Laes `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` foer noget andet. Den indeholder write-gate-reglerne og sprogpolitikken. At gemme filen (til Drive eller lokalt) er en ekstern write — gated bag eksplicit bekraeftelse.

**Sprog: alt foregaar paa dansk** — spørgsmål i intake, statusbeskeder, output-tabellen og naeste-skridt. Skift kun til engelsk hvis brugeren skriver til dig paa engelsk eller udtrykkeligt beder om det. Selve annonceteksterne skrives ogsaa paa dansk (se Trin 3).

## Hard rule — brug ALTID AskUserQuestion til intake

Hvert intake-felt (klientnavn, landingsside, netvaerk/format, maalretning, kampagnenavn, ad group, gem-destination) skal spoerges via `AskUserQuestion` med konkrete forslag som options. Gaet aldrig vaerdier. Hvis du har et logisk default, vis det som **foerste option** med `(Anbefalet)` i label — brugeren kan altid vaelge "Other" og skrive sin egen vaerdi.

Grunden: vi vil bygge muskelhukommelse om Inbounds navngivningskonvention og fange afvigelser (fx pMax i stedet for GSN, brand-kampagne i stedet for generic) foer arket genereres. Friform-input giver inkonsistente kampagnenavne som senere skal renses i Editor.

## Trin 1 — Intake (eet AskUserQuestion ad gangen)

Spoerg i denne raekkefoelge. Hvert trin er et separat `AskUserQuestion`-kald.

1. **Klientnavn** — fri tekst via AskUserQuestion (én option `(Anbefalet)` hvis konteksten allerede har et klientnavn fra samtalen, ellers bare "Other"). Bruges i fil-titlen og som `Eventuelt`-feltet i kampagnenavnet.
2. **Landingsside-URL** — fri tekst. Hvis brugeren har naevnt en URL tidligere i samtalen, foreslå den som første option.
3. **Kampagnetype** — bestemmer hvilken navngivningsskabelon der bruges. Options:
   - Search / Shopping / pMax  — skabelon: `IC | NETVÆRK | Målretning | Kampagnenavn | Eventuelt`
   - Display / YouTube / Demand Gen — skabelon: `IC | FORMAT | KAMPAGNENAVN | MÅLRETNING`
   - Audience — skabelon: `YYYY-MD - IC - Audience type - Audience navn`
4. **Netvaerk / Format** — afhaenger af kampagnetype (se "Navngivnings-skabelon" nedenfor).
5. **Maalretning** — afhaenger af kampagnetype.
6. **Kampagnenavn / produkt** — det specifikke produkt eller tema (fx "Alarmsystemer", "Bliv groennere sammen", "Gratis introforloeb").
7. **Eventuelt** (kun Search/Shopping/pMax, valgfrit) — fx brandnavn "Securitas". Vis "(ingen)" som første option.
8. **Foreslået kampagnenavn** — saml svarene til en streng efter den valgte skabelon, og vis den som første option `(Anbefalet)` i et sidste `AskUserQuestion`. Brugeren bekraefter eller skriver et frit alternativ via "Other".
9. **Ad group-navn** (valgfrit) — default tom (foerste option: `(tom)`).
10. **Gem hvor?** — to options:
    - **Drive** — efterfoelgende `AskUserQuestion` om destinationsmappe (foreslå klientnavn → kendt mappe under `${user_config.inbound_root_folder_id}` hvis muligt).
    - **Lokalt** — efterfoelgende `AskUserQuestion` om sti (default cwd som foerste option).

Bekraeft det samlede scope (klient, URL, kampagnenavn, gem-destination) i én tekstbesked foer du gaar til Trin 2.

## Navngivnings-skabelon — byg kampagnenavnet

Saml svarene efter den skabelon som matcher kampagnetypen. Vis ALTID resultatet til brugeren via et `AskUserQuestion` med strengen som foerste option `(Anbefalet)` — brugeren kan overstyre.

### Search / Shopping / pMax
Skabelon: `IC | NETVÆRK | Målretning | Kampagnenavn | Eventuelt`

| Felt | Mulige vaerdier (vis som options) |
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

| Felt | Mulige vaerdier |
|---|---|
| FORMAT | `GDN` (Google Display Network), `YT` (YouTube), `DG` (Demand Gen) |
| KAMPAGNENAVN | fri tekst (kampagne/tema) |
| MÅLRETNING | `Reach`, `Retargeting`, `Awareness`, `Consideration`, `Conversion` (eller fri tekst via "Other") |

Eksempler:
- `IC | GDN | Webinarer | Reach`
- `IC | YT | Bliv groennere sammen | Retargeting`
- `IC | DG | Gratis introforloeb | Retargeting`

### Audience
Skabelon: `YYYY-MD - IC - Audience type - Audience navn`

| Felt | Vaerdi |
|---|---|
| YYYY-MD | Indeværende år + maaned uden ledende nul (fx `2025-1`, ikke `2025-01`). Brug dagens dato som default. **Bemærk:** eksemplerne fra Inbound bruger `2025-01` med ledende nul — spoerg brugeren om begge varianter via AskUserQuestion. |
| Audience type | `Custom Intent`, `Retargeting`, `Affinity`, `In-Market`, `Similar`, `Lookalike` (eller fri tekst) |
| Audience navn | fri tekst (fx "Søgninger paa HR system", "Alle besøgende") |

Eksempler:
- `2025-01 - IC - Custom Intent - Søgninger paa HR system`
- `2025-01 - IC - Retargeting - Alle besøgende`

## Trin 2 — Analyser landingssiden

Scrape URL'en med Firecrawl. Udtraek: produkt/ydelse, USP'er, tone, CTA'er, trust-signaler (anmeldelser, garantier, certificeringer), pris/tilbud, brandnavn. Hvis siden ikke kan hentes: sig det og stop — vi opfinder ikke claims.

## Trin 3 — Generer copy (med laengde-selvtjek)

Producer:
- **15 headlines** (<= 30 tegn), **4 descriptions** (<= 90 tegn), **2 paths** (<= 15 tegn).

Variér headlines paa vinkel saa Google har reelt materiale at teste: USP, pris/tilbud, trust, CTA, brand, feature, lokation. Descriptions skal kunne staa alene to og to.

**Regler:**
- Kun claims der staar paa landingssiden. Ingen opfundne tal, garantier eller priser.
- **Annonceteksterne skrives paa dansk** (medmindre landingssiden tydeligt er paa et andet sprog — saa matcher du sidens sprog).
- **Laengde-selvtjek:** for hver streng, taeel tegn. Skriv om enhver headline > 30, description > 90 eller path > 15 INDEN du gaar videre. `fill-sheet.py` afviser desuden at skrive hvis noget er for langt — men ret det her foerst.

Skriv copy'en til en `copy.json`. Brug det kampagnenavn brugeren bekraeftede i intake (Trin 1, punkt 8):
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

## Trin 4 — Byg arket

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/rsa-copy/fill-sheet.py \
  --copy copy.json \
  --out "RSA - <klient> - <YYYY-MM-DD>.xlsx"
```

Hvis scriptet afviser pga. for lange felter: ret copy'en og koer igen. Output er en `.xlsx` med teksterne i raekke 2, live LEN-formler, og roede farveregler — klar til kunde-review.

## Trin 5 — Gem (write — gated)

Foreslaa gem-handlingen, vent paa bekraeftelse.

**Drive:** upload `.xlsx` via Drive-connector `create_file`:
- `title`: `RSA - <klient> - <YYYY-MM-DD>`
- `parentId`: mappen fra intake
- `contentMimeType`: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- `base64Content`: base64 af `.xlsx`-filen

Filen lander som en redigerbar Office-mode-fil i Drive. `=LEN()`-formler regner live, og farvereglerne virker — bekraeftet ved test.

**Lokalt:** filen er allerede skrevet af `fill-sheet.py` til den valgte sti. Bekraeft stien.

## Trin 6 — Output

Lever:
1. **Link til Drive-filen** (eller den lokale sti).
2. **En tabel** med alle 19 strenge + tegnantal, saa brugeren ser alt er sikkert.
3. **Naeste skridt (manuelt, human-in-the-loop):** del filen med kunden til review (skillen deler IKKE selv), og efter kundens rettelser: importer arket i Google Ads Editor.

Del aldrig filen med kunden automatisk. Send aldrig nogen mail. Praesenter linket — Carl/brugeren videresender.

## Eksempel-output

```
Annonce-ark klar: RSA - Nordkap Friluft - 2026-05-27
Gemt i Drive: https://docs.google.com/.../<file id>

| # | Headline | Tegn |
|---|---|---|
| 1 | Gratis fragt over 499 kr | 24 |
| 2 | Friluftsudstyr i topkvalitet | 28 |
| ... | ... | ... |

| # | Description | Tegn |
|---|---|---|
| 1 | Stort udvalg af telte, soveposer og rygsaekke til enhver tur. Hurtig levering. | 78 |
| ... | ... | ... |

Paths: friluft (7) udstyr (6) | Final URL: https://nordkapfriluft.dk/outdoor

Alle felter inden for graensen. LEN-formler + conditional formatting aktiv — kundens for lange rettelser bliver roede live.
Naeste: del med kunden til review, importer derefter i Google Ads Editor.
```

## Maintenance

- Regenerer template: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/rsa-copy/build-template.py` (kun naar kolonnelayout aendrer sig).
- `fill-sheet.py` og `build-template.py` deler kolonne-kortet implicit; hvis du aendrer layoutet i `build-template.py`, opdater celle-listerne i `fill-sheet.py` tilsvarende.
