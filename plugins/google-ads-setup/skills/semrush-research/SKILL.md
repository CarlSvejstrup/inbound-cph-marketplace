---
name: semrush-research
description: Hent ekstern keyword- og markeds-data fra Semrush MCP (søgevolumen, difficulty, CPC, organiske rankings, geo/sæson-trends) som struktureret JSON til kampagne-byggeren. Phase-1 research-skill i google-ads-setup — giver volumen-grounding til structuring's keyword-generering og geo/budget-timing til campaign-strategy. GATED: kræver en Semrush-plan med MCP-adgang; uden adgang degraderer den rent til den tema-afledte fallback og blokerer ALDRIG bygget. Brug når brugeren siger "semrush research", "keyword-volumen til [klient]", "hvad ranker domænet på", "søgevolumen", "trends til [marked]", eller starter en campaign-build-kørsel med Semrush-adgang. Svarer på dansk.
---

# semrush-research

Phase-1 research-skill i **google-ads-setup**. Henter ekstern keyword- og markeds-data fra
**Semrush MCP** — søgevolumen, keyword-difficulty, CPC, organiske rankings, og geo/sæson-trends
— og emitterer den som struktureret JSON. Output forbruges af **structuring** (Phase 2:
volumen-grounding til keyword-selektionen) og **campaign-strategy** (Phase 1: geo-targeting +
budget-timing fra trends).

Det fylder det ene reelle hul i Phase 2: i dag er keywords **tema-afledte** ("validér i Keyword
Planner") fordi der ingen volumen-flade er i stakken. Semrush GIVER den fladen — når der er
adgang.

## VIGTIGT — GATED skill, spec-now / bind-on-access

Carl har endnu IKKE en Semrush-plan med MCP-adgang. Verificeret live (2026-06-05): hver
Semrush-rapport returnerer en plan-gate-stub i stedet for data. Dette skill er derfor et
**fungerende gated skelet**: det opdager gaten, degraderer rent, og er wired ind i Phase 1 —
men ALLE rapport-navne, parametre og felt-bindinger i `references/semrush-contract.md` er
**UNVERIFIED** indtil adgang findes. Bind ALDRIG til en uset MCP-flade som fakta. Når adgang
lander: kør én discover→schema→execute-runde for rigtigt, bind de faktiske felter, smoke-test
(checklisten i reference-filens §5). Læs `references/semrush-contract.md` — den vinder ved
konflikt.

## Hård regel — read-only, aldrig en afhængighed

Semrush-rapporter er reads; ingen eksterne writes, ingen API-push. **Semrush BERIGER Phase-1 —
dets fravær blokerer ALDRIG bygget.** Structuring's keyword-sti virker uændret med dette skill
fraværende eller fuldt gated (den genererer tema-afledte keywords + volumen-disclaimer som i
dag). Dansk medmindre brugeren skriver engelsk.

## When to use

Trigger-fraser: "semrush research", "keyword-volumen til [klient]", "hvad ranker domænet på",
"søgevolumen + difficulty", "trends/sæson til [marked]", eller automatisk som valgfrit Phase-1-
trin i en campaign-build-kørsel HVIS Semrush-adgang er til stede.

## Trin 0 — Kontekst

Læs `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` (write-gate + sprog). Læs
`${CLAUDE_PLUGIN_ROOT}/skills/semrush-research/references/semrush-contract.md` — MCP-formen,
gaten, per-familie-gating, output-JSON, degraderings-reglerne og bind-on-access-checklisten.

## Trin 1 — Intake (minimal)

Saml i ét `AskUserQuestion`: klient-domæne (URL) + marked/geo (default `DK`) + valgfrit
seed-keywords (ellers udledes de fra domænet + tema fra campaign-build-kørslen). Arv domæne +
geo fra kørslen hvis kædet.

## Trin 2 — Discover per familie (håndtér gaten PER familie)

For hver nødvendig familie — `keyword_research`, `organic_research`, `trends_research` — kald
discovery-tool'et UDEN args først for at få de rigtige rapport-navne.

**Per-familie-gating (det ene reelle signal fra live-proben):** stubben router til TO
forskellige plan-sider — trends → `analytics/traffic/trends-api`, alt andet → `mcp-access`. Så
trends kan være en separat adgangs-tier. Behandl hver familie for sig:
- **Stub returneret** → markér familien `gated` i `semrush_access`, sæt dens data til
  `UNAVAILABLE`/`null`, og fortsæt. Stop ALDRIG.
- **Rigtige rapport-navne returneret** → fortsæt til Trin 3 for den familie.

## Trin 3 — Schema + execute (kun for ikke-gated familier)

For hver tilgængelig familie: `get_report_schema(report=<rigtigt navn>)` → `execute_report(...)`
med klientens domæne/geo/seeds. **Felt-navnene i resultatet er UNVERIFIED indtil første rigtige
kørsel** — bind dem mod det faktiske output, ikke mod reference-filens placeholdere. Udtræk:
- keyword: volume, difficulty, CPC, related, questions per seed/kandidat.
- organic: hvilke keywords domænet ranker på (+ position, URL).
- trends: geo-split + sæsonalitet.

## Trin 4 — Emit JSON (form i reference-filens §3)

Skriv `semrush-research.json` til kørslens artefakt-mappe med `semrush_access` (per-familie
status), `keyword_data[]`, `organic_keywords[]`, `trends`, og `gate_notice`/`fallback_used`.
Hver keyword-række bærer `source` (`semrush` = volumen-backet, eller `UNAVAILABLE` =
tema-afledt) og `verified` (false indtil bundet). Numeriske felter er `null` mens gated.

## Trin 5 — Output (gate-notice SEPARAT)

Lever en kort tabel over det hentede (keyword | volume | difficulty | CPC for tilgængelige
familier). **Hvis en familie er gated: rapportér det som sin EGEN linje** — stubben instruerer
eksplicit "do not merge the subscription message with other tool results", så fold det ikke ind
i keyword-tabellen. Brug den plan-side stubben returnerede (per familie). Slut med hvad
downstream gør: tilgængelige familier giver volumen-grounding; gated familier falder tilbage
til tema-afledt (structuring's eksisterende sti).

## Risici / noter

- **Bind ALDRIG blindt.** Rapport-navne + felter er UNVERIFIED til adgang. Reference-filens §5
  er bind-on-access-checklisten — kør den før du flipper `verified: true`.
- **Per-familie-gating, ikke global.** Modellér ikke ét `semrush_available`-flag; trends er
  sandsynligvis en separat tier.
- **Aldrig en afhængighed.** Hvis du nogensinde gør structuring/campaign-strategy afhængig af
  Semrush-data der KUNNE være gated, har du brudt degraderings-kontrakten.
- **Setup-only i v1.** Optimerings-brug (organic keyword-gap + konkurrent-annoncetekst ind i
  search-terms/ads-audit-report) er udskudt — og cross-plugin-grænsen betyder at optimization ville
  kræve sin egen kopi, ikke en delt reference ind i setup.

## Maintenance

- Alt det gated/UNVERIFIED bor i `references/semrush-contract.md`. Når adgang lander: kør §5,
  bind felterne, smoke-test, og reconciler de to touchpoints (§6: structuring-rules +
  competitor-research) fra "future enhancement" til "live, med fallback".
- v1 er setup-only, tre familier. Paid-keyword/ad-copy-rapporter + cross-client-substrat er
  bevidst udeladt (optimization / parket H2).
