# Findings-skema (kontrakten mellem sub-agenterne og `build_docx.py`)

Dette er den kanoniske form for findings-objektet. `lib/build_docx.py` **forbruger** dette skema
(dets docstring gengiver samme kontrakt for koden — hold de to i sync hvis kontrakten ændres). Både
verifikations-sub-agenterne (Trin 3) og samlingen (Trin 4) skriver mod denne form.

## Per-modul-objektet (det hver sub-agent returnerer)

Hver sub-agent returnerer præcis denne form (`details`/`evidence`/`pointer` er valgfri og udelades
for korte punkter):

```json
{"key": "C", "title": "Modul C — Annoncetekster (ad copy)",
 "items": [{"n": 13, "punkt": "<ordret fra reference>", "status": "warn",
            "kind": "judgment",
            "finding": "<kort dansk konstatering m. tal>",
            "details": "<valgfri længere prosa: fordeling, per-ad-group, eksempler>",
            "evidence": ["Kampagne 'IC | GSN | Hele DK' › ad group 'Aalborg' › headline 'Bestil taxi til Aaborg' → skal være 'Aalborg'"],
            "pointer": "<valgfri: for fuld dybde kør inb-ads-rsa-hygiene / inb-ads-quality-score (kræver kørselshistorik)>"}]}
```

Et rent lookup-punkt uden dybde-felter ser sådan ud:

```json
{"n": 1, "punkt": "Sitelinks: min. 4 på hver kampagne", "status": "ok", "kind": "lookup", "finding": "..."}
```

## Feltbetydninger

- **`status`** — `ok` / `warn` / `critical` / `no_data`, afgjort per punkt efter doms-reglen i
  `analysearbejdet.md`. På en frisk konto uden historik er svaret `no_data` (ikke et fabrikeret fund).
- **`kind`** (påkrævet — `lookup` eller `judgment`) — kopiér fra reference-filens kolonne, gæt ikke.
  `lookup` = et faktuelt opslag (eksisterer en udvidelse? er display select slået fra? hvilke lister
  findes?). `judgment` = en vurdering (er teksten velskrevet? er broad kontrolleret? er strukturen
  fornuftig?). Det styrer .docx'ens Ekspert-boks: lookup-punkter får ingen (intet at efterse),
  judgment-punkter får én (eksperten bekræfter agentens skøn). Defaulter til `judgment` hvis feltet
  mangler.
- **`finding`** — kort dansk konstatering med det faktiske tal/navn bag (fx "3 af 7 kampagner har
  <4 sitelinks: Brand, Generisk-DK, Lufthavn"), aldrig en påstand uden data.
- **`evidence`** (valgfri) — et array der lokaliserer hvert fund: kampagne › ad group ›
  annonce/asset › den nøjagtige streng — når punktet peger på noget konkret (en stavefejl, en POOR
  annonce, en tom ad group, en forkert indstilling). Det er forskellen på "der er en stavefejl"
  (ubrugeligt) og "kampagne X › ad group Aalborg › headline 'Bestil taxi til Aaborg'"
  (handlingsbart). Skriv `evidence` som hele, færdige strenge — de gives videre ORDRET i samlingen
  (Trin 4). Rendered som en "Hvor:"-blok i .docx'en.
- **`details`** (valgfri) — længere dansk prosa for tunge moduler (især C annoncetekster, G
  keywords): fordelinger, per-ad-group-opdeling, eksempler. Fyld kun hvor det tilføjer værdi;
  koncise punkter forbliver én linje.
- **`pointer`** (valgfri) — hvor en fuld gennemgang sprænger en opstartsrapport (fx per-annonce
  RSA-hygiejne på hundredvis af annoncer), et felt der henviser til det rette dybde-skill
  (`inb-ads-rsa-hygiene` / `inb-ads-search-term-analyse` / `inb-ads-quality-score`), med
  forbeholdet at de kræver kørselshistorik. `pointer` erstatter ALDRIG et reelt fund — giv altid
  top-N det værste først (fx "5 ad groups på POOR: [navne]"), dernæst pointeren.

## Det samlede findings-objekt (Trin 4 bygger dette)

```json
{
  "client": "Dantaxi",
  "customer_id": "4149791707",
  "window": "Struktur-gennemgang (ny konto)" | "LAST_90_DAYS" | "...",
  "generated": "2026-06-10",
  "headline_findings": ["...", "...", "..."],
  "modules": [ /* de ni per-modul-objekter ovenfor, i rækkefølge A-I */ ],
  "sources": ["get_ad_extensions", "run_custom_gaql (campaign_asset)", "..."]
}
```

- **`generated`** sættes af agenten (dagens dato) — scriptet kalder aldrig en ur-funktion.
- **`window`** er analysegrundlaget (Struktur-gennemgang eller datavinduet).
- **`headline_findings`** — 3-5 vigtigste fund, dansk, prioritér `critical` > `warn`. Skarpt og
  konkret (et tal, en konsekvens). Dette er den eneste redaktionelle vurdering der sendes ind:
  overbliks-tallene (OK/kan forbedres/kritisk/mangler data) beregner scriptet selv fra punkternes
  `status`, så båndet aldrig kan modsige rækkerne. Enhver `summary`-nøgle i inputtet ignoreres.
- **`modules`** — de ni objekter i rækkefølge A-I. `evidence`/`details`/`pointer` gives videre
  ORDRET fra sub-agenterne — omskriv eller komprimér dem aldrig i samlingen. `finding`-prosaen må
  strammes let, men `evidence` er adresser og skal stå præcist.
- **`sources`** — de MCP-værktøjer + URLs der faktisk blev kaldt.

`build_docx.py` validerer objektet (fejler højlydt på ugyldig status eller tomme moduler) og
skriver den to-lags Inbound-stylede .docx.
