---
name: annonce-optimering
description: Diagnosticer en kundes LIVE Google Ads RSA-opsætning efter annoncerne har kørt - asset-hygiejne, ikke profit-dom. Tjekker RSA-dækning per ad group (champion-challenger), finder dødvægt-assets der aldrig serveres, og udleder vinkel-huller der fødes tilbage i annoncetekster-v2 som gap-brief. Læser kun aktive kampagner via Google Ads MCP, anbefaler kun (skriver aldrig til kontoen). Aflever en farvekodet .xlsx. Brug når brugeren siger "optimer annoncer", "annonce-optimering", "tjek RSA-opsætning", "asset-hygiejne", "hvilke headlines virker", "post-launch RSA-tjek", eller vil lukke loopet efter annoncetekster. Svarer på dansk.
---

# annonce-optimering

Diagnosticer en kundes **live** Google Ads RSA-opsætning efter annoncerne er importeret og har kørt. Skillet er bevidst en **asset-hygiejne-diagnose**, ikke en profit-klassifikator: det rapporterer strukturelle fakta (RSA-dækning, dødvægt-assets, vinkel-huller) der er sande uden statistisk signifikans, og det udleder et **gap-brief** der fødes direkte tilbage i `annoncetekster-v2`. Hele forløbet og alt output er på dansk.

## Hvorfor skillet er formet sådan (læs én gang — det er ikke til forhandling)

Den oprindelige idé var en firefelts-matrix (Winners / Hidden Gems / Money Pits / Losers) baseret på per-asset CTR×CVR. **En live-test mod faktiske Inbound-konti (2026-05-29) viste at den matrix ikke kan bygges ærligt:**

1. **`performance_label` er reelt altid `NOT_APPLICABLE` eller `PENDING`** på Inbounds konti — aldrig BEST/GOOD/LOW. Selv en asset med 55.865 impressions fik PENDING. Inbounds konti (små danske annoncører) når ikke det volumen Google kræver. Labelen kan derfor ikke være primær-signal.
2. **Per-asset CTR/CVR er konfunderet.** En RSA serverer ~3 headlines + 2 descriptions per impression, og samme klik/konvertering tilskrives ALLE serverede assets. Det gav umulige tal som 39 klik / 57 impr = 68% CTR. En svag headline ved siden af en vinder ser ud som en vinder. Plus: konverteringer på 0/1/2 per asset er under signifikans.

Derfor: skillet dømmer **aldrig** en asset på dens konverteringsrate. Det rapporterer det der holder uden signifikans — dækning og struktur — og er ærligt om hvad data ikke kan svare på.

## Hvad skillet leverer (og hvad det IKKE gør)

**Det gør:**
- Tæller aktive RSA per ad group → flag ad groups med <2 (byg en challenger).
- Finder dødvægt-assets (aldrig serveret / næsten-nul impressions) → kandidater til at skære.
- Klassificerer serverede assets på vinkel-type og finder vinkler uden serveret asset → **gap-brief** til `annoncetekster-v2`.
- Viser Googles `performance_label` KUN når den er BEST/GOOD/LOW; ellers "Google har ikke nok data endnu".

**Det gør IKKE:**
- Dømmer ikke assets på CVR (konfunderet + under signifikans). En valgfri CVR-indikation vises kun bag en hård signifikans-tærskel; ellers "utilstrækkelig data".
- Skriver/redigerer/pauser aldrig på kontoen. Alt er anbefalinger (human-in-the-loop hard rule).
- Vurderer aldrig pausede kampagner/annoncer (bevidste — ekskluderes, flages aldrig som negativt fund).

## How it works (architecture — read once)

En **læse-skill**: henter per-asset data via Google Ads MCP (`run_custom_gaql`), bygger en farvekodet `.xlsx` fra `build-sheet.py` (openpyxl), og gemmer den til Drive (connector) eller lokalt. Samme xlsx-mekanik som `search-terms` og `annoncetekster` — ingen `gws`, ingen Sheets-API, kører i Cowork OG lokalt.

**Runs on any machine.** Eneste forudsætning er Python 3 med `pip`. `build-sheet.py` self-bootstrapper openpyxl hvis det mangler. Drive-connector kræves kun hvis der gemmes til Drive; lokal gem kræver kun Python.

## Trin 0 — Kontekst

Læs `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` før noget andet (write-gate, sprogpolitik). At gemme filen er en ekstern write — gated bag eksplicit bekræftelse.

**Sprog: alt på dansk** — intake-spørgsmål, statusbeskeder, output-tabellen, næste-skridt. Skift kun til engelsk hvis brugeren skriver på engelsk.

**Forudsætning:** dette skill kræver Google Ads MCP + et `customer_id`. Hvis MCP ikke er tilgængelig: sig det og stop — der er ikke et meningsfuldt fallback (modsat `annoncetekster`, der kan køre på landingsside alene).

## Trin 1 — Intake (få AskUserQuestion-kald)

Brug `AskUserQuestion`. Udled så meget som muligt fra samtalen først. Saml felter i ét kald:

1. **Klient + `customer_id`** — bekræft hvis allerede nævnt; ellers spørg. Hvis brugeren kun har klientnavn, brug `list_accessible_accounts` til at finde id'et, og bekræft.
2. **Analysevindue** — default sidste 30 dage. Vis `Sidste 30 dage (Anbefalet)`, `Sidste 90 dage`, `Andet` (fri tekst). **VIGTIGT:** `LAST_90_DAYS` er IKKE et gyldigt GAQL-literal. For alt over 30 dage: beregn `BETWEEN '<YYYY-MM-DD>' AND '<YYYY-MM-DD>'`. Kun `LAST_30_DAYS` (og enkelte andre) virker som literal.
3. **Gem-destination** — `Drive (klientens mappe)`, `Lokalt (.xlsx)`, eller begge. Begge er eksterne writes hvis Drive vælges — bekræft én gang før gem.

Sample-floor (`MIN_IMPRESSIONS`): default **50**. Vises i Oversigt så brugeren ved hvad der blev ekskluderet som dødvægt. Nævn defaulten; brugeren kan overstyre.

## Trin 2 — Hent per-asset data (GAQL, kun ENABLED)

Brug `run_custom_gaql`. Hård regel: kun ENABLED kampagner OG annoncer (pausede er bevidste — ekskluderes, flages aldrig).

```sql
SELECT
  campaign.name,
  ad_group.name,
  ad_group_ad_asset_view.field_type,
  ad_group_ad_asset_view.performance_label,
  asset.text_asset.text,
  metrics.impressions,
  metrics.clicks,
  metrics.conversions,
  metrics.cost_micros
FROM ad_group_ad_asset_view
WHERE campaign.status = 'ENABLED'
  AND ad_group_ad.status = 'ENABLED'
  AND segments.date DURING LAST_30_DAYS
```

For et vindue over 30 dage: erstat `DURING LAST_30_DAYS` med `BETWEEN '<start>' AND '<end>'` (beregnede datoer — `LAST_90_DAYS` virker ikke).

**Verificeret feltform (live, 2026-05-29):** `ad_group_ad_asset_view.field_type` = `HEADLINE`/`DESCRIPTION`; `performance_label` returnerer typisk `NOT_APPLICABLE`/`PENDING` (sjældent BEST/GOOD/LOW); per-asset `clicks`/`conversions`/`cost_micros`/`impressions` kommer alle tilbage. `cost_micros` er micros → DKK = `cost_micros / 1_000_000`.

For at tælle RSA per ad group (champion-challenger), kør en let separat query:

```sql
SELECT campaign.name, ad_group.name, ad_group_ad.ad.id
FROM ad_group_ad
WHERE campaign.status = 'ENABLED'
  AND ad_group_ad.status = 'ENABLED'
  AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
```

Tæl distinkte ad-id'er per (kampagne, ad group).

## Trin 3 — Klassificér (struktur, ikke profit)

For hver asset, beregn `status`:
- **DOEDVAEGT** — impressions under `MIN_IMPRESSIONS` (eller 0). Et dæknings-faktum, ikke en CVR-dom.
- **FOR_NY** — `performance_label` er `LEARNING` eller `PENDING` OG impressions er lave. "Google lærer stadig — rør ikke endnu."
- **AKTIV** — serveres med rimeligt volumen.

For hver asset, udled `vinkel` (benefit / trust / urgency / CTA / feature / keyword-led / brand / location / garanti — samme taksonomi som `annoncetekster-v2/references/headline-craft.md`). Brug asset-teksten.

Per ad group: hvilke vinkler har INGEN serveret asset? Det er `manglende_vinkler` → fødes til gap-brief.

`google_label`: behold rå-værdien; `build-sheet.py` viser den kun hvis den er BEST/GOOD/LOW, ellers "Google har ikke nok data endnu".

`cvr_hint`: lad den være tom MEDMINDRE en asset overstiger en hård signifikans-tærskel (fx ≥100 impressions OG ≥10 konverteringer — på næsten alle Inbound-konti vil ingen asset nå det, og det er ærligt). Når tom → scriptet skriver "utilstrækkelig data".

**Anbefalinger er recommend-only.** Eksempler: "Aldrig serveret — kandidat til at skære." / "Kun 1 RSA i denne ad group — byg en challenger." / "Mangler en CTA-vinkel — tilføj i næste runde." Aldrig "fjern denne" som en kommando; altid som forslag til mennesket.

## Trin 4 — Byg gap-brief'et (det der lukker loopet)

Saml `manglende_vinkler` per ad group til en `gap_brief`-liste. For hver: et konkret `forslag` til hvilke challenger-headlines `annoncetekster-v2` skal skrive. Det er her build→operate→iterate-loopet lukkes: outputtet fra dette skill er inputtet til næste `annoncetekster-v2`-kørsel.

## Trin 5 — Skriv analysis.json og byg arket

Skriv en `analysis.json` efter skemaet i toppen af `build-sheet.py` (felter: `client`, `account_id`, `period`, `scope`, `min_impressions`, `method_notes`, `ad_groups`, `assets`, `gap_brief`).

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/annonce-optimering/build-sheet.py \
  --in analysis.json \
  --out "Annonce-optimering - <klient> - <YYYY-MM-DD>.xlsx"
```

Output: en `.xlsx` med fire faner — **Oversigt** (med en ærligheds-banner om hvad rapporten er/ikke er), **Ad group-dækning** (challenger-flag + manglende vinkler), **Assets** (status-farvet, label-maskeret), **Gap-brief** (til annoncetekster-v2).

## Trin 6 — Gem (write — gated)

Bed om eksplicit bekræftelse én gang før du skriver (dækker både lokal og Drive).

- **Lokal:** `build-sheet.py` har allerede skrevet `.xlsx` til disk.
- **Drive:** upload via connector `create_file`:
  - `title`: `Annonce-optimering - <klient> - <YYYY-MM-DD>`
  - `parentId`: klientens mappe under `${user_config.inbound_root_folder_id}` hvis den kan resolves; ellers Drive-rod (nævn at den kan flyttes).
  - `contentMimeType`: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
  - `base64Content`: base64 af `.xlsx`-filen

## Trin 7 — Output

Lever:
1. **Lokal sti** + **Drive-link** (hvis uploadet).
2. **Kort opsummering:** antal ad groups uden challenger, antal dødvægt-assets, og de vigtigste vinkel-huller.
3. **Det ærlige forbehold:** "Rapporten er strukturel hygiejne — den dømmer ikke assets på konverteringsrate, fordi Google-data på disse konti er for tyndt og per-asset-metrics er konfunderede."
4. **Loop-tilbagekobling:** "Gap-brief'et kan fødes direkte ind i `annoncetekster-v2` til at skrive challenger-headlines."
5. **Næste skridt (manuelt, human-in-the-loop):** brugeren beslutter hvilke assets der skæres/bygges; skillet rører aldrig kontoen.
6. **Datakilder:** Google Ads MCP (`run_custom_gaql`, `ad_group_ad_asset_view` + `ad_group_ad`), vindue brugt.

## Eksempel-output

```
Annonce-optimering klar: Annonce-optimering - Dansk Studie Center - 2026-05-29
Lokal: /Users/carl/work/Annonce-optimering - Dansk Studie Center - 2026-05-29.xlsx
Drive: https://docs.google.com/.../<file id>

- 3 ad groups har kun 1 RSA -> byg en challenger i hver.
- 7 assets er dødvægt (under 50 impressions i perioden) -> kandidater til at skære.
- Vinkel-huller: 'Hojskole udland' mangler en CTA + urgency; 'Sabbataar' er fuldt dækket.

Forbehold: strukturel hygiejne. Ingen CVR-dom - Google-label er PENDING/NOT_APPLICABLE
på kontoen, og per-asset-metrics er konfunderede.

Gap-brief'et er klar til at fodre annoncetekster-v2's næste challenger-runde.
Næste: du beslutter hvad der skæres/bygges. Skillet rører aldrig kontoen.
```

## Maintenance

- `build-sheet.py` self-bootstrapper openpyxl; kør lokalt for at smoke-teste mod en `analysis.json`.
- Hvis Google begynder at tildele BEST/GOOD/LOW på Inbounds konti (højere volumen i fremtiden), kan signifikans-gaten i Trin 3 løsnes — men kun efter en ny live-verifikation, ikke på antagelse.
- Feltformen for `ad_group_ad_asset_view` blev verificeret live 2026-05-29; re-verificér hvis Google ændrer API-versionen.
