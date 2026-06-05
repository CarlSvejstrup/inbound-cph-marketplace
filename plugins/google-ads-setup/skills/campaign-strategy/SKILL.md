---
name: campaign-strategy
description: Definer en ny Google Ads kampagnes strategi og settings (kampagnetype, mål, geo, sprog, netværk, budstrategi, budget, conversion action, tracking-gate) som struktureret objekt til kampagne-byggeren. Phase-1 research-skill i campaign-build — Inbounds tab-01-konventioner som anbefalede defaults, med volumen-drevet bud/budget-logik. Skriver ingen eksterne writes og pusher ALDRIG til Google Ads API'et. Brug når brugeren siger "kampagne-strategi", "campaign settings til [klient]", "opsæt kampagne", eller starter en campaign-build-kørsel. Svarer på dansk.
---

# campaign-strategy

Phase-1 research-skill i **campaign-build**. Definerer strategien og settings for en ny Google Ads-kampagne — kampagnetype, mål, geo/sprog/netværk, budstrategi, budget, conversion action og tracking-gate — og emitterer dem som ét struktureret objekt der spejler Inbounds "01 Campaign settings"-fane. Dette er Ian's tab 01 hævet fra dataindtastning til et beslutnings-skill.

Output forbruges af **structuring** (Phase 2, læser match-type-politik + kampagnenavn + mål) og **assembler** (Phase 4, fylder tab-01-rækken + seeder tab-08-launch-gates).

## Designprincip

Dette er ikke 19 uafhængige valg. Det er ~6 koblede beslutnings-klynger hvor ét datasignal driver flere kolonner. Skillets værdi: reproducér Inbounds hus-stil (de låste tab-01-værdier) og træf de **volumen-drevne** valg (bud, budget) defensibelt frem for per rutine. Alle låste defaults + bud/budget-logikken bor i `references/campaign-settings-defaults.md` — læs den.

## Hård regel — INGEN API-push

Dette skill (og hele campaign-build) pusher ALDRIG til Google Ads API'et (beslutning 2026-06-03). Det producerer et struktureret objekt mennesket godkender, og leverancen er CSV/workbook til manuel Editor-import. Det bryder ellers tre låste ting: den verificerede CSV-import-sti, Inbounds human-in-the-loop-regel, og skeletons "Paused until launch QA"-model. Dette skill laver ingen eksterne writes overhovedet.

## When to use

Trigger-fraser: "kampagne-strategi", "campaign settings til [klient]", "opsæt kampagne", "kampagne-opsætning", eller automatisk som parallelt Phase-1-trin i en campaign-build-kørsel.

## Trin 0 — Kontekst

Læs `references/campaign-settings-defaults.md` — de låste defaults, de 6 klynger og bud/budget-logikken. Den vinder ved konflikt. Dansk medmindre brugeren skriver på engelsk.

## Trin 1 — Intake (få AskUserQuestion-kald, mange felter)

Følg hus-reglen (`responsive-search-ads` L97-104): hvert felt via `AskUserQuestion`, den låste tab-01-værdi vist som **første option `(Anbefalet)`**, "Other" altid muligt. Mål: 2-3 kald.

- **Kald 1** — klient + URL + konto-match + mål + kampagnetype.
  - Konto-match: spørg klientnavn → kør stille `list_accessible_accounts` → bekræft "Fandt [Kontonavn] (ID: …) — rigtigt?" (samme mønster som `ads-audit-report` Trin 1a). Arv klient/URL fra campaign-build-kørslen hvis kædet.
  - Mål default **Leads**; kampagnetype default **Search** (v1 er Search-only).
- **Kald 2** — budget-intent (bekræft 500 DKK/dag eller overstyr) + bekræft den låste targeting-blok (geo/sprog/netværk/match-types som forhåndsvalgte defaults) + tracking-verificeret ja/nej.
- **Kald 3** — bekræft det samlede kampagnenavn (RSA Kald 3-mønster) efter navne-templaten i reference-filen.

**Udled, spørg ikke om:** konto-ID (`list_accessible_accounts`), forventet CPC (Google Ads MCP / Keyword Planner, `run_custom_gaql` ENABLED-only), conversion history; og alle låste geo/sprog/netværk/rotation/schedule/match-type-værdier (vises som bekræftbare defaults, ikke åbne spørgsmål).

## Trin 2 — Bud/budget-logik (den eneste rigtige beregning)

Følg kæden i reference-filen:
1. Ingen conversion history → **Maximize Conversions** (cold-start).
2. Dimensionér budget til at NÅ ~30 conv/md-tærsklen: clicks/dag ≈ (30÷30)÷CVR; dagsbudget ≈ clicks/dag × CPC. Sammenlign med 500 DKK/dag-defaulten; hvis matematikken siger den ikke kan købe ~1 conv/dag ved kundens CPC/CVR, **flag det** frem for stiltiende at emittere 500.
3. Genvurdér ved 14 dage. 4. Flip til Target CPA først efter ~30 conv/md (emit som regel for senere). 5. Target ROAS kun ved revenue-værdier (N/A her).

Mangler MCP/CPC-data (helt ny kunde, ingen konto endnu): fald tilbage til 500 DKK/dag MED et flag om at det er en utunet default.

## Trin 3 — Emit objektet

Skriv det strukturerede objekt (keyet til tab-01's 19 kolonner) til kørslens artefakt-mappe, fx `.firecrawl/campaign-strategy.json` eller orkestratorens sti. Form:

```json
{
  "account_id": "9143889167",
  "campaign": "IC | GSN | AI-SEO",
  "campaign_type": "Search",
  "campaign_state": "Paused",
  "goal": "Leads",
  "budget_recommendation": { "daily_dkk": 500, "rationale": "...CPC×clicks...", "review_after_days": 14 },
  "bidding_strategy": "Maximize Conversions",
  "primary_conversion_action": "Alle Hubspot formular",
  "do_not_optimize_toward": "Form submit - Estimer projekt until tracking is fixed",
  "location": "Denmark",
  "location_option": "Presence: people in or regularly in Denmark",
  "languages": ["Danish", "English"],
  "networks": { "search": true, "search_partners": false, "display": false },
  "ad_rotation": "Optimize",
  "start_match_types": "Exact + selected Phrase only; no Broad at launch",
  "ai_max_for_search": false,
  "target_cpa_switch_rule": "Consider Target CPA only after roughly 30 conversions/month",
  "ad_schedule": "All days at launch; review by hour/day after statistically useful data",
  "tracking_prerequisite": "Verify HubSpot form fires in Google Ads AW-921001998 before enabling campaign"
}
```

Behold de menneske-læsbare strenge (fx hele budget-sætningen) — de renderes verbatim i Ians review-workbook. `networks`-booleans mapper 1:1 til tab-08 Must-pass-gates.

## Trin 4 — Output

Lever: stien til objektet + en kort tabel med de 6 klyngers valg (type/mål, budstrategi + budget-rationale, conversion action + exclusion, targeting, tracking-gate, kampagnenavn). Flag eksplicit hvis budgettet er en utunet fallback, og hvis tracking endnu ikke er verificeret (→ state forbliver Paused).

## Risici / noter

- **Sprog-akse:** `languages` (audience-targeting) ≠ RSA-copy-sprog (default dansk). Bland dem ikke når begge skills kører i samme session.
- **ads-audit-report-overlap:** ads-audit-report er *diagnostisk på en eksisterende konto*; campaign-strategy er *generativ for en ny kampagne*. De deler kun `list_accessible_accounts` + MCP-plumbing. Kører en audit forud, kan den levere conversion-volumen-signalet der flytter bud fra Maximize Conversions (cold) mod Target CPA (warm) — en *berigende input*, ikke en afhængighed.
- **Navne-token-uoverensstemmelse:** Ians `IC | GSN | AI-SEO` (3 tokens) matcher ikke RSA-templaten (5 tokens). Reproducér den bekræftede operator-navn; tilbyd 5-token-formen som anbefalet. Resolv én gang — structuring + rsa-copywriter genbruger samme konvention.

## Maintenance

- Alle låste defaults + bud/budget-logikken bor i `references/campaign-settings-defaults.md`. Ret kun den, hvis Inbound ændrer hus-stil. Navne-templaten spejler `responsive-search-ads` — hold dem i sync.
- v1 er Search-only. pMax/Shopping/Display ændrer bud (tROAS), targeting og hele tab-01-formen — branch senere.
