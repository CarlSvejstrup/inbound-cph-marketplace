# Trin 7 — Tilføj de aftalte beslutninger (mekanik)

Læs denne fil når du når Trin 7 — altså EFTER brugeren har set hele listen og valgt en vej i Trin 6.
Aldrig før. Skriv kun det der stod på den godkendte liste.

Byg i alle tilfælde en `decisions.json` af præcis den godkendte liste (ID'erne ligger i pullet fra
Trin 3; ellers resolves de i 7A):

```json
{
  "client": "Capio", "customer_id": "4636067288",
  "negatives": [
    {"keyword": "naya kardiologi", "match_type": "phrase", "level": "campaign",
     "campaign": "IC | GSN | Aarhus", "campaign_id": "111"},
    {"keyword": "mommy makeover", "match_type": "phrase", "level": "ad_group",
     "campaign": "IC | GSN | Aarhus", "campaign_id": "111",
     "ad_group": "MR-helkropsscanning", "ad_group_id": "901"}
  ],
  "new_keywords": [
    {"keyword": "helkropsscanning aarhus", "match_type": "exact",
     "campaign": "IC | GSN | Aarhus", "campaign_id": "111",
     "ad_group": "MR-helkropsscanning", "ad_group_id": "901"}
  ]
}
```

## 7A — Tilføj LIVE via MCP (efter `Tilføj live i kontoen nu`)

Disciplinen her ER sikkerheden. I rækkefølge:

1. **Slå ID'er op (navn → id).** Write-toolsene targeter på `campaign_id` / `ad_group_id`, ikke navne.
   `campaign.id` + `ad_group.id` ligger i Trin 3-pullet; mangler de (≤30-dages rapport-vej), hent dem:
   ```sql
   SELECT campaign.id, campaign.name FROM campaign WHERE campaign.status != 'REMOVED'
   SELECT ad_group.id, ad_group.name, campaign.name FROM ad_group WHERE ad_group.status != 'REMOVED'
   ```
   Match på EKSAKT navn. Et navn der ikke kan resolves → stop og spørg, gæt aldrig et id.
2. **Grupér efter mål + match-type.** Begge tools tager en LISTE af keywords pr. kald, så saml alle
   negatives med samme (`campaign_id`|`ad_group_id`, `match_type`) i ét kald, og keywords pr.
   (`ad_group_id`, `match_type`). `match_type` skal være STORE bogstaver (`BROAD`/`PHRASE`/`EXACT`).
3. **Account-niveau-negatives** udfoldes til ét campaign-level-kald pr. aktiv kampagne. Vis listen af
   kampagner det rammer, og bekræft kort, før du kører.
4. **Dry-run FØRST, så commit** — for hver gruppe:
   - `add_negative_keywords(customer_id, campaign_id=… | ad_group_id=…, keywords=[…], match_type="PHRASE", dry_run=true)` → læs valideringen → samme kald med `dry_run=false, confirm=true`.
   - `add_keywords(customer_id, ad_group_id=…, keywords=[…], match_type="EXACT", dry_run=true)` → så
     `dry_run=false, confirm=true`. `add_keywords` committer LIVE som default — derfor ALTID dry-run
     først. Ingen paused-tilstand: keywordet er aktivt med det samme.
5. **Rapportér præcist:** "Tilføjede 3 negatives (phrase) til IC | GSN | Aarhus, 1 keyword (exact) til
   ad group MR-helkropsscanning." Fejl i dry-run/commit → vis fejlen, ret, kør gruppen igen. Tilføj
   aldrig noget uden for den godkendte liste.

Begrænsninger i MCP'en (derfor findes CSV-vejen): ingen account-niveau som ét kald (fan-out i stedet),
ingen delt negativliste, ingen paused keywords.

## 7B — Editor-CSV (efter `Lav Editor-CSV i stedet`)

Til paused challengers, delte negativlister, eller når ad-teamet selv vil importere:
```bash
python3 $LIB/write_csv.py --in <decisions.json> \
  --outdir ~/Downloads --slug "Søgeterm - <klient> - <YYYY-MM-DD>"
```
Writeren ABORTERER hellere end at sende en knækket import:
- **negatives[]:** `keyword`, `match_type` (`exact`/`phrase`/`broad`), `level` (`campaign` default /
  `ad_group` / `account`), `campaign` (kræves ved campaign+ad_group), `ad_group` (kræves ved ad_group),
  ELLER `list_name` for en delt negativliste. Negativ uden mål → abort.
- **new_keywords[]:** `keyword`, `match_type` (kun `exact`/`phrase` — aldrig Broad/blank), `campaign` +
  `ad_group` (begge kræves). Skrives `Status=Paused`.
- `level=account` → `<Account-level>`; `list_name` → negativliste-skema.

Output: `negative keywords.csv` og/eller `nye keywords.csv` (>1 fil → én `.zip`), UTF-8-med-BOM (Æ Ø Å
overlever i Editor + Excel). Brugeren importerer i Editor og trykker Send.

## 7C — Excel-overblik (efter `Excel-overblik`) — OPT-IN

Et farvekodet referat til klient/arkiv — ikke en import-fil, ikke en handling. Statisk (ingen FILTER-
formler):
```bash
python3 $LIB/build_xlsx.py --raw ~/Downloads/_st_raw.json --decisions <decisions.json> \
  --out "~/Downloads/Søgeterm-overblik - <klient> - <YYYY-MM-DD>.xlsx"
```
Tre faner: **Søgetermer** (hele den dømte liste, farvekodet — rød = blev negativ, grøn = tilføjet
keyword, grå = gennemgået), **Beslutninger**, **Temaer** (n-gram spild-/vinder-temaer). Farven er kun
en afspejling af de trufne beslutninger, ikke en ny dom. Kan laves alene eller oveni 7A/7B. Kræver
`openpyxl`.

## Afslut (alle veje)

Aflever en kort opsummering i chatten: hvad der blev tilføjet/skrevet (X negatives, Y keywords — og
hvordan: live/CSV/Excel), de vigtigste mønstre, og ærlige forbehold (opkald-attribution, små tal, ting
der skal verificeres). Tilføj `## Kilder` — de MCP-værktøjer + URL'er der faktisk blev brugt.
