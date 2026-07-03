---
name: inb-ads-change-log
description: Genererer en formatmatchet changelog-tekst til klientens Drive-optimeringslog ud fra Google Ads' egen ændringshistorik (change_event), enten per kunde eller per specialist på tværs af dennes konti, og leverer den read-only som en tekstblok til copy-paste frem for at skrive direkte til Drive.
---

# inb-ads-change-log

Byg en changelog-tekst direkte fra Google Ads' indbyggede ændringshistorik (`change_event`-ressourcen, samme data som **Værktøjer → Ændringshistorik** i UI'et), klar til at sætte ind i klientens optimeringslog/changelog på Drive.

Skillet automatiserer den faktuelle halvdel af changelog-arbejdet (hvad blev ændret, hvornår, af hvem). Mennesket tilføjer kun **hvorfor**.

Read-only mod Google Ads. Skillet henter og formaterer, men skriver hverken til kontoen eller til Drive (se Trin 0) - det leverer en tekstblok mennesket selv indsætter.

Fuld designbegrundelse: `SPEC.md` i denne mappe. Denne fil er den kørbare kontrakt.

## Hvornår

Triggerfraser: "lav changelog", "ads-ændringslog", "log hvad der er lavet på [kunde]", "hvad har [person] lavet", "hvad lavede Rikke i denne uge", "ugentlig ændringslog", "optimeringslog fra Ads", "log ændringerne", "changelog for [kunde]".

## Kontekst

To begreber:
- **change_event** = Google Ads' egen revisionslog over hver skrivning til kontoen (oprettet/opdateret/fjernet ressource, hvilke felter, hvornår, af hvilken bruger-email). Kontoens log, ikke teamets.
- **changelog / optimeringslog** = Doc'et på Drive hvor specialisten skriver hvad de lavede *og hvorfor*, plus off-platform arbejde (mails, møder, sheets). Menneskets arbejdslog.

`change_event` er en delmængde af changelog'ens konto-mutérende del, i finere kornstørrelse og uden "hvorfor". Skillet udkaster den faktuelle del fra `change_event` i changelog'ens eget format og lader mennesket fylde hvorfor + off-platform.

To hårde grænser fra API'et, som skal siges højt i outputtet:
1. **30-dages loft.** `change_event` rækker kun ~30 dage tilbage. `lookback_days` skal være ≤ 29 (30 kaster `START_DATE_TOO_OLD`). Tom periode = "ingen ændringer i vinduet", ikke "konto inaktiv". Det er det eneste sted API'et er ringere end changelog'en (som har fuld historik) - skillet er derfor et kør-på-skema-værktøj: snapshot før ændringerne falder ud af vinduet.
2. **Bulk-støj.** Én Editor-upload skriver mange `change_event`-rækker med samme timestamp (561 negative keywords = 1 indsæt, ikke 561 handlinger). Rå optælling overdriver arbejdet ~20x på bulk-dage. Kollaps altid på timestamp+ressourcetype og rapportér som én handling ("tilføjede negativ-liste (557 ord)").

## Trin 0 - Kontekst og skrivegrænse

Klientmapper findes på Drive via `search_files` scoped til klientmappen under `${user_config.inbound_root_folder_id}` (navnemønster + placering varierer per klient - se Trin 4). Enhver ekstern write er gated bag eksplicit bekræftelse (vis hvad og hvor, vent på `ja`, skriv så) - men dette skill skriver ikke selv. Alt på dansk medmindre brugeren skriver engelsk.

**Værktøjsgrænse der afgør leveringsformen:** Drive-connectoren kan kun oprette nye filer (`create_file`), ikke appende til eller redigere et eksisterende Doc. Skillet kan derfor ikke selv skrive ind i den eksisterende changelog. Leveringsformen er:

> **Udkast → mennesket indsætter.** Skillet producerer den præcise tekstblok (formatmatchet til changelog'en) + dokumentets navn/ID/sti, så specialisten åbner Doc'et og sætter blokken ind øverst under den aktuelle måned.

Fuldt i tråd med human-in-the-loop: alt det tunge (hente, filtrere, kollapse bulk, formatere) er automatiseret, kun det sidste tastetryk er menneskets. Hvis Drive-connectoren en dag får et append/update-værktøj, kan Trin 6 opgraderes til en gated skrivning (vis target-Doc + blok, vent på eksplicit `ja`, skriv, bekræft tilbage) - indtil da: udkast-til-indsæt.

Alt mod Google Ads er read-only.

## Trin 0.5 - Hent klient-kontekst (AI Context) først

Kør `../../shared/client-context-intake.md` som allerførste trin på en navngiven klient (identificér klient → åbn master-klientindekset → find rækken + Stage → åbn AI Context-filen). Læsning, aldrig gated, men obligatorisk - sådan arver du klientens ID'er, kontakter, hårde rammer, navngivningskonvention, budstrategi-norm, KPI'er og pausede-kampagner-intention i stedet for at starte blindt.

To ting der er specifikke for dette skill:
- **AI Context-filen linker klientens changelog/optimeringslog-Doc** - brug det link som **første kandidat i Trin 4**.
- **PER PERSON:** kør intaket per berørt kunde inden du resolver hver kundes changelog-Doc.

## Trin 1 - Intake (ét spørgsmål ad gangen)

**1a. Tilstand.** Spørg: "Er det en changelog for én kunde, eller alt hvad én person har lavet på tværs af sine konti?"
- PER KUNDE → gå til 1b-kunde.
- PER PERSON → gå til 1b-person.

**1b-kunde. Klientnavn.** Match mod `list_accessible_accounts` på kontonavn. Nogle konti ligger under sub-MCC'er og dukker ikke op der (den enumererer kun ét niveau) - i så fald bed om konto-ID'et direkte, eller find det via sub-MCC-traversal (`run_custom_gaql` mod manager-ID: `SELECT customer_client.id, customer_client.descriptive_name FROM customer_client`). Bekræft: "Fandt [Kontonavn] (ID: XXXXXXXXXX) - rigtig konto?"

**1b-person. Hvem.** Spørg om personens navn og bekræft email (Inbound-mønster: `rkj@inboundcph.dk` = Rikke, `cri@` = Caroline, `na@` = Nur osv. - bekræft den fulde email, ikke et gæt). Find personens konti via specialist-rosteren: den ligger i master-klientindeks-Doc'et (`1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`, hentet i Trin 0.5) med en ansvarlig specialist per klientrække; alternativt de lokale `clients/*.md` frontmatter-felter `responsible`. Kun personens egne konti, med mindre brugeren beder om andet (holder loopet lille: "deres bog", ikke "hvert tastetryk overalt"). En person kan have ændret på en konto de ikke står som ansvarlig på - det fanges kun ved den udtømmende variant (alle konti, filtreret på email).

**1c. Periode.** Tilbyd "Sidste 7 dage (standard for ugentlig)", "Sidste 24 timer", "Sidste 14 dage", "Sidste 30 dage", eller custom. Standard = sidste 7 dage. `lookback_days` ≤ 29 altid. Omsæt til et konkret vindue og vis det overalt (f.eks. "29. maj - 4. jun 2026").

**1d. Bekræft scope**, så: "Godt - jeg henter ændringshistorikken nu."

## Trin 2 - Dataindhentning (read-only)

Brug `get_change_history` (hurtig vej, ét kald per konto) eller `run_custom_gaql` mod `change_event` (når du skal filtrere på bruger server-side).

**PER KUNDE** - ét kald, ingen brugerfilter (vi vil have alle der rørte kontoen):

```sql
SELECT change_event.change_date_time, change_event.user_email,
       change_event.change_resource_type, change_event.resource_change_operation,
       change_event.changed_fields, campaign.name, ad_group.name
FROM change_event
WHERE change_event.change_date_time DURING LAST_7_DAYS    -- eller dit vindue (≤29 dage)
ORDER BY change_event.change_date_time DESC
LIMIT 9000
```

**PER PERSON** - loop over personens konti, brugerfilter server-side per konto:

```sql
SELECT change_event.change_date_time, change_event.user_email,
       change_event.change_resource_type, change_event.resource_change_operation,
       change_event.changed_fields, campaign.name, ad_group.name
FROM change_event
WHERE change_event.change_date_time DURING LAST_7_DAYS
  AND change_event.user_email = 'rkj@inboundcph.dk'        -- personens email
ORDER BY change_event.change_date_time DESC
LIMIT 9000
```

Feltregler (verificeret mod live data):
- **`change_date_time`** er sekund-præcist; brug `[0:10]` for dag, `[0:16]` for minut.
- **Bulk-kollaps:** grupper på (`change_date_time`, `change_resource_type`) - rækker med identisk timestamp + type = én bulk-handling. Tæl medlemmer for "(N ord/keywords)".
- **`user_email`** kan være en specialist, et eksternt bureau (f.eks. `navn@eksternt-bureau.com`), `Recommendations Auto-Apply`, eller `INTERNAL_TOOL`/"Low activity system bulk change". Bevar den ordret - "hvem" er en del af loggen. I PER KUNDE-tilstand: hvis ændringen er lavet af en anden end den primære specialist, annotér det som changelog'en allerede gør: "DD.MM.ÅÅ (Specialist)".
- **Stort svar:** tunge konti (bulk-dage) kan sprænge token-loftet. Hent da kun `change_date_time`, `change_resource_type`, `resource_change_operation`, `changed_fields` (drop campaign/ad_group navne) og aggregér, eller pagér. Rapportér aldrig et trunkeret tal som om det var fuldt.
- **`changed_fields`** afslører handlingens natur: `amountMicros` = budgetændring; `keyword.text` + `negative` = negativt keyword; `responsiveSearchAd.headlines` = annoncetekst-redigering; `status` = pause/aktivér.

## Trin 3 - Kollaps og klassificér til menneskelæsbare handlinger

Lav rå events om til den slags linjer et menneske ville skrive i changelog'en. Per konto, per dag:

1. **Kollaps bulk** (samme timestamp + ressourcetype) til én linje med antal.
2. **Oversæt ressourcetype + operation + changed_fields** til dansk handling:
   - `CAMPAIGN_BUDGET UPDATE amountMicros` → "Justerede budget på [kampagne]"
   - `CAMPAIGN_CRITERION CREATE ...negative` (bulk) → "Tilføjede negativ-keyword-liste (N ord) til [kampagne]"
   - `AD_GROUP_CRITERION CREATE keyword` → "Tilføjede keywords i [ad group]"
   - `AD UPDATE responsiveSearchAd.headlines` → "Redigerede annoncetekster i [ad group]"
   - `CAMPAIGN UPDATE status` → "Satte [kampagne] på pause / aktiverede den" (afgør ud fra kontekst hvis muligt; ellers "ændrede status på")
   - `ASSET CREATE` + `CAMPAIGN_ASSET` → "Tilføjede/skiftede assets i [kampagne]"
   - `*_CRITERION REMOVE` → "Fjernede keywords/målgruppe i [kampagne]"
3. **Grupper per dag**, nyeste dag øverst. Slå små relaterede handlinger på samme kampagne/dag sammen ("budgetjustering på 7 kampagner" frem for 7 linjer).
4. **Spring konti uden aktivitet over** (PER PERSON: nævn dem kort i chat-resuméet, men lav ingen changelog-blok for dem).

## Trin 4 - Find changelog-dokumentet (per kunde)

For hver konto med aktivitet: find klientens changelog/optimeringslog-Doc på Drive via connectoren. Navnemønstret og placeringen varierer per klient: "Optimeringslog", "changelog", "[Klient] Google Ads log", ofte inde i en **Paid Search**-mappe, men også under den ældre "Google/Bing Ads", "#4 - Google Ads", eller på klientmappens topniveau.

1. `search_files` efter navnemønster (`optimeringslog`, `changelog`, `ads log`) scoped til klientmappen under `${user_config.inbound_root_folder_id}`.
2. Hvis flere kandidater eller ingen sikker match: vis kandidaterne (navn + ID + mappesti) og bed mennesket bekræfte hvilket Doc før du udkaster. Et fejl-resolvet Doc korrumperer klientens log.
3. `read_file_content` på det bekræftede Doc for at aflæse dets format (måneds-headers, datoformat) og hvor "øverst under aktuelle måned" er, så blokken matcher.

### Fejlfinding - changelog-Doc'et

- **Flere changelog-docs (gammel + ny):** klienter migrerer ofte fra en ældre log ("Google/Bing Ads") til en nyere ("Optimeringslog") - begge kan stadig ligge i mappen. Skriv aldrig blindt i den nyeste. Vis begge kandidater (navn + ID + sti + sidst ændret) og bed mennesket bekræfte den aktive, før du udkaster. Prioritér AI Context-filens changelog-link som den kanoniske, hvis den peger på én.
- **Søgning giver ingen match:** udvid navnemønstret (`log`, `optimering`, `historik`) og søg bredere i klientmappen inkl. undermapper. Stadig intet: sig det, lever udkastet uden target-Doc (blokken er brugbar i sig selv), og bed mennesket pege på det rigtige Doc eller bekræfte at ingen log findes endnu. Opfind aldrig et Doc-ID.

## Trin 5 - Formatmatch (ikke et nyt format)

Match changelog'ens eksisterende stil (verificeret fra Capio-loggen som kanonisk eksempel):
- Omvendt kronologisk, nyeste øverst.
- **Måneds-header**: `## Juni 2026`. Hvis ny måned siden sidste indførsel: lav headeren.
- **Datolinje**: `DD.MM.YYYY` (f.eks. `04.06.2026`), derunder punktopstilling med handlingerne.
- Dansk, kort, faktuelt. Ingen emojis, ingen tankestreger (brug komma/kolon).
- **`_Hvorfor:_`-placeholder** til sidst i hver dato-blok, fordi API'et ikke kender hvorfor: `  - _Hvorfor: (udfyld - API'et fanger kun hvad, ikke hvorfor)_`.
- I PER KUNDE med flere forfattere: annotér ikke-primær forfatter i parentes på datolinjen ("(Rikke)"), som changelog'en gør.

Eksempel på en udkastet blok (Lime SE, Rikke, uge):

```
## Juni 2026

03.06.2026 (Rikke)
  - Tilføjede negativ-keyword-liste (557 ord) til NEW IC | GSN | Generic | LGOLCRM | SE
  - Justerede budget på 4 kampagner
  - _Hvorfor: (udfyld - API'et fanger kun hvad, ikke hvorfor)_
```

## Trin 6 - Lever udkast(ene) (ingen skrivning - mennesket indsætter)

Connectoren kan ikke appende til et eksisterende Doc (Trin 0), så skillet skriver ikke. I stedet:

**PER KUNDE** - ét udkast:
1. Vis det resolvede changelog-Doc: navn + ID + mappesti.
2. Vis den formatmatchede tekstblok i en kodeblok, klar til at kopiere.
3. Sig: *"Indsæt denne blok øverst under [måned] i changelog'en. Jeg kan ikke skrive til Doc'et selv (connectoren understøtter det ikke), så det er et copy-paste."*

**PER PERSON** - fan-out, ét udkast per berørt kunde:
1. List alle berørte kunder med deres resolvede changelog-Doc (navn + ID + sti).
2. Per kunde: den formatmatchede blok i sin egen kodeblok.
3. Et samlet chat-resumé øverst: "[Person] rørte N konti i [periode]: [liste]. Ingen aktivitet på: [liste]." plus den ærlige optælling (distinkte handlinger, ikke rå events).

Hvis Drive-connectoren senere får et append/update-værktøj: opgradér til en gated skrivning (vis target-Doc + blok, vent på eksplicit `ja`, skriv, bekræft tilbage). Vis altid hvert target-Doc - skriv aldrig et Doc der ikke er vist.

## Trin 7 - Output

Afslut med:
1. **Udkast(ene)** som ovenfor (per kunde, eller fan-out per person).
2. **Ærligt resumé:** distinkte handlinger pr. konto (ikke rå event-tal), berørte vs. uberørte konti, og perioden eksplicit.
3. **`## Datakilder`**: MCP-værktøjer kaldt (`get_change_history` / `run_custom_gaql` mod `change_event`, Drive `search_files` + `read_file_content`), konto-ID'er, og det konkrete dato-vindue.
4. **30-dages note:** mind om at alt før vinduet ikke kan hentes - kør skemalagt (ugentligt/dagligt) for at fange ændringer før de falder ud.
