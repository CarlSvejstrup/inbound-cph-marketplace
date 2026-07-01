# Phase 2 — structuring (kontostruktur-gaten)

Phase-2-gaten. Tager Phase-1 research (`01-landing-page` + `02-competitor` + `03-campaign-strategy`) og
producerer kontoarkitekturen: **ad groups**, **keyword-selektion + match types**, og
**klient-specifikke negative tilføjelser**. Plus **vinkler + keyword-seeds per ad group** — det
semantiske indhold `05-rsa-copy` forbruger. Det tunge generative trin: alt downstream (creative,
assembly) afhænger af det denne gate producerer. Output forbruges af `05-rsa-copy` (vinkler +
keyword-selektion) og `07-assembler` (fylder tab 02/03/04/05 + launch-gates).

Pipeline-mode-først; `structuring`-shell-skillet wrapper solo-mode. **Dette er gaten hvor orkestratoren
beder mennesket om godkendelse før Phase 3** (se `pipeline-flow.md`).

## Designprincip

Tre koblede beslutninger i ét trin: ad groups, keywords, negatives. Koblede fordi keyword-temaerne
definerer ad group-grænserne, og negatives beskytter den selektion. Alle verificerede regler, tal og
output-formen bor i `${CLAUDE_SKILL_DIR}/references/structuring-rules.md` — læs den, den vinder ved
konflikt. Den er kort med vilje; dette er kun flowet.

## Hård regel — INGEN API-push, ingen eksterne writes

Pusher ALDRIG til Google Ads API'et. LÆSER fra Google Ads MCP (den delte negativliste) men SKRIVER intet
til kontoen. Read-only MCP-kald er fine; ethvert skrive-kald er forbudt.

## Trin 0 — Kontekst

Læs `references/structuring-rules.md` — de verificerede regler for ad groups, keywords og negatives +
output-formen. Dansk medmindre brugeren skriver engelsk.

**Forbrug Phase-1 input:** læs `landing-page-analysis.json` (product/service, USP'er, tone, CTAs, trust,
sprog), `competitor-research.json` (differentiatorer, sea-of-sameness, positionerings-huller),
`campaign-strategy.json` (kampagnenavn, mål, match-type-politik, geo) fra artefakt-mappen. Mangler de
(solo-mode standalone), saml minimal intake: klientnavn + URL + tema/kampagnetype, og kør
`01-landing-page`-mønstret inline om nødvendigt.

## Trin 1 — Hent den delte negativliste LIVE (kontekst, ikke output)

Kør (read-only) mod Inbound CPH Clients MCC for de "allerede-dækkede" negatives, så generation IKKE
genopfinder `gratis`/`job`/`guide` som nye:

```
run_custom_gaql(customer_id="1138360630",
  query="SELECT shared_criterion.keyword.text, shared_criterion.keyword.match_type
         FROM shared_criterion WHERE shared_set.id = 6688642473")
```

Det er "Generelle negative søgeord" (~277 medlemmer pr. 2026-06-03 — brug altid det LIVE antal). Fald
tilbage til `references/generelle-negative-eksempel.md` KUN hvis MCC'en ikke kan nås — og sig det i
output. **Genudsend ALDRIG de 277 som CSV-rækker** — de påføres by-reference (Trin 4).

## Trin 2 — Ad groups (få, brede)

Byg ad groups efter §1 i reference-filen: **én ad group = ét tæt tema / én intent / én landingsside**,
INGEN single-keyword-grupper, blød bånd ~5-15 keywords/gruppe. Splittér når én RSA ikke kan være relevant
for alle keywords i gruppen; mergér tema-søskende under ~2.000 impr/md-gulvet. Tag hver gruppe med
temperatur (Brand/Product/Generic). Begrund strukturen på det RIGTIGE niveau (conversion-pooling =
kampagne-niveau ~30/30d; impression-density = ad group-niveau). Brug self-explanation-strengen verbatim
fra §1.

## Trin 3 — Keywords + match types

Generér keyword-kandidater per ad group fra landingsside + konkurrent-research + tema (§2). **Ingen
volumen-grounding findes** (verificeret: ingen Keyword Planner-flade i MCP'en, Semrush cut). Så:
- Markér eksplicit: keywords er **tema-afledte, IKKE volumen-rangerede** — mennesket validerer volumen i
  Keyword Planner før launch. Sig det i output.
- **Match types: Exact + selected Phrase only, ALDRIG Broad.** Emit en eksplicit `Exact`/`Phrase`-værdi på
  HVER keyword — aldrig blank, aldrig bart ord (begge → Broad ved Editor-import, bryder låsen stiltiende).
  Default Exact; promovér til Phrase kun ved reel ordstillings-/kvalifikator-variation værd at fange.

## Trin 4 — Negatives (tilføj, genudsend ikke)

To tiers + monitor (§3), spejler Ians tab 04 + 05:
1. **Arvet delt liste — påført by-reference** (launch-gate-trin): "Tilknyt delt negativliste 'Generelle
   negative søgeord' (id 6688642473) til kampagnen." IKKE CSV-rækker.
2. **Klient-specifikke tilføjelser** (kampagne-niveau): kun det de 277 MANGLER for netop denne klient (fx
   konkurrenters brandnavne, nabo-men-irrelevante service-ord). Emit **singular+plural-par + nøgle-
   synonymer eksplicit**; emit ALDRIG misspelling-varianter (Editor auto-blokerer stavefejl + casing).
   For negatives er **broad den rigtige default** — normalisér ALDRIG til phrase/exact (no-Broad-låsen
   gælder kun POSITIVE keywords).
3. **Monitor-first-kandidater:** spekulative negatives der IKKE committes up-front — overvåges via
   search-terms-rapporten først.

## Trin 5 — Emit objektet

Skriv `structuring.json` (formen i §5 af reference-filen) til artefakt-mappen. Indeholder: `campaign`,
`ad_groups[]` (name, temperature, landing_page_url, theme, paths, max_cpc, keywords[{text, match_type}],
angles[], keyword_seeds_for_rsa[]), `negatives` (inherited_shared_list by-reference +
client_specific_additions + monitor_first_candidates), `keyword_volume_disclaimer`, og
`structure_rationale`. `angles` + `keyword_seeds_for_rsa` er det `05-rsa-copy` forbruger.

## Trin 6 — Godkendelse (dette ER gaten)

I pipeline-mode returnerer subagenten en kort, godkendelses-klar opsummering til orkestratoren, som
præsenterer den for mennesket og **beder eksplicit om godkendelse før Phase 3**:
- **Ad groups-tabel:** navn | temperatur | #keywords | tema | landingsside + struktur-rationalet.
- **Keywords-tabel per ad group:** keyword | match type, med volumen-disclaimer øverst.
- **Negatives:** "Delt liste (N medlemmer, hentet live) påføres by-reference" — det LIVE antal fra Trin 1,
  ALDRIG et hardcoded tal + tabel over klient-specifikke tilføjelser (term | match type | niveau | hvorfor)
  + monitor-first-kandidater separat.

Intet downstream kører før mennesket har sagt god.

## Risici / noter

- **Keyword-volumen-hullet er reelt** — skjul det ikke. Den ærlige leverance er "tema-afledte kandidater,
  validér volumen manuelt".
- **Negativ-listen er live** — pull hver kørsel; snapshot'et i references er kun fallback. Skriver du
  nogensinde de 277 ind i en fil/CSV: stop — du er drevet væk fra "add to this".
- **Match-type-fælden** er den mest sandsynlige stille fejl: blank/bart ord = Broad. Verificér at hver
  keyword-række har Exact eller Phrase før emit.
- **Konsolidering ≠ broad match.** Få ad groups giver data-fordelen UDEN at låse broad op.
- v1 er Search-only. pMax/Shopping ændrer hele struktur-modellen — branch senere.

## Maintenance

Alle regler/tal/output-form bor i `references/structuring-rules.md`. `generelle-negative-eksempel.md` er
KUN et eksempel-snapshot — den live GAQL er kanonisk. Match-type-encoding + Editor-kolonner spejler hvad
`07-assembler` emitterer — hold dem i sync.
