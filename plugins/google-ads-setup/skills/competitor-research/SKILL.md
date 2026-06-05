---
name: competitor-research
description: Kortlæg en kundes konkurrent-positionering ved at scrape konkurrenternes egne sider og udlede en differentierings-liste + "sea of sameness"-kort, så annoncerne ikke drukner i ens budskaber. Phase-1 research-skill i campaign-build — fødes ind i structuring + RSA-tekster. Single-client, per-kørsel, ingen vedvarende database. Leverer positionering fra konkurrenternes EGNE sider, IKKE deres annoncetekster eller spend (kan ikke hentes). Brug når brugeren siger "konkurrent-research", "hvad gør konkurrenterne", "positionerings-analyse", eller starter en campaign-build-kørsel. Svarer på dansk.
---

# competitor-research

Phase-1 research-skill i **campaign-build**. Kortlægger kundens konkurrent-landskab på build-tidspunktet og udleder den ene ting structuring + RSA-copy faktisk har brug for: en **differentierings-liste** (hvad kunden kan eje) + et **"sea of sameness"-kort** (commoditiserede claims annoncerne skal undgå) + **positionerings-huller** (white space). Output forbruges af structuring (Phase 2) og rsa-copywriter (Phase 3).

Skillet genbruger den delte page-extraction-kontrakt fra `landing-page-analyzer` — det er **landingsside-analysen peget mod konkurrenternes sider** plus et synteselag ovenpå.

## Det vigtigste at vide først (datakilde-virkelighed)

Testet live 2026-06-03 mod de tilsluttede MCP'er:

- **Semrush MCP er plan-gated** — hver rapport (`organic_research`, `overview_research`, `keyword_research`) returnerer samme stub: brugeren har ikke en Semrush-plan med MCP-adgang. **Nul data på nuværende plan.** Design ALDRIG skillet til at afhænge af Semrush; det er en upgrade-gated fremtidig forbedring til konkurrent-*opdagelse*.
- **Google Ads MCP rækker kun til kundens EGNE konti** (under MCC'en) og har ingen konkurrent-flade: `auction_insight_domain` er `UNRECOGNIZED_FIELD` i GAQL. Ingen konkurrent-domæner, -impression share eller -annoncetekst via API'et. Kald det IKKE fra dette skill.
- **Firecrawl er den eneste virkende eksterne datasti.** Scrape konkurrenternes egne sider med den delte ekstraktion.

**Ærlig forventningsafstemning (sig det til Ian/brugeren):** vi leverer konkurrent-**positionering fra deres egne sider** — IKKE deres faktiske annoncetekster eller spend (ikke teknisk hentbart i denne stack). `ads-audit` behandler allerede "hvad gør konkurrenterne" som en manuel-gennemgang-placeholder; dette skill foregiver ikke andet.

## When to use

Trigger-fraser: "konkurrent-research", "hvad gør konkurrenterne", "positionerings-analyse", "differentierings-analyse", eller automatisk som parallelt Phase-1-trin i en campaign-build-kørsel.

## Scope-guardrails (per-kørsel — ALDRIG H2-substrat)

Dette skill er bevidst **single-client, per-kørsel**. Det er IKKE det parkerede H2 cross-client Supabase-konkurrent-substrat. Hårde regler:

1. **Intet vedvarende lager.** Ingen Supabase, ingen DB-write, ingen cross-run-cache, ingen append til en delt fil. Kun kørslens egen artefakt-mappe.
2. **Output dør med kørslen.** `competitor-research.json` er scoped til *denne* kunde + *denne* kampagne.
3. **Konkurrent-listen leveres per kørsel, aldrig hentet fra hukommelse.** Ingen "huskede konkurrenter for kunde X".
4. **Én kunde per kørsel.** Ingen batching på tværs af kunder.
5. **Ingen konkurrent-identitet ud over kørslen.** Skriv ikke konkurrentnavne/USP'er nogen vedvarende steder. Vil Ian senere have H2-substratet, er det et separat, commissioned build — flag det, byg det ikke på forhånd.

Lakmustest: kør skillet to gange for to kunder — intet fra kørsel 1 må være synligt i kørsel 2.

## Trin 0 — Kontekst

Læs `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` (write-gate + sprog). Læs `${CLAUDE_PLUGIN_ROOT}/skills/landing-page-analyzer/references/page-extraction.md` — den delte ekstraktion du kører mod konkurrent-URL'er. Dansk medmindre brugeren skriver på engelsk. Scraping af offentlige sider er en read; oplys hvilke URL'er du rammer.

## Trin 1 — Intake (få AskUserQuestion-kald, mange felter)

Følg hus-reglen fra `responsive-search-ads` (anbefalet-option først, "Other" altid muligt, saml felter).

- **Klient + URL + kerne-ydelse + geo** — arv fra campaign-build-kørslen hvis kædet; spørg ikke igen.
- **Konkurrent-identifikation (ask-user-primær, fordi Semrush er død):** ét `AskUserQuestion`: "Hvem er klientens 3-5 vigtigste konkurrenter?" Tilbyd en valgfri sti: "Eller lad mig finde kandidater via en SERP-søgning" → Firecrawl `search` på kerne-ydelse + geo, præsentér fundne domæner som options, brugeren bekræfter. **Auto-vælg aldrig** — brugeren bekræfter det endelige konkurrent-sæt (det er også en scope-guardrail).

## Trin 2 — Scrape hver konkurrent (Firecrawl)

For hver bekræftet konkurrent-URL: kør den delte ekstraktion, præcis som `landing-page-analyzer` gør (scrape til markdown, læs, udtræk mod `page-extraction-schema.json`), men mod konkurrentens side. Kan en side ikke hentes: marker `scraped_ok: false`, opfind intet.

```bash
firecrawl scrape "<competitor_url>" --only-main-content -o ".firecrawl/competitor-<n>.md"
```

Læs hver `.md` og udtræk felterne. `firecrawl scrape` har ingen `--schema-file`-flag (verificeret 2026-06-03) — skemaet er felt-kontrakten du udtrækker mod, ikke et CLI-argument.

## Trin 3 — Syntese (skillets egentlige intelligens)

Læs de udtrukne konkurrent-positioneringer + klientens egen (fra `landing-page-analyzer` hvis tilgængelig) og udled:

- **`differentiator_list`** — hvad kunden kan eje, fordi få/ingen konkurrenter siger det. **DEN primære leverance.**
- **`sea_of_sameness`** — claims/fraser ALLE bruger (commoditiseret) → RSA skal undgå at lede med dem.
- **`positioning_gaps`** — white space ingen konkurrent besætter.
- **`angle_recommendations`** — mappet til vinkel-taksonomien i `responsive-search-ads/references/headline-craft.md` (benefit, trust, urgency, CTA, feature, keyword-led, brand, location, garanti). Dette er sømmen: competitor-research anbefaler *hvilke vinkler der differentierer vs. er bordkant*, RSA udfører copyen.
- **`vocabulary_overlap`** — termer konkurrenterne bruger for samme ydelse (keyword-seeds + negative-hints til structuring).

**Firewall (samme som RSA):** hver claim skal kunne spores til en scrapet side. Ingen opfundne claims, ingen generisk "de siger alle kvalitet" uden belæg. Citer hvilken konkurrent sagde hvad.

## Trin 4 — Emit JSON

Skriv `competitor-research.json` til kørslens artefakt-mappe (lokal arbejdsfil, ikke ekstern write). Form:

```json
{
  "client": "Acme A/S",
  "client_url": "https://acme.dk/ydelse",
  "run_date": "<stamp efter kørsel>",
  "competitors": [
    {
      "name": "Konkurrent A", "url": "https://...", "source": "user-named",
      "scraped_ok": true,
      "usps": ["..."], "ctas": ["..."], "trust_signals": ["..."],
      "active_offer": "string|null", "positioning_summary": "..."
    }
  ],
  "synthesis": {
    "differentiator_list": ["..."],
    "sea_of_sameness": ["..."],
    "positioning_gaps": ["..."],
    "angle_recommendations": [ { "angle": "garanti", "rationale": "ubesat af konkurrenter" } ],
    "vocabulary_overlap": ["..."]
  },
  "data_sources": ["firecrawl"],
  "notes": "Semrush MCP utilgængelig på nuværende plan; konkurrenter user-named. Konkurrent-annoncetekst ikke hentbar."
}
```

`source` er `"user-named"` eller `"firecrawl-serp"`.

**NB — per-konkurrent `trust_signals`/`active_offer` er bevidst SAMMENFATTEDE strenge**, ikke
den strukturerede `{claim, has_numbers}` / `{present, text, expiry}`-form fra den delte
page-extraction-kontrakt. Den strukturerede firewall gælder KUNDENS side (landing-page-analyzer).
Downstream (structuring + rsa-copywriter) læser KUN `synthesis`-blokken
(`differentiator_list`/`sea_of_sameness`/`positioning_gaps`/`angle_recommendations`) — aldrig
konkurrenternes trust/offer — så den fladere form her er uskadelig.

## Trin 5 — Output + handoff

Lever: differentierings-listen, "undgå disse commoditiserede claims"-listen, og en kort tabel per konkurrent. Oplys datakilder ærligt (kun Firecrawl; Semrush utilgængelig; annoncetekst ikke hentbar). Slut med at slå scope-grænsen fast: analyseret de navngivne konkurrenter for DENNE kørsel alene.

## Maintenance

- Ekstraktionen bor i `landing-page-analyzer/references/page-extraction.md` — ret den ÉT sted; dette skill følger med. Vinkel-taksonomien bor i `responsive-search-ads/references/headline-craft.md`.
- Hvis Semrush-planen opgraderes: `semrush-research`-skillet (samme plugin) bliver den stærke sti til konkurrent-*opdagelse* + keyword-gap via `organic_research`. Tilføj dens output som en valgfri discovery-kilde i Trin 1 — gør den aldrig til en afhængighed (dette skill forbliver Firecrawl-primært).
- **Ingen scripts** — output er ren JSON-syntese (LLM-ræsonnement), ingen beregning. Hold det script-frit.
