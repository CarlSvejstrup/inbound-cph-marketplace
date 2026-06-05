---
name: landing-page-analyzer
description: Analyser en kundes landingsside og udtræk struktureret positionering (produkt, USP'er, tone, CTA'er, trust-tal, aktivt tilbud, sprog) som JSON til kampagne-byggeren. Phase-1 research-skill i campaign-build — fødes ind i structuring + RSA-tekster. Læser kun (scraper en offentlig side), skriver ingen eksterne writes. Brug når brugeren siger "analyser landingsside", "udtræk positionering fra [URL]", "landing page analyse", eller starter en campaign-build-kørsel. Svarer på dansk.
---

# landing-page-analyzer

Phase-1 research-skill i den modulære **campaign-build**-workflow. Tager én landingsside-URL og udtrækker et struktureret positioneringsbillede (produkt, USP-kandidater, tone, CTA'er, trust-tal, aktivt tilbud, sprog) som JSON. Output forbruges af **structuring** (Phase 2) og **rsa-copywriter** (Phase 3).

Dette skill ejer den **delte page-extraction-kontrakt** (`references/page-extraction.md` + `page-extraction-schema.json`). `competitor-research` peger den samme ekstraktion mod konkurrenters sider; den shippede `responsive-search-ads` Trin 2 forbruger den senere (Phase-3-integration, ikke gjort endnu).

## Hvorfor dette skill findes

Ad-teamet starter altid med landingssiden — alt copy skal matche siden for høj Quality Score, og alle claims skal stå på siden (vi opfinder ikke tal). I dag laver `responsive-search-ads` denne analyse inline (Trin 2). I campaign-build kører den som et selvstændigt parallelt research-trin, så structuring og RSA bygger på ét fælles, kontrolleret faktagrundlag i stedet for hver sin ad-hoc-læsning.

## When to use

Trigger-fraser: "analyser landingsside", "udtræk positionering fra [URL]", "landing page analyse", eller automatisk som første parallel-trin i en campaign-build-kørsel.

## How it works (architecture — read once)

Firecrawl-`scrape` til markdown → DU (modellen) udtrækker felterne fra markdown'en → de tre firewall-regler anvendes → struktureret JSON emitteres. Dette er præcis samme mønster som de shippede skills (`responsive-search-ads` Trin 2, `ads-audit-report` Trin 3): scrape til markdown, læs, udtræk. Ingen scripts nødvendige. Kører i Cowork og lokalt — eneste forudsætning er `firecrawl`-CLI'en.

**Vigtigt:** `firecrawl scrape` har INGEN `--schema-file`-flag (verificeret 2026-06-03) — det flag bor på `firecrawl agent`, som vi ikke bruger her. `page-extraction-schema.json` er felt-kontrakten du udtrækker *mod* (og kan validere mod), ikke et CLI-argument.

## Trin 0 — Kontekst

Læs `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` før noget andet (write-gate + sprogpolitik). **At scrape en offentlig side er en read, ikke en ekstern write — ingen write-gate.** Men oplys hvilken URL du rammer. Alt foregår på dansk medmindre brugeren skriver på engelsk.

Læs derefter `${CLAUDE_PLUGIN_ROOT}/skills/landing-page-analyzer/references/page-extraction.md` — den definerer felterne, de tre firewall-regler og output-formen. Den vinder ved enhver konflikt med dette skill.

## Trin 1 — Intake (minimal)

Dette er et **ubemandet research-trin**, ikke det menneske-tunge RSA-intake. Det eneste påkrævede input er **URL'en**.

- Hvis skillet kaldes af campaign-build-orkestratoren med en URL (og evt. forventet annoncetekst-sprog), spørg **ingenting** — kør direkte.
- Hvis kaldt manuelt uden URL: ét `AskUserQuestion` med URL'en (og evt. forventet annoncesprog som andet felt, default dansk). Følg hus-reglen fra `responsive-search-ads` (anbefalet-option først, "Other" altid muligt) — men hold dig til dette ene kald.

Option-præsentation og menneske-godkendelse af det udtrukne ligger IKKE her — det hører til Phase-2 structuring-gaten. Dette skill udtrækker kandidater; mennesket vælger senere.

## Trin 2 — Scrape + udtræk

Kør ekstraktionen som beskrevet i `references/page-extraction.md` — scrape til markdown, læs den, udtræk felterne:

```bash
firecrawl scrape "<final_url>" --only-main-content -o .firecrawl/page.md
```

Læs `.firecrawl/page.md` og udfyld felterne i `page-extraction-schema.json` ved at læse siden. Brug IKKE `firecrawl agent` (autonom multi-side, flere credits). Hvis siden ikke kan hentes: sig det og stop — vi opfinder ikke felter.

Anvend derefter de tre firewall-regler fra reference-filen på råudtrækket:
1. Trust-signaler er verbatim; `has_numbers` kun når der står et brugbart tal. Intet tal → tom liste, ingen opfundne claims.
2. Aktivt tilbud → `expiry` påkrævet (dato eller `"unknown"`).
3. `page_language` detekteres; sæt `language_note` hvis det kan afvige fra brugerens valgte annoncesprog — skift aldrig sprog stiltiende.

## Trin 3 — Emit JSON

Skriv output-JSON'en (formen i reference-filen) til kørslens artefakt-mappe, fx `.firecrawl/landing-page-analysis.json` eller den sti orkestratoren angiver. Stempl `scraped_at` efter kørslen. Sæt `extraction_confidence` (`high`/`partial`/`low`) og `missing_fields` ærligt: `partial`/`low` når USP'er, trust eller tilbud ikke kunne findes, med hullerne listet.

At skrive denne JSON-fil til disk i kørslens egen artefakt-mappe er en lokal arbejdsfil, ikke en ekstern write (ingen Drive/mail/API). Hvis brugeren beder om at gemme den et delt sted (Drive), er DET en ekstern write og gates.

## Trin 4 — Output

Lever:
1. **Stien** til JSON-filen.
2. **En kort tabel** der viser hvad der blev udtrukket (produkt, top-3 USP'er, tone, trust-tal, tilbud + udløb, sprog) så brugeren ser grundlaget.
3. **Hvilken URL** der blev scrapet og med hvilket værktøj.
4. Hvis `extraction_confidence` er `partial`/`low`: nævn hvad der mangler, så structuring-gaten ved hvad mennesket skal udfylde.

## Eksempel-output

```
Landingsside analyseret: https://acme.dk/ydelse
Værktøj: firecrawl scrape --only-main-content (markdown) + LLM-udtræk
JSON: .firecrawl/landing-page-analysis.json

| Felt | Værdi |
|---|---|
| Produkt | Erhvervsrengøring til kontorer |
| Top-USP'er | Fast pris uden tillæg; samme team hver gang; miljøcertificeret |
| Tone | venlig-direkte |
| Trust-tal | "4.8 stjerner fra 1.200 anmeldelser" (tal: ja) |
| Tilbud | Ingen aktivt tilbud |
| Sprog | da |

Konfidens: high. Klar til structuring + RSA.
```

## Maintenance

- Feltlisten, firewall-reglerne og JSON-formen bor ÉT sted: `references/page-extraction.md` + `page-extraction-schema.json`. Ret kun dem; alle tre forbrugere (dette skill, `competitor-research`, senere RSA Trin 2) følger med.
- `firecrawl scrape --format branding` blev overvejet til brand/logo men er ikke verificeret på danske SMB-sider — `json`-skemaet udtrækker allerede `brand`. Spot-test `branding` før det evt. tilføjes.
