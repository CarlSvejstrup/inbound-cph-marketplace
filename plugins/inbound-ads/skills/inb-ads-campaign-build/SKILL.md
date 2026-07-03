---
name: inb-ads-campaign-build
description: Orkestrerer den fulde Google Ads kampagne-build for en ny klient — research, struktur, annoncer, assets — og opretter den som standard direkte i kontoen via ads-writer (HITL-gated, du vælger start på pause eller aktiv), eller leverer et Excel review-ark hvis kunden skal godkende først. Brug når brugeren siger "byg en ny kampagne til [klient]", "opret kampagne", "kør hele kampagne-flowet", eller "fuld kampagne-opsætning fra bunden".
---

# inb-ads-campaign-build

Orkestratoren for den fulde kampagne-build. Tager en ny klient fra research til en **launch-klar
kampagne** ved at køre fire faser i rækkefølge, hver i sin egen subagent ud fra en reference i
`references/`. `inb-ads-rsa-copy` er stadig et selvstændigt skill og kaldes af Phase 3.

**Læs `references/pipeline-flow.md` først** — den er den præcise kontrakt for rækkefølge, parallelisme,
data-flow mellem faser, join-nøgle, subagent-dispatch og de to menneske-gates (structuring + selve
oprettelsen). Denne SKILL.md er flowet i prosa; `pipeline-flow.md` vinder ved konflikt om rækkefølge og
fase-kontrakter — men leverancen/write-retningen nedenfor (2026-07-01) vinder over den gamle
"INGEN API-push"-sektion i pipeline-flow.

**Leverancen (2026-07-01 skift):** som standard **oprettes kampagnen direkte i Google Ads-kontoen** via
`ads-writer`-agenten — hver write HITL-bekræftet, og du vælger om kampagnen starter **på pause** (sikkert)
eller **aktiv**. Hvis kunden skal godkende opsætningen først, kan skillet i stedet levere Ians 10-fane
Excel review-ark (+ `Kampagne overblik.md` lead-doc). Faserne (Phase 1-4) læser frit fra Google Ads MCP /
web / Drive; kun oprettelsen i Trin 5 skriver til kontoen.

## Arbejdsmappe

Vælg én artefakt-mappe for kørslen (fx `.campaign-build/<klient>-<dato>/` i cwd, eller en mappe brugeren
angiver) og giv stien til hver fase. Alle fase-JSON'er skrives dertil; det er lokale arbejdsfiler (ingen
write-gate). De eksterne writes er (a) selve kampagne-oprettelsen i Google Ads (gated per action via
`ads-writer`) og (b) et evt. Excel-ark → Drive (gated før upload).

## Trin 0 — Hent klient-kontekst (AI Context) først

Preload klientens AI Context **før al anden handling** — som orkestrator henter du den én gang her og
giver den videre til hver fase-subagent, så faserne ikke slår klienten op igen. Følg
`../../shared/client-context-intake.md` (identificér klient → master-klientindeks i Drive → klientens
række + Stage → AI Context-fil → derefter arbejde). Delte-mapper og fallback ved manglende
række/fil er også dækket der.

## Trin 0.5 — Intake (resolv én gang, genbrug overalt)

Saml de kampagne-specifikke ting alle faser deler, så ingen subagent gen-spørger:
- **Landingsside-URL** (påkrævet).
- **Konto-match:** kør stille `list_accessible_accounts` → bekræft "Fandt [Kontonavn] (ID: …) — rigtigt?"
- **Kampagnenavn:** resolv ÉN gang i Phase 1c og genbrug verbatim downstream (join-nøgle).
- **Geo + annoncesprog** (default Danmark / dansk).
- **Start-tilstand ved direkte oprettelse:** pause vs. aktiv (afklares i Trin 5, men noter brugerens ønske hvis det nævnes tidligt).

Dansk medmindre brugeren skriver engelsk.

## Trin 1-4 — Kør de fire faser

**Læs `references/pipeline-flow.md` for rækkefølgen, parallelismen og fase-kontrakterne** (fil-navne,
læser/skriver-tabel, join-nøgle, subagent-dispatch). Én sætning per fase:

- **Trin 1 — Phase 1 (research, parallelt):** dispatch tre subagenter (`references/01-landing-page.md`, `02-competitor.md`, `03-campaign-strategy.md`). **Deleger de læse-tunge research-kald til `ads-analyst`-agenten** — den er den genbrugelige read-worker (Google Ads-læsning + `WebSearch`, intet write-scope); giv hver reference-sti, artefakt-mappe, `mode=pipeline`, AI Context og intake-felter. Structuring og creative dispatches IKKE gennem `ads-analyst` (rene build-trin), og leverancen i Trin 5 heller ikke.
- **Trin 2 — Phase 2 (structuring, gate):** dispatch én subagent på `references/04-structuring.md`. **Dette er den ene menneske-gate:** præsentér ad groups-tabel + rationale, keywords per ad group med volumen-disclaimer, og negatives (delt liste by-reference med LIVE antal + klient-specifikke + monitor-first), og **bed eksplicit om godkendelse før Phase 3**. Intet creative kører før mennesket har sagt god.
- **Trin 3 — Phase 3 (creative, parallelt, efter godkendelse):** dispatch to subagenter (`references/05-rsa-copy.md` → kalder `inb-ads-rsa-copy` per ad group; `references/06-assets.md`).
- **Trin 4 — Phase 4 (assembler, barriere):** dispatch én subagent på `references/07-assembler.md` (kører `scripts/assemble.py`, fletter de fire shapes til 10-fane-workbooken, kører guards + validering, udfylder `Kampagne overblik.md`). Læs `references/07-assembler.md` for exit-koderne (0/1/3) og guard-adfærd — kort: en fejlende guard (exit 1) skriver INTET, så overstyr aldrig en guard for at tvinge en build igennem; ret upstream og kør fasen igen.

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

Direkte Google Ads writes er tilladt (skift 2026-07-01) men KUN gennem `ads-writer`-agenten og KUN
per-action HITL-bekræftet — se repoets `CLAUDE.md` for de fulde write-guardrails. Skill-specifikt: Vej A
opretter kampagnen direkte via `ads-writer` (starter **på pause** som default med mindre brugeren vælger
aktiv), budget-writes er ekstra gated bag `INBOUND_ADS_BUDGET_GUARDRAIL` og kræver et separat eksplicit ja,
og fordi skillet skriver til klientkonti kræver ændringer Ians review før merge (CODEOWNERS). Read-only
MCP-kald i Phase 1-4 er frie. Faserne er kilden til sandhed for deres egen logik: ændrer en fases regler
sig, rettes referencen, ikke her.
