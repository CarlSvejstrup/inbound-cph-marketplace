---
name: research
description: Kør Phase-1 kampagne-research for en klient som selvstændigt trin og aflever en samlet rapport (.docx) — landingsside-positionering, konkurrent-analyse og kampagne-strategi/settings. Tynd indgang til de tre research-referencer i campaign-build; kan køre hele research-bundtet eller ét enkelt stykke (kun landingsside, kun konkurrenter, kun strategi) afhængigt af hvad brugeren beder om. Læser kun (web + Google Ads MCP), pusher ALDRIG til kontoen. Brug når brugeren siger "lav research på [klient]", "analyser landingsside", "udtræk positionering fra [URL]", "konkurrent-research", "hvad gør konkurrenterne", "kampagne-strategi", "campaign settings til [klient]", eller vil have research-grundlaget før en kampagne bygges. Svarer på dansk.
---

# research

Selvstændig indgang til **Phase-1 research** i kampagne-builden. Kører ét eller alle tre research-trin og
afleverer en samlet **`.docx`-rapport** mennesket kan læse og dele. Al logikken bor i campaign-build's
referencer — dette skill er en tynd shell der kører dem i **solo-mode** (forbruger ikke en pipeline,
producerer en rapport-fil i stedet for kun JSON).

De tre research-referencer (kilden til sandhed):
- `${CLAUDE_SKILL_DIR}/../campaign-build/references/01-landing-page.md` — landingsside-positionering
- `${CLAUDE_SKILL_DIR}/../campaign-build/references/02-competitor.md` — konkurrent-analyse
- `${CLAUDE_SKILL_DIR}/../campaign-build/references/03-campaign-strategy.md` — kampagne-strategi + settings

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
  `campaign-build/references/` — dette skill arver det automatisk.
- **Ingen vedvarende konkurrent-lager** (per-kørsel scope-guardrail i `02-competitor.md`).
