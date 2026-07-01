---
name: inb-ads-campaign-build
description: Orkestrerer den fulde Google Ads kampagne-build for en ny klient fra research over struktur og assets til Ians 10-fane Excel review-workbook, ved at køre fire faser i rækkefølge som subagenter med ét menneske-godkendelsespunkt undervejs, og pusher aldrig direkte til Google Ads API'et.
---

# inb-ads-campaign-build

Orkestratoren for den fulde kampagne-build. Tager en ny klient fra research til en launch-klar
**review-workbook** ved at køre fire faser i rækkefølge, hver i sin egen subagent ud fra en reference i
`references/`. Den ejer kun den brede "byg en hel kampagne"-indgang — de enkelte faser har deres egne
skills (`inb-ads-campaign-research`, `inb-ads-campaign-structure`, `inb-ads-campaign-assets`, `inb-ads-rsa-copy`) til at køre ét trin alene.

**Læs `references/pipeline-flow.md` først** — den er den præcise kontrakt for rækkefølge, parallelisme,
data-flow mellem faser, join-nøgle, subagent-dispatch og den ene menneske-gate. Denne SKILL.md er flowet i
prosa; `pipeline-flow.md` vinder ved konflikt.

Leverancen er Ians 10-fane Excel review-workbook + et `Kampagne overblik.md` lead-doc — det
klient-bekræftelses-artefakt kunden godkender. Pusher aldrig til Google Ads API'et (beslutning
2026-06-03); Editor-CSV'er genereres senere af `inb-ads-editor-csv-export` fra den bekræftede Excel.
Faserne læser frit fra Google Ads MCP / web / Drive, men skriver intet til kontoen.

## Arbejdsmappe

Vælg én artefakt-mappe for kørslen (fx `.campaign-build/<klient>-<dato>/` i cwd, eller en mappe brugeren
angiver) og giv stien til hver fase. Alle fase-JSON'er skrives dertil; det er lokale arbejdsfiler (ingen
write-gate). Kun den endelige workbook → Drive er en gated ekstern write.

## Trin 0 — Hent klient-kontekst (AI Context) først

Før al anden handling på en navngiven klient, hent klientens AI Context-fil ind i din kontekst. Det er
en læsning (aldrig gated), men obligatorisk — sådan arver du alt Inbound ved om klienten (ID'er,
kontakter, hårde rammer, navngivningskonvention, budstrategi-norm, KPI'er, pausede-kampagner-intention)
i stedet for at starte blindt. Som orkestrator henter du AI Context én gang her i toppen og giver den
videre til hver fase-subagent (sammen med reference-stien, artefakt-mappen og intake-felterne) —
faserne slår ikke selv klienten op igen.

1. **Identificér klienten.** Tag den klient brugeren nævner (navn, domæne eller konto). Er det uklart, spørg hvilken klient før du fortsætter.
2. **Åbn master-klientindekset i Drive** via Drive-connectoren: `search_files` efter Google Doc'en med titlen `Inbound CPH — Google Ads klient-index (AI Context)` (id `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`, i "A - Kunder"-mappen). Læs den med `read_file_content`. Den mapper hver klient til Google Ads ID, HubSpot ID, ClickUp-mappe, **Stage**, Drive-mappe og **AI Context-fil**.
3. **Find klientens række** (match på navn/domæne/Ads-ID). Notér **Stage** (customer / lead / opportunity / "ikke tagget") — en ikke-`customer`-stage betyder en ikke-lukket konto; vægt anbefalinger derefter og antag aldrig en aktiv retainer. For delte mapper (Lime, Retriever/Infomedia, GSGroup, Nemco, Julemærket, PhoneAlone, DI) vælg rækken for det specifikke marked/konto.
4. **Åbn klientens AI Context-`.md`** via Drive-linket i indeksrækken (`read_file_content`). Den indeholder driftsbriefen: ID'er, kontakter, hårde rammer (læs før du handler), mål/KPI'er, navngivningskonvention, sådan-kører-vi-den, samt link til changelog/optimeringslog (læs også changelog-doc'et hvis opgaven kræver ændringshistorik).
5. **Først derefter** går du videre til intake (Trin 0.5) og faserne, med AI Context som ground truth for klient-fakta — og send den med til hver subagent.

Har klienten ingen række i indekset eller ingen AI Context-fil endnu: sig det, og fortsæt med den kontekst du kan samle (Drive-mappe, Ads MCP) — men flag hullet. Spring aldrig opslaget stille over.

## Trin 0.5 — Intake (resolv én gang, genbrug overalt)

Saml de få ting alle faser deler, så ingen subagent gen-spørger:
- **Klient + landingsside-URL** (påkrævet).
- **Konto-match:** kør stille `list_accessible_accounts` → bekræft "Fandt [Kontonavn] (ID: …) — rigtigt?"
- **Kampagnenavn:** resolv det ÉN gang i Phase 1c og genbrug verbatim downstream (join-nøgle).
- **Geo + annoncesprog** (default Danmark / dansk).

Dansk medmindre brugeren skriver engelsk.

## Trin 1 — Phase 1: research (parallelt)

Dispatch tre subagenter (se subagent-kontrakten i `pipeline-flow.md` — giv hver reference-stien,
artefakt-mappen, `mode=pipeline` og de kendte intake-felter):
- `references/01-landing-page.md` → `landing-page-analysis.json`
- `references/02-competitor.md` → `competitor-research.json`
- `references/03-campaign-strategy.md` → `campaign-strategy.json`

Kør `01` først (eller giv `02` klientens analyse når den er klar) — `02` læser gerne klientens egen
positionering. De er ellers uafhængige. Saml de tre opsummeringer.

**Deleger de læse-tunge research-fasers konto- og web-læsninger til `ads-analyst`-agenten.** Phase 1
(landingsside-analyse, konkurrent-research, strategi) er ren læsning — konto-signaler via Google Ads
MCP + web-kontekst — og `ads-analyst` er den genbrugelige read-worker med Google Ads-læsning +
`WebSearch` og intet write-scope. Dispatch de tre research-subagenter via `ads-analyst` (giv hver
reference-stien, artefakt-mappen, `mode=pipeline`, AI Context og intake-felterne); den henter dataen,
ræsonnerer og returnerer fase-JSON'en. Structuring (Phase 2) og assembler/Excel-faserne (Phase 3-4) er
rene build-trin og forbliver som de er — de dispatches ikke gennem `ads-analyst`.

## Trin 2 — Phase 2: structuring (gate)

Dispatch én subagent på `references/04-structuring.md` (forbruger alle tre Phase-1-outputs). Den henter
den delte negativliste live, bygger ad groups + keywords + negatives, og skriver `structuring.json`.

**Dette er den ene menneske-gate.** Præsentér structuring-resultatet for brugeren — ad groups-tabel +
struktur-rationale, keywords per ad group med volumen-disclaimer, negatives (delt liste by-reference med
det LIVE antal + klient-specifikke + monitor-first) — og **bed eksplicit om godkendelse før Phase 3**.
Intet creative kører før mennesket har sagt god.

## Trin 3 — Phase 3: creative (parallelt, efter godkendelse)

Dispatch to subagenter:
- `references/05-rsa-copy.md` → kalder `inb-ads-rsa-copy`-skillet per ad group → `rsa-manifest.json`
  (+ per-ad-group `ads-*.json`).
- `references/06-assets.md` → sitelinks/callouts/snippets → `assets.json`.

De er uafhængige.

## Trin 4 — Phase 4: assembler (barriere)

Dispatch én subagent på `references/07-assembler.md`. Den kører `scripts/assemble.py` over de fire shapes,
fletter dem til 10-fane-workbooken, kører de to guards + valideringen, udfylder de semantiske slots i
`Kampagne overblik.md`, og leverer review-artefaktet.

- **Exit 0:** alt validt. **Exit 1:** en guard stoppede (kampagnenavn-mismatch eller blank/Broad keyword)
  — intet skrevet; ret upstream og kør fasen igen, overstyr aldrig en guard for at tvinge en build
  igennem. **Exit 3:** workbook skrevet, men tab 09 har over-længde-felter (rød) — ret teksten upstream
  før konvertering.

## Trin 5 — Gem + rapportér (write — gated)

Workbooken er en ekstern write. Bed om eksplicit bekræftelse én gang før du gemmer/uploader (vis sti +
filnavn, vent på eksplicit "ja", upload så via Drive `create_file`, Office-mode `.xlsx`, default
klientmappe under `${user_config.inbound_root_folder_id}`). Rapportér så:
- Sti til workbooken (+ Drive-link hvis uploadet) og lead-doc'et.
- Launch-gate-opsummering fra tab 08 (tracking verificeret, Presence-only geo, Search Partners/Display
  off, delt negativliste tilknyttet by-reference id 6688642473, klient-negatives anvendt).
- Validerings-status fra tab 09 (0 over-længde = grønt; ellers list dem og sig "ret før konvertering").
- Næste skridt (manuelt, human-in-the-loop): workbook → kunde-godkendelse → `inb-ads-editor-csv-export`-
  skillen laver Editor-CSV'erne → mennesket importerer og enabler først når alle Must-pass-gates er
  grønne.

## Safety

Ingen API-push, nogensinde — hele pipelinen er recommend-/build-only, read-only MCP-kald er fine. (Hvis
den parkerede beslutning om at pushe campaign-build direkte til Google Ads nogensinde omgøres, ville den
write skulle routes gennem `ads-writer`-agenten — men det er ikke nuværende adfærd.) Faserne er kilden
til sandhed for deres egen logik: denne orkestrator dispatcher og syntetiserer, men dublerer ikke
fase-logik — ændrer en fases regler sig, rettes referencen (og det matchende shell-skill arver det),
ikke her.
