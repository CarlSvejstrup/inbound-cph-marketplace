---
name: inb-ads-context-update
description: "Opdaterer en eksisterende klients AI-Context-fil on-demand ved at hente alt nyt siden sidste opdatering fra Drive, HubSpot og seneste statusrapport, og leverer samtidig et projektleder-overblik i chatten, mens ændringer foreslås som TILFØJ/ERSTAT/FJERN og kun skrives til Drive-filen efter eksplicit godkendelse. Makker til inb-ads-context-publish, som opretter en klients AI-Context-fil første gang, hvor dette skill vedligeholder den løbende."
---

# inb-ads-context-update

Opdatér én klients AI-kontekst on-demand, og lever et projektleder-overblik i samme kørsel:

1. **Projektleder-overblik** (chat): hvem klienten er, hvad der for nyligt er lavet/aftalt, aktuel status, åbne tråde.
2. **Opdateret AI-kontekst** (klientens AI-Context-fil på Drive): træk alt nyt siden sidste opdatering ind, herunder hvad der skal **fjernes/erstattes** — ikke kun tilføjes.

Makker til `inb-ads-context-publish` (som publicerer en klients AI-Context-fil første gang). Dette skill vedligeholder den fil bagefter. Læs `references/` for de dybe kontrakter; denne fil er den kørbare overflade.

## Kontekst

Alt lever på Google Drive — ingen lokal vault, ingen lokale noter.

- **Master-klientindekset** (Google Doc, id `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`, "Inbound CPH — Google Ads klient-index (AI Context)") — indgangen. Én række pr. klient: Klient, Google Ads ID, HubSpot ID, ClickUp folder, Stage, Drive-mappe, AI Context-fil, Noter.
- **Klientens AI-Context-fil** (`.md` i klientens "AI Context"-undermappe, fx `Dantaxi - 7438308806.md`) — denne fil ER konteksten og kilden til sandhed. Starter med `Sidst opdateret: YYYY-MM-DD`, indeholder ID-blok, durable sektioner og den 5-delte `## Klientoverblik`.
- **Klientens Drive-mappe** — hvor nye dokumenter og rapporter (statusdecks) ligger.

**To Google-MCP'er, forskellig rolle og auth:**
- **Drive-connectoren** (`mcp__10f9f31f-…`) — den ENESTE læse-vej til Drive. Create-only (`create_file`, `copy_file`; intet append/update/delete).
- **Workspace-MCP'en** (`mcp__acc7a973-…`, "gws") — kan opdatere en Drive-fil på stedet (`updateTextFile`, `updateDocFromMarkdown`, `findAndReplaceInDoc`). Brug kun til den gated skrivning i Trin 6; kan være i `needs_reauth` eller mangle adgang, altid med fallback.

**Sprog:** dansk medmindre brugeren skriver engelsk. Real Æ Ø Å, aldrig ASCII (aa/oe/ae); tjek indholdet før enhver skrivning.

## Watermarks

To linjer i AI-Context-filen selv fungerer som watermarks — ingen separat tidsstempel-kolonne eller lokalt felt.

1. **`Sidst opdateret: YYYY-MM-DD`** — hoved-watermark for Drive-dokumenter + HubSpot + Ads.
   - Læses for at beregne siden-vinduet ("nyt siden <dato>").
   - Skrives til i dag kun når kørslen var ren (alle tre kilder hentet uden fejl) og brugeren godkendte ændringer.
   - **Partial-success:** fejlede en kilde (HubSpot 403, Drive socket-drop), så ryk IKKE linjen frem — notér i stedet per-kilde as-of i Klientoverblik-introlinjen, så næste kørsel henter hullet.
   - Mangler linjen (ældre format): behandl hele filen som siden-gulv, sig antagelsen højt, tilføj linjen ved skrivning.
2. **`Seneste rapport læst: <titel> [id: <fil-id>]`** — separat watermark for rapport-ingestion (rapporter kommer månedligt, ikke løbende). Matcher den nyeste deck i rapport-mappen → allerede indlæst, spring den dyre konvertering over (Trin 2 C + `references/report-ingestion.md`). Mangler linjen → nyeste deck er altid ny. Opdateres i samme gated skrivning som Klientoverblik (Trin 6).

## Trin 0.5 — Start i indekset (obligatorisk indgang)

Via Drive-connectoren:
1. **Identificér klienten** (navn/domæne/konto). Uklart → spørg før du fortsætter.
2. **Åbn master-indekset:** `read_file_content` på id `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`.
3. **Find klientens række:** Google Ads ID, HubSpot ID, **Stage** (customer/lead/opportunity/"ikke tagget" — antag aldrig aktiv retainer på en ikke-customer), Drive-mappe-link, AI-Context-fil-link, Noter (delt-mappe-caveats står her). Delte mapper (Lime/Retriever/GSGroup/Nemco/Julemærket/PhoneAlone/DI/EDC) → vælg det specifikke markeds række.
4. **Åbn klientens AI-Context-fil** (`read_file_content` via fil-linket). Læs `Sidst opdateret`-linjen + den nuværende `## Klientoverblik`.
5. Ingen index-række eller ingen AI-Context-fil endnu: sig det, foreslå at køre `inb-ads-context-publish` først (den opretter filen), og stop — dette skill vedligeholder en eksisterende fil, det opretter den ikke.

## Trin 1 — Resolve + læs watermark

- **Siden-gulv** = AI-Context-filens `Sidst opdateret`-dato. Mangler den → behandl hele filen som gulv (bootstrap), sig antagelsen.
- Saml ID'erne fra **indeksrækken + AI-Context-filens ID-blok**: `Google Ads ID`, `HubSpot ID`, Drive-mappe-ID (fra mappe-linket), og en evt. allerede-noteret rapport-mappe (Trin 2 C). Index/fil-ID'er er autoritative over enhver MCP-payload (Ads-MCP'en fejlrouter).
- Beregn + vis siden-vinduet overalt (fx "siden 2026-06-17").

## Trin 2 — Fan-out: én ekspert-subagent per kilde, parallelt

Uddeleger kilde-fan-out'en til `drive-knowledge`-agenten (read-across-sources worker) via Task-værktøjet — den læser Drive/HubSpot/Ads-historik siden watermark og returnerer en konsolideret, kilde-attribueret opsummering. Skillet selv laver TILFØJ/ERSTAT/FJERN-diffen (Trin 4) og den gated skrivning (Trin 6). Giv `drive-knowledge` de resolvede ID'er (`Google Ads ID`, `HubSpot ID`, Drive-mappe-ID), siden-datoen, en evt. allerede-noteret rapport-mappe + `Seneste rapport læst`-watermark, og struktureret-output-kontrakten (`references/source-contracts.md`). Den er read-only mod alle kilder, honorerer tidsløs-reglen, fan-er de tre ekspert-læsninger nedenfor ud internt og returnerer kun fund (rå læsninger bliver i dens kontekst). Kan `drive-knowledge` ikke dispatches, så kør de tre ekspert-subagenter inline nedenfor.

Dispatch samtidigt (ét message, flere tool-kald), hver med de resolvede ID'er + siden-datoen + struktureret-output-kontrakten. Hver returnerer kun fund.

- **Drive-ekspert** (kun Drive-connectoren):
  - **(A) Nye/ændrede dokumenter:** `search_files parentId='<Drive-mappe-ID>'` + `get_file_metadata`, filtrér `modifiedTime > siden` (RFC-3339 UTC), rekursér undermapper, mærk per marked for delte mapper, `read_file_content` på dokumenter i vinduet.
  - **(C) Rapporter (høj prioritet, statusmøde-decks):** mappen er ankeret, ikke filtypen — klientmappens undermappe `#1 - Præsentationer og statusmøder` (varianter: `... Statusmøder og -rapporter`, `... Præsentationer & statusmøder`, `#1 - Statusmøder`, `#1 - Møder`, en-dash `#1 – Præsentationer`; mønster = `#1`-præfiks + "sentation"/"statusm"/"Møder"). Nogle klienter har ingen `#1`-mappe men år-baserede `<Klient> møder 20XX`-mapper → fald tilbage til nyeste år. Andre har slet ingen rapport-mappe → accepter "ingen" pænt, opfind ikke.
    - **Find nyeste deck:** står rapport-mappen allerede i AI-Context-filen, gå direkte dertil (`search '<mappe-id>' in parents and trashed=false`), ellers find mappen på navn (`title contains 'sentation' or title contains 'statusm' or title contains 'Møder'`; ignorér `OLD - ...`) og returnér den til hovedskillet så den kan gemmes (Trin 5/6). Vælg nyeste deck efter `YYYY-MM` i titlen (ikke `modifiedTime`; en måned findes ofte som både PDF og PPTX).
    - **Er nyeste deck nyere end `Seneste rapport læst`** → kald `references/report-ingestion.md` for at konvertere + udtrække et rapport-resumé (kun når ny — konvertering er dyr). Allerede indlæst → spring over. Ulæselig deck → vis linket, opfind ikke. Degradér på socket-drop, ingen blind-retry; rapportér partial.
    - Rapport-indholdet går i sin EGEN `## Rapport`-sektion (Trin 6), IKKE ind i Klientoverblik-diff'en (Trin 4) — rapport-resuméet forbliver sporbart, Klientoverblik forbliver ren durable kontekst.
- **HubSpot-ekspert** (HubSpot MCP): firma via indeksrækkens `HubSpot ID`. Aldrig `engagement_details_*` (403). Brug `notes_search`/`emails_search`/`calls_search`/`meetings_search`/`tasks_search` med `associations.company` EQ `<HubSpot ID>` + recency på `hs_lastmodifieddate`/`createdAt`/`updatedAt` `> siden`. Afkod lifecycle/deal-stage-ID'er til labels. Kollaps til menneskelæsbar aktivitet. Fejl → markér HubSpot partial.
- **Ads-ekspert** (Google Ads MCP, let): kun durable fakta til overblikkets "hvad ændrede sig på kontoen"-linje. `get_change_summary(customer_id=<Google Ads ID>, lookback_days=29)` / `get_change_history` (≤29; 30 hard-fejler `START_DATE_TOO_OLD`). Bulk-kollaps på (timestamp, ressourcetype). Sanity-check identitet mod `Google Ads ID`; kassér mismatch (fejlroute-vagt).

Hver subagents partial/ren-status fødes ind i watermark-reglen (Trin 6). Alt read-only.

## Trin 3 — Projektleder-overblik (OUTPUT #1, kun chat, FØR diff'en)

Syntetisér de tre subagenters fund. Sektioner, dansk:
- **Hvem de er.** 2-3 linjer fra AI-Context-filens Klientoverblik > Overblik (klient, marked, specialist, tier, budget, kontakt).
- **Hvor vi står.** Vigtigste hårde rammer + mål + åbne håndtag fra den nuværende Klientoverblik.
- **Hvad er nyt siden `<Sidst opdateret>`.** Per kilde: Drive (N dok.), HubSpot (N mails/noter), Rapporter (nyeste deck + kernebudskab, eller "ingen nyere rapport fundet").
- **Åbne tråde & håndtag lige nu.** Ubesvarede mails, ventende aftaler, håndtag fra rapporten, deadlines.
- **Datagrundlag & huller.** Hvilke kilder blev læst/fejlede + tidsvinduet.

Syntese, ikke et dump. Sig derefter: "Herunder er mine forslag til at opdatere selve AI-konteksten" → diff'en.

## Trin 4 — Diff: TILFØJ / ERSTAT / FJERN

Sammenlign nyt materiale **fra Drive-dokumenter + HubSpot + Ads** mod den nuværende `## Klientoverblik`. Rapport-indhold indgår IKKE her — det har sin egen `## Rapport`-sektion (Trin 6) og røres ikke af diff'en. Én dansk review-tabel: `# | Type | Sektion | Nuværende | Foreslået | Kilde`. Se `references/diff-classification.md` for den fulde kontrakt.

- Kør hver **TILFØJ** gennem tidsløs-vagten: afvis live-tal/domme; genformulér nyttige-men-forældede domme som **håndtag** ("hæv budget hvor markeder er capped — verificér først").
- Argumentér hver **ERSTAT/FJERN** med dens kilde (fx rapport markerer et håndtag afsluttet → FJERN). Vær kritisk, ikke destruktiv — foreslå, lad mennesket bestemme.
- Intet skrives endnu.

## Trin 5 — Human-in-the-loop-gate (godkend ændringerne)

- **TILFØJ:** ét batchet bekræft ("tilføj 1,4,5? ja/vælg/nej").
- **ERSTAT/FJERN:** eksplicit per-punkt (eller udtrykkeligt-listet sæt), vis den præcise tekst der fjernes.
- **Rapport-mappe:** blev en kandidat fundet i Trin 2 C og er den ikke allerede noteret i filen, foreslå at tilføje en `Rapporter:`-linje i ID-blokken med mappe-linket; bekræft.
- **Ny rapport:** blev en NY rapport indlæst (Trin 2 C via `report-ingestion.md`), indgår (a) den nye/erstattede `## Rapport`-sektion og (b) den opdaterede `Seneste rapport læst:`-linje (titel + fil-id) i skrivningen. `## Rapport` erstattes med nyeste rapport (ikke append) og flettes ikke ind i Klientoverblik. Ingen ny rapport indlæst → rør ikke `## Rapport`.
- Saml de godkendte ændringer (Klientoverblik-diff: TILFØJ + godkendte ERSTAT/FJERN; evt. `Rapporter:`-linje; evt. ny `## Rapport`-sektion + `Seneste rapport læst:`-linje) til den samlede skrivning. Opdatér `Sidst opdateret`-linjen til i dag kun hvis alle 3 kilder var rene (ellers lad stå + notér per-kilde as-of i Klientoverblik-introlinjen). Intet er skrevet endnu — det sker i Trin 6.

## Trin 6 — Skriv den opdaterede AI-Context-fil (gated, gws-eller-fallback)

Den eneste skrivning. Probe gws (`authGetStatus` på `mcp__acc7a973-…`):
- **Authed + filen skrivbar:** gated skrivning til AI-Context-filen. Foretræk surgiske `findAndReplaceInDoc`/`updateTextFile`-operationer der erstatter (a) den gamle `## Klientoverblik`-blok, (b) den gamle `## Rapport`-sektion hvis en ny rapport blev indlæst, og (c) `Sidst opdateret`- + evt. `Rapporter:`- + `Seneste rapport læst:`-linjerne — hold resten af filen intakt. Findes `## Rapport` ikke endnu, indsæt den (fx efter Klientoverblik). Vis target-fil (navn + link) + de præcise nye blokke, vent på `ja`, skriv, bekræft tilbage.
- **`needs_reauth` / 403 / fejl:** skriv ikke. Lever de copy-paste-klare blokke (ny `## Klientoverblik`, evt. ny `## Rapport`, + de opdaterede `Sidst opdateret`/`Rapporter:`/`Seneste rapport læst:`-linjer) i kodeblokke, og sig: "Åbn AI-Context-filen <navn + link> og erstat de viste sektioner med dette. Jeg kan ikke skrive til filen lige nu (Workspace-MCP'en er ikke auth'et / mangler adgang)." Peg evt. på `inb-ads-context-publish` for en fuld genudgivelse (notér dens create-once-forbehold).

Opret aldrig en ny/dublet fil via Drive-connectoren her — heller ikke for at "rette" en fejlet gws-skrivning (en dublet kan ikke fjernes programmatisk).

## Trin 7 — Rapport

Afslut med:
1. Siden-vinduet, de 3 kilders as-of-datoer, antal tilføjet/erstattet/fjernet, og skrive-udfald (gws-skrevet eller copy-paste-leveret).
2. **`## Datakilder`:** MCP-værktøjer kaldt (Drive `read_file_content`/`search_files`/`get_file_metadata`; HubSpot `*_search` med association-filter; evt. Ads `get_change_summary`; gws til skrivning), ID'erne, dato-vinduet, og enhver kilde der fejlede.

## Regler

- **30-dages loft** på Ads `change_event` (`lookback_days` ≤ 29); tomt vindue = "ingen ændringer i perioden", aldrig "inaktiv".
- **Pausede kampagner er bevidste** — flag aldrig som negativt fund.
- Ingen emojis. Ingen tankestreger (komma/kolon). Marker manglende/utroværdige data; opfind aldrig kontekst.
