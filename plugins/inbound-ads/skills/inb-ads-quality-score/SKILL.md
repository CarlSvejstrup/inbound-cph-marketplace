---
name: inb-ads-quality-score
description: Actionable Quality Score-deep-dive for én live Google Ads-konto. Trækker QS på keyword-grain via get_quality_score_audit, klynger de værste keywords, mapper hver svag komponent (creative_quality, expected_ctr, landing_page_quality) til den lever der faktisk flytter den, og fører en samtale om fundene før den — kun efter eksplicit bekræftelse per handling — udfører bud- eller keyword-ændringer via ads-writer. Landingsside- og creative-fixes er anbefal-kun. Brug når brugeren siger "tjek quality score", "kvalitetsscore", "hvorfor er QS lav", "forbedr quality score på [kunde]", eller "QS-audit". Adskilt fra inb-ads-account-audit, der kun RAPPORTERER QS i et deck, og fra inb-ads-search-term-analyse / inb-ads-rsa-hygiene, som dækker andre dimensioner (søgetermer, RSA-asset-hygiejne). Svarer på dansk.
---

# inb-ads-quality-score

Én dimension, gravet i dybden: **Quality Score**. Målet er ikke en tabel og ikke et deck — det er at finde de keywords hvor QS koster penge, forstå *hvilken* komponent der trækker ned, og handle på den ene lever der kan handles på. Read-only indtil vi er enige; enhver konto-write går derefter gennem `ads-writer`, bekræftet per handling. Alt på dansk (skift kun til engelsk hvis brugeren skriver engelsk).

## Baggrund — hvorfor et fokuseret QS-skill

QS var den ene *handlingsbare* dimension i det nu-nedlagte `inb-ads-optimization-loop`. De to overlevende motorer dækker den ikke: `inb-ads-search-term-analyse` handler om søgetermer og negatives, `inb-ads-rsa-hygiene` om RSA-asset-dækning. QS er en tredje akse, og den er værd at isolere fordi den peger præcist: et lavt keyword-QS med en `expected_ctr` BELOW_AVERAGE er et keyword/struktur-problem, mens `creative_quality` BELOW_AVERAGE er et annoncetekst-problem — to helt forskellige levers, som en samlet "audit" udvander til én QS-søjle i et deck. Dette skill oversætter QS-diagnosen til konkrete handlinger og lukker dem HITL-gated.

To ærligheds-forbehold bygget ind fra start:
1. **QS lever på keyword-grain.** Der findes ingen native ad-group- eller konto-QS. Vi rapporterer flagede *keywords* (med den ad group de sidder i), aldrig en opfundet ad-group-QS.
2. **Landingsside er et FLAG, ikke en score.** API'et giver aldrig en numerisk "LP-score" — kun en `BELOW_AVERAGE | AVERAGE | ABOVE_AVERAGE`-label per keyword. Vi anbefaler en LP-fix på de ramte keywords; vi finder aldrig på en "LP-score %".

Fuld QS-kontrakt (tool, grain, dato-gotcha, output-form): `../../shared/quality-score-pull.md`. Læs den; dette skill duplikerer den ikke.

## Hvad skillet gør / ikke gør

**Gør:**
- Trækker QS på keyword-grain via `get_quality_score_audit` og normaliserer med den bundlede `lib/quality_score.py`.
- Klynger de værste keywords og mapper hver svag komponent til dens lever.
- Foreslår konkrete handlinger, og fører de Ads-side-writes (bud, keyword/match-type) gennem `ads-writer` per-handling HITL.
- Leverer et kort in-chat overblik (evt. en lille tabel), ikke et Excel-ark som default.

**Gør ikke:**
- Rapporterer ikke bare QS i et deck — det er `inb-ads-account-audit`s job. Dette skill *handler*.
- Skriver aldrig til kontoen off the back of et QS-fund uden eksplicit bekræftelse; LP/creative-fixes skrives aldrig til Ads-kontoen (de er ikke Ads-account-writes).
- Vurderer aldrig pausede kampagner — de er bevidste, ekskluderes, flages aldrig som negativt fund.

## Trin 0 — Hent klient-kontekst (AI Context) FØRST

Kør `../../shared/client-context-intake.md` som allerførste trin — før det første Google Ads MCP-kald. Det er en læsning (aldrig gated), men obligatorisk: sådan arver du ID'er, kontakter, hårde rammer, budstrategi-norm, KPI'er og pausede-kampagners-intention i stedet for at diagnosticere blindt. Den fil holder også reglen om delte Drive-mapper (Lime, Retriever/Infomedia, GSGroup, Nemco, Julemærket, PhoneAlone, DI → vælg rækken for det specifikke marked) og fallback når en klient endnu ikke har en AI Context-fil.

Fire ting i AI Context'en styrer QS-analysen direkte:
- **Budstrategi-norm** (tCPA/tROAS/manuel) — afgør om en bud-lever overhovedet giver mening: på en Smart Bidding-konto justerer man mål/struktur, ikke rå max-CPC. Læs dette før du foreslår `update_ad_group_bid`.
- **Hårde rammer** — afgrænser hvad du må røre og anbefale.
- **KPI'er** — hvilke keywords der er værd at redde (høj-intent, høj-værdi) vs. lade ligge.
- **Stage** — en ikke-`customer`-stage betyder en ikke-lukket konto; antag aldrig en aktiv retainer.

## Trin 0.5 — Forudsætninger

Kræver Google Ads MCP + et `customer_id`. Er MCP ikke tilgængelig: sig det og stop — QS kan ikke hentes uden. Alt sprog på dansk.

## Trin 1 — Intake (ét AskUserQuestion-kald)

Udled så meget som muligt fra samtalen først. Saml resten i ét kald:

1. **Klient + `customer_id`** — bekræft hvis allerede nævnt (mod AI Context'en fra Trin 0); ellers spørg. Kun klientnavn kendt → brug `list_accessible_accounts` til at finde id'et og bekræft.
2. **Analysevindue** — QS ønsker volumen, så default et **~90-dages BETWEEN-vindue** (beregn `('<YYYY-MM-DD>', '<YYYY-MM-DD>')` for de sidste ~90 dage). Vis `Sidste ~90 dage (Anbefalet)`, `Sidste 30 dage`, `Andet` (fri tekst). **`LAST_90_DAYS` er IKKE et gyldigt rå-GAQL-literal** — brug altid et beregnet BETWEEN for 90-dages-vinduet (det er derfor `date_range_arg()` afviser literalen; se `../../shared/quality-score-pull.md` for hvorfor tool-argumentet og rå-GAQL opfører sig forskelligt).

Ingen gem-destination i intake: default-output er in-chat. Kun hvis brugeren beder om det leverer vi en lille tabel eller fil.

## Trin 2 — Træk QS (dispatch til ads-analyst)

Uddeleger konto-læsningen til `ads-analyst`-agenten (read-only account analyst) via Task-værktøjet. Giv den det bekræftede `customer_id`, vinduet fra Trin 1 og AI Context'en fra Trin 0, og bed den kalde:

```
get_quality_score_audit(customer_id, date_range=<BETWEEN '<start>' AND '<end>'>)
```

Byg `date_range`-strengen med helperen i den bundlede `lib/quality_score.py`:

```python
from lib.quality_score import date_range_arg
date_range = date_range_arg((start, end))   # -> "BETWEEN '<start>' AND '<end>'"
# date_range_arg("LAST_90_DAYS") rejser ValueError med vilje — brug tuple-formen.
```

`ads-analyst` returnerer den rå `get_quality_score_audit`-respons (den verificerede form: `total_keywords_with_qs`, `average_quality_score`, `distribution`, `worst_keywords[]` med de tre komponent-labels). Den skriver aldrig til kontoen.

## Trin 3 — Normalisér

Kør den rå respons gennem `normalise_findings()` fra den bundlede `lib/quality_score.py`:

```python
from lib.quality_score import normalise_findings
norm = normalise_findings(raw_audit)
# -> { "average_quality_score", "spend_by_qs":[{qs,keyword_count}], "flagged_keywords":[...] }
```

`flagged_keywords` er keyword-grain (verificeret): hver post har `campaign`, `ad_group`, `keyword`, `match_type`, `quality_score`, de tre komponent-labels, `impressions`, `cost` og convenience-flaget `lp_below_average`. `spend_by_qs` er QS 1-10-fordelingen (til et evt. lille distributions-overblik).

## Trin 4 — Analysér: klynge + lever-mapping

Grav mønstrene frem, dømm ikke enkelt-keywords blindt:

1. **Klynge de værste keywords.** Grupper `flagged_keywords` efter fælles svaghed — samme ad group, samme dominerende svage komponent, samme landingsside. En klynge af QS 1-2 i én ad group er et struktur-signal, ikke fem uafhængige problemer.
2. **Map hver svag komponent til dens lever:**
   - `creative_quality` BELOW_AVERAGE → **RSA-rewrite**. Annonce-relevans er for lav. Anbefal-kun her: hand videre til `inb-ads-rsa-copy` (skriv nye challenger-headlines) eller `inb-ads-rsa-hygiene` (diagnosér den eksisterende RSA-opsætning). Dette er ikke en Ads-account-write fra dette skill.
   - `expected_ctr` BELOW_AVERAGE → **keyword / match-type / struktur**. Keywordet matcher for bredt eller sidder i en for løs ad group. Lever: stram match-type, flyt til en tættere ad group, eller (Smart Bidding-afhængigt) et bud-signal. Disse er Ads-account-writes → Trin 5.
   - `landing_page_quality` BELOW_AVERAGE → **et FLAG, ikke en score**. Post-click-oplevelsen trækker ned. Anbefal en konkret LP-fix (hastighed, relevans mellem keyword og side, mobil), med keyword + ad group som kontekst. Dette er en klient-side-ændring, ikke en Ads-account-write — altid anbefal-kun. Find aldrig på en numerisk LP-score.
3. **Prioritér efter spend/impressions.** Et QS 1-keyword med høj `cost` er dyrere end et QS 3-keyword med tre impressions. Brug `impressions`/`cost` fra `flagged_keywords` til at rangere, og læn dig på KPI'erne fra AI Context'en.

Formulér alt som forslag til mennesket, aldrig som kommando.

## Trin 5 — Skriv-stien (Ads-side levers, HITL-gated)

Efter samtalen: for de handlinger der ER Google Ads-writes — typisk et bud-adjustment (`update_ad_group_bid`) eller en keyword/match-type-ændring (`update_keyword`, `remove_keyword` + genoprettelse i en tættere ad group) — rutes hver **bekræftet** handling gennem `ads-writer`-agenten via Task, én handling ad gangen. `ads-writer` genformulerer den præcise ændring (customer ID, entitet, felt, gammel → ny værdi), beder om eksplicit per-handling-bekræftelse, og skriver kun på et klart ja. Ingen skill skriver autonomt.

Budstrategi-tjek før du foreslår et bud: på en tCPA/tROAS-konto (fra AI Context-norm) er rå max-CPC ofte ikke leveren — foreslå i stedet mål- eller struktur-justering. Rene budget-writes hører ikke hjemme i dette skill; skulle en dukke op, er de under alle omstændigheder holdt hos `ads-writer` til budget-guardrailen er live.

LP- og creative-fixes rutes IKKE gennem `ads-writer` — de er ikke Ads-account-writes. De leveres som anbefalinger (LP-fix til klienten; RSA-rewrite som en `inb-ads-rsa-copy`/`inb-ads-rsa-hygiene`-overlevering).

## Trin 6 — Output (in-chat)

Lever på dansk:
1. **Overblik:** gennemsnits-QS, antal keywords med QS, og QS-fordelingen (`spend_by_qs` — evt. en lille tekst-tabel eller kort optælling af hvor mange keywords der ligger i QS 1-3).
2. **De værste klynger:** per klynge — ad group, keywords, den dominerende svage komponent, og leveren.
3. **Handlingerne, delt i to spande:**
   - Ads-side (bud/keyword/match-type) → foreslået, klar til `ads-writer` per bekræftelse.
   - Anbefal-kun (LP-fix, RSA-rewrite) → hvad, hvorfor, og hvem der ejer det.
4. **Signifikans-forbeholdet** (se Hårde regler): på små danske konti når QS ofte ikke det volumen der gør komponent-labels stabile — sig det eksplicit hvis `total_keywords_with_qs` eller impressions er lave, og markér lav sikkerhed.

## Hårde regler

- **Recommend-only indtil eksplicit bekræftelse.** Ingen konto-write sker off the back of et QS-fund uden et klart ja; hver Ads-side-write går gennem `ads-writer` per handling. Skillet skriver aldrig autonomt.
- **QS er keyword-grain; landingsside er et flag, ikke en score.** Rapportér flagede keywords (med deres ad group), aldrig en opfundet ad-group-QS, og aldrig en numerisk LP-score.
- **Små danske konti rammer sjældent QS-signal-volumen.** Google-komponent-labels bliver først stabile ved volumen; ved lave impressions/få keywords — flag lav sikkerhed frem for at overfortolke en enkelt BELOW_AVERAGE.
- **LP/creative-fixes er ikke Ads-account-writes** — de leveres som anbefalinger, ikke gennem `ads-writer`.
- **Pausede kampagner ekskluderes** — de er bevidste og flages aldrig som negativt fund.

## Kilder

- `../../shared/quality-score-pull.md` — den delte QS-kontrakt (tool, keyword-grain, dato-gotcha, normaliseret output-form). Citeret, ikke duplikeret.
- `../../shared/client-context-intake.md` — Trin 0 klient-kontekst-intake.
- `lib/quality_score.py` — bundlet, live-verificeret (DSC, 2026-06-05) normaliserings-modul: `date_range_arg()` (afviser `LAST_90_DAYS`-literalen) og `normalise_findings()`.
- `agents/ads-analyst.md` — read-only account analyst; QS-pullen dispatches hertil.
- `agents/ads-writer.md` — den eneste konto-write-sti; bekræftede bud/keyword-ændringer rutes hertil per handling.
