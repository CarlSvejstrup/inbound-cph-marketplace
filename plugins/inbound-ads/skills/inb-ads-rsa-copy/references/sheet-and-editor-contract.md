# Ark-arkitektur, kolonne-kontrakt + Editor-import

Al reference-detaljen om HVORDAN arket bygges, hvad kolonnerne er, og hvorfor .xlsx ikke er import-filen. SKILL.md holder den korte version; dybden bor her. Læs den hvis du skal ændre `sheet_layout.py`, forstå multi-row-formatet, eller forklare Editor-stien.

## Arkitektur (byg-fra-bunden hver kørsel)

Et **nyt ark bygges fra bunden hver kørsel** — der klones intet remote-ark og redigeres ingen celler i en eksisterende fil.

- `sheet_layout.py` er single source of truth for layoutet: kolonne-rækkefølge, `=LEN()`-formlen ved siden af hvert tekstfelt, og de røde conditional-formatting-regler (headline LEN > 30, description LEN > 90, path LEN > 15). `build_sheet(n_rows)` bygger en workbook med header i række 1 og `n_rows` datarækker, hver række pre-wired med sine egne LEN-formler og CF-rangen udvidet til at dække alle rækker. Fordi de lever i `.xlsx`-laget (ikke i CSV-værdier), overlever de upload til Drive og bliver ved med at være live når kunden redigerer arket. Verificeret: upload af en udfyldt `.xlsx` via Drive-connectoren holder `=LEN()` computende.
- `build-template.py` regenererer det committede single-RSA `template.xlsx` (kalder `build_sheet(1)`). Det er et reference-artefakt + et hurtigt smoke-check; skillen loader det **ikke** ved fill-tid — `fill-sheet.py` genbygger layoutet friskt for præcis så mange rækker som der er RSA'er. Kør kun `build-template.py` når du vil inspicere det tomme layout.
- `fill-sheet.py` læser `ads.json`, kalder `build_sheet(len(ads))`, skriver kun tekstcellerne (aldrig LEN-cellerne), validerer hver streng per RSA, og gemmer en ny `.xlsx`. Én kørsel kan producere **1 RSA (én datarække) eller flere RSA'er (én række hver) i samme ad group**.

Kører i **Cowork** (Drive-connector) og **lokalt** (skriv fil til disk) — ingen `gws` CLI, ingen Sheets API. Begge scripts self-bootstrapper `openpyxl` via `pip install` hvis den mangler, så det eneste krav er Python 3 med pip — ingen checked-in virtualenv, ingen maskine-specifikke stier, ingen ekstern konto-auth.

## Kolonne-kontrakt (defineret i `sheet_layout.py`)

Kolonnenavnene følger Editors felt-navne (`Campaign`, `Ad Group`, `Headline 1`, …), så arket er en tro 1:1-spejling af Editor-skemaet — men arket selv (.xlsx) importeres ikke direkte (se Editor-import nedenfor). Header i række 1, derefter **én datarække per RSA** (række 2 for én annonce; rækker 2..N+1 for N annoncer). Hver tekst-kolonne følges af en `LEN`-kolonne. Pre-seedet på hver datarække: `Ad type = "Responsive search ad"`. `Campaign`-cellen overskrives ved hver kørsel med det navn brugeren bekræfter i Trin 1.

```
Campaign | Ad Group | Ad type | Labels |
Headline 1 | LEN | ... | Headline 15 | LEN |
Description 1 | LEN | ... | Description 4 | LEN |
Path 1 | LEN | Path 2 | LEN |
Final URL | Final mobile URL | Vinkel | Hypotese
```

`LEN`, `Vinkel` og `Hypotese` er IKKE Editor-felter — de hører kun til menneske-review-laget. `LEN` giver live tegntælling + rød farve til kunden; `Vinkel`/`Hypotese` (de to sidste kolonner) dokumenterer annoncens led-vinkel + hypotese per RSA. **Når data konverteres til en import-CSV, tager CSV'en KUN Editor-skema-kolonnerne med** — review-laget bærer ekstra-kolonnerne, import-laget bærer kun Editor-felterne. (Bruger ads-teamet i stedet paste-stien, skal mennesket markere kun Editor-kolonnerne — antag ikke at Editor selv filtrerer dem fra.)

## Editor-import (det .xlsx'en IKKE gør)

Google Ads Editor importerer **ikke** .xlsx (answer 56368: "Google Ads Editor doesn't import XLS files", `support.google.com/google-ads/editor/answer/56368`). Editors to rigtige import-stier:

1. **File import:** en **CSV** (eller Unicode-tekst `.txt`) i Editors kolonne-skema → Account → Import → From file.
2. **Paste:** "Make multiple changes" → indsæt tab-separerede rækker (kolonne-auto-mapping).

**Uafklaret (workflow-fakta, ikke en API-fakta):** hvilken sti ads-teamet faktisk bruger. Rikkes oprindelige beskrivelse ("importer arket … bulk-upload") er tvetydig. Spørg/afklar med Rikke før der bygges en CSV-eksportør — `inb-ads-campaign-build`-spec'en (§4) planlægger allerede at emittere Editor-skema RSA-CSV'er, så en CSV-eksportør hører sandsynligvis hjemme dér, ikke som en parallel sti her.

## Flere RSA'er i samme ad group (multi-row)

Editor opretter **én RSA per række** i import-skemaet. Gentager man `Campaign` + `Ad Group` på flere rækker, lander de som flere RSA'er i samme ad group — ÉT ark (review) → ÉN CSV med flere rækker (import), ikke flere filer.

`fill-sheet.py` accepterer to `ads.json`-former:

- **Én RSA (default):** top-level `headlines`/`descriptions`/`paths` (uændret fra før).
- **Flere RSA'er:** `campaign`/`ad_group`/`final_url` på top-niveau + en `ads`-liste hvor hvert element er én RSA's tekst. Top-niveau-felterne arves af hver annonce medmindre annoncen selv overstyrer dem.

```json
{
  "campaign": "IC | GSN | Generic | Brandsikring",
  "ad_group": "Brandsikring",
  "final_url": "https://...",
  "ads": [
    { "headlines": ["...15..."], "descriptions": ["...4..."], "paths": ["...2..."] },
    { "headlines": ["...15..."], "descriptions": ["...4..."], "paths": ["...2..."] },
    { "headlines": ["...15..."], "descriptions": ["...4..."], "paths": ["...2..."] }
  ]
}
```

Hårde grænser og kvalitets-gates køres **per RSA**; fejl labelles med "RSA 2, Headline 4: …" så du ved hvilken annonce der skal rettes. Antallet af RSA'er og deres vinkler vælges af brugeren i intake (Trin 1, Kald 1, spørgsmål 4) — default 1; vinkel-strategien står i Trin 4.

## Maintenance-note

Layoutet bor ÉT sted: `sheet_layout.py` (`FIELDS`, `COLUMNS`, `build_sheet`, `text_cell`, `autosize_columns`). `build-template.py` og `fill-sheet.py` importerer begge derfra — ret kun `sheet_layout.py`, så følger begge med automatisk. Regenerer det committede single-RSA `template.xlsx` (reference + smoke test) med `python3 ${CLAUDE_SKILL_DIR}/build-template.py` (kun når layoutet ændrer sig).
