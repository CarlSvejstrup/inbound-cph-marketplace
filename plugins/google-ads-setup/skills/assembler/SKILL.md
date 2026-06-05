---
name: assembler
description: Phase-4-barrieren i campaign-build der fletter de fire upstream-outputs (campaign-strategy, structuring, rsa-manifest, assets) til Ians 10-fane review-workbook (Excel-only), kører QA/validering, og stopper ved review-artefaktet. Pusher ALDRIG til Google Ads API'et. Workbooken er klient-bekræftelses-artefaktet; Editor-CSV'er genereres SENERE fra den bekræftede Excel af google-ads-general-konverteringsskillen. Workbooken er et tabsfrit superset (Max CPC, numerisk budget, negativ-level, per-type asset-kolonner). Den arvede 277-term delte negativliste påføres by-reference, aldrig enumereret. Brug når brugeren siger "saml kampagnen", "assembler", "byg review-workbook", "flet alt sammen", eller afslutter en campaign-build-kørsel. Svarer på dansk.
---

# assembler

Phase-4-barrieren i **campaign-build**. Fletter de fire upstream-outputs til Ians 10-fane
review-workbook (**Excel-only**), kører QA/validering, og leverer review-artefaktet til
mennesket. Det er en **ren transform** (4 JSON-shapes → workbook) — ingen eksterne reads,
ingen writes til nogen konto, ingen CSV.

Hele transform-logikken bor i `assemble.py`; alle fane-kontrakter + de hårde regler bor i
`references/assembler-contract.md` — **læs den, den vinder ved konflikt.**

## Hård regel — Excel-only, INGEN CSV, INGEN API-push

Assembleren producerer KUN workbooken (beslutning 2026-06-05). Workbooken er
klient-bekræftelses-artefaktet — det er ofte den Excel der sendes til kunden for godkendelse.
**Editor-CSV'er genereres SENERE**, fra den bekræftede Excel, af konverteringsskillen i
`google-ads-general` (Excel-upload → 6 Editor-CSV'er). Derfor er workbooken et **tabsfrit
superset**: hvert felt en CSV skal bruge har en dedikeret celle (Max CPC, numerisk dagsbudget,
negativ-level/ad-group, asset-level, per-type asset-kolonner). `CSV = kun Editor-skema`-grænsen
bor nu i konverteren, ikke her.

Assembleren kalder ALDRIG Google Ads API'et (beslutning 2026-06-03). `assemble.py` laver kun
én lokal `.xlsx`-write.

## Designprincip — fletter, opfinder ikke

De fire inputs er allerede produceret og godkendt af de tidligere faser. Assembleren
RECONCILER dem og renderer — den genererer intet nyt indhold. Tre ting den håndhæver (alle i
reference-filen, verificeret mod Ians skeleton):

1. **Negatives flades ALDRIG.** structuring's tre negative-tiers går tre forskellige steder:
   den arvede 277-term delte liste (`inherited_shared_list`) → tab 08 launch-gate-linje +
   reference-linje i tab 04, ALDRIG enumereret; `client_specific_additions` → tab 04 (med
   Level/Ad group så konverteren kan udlede Editor-Type); `monitor_first_candidates` → KUN
   tab 05. Hvis de 277 nogensinde enumereres, er Phase-2-beslutningen ("add to this") regreset.
2. **Workbooken er et tabsfrit superset.** Hvert felt konverteren senere skal bruge har en
   dedikeret celle: Max CPC (tab 02), numerisk dagsbudget (tab 01), negativ Level + Ad group
   (tab 04), asset-Level + per-type kolonner (tab 07). Review-metadata (`grounded_in`,
   `url_source`, `why`, `vinkel`/`hypotese`, LEN, `Pass`) bliver også i workbooken — konverteren
   dropper dem ned til rene Editor-headers, ikke assembleren.
3. **Limits er importeret, ikke retypet.** 30/90/15 + LEN+rød-CF kommer fra
   `responsive-search-ads/sheet_layout.py` FIELDS. Én kilde til sandhed.

## To hårde emit-time guards (defense-in-depth)

`assemble.py` fejler LØST før den skriver noget:
- **Guard 1 — ingen blank/Broad positiv keyword.** Hver keyword-række SKAL have eksplicit
  `Exact`/`Phrase`. Blank/manglende/Broad → assembleren nægter at bygge og rapporterer
  rækkerne (silent-Broad-fælden fanget ved grænsen).
- **Guard 2 — tab 09 genberegnes uafhængigt.** Stol IKKE på fill-sheets tidligere gate;
  genberegn LEN + Pass mod de importerede limits, så en menneske-redigering mellem Phase 3 og
  assembly der overskrider en grænse stadig fanges. Over-længde → exit 3 + rød markering.
- Begge køres FØR nogen fil skrives; mismatch i kampagnenavn på tværs af de fire shapes stopper
  også (paste mellem faser kan desynce dem).

**NB:** Guard 1 + 2 SKAL også køre igen i konverteren, fordi et menneske kan redigere Excel'en
mellem assembly og konvertering (en Broad-keyword indført dér ville ellers sejle igennem).

## When to use

Trigger-fraser: "saml kampagnen", "assembler", "byg review-workbook", "flet alt sammen",
"campaign-build assembly", eller automatisk som Phase-4-barriere når Phases 1-3 er godkendt.

## Trin 0 — Kontekst

Læs `references/assembler-contract.md` — de fire shapes,
fane-kontrakter, superset-reglen, negatives-non-flatten-reglen, guards og
smoke-test-invarianter. Dansk medmindre brugeren skriver engelsk.

## Trin 1 — Saml de fire inputs

Find kørslens fire artefakter (artefakt-mappe eller manuelt indsat):
`campaign-strategy.json`, `structuring.json`, rsa-manifest (`rsa_artifacts`), `assets.json`.
Join-nøgle = `campaign` (skal matche på tværs af alle fire). Ad groups joines på `name` mellem
structuring + rsa-manifest. Mangler en: sig hvilken og stop — assembleren kræver alle fire.

## Trin 2 — Kør assembleren

```bash
python3 ${CLAUDE_SKILL_DIR}/assemble.py \
  --strategy campaign-strategy.json \
  --structuring structuring.json \
  --rsa rsa-manifest.json \
  --assets assets.json \
  --workbook "Campaign - <klient> - <YYYY-MM-DD>.xlsx" \
  --overview "Kampagne overblik.md" \
  --date <YYYY-MM-DD>
```

`--date` gives ind (scriptet kan ikke kalde `now()`). Output: 10-fane workbook (Excel-only,
INGEN CSV) + `Kampagne overblik.md` (lead-doc, forsiden) + en JSON-opsummering på stdout.
- **Exit 0:** alt validt.
- **Exit 1:** en guard stoppede (kampagnenavn-mismatch eller blank/Broad keyword) — INTET
  skrevet. Ret upstream og kør igen.
- **Exit 3:** workbook blev skrevet, MEN tab 09 har over-længde-felter (rød). Ret teksten
  upstream før konvertering — overstyr ikke.

## Trin 2.5 — Udfyld `Kampagne overblik.md` (de semantiske slots)

Scriptet pre-udfylder de strukturelle fakta i overbliks-doc'et, men efterlader `{{model: …}}`-
slots til de **semantiske** dele (fund + struktur-rationale + launch-gates), fordi de ikke kan
kodes mekanisk. Åbn `Kampagne overblik.md` og erstat hver `{{model: …}}`-slot:
- **Struktur-rationale:** én linje fra structuring's `structure_rationale`.
- **Vigtigste fund/flag:** 2-5 one-linere fra tab 08 (Must-pass) + tab 09 (over-længde) +
  input-objekterne (udeladte usikre sitelink-URL'er, snippet-header-kolonne UNVERIFIED,
  tracking-gate, overlappende ad groups der skal pauses). Intet blokerende → "Ingen blokerende
  fund — klar til review."
- **Launch-gate:** Must-pass-rækkerne fra tab 08 som one-liners.
Hold det stramt — one-liners, ikke afsnit. Overbliks-doc'et er forsiden; workbooken er
detaljen. Template + regler: `references/kampagne-overblik-template.md`. **Ét lead-doc** — lav
ikke også en separat import-README.

## Trin 3 — Verificér output (kort)

Bekræft hurtigt: 10 faner; de 277 / shared-list-id IKKE enumereret (kun reference-linjen i
tab 04 + tab 08); monitor-kandidater kun i tab 05; tab 03 keywords kun Exact/Phrase; tab 09
Pass beregnet; superset-cellerne til stede (tab 02 Max CPC, tab 01 numerisk budget, tab 04
Level/Ad group, tab 07 Level + per-type kolonner); `Kampagne overblik.md` har ingen
tilbageværende `{{model: …}}`-slots. (Disse er smoke-test-invarianterne.)

## Trin 4 — Gem (write — gated)

Workbooken er en ekstern write. Bed om eksplicit bekræftelse én gang før du gemmer/uploader.
Workbook → Drive via connector (`create_file`, Office-mode `.xlsx`). Default klientmappe under
`${user_config.inbound_root_folder_id}` hvis den kan resolves, ellers Drive-rod med en note.

## Trin 5 — Output

Lever:
1. Sti til workbooken (+ Drive-link hvis uploadet).
2. **Launch-gate-opsummering fra tab 08** — fremhæv Must-pass-gates: tracking verificeret,
   Presence-only geo, Search Partners/Display off, **den delte negativliste tilknyttet
   by-reference (id 6688642473)**, klient-negatives anvendt.
3. **Validerings-status fra tab 09** — antal over-længde-felter (0 = grønt); hvis >0, list dem
   og sig "ret før konvertering".
4. **Næste skridt (manuelt, human-in-the-loop):** workbooken sendes til kunden for
   bekræftelse. Efter godkendelse konverteres den til Editor-CSV'er af `google-ads-general`
   konverteren, og mennesket importerer CSV'erne i Editor (Account → Import → From file),
   tilknytter den delte negativliste, kører launch-QA, og enabler først når alle Must-pass-gates
   er grønne. Assembleren pusher INTET.
5. **Carried-forward-flags** (uændret): snippet-header-kolonnenavnet UNVERIFIED (verificeres i
   konverteren via Editor-round-trip); UTM ikke emitteret endnu (dækket som tab-08-gate); ingen
   live-Cowork-ende-til-ende-kørsel endnu; rsa-copywriter intake-injection-antagelse uafprøvet.
   Carl har parkeret dem.

## Risici / noter

- **Negatives-non-flatten er den vigtigste regel.** Hvis du ser de 277 enumereret nogetsteds:
  stop — Phase-2-beslutningen er brudt. De påføres KUN by-reference.
- **Guards fejler LØST før write** — en exit 1 betyder INGEN fil blev skrevet; det er
  designet. Ret upstream, ikke i assembleren.
- **Limits importeres fra sheet_layout.py** — ret aldrig 30/90/15 her; ret RSA-layoutet hvis
  Google ændrer grænserne.
- **Excel-only:** assembleren emitterer INGEN CSV. CSV-genereringen + `CSV = kun Editor-skema`
  -grænsen bor i `google-ads-general`-konverteren, som læser den klient-bekræftede Excel.
- **Pure transform:** ingen MCP-kald, ingen scrape, ingen API. Hvis du finder dig selv i at
  hente data her, er du drevet uden for Phase 4 — det hører til Phases 1-3.

## Maintenance

- Transform-logik i `assemble.py`; kontrakter/regler i `references/assembler-contract.md`. Ret
  kun de to.
- Fane-kolonner spejler Ians skeleton + superset-kontrakten (konverteren afhænger af dem). Ændrer
  Ian skeletonet, eller tilføjes et nyt CSV-felt i konverteren, opdatér begge + denne skill.
- Limits + CF-teknik importeres fra `responsive-search-ads/sheet_layout.py` — rør ikke en kopi.
- v1 er Search-only. pMax/Shopping/Display senere.
  branches senere.
