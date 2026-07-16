---
name: inb-ads-shopping-performance
description: Analyserer produkt-performance i én live Google Ads Shopping/Performance Max-konto ved at trække data server-side i GAQL og rulle det til en kompakt indsigts-brief (spild uden retur, impression share-huller, vindere der er budget-/rank-begrænsede, custom-label- og product_type-mønstre), og fører derefter en samtale om fundene før den, kun efter eksplicit bekræftelse, laver bud- eller eksklusions-ændringer via ads-writer-agenten. Ser KUN Google Ads-siden (performance) — de faktiske feed-afvisninger og feed-indholdet ligger i Merchant Center og er IKKE dækket her. Svarer på dansk.
---

# shopping-performance

Én konto. Målet er indsigt om **hvilke produkter der tjener penge og hvilke der brænder budget** — og
derefter en samtale, ikke en aflevering. Grav mønstrene frem, beslut sammen med brugeren, og lav kun de
aftalte bud-/eksklusions-ændringer efter eksplicit bekræftelse. Read-only indtil da. Svar på dansk. Sæt
`LIB=${CLAUDE_SKILL_DIR}/lib`.

## Hvad dette skill KAN og IKKE kan se

Dette er den halvdel af "feed-arbejde" der ligger i **Google Ads API** — produkt-performance. Det ser:
forbrug, klik, konverteringer, værdi, ROAS, impression share, gross profit og custom labels /
product_type pr. produkt.

Det ser **IKKE**: hvorfor et produkt er afvist i Merchant Center, item-level issues, per-destination
status, eller selve feed-indholdet (titler, beskrivelser, billeder). De data findes kun i **Merchant
API**, som pluginnet ikke er koblet på endnu. Ser du et produkt med 0 impressions, kan dette skill sige
"det server ikke" — men ikke hvorfor. Peg i så fald brugeren mod en Merchant Center-gennemgang (det
kommende `inb-ads-feed-health`, blokeret på Merchant API-integrationen). Fuld kontekst:
`work/inbound-cph/research/2026-07-16-shopping-feed-merchant-center-capability.md` i vaulten.

## 0. Hent klientkontekst først

Kør `../../shared/client-context-intake.md` som allerførste trin: master-klientindekset i Drive →
klientens række (Google Ads-ID, Stage, AI Context-link) → AI Context-filen som ground truth. Den dækker
også delte-mappe-grupperne (Lime, Retriever/Infomedia, GSGroup, Nemco, Julemærket, PhoneAlone, DI → vælg
markedets række), `.md`-ulæselig→Google Docs-fallback, og no-row/no-file-fallback. Ren læsning, aldrig
gated. Kan intet læses: sig det, fortsæt med det du har (Drive-mappe, Ads MCP), flag hullet.

Bemærk fra AI Context, hvis det står der: **hvilken konvertering der tæller** (leads vs. køb),
**tROAS-mål**, og **paused-kampagne-intent** — det er linsen "spild uden retur" hviler på.

## 1. Intake (ét `AskUserQuestion`-kald)

Udled så meget som muligt selv; saml resten i ét kald:

1. **Klient + `customer_id`** — normalt kendt fra trin 0; bekræft bare.
2. **Analysevindue** — default `Sidste 30 dage`, ellers `Andet (BETWEEN)`. GAQL på Shopping tager KUN
   Googles literaler (`LAST_30_DAYS`, `LAST_14_DAYS`, `LAST_7_DAYS`, `THIS_MONTH`, `LAST_MONTH`) —
   **`LAST_90_DAYS` afvises**. Vil brugeren have >30 dage, brug eksplicit
   `BETWEEN 'ÅÅÅÅ-MM-DD' AND 'ÅÅÅÅ-MM-DD'`.
3. **Scope** — hele kontoen eller én kampagne (→ `campaign_id`). PMax og Shopping kan blandes; sig hvad
   du inkluderer.
4. **Forbrugs-tærskel** (styrer payload-størrelsen): `Forbrug ≥ 50 kr (anbefalet)`, `Forbrug ≥ andet`,
   eller `Alt` (advar: tungt på en stor katalog-konto). Rapportér altid "trak X produkter (tærskel: …)".
5. **Hvilken konvertering tæller** — alle, eller kun primære (køb)? Ved tvivl: antag alle, men skriv
   forbeholdet. På en webshop er det næsten altid køb + værdi.

## 2. Forstå kontoen billigt (nice-to-have)

Skriv 2-3 linjers forståelse til dig selv: er det Shopping, PMax eller begge? Er der et tROAS-mål? Hvad
er en normal ordreværdi? Kampagnenavnene bærer det meste (`IC | Shopping | Generisk`, `LP-PMax-...`).
Det er linsen der afgør om en ROAS på 3 er god eller elendig for netop denne konto.

## 3. Hent data server-side (fire faste pulls)

Alle via `run_custom_gaql`. Skriv hvert tool-svar **ordret** til en `.json`-fil under `~/Downloads/`
(hele svaret, præcis som returneret) — skriv aldrig et Python-script med håndtastede rækker; data skal
være data. De præcise queries, felt-typer og GAQL-fælder står i `references/gaql-contract.md` — læs den
først. Kort:

- **A. Produkt-performance** (`shopping_performance_view`, produkt-grain, INGEN impression share) →
  `_sp_products.json`. IS må IKKE co-selectes med `segments.product_title` (kaster
  `PROHIBITED_SEGMENT_WITH_METRIC`).
- **B. Impression share pr. kampagne** (`FROM campaign`, med budget-lost + rank-lost) → `_sp_is.json`.
  Dette er den eneste grain der giver budget-/rank-nedbrydningen.
- **C. Custom labels + product_type** (produkt-grain, tages med i A via de ekstra segments) — ingen
  ekstra pull, men bekræft hvilke `product_custom_attribute0..4` klienten faktisk bruger.
- **D. (Kun hvis PMax)** asset group-produktopdeling (`asset_group_product_group_view`) → `_sp_pmax.json`,
  hvis PMax-produkter ikke dukker op i A (kendt: PMax-netværksdata lander først i
  `shopping_performance_view` fra 15. jun 2026 — verificér live).

Rammer du et `LIMIT`, sig det ("trak de 500 dyreste produkter").

## 4. Byg indsigts-briefen

```bash
python3 $LIB/digest.py --products ~/Downloads/_sp_products.json --is ~/Downloads/_sp_is.json \
  --out ~/Downloads/_sp_digest.json --top 20
```
Læs den printede brief, ikke de rå rækker. Den slanker (dropper skrald, aggregerer samme produkt), og
ruller op til: overblik (forbrug, konv, værdi, blended ROAS, andel forbrug uden retur), top-forbrug,
**spild uden retur** (forbrug > 0, konv = 0 — sorteret efter forbrug), **vindere** (høj ROAS, værd at
skubbe), **impression share-huller** (kampagner der taber IS til budget vs. rank — forskellig
handling), og **struktur-/label-mønstre** (er bestsellere og lav-margin-varer overhovedet delt op?).
`--top` er kun rækker pr. tabel — hele datasættet analyseres. Læg egne observationer oveni.

Scriptet **vurderer intet** — hver gruppe er en samtale-starter med tallet bag. Den kardinale regel som
i søgeterm-skillet: **0 konverteringer er ikke bevis på spild** på en konto hvor folk også ringer eller
køber offline. "Spild uden retur" er noget man **taler om**, aldrig en auto-eksklusion.

## 5. Læg ét samlet udkast på bordet

Skriv i prosa, med tallet bag hvert punkt:

- **Spild-kandidater:** produkter/product-grupper der brænder budget uden retur. En eksklusion eller et
  bud-ned kræver et positivt tegn (fx sæsonvare ude af sæson, product-type der aldrig konverterer, en
  vare der er udgået) — ikke bare 0 konverteringer. Er produktet en kernevare, er 0 konv i stedet et
  **feed- eller landingsside-signal** → flag det til en Merchant Center-gennemgang, foreslå ikke en
  eksklusion.
- **Vinder-kandidater:** høj-ROAS produkter/grupper der er impression-share-begrænsede. Er tabet mest
  **budget-lost** → foreslå budget/bud op. Er det mest **rank-lost** → foreslå bud op eller bedre
  feed-relevans (titel), ikke budget.
- **Struktur-observationer:** ikke-delt katalog (alt i én asset group / product-gruppe), bestsellere der
  ikke er skilt ud, custom labels der ikke bruges. Anbefal-kun (struktur-ændringer laver dette skill
  ikke selv).
- Plus 2-4 interessante fund værd at tale om.

Herefter almindelig dialog — gem `AskUserQuestion` til de få reelt skarpe valg og til godkendelsen i
trin 6. Hold en løbende beslutningsliste (produkt/gruppe, handling, kampagne, ny bud/tROAS).

## 6. Bekræft hele listen, vælg leverings-vej

Før noget skrives: vis hele den endelige liste (hver med produkt/gruppe · handling · kampagne · konkret
værdi) og få et eksplicit ja — dette kan ændre en LIVE konto. Sig hvad et ja betyder.

Spørg med ét `AskUserQuestion`:
- `Lav ændringerne live i kontoen nu` → gå til trin 7, spor A (via ads-writer-agenten).
- `Excel-overblik` → spor B (kan laves oveni A).
- `Kun brief, ingen ændringer (Anbefalet ved tvivl)` → stop efter en kort opsummering.
- `Ret noget først` → tilbage i samtalen, opdatér, bekræft igen.

## 7. Udfør

Læs `references/apply.md` for mekanikken. **Alle kontoskrivninger går gennem ads-writer-agenten** — dette
skill foreslår, agenten udfører, og kun det der stod på den godkendte liste, ét bekræftet punkt ad
gangen. Bud- og eksklusions-ændringer er tilladt (HITL-per-handling); **budget-ændringer er strammere
gated og blokeret indtil budget-guardrail'en er på plads** — foreslå dem, men skriv dem ikke. Spor B
(Excel) laver `$LIB/build_xlsx.py` et farvekodet overblik. Afslut med en kort opsummering og `## Kilder`.

## lib/

- **`digest.py`** — orkestratoren: tager de rå pulls og printer den kompakte indsigts-brief (Trin 4).
- **`slim.py`** — skærer pullet ned til de få felter en dom kræver; håndterer de blandede felt-typer
  (cost/impressions/clicks er strings, conv/værdi/IS er floats) og de **udeladte tomme segment-nøgler**.
  Aggregerer samme produkt-id på tværs af rækker. Fodrer `digest.py`.
- **`build_xlsx.py`** — opt-in, farvekodet Excel-overblik (produkt-tabel + spild-uden-retur + IS-tab).

Ingen af scripterne vurderer noget — al klassifikation sker i samtalen.
