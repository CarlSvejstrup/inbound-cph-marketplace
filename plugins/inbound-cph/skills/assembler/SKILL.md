---
name: assembler
description: Phase-4-barrieren i campaign-build der fletter de fire upstream-outputs (campaign-strategy, structuring, rsa-manifest, assets) til Ians 10-fane review-workbook + per-entitet Google Ads Editor-CSV'er, kører QA/validering, og stopper ved import-artefakter. Pusher ALDRIG til Google Ads API'et — mennesket importerer CSV'erne i Editor efter godkendelse. Den arvede 277-term delte negativliste påføres by-reference, aldrig som CSV-rækker. Brug når brugeren siger "saml kampagnen", "assembler", "byg workbook + CSV", "flet alt sammen", eller afslutter en campaign-build-kørsel. Svarer på dansk.
---

# assembler

Phase-4-barrieren i **campaign-build**. Fletter de fire upstream-outputs til Ians 10-fane
review-workbook + per-entitet Editor-CSV'er, kører QA/validering, og leverer import-artefakter
til mennesket. Det er en **ren transform** (4 JSON-shapes → workbook + CSV) — ingen eksterne
reads, ingen writes til nogen konto.

Hele transform-logikken bor i `assemble.py`; alle fane-/CSV-kontrakter + de hårde regler bor i
`references/assembler-contract.md` — **læs den, den vinder ved konflikt.**

## Hård regel — INGEN API-push

Assembleren kalder ALDRIG Google Ads API'et (beslutning 2026-06-03). Den producerer en workbook
(menneske-review) + CSV'er (Editor-import efter godkendelse). Det bryder ellers tre låste ting:
den verificerede CSV-import-sti, human-in-the-loop, og paused-until-QA-modellen. `assemble.py`
laver kun lokale fil-writes.

## Designprincip — fletter, opfinder ikke

De fire inputs er allerede produceret og godkendt af de tidligere faser. Assembleren
RECONCILER dem og renderer — den genererer intet nyt indhold. Tre ting den håndhæver (alle i
reference-filen, verificeret mod Ians skeleton + Editor-CSV-research):

1. **Negatives flades ALDRIG.** structuring's tre negative-tiers går tre forskellige steder:
   den arvede 277-term delte liste (`inherited_shared_list`) → tab 08 launch-gate-linje +
   reference-linje i tab 04, ALDRIG en CSV-række; `client_specific_additions` → tab 04 + den
   committede negatives-CSV; `monitor_first_candidates` → KUN tab 05. Hvis de 277 nogensinde
   havner i en CSV, er Phase-2-beslutningen ("add to this") regreset.
2. **CSV = kun Editor-skema-kolonner.** Al review-metadata (`grounded_in`, `url_source`, `why`,
   `vinkel`/`hypotese`, LEN, `Pass`) bliver i workbooken; CSV'erne bærer kun verificerede
   Editor-headers. Samme rene grænse som RSA-arket.
3. **Limits er importeret, ikke retypet.** 30/90/15 + LEN+rød-CF kommer fra
   `responsive-search-ads/sheet_layout.py` FIELDS. Én kilde til sandhed.

## To hårde emit-time guards (defense-in-depth)

`assemble.py` fejler LØST før den skriver noget:
- **Guard 1 — ingen blank/Broad positiv keyword.** Hver keyword-række SKAL have eksplicit
  `Exact`/`Phrase`. Blank/manglende/Broad → assembleren nægter at emittere og rapporterer
  rækkerne (silent-Broad-fælden fanget ved grænsen).
- **Guard 2 — tab 09 genberegnes uafhængigt.** Stol IKKE på fill-sheets tidligere gate;
  genberegn LEN + Pass mod de importerede limits, så en menneske-redigering mellem Phase 3 og
  assembly der overskrider en grænse stadig fanges. Over-længde → exit 3 + rød markering.
- Begge køres FØR nogen fil skrives; mismatch i kampagnenavn på tværs af de fire shapes stopper
  også (paste mellem faser kan desynce dem).

## When to use

Trigger-fraser: "saml kampagnen", "assembler", "byg workbook + CSV", "flet alt sammen",
"campaign-build assembly", eller automatisk som Phase-4-barriere når Phases 1-3 er godkendt.

## Trin 0 — Kontekst

Læs `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` (write-gate + sprog). Læs
`${CLAUDE_PLUGIN_ROOT}/skills/assembler/references/assembler-contract.md` — de fire shapes,
fane-/CSV-kontrakter, negatives-non-flatten-reglen, guards og smoke-test-invarianter. Dansk
medmindre brugeren skriver engelsk.

## Trin 1 — Saml de fire inputs

Find kørslens fire artefakter (artefakt-mappe eller manuelt indsat):
`campaign-strategy.json`, `structuring.json`, rsa-manifest (`rsa_artifacts`), `assets.json`.
Join-nøgle = `campaign` (skal matche på tværs af alle fire). Ad groups joines på `name` mellem
structuring + rsa-manifest. Mangler en: sig hvilken og stop — assembleren kræver alle fire.

## Trin 2 — Kør assembleren

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/assembler/assemble.py \
  --strategy campaign-strategy.json \
  --structuring structuring.json \
  --rsa rsa-manifest.json \
  --assets assets.json \
  --workbook "Campaign - <klient> - <YYYY-MM-DD>.xlsx" \
  --csvdir "editor-csvs/" \
  --date <YYYY-MM-DD>
```

`--date` gives ind (scriptet kan ikke kalde `now()`). Output: 10-fane workbook + 6 CSV'er
(campaigns, adgroups, keywords, negatives, ads, assets) + en JSON-opsummering på stdout.
- **Exit 0:** alt validt.
- **Exit 1:** en guard stoppede (kampagnenavn-mismatch eller blank/Broad keyword) — INTET
  skrevet. Ret upstream og kør igen.
- **Exit 3:** workbook + CSV blev skrevet, MEN tab 09 har over-længde-felter (rød). Ret
  teksten upstream før import — overstyr ikke.

## Trin 3 — Verificér output (kort)

Bekræft hurtigt: 10 faner; de 277 / shared-list-id IKKE i nogen CSV; monitor-kandidater kun i
tab 05; keywords-CSV kun Exact/Phrase; tab 09 Pass beregnet. (Disse er smoke-test-invarianterne
— scriptet håndhæver dem, men spot-tjek ved leverance.)

## Trin 4 — Gem (write — gated)

Workbook + CSV-mappe er eksterne writes. Bed om eksplicit bekræftelse én gang før du gemmer/
uploader. Workbook → Drive via connector (`create_file`, Office-mode `.xlsx`); CSV'erne kan
zippes eller lægges i klientmappen. Default klientmappe under `${user_config.inbound_root_folder_id}`
hvis den kan resolves, ellers Drive-rod med en note.

## Trin 5 — Output

Lever:
1. Sti til workbooken + CSV-mappen (+ Drive-link hvis uploadet).
2. **Launch-gate-opsummering fra tab 08** — fremhæv Must-pass-gates: tracking verificeret,
   Presence-only geo, Search Partners/Display off, **den delte negativliste tilknyttet
   by-reference (id 6688642473)**, klient-negatives anvendt.
3. **Validerings-status fra tab 09** — antal over-længde-felter (0 = grønt); hvis >0, list dem
   og sig "ret før import".
4. **Næste skridt (manuelt, human-in-the-loop):** mennesket importerer CSV'erne i Editor
   (Account → Import → From file), tilknytter den delte negativliste, kører launch-QA, og
   enabler først når alle Must-pass-gates er grønne. Assembleren pusher INTET.
5. **Carried-forward-flags** (uændret): snippet-header-kolonnen UNVERIFIED (Editor-round-trip);
   UTM ikke emitteret endnu (dækket som tab-08-gate); ingen live-Cowork-ende-til-ende-kørsel
   endnu; rsa-copywriter intake-injection-antagelse uafprøvet. Carl har parkeret dem.

## Risici / noter

- **Negatives-non-flatten er den vigtigste regel.** Hvis du ser de 277 i en CSV: stop —
  Phase-2-beslutningen er brudt. De påføres KUN by-reference.
- **Guards fejler LØST før write** — en exit 1 betyder INGEN filer blev skrevet; det er
  designet. Ret upstream, ikke i assembleren.
- **Limits importeres fra sheet_layout.py** — ret aldrig 30/90/15 her; ret RSA-layoutet hvis
  Google ændrer grænserne.
- **Snippet-header-kolonnen** emitteres i en eksplicit UNVERIFIED-mærket kolonne — verificér via
  Editor-round-trip før import; hardcode den ikke som sikker.
- **Pure transform:** ingen MCP-kald, ingen scrape, ingen API. Hvis du finder dig selv i at
  hente data her, er du drevet uden for Phase 4 — det hører til Phases 1-3.

## Maintenance

- Transform-logik i `assemble.py`; kontrakter/regler i `references/assembler-contract.md`. Ret
  kun de to.
- Fane-/CSV-kolonner spejler Ians skeleton + den verificerede Editor-CSV-research. Ændrer Ian
  skeletonet, eller verificeres snippet-header-kolonnen, opdatér begge.
- Limits + CF-teknik importeres fra `responsive-search-ads/sheet_layout.py` — rør ikke en kopi.
- v1 er Search-only, én CSV per entitet. pMax/Shopping/Display + shared-list-via-CSV (UNVERIFIED)
  branches senere.
