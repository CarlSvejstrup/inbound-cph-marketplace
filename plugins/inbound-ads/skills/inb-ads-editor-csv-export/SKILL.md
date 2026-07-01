---
name: inb-ads-editor-csv-export
description: Konverterer en bekræftet Google Ads review-workbook (.xlsx) fra enten inb-ads-campaign-build eller optimerings-loopet til Google Ads Editor-import-CSV'er bundtet i ÉN .zip, som ren lokal transform der aldrig selv pusher til Google Ads-kontoen.
---

# inb-ads-editor-csv-export

Den delte workbook→CSV-konverter for begge Google Ads-workflows. Editor importerer KUN CSV, ikke
.xlsx ([answer 30564](https://support.google.com/google-ads/editor/answer/30564)), så begge
workflows leverer en pæn, menneske-redigerbar Excel til review, og denne skill dropper den
bekræftede Excel ned til de flade per-entitet CSV'er Editor faktisk importerer, bundtet i ÉN .zip.

```
SETUP:     inb-ads-campaign-build → assembler       → fuld .xlsx        ─┐
OPTIMIZE:  live-analyse           → review_workbook  → delmængde .xlsx   ─┤
                                                                  [mennesket bekræfter/redigerer]
                                              inb-ads-editor-csv-export → ÉN .zip (op til 6 Editor-CSV'er) → [udpak + import i Editor]
```

Begge workbooks taler samme Editor-vokabular per entitet (Campaign / Level / Ad group / Negative
keyword / Match type; Headline 1-15; osv. — harmoniseret 2026-06-09), så konverteren udleder
hvilke CSV'er den skriver fra hvilke faner der findes. Én delt `export_csv.py` for både
`inb-ads-campaign-build` og `inb-ads-optimization-loop` — ingen fork, ingen duplikeret logik.

Ren transform: læser ÉN lokal `.xlsx`, skriver ÉN lokal `.zip` med op til 6 `.csv` indeni. Ingen
Google Ads API-kald, intet push, ingen ekstern read/write — mennesket udpakker og importerer
CSV'erne i Editor (Account → Import → From file) efter review. CSV'erne er nummererede
(`1-campaigns.csv` … `6-negatives.csv`) så det udpakkede bundt sorterer i Editors import-rækkefølge.

## To workbook-dialekter, én kontrakt

| Dialekt | Faner | Hvad den indeholder |
|---|---|---|
| **assembler** (inb-ads-campaign-build) | `01 Campaign settings`, `02 Ad groups`, `03 Keywords`, `04 Negative keywords`, `06 RSAs`, `07 Assets` | en fuld NY kampagne (alt net-new, Paused) |
| **optimerings-loop** | `Negative keywords`, `Nye keywords (vindere)`, `RSA challengers` | en delmængde — kun negatives, promoverede vinder-keywords, RSA-challengers |

`read_tab` matcher fanenavne på alias (tolerant for `NN `-præfiks), så begge dialekter rammer de
samme writers. Mindst ÉN genkendt entitet-fane kræves (campaign-settings er ikke påkrævet).

Loop-specifikke regler (gælder kun loop-workbooken):
- Alle RSA-rækker er net-new challengers, aldrig in-place edits — at redigere en live RSA nulstiller
  dens læring, og Editors CSV kan ikke pålideligt matche en eksisterende RSA. Mennesket sætter den
  gamle annonce på pause når challengeren er bevist.
- Konto-niveau negatives udfoldes til én `Campaign negative`-række per aktiv kampagne (Editor CSV
  har ingen konto-niveau). Det sker i loopets builder, som har kampagnelisten.
- `#Original`-kolonner bevares verbatim (korrekt for redigerbare entiteter som en keywords
  bud/URL) — harmløst når ingen findes, og loopet emitterer aldrig én for RSA'er.

## Trin 0 — Kontekst

Læs `references/editor-csv-contract.md` — målskemaet (hvilke CSV-kolonner der kommer fra hvilke
workbook-celler), de to guards, negatives-non-flatten-reglen og de UNVERIFIED kolonnenavne. Den
vinder ved konflikt. Dansk medmindre brugeren skriver engelsk.

## Trin 1 — Find den bekræftede workbook

Du skal bruge den godkendte `.xlsx` fra assembler-kørslen, ikke et udkast. Spørg brugeren om stien
hvis den ikke er givet. Ligger den på Drive, download den lokalt først — scriptet læser en lokal fil.

## Trin 2 — Kør konverteren

```bash
python3 ${CLAUDE_SKILL_DIR}/export_csv.py \
  --workbook "Campaign - <klient> - <YYYY-MM-DD>.xlsx" \
  --outdir ./editor-csv
```

Output: ÉN `.zip` i `--outdir` (`<workbook-navn> - editor-csv.zip`) med op til 6 nummererede CSV'er
indeni + en JSON-opsummering på stdout (peger på zip'en, beholder rækketal per fil).

De to guards fra assembleren (§6 i kontrakten) genkører her, fordi et menneske kan have redigeret
den bekræftede Excel mellem godkendelse og konvertering:
1. Ingen positiv keyword må være blank/Broad — kun Exact eller Phrase.
2. RSA-felter genberegnes mod 30/90/15 (headline/description/path).

- **Exit 0:** zip'en skrevet med alle relevante CSV'er.
- **Exit ≠ 0:** en guard stoppede — INGEN zip for denne workbook i `--outdir` (en evt. ældre zip fra
  et tidligere kør ryddes FØR guarden, så en fejlende kørsel aldrig efterlader et vildledende
  bundt). Ret i workbooken (fane 03 for keywords, fane 06 for RSA'er) og kør igen — overstyr aldrig
  guarden.

## Trin 3 — De 6 CSV'er i zip'en

| CSV (i zip) | Fra workbook-fane | Editor-entitet |
|---|---|---|
| `1-campaigns.csv` | 01 Campaign settings | kampagne (status altid `Paused`) |
| `2-adgroups.csv` | 02 Ad groups | ad groups (+ Max CPC) |
| `3-keywords.csv` | 03 Keywords | positive keywords (Exact/Phrase, `Paused`) |
| `4-ads.csv` | 06 RSAs | RSA'er (Headline 1-15, Description 1-4, Path 1-2) |
| `5-assets.csv` | 07 Assets | sitelinks / callouts / structured snippets |
| `6-negatives.csv` | 04 Negative keywords | kun klient-specifikke negatives |

Nummerprefikset gør at de udpakkede filer sorterer i præcis den rækkefølge Editor skal have dem
importeret. En loop-dialekt med kun 3 faner giver et 3-filers bundt (fx `3`, `4`, `6`) — huller i
nummereringen er harmløse, rækkefølgen holder.

Faner der aldrig bliver en CSV: 00 README, 05 Monitor negatives, 08 Launch QA, 09 Validation
(review-only metadata). Review-kolonner (`Notes`, `Keyword display`, `Test hypothesis`, `Reason`,
`Category`, `vinkel`/`hypotese`) droppes — kun rene Editor-headers overlever.

## Trin 4 — Negatives-non-flatten

`negatives.csv` læser kun fane-04's klient-specifikke rækker:
- Springer linjen `[SHARED LIST APPLIED BY REFERENCE ...]` over — den er en reference-markør, ikke
  en Editor-række. De 277 delte negative ord kommer aldrig i en CSV; de tilknyttes by-reference i
  Editor (vedhæft den delte liste "Generelle negative søgeord" id `6688642473` til kampagnen manuelt).
- Læser aldrig fane 05 (monitor-first-kandidater) — at committe dem er over-blokerings-skaden
  Phase 2 bevidst undgår.

Ser du de 277 i en CSV, er reglen brudt — stop.

## Trin 5 — Output + import-vejledning

Lever:
1. Stien til den skrevne `.zip` (+ rækketal per CSV, fra JSON-opsummeringen).
2. Udpakningsvejledning: import-rækkefølgen (afhængigheder) er `campaigns → adgroups → keywords →
   ads → assets → negatives` — nummerprefikset sorterer dem allerede sådan. Kør Check Changes efter
   hver. I Editor: Account → Import → From file → vælg CSV'en → tjek kolonne-headers (Editor
   auto-mapper engelske headers; ret i dropdown hvis nødvendigt) → Import → Review imported changes.
3. Den delte negativliste tilknyttes manuelt by-reference (id `6688642473`) — ikke i nogen CSV.
4. Manuelt efter import: sprog = Dansk, Denmark = Presence (ikke Presence-or-Interest), verificér
   leadgen-konverteringshandlingen, status = Paused, kør launch-QA (workbookens fane 08), enable
   først når alle Must-pass-gates er grønne.
5. UNVERIFIED-flag: structured-snippet-headerens CSV-kolonnenavn (`Header` — kan være `Subject`
   eller andet). Verificér via ÉN Editor-round-trip (eksportér en konto med en snippet, se den
   faktiske header) før du stoler på den. Fejler snippet-importen indtil da: ret kun den ene
   header-celle i CSV'en.

## Sandheds-grænse

Målskemaet (`references/editor-csv-contract.md` §-mapping) stammer fra Ians faktiske skeleton +
assembler-kontrakten, ikke fra Googles offentlige docs (de udskyder bevidst den fulde kolonneliste
til "den næste artikel"). Den ærlige accept-test er ÉN rigtig Editor-import (eller en eksport-diff
fra en lille rigtig kampagne), ikke doc-læsning. En forkert-men-plausibel header degraderer til
Editors manuelle mapping-dropdown, ikke stille korruption — men kald det aldrig "verificeret" uden
den ene rigtige import.

## Maintenance

- Transform-logik i `export_csv.py`; målskema + regler i `references/editor-csv-contract.md`. Ret
  kun de to.
- CSV-kolonnerne skal spore til workbook-cellerne. Ændrer `assembler`-fanerne kolonner, eller
  tilføjes et felt, opdatér begge skills + denne kontrakt (de er tæt koblede par).
- Læs workbooken by header-navn, ikke kolonneindeks — Editor-headers er case-/space-ufølsomme, og
  by-navn-læsning gør konverteren immun mod kolonne-omrokering fra assembler-stylingen.
- 30/90/15-grænserne er de eneste duplikerede konstanter (Google-faste, ikke et Inbound-valg);
  assembler importerer dem fra `sheet_layout.py`, men cross-plugin-import virker ikke i Cowork, så
  de tre heltal er gentaget her med vilje.
