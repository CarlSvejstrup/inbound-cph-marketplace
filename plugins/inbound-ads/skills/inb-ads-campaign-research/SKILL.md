---
name: inb-ads-campaign-research
description: Kører kampagne-buildens Phase-1 research som selvstændigt trin — landingsside-positionering, konkurrent-analyse og kampagne-strategi, hele bundtet eller ét enkelt stykke — og afleverer en samlet, læsbar .docx-rapport, read-only mod web og Google Ads MCP uden nogensinde at skrive til kontoen.
---

# inb-ads-campaign-research

Selvstændig indgang til **Phase-1 research** i kampagne-builden. Kører ét eller alle tre research-trin og
afleverer en samlet **`.docx`-rapport** mennesket kan læse og dele. Al logikken bor i inb-ads-campaign-build's
referencer — dette skill er en tynd shell der kører dem i **solo-mode** (forbruger ikke en pipeline,
producerer en rapport-fil i stedet for kun JSON).

De tre research-referencer (kilden til sandhed):
- `${CLAUDE_SKILL_DIR}/../inb-ads-campaign-build/references/01-landing-page.md` — landingsside-positionering
- `${CLAUDE_SKILL_DIR}/../inb-ads-campaign-build/references/02-competitor.md` — konkurrent-analyse
- `${CLAUDE_SKILL_DIR}/../inb-ads-campaign-build/references/03-campaign-strategy.md` — kampagne-strategi + settings

## Trin 0 — Hent klient-kontekst (AI Context)

> Kaldes skillet via inb-ads-campaign-build-orchestratoren, er AI Context allerede hentet og videregivet — så er dette trin et no-op. Kør det kun når skillet kaldes standalone.

1. **Identificér klienten.** Tag den klient brugeren nævner (navn, domæne eller konto). Uklart → spørg hvilken klient før du fortsætter.
2. **Åbn master-klientindekset i Drive** via Drive-connectoren: `search_files` efter Google Doc'en `Inbound CPH — Google Ads klient-index (AI Context)` (id `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`, i "A - Kunder"-mappen), læs med `read_file_content`. Den mapper hver klient til Google Ads ID, HubSpot ID, ClickUp-mappe, **Stage**, Drive-mappe og **AI Context-fil**.
3. **Find klientens række** (match på navn/domæne/Ads-ID). Notér **Stage** (customer / lead / opportunity / "ikke tagget") — en ikke-`customer`-stage betyder en ikke-lukket konto; vægt anbefalinger derefter og antag aldrig en aktiv retainer. For delte mapper (Lime, Retriever/Infomedia, GSGroup, Nemco, Julemærket, PhoneAlone, DI) vælg rækken for det specifikke marked/konto.
4. **Åbn klientens AI Context-`.md`** via Drive-linket i indeksrækken (`read_file_content`). Den indeholder driftsbriefen: ID'er, kontakter, hårde rammer, mål/KPI'er, navngivningskonvention, sådan-kører-vi-den, plus link til changelog/optimeringslog (læs det med, hvis opgaven kræver ændringshistorik).
5. Først derefter starter du skillens egentlige arbejde, med AI Context som ground truth for klient-fakta.

Ingen række i indekset eller ingen AI Context-fil endnu: sig det, fortsæt med den kontekst du kan samle (Drive-mappe, Ads MCP), men flag hullet.

## Trin 1 — Hvad skal køres?

Læs hvad brugeren bad om:
- **Hele research-bundtet** ("lav research på [klient]") → kør alle tre referencer.
- **Ét stykke** ("analyser landingsside" / "konkurrent-research" / "kampagne-strategi") → kør kun den
  matchende reference. Spørg ikke om de andre to medmindre brugeren vil have dem.

## Trin 2 — Saml minimal intake

Som selvstændigt skill arver du ingen pipeline-kontekst. Saml det referencen kræver (typisk klient +
landingsside-URL + geo; konkurrent-trinnet beder også om konkurrent-navne; strategi-trinnet kører
`list_accessible_accounts` til konto-match). Følg hver references egne intake-trin.

## Trin 3 — Kør reference(rne)

Følg den/de valgte references trin præcist — referencen vinder ved konflikt, og logikken bor der, ikke
her (ændrer en research-regel sig, rettes den i `inb-ads-campaign-build/references/`, og dette skill arver
det automatisk). Scraping og Google Ads MCP-reads er frie; ingen API-push, ingen konto-writes — dette
skill er read-only. Hver reference skriver sit JSON (`landing-page-analysis.json` /
`competitor-research.json` / `campaign-strategy.json`) til en lokal arbejdsmappe; konkurrent-research har
ingen vedvarende lager (per-kørsel scope-guardrail i `02-competitor.md`). Det er solo-mode, så du stopper
IKKE for en pipeline-gate — du går videre til rapporten.

## Trin 4 — Aflever rapporten (.docx)

Pak resultatet i én læsbar `.docx` (brug `docx`-skillet). Research er prosa-tungt — en docx læser bedre
end et regneark. Struktur:
- **Landingsside:** produkt, top-USP'er, tone, trust-tal (verbatim), aktivt tilbud, sprog.
- **Konkurrenter:** differentierings-liste, "sea of sameness", positionerings-huller, tabel per konkurrent.
- **Strategi:** de 6 klyngers valg (type/mål, budstrategi + budget-rationale, conversion action, targeting,
  tracking-gate, kampagnenavn).
- Kørte du kun ét trin, aflever kun den sektion.

Følg datakilde-ærligheden fra referencerne (Semrush er cut; konkurrent-annoncetekst ikke hentbar; keywords
tema-afledte). At gemme rapporten til Drive er en ekstern write — gated, bekræft før upload
(human-in-the-loop). Lokalt er fint.
