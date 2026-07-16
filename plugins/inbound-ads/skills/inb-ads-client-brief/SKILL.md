---
name: inb-ads-client-brief
description: "Giver et projektleder-overblik over én Google Ads-klient: hvem de er, hvad der for nylig er lavet og aftalt, aktuel status og åbne tråde, hentet fra klientens AI-Context-fil på Drive plus alt nyt siden sidste opdatering (Drive-dokumenter, HubSpot, seneste statusrapport). I samme kørsel kan det on-demand opdatere selve AI-Context-filen: ændringer foreslås som TILFØJ/ERSTAT/FJERN og skrives kun til Drive efter eksplicit godkendelse. Brug når brugeren siger 'brief mig på [kunde]', 'klientoverblik på [kunde]', 'hvad er nyt på [kunde]', 'saml mig op på [kunde]', 'projektleder-overblik på [kunde]', 'opdatér kontekst på [kunde]' eller 'opdatér AI-konteksten'. Makker til inb-ads-context-publish, som opretter en klients AI-Context-fil første gang, hvor dette skill briefer på den og vedligeholder den løbende."
---

# inb-ads-client-brief

Lever et projektleder-overblik over én Google Ads-klient — og kan i samme kørsel opdatere klientens AI-kontekst on-demand. To outputs, ét smæk:

1. **Projektleder-overblik** (hovedformålet): hvem klienten er, hvad der for nylig er lavet/aftalt, aktuel status, åbne tråde. Som en projektleder der lige er kommet op i fart på kunden. Leveres i ét af to formater brugeren vælger i Trin 0 — en delbar visuel **side** (claude.ai-artifact, default) eller struktureret tekst **i chatten** — begge med samme scanbare zone-struktur (`references/output-format.md`).
2. **Opdateret AI-kontekst** (on-demand, klientens AI-Context-fil på Drive): træk alt nyt siden sidste opdatering ind, herunder hvad der skal **fjernes/erstattes** — ikke kun tilføjes. Sker altid conversationelt i chatten, uanset briefets format.

Overblikket er altid gratis at levere; selve fil-opdateringen sker kun når der er noget nyt at flette ind, og altid efter godkendelse. Makker til `inb-ads-context-publish` (som publicerer en klients AI-Context-fil første gang). Dette skill briefer på filen bagefter og vedligeholder den. Læs `references/` for de dybe kontrakter; denne fil er den kørbare overflade.

## Kontekst

Alt lever på Google Drive — ingen lokal vault, ingen lokale noter.

- **Master-klientindekset** (Google Doc, id `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`, "Inbound CPH — Google Ads klient-index (AI Context)") — indgangen. Én række pr. klient: Klient, Google Ads ID, HubSpot ID, ClickUp folder, Stage, Drive-mappe, AI Context-fil, Noter.
- **Klientens AI-Context-fil** (et **native Google Doc** i klientens "AI Context"-undermappe, fx `Dantaxi - 7438308806`) — denne fil ER konteksten og kilden til sandhed. Filtype + sektions-skelet er låst i den delte kontrakt `../../shared/ai-context-file-contract.md` (samme kilde som `inb-ads-context-publish` opretter filen efter, så de to skills er enige om artefakttypen). Starter med `Sidst opdateret: YYYY-MM-DD`, indeholder ID-blok, durable sektioner og den 5-delte `## Klientoverblik`. (Det ER et native Google Doc, ikke en rå `.md` — det er præcis det, der gør `findAndReplaceInDoc` mulig til inline-ændringer i Trin 6; en rå `.md` kan ikke redigeres in-place af det værktøj.) Eksisterende `.md`-filer (kun Deloitte-outlieren, flagget som `.md` i indekset) konverteres til et Doc ved næste opdatering.
- **Klientens Drive-mappe** — hvor nye dokumenter og rapporter (statusdecks) ligger.

**Én Google-MCP til ALT: den Inbound Google Drive MCP (`mcp__acc7a973-…`).** Den læser (indekset, AI-Context-Docs, nye dokumenter, statusdecks) OG skriver den ene gated inline-ændring. Ingen anden Drive/Workspace-connector bruges.
- **Læsning:** `search` (rawQuery for dato/mime-filtre), `readGoogleDoc` (AI-Context-Doc + indeks), `listFolder`, deck-læserne (`getGoogleSlidesContent`; PDF via `convertPdfToGoogleDoc` → `readGoogleDoc` → `deleteItem`).
- **Inline-skrivning (Trin 6):** **KUN `findAndReplaceInDoc`.** Erstat den gamle `## Klientoverblik`-blok, evt. den gamle `## Rapport`-sektion, og watermark-linjerne via find-og-erstat på Doc'en. Brug IKKE `updateTextFile`/`updateDocFromMarkdown`/`insertText` til AI-Context-ændringer — `findAndReplaceInDoc` er den eneste tilladte inline-operation (surgisk, bevarer resten af Doc'en). Opret aldrig en dublet-fil for at "rette" en fejlet skrivning.

**Sprog:** dansk medmindre brugeren skriver engelsk. Real Æ Ø Å, aldrig ASCII (aa/oe/ae); tjek indholdet før enhver skrivning.

## Watermarks

To linjer i AI-Context-filen selv fungerer som watermarks — ingen separat tidsstempel-kolonne eller lokalt felt.

1. **`Sidst opdateret: YYYY-MM-DD`** — hoved-watermark for Drive-dokumenter + HubSpot + Ads.
   - Læses for at beregne siden-vinduet ("nyt siden <dato>").
   - Skrives til i dag kun når kørslen var ren (alle tre kilder hentet uden fejl) og brugeren godkendte ændringer.
   - **Partial-success:** fejlede en kilde (HubSpot 403, Drive socket-drop), så ryk IKKE linjen frem — notér i stedet per-kilde as-of i Klientoverblik-introlinjen, så næste kørsel henter hullet.
   - Mangler linjen (ældre format): behandl hele filen som siden-gulv, sig antagelsen højt, tilføj linjen ved skrivning.
2. **`Seneste rapport læst: <titel> [id: <fil-id>]`** — separat watermark for rapport-ingestion (rapporter kommer månedligt, ikke løbende). Matcher den nyeste deck i rapport-mappen → allerede indlæst, spring den dyre konvertering over (Trin 2 C + `references/report-ingestion.md`). Mangler linjen → nyeste deck er altid ny. Opdateres i samme gated skrivning som Klientoverblik (Trin 6).

## Trin 0 — Vælg output-format (allerførst)

Før al dataindhentning: spørg brugeren hvordan briefet skal leveres, med `AskUserQuestion`. Ét enkelt valg, i ord teamet forstår (ikke "artifact"/"HTML"/"Markdown"):

- **Spørgsmål:** "Hvordan vil du have briefet på <klient>?"
- **Rapport (side)** *(default, markér "Anbefalet")* — "En delbar, visuel side du kan åbne og scanne. God før et møde."
- **Rapport (i chatten)** — "Briefet skrevet direkte her i chatten. Hurtigst, og nemt at kopiere ind i noter."

Springer brugeren allerede formatet i sin besked ("brief mig på X **som side**" / "**i chatten**"), så spring spørgsmålet over og brug det. Ellers spørg hver gang — det er ét klik, ingen reel friktion. Formatet styrer KUN Trin 3-præsentationen; alt andet (fan-out, diff, gated skrivning) er format-uafhængigt. Hele kontrakten for begge formater ligger i `references/output-format.md` — læs den før du renderer i Trin 3.

## Trin 0.5 — Start i indekset (obligatorisk indgang)

Via den Inbound Google Drive MCP (`mcp__acc7a973-…`):
1. **Identificér klienten** (navn/domæne/konto). Uklart → spørg før du fortsætter.
2. **Åbn master-indekset:** `readGoogleDoc(documentId="1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA")`.
3. **Find klientens række:** Google Ads ID, HubSpot ID, **Stage** (customer/lead/opportunity/"ikke tagget" — antag aldrig aktiv retainer på en ikke-customer), Drive-mappe-link, AI-Context-fil-link, Noter (delt-mappe-caveats står her). Delte mapper (Lime/Retriever/GSGroup/Nemco/Julemærket/PhoneAlone/DI/EDC) → vælg det specifikke markeds række.
4. **Åbn klientens AI-Context-Doc** (`readGoogleDoc` på fil-id'et fra linket). Læs `Sidst opdateret`-linjen + den nuværende `## Klientoverblik`.
5. Ingen index-række eller ingen AI-Context-fil endnu: sig det, foreslå at køre `inb-ads-context-publish` først (den opretter filen), og stop — dette skill vedligeholder en eksisterende fil, det opretter den ikke.

## Trin 1 — Resolve + læs watermark

- **Siden-gulv** = AI-Context-filens `Sidst opdateret`-dato. Mangler den → behandl hele filen som gulv (bootstrap), sig antagelsen.
- Saml ID'erne fra **indeksrækken + AI-Context-filens ID-blok**: `Google Ads ID`, `HubSpot ID`, Drive-mappe-ID (fra mappe-linket), og en evt. allerede-noteret rapport-mappe (Trin 2 C). Index/fil-ID'er er autoritative over enhver MCP-payload (Ads-MCP'en fejlrouter).
- Beregn + vis siden-vinduet overalt (fx "siden 2026-06-17").

## Trin 2 — Fan-out: én ekspert-subagent per kilde, parallelt

Uddeleger kilde-fan-out'en til `drive-knowledge`-agenten (read-across-sources worker) via Task-værktøjet — den læser Drive/HubSpot/Ads-historik siden watermark og returnerer en konsolideret, kilde-attribueret opsummering. Skillet selv laver TILFØJ/ERSTAT/FJERN-diffen (Trin 4) og den gated skrivning (Trin 6). Giv `drive-knowledge` de resolvede ID'er (`Google Ads ID`, `HubSpot ID`, Drive-mappe-ID), siden-datoen, en evt. allerede-noteret rapport-mappe + `Seneste rapport læst`-watermark, og struktureret-output-kontrakten (`references/source-contracts.md`). Den er read-only mod alle kilder, honorerer tidsløs-reglen, fan-er de tre ekspert-læsninger nedenfor ud internt og returnerer kun fund (rå læsninger bliver i dens kontekst). Kan `drive-knowledge` ikke dispatches, så kør de tre ekspert-subagenter inline nedenfor.

Dispatch samtidigt (ét message, flere tool-kald), hver med de resolvede ID'er + siden-datoen + struktureret-output-kontrakten. Hver returnerer kun fund.

- **Drive-ekspert** (kun den Inbound Google Drive MCP, `mcp__acc7a973-…`):
  - **(A) Nye/ændrede dokumenter:** `listFolder(folderId='<Drive-mappe-ID>')` eller `search(rawQuery=true, query="'<Drive-mappe-ID>' in parents and modifiedTime > '<siden>T00:00:00Z'")`, rekursér undermapper, mærk per marked for delte mapper, `readGoogleDoc` på dokumenter i vinduet.
  - **(C) Rapporter (høj prioritet, statusmøde-decks):** mappen er ankeret, ikke filtypen — klientmappens undermappe `#1 - Præsentationer og statusmøder` (varianter: `... Statusmøder og -rapporter`, `... Præsentationer & statusmøder`, `#1 - Statusmøder`, `#1 - Møder`, en-dash `#1 – Præsentationer`; mønster = `#1`-præfiks + "sentation"/"statusm"/"Møder"). Nogle klienter har ingen `#1`-mappe men år-baserede `<Klient> møder 20XX`-mapper → fald tilbage til nyeste år. Andre har slet ingen rapport-mappe → accepter "ingen" pænt, opfind ikke.
    - **Find nyeste deck:** står rapport-mappen allerede i AI-Context-filen, gå direkte dertil (`search '<mappe-id>' in parents and trashed=false`), ellers find mappen på navn (`title contains 'sentation' or title contains 'statusm' or title contains 'Møder'`; ignorér `OLD - ...`) og returnér den til hovedskillet så den kan gemmes (Trin 5/6). Vælg nyeste deck efter `YYYY-MM` i titlen (ikke `modifiedTime`; en måned findes ofte som både PDF og PPTX).
    - **Er nyeste deck nyere end `Seneste rapport læst`** → kald `references/report-ingestion.md` for at konvertere + udtrække et rapport-resumé (kun når ny — konvertering er dyr). Allerede indlæst → spring over. Ulæselig deck → vis linket, opfind ikke. Degradér på socket-drop, ingen blind-retry; rapportér partial.
    - Rapport-indholdet går i sin EGEN `## Rapport`-sektion (Trin 6), IKKE ind i Klientoverblik-diff'en (Trin 4) — rapport-resuméet forbliver sporbart, Klientoverblik forbliver ren durable kontekst.
- **HubSpot-ekspert** (HubSpot MCP): firma via indeksrækkens `HubSpot ID`. Aldrig `engagement_details_*` (403). Brug `notes_search`/`emails_search`/`calls_search`/`meetings_search`/`tasks_search` med `associations.company` EQ `<HubSpot ID>` + recency. **`hs_createdate` er det PRIMÆRE "nyt siden"-filter — IKKE `hs_lastmodifieddate`.** HubSpot bulk-rører `hs_lastmodifieddate` ved re-index (set 2026-06-30: 141 falske positiver, måneder-gammel mail rapporteret som frisk); filtrér derfor på `hs_createdate > siden` for at fange reelt nye objekter, og brug kun `hs_lastmodifieddate` som sekundær bekræftelse hvis relevant. Afkod lifecycle/deal-stage-ID'er til labels. Kollaps til menneskelæsbar aktivitet. Fejl → markér HubSpot partial.
- **Ads-ekspert** (Google Ads MCP, let): kun durable fakta til overblikkets "hvad ændrede sig på kontoen"-linje. `get_change_summary(customer_id=<Google Ads ID>, lookback_days=29)` / `get_change_history` (≤29; 30 hard-fejler `START_DATE_TOO_OLD`). Bulk-kollaps på (timestamp, ressourcetype). Sanity-check identitet mod `Google Ads ID`; kassér mismatch (fejlroute-vagt).

Hver subagents partial/ren-status fødes ind i watermark-reglen (Trin 6). Alt read-only.

## Trin 3 — Projektleder-overblik (OUTPUT #1, FØR diff'en)

Syntetisér de tre subagenters fund til briefet og render det i **det format brugeren valgte i Trin 0**. Den fulde præsentations-kontrakt (zone-struktur, husstil, begge formater) ligger i `references/output-format.md` — følg den. Syntese, ikke et dump; hvert nyt-fund parres med et "Betyder:" (så-hvad), handlinger står øverst med ejer/deadline, og kildeteknik (delvis/watermark/as-of) hører i datagrundlag-footeren, ikke i selve briefet.

Zonerne (fælles for begge formater, i læse-prioritet): **BLUF/header** (hvem + status-chip + "Kort sagt"-verdikt + meta) → **Hvad kræver handling** (Beslutning / Handlinger / Venter på, adskilt, ikke prosa) → **Hvad er nyt** (per kilde, med freshness-pill + "Betyder:") → **Hvem de er & hvor vi står** (komprimeret durable kontekst) → *(gaten, Trin 4-5)* → **Datagrundlag & kilder** (footer).

- **Rapport (side):** byg HTML'en fra `references/brief-template.html` (kopiér den, behold `<style>` + den indlejrede Manrope-font uændret, erstat kun indholdet), skriv til en scratchpad-`.html`, og publicér med `Artifact`-værktøjet. Giv linket i chatten med en kort intro. Se `references/output-format.md` § Format A for levering + font-reglen (CSP blokerer font-CDN → Manrope skal være inlinet).
- **Rapport (i chatten):** skriv zonerne som struktureret Markdown direkte i svaret. Se `references/output-format.md` § Format B for skabelonen.

**Diffen (Trin 4-6) sker ALTID i chatten** uanset format — også når briefet blev en side. En artifact kan ikke godkende eller skrive noget, og human-in-the-loop på writes er en hard regel. Efter briefet (linket eller Markdown), sig: "Herunder er mine forslag til at opdatere selve AI-konteksten" → diff'en i chatten.

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

## Trin 6 — Skriv den opdaterede AI-Context-Doc (gated, KUN findAndReplaceInDoc)

Den eneste skrivning, og den sker udelukkende via **`findAndReplaceInDoc`** på den Inbound Google Drive MCP (`mcp__acc7a973-…`). AI-Context-filen er en Google Doc, så find-og-erstat er den rette surgiske operation; brug ALDRIG `updateTextFile`/`updateDocFromMarkdown`/`insertText` her.

1. **Vis først** target-Doc (navn + link) + de præcise nye blokke (ny `## Klientoverblik`; evt. ny `## Rapport`; opdaterede `Sidst opdateret`/`Rapporter:`/`Seneste rapport læst:`-linjer). Vent på eksplicit `ja`.
2. **Erstat surgisk med `findAndReplaceInDoc`**, ét kald per blok, `findText` = den nøjagtige eksisterende tekst (nok omkringliggende kontekst til at matche præcis én gang), `replaceText` = den nye:
   - (a) den gamle `## Klientoverblik`-blok → den nye.
   - (b) den gamle `## Rapport`-sektion → den nye (KUN hvis en ny rapport blev indlæst).
   - (c) `Sidst opdateret:`-linjen (gammel dato → i dag), + evt. `Rapporter:`- og `Seneste rapport læst:`-linjer.
   - Kør evt. `findAndReplaceInDoc` med `dryRun=true` først for at bekræfte at `findText` matcher præcis én gang, før den rigtige erstatning.
3. **Findes `## Rapport` ikke endnu** i Doc'en (så der ikke er noget at erstatte): `findAndReplaceInDoc` kan ikke indsætte ny tekst. Erstat da slutningen af `## Klientoverblik`-blokken med "den blok + `\n\n## Rapport\n\n<ny sektion>`" i ét find-og-erstat (dvs. gør indsættelsen til en erstatning af et unikt ankerstykke). Samme trick for en manglende `Rapporter:`-linje: udvid en tilstødende ID-blok-linje.
4. **Bekræft tilbage** hvad der blev erstattet.

Kan et `findText` ikke matche (Doc'ens tekst afviger fra forventet), så STOP og vis brugeren den copy-paste-klare blok i stedet — skriv aldrig et gæt. Opret ALDRIG en ny/dublet fil for at "rette" en fejlet skrivning (en dublet kan ikke fjernes rent).

## Trin 7 — Rapport

Afslut med:
1. Siden-vinduet, de 3 kilders as-of-datoer, antal tilføjet/erstattet/fjernet, og skrive-udfald (`findAndReplaceInDoc`-skrevet eller copy-paste-leveret hvis et match fejlede).
2. **`## Datakilder`:** MCP-værktøjer kaldt (Inbound Google Drive `search`/`readGoogleDoc`/`listFolder` + `findAndReplaceInDoc` til skrivning; HubSpot `*_search` med association-filter; evt. Ads `get_change_summary`), ID'erne, dato-vinduet, og enhver kilde der fejlede.

## Regler

- **Format vælges i Trin 0**, styrer kun Trin 3-præsentationen. Zone-struktur + begge formaters kontrakt: `references/output-format.md`. Side-formatet kopierer `references/brief-template.html` (Inbound-husstil, Manrope inlinet — link aldrig et font-CDN i en artifact, CSP blokerer det).
- **Brief og gate er to dokumenter.** Briefet (læse) er adskilt fra kontekst-diffen (beslut-og-skriv). Diffens godkendelse + `findAndReplaceInDoc`-skrivning sker ALTID i chatten, aldrig på en artifact-side.
- **30-dages loft** på Ads `change_event` (`lookback_days` ≤ 29); tomt vindue = "ingen ændringer i perioden", aldrig "inaktiv".
- **Pausede kampagner er bevidste** — flag aldrig som negativt fund.
- Ingen tankestreger (komma/kolon). Marker manglende/utroværdige data; opfind aldrig kontekst. Real Æ Ø Å (aldrig aa/oe/ae), også i HTML-siden — grep før publicering.
- Emojis kun som status-pills i chat-formatet (🟢 🟠 🔵 ⚪ + ord); ellers ingen emojis. Side-formatet bruger SVG-ikoner, ikke emoji.
