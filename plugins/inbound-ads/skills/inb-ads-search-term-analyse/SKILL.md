---
name: inb-ads-search-term-analyse
description: Analyserer søgetermerne i én live Google Ads-konto ved at filtrere data server-side i GAQL og rulle dem til en kompakt indsigts-brief (spild-temaer, vinder-temaer, intent, match-type-lækage), og fører derefter en samtale om fundene før den, kun efter eksplicit bekræftelse, tilføjer negatives og keywords via MCP eller Editor-CSV. Svarer på dansk.
---

# search-term-analyse

Én konto. Målet er indsigt, ikke en tabel — og derefter en samtale, ikke en aflevering. Grav mønstrene
frem, beslut sammen med brugeren, og tilføj kun de aftalte negatives/keywords efter eksplicit
bekræftelse. Read-only indtil da. Svar på dansk. Sæt `LIB=${CLAUDE_SKILL_DIR}/lib`.

## 0. Hent klientkontekst først

Kør `../../shared/client-context-intake.md` som allerførste trin: master-klientindekset i Drive →
klientens række (Google Ads-ID, Stage, AI Context-link) → AI Context-filen som ground truth. Den fil
dækker også delte-mappe-grupperne (Lime, Retriever/Infomedia, GSGroup, Nemco, Julemærket, PhoneAlone,
DI → vælg markedets række), `.md`-ulæselig→Google Docs-fallback, og no-row/no-file-fallback. Ren
læsning, aldrig gated. Kan intet læses: sig det, fortsæt med det du har (Drive-mappe, Ads MCP), flag
hullet.

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

## 2. Forstå tilbuddet billigt (nice-to-have)

Skriv 3-5 linjers forståelse af tilbuddet til dig selv, så du kan kende "vores tilbud" fra "ikke vores
tilbud" — det er linsen al relevans-dom hviler på. Ad group-navnene (geografi + ydelses-opdeling) bærer
det meste. Vil du have det skarpere, tilføj ét `firecrawl-scrape` af forsiden — UX-polish, ikke krav;
fejler scrape, kør videre på ad group-navnene og sig det. Tilgangen (landingsside + konto-signaler →
`OFFERING_TOKENS`) er fuldt beskrevet i `../../shared/offering-brief.md`.

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

## Output-format (hvordan indsigts-briefen præsenteres)

Trin 5-briefen (og den afsluttende opsummering i Trin 7) følger Inbounds **report house style** (den
er beskrevet fuldt ud her — ingen ekstern fil nødvendig; forfattere kan læse den dybere vejledning i
`inbound-skill-creator`). Led med svaret, gør det skanbart, skjul plumbing (GAQL, `cost_micros`,
view-navne). To formater: spørg én gang "som side eller i chatten?" (eller brug det brugeren allerede
sagde) — "side" bygger en delbar artifact-side i Inbound-husstil (skabelon:
`../../shared/report-template.html`); "i chatten" er struktureret Markdown. Chat er en fin default
her, da fundene alligevel skal diskuteres.

Zonerne, i rækkefølge (udelad dem der er tomme):

1. **BLUF** — status-chip + "Kort sagt" (1-2 sætninger: største spild-tema + største udækkede vinder)
   + meta (konto, vindue, "trak X termer, tærskel Y").
2. **Hvad kræver handling** — de foreslåede negatives og nye keywords som handlinger (verbum først:
   "**Bloker** …", "**Opret** exact-keyword …"), hver med den lille begrundelse. Recommend-only indtil
   Trin 6-godkendelsen, så del gerne "klar til at tilføje" fra "værd at drøfte".
3. **Fund** — top spild-temaer og udækkede vindere, vigtigst først, som en lille tabel
   (`Søgeterm/tema | Klik | Konv | CPA | Anbefaling`). Hvert tema parret med *"Betyder:"* (så-hvad i
   kroner/CPA). Navngiv N-cuttet ("top 13 af 240 termer — sig til for resten"), dump aldrig hele listen.
4. *(Kontekst-zonen udelades typisk her.)*
5. *(Gaten:)* selve godkendelsen (Trin 6) sker altid i chatten, aldrig i en artifact.
6. **Datagrundlag** — footer: vindue, tærskel, "trak X termer", hvilke MCP-kald (kort, ikke en logliste).

Status-pills: 🟢 ren/ok · 🟠 hold øje · 🔴 tydeligt spild · 🔵 info · ⚪ neutral. Æ Ø Å altid.

## lib/

- **`digest.py`** — orkestratoren: tager det rå pull og printer den kompakte indsigts-brief (Trin 4).
- **`slim.py`** — skærer pullet ned til de få felter en dom kræver; leverer `where_predicate()` (bygger
  GAQL-filtret) og `aggregate_terms()` (samme term på tværs af ad groups). Fodrer `digest.py`.
- **`ngram.py`** — n-gram-analyse (temaer per 1/2/3-gram) af søgeterm-listen. Fodrer `digest.py`.
- **`write_csv.py`** — gør den godkendte `decisions.json` til Editor-import-CSV'er med hårde guards (7B).
- **`build_xlsx.py`** — opt-in, farvekodet Excel-overblik af gennemgangen (7C).

Ingen af scripterne vurderer noget — al klassifikation sker i samtalen.
