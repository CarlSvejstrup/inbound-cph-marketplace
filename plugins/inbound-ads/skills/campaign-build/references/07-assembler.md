# Phase 4 — assembler (review-workbook-barrieren)

Phase-4-barrieren. Fletter de fire upstream-outputs (`campaign-strategy.json`, `structuring.json`,
`rsa-manifest.json`, `assets.json`) til Ians 10-fane review-workbook (**Excel-only**), kører
QA/validering, og leverer review-artefaktet. En **ren transform** (4 JSON-shapes → workbook) — ingen
eksterne reads, ingen writes til nogen konto, ingen CSV.

**Phase 4 emitterer altid en fil** — også når hele pipelinen kører automatisk. Review-workbooken ER
leverancen; der er ingen separat solo-mode for assembleren (den har intet selvstændigt shell-skill).
Transform-logikken bor i `${CLAUDE_SKILL_DIR}/scripts/assemble.py`; alle fane-kontrakter + de hårde regler
bor i `${CLAUDE_SKILL_DIR}/references/assembler-contract.md` — læs den, den vinder ved konflikt.

## Hård regel — Excel-only, INGEN CSV, INGEN API-push

Producerer KUN workbooken (beslutning 2026-06-05). Workbooken er klient-bekræftelses-artefaktet — ofte
den Excel der sendes til kunden for godkendelse. **Editor-CSV'er genereres SENERE**, fra den bekræftede
Excel, af `editor-csv-export`-skillen. Derfor er workbooken et **tabsfrit superset**:
hvert felt en CSV skal bruge har en dedikeret celle. `assemble.py` laver kun én lokal `.xlsx`-write (+ et
overbliks-`.md`); den kalder ALDRIG Google Ads API'et.

## Designprincip — fletter, opfinder ikke

De fire inputs er allerede produceret og godkendt. Assembleren RECONCILER og renderer — genererer intet
nyt indhold. Tre ting den håndhæver (alle i reference-filen, verificeret mod Ians skeleton):

1. **Negatives flades ALDRIG.** structuring's tre negative-tiers går tre steder: den arvede 277-term delte
   liste (`inherited_shared_list`) → tab 08 launch-gate-linje + reference-linje i tab 04, ALDRIG
   enumereret; `client_specific_additions` → tab 04 (med Level/Ad group); `monitor_first_candidates` → KUN
   tab 05.
2. **Workbooken er et tabsfrit superset.** Hvert felt konverteren senere skal bruge har en dedikeret celle:
   Max CPC (tab 02), numerisk dagsbudget (tab 01), negativ Level + Ad group (tab 04), asset-Level +
   per-type kolonner (tab 07).
3. **Limits er Googles faste RSA-grænser (30/90/15), ikke layout-logik.** De er navngivne konstanter i
   `assemble.py` (med kanonisk mirror i `responsive-search-ads/sheet_layout.py` FIELDS). Scriptet importerer
   IKKE længere det andet skill — det er self-contained og bootstrapper selv openpyxl. Ændrer Google en
   grænse: ret begge steder.

## To hårde emit-time guards (defense-in-depth)

`assemble.py` fejler LØST før den skriver noget:
- **Guard 1 — ingen blank/Broad positiv keyword.** Hver keyword-række SKAL have eksplicit `Exact`/`Phrase`.
  Blank/manglende/Broad → assembleren nægter at bygge og rapporterer rækkerne.
- **Guard 2 — tab 09 genberegnes uafhængigt** mod de navngivne limits, så en menneske-redigering mellem
  Phase 3 og assembly der overskrider en grænse stadig fanges. Over-længde → exit 3 + rød markering.
- Mismatch i kampagnenavn på tværs af de fire shapes stopper også (paste mellem faser kan desynce dem).

## Trin 0 — Kontekst

Læs `references/assembler-contract.md` — de fire shapes, fane-kontrakter, superset-reglen,
negatives-non-flatten-reglen, guards og smoke-test-invarianter. Dansk medmindre brugeren skriver engelsk.

## Trin 1 — Saml de fire inputs

Find kørslens fire artefakter i artefakt-mappen: `campaign-strategy.json`, `structuring.json`,
`rsa-manifest.json`, `assets.json`. Join-nøgle = `campaign` (skal matche på tværs af alle fire). Ad groups
joines på `name` mellem structuring + rsa-manifest. Mangler en: sig hvilken og stop.

## Trin 2 — Kør assembleren

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/assemble.py \
  --strategy campaign-strategy.json \
  --structuring structuring.json \
  --rsa rsa-manifest.json \
  --assets assets.json \
  --workbook "Campaign - <klient> - <YYYY-MM-DD>.xlsx" \
  --overview "Kampagne overblik.md" \
  --date <YYYY-MM-DD>
```

`--date` gives ind (scriptet kan ikke kalde `now()`). Output: 10-fane workbook (Excel-only, INGEN CSV) +
`Kampagne overblik.md` (lead-doc) + en JSON-opsummering på stdout.
- **Exit 0:** alt validt. **Exit 1:** en guard stoppede (kampagnenavn-mismatch eller blank/Broad keyword) —
  INTET skrevet; ret upstream og kør igen. **Exit 3:** workbook blev skrevet, MEN tab 09 har over-længde-
  felter (rød); ret teksten upstream før konvertering — overstyr ikke.

## Trin 2.5 — Udfyld `Kampagne overblik.md` (de semantiske slots)

Scriptet pre-udfylder de strukturelle fakta, men efterlader `{{model: …}}`-slots til de **semantiske**
dele (fund + struktur-rationale + launch-gates). Åbn `Kampagne overblik.md` og erstat hver slot:
- **Struktur-rationale:** én linje fra structuring's `structure_rationale`.
- **Vigtigste fund/flag:** 2-5 one-linere fra tab 08 (Must-pass) + tab 09 (over-længde) + input-objekterne
  (udeladte usikre sitelink-URL'er, snippet-header UNVERIFIED, tracking-gate, overlappende ad groups).
  Intet blokerende → "Ingen blokerende fund — klar til review."
- **Launch-gate:** Must-pass-rækkerne fra tab 08 som one-liners.
Hold det stramt. Template + regler: `references/kampagne-overblik-template.md`. **Ét lead-doc** — lav ikke
også en separat import-README.

## Trin 3 — Verificér output (kort)

Bekræft: 10 faner; de 277 / shared-list-id IKKE enumereret (kun reference-linjen i tab 04 + tab 08);
monitor-kandidater kun i tab 05; tab 03 keywords kun Exact/Phrase; tab 09 Pass beregnet; superset-cellerne
til stede; `Kampagne overblik.md` har ingen tilbageværende `{{model: …}}`-slots.

## Trin 4 — Gem (write — gated)

Workbooken er en ekstern write. Bed om eksplicit bekræftelse én gang før du gemmer/uploader. Workbook →
Drive via connector (`create_file`, Office-mode `.xlsx`). Default klientmappe under
`${user_config.inbound_root_folder_id}` hvis den kan resolves, ellers Drive-rod med en note.

## Trin 5 — Returnér

Returnér: sti til workbooken (+ Drive-link hvis uploadet); launch-gate-opsummering fra tab 08 (tracking
verificeret, Presence-only geo, Search Partners/Display off, den delte negativliste tilknyttet by-reference
id 6688642473, klient-negatives anvendt); validerings-status fra tab 09 (antal over-længde-felter, 0 =
grønt); og næste skridt (manuelt, human-in-the-loop): workbooken sendes til kunden, derefter konverteres
den til Editor-CSV'er af `editor-csv-export`-skillen, og mennesket importerer + enabler først når alle
Must-pass-gates er grønne. Assembleren pusher INTET.

## Risici / noter

- **Negatives-non-flatten er den vigtigste regel.** Ser du de 277 enumereret: stop — Phase-2-beslutningen
  er brudt.
- **Guards fejler LØST før write** — exit 1 = INGEN fil skrevet, by design. Ret upstream.
- **Limits:** ret aldrig 30/90/15 her uden også at rette `responsive-search-ads/sheet_layout.py` FIELDS
  (den kanoniske mirror).
- **Excel-only:** assembleren emitterer INGEN CSV. CSV-genereringen bor i `editor-csv-export`-skillen.
- **Pure transform:** ingen MCP-kald, ingen scrape, ingen API.

## Maintenance

Transform-logik i `scripts/assemble.py`; kontrakter/regler i `references/assembler-contract.md`. Fane-
kolonner spejler Ians skeleton + superset-kontrakten (konverteren afhænger af dem). v1 er Search-only.
