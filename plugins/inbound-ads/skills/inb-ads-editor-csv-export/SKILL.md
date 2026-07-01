---
name: inb-ads-editor-csv-export
description: Konvertér en bekræftet Google Ads review-workbook (.xlsx) til Google Ads Editor import-CSV'er bundtet i ÉN .zip. Læser TO workbook-dialekter med samme kontrakt - (a) inb-ads-campaign-build assembler-workbooken (fuld ny kampagne) og (b) optimerings-loopets review-workbook (delmængde - negatives, vinder-keywords, RSA-challengers). Anden halvdel af Excel-only-grænsen - workbooken er bekræftelses-artefaktet, denne skill dropper den ned til de flade per-entitet CSV'er Editor importerer (Editor importerer KUN CSV, ikke .xlsx). Ren transform - læser én lokal .xlsx, skriver ÉN lokal .zip med op til 6 CSV'er indeni (nummereret 1-campaigns ... 6-negatives så de sorterer i Editors import-rækkefølge). Pusher ALDRIG til Google Ads API'et; mennesket udpakker og importerer CSV'erne i Editor. Genkører de to hårde guards (ingen Broad/blank positiv keyword, LEN-tjek) fordi et menneske kan have redigeret Excel'en efter godkendelse. Den arvede 277-term delte negativliste kommer ALDRIG i en CSV - den tilknyttes by-reference i Editor. Brug når brugeren siger "lav CSV'er", "konvertér til Editor", "export til Editor", "editor-csv", "lav import-filer", "lav en zip med CSV'erne", eller har en godkendt kampagne- eller optimerings-workbook der skal importeres. Svarer på dansk.
---

# inb-ads-editor-csv-export

Den **delte workbook→CSV-konverter** for begge Google Ads-workflows. Editor importerer KUN CSV,
ikke .xlsx ([answer 30564](https://support.google.com/google-ads/editor/answer/30564)) — så begge
workflows leverer en pæn, menneske-redigerbar Excel til review, og DENNE skill dropper den
bekræftede Excel ned til de flade per-entitet CSV'er Editor faktisk importerer, bundtet i ÉN .zip.

```
SETUP:     inb-ads-campaign-build → assembler       → fuld .xlsx        ─┐
OPTIMIZE:  live-analyse           → review_workbook  → delmængde .xlsx   ─┤
                                                                  [mennesket bekræfter/redigerer]
                                              inb-ads-editor-csv-export → ÉN .zip (op til 6 Editor-CSV'er) → [udpak + import i Editor]
```

**Hvorfor ÉN delt skill (ikke én per workflow):** begge workbooks taler bevidst SAMME
Editor-vokabular per entitet (Campaign / Level / Ad group / Negative keyword / Match type;
Headline 1-15; osv. — harmoniseret 2026-06-09). Konverteren udleder hvilke CSV'er den skriver fra
hvilke faner der findes — ingen fork, ingen duplikeret builder-logik, ingen drift. Den er den
delte konverter for BÅDE build-vejen (`inb-ads-campaign-build`) og optimize-vejen (`inb-ads-optimization-loop`) —
alle søsken-skills i samme plugin, så der er kun én `export_csv.py`, ingen kopi at drive fra
hinanden.

**Ren transform:** læser ÉN lokal `.xlsx`, skriver ÉN lokal `.zip` med op til 6 `.csv` indeni.
Ingen Google Ads API-kald, intet push, ingen ekstern read/write. Mennesket udpakker og importerer
CSV'erne i Editor (Account → Import → From file) efter review. CSV'erne er nummereret
(`1-campaigns.csv` … `6-negatives.csv`) så det udpakkede bundt sorterer i Editors
import-rækkefølge. Dialekt-detaljen står lige nedenfor.

## To workbook-dialekter, én kontrakt

Skillen læser **to** slags workbooks med samme per-entitet CSV-mål (den er stadig en ren
transform — den genkender bare begge):

| Dialekt | Faner | Hvad den indeholder |
|---|---|---|
| **assembler** (inb-ads-campaign-build) | `01 Campaign settings`, `02 Ad groups`, `03 Keywords`, `04 Negative keywords`, `06 RSAs`, `07 Assets` | en fuld NY kampagne (alt net-new, Paused) |
| **optimerings-loop** | `Negative keywords`, `Nye keywords (vindere)`, `RSA challengers` | en delmængde — kun negatives, promoverede vinder-keywords, RSA-challengers |

`read_tab` matcher fanenavne på alias (tolerant for `NN `-præfiks), så begge dialekter rammer de
samme writers. Mindst ÉN genkendt entitet-fane kræves (campaign-settings er IKKE længere påkrævet).

**Loop-specifikke regler (gælder kun loop-workbooken):**
- **Alle RSA-rækker er NET-NEW challengers** — aldrig in-place edits. At redigere en live RSA
  nulstiller dens læring (RSA'er er reelt immutable), og Editors CSV kan ikke pålideligt matche en
  eksisterende RSA. Loopet emitterer derfor en frisk challenger; mennesket sætter den gamle annonce
  på pause når challengeren er bevist.
- **Konto-niveau negatives udfoldes** til én `Campaign negative`-række per aktiv kampagne (Editor
  CSV har ingen konto-niveau). Det sker i loopets builder (som har kampagnelisten), så CSV'en er
  what-you-see-is-what-imports.
- **`#Original`-passthrough:** skillen bevarer enhver `*#Original`-kolonne verbatim (korrekt for
  reelt-redigerbare entiteter som en keywords bud/URL). Den er harmløs når ingen findes — og
  loopet emitterer aldrig én for RSA'er.

## Hård regel — pusher ALDRIG, mennesket importerer

Denne skill rører ALDRIG Google Ads-kontoen. Den laver CSV-filer; et menneske importerer dem i
Editor og kører **Check Changes** før **Post Changes**. Human-in-the-loop på hver ekstern write
er ikke til forhandling.

## Hvornår

Triggerfraser: "lav CSV'er", "konvertér til Editor", "export til Editor", "editor-csv", "lav
import-filer", "lav en zip med CSV'erne", "gør workbooken klar til Editor", eller når en godkendt
kampagne-workbook skal importeres.

## Trin 0 — Kontekst

Læs `references/editor-csv-contract.md` — målskemaet (hvilke CSV-kolonner der kommer fra hvilke
workbook-celler), de to genkørte guards, negatives-non-flatten-reglen og de UNVERIFIED
kolonnenavne. **Den vinder ved konflikt.** Dansk medmindre brugeren skriver engelsk.

## Trin 1 — Find den bekræftede workbook

Du skal bruge **den godkendte** `.xlsx` fra assembler-kørslen (ikke et udkast). Spørg brugeren om
stien hvis den ikke er givet. Ligger den på Drive, så download den lokalt først (read, ingen
gate) — scriptet læser en lokal fil.

## Trin 2 — Kør konverteren

```bash
python3 ${CLAUDE_SKILL_DIR}/export_csv.py \
  --workbook "Campaign - <klient> - <YYYY-MM-DD>.xlsx" \
  --outdir ./editor-csv
```

Output: ÉN `.zip` i `--outdir` (`<workbook-navn> - editor-csv.zip`) med op til 6 nummererede CSV'er
indeni + en JSON-opsummering på stdout (peger på zip'en, beholder rækketal per fil indeni).

- **Exit 0:** zip'en skrevet med alle relevante CSV'er.
- **Exit ≠ 0 (en guard stoppede):** INGEN zip for denne workbook i `--outdir` — en evt. ældre zip
  fra et tidligere kør af samme workbook ryddes FØR guarden, så en fejlende kørsel aldrig efterlader
  et vildledende importérbart bundt. Enten (a) en positiv keyword er blank/Broad i workbooken, eller
  (b) et RSA-felt er over hård grænse (et menneske redigerede Excel'en efter godkendelse). Ret i
  workbooken (fane 03 hhv. fane 06) og kør igen — overstyr aldrig guarden.

### Hvorfor guards genkøres her

De samme to guards kører i `assembler`, MEN et menneske kan have redigeret den bekræftede Excel
mellem godkendelse og konvertering. En Broad-keyword eller en for-lang headline indført dér ville
ellers sejle direkte ind i en CSV. Konverteren tjekker derfor igen ved SIN egen grænse
(contract §6).

## Trin 3 — De 6 CSV'er i zip'en (én per entitet, nummereret i import-rækkefølge)

| CSV (i zip) | Fra workbook-fane | Editor-entitet |
|---|---|---|
| `1-campaigns.csv` | 01 Campaign settings | kampagne (status altid `Paused`) |
| `2-adgroups.csv` | 02 Ad groups | ad groups (+ Max CPC) |
| `3-keywords.csv` | 03 Keywords | positive keywords (Exact/Phrase, `Paused`) |
| `4-ads.csv` | 06 RSAs | RSA'er (Headline 1-15, Description 1-4, Path 1-2) |
| `5-assets.csv` | 07 Assets | sitelinks / callouts / structured snippets |
| `6-negatives.csv` | 04 Negative keywords | **kun klient-specifikke** negatives |

Nummerprefikset gør at de udpakkede filer sorterer i præcis den rækkefølge Editor skal have dem
importeret. En loop-dialekt der kun har 3 faner giver et 3-filers bundt (fx `3`, `4`, `6`) — huller
i nummereringen er harmløse, rækkefølgen holder.

Faner der ALDRIG bliver en CSV: 00 README, 05 Monitor negatives, 08 Launch QA, 09 Validation
(review-only metadata). Snippet-/keyword-review-kolonner (`Notes`, `Keyword display`, `Test
hypothesis`, `Reason`, `Category`, `vinkel`/`hypotese`) droppes — kun rene Editor-headers
overlever.

## Trin 4 — Negatives-non-flatten (vigtigste regel)

`negatives.csv` læser **KUN** fane-04's klient-specifikke rækker. Den:
- **SPRINGER** linjen `[SHARED LIST APPLIED BY REFERENCE ...]` over — den er en reference-markør,
  ikke en Editor-række. De 277 delte negative ord kommer **ALDRIG** i en CSV; de tilknyttes
  by-reference i Editor (vedhæft den delte liste "Generelle negative søgeord" id `6688642473` til
  kampagnen manuelt).
- **Læser ALDRIG fane 05** (monitor-first-kandidater) — at committe dem er over-blokerings-skaden
  Phase 2 bevidst undgår.

Ser du de 277 i en CSV: stop — reglen er brudt.

## Trin 5 — Output + import-vejledning

Lever:
1. **Stien** til den skrevne `.zip` (+ rækketal per CSV indeni, fra JSON-opsummeringen).
2. **Udpak zip'en**, så **import-rækkefølgen** (afhængigheder): `campaigns → adgroups → keywords →
   ads → assets → negatives` — nummerprefikset sorterer dem allerede sådan. Kør **Check Changes**
   efter hver. I Editor: Account → Import → From file → vælg CSV'en → tjek kolonne-headers (Editor
   auto-mapper engelske headers; ret i dropdown hvis nødvendigt) → Import → Review imported changes.
3. **Den delte negativliste tilknyttes manuelt** by-reference (id `6688642473`) — IKKE i nogen CSV.
4. **Manuelt efter import:** sprog = Dansk, Denmark = Presence (ikke Presence-or-Interest),
   verificér leadgen-konverteringshandlingen, status = **Paused**, kør launch-QA (workbookens
   fane 08), enable først når alle Must-pass-gates er grønne.
5. **UNVERIFIED-flag:** structured-snippet-headerens CSV-kolonnenavn (`Header` — kan være `Subject`
   eller andet). Verificér via ÉN Editor-round-trip (eksportér en konto med en snippet, se den
   faktiske header) før du stoler på den. Indtil da: hvis snippet-importen fejler, ret kun den ene
   header-celle i CSV'en.

## Hård sandheds-grænse (skriv aldrig "verificeret mod Google docs")

Målskemaet (`references/editor-csv-contract.md` §-mapping) stammer fra Ians faktiske skeleton +
assembler-kontrakten, IKKE fra Googles offentlige docs (de udskyder bevidst den fulde kolonneliste
til "den næste artikel"). Den ærlige accept-test er **én rigtig Editor-import** (eller en
eksport-diff fra en lille rigtig kampagne), ikke doc-læsning. En forkert-men-plausibel header
degraderer til Editors manuelle mapping-dropdown, ikke stille korruption — så det er ikke
alt-eller-intet, men kald det aldrig "verificeret" uden den ene rigtige import.

## Maintenance

- Transform-logik i `export_csv.py`; målskema + regler i `references/editor-csv-contract.md`. Ret
  kun de to.
- CSV-kolonnerne SKAL spore til workbook-cellerne. Ændrer `assembler`-fanerne kolonner, eller
  tilføjes et felt, opdatér begge skills + denne kontrakt (de er tæt koblede par).
- Læs workbooken **by header-navn, ikke kolonneindeks** — Editor-headers er case-/space-ufølsomme,
  og by-navn-læsning gør konverteren immun mod kolonne-omrokering fra assembler-stylingen.
- 30/90/15-grænserne er de eneste duplikerede konstanter (Google-faste, ikke et Inbound-valg);
  assembler importerer dem fra `sheet_layout.py`, men cross-plugin-import virker ikke i Cowork, så
  de tre heltal er gentaget her med vilje.
