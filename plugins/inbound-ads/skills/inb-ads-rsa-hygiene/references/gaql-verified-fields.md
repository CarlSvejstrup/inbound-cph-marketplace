# GAQL feltform — verificeret live (2026-05-29)

Provenance og feltdetaljer for de to queries i Trin 2. Queryerne selv (SELECT + WHERE) står inline i SKILL.md; denne fil holder hvad hvert felt faktisk returnerede da det blev kørt mod rigtige Inbound-konti, så en fremtidig læser ikke skal gætte på API-adfærd.

## Verificeret feltform (live, 2026-05-29)

Kørt mod flere Inbound-konti via `run_custom_gaql`:

- **`ad_group_ad_asset_view.field_type`** returnerer `HEADLINE` eller `DESCRIPTION` — det er sådan headlines og descriptions skilles ad per asset-række.
- **`ad_group_ad_asset_view.performance_label`** returnerer i praksis `NOT_APPLICABLE` eller `PENDING` — sjældent `BEST`/`GOOD`/`LOW`. På små danske annoncører når kontiene ikke det volumen Google kræver for at tildele en rigtig label (set som identisk selv ved 55.865 impressions). Derfor er den ikke primær-signal og vises ikke i arket.
- **`asset.text_asset.text`** bærer selve asset-teksten (headline- eller description-strengen).
- **Per-asset `metrics.impressions` / `metrics.clicks` / `metrics.conversions` / `metrics.cost_micros`** kommer alle tilbage. Men klik/konverteringer er konfunderede: en RSA serverer ~3 headlines + 2 descriptions per impression, og samme klik/konvertering tilskrives alle serverede assets (fx 39 klik / 57 impr = 68% "CTR" er umuligt at fortolke). Derfor bruges kun `impressions` som strukturelt signal (dæknings-faktum), aldrig CVR som dom.
- **`cost_micros` er micros** → DKK = `cost_micros / 1_000_000`.

## RSA-tælling per ad group

Den anden query (`FROM ad_group_ad`, `ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'`) returnerer `campaign.name`, `ad_group.name`, `ad_group_ad.ad.id`. Tæl **distinkte ad-id'er per (kampagne, ad group)** for at få champion-challenger-dækningen. Under 2 = flag "byg en challenger".

## Dato-literal-gotcha

`LAST_30_DAYS` virker som rå-GAQL-literal. **`LAST_90_DAYS` gør IKKE** — for ethvert vindue over 30 dage skal du beregne `BETWEEN '<YYYY-MM-DD>' AND '<YYYY-MM-DD>'` med rigtige datoer og erstatte `DURING LAST_30_DAYS` med det.

## Re-verifikation

Feltformen blev verificeret live 2026-05-29 mod Inbound-konti. Re-verificér hvis Google ændrer API-versionen. Hvis Google begynder at tildele `BEST`/`GOOD`/`LOW` (højere volumen i fremtiden), kan signifikans-gaten i Trin 3 løsnes — men kun efter en ny live-verifikation, ikke på antagelse.
