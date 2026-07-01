---
name: inb-ads-search-term-analyse
description: Skarp, samtale-drevet søgeterm-analyse af én LIVE Google Ads-konto, der leverer INTERESSANTE indsigter — ikke bare den flade liste Google Ads giver. Filtrerer data server-side i GAQL så selv 1000+ termer aldrig læsses rå ind i kontekst, kører et let script (digest.py) der ruller rækkerne til en kompakt indsigts-brief (systemiske spild-temaer via n-gram, vinder-temaer, intent-linser, match-type-lækage, struktur-smell, udækkede vindere), og FØRER så en samtale om fundene — I beslutter SAMMEN hvad der skal blokeres og promoveres. Efter en EKSPLICIT bekræftelse af hele listen tilføjer den negatives og keywords direkte i kontoen via MCP (dry-run så commit), eller laver Editor-CSV som fallback. Read-only indtil du siger ja. VIGTIGT — 0 konverteringer er IKKE bevis for spild når folk ringer. Brug når brugeren siger "search term", "søgeterm-analyse", "analysér søgetermerne", "gå søgetermerne igennem", "find negatives og keywords", eller vil tale sig frem til beslutningerne og tilføje dem. Svarer på dansk.
---

# search-term-analyse

Én konto. Målet er indsigt, ikke en tabel — og derefter en samtale, ikke en aflevering. Du graver
mønstrene frem, I beslutter sammen, og først efter en eksplicit bekræftelse tilføjer du de aftalte
negatives/keywords (live via MCP, CSV, eller Excel). Read-only indtil da. Svar på dansk.

## Ufravigelige tjek — kør HVER gang (skim ikke forbi)

Resten af dokumentet er *hvordan*. Disse fem er *hvad der aldrig må svigte* — også på en travl dag
eller en svag model:

1. **AI Context FØRST** (Trin 0). Ingen analyse på en navngiven klient uden at have læst klientens
   AI Context — det er ground truth for ID'er, rammer og hvad de tilbyder.
2. **Gem pullet ordret som JSON** (Trin 3). Tool-svaret skrives 1:1 til en `.json`-fil. Gen-tast,
   rens eller opfind ALDRIG rækker; skriv aldrig et Python-script med en `data = [...]`-liste.
3. **Læs aldrig de rå rækker.** Kør `digest.py` på filen og læs den lille brief (Trin 4).
4. **Web-validér HVER kandidat — negatives OG nye keywords — FØR du viser udkastet** (Trin 5). Intet
   forslag når skærmen uvalideret. For hver kandidat: tjek aktive keywords (`keyword_view`) + AI
   Context + en web-søgning på `"<brand> <term>"` der leder efter en landingsside/et tilbud.
   Web-søgningen er ALTID, ikke kun ved tvivl — spring den aldrig over.
   - **Negativ:** findes der et aktivt keyword, et tilbud eller en landingsside → den er IKKE en
     negativ (kernetrafik/dæknings-hul; en negativ må aldrig overlappe et aktivt keyword). Kun
     bekræftet off-offering blokeres.
   - **Nyt keyword:** der SKAL findes en relevant landingsside/et tilbud at sende trafikken til.
     Gør der ikke det, tilføj den ikke — flag i stedet at siden mangler. Et keyword uden relevant
     landingsside er spildte klik.
5. **Read-only indtil eksplicit bekræftelse** (Trin 6). Mutér kun det der er godkendt; dry-run før
   commit. Og 0 konverteringer er IKKE bevis for spild på en konto hvor folk ringer.

## Forudsætning

Google Ads MCP + et `customer_id`. Ingen MCP → sig det og stop. Sæt `LIB=${CLAUDE_SKILL_DIR}/lib`.
MCP'en kan skrive til kontoen (`add_negative_keywords`, `add_keywords`) — men kun i Trin 7, og kun
efter bekræftelsen i Trin 6.

## Trin 0 — Hent klient-kontekst (AI Context) FØRST

Før alt andet på en navngiven klient — og før du henter søgeterm-rapporten:

1. **Identificér klienten.** Uklart → spørg hvilken klient før du fortsætter.
2. **Åbn master-klientindekset i Drive:** `search_files` efter Google Doc'en
   `Inbound CPH — Google Ads klient-index (AI Context)` (id `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`,
   i "A - Kunder"), læs med `read_file_content`. Den mapper hver klient til Google Ads ID, HubSpot ID,
   ClickUp-mappe, Stage, Drive-mappe og AI Context-fil.
3. **Find klientens række** (navn/domæne/Ads-ID). Notér **Stage** — en ikke-`customer`-stage betyder en
   ikke-lukket konto; vægt anbefalinger derefter. Delte mapper (Lime, Retriever/Infomedia, GSGroup,
   Nemco, Julemærket, PhoneAlone, DI): vælg rækken for det specifikke marked/konto.
4. **Åbn klientens AI Context** via Drive-linket (`read_file_content`) og tag den ind: ID'er,
   kontakter, hårde rammer, mål/KPI'er, navngivningskonvention og budstrategi-norm — så
   negatives/keywords flugter med klientens faktiske opsætning frem for et gæt.
   - **Fald tilbage hvis den linkede fil ikke kan læses.** Uploadede `.md`-filer er ofte blokeret for
     AI-adgang i Drive ("...ineligible to be used in generative AI contexts"). Sker det: `search_files`
     i klientens AI Context-mappe (parentId-søgning) efter **Google Doc-versionen** — typisk
     `<Klient> - Projektoverblik` eller en doc med "AI Context" i navnet — og læs den. Google Docs er
     læsbare hvor rå `.md`-uploads ikke er. Forsøg ALTID dette fallback før du erklærer konteksten utilgængelig.

Ingen række, og hverken `.md` eller Google Doc kan læses: sig det, fortsæt med den kontekst du kan samle
(Drive-mappe, Ads MCP) — men flag hullet. Spring aldrig opslaget stille over. (Tip til mennesket: hvis
`.md`-filen skal kunne læses fremover, konvertér den til et Google Doc eller slå AI-adgang til på filen.)

## Trin 1 — Intake (ét `AskUserQuestion`-kald)

Udled så meget som muligt først; saml resten i ét kald:

1. **Klient + `customer_id`** — normalt fra Trin 0; bekræft bare. Mangler det → `list_accessible_accounts`.
2. **Analysevindue** — default sidste 90 dage (`Sidste 90 dage (Anbefalet)`, `Sidste 30 dage`, `Andet`).
   Vinduet bestemmer kilden (Trin 3): `get_search_terms_report`s `date_range` accepterer KUN Googles
   literaler (`LAST_30_DAYS`, `LAST_14_DAYS`, `LAST_7_DAYS`, `THIS_MONTH`, `LAST_MONTH`) — `BETWEEN`
   OG `LAST_90_DAYS` afvises. Så ≤30 dage → rapporten; >30 dage / custom → `run_custom_gaql`.
3. **Scope** — hele kontoen eller specifik kampagne (→ `campaign_id`).
4. **Filter-tærskel** (lethedsgrebet — styrer payloadets størrelse). Byg WHERE med
   `slim.where_predicate(dim, value)`: `Forbrug ≥ 50 kr (anbefalet)` (`cost`/50) · `Forbrug ≥ andet` ·
   `Impressions ≥ N` (kan tabe høj-forbrugs/lav-visnings-term) · `Alt` (advar: tungt på stor konto).
   Rapportér altid "trak X termer (tærskel: …)".
5. **Hvilken konvertering tæller** — alle, eller kun primære (leads/opkald)? Ændrer hvad der er vinder
   vs. spild. Vil brugeren skille dem ad → segmentér på `segments.conversion_action`. Ved tvivl: antag
   alle, men skriv forbeholdet.

## Trin 2 — Forstå tilbuddet billigt (forside + ad groups)

Du skal kunne kende "vores by/ydelse" fra "ikke vores tilbud". Ét `firecrawl-scrape` af forsiden +
ad group-navnene (de staver geografien + ydelses-opdelingen). Skriv 3-5 linjers forståelse til dig
selv. Fejler scrape: brug ad group-navnene og sig det.

## Trin 3 — Hent LET (server-side filter FØR kontekst)

Filtrér ALTID server-side — det er der letheden kommer fra.

**≤30 dage:** `get_search_terms_report(customer_id, date_range=LAST_30_DAYS, campaign_id?, limit)`.

**>30 dage / custom:** `run_custom_gaql`:
```sql
SELECT search_term_view.search_term, search_term_view.status,
       segments.keyword.info.text, segments.keyword.info.match_type,
       campaign.id, campaign.name, ad_group.id, ad_group.name,
       metrics.impressions, metrics.clicks, metrics.cost_micros,
       metrics.conversions, metrics.conversions_value
FROM search_term_view
WHERE segments.date BETWEEN '<start>' AND '<slut>'
  AND <FILTER-PRÆDIKAT>                 -- slim.where_predicate(dim, value)
ORDER BY metrics.cost_micros DESC
LIMIT 1000
```
`cost`/50 → `metrics.cost_micros >= 50000000`. Rammer `LIMIT` → sig det ("trak de 1000 dyreste").

**Gem svaret (jf. Ufravigeligt tjek #2):** skriv tool-svaret ordret til en `.json`-fil (fx
`~/Downloads/_st_raw.json`) med fil-værktøjet — hele `{"results": [...]}`, præcis som returneret. Aldrig
et Python-script, aldrig håndtastede/opfundne rækker. Data skal være data. Du behøver ikke læse filen.

## Trin 4 — Byg indsigts-briefen (`digest.py`)

```bash
python3 $LIB/digest.py --in ~/Downloads/_st_raw.json --out ~/Downloads/_st_digest.json --top 20
```
Læs den printede brief — ikke de rå rækker. Den slanker (dropper skrald, aggregerer samme term på
tværs af ad groups), kører n-gram, og ruller op til: overblik (forbrug, konv, blended CPA, 0-konv-andel),
top-forbrug, systemiske spild-temaer, vinder-temaer (udækkede), intent-linser, match-type-lækage,
struktur-smell, udækkede vindere. `--top` er kun rækker pr. tabel — hele datasættet analyseres. Læg
gerne egne observationer oveni (sært cost/konv, stavevariant, geo udenfor dækning, brand I ikke ejer).

## Trin 5 — Verificér, præsentér ét udkast, før så en samtale

Rytmen: **verificér negativ-kandidater → ét samlet udkast → almindelig samtale → enighed.** Du forhører
ikke brugeren term for term — du har lavet analysen, så kom med ét bud.

**Først: web-validér hver kandidat — BÅDE negatives og nye keywords (Ufravigeligt tjek #4) — FØR
udkastet vises.** For hver: aktive keywords (`keyword_view`) → AI Context → **en web-søgning på
`"<brand> <term>"` (altid, ikke kun ved tvivl) der leder efter en landingsside/et tilbud.** En negativ
droppes hvis siden/tilbuddet findes (så tilbyder de det); et nyt keyword tilføjes kun hvis en relevant
landingsside findes (ellers er det spildte klik — flag at siden mangler). Det er gjort FÆRDIGT inden du
åbner munden; udkastet indeholder kun validerede forslag, og du viser kort hvad du tjekkede ud for hver.
(Især ydelses-termer som `mommy makeover`, `maveplastik` — nemme at antage forkert.)

Så samtalen:
1. **Læg ét konkret udkast på bordet, i prosa:** de negatives og nye keywords du foreslår (hver med
   keyword, match-type, hvor) + 2-4 interessante ting værd at tale om. Med tallet bag hvert punkt.
2. **Derefter normal dialog.** Gem `AskUserQuestion` til de få ægte skarpe valg og til godkendelsen
   (Trin 6) — ikke ét pr. punkt.
3. Foreslå bredere keywords/negatives hvor det giver mening (`helkropsscanning pris` → `helkropsscanning`).
4. Hold en løbende beslutnings-liste (keyword, match-type, level, kampagne, ad group) → `decisions.json`.
5. Brug for mere viden? `firecrawl-map`/`-scrape` en underside eller en web-søgning — målrettet, ikke
   en blind crawl. Bedre end at gætte eller spørge om noget der står på klientens egen side.

Husk dommereglerne: on-offering lokal geo bliver aldrig en negativ; en negativ kræver et positivt tegn
på irrelevans (off-offering/forkert intent/konkurrent), ikke bare 0 konv; en vinder kræver reelt
udækket + fornuftig signifikans (små tal er støj). Ved tvivl → tag den op, ikke et forkert kald.

## Trin 6 — Bekræft HELE listen eksplicit, og vælg leverings-vej

Inden du tilføjer eller skriver én linje: præsentér hele den endelige liste og få et eksplicit ja —
obligatorisk, fordi næste skridt kan ændre en LIVE konto. Vis BÅDE negatives og positives, alt konkret:
keyword · match-type · level · præcis kampagne (+ ad group) eller delt liste; for keywords: kampagne +
ad group. Hver kandidat — både negatives og nye keywords — skal være web-valideret (Trin 5).

Sig hvad et ja betyder: negatives/keywords tilføjes LIVE (keywords serve straks; ingen paused via MCP);
MCP kan kun campaign/ad_group-niveau (account → fan-out pr. kampagne; delt liste → kun CSV).

Spørg så med ÉT `AskUserQuestion`:
- `Tilføj live i kontoen nu (Anbefalet)` → Trin 7A.
- `Lav Editor-CSV i stedet` → Trin 7B.
- `Excel-overblik` → Trin 7C (kan også laves oveni live/CSV).
- `Ret noget først` → tilbage i samtalen; opdatér og bekræft igen.

Tilføj/skriv først når brugeren har valgt. Aldrig en mutation uden grønt lys på den fulde liste, og
aldrig noget der ikke stod på den.

## Trin 7 — Udfør (læs `references/apply.md`)

Når brugeren har valgt, **læs `references/apply.md`** for den præcise mekanik: byg `decisions.json`, og
følg 7A (live MCP: ID-opslag → grupper → dry-run → commit), 7B (CSV via `write_csv.py`) eller 7C (Excel
via `build_xlsx.py`). Afslut med en kort opsummering + `## Kilder`.

## lib/ (selvstændig)

- `slim.py` — slanker rapporten + `where_predicate()` (server-side-filter) + `aggregate_terms()` (én
  vejet række pr. term). `ngram.py` — systemiske temaer pr. 1/2/3-gram. `digest.py` — komponerer dem
  til den kompakte brief. Ingen vurdering i nogen af dem.
- `write_csv.py` (Trin 7B) + `build_xlsx.py` (Trin 7C) — render de aftalte beslutninger til CSV/Excel
  med hårde guards. Live-tilføjelsen (7A) er direkte MCP-kald, ikke et script. Ingen vurdering rører
  output — al klassifikation hører til i samtalen.
