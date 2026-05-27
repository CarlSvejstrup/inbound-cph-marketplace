---
name: rsa-copy
description: Turn a client landing page into Google Ads Responsive Search Ad copy in an Editor-ready Google Sheet. Clones Inbound's real RSA template (so live char-count formulas and red over-length color rules survive), fills 15 headlines + 4 descriptions + 2 paths that respect Google's hard limits, and returns a client-ready sheet link. Use when the user says "lav annoncetekster til [klient]", "RSA til [landingsside]", "lav et annonce-ark", "responsive search ad copy", or "tekster ud fra landingsside".
---

# rsa-copy

Generate Google Ads Responsive Search Ad (RSA) copy from a client landing page and deliver it in a spreadsheet that imports straight into Google Ads Editor.

## Why this skill exists

The ads team turns a client's landing page into RSA ad copy, fills a template sheet, sends it to the client for review, then imports the corrected sheet into Google Ads Editor. The slow, skilled part is the landing-page analysis + copywriting under hard character limits. The risky part is the client editing a headline too long and it sneaking back over-length. This skill automates the copywriting and keeps the live char-count + red color-code so over-length text is caught the moment the client types it.

## When to use

Trigger phrases: "lav annoncetekster", "RSA til", "annonce-ark", "responsive search ad", "tekster til [klient]", "annoncetekster ud fra landingsside".

## Runtime — read first

This is a **local-run skill**. It needs two things on the machine it runs on:

1. The Google Drive connector (to clone the template).
2. The `gws` CLI (the `gws-sheets` skill, binary `gws`) authed to a Google account that can **read and write the cloned sheet**.

**Account note (important):** Inbound's RSA template is owned by `csc@inboundcph.dk`. If `gws` is authed as a different account (e.g. a personal Gmail), it gets a 403 on the Inbound-owned sheet. Before writing cells, confirm the `gws` account can reach the clone. If it cannot, use the fallback in Trin 5b.

If neither tool is present (e.g. running inside the Cowork in-app runtime), say so and stop: "rsa-copy koerer lokalt — den skal bruge `gws` CLI og Drive-connector. Koer den fra Carls maskine."

## Hard limits (Google rejects over-length, it does not truncate)

| Field | Max chars |
|---|---|
| Headline (x15) | 30 |
| Description (x4) | 90 |
| Path (x2) | 15 |

## The template + its column contract

Template Google Sheet: `17kvou0GmIDZtKGloOvLBwRsMZW95sHXXvIFkEJ6SjRI`.

This IS the Google Ads Editor import schema. Header row 1, single data row 2. Every text column is followed by a `LEN` column holding a live `=LEN()` formula. Never write into a LEN column — those stay formula-driven.

Exact A1 column map (data row = row 2):

| Field | Cell | Field | Cell |
|---|---|---|---|
| Campaign | A2 | Headline 8 | S2 |
| Ad Group | B2 | Headline 9 | U2 |
| Ad type | C2 | Headline 10 | W2 |
| Labels | D2 | Headline 11 | Y2 |
| Headline 1 | E2 | Headline 12 | AA2 |
| Headline 2 | G2 | Headline 13 | AC2 |
| Headline 3 | I2 | Headline 14 | AE2 |
| Headline 4 | K2 | Headline 15 | AG2 |
| Headline 5 | M2 | Description 1 | AI2 |
| Headline 6 | O2 | Description 2 | AK2 |
| Headline 7 | Q2 | Description 3 | AM2 |
| | | Description 4 | AO2 |
| Path 1 | AQ2 | Path 2 | AS2 |
| Final URL | AU2 | Final mobile URL | AV2 |

The columns in between (F, H, J, ...) are the LEN columns — skip them. `Campaign` defaults to `IC | GSN | Generic |` and `Ad type` is always `Responsive search ad` (both pre-seeded in the template; reuse, do not overwrite unless the user gives a different campaign name).

## Trin 0 — Kontekst

Laes `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` foer noget andet. Den indeholder write-gate-reglerne og sprogpolitikken. Hver Drive-klon og hver celle-skrivning er en ekstern write — alle er gated bag eksplicit bekraeftelse.

## Trin 1 — Intake (eet spoergsmaal ad gangen)

1. **Klientnavn** — bruges i ark-titlen.
2. **Landingsside-URL** — den side teksterne skal afspejle.
3. **Kampagnenavn** — default `IC | GSN | Generic |`. Tilbyd default, lad brugeren overstyre.
4. **Ad group-navn** (valgfrit) — default tom.

Bekraeft scope foer du fortsaetter.

## Trin 2 — Analyser landingssiden

Scrape URL'en med Firecrawl. Udtraek: produkt/ydelse, USP'er, tone, CTA'er, trust-signaler (anmeldelser, garantier, certificeringer), pris/tilbud, brandnavn. Hvis siden ikke kan hentes: sig det og stop — vi opfinder ikke claims.

## Trin 3 — Generer copy (med laengde-selvtjek FOER skrivning)

Producer:
- **15 headlines** (<= 30 tegn), **4 descriptions** (<= 90 tegn), **2 paths** (<= 15 tegn).

Variér headlines paa vinkel saa Google har reelt materiale at teste: USP, pris/tilbud, trust, CTA, brand, feature, lokation. Descriptions skal kunne staa alene to og to.

**Regler:**
- Kun claims der staar paa landingssiden. Ingen opfundne tal, garantier eller priser.
- Dansk, medmindre landingssiden er paa et andet sprog.
- **Laengde-selvtjek:** for hver streng, taeel tegn. Enhver headline > 30, description > 90 eller path > 15 skrives om INDEN den skrives til arket. Print en tabel med alle strenge + tegnantal saa brugeren ser de er sikre.

## Trin 4 — Klon skabelonen (write — gated)

Foreslaa klonen, vent paa bekraeftelse, klon saa via Drive-connector `copy_file`:
- `fileId`: `17kvou0GmIDZtKGloOvLBwRsMZW95sHXXvIFkEJ6SjRI`
- `title`: `RSA - <klient> - <YYYY-MM-DD>`
- `parentId`: klientens arbejdsmappe i Drive hvis kendt, ellers udelad (lander i rod).

Klon bevarer LEN-formler og conditional formatting. Notér den nye `spreadsheetId` fra svaret.

## Trin 5 — Skriv copy ind i cellerne (write — gated)

Skriv KUN tekstkolonnerne, aldrig LEN-kolonnerne. Brug `gws sheets spreadsheets values batchUpdate` med ranges fra kolonnekortet ovenfor. `valueInputOption` SKAL vaere `USER_ENTERED` (ellers evaluerer LEN-formlerne ikke mod nye vaerdier korrekt — selve teksten er almindelige strenge, men hold konsistens).

Eksempel (eet kald, alle felter):

```bash
gws sheets spreadsheets values batchUpdate \
  --params '{"spreadsheetId":"<CLONE_ID>"}' \
  --json '{"valueInputOption":"USER_ENTERED","data":[
    {"range":"A2","values":[["IC | GSN | Generic |"]]},
    {"range":"E2","values":[["<headline 1>"]]},
    {"range":"G2","values":[["<headline 2>"]]},
    ... (I2,K2,M2,O2,Q2,S2,U2,W2,Y2,AA2,AC2,AE2,AG2 for headlines 3-15) ...,
    {"range":"AI2","values":[["<description 1>"]]},
    {"range":"AK2","values":[["<description 2>"]]},
    {"range":"AM2","values":[["<description 3>"]]},
    {"range":"AO2","values":[["<description 4>"]]},
    {"range":"AQ2","values":[["<path 1>"]]},
    {"range":"AS2","values":[["<path 2>"]]},
    {"range":"AU2","values":[["<final url>"]]}
  ]}'
```

### Trin 5b — Fallback hvis `gws` ikke kan naa klonen (403)

Hvis `gws`-kontoen ikke ejer/kan skrive klonen (typisk fordi `gws` er authed som personlig Gmail og arket ejes af `csc@inboundcph.dk`):
- Enten: authentificér `gws` som `csc@inboundcph.dk` og koer igen.
- Eller: lever de 19 strenge som en paste-klar blok i chat, og bed brugeren indsaette dem i den klonede skabelon manuelt (formler + farver er bevaret af klonen, saa det er sikkert). Det er stadig hele copywriting-vaerdien — kun indsaettelsen er manuel.

## Trin 6 — Verificér farve-sikkerhed

Laes LEN-kolonnerne tilbage og bekraeft hver er under graensen:

```bash
gws sheets spreadsheets values get \
  --params '{"spreadsheetId":"<CLONE_ID>","range":"A2:AV2","valueRenderOption":"UNFORMATTED_VALUE"}'
```

Hvis skabelonen mangler en conditional-format-regel (test ved at se om en for lang vaerdi bliver roed), tilfoej en via `batchUpdate`. Eksempel for én headline-LEN-kolonne (gentag pr. LEN-kolonne eller daek hele raekken af headline-LEN-kolonner; `sheetId` hentes fra `spreadsheets.get`):

```bash
gws sheets spreadsheets batchUpdate \
  --params '{"spreadsheetId":"<CLONE_ID>"}' \
  --json '{"requests":[{"addConditionalFormatRule":{"rule":{
    "ranges":[{"sheetId":<GID>,"startRowIndex":1,"startColumnIndex":5,"endColumnIndex":6}],
    "booleanRule":{"condition":{"type":"NUMBER_GREATER","values":[{"userEnteredValue":"30"}]},
    "format":{"backgroundColor":{"red":0.96,"green":0.8,"blue":0.8}}}},"index":0}}]}'
```

(Headline-LEN-kolonner bruger graense 30, description-LEN graense 90, path-LEN graense 15.)

## Trin 7 — Output

Lever:
1. **Link til det klonede ark.**
2. **En tabel** med alle 19 strenge + tegnantal, saa brugeren ser alt er sikkert.
3. **Naeste skridt (manuelt, human-in-the-loop):** del arket med kunden til review (skillen deler IKKE selv), og efter kundens rettelser: eksporter arket og importer i Google Ads Editor.

Del aldrig arket med kunden automatisk. Send aldrig nogen mail. Praesenter linket — Carl videresender.

## Eksempel-output

```
Annonce-ark klar: RSA - Nordkap Friluft - 2026-05-27
Link: https://docs.google.com/spreadsheets/d/<CLONE_ID>

| # | Headline | Tegn |
|---|---|---|
| 1 | Gratis fragt over 499 kr | 24 |
| 2 | Friluftsudstyr i topkvalitet | 28 |
| ... | ... | ... |
| 15 | Shop outdoor i dag | 18 |

| # | Description | Tegn |
|---|---|---|
| 1 | Stort udvalg af telte, soveposer og rygsaekke til enhver tur. Hurtig levering. | 78 |
| ... | ... | ... |

Paths: /friluft (8) /udstyr (7) | Final URL: https://nordkapfriluft.dk/outdoor

Alle felter inden for graensen. Conditional formatting aktiv — kundens for lange rettelser bliver roede.
Naeste: del med kunden til review, importer derefter i Google Ads Editor.
```
