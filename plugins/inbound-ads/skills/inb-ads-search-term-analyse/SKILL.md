---
name: inb-ads-search-term-analyse
description: Skarp, samtale-drevet søgeterm-analyse af én LIVE Google Ads-konto, der leverer INTERESSANTE indsigter — ikke bare den flade liste Google Ads giver. Filtrerer data server-side i GAQL så selv 1000+ termer aldrig læsses rå ind i kontekst, kører et let script (digest.py) der ruller rækkerne til en kompakt indsigts-brief (systemiske spild-temaer via n-gram, vinder-temaer, intent-linser, match-type-lækage, struktur-smell, udækkede vindere), og FØRER så en samtale om fundene — I beslutter SAMMEN hvad der skal blokeres og promoveres. Efter en EKSPLICIT bekræftelse af hele listen tilføjer den negatives og keywords direkte i kontoen via MCP (dry-run så commit), eller laver Editor-CSV som fallback. Read-only indtil du siger ja. VIGTIGT — 0 konverteringer er IKKE bevis for spild når folk ringer. Brug når brugeren siger "search term", "søgeterm-analyse", "analysér søgetermerne", "gå søgetermerne igennem", "find negatives og keywords", eller vil tale sig frem til beslutningerne og tilføje dem. Svarer på dansk.
---

# search-term-analyse

Én konto. Målet er indsigt, ikke en tabel — og derefter en samtale, ikke en aflevering. Grav mønstrene
frem, beslut sammen med brugeren, og tilføj kun de aftalte negatives/keywords efter eksplicit
bekræftelse. Read-only indtil da. Svar på dansk. Sæt `LIB=${CLAUDE_SKILL_DIR}/lib`.

## 0. Hent klientkontekst først

Identificér klienten (uklart → spørg). Åbn master-klientindekset i Drive — Google Doc'en
`Inbound CPH — Google Ads klient-index (AI Context)` (id `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`,
i "A - Kunder") — og find klientens række for Google Ads-ID og link til AI Context. Åbn AI Context
(`read_file_content`): ID'er, kontakter, mål/KPI'er, navngivningskonvention, budstrategi-norm. Delte
mapper (Lime, Retriever/Infomedia, GSGroup, Nemco, Julemærket, PhoneAlone, DI) → vælg rækken for det
specifikke marked.

Hvis den linkede `.md`-fil ikke kan læses ("ineligible to be used in generative AI contexts"), søg i
klientens AI Context-mappe efter Google Doc-versionen (fx `<Klient> - Projektoverblik`) — Google Docs er
læsbare hvor rå `.md`-uploads ikke er. Kan intet læses: sig det og fortsæt med det du har (Drive-mappe,
Ads MCP), men flag hullet.

## 1. Intake (ét `AskUserQuestion`-kald)

Udled så meget som muligt selv; saml resten i ét kald:

1. **Klient + `customer_id`** — normalt kendt fra trin 0; bekræft bare.
2. **Analysevindue** — default `Sidste 90 dage`, ellers `Sidste 30 dage` / `Andet`. ≤30 dage bruger
   `get_search_terms_report` (kun Googles literaler: `LAST_30_DAYS` osv. — `BETWEEN` afvises); >30 dage
   eller custom bruger `run_custom_gaql`.
3. **Scope** — hele kontoen eller én kampagne (→ `campaign_id`).
4. **Filter-tærskel** (styrer payload-størrelsen): `Forbrug ≥ 50 kr (anbefalet)`, `Forbrug ≥ andet`,
   `Impressions ≥ N`, eller `Alt` (advar: tungt på en stor konto). Byg WHERE med
   `slim.where_predicate(dim, value)`. Rapportér altid "trak X termer (tærskel: …)".
5. **Hvilken konvertering tæller** — alle, eller kun primære (leads/opkald)? Ved tvivl: antag alle, men
   skriv forbeholdet.

## 2. Forstå tilbuddet billigt

Ét `firecrawl-scrape` af forsiden + ad group-navnene (de staver geografi + ydelses-opdeling). Skriv 3-5
linjers forståelse til dig selv, så du kan kende "vores tilbud" fra "ikke vores tilbud". Fejler scrape:
brug ad group-navnene og sig det.

## 3. Hent data server-side filtreret

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

Skriv tool-svaret ordret til en `.json`-fil (fx `~/Downloads/_st_raw.json`) — hele `{"results": [...]}`,
præcis som returneret. Skriv aldrig et Python-script med håndtastede rækker; data skal være data.

## 4. Byg indsigts-briefen

```bash
python3 $LIB/digest.py --in ~/Downloads/_st_raw.json --out ~/Downloads/_st_digest.json --top 20
```
Læs den printede brief, ikke de rå rækker. Den slanker (dropper skrald, aggregerer samme term på tværs
af ad groups), kører n-gram, og ruller op til: overblik (forbrug, konv, blended CPA, 0-konv-andel),
top-forbrug, systemiske spild-temaer, vinder-temaer (udækkede), intent-linser, match-type-lækage,
struktur-smell, udækkede vindere. `--top` er kun rækker pr. tabel — hele datasættet analyseres. Læg egne
observationer oveni (sært cost/konv, stavevariant, geo udenfor dækning, brand I ikke ejer).

## 5. Web-validér hver kandidat, så ét udkast

For hver kandidat — negativ eller nyt keyword — tjek tre ting før den kommer med i udkastet: aktive
keywords (`keyword_view`), AI Context, og en websøgning på `"<brand> <term>"` der leder efter en
landingsside eller et tilbud. Gør dette for alle kandidater, ikke kun de tvivlsomme — det er nemt at
gætte forkert på ydelses-termer (`mommy makeover`, `maveplastik`).

- **Negativ:** findes der et aktivt keyword, et tilbud eller en landingsside, er det ikke en negativ —
  det er kernetrafik eller et dæknings-hul. En negativ kræver et positivt tegn på irrelevans
  (off-offering, forkert intent, konkurrent), aldrig bare 0 konverteringer.
- **Nyt keyword:** kun med en relevant landingsside at sende trafikken til. Findes den ikke, flag i
  stedet at siden mangler, i stedet for at tilføje keywordet.

Læg så ét samlet udkast på bordet i prosa: de foreslåede negatives og nye keywords (keyword, match-type,
hvor) plus 2-4 interessante fund værd at tale om, med tallet bag hvert punkt. Foreslå bredere varianter
hvor det giver mening (`helkropsscanning pris` → `helkropsscanning`). Herefter almindelig dialog — gem
`AskUserQuestion` til de få reelt skarpe valg og til godkendelsen i trin 6, ikke ét spørgsmål per punkt.
Hold en løbende beslutningsliste (keyword, match-type, level, kampagne, ad group).

## 6. Bekræft hele listen, vælg leverings-vej

Før noget skrives: vis hele den endelige liste (negatives og nye keywords, hver med keyword · match-type
· level · kampagne/ad group) og få et eksplicit ja — dette kan ændre en LIVE konto. Sig hvad et ja
betyder: keywords serve straks (ingen paused-tilstand via MCP); MCP virker kun på campaign/ad_group-
niveau (account-scope fanner ud pr. kampagne; delt liste kræver CSV).

Spørg med ét `AskUserQuestion`:
- `Tilføj live i kontoen nu (Anbefalet)` → gå til trin 7, spor A.
- `Lav Editor-CSV i stedet` → spor B.
- `Excel-overblik` → spor C (kan laves oveni A/B).
- `Ret noget først` → tilbage i samtalen, opdatér, bekræft igen.

## 7. Udfør

Læs `references/apply.md` for mekanikken bag spor A (live MCP), B (CSV) og C (Excel), og for
`decisions.json`-formatet. Skriv kun det der stod på den godkendte liste. Afslut med en kort
opsummering og `## Kilder`.

## lib/

`slim.py` (slanker rapporten, `where_predicate()`, `aggregate_terms()`) og `ngram.py` (temaer per
1/2/3-gram) fodrer `digest.py`. `write_csv.py` og `build_xlsx.py` gør beslutningerne til CSV/Excel med
hårde guards. Ingen af scripterne vurderer noget — al klassifikation sker i samtalen.
