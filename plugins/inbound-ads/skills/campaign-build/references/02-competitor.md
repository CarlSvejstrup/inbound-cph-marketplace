# Phase 1b — competitor (konkurrent-positionering)

Phase-1 research-trin. Kortlægger kundens konkurrent-landskab på build-tidspunktet og udleder det
structuring + RSA-copy faktisk har brug for: en **differentierings-liste** (hvad kunden kan eje) + et
**"sea of sameness"-kort** (commoditiserede claims annoncerne skal undgå) + **positionerings-huller**
(white space). Output forbruges af `04-structuring` (Phase 2) og `05-rsa-copy` (Phase 3).

Genbruger den delte page-extraction-kontrakt fra `01-landing-page` — det er landingsside-analysen peget
mod konkurrenternes sider plus et synteselag ovenpå. Pipeline-mode-først; `research`-shell-skillet
wrapper solo-mode.

## Datakilde-virkelighed (læs først)

Testet live 2026-06-03 mod de tilsluttede MCP'er:

- **Semrush MCP er plan-gated** og er CUT fra denne suite — afhæng ALDRIG af Semrush. Konkurrent-
  *opdagelse* via bruger-input er den primære vej (Trin 1).
- **Google Ads MCP rækker kun til kundens EGNE konti** og har ingen konkurrent-flade
  (`auction_insight_domain` er `UNRECOGNIZED_FIELD`). Ingen konkurrent-domæner/-spend/-annoncetekst via
  API'et. Kald det IKKE herfra.
- **`web_fetch` henter konkurrenternes egne sider** (indbygget værktøj, virker i Cowork). Kør den delte
  ekstraktion mod hver side. En valgfri SERP-søgning kan bruges til *opdagelse* hvis firecrawl-CLI'en er
  tilgængelig — gør den aldrig til en forudsætning.

**Ærlig forventningsafstemning:** vi leverer konkurrent-positionering fra deres EGNE sider — IKKE deres
faktiske annoncetekster eller spend (ikke teknisk hentbart i denne stack).

## Scope-guardrails (per-kørsel — ALDRIG H2-substrat)

Bevidst **single-client, per-kørsel**. IKKE det parkerede H2 cross-client Supabase-substrat:

1. **Intet vedvarende lager.** Ingen Supabase, ingen DB-write, ingen cross-run-cache. Kun kørslens
   artefakt-mappe.
2. **Output dør med kørslen.** `competitor-research.json` er scoped til *denne* kunde + *denne* kampagne.
3. **Konkurrent-listen leveres per kørsel**, aldrig hentet fra hukommelse.
4. **Én kunde per kørsel.** Ingen batching.
5. **Ingen konkurrent-identitet ud over kørslen.** Vil Ian senere have H2-substratet, er det et separat
   commissioned build — flag det, byg det ikke på forhånd.

## Trin 0 — Kontekst

Læs `${CLAUDE_SKILL_DIR}/references/page-extraction.md` — den delte ekstraktion du kører mod
konkurrent-URL'er. Dansk medmindre brugeren skriver engelsk. Scraping er en read; oplys hvilke URL'er du
rammer.

## Trin 1 — Intake

I pipeline-mode arver du klient + URL + kerne-ydelse + geo fra orkestratoren — spørg ikke igen.
**Konkurrent-identifikation** er det ene du typisk mangler: ét `AskUserQuestion` — "Hvem er klientens 3-5
vigtigste konkurrenter?" Valgfri sti hvis firecrawl-CLI'en findes: en SERP-søgning på kerne-ydelse + geo,
præsentér fundne domæner som options. **Auto-vælg aldrig** — brugeren bekræfter det endelige
konkurrent-sæt (også en scope-guardrail).

## Trin 2 — Hent hver konkurrent (web_fetch)

For hver bekræftet konkurrent-URL: kør den delte ekstraktion, præcis som `01-landing-page` (hent med
`web_fetch`, udtræk mod `page-extraction-schema.json`), men mod konkurrentens side. Kan en side ikke
hentes: marker `scraped_ok: false`, opfind intet.

## Trin 3 — Syntese (trinnets egentlige intelligens)

Læs de udtrukne konkurrent-positioneringer + klientens egen (fra `landing-page-analysis.json` hvis
tilgængelig) og udled:

- **`differentiator_list`** — hvad kunden kan eje, fordi få/ingen konkurrenter siger det. DEN primære
  leverance.
- **`sea_of_sameness`** — claims ALLE bruger (commoditiseret) → RSA skal undgå at lede med dem.
- **`positioning_gaps`** — white space ingen konkurrent besætter.
- **`angle_recommendations`** — mappet til vinkel-taksonomien i
  `${CLAUDE_SKILL_DIR}/../responsive-search-ads/references/headline-craft.md` (benefit, trust, urgency,
  CTA, feature, keyword-led, brand, location, garanti). Sømmen: dette trin anbefaler *hvilke vinkler der
  differentierer vs. er bordkant*; RSA udfører copyen.
- **`vocabulary_overlap`** — termer konkurrenterne bruger for samme ydelse (keyword-seeds + negative-hints
  til structuring).

**Firewall (samme som RSA):** hver claim skal kunne spores til en scrapet side. Ingen opfundne claims,
ingen generisk "de siger alle kvalitet" uden belæg. Citer hvilken konkurrent sagde hvad.

## Trin 4 — Emit JSON

Skriv `competitor-research.json` til artefakt-mappen (lokal arbejdsfil). Form:

```json
{
  "client": "Acme A/S", "client_url": "https://acme.dk/ydelse", "run_date": "<stamp efter kørsel>",
  "competitors": [
    { "name": "Konkurrent A", "url": "https://...", "source": "user-named", "scraped_ok": true,
      "usps": ["..."], "ctas": ["..."], "trust_signals": ["..."],
      "active_offer": "string|null", "positioning_summary": "..." }
  ],
  "synthesis": {
    "differentiator_list": ["..."], "sea_of_sameness": ["..."], "positioning_gaps": ["..."],
    "angle_recommendations": [ { "angle": "garanti", "rationale": "ubesat af konkurrenter" } ],
    "vocabulary_overlap": ["..."]
  },
  "data_sources": ["firecrawl"],
  "notes": "Semrush utilgængelig (cut); konkurrenter user-named. Konkurrent-annoncetekst ikke hentbar."
}
```

`source` er `"user-named"` eller `"firecrawl-serp"`. Per-konkurrent `trust_signals`/`active_offer` er
bevidst SAMMENFATTEDE strenge — den strukturerede firewall gælder kun KUNDENS side (`01-landing-page`).
Downstream læser KUN `synthesis`-blokken, så den fladere form her er uskadelig.

## Trin 5 — Returnér

Returnér: differentierings-listen, "undgå disse commoditiserede claims"-listen, en kort tabel per
konkurrent, og datakilderne ærligt (kun Firecrawl; Semrush utilgængelig; annoncetekst ikke hentbar).
Slå scope-grænsen fast: analyseret de navngivne konkurrenter for DENNE kørsel alene.

## Maintenance

Ekstraktionen bor i `page-extraction.md` — ret den ÉT sted. Vinkel-taksonomien bor i
`responsive-search-ads/references/headline-craft.md`. **Ingen scripts** — ren JSON-syntese, hold det
script-frit.
