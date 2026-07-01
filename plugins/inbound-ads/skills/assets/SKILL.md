---
name: assets
description: Generér Google Ads kampagne-assets (sitelinks, callouts, structured snippets) som selvstændigt trin og aflever dem som regneark (.xlsx), grounded i en klients landingsside + intake. Tynd indgang til assets-referencen i campaign-build, kørt i solo-mode. To hårde firewalls, hvor den første er at opfinde ALDRIG asset-tekst (kun grounded i analyse/intake), og den anden at sitelink-URL'er IKKE er udledelige fra den skrabne side (operator-leveret eller Firecrawl-map). Pusher ALDRIG til kontoen. Brug når brugeren siger "lav assets", "sitelinks + callouts", "extensions til kampagnen", "structured snippets", eller vil have assets som et selvstændigt stykke (ikke en fuld build). Svarer på dansk.
---

# assets

Selvstændig indgang til **Phase 3 — assets** i kampagne-builden. Genererer sitelinks, callouts og
structured snippets og afleverer dem som et **`.xlsx`-regneark** (tabulært per asset-type). Al logikken
bor i campaign-build's reference — dette skill er en tynd shell der kører den i **solo-mode** (producerer
en regnearks-rapport i stedet for kun JSON til en pipeline).

Kilden til sandhed: `${CLAUDE_SKILL_DIR}/../campaign-build/references/06-assets.md` (+ dens kontrakt
`asset-rules.md` i samme references-mappe).

## Trin 0 — Hent klient-kontekst (AI Context) FØRST

Når assets kaldes via campaign-build-orchestratoren er AI Context allerede hentet og videregivet — kør kun dette trin når assets kaldes standalone.

Før al anden handling på en navngiven klient skal du hente klientens AI Context-fil ind i din kontekst. Det er en læsning (aldrig gated), men obligatorisk — sådan arver du alt Inbound ved om klienten (ID'er, kontakter, hårde rammer, navngivningskonvention, budstrategi-norm, KPI'er, pausede-kampagner-intention) i stedet for at starte blindt.

1. **Identificér klienten (kunden).** Tag den klient brugeren nævner (navn, domæne eller konto). Er det uklart, så spørg hvilken klient før du fortsætter.
2. **Åbn master-klientindekset i Drive** via Drive-connectoren: `search_files` efter Google Doc'en med titlen `Inbound CPH — Google Ads klient-index (AI Context)` (aktuelt id `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`, i "A - Kunder"-mappen). Læs den med `read_file_content`. Den mapper hver klient til Google Ads ID, HubSpot ID, ClickUp-mappe, **Stage**, Drive-mappe og **AI Context-fil**.
3. **Find klientens række** (match på navn/domæne/Ads-ID). Notér **Stage** (customer / lead / opportunity / "ikke tagget") — en ikke-`customer`-stage betyder en ikke-lukket konto; vægt anbefalinger derefter og antag aldrig en aktiv retainer. For delte mapper (Lime, Retriever/Infomedia, GSGroup, Nemco, Julemærket, PhoneAlone, DI) vælg rækken for det specifikke marked/konto.
4. **Åbn klientens AI Context-`.md`** via Drive-linket i indeksrækken (`read_file_content`) og tag den ind i din kontekst. Den indeholder driftsbriefen: ID'er, kontakter, hårde rammer (læs før du handler), mål/KPI'er, navngivningskonvention, sådan-kører-vi-den, samt link til changelog/optimeringslog (læs også changelog-doc'et hvis opgaven kræver ændringshistorik — den holdes separat, linket fra AI Context-filen).
5. **Først derefter** starter du skillens egentlige arbejde, med AI Context som ground truth for klient-fakta.

Har klienten ingen række i indekset eller ingen AI Context-fil endnu: sig det, og fortsæt med den kontekst du kan samle (Drive-mappe, Ads MCP) — men flag hullet. Spring aldrig opslaget stille over.

## Trin 1 — Indlæs input

Som selvstændigt skill: saml minimal intake (landingsside-URL + klient) og kør `01-landing-page`-mønstret
for at få analyse-felterne (`product_service`, `usp_candidates`, `trust_signals`, `active_offer`,
`on_page_ctas`, `tone`). Har brugeren allerede en `landing-page-analysis.json` fra `research`-skillet, så
læs den fra arbejdsmappen i stedet. Default attachment level = campaign.

## Trin 2 — Kør referencen

Følg `06-assets.md` præcist — den vinder ved konflikt. De to firewalls er korrekthed, ikke pynt:
1. **Opfind ALDRIG asset-tekst** — hver callout/snippet-værdi grounded i et analyzer-felt (`grounded_in`).
   Ingen grounding → emit ikke.
2. **Sitelink-URL'er er ikke udledelige fra den skrabne side** — operator-leveret (default) eller
   `firecrawl map` hvis CLI'en findes. Kan en URL ikke bekræftes: udelad sitelinket.

Referencen skriver `assets.json` til arbejdsmappen.

## Trin 3 — Aflever regnearket (.xlsx)

Pak resultatet i én `.xlsx` (brug `xlsx`-skillet) med en fane per asset-type:
- **Sitelinks:** tekst | Final URL | url_source (kun bekræftede URL'er).
- **Callouts:** tekst | grounded_in.
- **Structured snippets:** header | værdier | grounded_in.

Bekræft firewall'en i en note ("Alle assets grounded i landingssiden/intake; intet opfundet"), og flag den
UNVERIFIED snippet-header-kolonne. At gemme til Drive er en gated write (bekræft før upload). Lokalt er fint.

## Safety

- **Firewall A (grounding)** er den hyppigste drift — hver asset SKAL have `grounded_in`; tom = drop.
- **Firewall B (sitelink-URL'er)** — gæt aldrig en sti fra én skrabet side. Operator eller firecrawl map.
- **Lead forms er manuelle** — ikke CSV-importerbare; emit ingen række, henvis til Google Ads UI'et.
- **Read-only; gem til Drive = gated write.** **Logikken bor i referencen, ikke her** — ret `06-assets.md`
  hvis reglerne ændrer sig.
