---
name: inb-ads-context-update
description: >
  Opdatér én klients AI-kontekst on-demand, og giv samtidig et projektleder-overblik
  over klienten. To fluer, ét smæk. Alt lever på Google Drive: skillet starter ALTID i
  master-klientindekset (Google Doc), finder klientens række, navigerer til klientens
  Drive-mappe og åbner klientens AI-Context-fil (den .md i klientens "AI Context"-mappe
  der ER konteksten). Det finder så ALT nyt siden AI-Context-filens "Sidst opdateret"-dato,
  fra tre kilder: klientens Drive-mappe (nye/ændrede dokumenter), HubSpot (nye mails,
  noter, aktivitet via MCP'en) og rapporter til kunden (statusmøde-præsentationer, Google
  Slides, ligger ofte i HOVEDmappen i en undermappe som "Præsentation" eller "statusmøder",
  ikke i Paid Search; vi læser den nyeste). Det synteserer et kort situations-brief i chatten
  FØRST, og foreslår så ændringer til AI-Context-filens Klientoverblik klassificeret som
  TILFØJ / ERSTAT / FJERN: tilføjelser vises og bekræftes let, mens erstatninger og
  sletninger kræver eksplicit menneske-godkendelse per punkt før filen skrives. Respekterer
  tidsløs-reglen (aldrig live-tal i Klientoverblik). Skriver kun til Drive-filen efter
  godkendelse. Read-only mod Google Ads og HubSpot. Human-in-the-loop på enhver skrivning. Dansk.
  Brug når brugeren siger "opdatér kontekst på [kunde]", "kontekst-opdater",
  "hvad er nyt på [kunde]", "saml mig op på [kunde]", "opdatér AI-konteksten",
  "projektleder-overblik på [kunde]", eller "hvad er sket siden sidst på [kunde]".
---

# inb-ads-context-update

Opdatér én klients AI-kontekst on-demand, OG lever et projektleder-overblik over klienten i samme kørsel. To outputs, ét smæk:

1. **Projektleder-overblik** (chat): hvem klienten er, hvad der for nyligt er lavet/aftalt, aktuel status, åbne tråde. Som en projektleder der lige er kommet op i fart.
2. **Opdateret AI-kontekst** (klientens AI-Context-fil på Drive): træk alt nyt siden sidste opdatering og flet det ind, kritisk om hvad der skal **fjernes/erstattes** (ikke kun tilføjes).

Det er makker til `inb-ads-context-publish` (som første gang publicerer en klients AI-Context-fil til Drive). Dette skill VEDLIGEHOLDER den fil bagefter. Læs `references/` for de dybe kontrakter; denne fil er den kørbare overflade.

## Kontekst (læs før noget andet)

**Alt lever på Google Drive. Der er ingen lokal vault, ingen lokale noter.** De relevante flader:
- **Master-klientindekset** (Google Doc, id `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`, titel `Inbound CPH — Google Ads klient-index (AI Context)`) — INDGANGEN. Én række pr. klient med: Klient, Google Ads ID, HubSpot ID, ClickUp folder, Stage, Drive-mappe (link), AI Context-fil (link), Noter.
- **Klientens AI-Context-fil** (en `.md` i en "AI Context"-undermappe i klientens Drive-mappe, fx `Dantaxi - 7438308806.md`) — **denne fil ER konteksten** og er kilden til sandhed. Den starter med en `Sidst opdateret: YYYY-MM-DD`-linje og indeholder ID-blokken, durable sektioner og den 5-delte `## Klientoverblik`.
- **Klientens Drive-mappe** — hvor nye dokumenter og rapporter (statusdecks) ligger.

**To Google-MCP'er, forskellige evner OG forskellig auth (afgør hele leveringsformen):**
- **Drive-connectoren** (`mcp__10f9f31f-…`) — HAR adgang til klientmapperne, men er **create-only** (`create_file`, `copy_file`; intet append/update/delete). **Dette er den ENESTE læse-vej til Drive** i dette skill.
- **Workspace-MCP'en** (`mcp__acc7a973-…`, "gws") — KAN opdatere en Drive-fil på stedet (`updateTextFile`, `updateDocFromMarkdown`, `findAndReplaceInDoc`). Brug den **kun** til den faktiske skrivning til AI-Context-filen (Trin 6), altid gated og altid med ren fallback (den kan være i `needs_reauth` eller mangle adgang).

**Skrivegrænser (hårde):**
- AI-Context-filen skrives **kun efter diff-godkendelse** (Trin 5/6). ERSTAT/FJERN kræver eksplicit per-punkt-`ja`; TILFØJ kan batches efter ét `ja`. Skriv aldrig en linje der ikke er vist.
- **Read-only** mod Google Ads og HubSpot. Anbefal/registrér; skriv aldrig til en konto eller et CRM-objekt.
- Opret aldrig en dublet AI-Context-fil via Drive-connectoren for at "rette" en fejlet gws-skrivning (en dublet kan ikke fjernes programmatisk).

**Sprog:** alt på dansk medmindre brugeren skriver engelsk. Real Æ Ø Å, aldrig ASCII (aa/oe/ae); `grep`/tjek indholdet før enhver skrivning.

## Watermarks (to stykker, begge i AI-Context-filen)

Ingen separat tidsstempel-kolonne, intet lokalt felt. To linjer i selve AI-Context-filen er watermarks:

1. **`Sidst opdateret: YYYY-MM-DD`** — hoved-watermark'et for Drive-dokumenter + HubSpot + Ads. Skillet:
   - **Læser** den for at beregne siden-vinduet ("nyt siden <dato>").
   - **Skriver** den til i dag når en kørsel var ren (alle tre kilder hentet uden fejl) og brugeren godkendte ændringer.
   - **Partial-success:** fejlede en kilde (HubSpot 403, Drive socket-drop), så ryk IKKE "Sidst opdateret" til i dag, og notér per-kilde as-of i Klientoverblik-introlinjen, så næste kørsel henter hullet.
   - Mangler linjen (ældre format): behandl hele filen som siden-gulv, sig antagelsen højt, tilføj linjen ved skrivning.
2. **`Seneste rapport læst: <titel> [id: <fil-id>]`** — separat watermark for rapport-ingestion (rapporter kommer månedligt, ikke løbende, så de har deres eget spor). Skillet sammenligner den mod nyeste deck i rapport-mappen; matcher de → rapporten er allerede indlæst, spring den dyre konvertering over (se Trin 2 C + `references/report-ingestion.md`). Mangler linjen → ingen rapport indlæst endnu, nyeste er altid ny. Opdateres i samme gated skrivning som Klientoverblik (Trin 6).

## Trin 0.5 — Start i indekset (obligatorisk indgang)

Via Drive-connectoren:
1. **Identificér klienten** (navn/domæne/konto). Uklart → spørg før du fortsætter.
2. **Åbn master-indekset:** `read_file_content` på id `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`.
3. **Find klientens række** og læs: Google Ads ID, HubSpot ID, **Stage** (customer/lead/opportunity/"ikke tagget" — antag aldrig aktiv retainer på en ikke-customer), **Drive-mappe-linket**, **AI-Context-fil-linket**, og Noter (delt-mappe-caveats står her). For delte mapper (Lime/Retriever/GSGroup/Nemco/Julemærket/PhoneAlone/DI/EDC) vælg det specifikke markeds række.
4. **Åbn klientens AI-Context-fil** (`read_file_content` via fil-linket) — det er konteksten + skrivemålet. Læs `Sidst opdateret`-linjen (watermark) + den nuværende `## Klientoverblik`.
5. **Først derefter** videre. Ingen index-række eller ingen AI-Context-fil endnu: sig det, foreslå at køre `inb-ads-context-publish` først (den opretter filen), og stop — dette skill vedligeholder en eksisterende fil, det opretter den ikke.

## Trin 1 — Resolve + læs watermark

- **Siden-gulv** = AI-Context-filens `Sidst opdateret`-dato. Mangler den → behandl hele filen som gulv (bootstrap), sig antagelsen.
- Saml de ID'er du skal bruge fra **indeksrækken + AI-Context-filens ID-blok**: `Google Ads ID`, `HubSpot ID`, Drive-mappe-ID (træk ud af mappe-linket), og en evt. allerede-noteret rapport-mappe i filen (se Trin 2 C). **Index/fil-ID'er er autoritative over enhver MCP-payload** (Ads-MCP'en fejlrouter).
- Beregn + vis siden-vinduet overalt (fx "siden 2026-06-17").

## Trin 2 — Fan-out: én ekspert-subagent per kilde, parallelt

**Uddeleger kilde-fan-out'en til `drive-knowledge`-agenten (read-across-sources worker) via Task-værktøjet;** den læser Drive/HubSpot/Ads-historik siden watermark og returnerer en konsolideret, kilde-attribueret opsummering. Skillet laver TILFØJ/ERSTAT/FJERN-diffen (Trin 4) og den gated skrivning (Trin 6). Giv `drive-knowledge` de resolvede ID'er (`Google Ads ID`, `HubSpot ID`, Drive-mappe-ID), siden-datoen (watermark), en evt. allerede-noteret rapport-mappe + `Seneste rapport læst`-watermark, og struktureret-output-kontrakten (se `references/source-contracts.md`). `drive-knowledge` er read-only mod alle kilder og honorerer tidsløs-reglen; den fan-er de tre ekspert-læsninger nedenfor ud internt og returnerer **kun fund** (rå læsninger bliver i dens kontekst, ikke hovedkonteksten). Kan `drive-knowledge` ikke dispatches, så kør de tre ekspert-subagenter inline som beskrevet nedenfor.

De tre kilde-læsninger `drive-knowledge` udfører (og som ellers køres inline) — dispatch samtidigt (ét message, flere tool-kald), hver med de resolvede ID'er + siden-datoen + struktureret-output-kontrakten. Hver returnerer **kun fund**.

- **Drive-ekspert** (kun Drive-connectoren):
  - **(A) Nye/ændrede dokumenter:** `search_files parentId='<Drive-mappe-ID>'` + `get_file_metadata`, filtrér `modifiedTime > siden` (RFC-3339 UTC), rekursér undermapper, mærk per marked for delte mapper, `read_file_content` på dokumenter i vinduet.
  - **(C) Rapporter (høj prioritet, statusmøde-decks):** mappen er ankeret, ikke filtypen — det er klientmappens undermappe `#1 - Præsentationer og statusmøder` (varianter set i praksis: `... Statusmøder og -rapporter`, `... Præsentationer & statusmøder`, `#1 - Statusmøder`, `#1 - Møder`, en-dash `#1 – Præsentationer`; mønster = `#1`-præfiks + "sentation"/"statusm"/"Møder"). Nogle klienter har ingen `#1`-mappe men år-baserede `<Klient> møder 20XX`-mapper → fald tilbage til nyeste år. Nogle har slet ingen rapport-mappe → accepter "ingen" pænt, opfind ikke. **To trin:** (1) **find nyeste deck** — står rapport-mappen allerede i AI-Context-filen, gå direkte dertil (`search '<mappe-id>' in parents and trashed=false`), ellers find mappen på navn (`title contains 'sentation' or title contains 'statusm' or title contains 'Møder'`; ignorér `OLD - ...`) og returnér den til hovedskillet så den kan gemmes (Trin 5/6). Vælg nyeste deck efter `YYYY-MM` i titlen (ikke `modifiedTime`; en måned findes ofte som både PDF og PPTX). (2) **er nyeste deck NYERE end `Seneste rapport læst` i AI-Context-filen → kald `references/report-ingestion.md`** for at konvertere + udtrække et rapport-resumé (konvertering er dyr, så KUN når ny). Allerede indlæst → spring over. Ulæselig deck → vis linket, opfind ikke. Degradér på socket-drop, ingen blind-retry; rapportér partial. **Rapport-indholdet går i sin EGEN `## Rapport`-sektion (skrives i Trin 6), IKKE ind i Klientoverblik-diff'en (Trin 4)** — rapport og Klientoverblik holdes adskilt: rapport-resuméet er sporbart og let at finde, Klientoverblik forbliver ren durable kontekst.
- **HubSpot-ekspert** (HubSpot MCP): firma via indeksrækkens `HubSpot ID`. **Aldrig** `engagement_details_*` (403). Brug `notes_search`/`emails_search`/`calls_search`/`meetings_search`/`tasks_search` med `associations.company` EQ `<HubSpot ID>` + recency på `hs_lastmodifieddate`/`createdAt`/`updatedAt` `> siden`. Afkod lifecycle/deal-stage-ID'er til labels. Kollaps til menneskelæsbar aktivitet. Fejl → markér HubSpot partial.
- **Ads-ekspert** (Google Ads MCP, let): kun durable fakta til overblikkets "hvad ændrede sig på kontoen"-linje. `get_change_summary(customer_id=<Google Ads ID>, lookback_days=29)` / `get_change_history` (≤29; 30 hard-fejler `START_DATE_TOO_OLD`). Bulk-kollaps på (timestamp, ressourcetype). **Fejlroute-vagt:** sanity-check identitet mod `Google Ads ID`; kassér mismatch.

Hver subagents partial/ren-status fødes ind i watermark-reglen (Trin 6). Alt read-only.

## Trin 3 — Projektleder-overblik (OUTPUT #1, kun chat, FØR diff'en)

Syntetisér de tre subagenters fund. Sektioner, dansk:
- **Hvem de er.** 2-3 linjer fra AI-Context-filens Klientoverblik > Overblik (klient, marked, specialist, tier, budget, kontakt).
- **Hvor vi står.** Vigtigste hårde rammer + mål + åbne håndtag fra den NUVÆRENDE Klientoverblik.
- **Hvad er nyt siden `<Sidst opdateret>`.** Per kilde: Drive (N dok.), HubSpot (N mails/noter), Rapporter (nyeste deck + kernebudskab, eller "ingen nyere rapport fundet").
- **Åbne tråde & håndtag lige nu.** Hvad en projektleder skal handle på: ubesvarede mails, ventende aftaler, håndtag fra rapporten, deadlines.
- **Datagrundlag & huller.** Hvilke kilder blev læst/fejlede + tidsvinduet.

Syntese, ikke et dump. Sig derefter: "Herunder er mine forslag til at opdatere selve AI-konteksten" → diff'en.

## Trin 4 — Diff: TILFØJ / ERSTAT / FJERN

Sammenlign nyt materiale **fra Drive-dokumenter + HubSpot + Ads** mod den nuværende `## Klientoverblik` i AI-Context-filen. **Rapport-indhold indgår IKKE her** — det får sin egen `## Rapport`-sektion (Trin 6) og røres ikke af diff'en. Én dansk review-tabel: `# | Type | Sektion | Nuværende | Foreslået | Kilde`. Regler:
- Kør hver **TILFØJ** gennem tidsløs-vagten: afvis live-tal/domme; genformulér nyttige-men-forældede domme som **håndtag** ("hæv budget hvor markeder er capped — verificér først"). Se `references/diff-classification.md`.
- Argumentér hver **ERSTAT/FJERN** med dens kilde (fx rapport markerer et håndtag afsluttet → FJERN). Vær kritisk, ikke destruktiv — foreslå, lad mennesket bestemme.
- Intet skrives endnu.

## Trin 5 — Human-in-the-loop-gate (godkend ændringerne)

- **TILFØJ:** ét batchet bekræft ("tilføj 1,4,5? ja/vælg/nej").
- **ERSTAT/FJERN:** eksplicit per-punkt (eller udtrykkeligt-listet sæt), vis den præcise tekst der fjernes.
- **Rapport-mappe:** blev en kandidat fundet i Trin 2 og er den ikke allerede noteret i filen, så foreslå at tilføje en `Rapporter:`-linje i ID-blokken med mappe-linket; bekræft.
- **Ny rapport:** blev en NY rapport indlæst (Trin 2 C via `report-ingestion.md`), så (a) den nye/erstattede `## Rapport`-sektion (rapport-resuméet) og (b) den opdaterede `Seneste rapport læst:`-linje (titel + fil-id) indgår i skrivningen. `## Rapport` **erstattes** med nyeste rapport (ikke append), og er en selvstændig sektion — den flettes ikke ind i Klientoverblik. Blev ingen ny rapport indlæst → rør ikke `## Rapport`.
- Saml de godkendte ændringer (Klientoverblik-diff: TILFØJ + godkendte ERSTAT/FJERN; + evt. `Rapporter:`-linje; + evt. ny `## Rapport`-sektion + `Seneste rapport læst:`-linje) til den samlede skrivning. Opdatér `Sidst opdateret`-linjen til i dag **kun hvis alle 3 kilder var rene** (ellers lad stå + notér per-kilde as-of i Klientoverblik-introlinjen). Intet er skrevet endnu — det sker i Trin 6.

## Trin 6 — Skriv den opdaterede AI-Context-fil (gated, gws-eller-fallback)

Den eneste skrivning. Probe gws (`authGetStatus` på `mcp__acc7a973-…`):
- **Authed + filen skrivbar:** gated skrivning til AI-Context-filen. Foretræk surgiske `findAndReplaceInDoc`/`updateTextFile`-operationer der erstatter (a) den gamle `## Klientoverblik`-blok, (b) den gamle `## Rapport`-sektion hvis en ny rapport blev indlæst, og (c) `Sidst opdateret`- + evt. `Rapporter:`- + `Seneste rapport læst:`-linjerne — hold resten af filen intakt. Findes `## Rapport` ikke endnu, så indsæt den (fx efter Klientoverblik). Vis target-fil (navn + link) + de præcise nye blokke, vent på `ja`, skriv, bekræft tilbage.
- **`needs_reauth` / 403 / fejl:** skriv ikke. Lever de **copy-paste-klare** blokke (ny `## Klientoverblik`, evt. ny `## Rapport`, + de opdaterede `Sidst opdateret`/`Rapporter:`/`Seneste rapport læst:`-linjer) i kodeblokke, og sig: "Åbn AI-Context-filen <navn + link> og erstat de viste sektioner med dette. Jeg kan ikke skrive til filen lige nu (Workspace-MCP'en er ikke auth'et / mangler adgang)." Peg evt. på `inb-ads-context-publish` for en fuld genudgivelse (notér dens create-once-forbehold).

Opret ALDRIG en ny/dublet fil via Drive-connectoren her.

## Trin 7 — Rapport

Afslut med:
1. Siden-vinduet, de 3 kilders as-of-datoer, antal tilføjet/erstattet/fjernet, og skrive-udfald (gws-skrevet eller copy-paste-leveret).
2. **`## Datakilder`:** MCP-værktøjer kaldt (Drive `read_file_content`/`search_files`/`get_file_metadata`; HubSpot `*_search` med association-filter; evt. Ads `get_change_summary`; gws til skrivning), ID'erne, dato-vinduet, og enhver kilde der fejlede.

## Regler

- **Alt lever på Drive.** Indekset er indgangen; AI-Context-filen er konteksten + skrivemålet. Ingen lokal vault/note.
- **Read-only** mod Google Ads + HubSpot. Skriv aldrig til en konto eller et CRM-objekt.
- **Drive-connectoren (`10f9f31f…`) er den eneste Drive-læse-vej.** gws kun til den gated skrivning til AI-Context-filen.
- **Skriv kun efter diff-godkendelse.** ERSTAT/FJERN per-punkt; TILFØJ batchet; aldrig en uvist linje. Opret aldrig en dublet-fil.
- **Tidsløs-reglen:** foreslå aldrig at tilføje live-tal (ROAS/CPA/CPC/CTR/spend/counts/`LAST_30_DAYS`) eller present-tense performance-domme til Klientoverblik. Genformulér nyttige-men-forældede domme som håndtag.
- **Watermark = filens `Sidst opdateret`-linje;** ryk kun frem ved ren fuld-kilde-kørsel.
- **30-dages loft** på Ads `change_event` (`lookback_days` ≤ 29); tomt vindue = "ingen ændringer i perioden", aldrig "inaktiv".
- **MCP-fejlroute:** index/fil-ID'er (`Google Ads ID`/`HubSpot ID`) autoritative; sanity-check enhver payload; kassér forkert-routet data.
- **HubSpot `engagement_details` er 403** — brug `*_search` med `associations.company` EQ.
- **Rapporter:** Google Slides, nyeste først, høj prioritet; søg HELE klientmappen (ikke kun Paid Search); notér rapport-mappen i AI-Context-filen så næste kørsel er et direkte opslag.
- **Pausede kampagner er bevidste** — flag aldrig som negativt fund.
- Real Æ Ø Å. Dansk. Ingen emojis. Ingen tankestreger (komma/kolon). Marker manglende/utroværdige data; opfind aldrig kontekst.
