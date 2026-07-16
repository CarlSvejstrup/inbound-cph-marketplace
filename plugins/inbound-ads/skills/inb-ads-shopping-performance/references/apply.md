# Trin 7 — Udfør de aftalte handlinger (mekanik)

Læs denne fil når du når Trin 7 — altså EFTER brugeren har set hele listen og sagt ja i Trin 6.
Aldrig før. Skriv kun det der stod på den godkendte liste. **Alle konto-writes går gennem
`ads-writer`-agenten via Task, én bekræftet handling ad gangen.** Dette skill skriver aldrig selv.

## Hvad der KAN skrives live (via ads-writer)

MCP'ens skrive-flade for Shopping/PMax er begrænset. Kun disse er rigtige live-writes:

- **Bud på ad group-niveau** — `update_ad_group_bid(customer_id, ad_group_id, cpc_bid)`. Relevant på
  manuelle/eCPC Shopping-kampagner. På tROAS/tCPA-kampagner er rå max-CPC sjældent leveren.
- **Budstrategi / mål på kampagne-niveau** — `update_campaign_bidding_strategy(customer_id,
  campaign_id, bidding_strategy, target_roas|target_cpa)`. Det er den rigtige lever på en
  value-baseret Shopping/PMax-konto: juster tROAS op på en vinder, ned på en spender. Bekræft mod
  AI Context-normen først.
- **Fjern et kampagne-kriterium** — `remove_campaign_criterion(...)` (fx en forkert location/schedule
  fundet undervejs). Destruktivt; kræver `confirm=True`.

## Hvad der IKKE kan skrives (recommend-only)

- **Produkt-/listing-group-eksklusion.** Der er INGEN tool til at ekskludere et enkelt produkt eller en
  listing-group i denne MCP. Vil brugeren ekskludere en spild-vare, er det **anbefal-kun**: forklar at
  det gøres i Google Ads UI (eller Editor) på listing-group-niveau, eller pak det som en opgave. Foreslå
  aldrig at det sker "live herfra" — det kan det ikke.
- **Budget.** Rene budget-writes er strammere gated og **blokeret indtil budget-guardrail'en er live**
  (se `backlog/inbound-cph.md` → Sommer-item 1). Foreslå gerne "hæv budget på den budget-begrænsede
  vinder", men skriv det ikke; lever det som anbefaling til brugeren/PM.
- **Feed-ændringer** (titel, kategori, eksklusion i selve feed'et) — hører til Merchant Center /
  `inb-ads-feed-health`, ikke her.

## Rute en bekræftet handling gennem ads-writer

For hver handling der ER en tilladt live-write, dispatch én Task til `ads-writer` ad gangen:

1. **Slå ID'er op (navn → id)** hvis du ikke allerede har dem. `update_ad_group_bid` targeter
   `ad_group_id`; `update_campaign_bidding_strategy` targeter `campaign_id`. Hent med `run_custom_gaql`:
   ```sql
   SELECT campaign.id, campaign.name FROM campaign WHERE campaign.status != 'REMOVED'
   SELECT ad_group.id, ad_group.name, campaign.name FROM ad_group WHERE ad_group.status != 'REMOVED'
   ```
   Match på EKSAKT navn. Et navn der ikke kan resolves → stop og spørg, gæt aldrig et id.
2. **Byg en `decisions.json`** af præcis den godkendte liste, så handlingerne er entydige:
   ```json
   {
     "client": "Light-Point", "customer_id": "3257702845",
     "bid_changes": [
       {"level": "campaign", "campaign": "IC | Shopping | Generisk | Outdoor",
        "campaign_id": "22401300178", "action": "target_roas",
        "bidding_strategy": "MAXIMIZE_CONVERSION_VALUE", "old": 3.0, "new": 4.0,
        "why": "budget-begrænset vinder, IS 73% men taber 11% til budget"}
     ],
     "recommend_only": [
       {"type": "product_exclusion", "product": "STRIPE S1500 ...", "product_item_id": "270362",
        "why": "254 kr forbrug, 0 konv i 30 dage, Shopping (ikke PMax)"}
     ]
   }
   ```
3. **Dispatch til ads-writer** (Task, `subagent_type: inbound-ads:ads-writer`) med præcis én ændring pr.
   kald i klar prosa: customer ID, entitet (campaign/ad_group + id), felt, **gammel → ny værdi**, og
   hvorfor. `ads-writer` genformulerer ændringen, beder om eksplicit per-handling-bekræftelse, kører
   først `dry_run=True`, og skriver kun på et klart ja med `confirm=True`. En repo-hook er hård backstop
   og blokerer ubekræftede writes + alle budget-writes.
4. **Recommend-only-punkter** (produkt-eksklusion, budget) skrives IKKE. Saml dem i den afsluttende
   opsummering som klare anbefalinger brugeren/PM kan udføre.

## Afslut

Kort opsummering: hvad blev skrevet (entitet, gammel → ny), hvad blev anbefalet (recommend-only), og en
`## Kilder`-sektion med de pulls og AI Context du brugte. Ændrede du konto-tilstand, så husk
`asa-update`-tankegangen findes ikke her — men en changelog-note til klientens optimeringslog er god
skik (se `inb-ads-change-log`).
