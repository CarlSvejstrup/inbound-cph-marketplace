---
name: structuring
description: Byg en ny Google Ads-kampagnes kontostruktur fra Phase-1 research — ad groups (få, brede), keyword-selektion + match types (Exact + selected Phrase, ALDRIG Broad), og klient-specifikke negative tilføjelser oven på Inbounds delte MCC-negativliste. Phase-2-gaten i campaign-build, det tunge generative trin med menneske-godkendelse. Skriver ingen eksterne writes og pusher ALDRIG til Google Ads API'et. Brug når brugeren siger "byg kampagne-struktur", "structuring", "ad groups + keywords til [klient]", "lav keyword-strukturen", eller fortsætter en campaign-build-kørsel efter research. Svarer på dansk.
---

# structuring

Phase-2-gaten i **campaign-build**. Tager Phase-1 research (landing-page-analyzer +
competitor-research + campaign-strategy) og producerer kontoarkitekturen: **ad groups**,
**keyword-selektion + match types**, og **klient-specifikke negative tilføjelser**. Plus
**vinkler + keyword-seeds per ad group** — det semantiske indhold Phase-3 rsa-copywriter
forbruger. Dette er det tunge generative trin med menneske-godkendelse: alt downstream
(creative, assembly) afhænger af det denne gate producerer.

Output forbruges af **rsa-copywriter** (Phase 3, læser vinkler + keyword-selektion) og
**assembler** (Phase 4, fylder tab 02/03/04/05 + launch-gates).

## Designprincip

Tre koblede beslutninger i ét skill (blueprint-gruppering): ad groups, keywords, negatives.
De er koblede fordi keyword-temaerne definerer ad group-grænserne, og negatives beskytter
den selektion. Alle verificerede regler, tal og output-formen bor i
`references/structuring-rules.md` — **læs den, den vinder ved konflikt.** Den er kort med
vilje; denne SKILL.md er kun flowet.

## Hård regel — INGEN API-push, ingen eksterne writes

Dette skill (og hele campaign-build) pusher ALDRIG til Google Ads API'et (beslutning
2026-06-03). Det LÆSER fra Google Ads MCP (den delte negativliste) men SKRIVER intet til
kontoen. Det producerer et struktureret objekt mennesket godkender; leverancen er
CSV/workbook til manuel Editor-import. Read-only MCP-kald er fine; ethvert skrive-kald er
forbudt.

## When to use

Trigger-fraser: "byg kampagne-struktur", "structuring", "ad groups + keywords til [klient]",
"lav keyword-strukturen", "strukturér kampagnen", eller automatisk som Phase-2-trin i en
campaign-build-kørsel når Phase-1 research er klar.

## Trin 0 — Kontekst

Læs `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` (write-gate + sprog). Læs
`${CLAUDE_PLUGIN_ROOT}/skills/structuring/references/structuring-rules.md` — de verificerede
regler for ad groups, keywords og negatives + output-formen. Dansk medmindre brugeren
skriver på engelsk.

**Forbrug Phase-1 input hvis kædet:** landing-page-analyzer JSON (product/service, USP'er,
tone, CTAs, trust, sprog), competitor-research (differentiatorer, sea-of-sameness,
positionerings-huller), campaign-strategy (kampagnenavn, mål, match-type-politik, geo).
Mangler de (skillet kørt standalone), saml minimal intake: klientnavn + URL + tema/
kampagnetype, og kør landing-page-analyzer-mønstret inline hvis nødvendigt.

## Trin 1 — Hent den delte negativliste LIVE (kontekst, ikke output)

Kør (read-only) mod Inbound CPH Clients MCC for at få de "allerede-dækkede" negatives, så
generation IKKE genopfinder `gratis`/`job`/`guide` som nye:

```
run_custom_gaql(customer_id="1138360630",
  query="SELECT shared_criterion.keyword.text, shared_criterion.keyword.match_type
         FROM shared_criterion WHERE shared_set.id = 6688642473")
```

Det er listen "Generelle negative søgeord" (~277 medlemmer pr. 2026-06-03 — brug altid det
LIVE antal, ikke dette tal). Fald tilbage til
`references/generelle-negative-eksempel.md` KUN hvis MCC'en ikke kan nås — og sig det i
output. **Genudsend ALDRIG de 277 som CSV-rækker** — de påføres by-reference (Trin 4).

## Trin 2 — Ad groups (få, brede)

Byg ad groups efter §1 i reference-filen: **én ad group = ét tæt tema / én intent / én
landingsside**, INGEN single-keyword-grupper, blød bånd ~5-15 keywords/gruppe. Splittér når
én RSA ikke kan være relevant for alle keywords i gruppen; mergér tema-søskende under
~2.000 impr/md-gulvet. Tag hver gruppe med temperatur (Brand/Product/Generic).

Begrund strukturen på det RIGTIGE niveau (conversion-pooling = kampagne-niveau ~30/30d;
impression-density = ad group-niveau). Brug self-explanation-strengen verbatim fra §1.

## Trin 3 — Keywords + match types

Generér keyword-kandidater per ad group fra landingsside + konkurrent-research + tema
(§2 i reference-filen). **Ingen volumen-grounding findes** (verificeret: ingen Keyword
Planner-flade i MCP'en, Semrush plan-gated). Så:
- Markér eksplicit: keywords er **tema-afledte, IKKE volumen-rangerede** — mennesket
  validerer volumen i Keyword Planner før launch. Sig det i output.
- **Match types: Exact + selected Phrase only, ALDRIG Broad.** Emit en eksplicit
  `Exact`/`Phrase`-værdi på HVER keyword — aldrig blank, aldrig bart ord (begge → Broad ved
  Editor-import, bryder låsen stiltiende). Default Exact; promovér til Phrase kun ved reel
  ordstillings-/kvalifikator-variation værd at fange.

## Trin 4 — Negatives (tilføj, genudsend ikke)

To tiers + monitor (§3 i reference-filen), spejler Ians tab 04 + 05:
1. **Arvet delt liste — påført by-reference** (launch-gate-trin): "Tilknyt delt negativliste
   'Generelle negative søgeord' (id 6688642473) til kampagnen." IKKE CSV-rækker.
2. **Klient-specifikke tilføjelser** (kampagne-niveau): kun det de 277 MANGLER for netop
   denne klient (fx konkurrenters brandnavne, nabo-men-irrelevante service-ord). Emit
   **singular+plural-par + nøgle-synonymer eksplicit**; emit ALDRIG misspelling-varianter
   (Editor auto-blokerer stavefejl + casing siden 2024). For negatives er **broad den
   rigtige default** — normalisér ALDRIG til phrase/exact for at "overholde" no-Broad-låsen
   (den lås gælder kun POSITIVE keywords).
3. **Monitor-first-kandidater:** spekulative negatives der IKKE committes up-front — overvåges
   via search-terms-rapporten først (en negativ er en hård blokering uden expansion-sikkerhed).

## Trin 5 — Emit objektet

Skriv det strukturerede objekt (formen i §5 af reference-filen) til kørslens artefakt-mappe
(fx `.firecrawl/structuring.json` eller orkestratorens sti). Det indeholder: `campaign`,
`ad_groups[]` (name, temperature, landing_page_url, theme, paths, max_cpc,
keywords[{text, match_type}], angles[], keyword_seeds_for_rsa[]), `negatives`
(inherited_shared_list by-reference +
client_specific_additions + monitor_first_candidates), `keyword_volume_disclaimer`, og
`structure_rationale`. `angles` + `keyword_seeds_for_rsa` er det rsa-copywriter forbruger.

## Trin 6 — Output (menneske-godkendelse — dette ER gaten)

Lever en kort, godkendelses-klar opsummering:
- **Ad groups-tabel:** navn | temperatur | #keywords | tema | landingsside. Plus
  struktur-rationalet (self-explanation-strengen).
- **Keywords-tabel per ad group:** keyword | match type. Med volumen-disclaimer øverst.
- **Negatives:** "Delt liste (N medlemmer, hentet live) påføres by-reference" — brug det
  LIVE antal fra Trin 1, ALDRIG et hardcoded tal (listen drifter) + tabel over
  klient-specifikke tilføjelser (term | match type | niveau | hvorfor) + monitor-first-
  kandidater separat.
- **Bed eksplicit om godkendelse** før Phase 3. Dette er det tunge gate-trin; intet
  downstream kører før mennesket har sagt god.

## Risici / noter

- **Keyword-volumen-hullet er reelt** — skjul det ikke. Den ærlige leverance er
  "tema-afledte kandidater, validér volumen manuelt", ikke et falsk volumen-tal.
- **Negativ-listen er live, ikke statisk** — pull hver kørsel; snapshot'et i references er
  kun fallback. Hvis du nogensinde skriver de 277 ind i en fil eller CSV: stop — det er
  signalet på at du er drevet væk fra "add to this".
- **Match-type-fælden** er den mest sandsynlige stille fejl: blank/bart ord = Broad. Verificér
  at hver keyword-række har Exact eller Phrase før du emitterer.
- **Konsolidering ≠ broad match.** Få ad groups giver data-fordelen UDEN at låse broad op.
  Bland dem ikke. (Hvis Carl/Rikke nogensinde vil revurdere: i litteraturen parres de to
  næsten altid — men no-Broad-låsen holder som default.)
- **ads-audit-report-overlap:** kører en audit forud på en eksisterende konto, kan dens
  search-terms-data fodre monitor-first-listen med ægte observeret spild — en berigende
  input, ikke en afhængighed.

## Maintenance

- Alle regler/tal/output-form bor i `references/structuring-rules.md`. Ret kun den.
- `references/generelle-negative-eksempel.md` er KUN et eksempel-snapshot — den live GAQL er
  kanonisk. Opdatér ikke snapshot'et rutinemæssigt; lad det drive og stol på live-pull.
- Match-type-encoding + Editor-kolonner spejler hvad assembler (Phase 4) emitterer — hold
  dem i sync når Phase 4 bygges.
- v1 er Search-only. pMax/Shopping ændrer hele struktur-modellen — branch senere.
