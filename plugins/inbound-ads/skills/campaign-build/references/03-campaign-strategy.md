# Phase 1c — campaign-strategy (settings + bud/budget)

Phase-1 research-trin. Definerer strategien og settings for en ny Google Ads-kampagne — kampagnetype,
mål, geo/sprog/netværk, budstrategi, budget, conversion action og tracking-gate — og emitterer dem som
ét struktureret objekt der spejler Inbounds "01 Campaign settings"-fane. Ian's tab 01 hævet fra
dataindtastning til et beslutnings-trin. Output forbruges af `04-structuring` (match-type-politik,
kampagnenavn, mål) og `07-assembler` (fylder tab-01-rækken + seeder tab-08-launch-gates).

Pipeline-mode-først; `research`-shell-skillet wrapper solo-mode.

## Designprincip

Ikke 19 uafhængige valg — ~6 koblede beslutnings-klynger hvor ét datasignal driver flere kolonner.
Værdien: reproducér Inbounds hus-stil (de låste tab-01-værdier) og træf de **volumen-drevne** valg (bud,
budget) defensibelt. Alle låste defaults + bud/budget-logikken bor i
`${CLAUDE_SKILL_DIR}/references/campaign-settings-defaults.md` — læs den, den vinder ved konflikt.

## Hård regel — INGEN API-push

Dette trin (og hele campaign-build) pusher ALDRIG til Google Ads API'et. Det producerer et struktureret
objekt mennesket godkender; leverancen er workbook → manuel Editor-import. Ingen eksterne writes herfra.

## Trin 0 — Kontekst

Læs `references/campaign-settings-defaults.md` — de låste defaults, de 6 klynger og bud/budget-logikken.
Dansk medmindre brugeren skriver engelsk.

## Trin 1 — Intake

I pipeline-mode arver du klient + URL fra orkestratoren. Følg hus-reglen (vist i
`${CLAUDE_SKILL_DIR}/../responsive-search-ads/SKILL.md`: anbefalet-option først `(Anbefalet)`, "Other"
altid muligt, saml felter). Mål: få kald.

- **Konto-match:** kør stille `list_accessible_accounts` → bekræft "Fandt [Kontonavn] (ID: …) — rigtigt?"
- **Mål** default **Leads**; **kampagnetype** default **Search** (v1 er Search-only).
- **Budget-intent:** bekræft 500 DKK/dag eller overstyr.
- **Targeting-blok** (geo/sprog/netværk/match-types) vises som forhåndsvalgte, bekræftbare defaults — ikke
  åbne spørgsmål.
- **Tracking-verificeret ja/nej.**
- **Kampagnenavn:** bekræft det samlede navn efter templaten i reference-filen. Resolv det ÉN gang —
  `04-structuring` + `05-rsa-copy` genbruger samme konvention.

**Udled, spørg ikke om:** konto-ID, forventet CPC (Google Ads MCP / Keyword Planner via `run_custom_gaql`
ENABLED-only), conversion history, og alle låste geo/sprog/netværk/rotation/schedule/match-type-værdier.

## Trin 2 — Bud/budget-logik (den eneste rigtige beregning)

Følg kæden i reference-filen:
1. Ingen conversion history → **Maximize Conversions** (cold-start).
2. Dimensionér budget mod ~30 conv/md-tærsklen: clicks/dag ≈ (30÷30)÷CVR; dagsbudget ≈ clicks/dag × CPC.
   Sammenlign med 500 DKK/dag-defaulten; kan matematikken ikke købe ~1 conv/dag ved kundens CPC/CVR,
   **flag det** frem for stiltiende at emittere 500.
3. Genvurdér ved 14 dage. 4. Flip til Target CPA først efter ~30 conv/md (emit som regel). 5. tROAS kun
   ved revenue-værdier (N/A her).

Mangler MCP/CPC-data (helt ny kunde): fald tilbage til 500 DKK/dag MED et flag om at det er en utunet
default.

## Trin 3 — Emit objektet

Skriv `campaign-strategy.json` (keyet til tab-01's 19 kolonner) til artefakt-mappen. Form:

```json
{
  "client": "Acme A/S", "account_id": "9143889167", "campaign": "IC | GSN | AI-SEO",
  "campaign_type": "Search", "campaign_state": "Paused", "goal": "Leads",
  "budget_recommendation": { "daily_dkk": 500, "rationale": "...CPC×clicks...", "review_after_days": 14 },
  "bidding_strategy": "Maximize Conversions",
  "primary_conversion_action": "Alle Hubspot formular",
  "do_not_optimize_toward": "Form submit - Estimer projekt until tracking is fixed",
  "location": "Denmark", "location_option": "Presence: people in or regularly in Denmark",
  "languages": ["Danish", "English"],
  "networks": { "search": true, "search_partners": false, "display": false },
  "ad_rotation": "Optimize", "start_match_types": "Exact + selected Phrase only; no Broad at launch",
  "ai_max_for_search": false,
  "target_cpa_switch_rule": "Consider Target CPA only after roughly 30 conversions/month",
  "ad_schedule": "All days at launch; review by hour/day after statistically useful data",
  "tracking_prerequisite": "Verify HubSpot form fires in Google Ads AW-921001998 before enabling campaign"
}
```

Behold de menneske-læsbare strenge (fx hele budget-sætningen) — de renderes verbatim i Ians
review-workbook. `networks`-booleans mapper 1:1 til tab-08 Must-pass-gates.

## Trin 4 — Returnér

Returnér: stien + en kort tabel med de 6 klyngers valg (type/mål, budstrategi + budget-rationale,
conversion action + exclusion, targeting, tracking-gate, kampagnenavn). Flag eksplicit hvis budgettet er
en utunet fallback, og hvis tracking ikke er verificeret (→ state forbliver Paused).

## Risici / noter

- **Sprog-akse:** `languages` (audience-targeting) ≠ RSA-copy-sprog (default dansk). Bland dem ikke.
- **Navne-token-uoverensstemmelse:** Ians `IC | GSN | AI-SEO` (3 tokens) matcher ikke RSA-templaten (5
  tokens). Reproducér den bekræftede operator-navn; tilbyd 5-token-formen som anbefalet. Resolv én gang.
- v1 er Search-only. pMax/Shopping/Display ændrer bud (tROAS), targeting og hele tab-01-formen — branch
  senere.

## Maintenance

Alle låste defaults + bud/budget-logikken bor i `references/campaign-settings-defaults.md`. Navne-templaten
spejler `responsive-search-ads` — hold dem i sync.
