---
name: rsa-copy
description: Turn a client landing page into Google Ads Responsive Search Ad copy in an Editor-ready spreadsheet. Builds a fresh .xlsx from a bundled template that carries live char-count formulas and red over-length color rules, fills 15 headlines + 4 descriptions + 2 paths under Google's hard limits, and saves it to Drive (user picks the folder) or locally. Use when the user says "lav annoncetekster til [klient]", "RSA til [landingsside]", "lav et annonce-ark", "responsive search ad copy", or "tekster ud fra landingsside".
---

# rsa-copy

Generate Google Ads Responsive Search Ad (RSA) copy from a client landing page and deliver it in a spreadsheet that imports into Google Ads Editor.

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

This IS the Google Ads Editor import schema. Header row 1, single data row 2. Every text column is followed by a `LEN` column. Pre-seeded: `Campaign = "IC | GSN | Generic |"`, `Ad type = "Responsive search ad"`.

```
Campaign | Ad Group | Ad type | Labels |
Headline 1 | LEN | ... | Headline 15 | LEN |
Description 1 | LEN | ... | Description 4 | LEN |
Path 1 | LEN | Path 2 | LEN |
Final URL | Final mobile URL
```

## Trin 0 — Kontekst

Laes `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` foer noget andet. Den indeholder write-gate-reglerne og sprogpolitikken. At gemme filen (til Drive eller lokalt) er en ekstern write — gated bag eksplicit bekraeftelse.

## Trin 1 — Intake (eet spoergsmaal ad gangen)

1. **Klientnavn** — bruges i fil-titlen.
2. **Landingsside-URL** — den side teksterne skal afspejle.
3. **Kampagnenavn** — default `IC | GSN | Generic |`. Tilbyd default, lad brugeren overstyre.
4. **Ad group-navn** (valgfrit) — default tom.
5. **Gem hvor?** — to valg:
   - **Drive** — spoerg om destinationsmappe (mappenavn eller -ID, eller klientnavn der mapper til en kendt klientmappe under `${user_config.inbound_root_folder_id}`). Brug det som `parentId`.
   - **Lokalt** — spoerg om sti (default cwd). Filen skrives til disk.

Bekraeft scope foer du fortsaetter.

## Trin 2 — Analyser landingssiden

Scrape URL'en med Firecrawl. Udtraek: produkt/ydelse, USP'er, tone, CTA'er, trust-signaler (anmeldelser, garantier, certificeringer), pris/tilbud, brandnavn. Hvis siden ikke kan hentes: sig det og stop — vi opfinder ikke claims.

## Trin 3 — Generer copy (med laengde-selvtjek)

Producer:
- **15 headlines** (<= 30 tegn), **4 descriptions** (<= 90 tegn), **2 paths** (<= 15 tegn).

Variér headlines paa vinkel saa Google har reelt materiale at teste: USP, pris/tilbud, trust, CTA, brand, feature, lokation. Descriptions skal kunne staa alene to og to.

**Regler:**
- Kun claims der staar paa landingssiden. Ingen opfundne tal, garantier eller priser.
- Dansk, medmindre landingssiden er paa et andet sprog.
- **Laengde-selvtjek:** for hver streng, taeel tegn. Skriv om enhver headline > 30, description > 90 eller path > 15 INDEN du gaar videre. `fill-sheet.py` afviser desuden at skrive hvis noget er for langt — men ret det her foerst.

Skriv copy'en til en `copy.json`:
```json
{
  "campaign": "IC | GSN | Generic |",
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
