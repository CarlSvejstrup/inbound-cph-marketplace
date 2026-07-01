---
name: inb-ads-campaign-structure
description: Bygger den selvstændige Phase 2-struktur for en Google Ads-kampagne — ad groups, keywords med Exact/Phrase match (aldrig Broad) og negatives — og afleverer den som .xlsx uden nogensinde at skrive til kontoen, til brug når structuring skal køres isoleret fra en fuld kampagne-build.
---

# inb-ads-campaign-structure

Selvstændig indgang til **Phase 2 — structuring** i kampagne-builden. Bygger kontoarkitekturen og
afleverer den som **`.xlsx`** (ad groups, keywords + match types, negatives — tabulært passer bedre end
prosa). Al logik bor i inb-ads-campaign-build's reference; dette skill er en tynd shell der kører den i
**solo-mode** (regnearks-rapport i stedet for kun JSON til en pipeline). Ret `04-structuring.md`, ikke
denne fil, hvis reglerne ændrer sig.

Kilde til sandhed: `${CLAUDE_SKILL_DIR}/../inb-ads-campaign-build/references/04-structuring.md` (+ dens
kontrakter `structuring-rules.md` og `generelle-negative-eksempel.md` i samme mappe).

## Trin 0 — Hent klient-kontekst (AI Context)

> Kaldt via inb-ads-campaign-build-orchestratoren er AI Context allerede hentet og videregivet — kør kun
> dette trin standalone.

Hent klientens AI Context-fil ind i din kontekst før alt andet. Det er en læsning (aldrig gated), men
obligatorisk — den bærer ID'er, kontakter, hårde rammer, navngivningskonvention, budstrategi-norm, KPI'er,
pausede-kampagner-intention. Til structuring vejer to ting tungest: **navngivningskonventionen** (ad
group- og kampagnenavne skal matche kontoens eksisterende mønster) og **klient-specifikke negative
termer** (fødes direkte ind i negatives-tieren oven på den delte MCC-liste).

1. **Identificér klienten.** Uklart hvilken → spørg før du fortsætter.
2. **Åbn master-klientindekset i Drive**: `search_files` efter Google Doc'en `Inbound CPH — Google Ads
   klient-index (AI Context)` (id `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`, i "A - Kunder"). Læs med
   `read_file_content`. Mapper klient → Google Ads ID, HubSpot ID, ClickUp-mappe, **Stage**, Drive-mappe,
   **AI Context-fil**.
3. **Find klientens række** (navn/domæne/Ads-ID). Notér **Stage** — ikke-`customer` betyder ikke-lukket
   konto; antag aldrig en aktiv retainer. Delte mapper (Lime, Retriever/Infomedia, GSGroup, Nemco,
   Julemærket, PhoneAlone, DI) → vælg rækken for det specifikke marked/konto.
4. **Åbn AI Context-`.md`** via Drive-linket (`read_file_content`): ID'er, kontakter, hårde rammer, mål/
   KPI'er, navngivningskonvention, samt link til changelog/optimeringslog (læs den også hvis opgaven
   kræver ændringshistorik).
5. **Så først** starter det egentlige arbejde, med AI Context som ground truth for klient-fakta.

Ingen række eller AI Context-fil endnu: sig det, fortsæt med hvad du kan samle (Drive-mappe, Ads MCP), men
flag hullet — spring aldrig opslaget stille over.

## Trin 1 — Saml input

Som selvstændigt skill arver du ingen Phase-1-output. Saml minimal intake: klientnavn + landingsside-URL +
tema/kampagnetype + geo. Har brugeren allerede et research-grundlag (JSON fra `inb-ads-campaign-research`),
læs det fra arbejdsmappen i stedet for at gen-samle. Mangler landingsside-indsigt helt, kør
`01-landing-page`-mønstret inline som referencen beskriver.

## Trin 2 — Kør referencen

Følg `04-structuring.md` præcist — den vinder ved konflikt:
- Hent den delte negativliste **LIVE** fra MCC'en (read-only GAQL) — ingen API-push, ingen konto-writes;
  al Google Ads-adgang i dette skill er read-only.
- Byg ad groups (få, brede).
- Generér keywords med eksplicit `Exact` eller `Phrase` på hver række — aldrig blankt/bart ord, aldrig
  Broad. Verificér før emit.
- Byg de to negative-tiers + monitor-kandidater.

Referencen skriver `structuring.json` til arbejdsmappen.

## Trin 3 — Aflever regnearket (.xlsx)

Pak resultatet i én `.xlsx` (brug `xlsx`-skillet) med faner der spejler structuring-outputtet:
- **Ad groups:** navn | temperatur | #keywords | tema | landingsside (+ struktur-rationalet øverst).
- **Keywords:** ad group | keyword | match type (med volumen-disclaimer øverst — keywords er tema-afledte,
  validér i Keyword Planner).
- **Negatives:** den delte liste som ÉN reference-linje med det LIVE antal — genudsend aldrig de ~277
  medlemmer som rækker, de påføres by-reference — plus klient-specifikke tilføjelser (term | match type |
  niveau | hvorfor) og monitor-first-kandidater separat.

At gemme til Drive er en gated write (bekræft før upload). Lokalt er fint.
