---
name: inb-ads-rsa-hygiene
description: Diagnosticerer en klients live Google Ads RSA-opsætning efter annoncerne har kørt og leverer en farvekodet .xlsx med RSA-dækning per ad group, dødvægt-assets og vinkel-huller der fødes tilbage som gap-brief til inb-ads-rsa-copy, alt sammen read-only mod Google Ads MCP uden nogensinde at skrive til kontoen.
---

# inb-ads-rsa-hygiene

Diagnosticer en klients **live** Google Ads RSA-opsætning efter annoncerne er importeret og har kørt. Dette er en **asset-hygiejne-diagnose**, ikke en profit-klassifikator: rapportér strukturelle fakta (RSA-dækning, dødvægt-assets, vinkel-huller) der er sande uden statistisk signifikans, og udled et **gap-brief** der fødes direkte tilbage i `inb-ads-rsa-copy`. Alt output på dansk.

## Baggrund — hvorfor ingen profit-matrix

En tidligere version brugte en firefelts-matrix (Winners / Hidden Gems / Money Pits / Losers) baseret på per-asset CTR×CVR. En live-test mod Inbound-konti (2026-05-29) viste at den ikke kan bygges ærligt:

1. `performance_label` er reelt altid `NOT_APPLICABLE` eller `PENDING` på Inbounds konti — aldrig BEST/GOOD/LOW, selv ved 55.865 impressions. Kontiene (små danske annoncører) når ikke det volumen Google kræver, så labelen kan ikke være primær-signal.
2. Per-asset CTR/CVR er konfunderet: en RSA serverer ~3 headlines + 2 descriptions per impression, og samme klik/konvertering tilskrives alle serverede assets (fx 39 klik / 57 impr = 68% CTR er umuligt at fortolke). Konverteringer på 0-2 per asset er under signifikans.

Derfor dømmer skillet aldrig en asset på konverteringsrate. Det rapporterer kun det der holder uden signifikans: dækning og struktur.

## Hvad skillet gør / ikke gør

**Gør:**
- Tæller aktive RSA per ad group → flager ad groups med <2 (byg en challenger).
- Finder dødvægt-assets (aldrig serveret / næsten-nul impressions) → kandidater til at skære.
- Klassificerer serverede assets på vinkel-type og finder vinkler uden serveret asset → gap-brief til `inb-ads-rsa-copy`.
- Klassificerer hver asset som DØDVÆGT / FOR NY / AKTIV ud fra `MIN_IMPRESSIONS`.

**Gør ikke:**
- Dømmer ikke assets på CVR (se Baggrund). Google-label og CVR-indikation vises ikke i arket — på Inbounds konti er de altid identiske og dermed støj; må bruges internt i status-logikken, men er ikke en kolonne.
- Skriver/redigerer/pauser aldrig på kontoen — alt er anbefalinger.
- Vurderer aldrig pausede kampagner/annoncer — de er bevidste, ekskluderes, og flages aldrig som negativt fund.

## Architecture

En læse-skill: henter per-asset data via Google Ads MCP (`run_custom_gaql`), bygger en farvekodet `.xlsx` via `build-sheet.py` (openpyxl, self-bootstrapper), og gemmer den til Drive (connector) eller lokalt. Samme xlsx-mekanik som `inb-ads-search-term-analyse`. Ingen `gws`, ingen Sheets-API — kører i Cowork og lokalt; eneste forudsætning er Python 3 med `pip`.

## Trin 0 — Hent klient-kontekst (AI Context) FØRST

Kør `../../shared/client-context-intake.md` som allerførste trin — før det første Google Ads MCP-kald. Det er en læsning (aldrig gated), men obligatorisk: sådan arver du ID'er, kontakter, hårde rammer, navngivningskonvention, budstrategi-norm, KPI'er og pausede-kampagners-intention i stedet for at diagnosticere blindt. Den fil holder også opslaget i master-klientindekset, reglen om delte Drive-mapper (Lime, Retriever/Infomedia, GSGroup, Nemco, Julemærket, PhoneAlone, DI → vælg rækken for det specifikke marked) og fallback når en klient endnu ikke har en AI Context-fil.

Fire ting i AI Context'en styrer direkte hvad du må flage og hvor hårdt du må anbefale — hav dem i hovedet, når du klassificerer i Trin 3 og formulerer anbefalinger:
- **Hårde rammer** — afgrænser hvad du overhovedet må røre/anbefale.
- **Budstrategi-norm** — tCPA/tROAS/manuel afgør om "for ny / Google lærer" er forventet, og hvordan dødvægt-anbefalinger formuleres.
- **Pausede-kampagners-intention** — bekræfter at pausede kampagner/annoncer er bevidste og aldrig flages som negativt fund.
- **Stage** — en ikke-`customer`-stage betyder en ikke-lukket konto; antag aldrig en aktiv retainer.

Behandl AI Context som ground truth for klient-fakta (også til at bekræfte `customer_id` i Trin 1), og gå videre til Trin 0.5.

## Trin 0.5 — Forudsætninger

At gemme filen er en ekstern write, gated bag eksplicit bekræftelse. Alt sprog på dansk (skift kun til engelsk hvis brugeren skriver på engelsk).

Kræver Google Ads MCP + et `customer_id`. Er MCP ikke tilgængelig: sig det og stop — der er intet meningsfuldt fallback (modsat `annoncetekster`, der kan køre på landingsside alene).

## Trin 1 — Intake (ét AskUserQuestion-kald)

Udled så meget som muligt fra samtalen først. Saml resten i ét kald:

1. **Klient + `customer_id`** — bekræft hvis allerede nævnt; ellers spørg. Kun klientnavn kendt → brug `list_accessible_accounts` til at finde id'et og bekræft.
2. **Analysevindue** — default sidste 30 dage. Vis `Sidste 30 dage (Anbefalet)`, `Sidste 90 dage`, `Andet` (fri tekst). `LAST_90_DAYS` er IKKE et gyldigt GAQL-literal — for alt over 30 dage beregn `BETWEEN '<YYYY-MM-DD>' AND '<YYYY-MM-DD>'`. Kun `LAST_30_DAYS` (og enkelte andre) virker som literal.
3. **Gem-destination** — `Drive (klientens mappe)`, `Lokalt (.xlsx)`, eller begge. Drive er en ekstern write — bekræft én gang før gem.

Sample-floor (`MIN_IMPRESSIONS`): default **50**. Vis defaulten i Oversigt så brugeren ved hvad der blev ekskluderet som dødvægt; brugeren kan overstyre.

## Trin 2 — Hent per-asset data (GAQL, kun ENABLED)

Uddeleger konto-læsningen til `ads-analyst`-agenten (read-only account analyst) via Task-værktøjet. Giv den det bekræftede `customer_id`, analysevinduet fra Trin 1 og AI Context'en fra Trin 0, og bed den køre de to GAQL-queries nedenfor (per-asset + RSA-tælling) med `run_custom_gaql`.

Hård regel: kun ENABLED kampagner OG annoncer — pausede er bevidste, ekskluderes, flages aldrig.

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

Feltformen blev verificeret live mod Inbound-konti 2026-05-29 — hvad hvert felt faktisk returnerer (`field_type`, `performance_label`, per-asset metrics, `cost_micros` → DKK) står i `references/gaql-verified-fields.md`. Læs den før du fortolker rå-outputtet.

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

For hver asset, beregn `status` (skriv ASCII-enummet i JSON; arket viser den danske form):
- **DOEDVAEGT** (vises som **DØDVÆGT**) — impressions under `MIN_IMPRESSIONS` (eller 0). Et dæknings-faktum, ikke en CVR-dom: Google serverer den næsten aldrig.
- **FOR_NY** (vises som **FOR NY**) — `performance_label` er `LEARNING`/`PENDING` OG impressions er lave. "Google lærer stadig — rør ikke endnu."
- **AKTIV** — impressions på eller over `MIN_IMPRESSIONS`. Serveres med rimeligt volumen.

Tærsklen er bevidst en ren impression-grænse, ikke en konvertering (se "Baggrund — hvorfor ingen profit-matrix" for hvorfor CVR-data er upålidelig på disse konti).

For hver asset, udled `vinkel` (benefit / trust / urgency / CTA / feature / keyword-led / brand / location / garanti — samme taksonomi som `../../shared/headline-craft.md`) ud fra asset-teksten.

Per ad group: hvilke vinkler har INGEN serveret asset? Det er `manglende_vinkler` → fødes til gap-brief.

`google_label` og `cvr_hint` behøves ikke i `analysis.json` — de renderes ikke som kolonner (se Baggrund). Brug dem internt i klassificeringen hvis nyttigt; arket viser kun `status`.

Anbefalinger er recommend-only, altid formuleret som forslag til mennesket, aldrig som kommando. Eksempler: "Aldrig serveret — kandidat til at skære." / "Kun 1 RSA i denne ad group — byg en challenger." / "Mangler en CTA-vinkel — tilføj i næste runde."

## Trin 4 — Byg gap-brief'et (det der lukker loopet)

Saml `manglende_vinkler` per ad group til en `gap_brief`-liste. For hver: et konkret `forslag` til hvilke challenger-headlines `inb-ads-rsa-copy` skal skrive. Det er her build→operate→iterate-loopet lukkes: outputtet fra dette skill er inputtet til næste `inb-ads-rsa-copy`-kørsel.

Ud over `gap_brief`-feltet i `analysis.json` (til arkets Gap-brief-fane), udskriv gap-brief'et i dit svar i denne kopiér-klare form, én linje per ad group:
```
- Ad group: <navn> | Manglende vinkler: <vinkel1>, <vinkel2> | Forslag: <kort tekst>
```
Vinkel-navnene skal være fra taksonomien i `../../shared/headline-craft.md` (benefit, trust, urgency, CTA, feature, keyword-led, brand, location, garanti), så `inb-ads-rsa-copy` kan forvælge dem direkte. Nævn at brugeren kan indsætte blokken i en `inb-ads-rsa-copy`-kørsel for at få challenger-annoncer der fylder hullerne.

Den fulde kontrakt — hvorfor transporten er manuel-paste (løs kobling mellem to Cowork-kørsler i samme plugin), og at forbrugeren hverken parser xlsx-fanen eller `analysis.json` — står i `references/gap-brief-contract.md`.

## Trin 5 — Skriv analysis.json og byg arket

Skriv en `analysis.json` efter skemaet i toppen af `build-sheet.py` (felter: `client`, `account_id`, `period`, `scope`, `min_impressions`, `method_notes`, `ad_groups`, `assets`, `gap_brief`).

```bash
python3 ${CLAUDE_SKILL_DIR}/build-sheet.py \
  --in analysis.json \
  --out "Annonce-optimering - <klient> - <YYYY-MM-DD>.xlsx"
```

Output: en farvekodet `.xlsx` med fanerne **Oversigt** (ærligheds-banner + `MIN_IMPRESSIONS`-floor), **Ad group-dækning** (challenger-flag + manglende vinkler på tværs af alle grupper), **én fane pr. ad group** (overblik øverst + asset-tabel med kolonnerne `Felt | Tekst | Vinkel | Impressions | Klik | Spend (DKK) | Status | Anbefaling`), og **Gap-brief** (til `inb-ads-rsa-copy`). Google-label og CVR-indikation er bevidst udeladt. Fuld fane- og kolonne-layout: `references/xlsx-layout.md`.

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
1. Lokal sti + Drive-link (hvis uploadet).
2. Kort opsummering: antal ad groups uden challenger, antal dødvægt-assets, de vigtigste vinkel-huller.
3. Det ærlige forbehold: "Rapporten er strukturel hygiejne — den dømmer ikke assets på konverteringsrate, fordi Google-data på disse konti er for tyndt og per-asset-metrics er konfunderede."
4. Loop-tilbagekobling: udskriv den kopiér-klare gap-brief-blok (formen fra Trin 4), og sig: "Indsæt denne blok i en `inb-ads-rsa-copy`-kørsel, så forvælger den vinklerne og skriver challenger-annoncer der fylder hullerne."
5. Næste skridt (manuelt, human-in-the-loop): brugeren beslutter hvilke assets der skæres/bygges; skillet rører aldrig kontoen.
6. Datakilder: Google Ads MCP (`run_custom_gaql`, `ad_group_ad_asset_view` + `ad_group_ad`), vindue brugt.

## Eksempel-output

```
Annonce-optimering klar: Annonce-optimering - Dansk Studie Center - 2026-05-29
Lokal: /Users/carl/work/Annonce-optimering - Dansk Studie Center - 2026-05-29.xlsx
Drive: https://docs.google.com/.../<file id>

- 3 ad groups har kun 1 RSA -> byg en challenger i hver.
- 7 assets er dødvægt (under 50 impressions i perioden) -> kandidater til at skære.
- Vinkel-huller: 'Højskole udland' mangler en CTA + urgency; 'Sabbatår' er fuldt dækket.

Forbehold: strukturel hygiejne. Ingen CVR-dom — Google-label er PENDING/NOT_APPLICABLE
på kontoen, og per-asset-metrics er konfunderede. Gap-brief'et følger (klar til
inb-ads-rsa-copy). Du beslutter hvad der skæres/bygges; skillet rører aldrig kontoen.
```

## Maintenance

- `build-sheet.py` self-bootstrapper openpyxl; kør lokalt for at smoke-teste mod en `analysis.json`.
- GAQL-feltformen (verificeret 2026-05-29) og hvornår signifikans-gaten kan løsnes står i `references/gaql-verified-fields.md`; re-verificér live hvis Google ændrer API-versionen — ikke på antagelse.

## References

- `../../shared/client-context-intake.md` — Trin 0 klient-kontekst-intake (delt).
- `../../shared/headline-craft.md` — vinkel-taksonomien (delt med `inb-ads-rsa-copy`).
- `references/gaql-verified-fields.md` — verificeret GAQL-feltform + dato-literal-gotcha + re-verifikation.
- `references/gap-brief-contract.md` — den fulde gap-brief-kontrakt med `inb-ads-rsa-copy`.
- `references/xlsx-layout.md` — fuld fane- og kolonne-layout for `build-sheet.py`-arket.
