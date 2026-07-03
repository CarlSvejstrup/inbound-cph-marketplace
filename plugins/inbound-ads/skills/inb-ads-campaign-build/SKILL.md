---
name: inb-ads-campaign-build
description: Orkestrerer den fulde Google Ads kampagne-build for en ny klient — research, struktur, annoncer, assets — og opretter den som standard direkte i kontoen via ads-writer (HITL-gated, du vælger start på pause eller aktiv), eller leverer et Excel review-ark hvis kunden skal godkende først. Brug når brugeren siger "byg en ny kampagne til [klient]", "opret kampagne", "kør hele kampagne-flowet", eller "fuld kampagne-opsætning fra bunden".
---

# inb-ads-campaign-build

Orkestratoren for den fulde kampagne-build. Tager en ny klient fra research til en **launch-klar
kampagne** ved at køre fire faser i rækkefølge, hver i sin egen subagent ud fra en reference i
`references/`. Én indgang: den fulde build. (De fire faser har ikke længere separate skills — al
fase-logik bor her i `references/`. `inb-ads-rsa-copy` er stadig et selvstændigt skill og bruges af
Phase 3.)

**Læs `references/pipeline-flow.md` først** — den er den præcise kontrakt for rækkefølge, parallelisme,
data-flow mellem faser, join-nøgle, subagent-dispatch og de to menneske-gates (structuring + selve
oprettelsen). Denne SKILL.md er flowet i prosa; `pipeline-flow.md` vinder ved konflikt.

**Leverancen (2026-07-01 skift):** som standard **oprettes kampagnen direkte i Google Ads-kontoen** via
`ads-writer`-agenten — hver write HITL-bekræftet, og du vælger om kampagnen starter **på pause** (sikkert)
eller **aktiv**. Hvis kunden skal godkende opsætningen først, kan skillet i stedet levere Ians 10-fane
Excel review-ark (+ `Kampagne overblik.md` lead-doc) som før. Dette **erstatter** den gamle "pusher aldrig
til API'et"-beslutning (2026-06-03): direkte writes er nu tilladt, men KUN gennem `ads-writer` og KUN
per-action-bekræftet. Faserne (Phase 1-4) læser frit fra Google Ads MCP / web / Drive; kun oprettelsen i
Trin 5 skriver til kontoen.

## Arbejdsmappe

Vælg én artefakt-mappe for kørslen (fx `.campaign-build/<klient>-<dato>/` i cwd, eller en mappe brugeren
angiver) og giv stien til hver fase. Alle fase-JSON'er skrives dertil; det er lokale arbejdsfiler (ingen
write-gate). De eksterne writes er (a) selve kampagne-oprettelsen i Google Ads (gated per action via
`ads-writer`) og (b) et evt. Excel-ark → Drive (gated før upload).

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
ræsonnerer og returnerer fase-JSON'en. Structuring (Phase 2) og creative (Phase 3) er rene build-trin og
dispatches ikke gennem `ads-analyst`. Selve leverancen i Trin 5 (direkte oprettelse via `ads-writer`,
eller Excel-assembler hvis kunden skal godkende) er ikke et `ads-analyst`-trin.

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

## Trin 5 — Aflever (spørg brugeren: konto eller ark)

Den byggede kampagne findes nu som de fire shapes i arbejdsmappen. **Spørg brugeren hvordan den skal
leveres** (ét spørgsmål, to valg):

> "Skal jeg **oprette kampagnen direkte i Google Ads-kontoen**, eller lave et **Excel review-ark** kunden
> kan godkende først?"

### Vej A — Opret direkte i kontoen (standard)

Al skrivning går gennem `ads-writer`-agenten — aldrig et Google Ads write-værktøj direkte. `ads-writer`
er den eneste konto-write-vej, og write-guardrail-hooken er backstoppet under den.

1. **Spørg om start-tilstand først:** "Skal kampagnen starte **på pause** (sikkert — den bruger intet før
   du selv aktiverer) eller **aktiv** med det samme?" **Anbefal pause** — så kan alt verificeres i UI'et
   før en krone bruges.
2. **Præsentér hele oprettelses-planen** før den første write: kampagne (navn, type, geo, netværk,
   budstrategi, **dagsbudget**, start-tilstand), ad groups, keywords (med match types), RSA'er, assets,
   klient-negatives. Dette er hele det menneske ser før noget rører kontoen.
3. **Route de bekræftede writes gennem `ads-writer`** i rækkefølge (kampagne → budget → ad groups →
   keywords → RSA'er → assets → negatives). Hver write er per-action HITL-bekræftet — `ads-writer`
   foreslår, mennesket siger ja, så skrives den.
4. **Budget er højrisiko — vær eksplicit i bekræftelsen.** En ny kampagne kræver et budget. Vis det
   præcist: "Nyt dagsbudget: **X kr/dag** på kampagne **[navn]** (ny kampagne, oprettes
   [pause/aktiv])" og få et separat, utvetydigt ja på netop budgettet. Write-guardrail-hooken gælder
   uændret: budget-writes er gated bag `INBOUND_ADS_BUDGET_GUARDRAIL` — er guardrailen ikke slået til på
   sædet, så oprettes kampagnen uden budget-writen (eller den standses), og du siger det ærligt frem for
   at tvinge den igennem. Sæt aldrig budget autonomt.
5. **Den delte MCC-negativliste** tilknyttes by-reference (id 6688642473) — genopret aldrig dens ~277
   medlemmer som rækker.
6. **Rapportér:** hvad blev oprettet (kampagne-id, ad groups, antal keywords/RSA'er/assets), start-tilstand,
   launch-gate-status (tracking, Presence-only geo, Search Partners/Display off, negativliste tilknyttet),
   og — hvis noget blev holdt tilbage (fx budget-writen) — præcis hvad der mangler og hvordan mennesket
   færdiggør det.

### Vej B — Excel review-ark (når kunden skal godkende)

Kør Phase 4 assembler (`references/07-assembler.md` → `scripts/assemble.py`) → Ians 10-fane workbook +
`Kampagne overblik.md`. Arket → Drive er en gated write: vis sti + filnavn, vent på eksplicit "ja", upload
via Drive `create_file` (Office-mode `.xlsx`, default klientmappe under
`${user_config.inbound_root_folder_id}`). Rapportér sti/Drive-link, launch-gate-opsummering (tab 08) og
valideringsstatus (tab 09). Næste skridt derfra: kunde-godkendelse → mennesket importerer workbooken
manuelt i Google Ads Editor, ELLER kør Vej A på den godkendte opsætning for at oprette direkte.

## Safety

**Direkte Google Ads writes er tilladt (skift 2026-07-01) — men KUN gennem `ads-writer`-agenten og KUN
per-action HITL-bekræftet.** Dette erstatter den gamle "pusher aldrig til API'et"-beslutning (2026-06-03).
Intet skill kalder et Google Ads write-værktøj direkte; ingen write sker autonomt. Budget-writes er ekstra
gated (write-guardrail-hooken + `INBOUND_ADS_BUDGET_GUARDRAIL`) og kræver et separat, eksplicit ja på selve
budgettet. Read-only MCP-kald i Phase 1-4 er frie. **Fordi dette skill nu skriver til klientkonti, kræver
ændringer Ians review før merge (CODEOWNERS).** Faserne er kilden til sandhed for deres egen logik: denne
orkestrator dispatcher og syntetiserer, men dublerer ikke fase-logik — ændrer en fases regler sig, rettes
referencen, ikke her.
