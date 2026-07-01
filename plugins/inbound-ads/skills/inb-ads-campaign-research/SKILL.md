---
name: inb-ads-campaign-research
description: Kør Phase-1 kampagne-research for en klient som selvstændigt trin og aflever en samlet rapport (.docx) — landingsside-positionering, konkurrent-analyse og kampagne-strategi/settings. Tynd indgang til de tre research-referencer i inb-ads-campaign-build; kan køre hele research-bundtet eller ét enkelt stykke (kun landingsside, kun konkurrenter, kun strategi) afhængigt af hvad brugeren beder om. Læser kun (web + Google Ads MCP), pusher ALDRIG til kontoen. Brug når brugeren siger "lav research på [klient]", "analyser landingsside", "udtræk positionering fra [URL]", "konkurrent-research", "hvad gør konkurrenterne", "kampagne-strategi", "campaign settings til [klient]", eller vil have research-grundlaget før en kampagne bygges. Svarer på dansk.
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

> Når inb-ads-campaign-research kaldes via inb-ads-campaign-build-orchestratoren er AI Context allerede hentet og videregivet — så er dette trin et no-op; kør det kun når skillet kaldes standalone.

Før al anden handling på en navngiven klient skal du hente klientens AI Context-fil ind i din kontekst. Det er en læsning (aldrig gated), men obligatorisk — sådan arver du alt Inbound ved om klienten (ID'er, kontakter, hårde rammer, navngivningskonvention, budstrategi-norm, KPI'er, pausede-kampagner-intention) i stedet for at starte blindt.

1. **Identificér klienten (kunden).** Tag den klient brugeren nævner (navn, domæne eller konto). Er det uklart, så spørg hvilken klient før du fortsætter.
2. **Åbn master-klientindekset i Drive** via Drive-connectoren: `search_files` efter Google Doc'en med titlen `Inbound CPH — Google Ads klient-index (AI Context)` (aktuelt id `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`, i "A - Kunder"-mappen). Læs den med `read_file_content`. Den mapper hver klient til Google Ads ID, HubSpot ID, ClickUp-mappe, **Stage**, Drive-mappe og **AI Context-fil**.
3. **Find klientens række** (match på navn/domæne/Ads-ID). Notér **Stage** (customer / lead / opportunity / "ikke tagget") — en ikke-`customer`-stage betyder en ikke-lukket konto; vægt anbefalinger derefter og antag aldrig en aktiv retainer. For delte mapper (Lime, Retriever/Infomedia, GSGroup, Nemco, Julemærket, PhoneAlone, DI) vælg rækken for det specifikke marked/konto.
4. **Åbn klientens AI Context-`.md`** via Drive-linket i indeksrækken (`read_file_content`) og tag den ind i din kontekst. Den indeholder driftsbriefen: ID'er, kontakter, hårde rammer (læs før du handler), mål/KPI'er, navngivningskonvention, sådan-kører-vi-den, samt link til changelog/optimeringslog (læs også changelog-doc'et hvis opgaven kræver ændringshistorik — den holdes separat, linket fra AI Context-filen).
5. **Først derefter** starter du skillens egentlige arbejde, med AI Context som ground truth for klient-fakta.

Har klienten ingen række i indekset eller ingen AI Context-fil endnu: sig det, og fortsæt med den kontekst du kan samle (Drive-mappe, Ads MCP) — men flag hullet. Spring aldrig opslaget stille over.

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

Følg den/de valgte references trin præcist — den vinder ved konflikt. Hver reference skriver sit JSON
(`landing-page-analysis.json` / `competitor-research.json` / `campaign-strategy.json`) til en lokal
arbejdsmappe. Det er solo-mode, så du stopper IKKE for en pipeline-gate — du går videre til rapporten.

## Trin 4 — Aflever rapporten (.docx)

Pak resultatet i én læsbar `.docx` (brug `docx`-skillet). Research er prosa-tungt — en docx læser bedre
end et regneark. Struktur:
- **Landingsside:** produkt, top-USP'er, tone, trust-tal (verbatim), aktivt tilbud, sprog.
- **Konkurrenter:** differentierings-liste, "sea of sameness", positionerings-huller, tabel per konkurrent.
- **Strategi:** de 6 klyngers valg (type/mål, budstrategi + budget-rationale, conversion action, targeting,
  tracking-gate, kampagnenavn).
- Kørte du kun ét trin, aflever kun den sektion.

Følg datakilde-ærligheden fra referencerne (Semrush er cut; konkurrent-annoncetekst ikke hentbar; keywords
tema-afledte). At gemme rapporten til Drive er en ekstern write → gated (bekræft før upload). Lokalt er fint.

## Safety

- **Read-only.** Scraping + Google Ads MCP-reads er frie; ingen API-push, ingen konto-writes.
- **Gem til Drive er en gated write** — bekræft før upload (human-in-the-loop).
- **Logikken bor i referencerne, ikke her.** Ændrer en research-regel sig, rettes referencen i
  `inb-ads-campaign-build/references/` — dette skill arver det automatisk.
- **Ingen vedvarende konkurrent-lager** (per-kørsel scope-guardrail i `02-competitor.md`).
