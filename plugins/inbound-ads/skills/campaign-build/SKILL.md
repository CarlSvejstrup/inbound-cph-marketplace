---
name: campaign-build
description: Orkestrer en HEL Google Ads kampagne-build for en ny klient, fra research til en launch-klar review-workbook. Kører de fire faser i rækkefølge — Phase 1 research (landingsside + konkurrenter + strategi), Phase 2 structuring (ad groups + keywords + negatives, med menneske-godkendelse), Phase 3 creative (RSA-tekster + assets), Phase 4 assembler (fletter alt til Ians 10-fane Excel review-workbook). Hver fase køres af en subagent fra en reference; de enkelte faser kan også køres alene via deres egne skills (research/structuring/assets/responsive-search-ads). Pusher ALDRIG til Google Ads API'et — leverancen er review-workbooken. Brug når brugeren siger "byg en ny kampagne til [klient]", "start en campaign-build", "kør hele kampagne-flowet", "fuld kampagne-opsætning fra bunden", eller vil tage en klient hele vejen fra research til launch-klar. Svarer på dansk.
---

# campaign-build

Orkestratoren for den fulde kampagne-build. Tager en ny klient fra research til en launch-klar
**review-workbook** ved at køre fire faser i rækkefølge, hver i sin egen subagent ud fra en reference i
`references/`. Den ejer KUN den brede "byg en hel kampagne"-indgang — de enkelte faser har deres egne
skills (`research`, `structuring`, `assets`, `responsive-search-ads`) til at køre ét trin alene.

**Læs `references/pipeline-flow.md` først** — den er den præcise kontrakt for rækkefølge, parallelisme,
data-flow mellem faser, join-nøgle, subagent-dispatch og den ene menneske-gate. Denne SKILL.md er flowet i
prosa; `pipeline-flow.md` vinder ved konflikt.

## Hvad du bygger (og hvad du IKKE gør)

Leverancen er Ians 10-fane Excel review-workbook + et `Kampagne overblik.md` lead-doc — det
klient-bekræftelses-artefakt kunden godkender. Du pusher **ALDRIG** til Google Ads API'et (beslutning
2026-06-03); Editor-CSV'er genereres SENERE af `editor-csv-export`-skillen fra den bekræftede Excel.
Faserne LÆSER frit fra Google Ads MCP / web / Drive, men SKRIVER intet til kontoen.

## Arbejdsmappe

Vælg én artefakt-mappe for kørslen (fx `.campaign-build/<klient>-<dato>/` i cwd, eller en mappe brugeren
angiver) og giv stien til hver fase. Alle fase-JSON'er skrives dertil; det er lokale arbejdsfiler (ingen
write-gate). Kun den endelige workbook → Drive er en gated ekstern write.

## Trin 0 — Hent klient-kontekst (AI Context) FØRST

Før al anden handling på en navngiven klient skal du hente klientens AI Context-fil ind i din kontekst. Det er en læsning (aldrig gated), men obligatorisk — sådan arver du alt Inbound ved om klienten (ID'er, kontakter, hårde rammer, navngivningskonvention, budstrategi-norm, KPI'er, pausede-kampagner-intention) i stedet for at starte blindt.

**Som orkestrator henter du AI Context ÉN gang her i toppen og giver den VIDERE til hver fase-subagent** (sammen med reference-stien, artefakt-mappen og intake-felterne). Faserne arver dermed klient-konteksten og må IKKE hver især slå klienten op igen — opslaget sker kun her.

1. **Identificér klienten (kunden).** Tag den klient brugeren nævner (navn, domæne eller konto). Er det uklart, så spørg hvilken klient før du fortsætter.
2. **Åbn master-klientindekset i Drive** via Drive-connectoren: `search_files` efter Google Doc'en med titlen `Inbound CPH — Google Ads klient-index (AI Context)` (aktuelt id `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`, i "A - Kunder"-mappen). Læs den med `read_file_content`. Den mapper hver klient til Google Ads ID, HubSpot ID, ClickUp-mappe, **Stage**, Drive-mappe og **AI Context-fil**.
3. **Find klientens række** (match på navn/domæne/Ads-ID). Notér **Stage** (customer / lead / opportunity / "ikke tagget") — en ikke-`customer`-stage betyder en ikke-lukket konto; vægt anbefalinger derefter og antag aldrig en aktiv retainer. For delte mapper (Lime, Retriever/Infomedia, GSGroup, Nemco, Julemærket, PhoneAlone, DI) vælg rækken for det specifikke marked/konto.
4. **Åbn klientens AI Context-`.md`** via Drive-linket i indeksrækken (`read_file_content`) og tag den ind i din kontekst. Den indeholder driftsbriefen: ID'er, kontakter, hårde rammer (læs før du handler), mål/KPI'er, navngivningskonvention, sådan-kører-vi-den, samt link til changelog/optimeringslog (læs også changelog-doc'et hvis opgaven kræver ændringshistorik — den holdes separat, linket fra AI Context-filen).
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

## Trin 2 — Phase 2: structuring (gate)

Dispatch én subagent på `references/04-structuring.md` (forbruger alle tre Phase-1-outputs). Den henter
den delte negativliste live, bygger ad groups + keywords + negatives, og skriver `structuring.json`.

**Dette er den ene menneske-gate.** Præsentér structuring-resultatet for brugeren — ad groups-tabel +
struktur-rationale, keywords per ad group med volumen-disclaimer, negatives (delt liste by-reference med
det LIVE antal + klient-specifikke + monitor-first) — og **bed eksplicit om godkendelse før Phase 3**.
Intet creative kører før mennesket har sagt god.

## Trin 3 — Phase 3: creative (parallelt, efter godkendelse)

Dispatch to subagenter:
- `references/05-rsa-copy.md` → kalder `responsive-search-ads`-skillet per ad group → `rsa-manifest.json`
  (+ per-ad-group `ads-*.json`).
- `references/06-assets.md` → sitelinks/callouts/snippets → `assets.json`.

De er uafhængige.

## Trin 4 — Phase 4: assembler (barriere)

Dispatch én subagent på `references/07-assembler.md`. Den kører `scripts/assemble.py` over de fire shapes,
fletter dem til 10-fane-workbooken, kører de to guards + valideringen, udfylder de semantiske slots i
`Kampagne overblik.md`, og leverer review-artefaktet.

- **Exit 0:** alt validt. **Exit 1:** en guard stoppede (kampagnenavn-mismatch eller blank/Broad keyword)
  — INTET skrevet; ret upstream og kør fasen igen. **Exit 3:** workbook skrevet, men tab 09 har
  over-længde-felter (rød) — ret teksten upstream før konvertering.

## Trin 5 — Gem + rapportér (write — gated)

Workbooken er en ekstern write. Bed om eksplicit bekræftelse én gang før du gemmer/uploader (Drive via
`create_file`, Office-mode `.xlsx`, default klientmappe under `${user_config.inbound_root_folder_id}`).
Rapportér så:
- Sti til workbooken (+ Drive-link hvis uploadet) og lead-doc'et.
- Launch-gate-opsummering fra tab 08 (tracking verificeret, Presence-only geo, Search Partners/Display
  off, delt negativliste tilknyttet by-reference id 6688642473, klient-negatives anvendt).
- Validerings-status fra tab 09 (0 over-længde = grønt; ellers list dem og sig "ret før konvertering").
- Næste skridt (manuelt, human-in-the-loop): workbook → kunde-godkendelse → `editor-csv-export`-
  skillen laver Editor-CSV'erne → mennesket importerer og enabler først når alle Must-pass-gates er
  grønne.

## Safety

- **Ingen API-push, nogensinde.** Hele pipelinen er recommend-/build-only. Read-only MCP-kald er fine.
- **Den endelige workbook → Drive er en gated write** — bekræft før upload (human-in-the-loop: vis
  sti + filnavn, vent på eksplicit `ja`, upload så).
- **Stop ved Phase-2-gaten.** Kør aldrig creative før mennesket har godkendt structuring.
- **Fail loud, ikke stille.** En assembler-guard der stopper (exit 1) betyder ret upstream — overstyr
  aldrig en guard for at tvinge en build igennem.
- **Faserne er kilden til sandhed for deres egen logik** — denne orkestrator dispatcher og syntetiserer,
  men dublerer ikke fase-logik. Ændrer en fases regler sig, rettes referencen (og det matchende
  shell-skill arver det), ikke her.
