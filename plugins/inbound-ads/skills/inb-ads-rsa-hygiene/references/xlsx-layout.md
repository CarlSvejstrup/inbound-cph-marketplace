# .xlsx-layout — hvad `build-sheet.py` renderer

Farverne, header-stil og freeze panes er bagt ind i `.xlsx`-laget, så de overlever upload til Drive og renderer når filen åbnes i Google Sheets. Denne fil beskriver hvad arket indeholder; `build-sheet.py`'s docstring er den autoritative skema-kilde.

## Faner

- **Oversigt** — ærligheds-banner om hvad rapporten er / ikke er (strukturel hygiejne, ingen CVR-dom), plus den brugte `MIN_IMPRESSIONS`-floor så brugeren ved hvad der blev ekskluderet som dødvægt.
- **Ad group-dækning** — challenger-flag + manglende vinkler på tværs af alle grupper i én tabel.
- **Én fane pr. ad group** — se overblik + asset-tabel nedenfor.
- **Gap-brief** — den kopiér-klare gap-brief-blok, til `inb-ads-rsa-copy`.

## Per ad group-fane

Åbner med et overblik øverst:

- Ad group + Kampagne (fulde navne — fanenavnet kan være afkortet til Excels 31-tegns-grænse).
- Aktive RSA i gruppen + "Byg challenger?" (gul hvis under 2).
- Assets i alt (split i headlines/descriptions).
- Status-fordeling (antal aktive / dødvægt / for ny).
- Manglende vinkler (gul hvis der er huller).

Derunder asset-tabellen med kolonnerne:

```
Felt | Tekst | Vinkel | Impressions | Klik | Spend (DKK) | Status | Anbefaling
```

Google-label og CVR-indikation er bevidst fjernet fra tabellen — på Inbounds konti er hver række identisk, så kolonnerne bar ingen information (se SKILL.md "Baggrund").
