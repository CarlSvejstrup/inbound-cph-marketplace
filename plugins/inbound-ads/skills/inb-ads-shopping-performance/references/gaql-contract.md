# GAQL-kontrakt — shopping-performance (Trin 3)

Læs denne før du henter data. Alle queries er verificeret live mod en rigtig Shopping+PMax-konto
(Light-Point, `3257702845`, 2026-07-16). Kør dem via `run_custom_gaql`. Skriv hvert svar ordret til en
`.json`-fil — data skal være data.

## Fælder (lært den hårde vej — respektér dem)

1. **Impression share kan IKKE co-selectes med produkt-segments.**
   `metrics.search_impression_share` sammen med `segments.product_title` (eller andre produkt-segments)
   kaster `PROHIBITED_SEGMENT_WITH_METRIC_IN_SELECT_OR_WHERE_CLAUSE`. → IS er en **separat** query på
   kampagne- eller product_group-grain (pull B).
2. **`LAST_90_DAYS` findes ikke.** `DURING` tager kun `LAST_30_DAYS`, `LAST_14_DAYS`, `LAST_7_DAYS`,
   `TODAY`, `YESTERDAY`, `THIS_MONTH`, `LAST_MONTH`. For >30 dage: `BETWEEN 'ÅÅÅÅ-MM-DD' AND 'ÅÅÅÅ-MM-DD'`.
3. **`product_group_view` understøtter kun `search_impression_share`** — IKKE
   `search_budget_lost_impression_share` (kaster `PROHIBITED_METRIC_IN_SELECT_OR_WHERE_CLAUSE`). Vil du
   have budget-/rank-nedbrydningen, skal det være `FROM campaign`.
4. **`shopping_product` (ressourcen) i denne MCP-version har INGEN status-/issue-felter** — kun metrics +
   dato-segments. Den kan ikke give afvisningsårsager. Brug den ikke til feed-health; det hører til
   Merchant API.
5. **Tomme segment-nøgler udelades af svaret** (ikke `null`). Mangler `product_brand` /
   `product_type_l1` i en række, er den tom for den række — ikke et ugyldigt felt. `slim.py` håndterer
   det.
6. **Blandede felt-typer i samme række:** `cost_micros`, `impressions`, `clicks` er **strings**
   (`"9632"`); `conversions`, `conversions_value` og alle IS-metrics er **floats** (`0.0`, `0.347`).
   Cast pr. felt.
7. **`product_type_l1` er klientens EGEN product_type-værdi** (fx `"simple"`), ikke en Google-kategori.
   Forveksl den ikke med `google_product_category` (som ikke findes i Google Ads API — kun i Merchant).

## Pull A — Produkt-performance (produkt-grain, INGEN IS)

Skriv til `~/Downloads/_sp_products.json`.

```sql
SELECT
  segments.product_item_id,
  segments.product_title,
  segments.product_brand,
  segments.product_type_l1,
  segments.product_custom_attribute0,
  segments.product_custom_attribute1,
  campaign.name,
  metrics.cost_micros,
  metrics.clicks,
  metrics.impressions,
  metrics.conversions,
  metrics.conversions_value
FROM shopping_performance_view
WHERE segments.date DURING LAST_30_DAYS
  AND metrics.cost_micros >= 50000000          -- tærskel: 50 kr = 50_000_000 micros
ORDER BY metrics.cost_micros DESC
LIMIT 500
```

- Tærskel: `X kr` → `metrics.cost_micros >= X*1_000_000`. `Alt` → drop AND-linjen (advar på store konti).
- Custom labels ligger i `product_custom_attribute0..4` — tag kun dem klienten bruger med (spørg/tjek i
  trin 2), ellers larmer det.
- Vil du fange produkter der IKKE bruger budget (0 impr = server ikke): kør samme query med
  `metrics.impressions = 0` i stedet — men husk, dette skill kan ikke sige HVORFOR (→ Merchant Center).

## Pull B — Impression share pr. kampagne (budget-/rank-nedbrydning)

Skriv til `~/Downloads/_sp_is.json`.

```sql
SELECT
  campaign.name,
  campaign.advertising_channel_type,
  metrics.search_impression_share,
  metrics.search_budget_lost_impression_share,
  metrics.search_rank_lost_impression_share,
  metrics.cost_micros,
  metrics.conversions_value
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
  AND campaign.advertising_channel_type IN ('SHOPPING','PERFORMANCE_MAX')
  AND metrics.impressions > 0
ORDER BY metrics.cost_micros DESC
LIMIT 50
```

- IS-værdier er andele (0-1): `0.348` = 34,8 %. `search_budget_lost` + `search_rank_lost` +
  `search_impression_share` ≈ 1.
- Tolkning: taber en vinder mest til **budget** → budget/bud op. Mest til **rank** → bud op eller bedre
  feed-relevans (titel), ikke budget.

## Pull D — PMax asset group-produktopdeling (kun hvis PMax og A er tom for PMax)

Skriv til `~/Downloads/_sp_pmax.json`. Brug hvis PMax-produkter ikke dukker op i pull A (PMax-netværks-
data lander først i `shopping_performance_view` fra 15. jun 2026 — verificér live før du stoler på det).

```sql
SELECT
  asset_group.name,
  campaign.name,
  metrics.cost_micros,
  metrics.clicks,
  metrics.conversions,
  metrics.conversions_value
FROM asset_group_product_group_view
WHERE segments.date DURING LAST_30_DAYS
  AND metrics.impressions > 0
ORDER BY metrics.cost_micros DESC
LIMIT 200
```

Verificér `asset_group_product_group_view`-feltsættet med `get_resource_metadata` hvis en kolonne
afvises — PMax-reporting-skemaet ændrer sig.
