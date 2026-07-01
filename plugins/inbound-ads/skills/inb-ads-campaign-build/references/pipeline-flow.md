# pipeline-flow — inb-ads-campaign-build orkestrering

Dette er kontrakten for hvordan `inb-ads-campaign-build` kører de fire faser, og hvordan hver
fase-reference dispatches. SKILL.md er flowet i prosa; denne fil er den præcise rækkefølge,
data-kontrakt og dispatch-regel. Den vinder ved konflikt.

## To modes (vigtigst at forstå)

Hver fase kan køre i to modes. Hvad fasen afleverer afhænger af **hvem der kaldte den**:

| Mode | Hvem kalder | Hvad fasen gør |
|---|---|---|
| **pipeline-mode** | `inb-ads-campaign-build`-orkestratoren (denne fil) | Forbruger upstream-JSON fra artefakt-mappen, emitterer sit eget JSON til samme mappe, spørger IKKE om intake den allerede har fået, og stopper IKKE for menneske-godkendelse undervejs (gaten ligger samlet til sidst). |
| **solo-mode** | Et selvstændigt skill (`inb-ads-campaign-research`/`inb-ads-campaign-structure`/`inb-ads-campaign-assets`) trigget direkte af brugeren | Samme kerne-logik, men samler minimal intake selv hvis nødvendigt, og pakker sit output i en `.xlsx`/`.docx`-rapport til mennesket. Defineret i shell-skillet, ikke her. |

Phase-referencerne i denne mappe er skrevet **pipeline-mode-først**. Solo-mode-wrappen bor i
shell-skillene. Den ENE undtagelse er Phase 4 (assembler): den afleverer altid review-workbooken,
også i pipeline-mode — det ER dens leverance.

## Artefakt-mappe (den delte arbejdsmappe)

Orkestratoren vælger én artefakt-mappe per kørsel (fx `.campaign-build/<klient>-<dato>/` i cwd, eller
en mappe brugeren angiver) og giver stien til hver fase. Alle fase-JSON'er skrives dertil. Det er
**lokale arbejdsfiler, ikke eksterne writes** — ingen write-gate (kun den endelige workbook→Drive er
en gated ekstern write). Fil-navne er faste, så join på tværs af faser er deterministisk:

| Fase | Reference | Skriver | Læser |
|---|---|---|---|
| 1a | `01-landing-page.md` | `landing-page-analysis.json` | (URL fra intake) |
| 1b | `02-competitor.md` | `competitor-research.json` | `landing-page-analysis.json` (klientens egen positionering) |
| 1c | `03-campaign-strategy.md` | `campaign-strategy.json` | (intake + Google Ads MCP CPC/konto) |
| 2 | `04-structuring.md` | `structuring.json` | `landing-page-analysis.json`, `competitor-research.json`, `campaign-strategy.json` |
| 3a | `05-rsa-copy.md` | `rsa-manifest.json` (+ per-ad-group `ads-*.json`) | `structuring.json` (angles + keyword_seeds_for_rsa) |
| 3b | `06-assets.md` | `assets.json` | `landing-page-analysis.json`, `campaign-strategy.json` |
| 4 | `07-assembler.md` | `Campaign - <klient> - <dato>.xlsx` + `Kampagne overblik.md` | alle fire: strategy, structuring, rsa-manifest, assets |

## Rækkefølge + parallelisme

```
Phase 1 (research, parallel):   01-landing-page ─┐
                                02-competitor   ─┼─►  [Phase-1 outputs]
                                03-strategy      ─┘
                                                      │
Phase 2 (gate):                 04-structuring  ◄─────┘   (forbruger alle tre)
                                                      │
                                                      ▼  [menneske-godkendelse — se nedenfor]
Phase 3 (creative, parallel):   05-rsa-copy     ─┐
                                06-assets        ─┴─►  [Phase-3 outputs]
                                                      │
Phase 4 (barriere):             07-assembler    ◄─────┘   (fletter alle fire → workbook)
```

- **Phase 1's tre referencer er uafhængige** og dispatches parallelt (hver i sin subagent). `02-competitor` læser dog gerne klientens egen `landing-page-analysis.json` hvis 1a er færdig — kør 1a først eller giv 1b både klient-URL og analysen når den er klar. Ingen hård barriere: 1b degraderer pænt uden 1a.
- **Phase 2 er en barriere:** den kræver alle tre Phase-1-outputs.
- **Phase 3's to referencer er uafhængige** og dispatches parallelt efter Phase 2 er godkendt.
- **Phase 4 er en barriere:** den kræver alle fire upstream-shapes (`assemble.py` stopper hårdt hvis én mangler).

## Join-nøgle

`campaign` (kampagnenavnet) er join-nøglen på tværs af alle fire shapes. `assemble.py` stopper hårdt
hvis kampagnenavnet ikke matcher på tværs af strategy/structuring/rsa-manifest/assets (paste mellem
faser kan desynce dem). Ad groups joines på `name` mellem `structuring.json` og `rsa-manifest.json`.
Resolv kampagnenavnet ÉN gang i Phase 1c (`03-campaign-strategy`) og genbrug det verbatim downstream.

## Sådan dispatcher orkestratoren en fase (subagent-kontrakt)

For hver fase spawner orkestratoren en subagent (`Agent`-værktøjet) og giver den:

1. **Reference-stien** — fx `${CLAUDE_SKILL_DIR}/references/04-structuring.md`. `${CLAUDE_SKILL_DIR}`
   er inb-ads-campaign-build-skillets egen mappe; alle kontrakt-filer ligger som `references/<navn>.md` ved
   siden af phase-referencerne, så stier resolver uanset hvor subagenten kører.
2. **Artefakt-mappen** — så fasen ved hvor den læser upstream-JSON og skriver sit eget.
3. **Mode = pipeline** — eksplicit, så fasen ikke spørger om intake den allerede har, og ikke selv
   pakker en rapport (kun Phase 4 emitterer en fil).
4. **De kendte intake-felter** (klient, URL, geo, kampagnenavn) så fasen ikke gen-spørger.

Subagenten kører reference'ns trin, skriver sit JSON, og returnerer en kort opsummering (sti + de
nøgletal orkestratoren skal bruge til Phase-2-godkendelsesoplægget). Subagentens fulde output er
IKKE brugeren-vendt — orkestratoren syntetiserer.

## Den ENE menneske-gate

Phase 2 (structuring) er det tunge gate-trin. Efter Phase 1+2 er kørt, præsenterer orkestratoren
structuring-resultatet (ad groups, keywords, negatives) og **beder eksplicit om godkendelse før
Phase 3**. Intet creative kører før mennesket har sagt god. Det er den eneste indbyggede stop i
pipeline-mode (ud over den endelige workbook→Drive write-gate i Phase 4).

## Hård regel — INGEN API-push (hele pipelinen)

Ingen fase pusher til Google Ads API'et (beslutning 2026-06-03). Faserne LÆSER fra Google Ads MCP
(konto-match, CPC, den delte negativliste) men SKRIVER intet til kontoen. Leverancen er
review-workbooken; Editor-CSV'er genereres SENERE af `inb-ads-editor-csv-export`-skillen fra den
klient-bekræftede Excel. Read-only MCP-kald er fine; ethvert skrive-kald er forbudt.
