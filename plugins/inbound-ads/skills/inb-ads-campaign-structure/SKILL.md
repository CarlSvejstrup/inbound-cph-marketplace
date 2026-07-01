---
name: inb-ads-campaign-structure
description: Byg en ny Google Ads-kampagnes kontostruktur som selvstændigt trin og aflever den som regneark (.xlsx) — ad groups (få, brede), keyword-selektion + match types (Exact + udvalgt Phrase, ALDRIG Broad), og klient-specifikke negative tilføjelser oven på Inbounds delte MCC-negativliste. Tynd indgang til structuring-referencen i inb-ads-campaign-build, kørt i solo-mode. Læser kun fra Google Ads MCP, pusher ALDRIG til kontoen. Brug når brugeren siger "byg kampagne-struktur", "structuring", "ad groups + keywords til [klient]", "lav keyword-strukturen", "strukturér kampagnen", eller vil have kontostrukturen som et selvstændigt stykke (ikke en fuld build). Svarer på dansk.
---

# inb-ads-campaign-structure

Selvstændig indgang til **Phase 2 — structuring** i kampagne-builden. Bygger kontoarkitekturen og
afleverer den som et **`.xlsx`-regneark** (ad groups, keywords + match types, negatives — tabulært, så et
regneark passer bedre end prosa). Al logikken bor i inb-ads-campaign-build's reference — dette skill er en tynd
shell der kører den i **solo-mode** (producerer en regnearks-rapport i stedet for kun JSON til en pipeline).

Kilden til sandhed: `${CLAUDE_SKILL_DIR}/../inb-ads-campaign-build/references/04-structuring.md` (+ dens kontrakter
`structuring-rules.md` og `generelle-negative-eksempel.md` i samme references-mappe).

## Trin 0 — Hent klient-kontekst (AI Context)

> Når inb-ads-campaign-structure kaldes via inb-ads-campaign-build-orchestratoren er AI Context allerede hentet og videregivet — kør kun dette trin når skillet kaldes standalone.

Før al anden handling på en navngiven klient skal du hente klientens AI Context-fil ind i din kontekst. Det er en læsning (aldrig gated), men obligatorisk — sådan arver du alt Inbound ved om klienten (ID'er, kontakter, hårde rammer, navngivningskonvention, budstrategi-norm, KPI'er, pausede-kampagner-intention) i stedet for at starte blindt. Til structuring vejer to ting særligt tungt: klientens **navngivningskonvention** (så ad group- og kampagnenavne matcher kontoens eksisterende mønster) og dens **klient-specifikke negative termer** (de fødes direkte ind i negatives-tieren oven på den delte MCC-liste).

1. **Identificér klienten (kunden).** Tag den klient brugeren nævner (navn, domæne eller konto). Er det uklart, så spørg hvilken klient før du fortsætter.
2. **Åbn master-klientindekset i Drive** via Drive-connectoren: `search_files` efter Google Doc'en med titlen `Inbound CPH — Google Ads klient-index (AI Context)` (aktuelt id `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`, i "A - Kunder"-mappen). Læs den med `read_file_content`. Den mapper hver klient til Google Ads ID, HubSpot ID, ClickUp-mappe, **Stage**, Drive-mappe og **AI Context-fil**.
3. **Find klientens række** (match på navn/domæne/Ads-ID). Notér **Stage** (customer / lead / opportunity / "ikke tagget") — en ikke-`customer`-stage betyder en ikke-lukket konto; vægt anbefalinger derefter og antag aldrig en aktiv retainer. For delte mapper (Lime, Retriever/Infomedia, GSGroup, Nemco, Julemærket, PhoneAlone, DI) vælg rækken for det specifikke marked/konto.
4. **Åbn klientens AI Context-`.md`** via Drive-linket i indeksrækken (`read_file_content`) og tag den ind i din kontekst. Den indeholder driftsbriefen: ID'er, kontakter, hårde rammer (læs før du handler), mål/KPI'er, navngivningskonvention, sådan-kører-vi-den, samt link til changelog/optimeringslog (læs også changelog-doc'et hvis opgaven kræver ændringshistorik — den holdes separat, linket fra AI Context-filen).
5. **Først derefter** starter du skillens egentlige arbejde, med AI Context som ground truth for klient-fakta.

Har klienten ingen række i indekset eller ingen AI Context-fil endnu: sig det, og fortsæt med den kontekst du kan samle (Drive-mappe, Ads MCP) — men flag hullet. Spring aldrig opslaget stille over.

## Trin 1 — Saml input

Som selvstændigt skill arver du ingen Phase-1-output. Saml minimal intake: klientnavn + landingsside-URL +
tema/kampagnetype + geo. Har brugeren allerede et research-grundlag (JSON fra `inb-ads-campaign-research`-skillet), så læs
det fra arbejdsmappen i stedet for at gen-samle. Mangler landingsside-indsigt helt, kør
`01-landing-page`-mønstret inline som referencen beskriver.

## Trin 2 — Kør referencen

Følg `04-structuring.md` præcist — den vinder ved konflikt. Det indebærer: hent den delte negativliste
LIVE fra MCC'en (read-only GAQL), byg ad groups (få, brede), generér keywords med eksplicit Exact/Phrase
(aldrig Broad), og to negative-tiers + monitor-kandidater. Referencen skriver `structuring.json` til
arbejdsmappen.

## Trin 3 — Aflever regnearket (.xlsx)

Pak resultatet i én `.xlsx` (brug `xlsx`-skillet) med faner der spejler structuring-outputtet:
- **Ad groups:** navn | temperatur | #keywords | tema | landingsside (+ struktur-rationalet øverst).
- **Keywords:** ad group | keyword | match type (med volumen-disclaimer øverst — keywords er tema-afledte,
  validér i Keyword Planner).
- **Negatives:** den delte liste som ÉN reference-linje med det LIVE antal (ALDRIG de 277 enumereret) +
  klient-specifikke tilføjelser (term | match type | niveau | hvorfor) + monitor-first-kandidater separat.

At gemme til Drive er en gated write (bekræft før upload). Lokalt er fint.

## Safety

- **Read-only mod Google Ads.** Den live negativliste-pull er et read; ingen API-push, ingen konto-writes.
- **Match-type-låsen:** hver positiv keyword SKAL have Exact eller Phrase — blank/bart ord = Broad ved
  import. Verificér før aflevering.
- **Genudsend ALDRIG de 277 delte negativer** som rækker — de påføres by-reference. Ser du dem enumereret,
  er du drevet væk fra "add to this".
- **Gem til Drive = gated write.** **Logikken bor i referencen, ikke her** — ret `04-structuring.md` hvis
  reglerne ændrer sig.
