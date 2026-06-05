---
name: ads-aendringslog
description: Generér en changelog-/optimeringslog-tekst fra Google Ads' egen ændringshistorik (change_event) for en periode, og udkast den klar til at sætte ind i klientens changelog på Drive. To tilstande - (1) PER KUNDE - alle ændringer på én konto i perioden, eller (2) PER PERSON - alt hvad én specialist (f.eks. Rikke) har lavet på tværs af sine konti, fanet ud til hver kundes changelog. Kollapser bulk-uploads til én linje (561 events = "tilføjede negativ-liste (557 ord)"), bevarer hvem der lavede ændringen (også eksterne bureauer/Google-anbefalinger), og tilføjer en _Hvorfor:_-placeholder fordi API'et kun kender "hvad", ikke "hvorfor". Read-only mod Google Ads. Skriver IKKE til Drive selv (connectoren kan ikke appende til et eksisterende Doc) - leverer en formatmatchet tekstblok som mennesket sætter ind. Kan køres dagligt/ugentligt. Brug når brugeren siger "lav changelog", "ads-ændringslog", "log hvad der er lavet på [kunde]", "hvad har [person] lavet i denne uge", "ugentlig ændringslog", "optimeringslog fra Ads", eller "log ændringerne". Svarer på dansk.
---

# ads-aendringslog

Byg en changelog-tekst direkte fra Google Ads' indbyggede ændringshistorik (`change_event`-ressourcen, samme data som **Værktøjer → Ændringshistorik** i UI'et), og lever den klar til at sætte ind i klientens optimeringslog/changelog på Drive.

Skillet løser det Inbound-teamet allerede gør manuelt: føre changelog. I dag afhænger kvaliteten af at specialisten husker at skrive hvad de lavede. Dette skill fylder **den faktuelle halvdel** (hvad blev ændret, hvornår, af hvem) automatisk, så mennesket kun skal tilføje **hvorfor**.

Read-only mod Google Ads. Skillet henter og formaterer. Det **skriver ikke** til kontoen, og det **skriver ikke** til Drive (se Trin 0 om hvorfor) - det leverer en tekstblok mennesket selv indsætter.

Fuld designbegrundelse: `SPEC.md` i denne mappe. Denne fil er den kørbare kontrakt.

## Hvornår

Triggerfraser: "lav changelog", "ads-ændringslog", "log hvad der er lavet på [kunde]", "hvad har [person] lavet", " hvad lavede Rikke i denne uge", "ugentlig ændringslog", "optimeringslog fra Ads", "log ændringerne", "changelog for [kunde]".

## Kontekst (læs før noget andet)

To begreber:
- **change_event** = Google Ads' egen revisionslog over hver skrivning til kontoen (oprettet/opdateret/fjernet ressource, hvilke felter, hvornår, af hvilken bruger-email). Det er ikke teamets changelog - det er kontoens.
- **changelog / optimeringslog** = det Doc på Drive hvor specialisten skriver hvad de lavede *og hvorfor* (plus alt det off-platform arbejde: mails, møder, sheets). Det er menneskets arbejdslog.

Forholdet: `change_event` ⊆ den konto-mutérende delmængde af changelog'en, men i finere kornstørrelse og uden "hvorfor". Skillet bygger bro: det udkaster den faktuelle del fra `change_event` i changelog'ens eget format, og lader mennesket fylde hvorfor + off-platform.

### To hårde grænser fra API'et (sig dem altid højt i outputtet)

1. **30-dages loft.** `change_event` rækker kun ~30 dage tilbage. `lookback_days` SKAL være ≤ 29 (30 kaster `START_DATE_TOO_OLD`). Der er ingen vej længere tilbage. Tom periode = "ingen ændringer i vinduet", IKKE "konto inaktiv". Dette er det ene sted API'et er ringere end changelog'en (som har fuld historik), så skillet er et **kør-på-skema**-værktøj: snapshot før ændringerne falder ud af vinduet.
2. **Bulk-støj.** Én Editor-upload skriver mange `change_event`-rækker med **samme timestamp** (561 negative keywords = 1 indsæt, ikke 561 handlinger). Rå optælling overdriver arbejdet ~20x på bulk-dage. Kollaps altid på timestamp+ressourcetype og rapportér som én handling ("tilføjede negativ-liste (557 ord)").

## Trin 0 - Kontekst og skrivegrænse

Læs `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` (skrivegate + sprogpolitik) og `${CLAUDE_PLUGIN_ROOT}/context/drive-map.md` (hvordan klientmapper findes på Drive) først.

**Vigtig værktøjsgrænse (afgør hele leveringsformen):** Drive-connectoren kan **kun oprette nye filer** (`create_file`), ikke appende til eller redigere et eksisterende Doc. Der findes intet `update`/`append`-værktøj til Drive. Derfor kan skillet **ikke** selv skrive ind i den eksisterende changelog. Leveringsformen er derfor:

> **Udkast → mennesket indsætter.** Skillet producerer den præcise tekstblok (formatmatchet til changelog'en) + dokumentets navn/ID/sti, så specialisten åbner Doc'et og sætter blokken ind øverst under den aktuelle måned.

Dette er fuldt i tråd med human-in-the-loop-reglen: alt det tunge (hente, filtrere, kollapse bulk, formatere) er automatiseret; kun det sidste tastetryk er menneskets. Hvis Drive-connectoren en dag får et append/update-værktøj, kan Trin 6 opgraderes til en gated skrivning efter den firetrins-godkendelsesproces i CLAUDE.md - indtil da: udkast-til-indsæt.

Alt mod Google Ads er read-only.

## Trin 1 - Intake (ét spørgsmål ad gangen)

**1a. Tilstand.** Spørg: "Er det en **changelog for én kunde**, eller **alt hvad én person har lavet** på tværs af sine konti?"
- **PER KUNDE** → gå til 1b-kunde.
- **PER PERSON** → gå til 1b-person.

**1b-kunde. Klientnavn.** Match mod `list_accessible_accounts` på kontonavn. Bemærk: nogle konti ligger under sub-MCC'er og dukker ikke op i `list_accessible_accounts` (den enumererer kun ét niveau). Hvis kunden ikke findes der, så bed om konto-ID'et direkte, eller find det via sub-MCC-traversal (`run_custom_gaql` mod manager-ID: `SELECT customer_client.id, customer_client.descriptive_name FROM customer_client`). Bekræft: "Fandt [Kontonavn] (ID: XXXXXXXXXX) - rigtig konto?"

**1b-person. Hvem.** Spørg om personens navn og bekræft email (Inbound-mønster: `rkj@inboundcph.dk` = Rikke, `cri@` = Caroline, `na@` = Nur, osv. - bekræft den fulde email, ikke et gæt). Find personens konti: brug listen over Inbound-konti og deres ansvarlige specialist. **Kun personens egne konti** med mindre brugeren beder om andet (det holder loopet lille og er det rigtige mentale billede: "deres bog", ikke "hvert tastetryk overalt"). Bemærk eksplicit at en person *kan* have ændret på en konto de ikke står som ansvarlig på - den fanges kun hvis man kører den udtømmende variant (alle konti, filtreret på email).

**1c. Periode.** Tilbyd "Sidste 7 dage (standard for ugentlig)", "Sidste 24 timer", "Sidste 14 dage", "Sidste 30 dage", eller custom. **Standard = sidste 7 dage.** `lookback_days` ≤ 29 altid. Omsæt til et konkret vindue og vis det overalt (sig "29. maj - 4. jun 2026" i outputtet og i changelog-blokken).

**1d. Bekræft scope**, så: "Godt - jeg henter ændringshistorikken nu."

## Trin 2 - Dataindhentning (read-only)

Brug `get_change_history` (hurtig vej, ét kald per konto) eller `run_custom_gaql` mod `change_event` (når du skal filtrere på bruger server-side - bekræftet at virke).

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

### Feltregler (verificeret mod live data)
- **`change_date_time`** er sekund-præcist; brug `[0:10]` for dag, `[0:16]` for minut.
- **Bulk-kollaps:** grupper på (`change_date_time`, `change_resource_type`) - rækker med identisk timestamp + type = én bulk-handling. Tæl medlemmer for "(N ord/keywords)".
- **`user_email`** kan være en person (`cri@inboundcph.dk`), et eksternt bureau (`toufik.charef@upscale-ads.com`, `adam.malmstedt@mildmedia.se`), `Recommendations Auto-Apply`, eller `INTERNAL_TOOL`/"Low activity system bulk change". **Bevar den ordret** - "hvem" er en del af loggen. I PER KUNDE-tilstand: hvis ændringen er lavet af en ANDEN end den primære specialist, annotér det (som changelog'en allerede gør: "26.02.26 (Rikke)").
- **Stort svar:** tunge konti (bulk-dage) kan sprænge token-loftet. Hent da kun `change_date_time`, `change_resource_type`, `resource_change_operation`, `changed_fields` (drop campaign/ad_group navne) og aggregér; eller pagér. Rapportér aldrig et trunkeret tal som om det var fuldt.
- **`changed_fields`** afslører handlingens natur: `amountMicros` = budgetændring; `keyword.text` + `negative` = negativt keyword; `responsiveSearchAd.headlines` = annoncetekst-redigering; `status` = pause/aktivér.

## Trin 3 - Kollaps + klassificér til menneskelæsbare handlinger

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
3. **Grupper per dag**, nyeste dag øverst. Slå små relaterede handlinger på samme kampagne/dag sammen til én linje hvor det giver mening ("budgetjustering på 7 kampagner" frem for 7 linjer).
4. **Spring konti uden aktivitet over** (i PER PERSON: nævn dem kort i chat-resuméet, men lav ingen changelog-blok for dem).

## Trin 4 - Find changelog-dokumentet (per kunde)

For hver konto med aktivitet: find klientens changelog/optimeringslog-Doc på Drive via connectoren. **Navnemønstret og placeringen varierer per klient** (set i praksis): "Optimeringslog", "changelog", "[Klient] Google Ads log", ofte inde i en **Paid Search**-mappe, men også under den ældre **"Google/Bing Ads"**, **"#4 - Google Ads"**, eller på klientmappens topniveau.

Fremgang:
1. `search_files` efter navnemønster (`optimeringslog`, `changelog`, `ads log`) scoped til klientmappen under `${user_config.inbound_root_folder_id}`.
2. Hvis flere kandidater eller ingen sikker match: **vis kandidaterne (navn + ID + mappesti) og bed mennesket bekræfte hvilket Doc** før du udkaster. Et fejl-resolvet Doc er præcis det der korrumperer en klients log.
3. `read_file_content` på det bekræftede Doc for at aflæse dets format (måneds-headers, datoformat) og hvor "øverst under aktuelle måned" er - så blokken matcher.

## Trin 5 - Formatmatch (skriv IKKE et nyt format)

Match changelog'ens eksisterende stil (verificeret fra Capio-loggen som kanonisk eksempel):
- **Omvendt kronologisk, nyeste øverst** (bekræftet i plugin-CLAUDE.md's memory-ordning også).
- **Måneds-header**: `## Juni 2026`. Hvis ny måned siden sidste indførsel: lav headeren.
- **Datolinje**: `DD.MM.YYYY` (f.eks. `04.06.2026`), derunder punktopstilling med handlingerne.
- **Dansk**, kort, faktuelt. Ingen emojis, ingen tankestreger (brug komma/kolon).
- **`_Hvorfor:_`-placeholder** til sidst i hver dato-blok, fordi API'et ikke kender hvorfor: `  - _Hvorfor: (udfyld - API'et fanger kun hvad, ikke hvorfor)_`.
- I PER KUNDE med flere forfattere: annotér ikke-primær forfatter i parentes på datolinjen, præcis som changelog'en gør ("(Rikke)").

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
1. Vis det resolvede changelog-Doc: **navn + ID + mappesti** (så mennesket åbner det rigtige).
2. Vis den formatmatchede tekstblok i en kodeblok, klar til at kopiere.
3. Sig: *"Indsæt denne blok øverst under [måned] i changelog'en. Jeg kan ikke skrive til Doc'et selv (connectoren understøtter det ikke), så det er et copy-paste."*

**PER PERSON** - fan-out, ét udkast per berørt kunde:
1. List **alle** berørte kunder med deres resolvede changelog-Doc (navn + ID + sti).
2. Per kunde: den formatmatchede blok i sin egen kodeblok.
3. Et samlet chat-resumé øverst: "[Person] rørte N konti i [periode]: [liste]. Ingen aktivitet på: [liste]." plus den ærlige optælling (distinkte handlinger, ikke rå events).

Hvis Drive-connectoren senere får et append/update-værktøj: opgradér dette trin til den gated firetrins-skrivning fra CLAUDE.md (vis target-Doc + blok, vent på eksplicit `ja`, skriv, bekræft tilbage). Vis ALTID hvert target-Doc - skriv aldrig et Doc der ikke er vist.

## Trin 7 - Output

Afslut med:
1. **Udkast(ene)** som ovenfor (per kunde, eller fan-out per person).
2. **Ærligt resumé:** distinkte handlinger pr. konto (ikke rå event-tal), berørte vs. uberørte konti, og perioden eksplicit.
3. **`## Datakilder`**: MCP-værktøjer kaldt (`get_change_history` / `run_custom_gaql` mod `change_event`, Drive `search_files` + `read_file_content`), konto-ID'er, og det konkrete dato-vindue.
4. **30-dages note:** mind om at alt før vinduet ikke kan hentes - kør skemalagt (ugentligt/dagligt) for at fange ændringer før de falder ud.

## Regler
- Read-only mod Google Ads. Skriver aldrig til kontoen.
- **Skriver ikke til Drive** (connectoren kan ikke appende) - leverer udkast til indsæt. Hvis det ændrer sig: fuld gated firetrins-skrivning, vis target-Doc først.
- **Kollaps altid bulk** (samme timestamp+type = én handling). Rapportér aldrig 561 rå events som 561 handlinger.
- **30-dages loft:** `lookback_days` ≤ 29. Tomt vindue = "ingen ændringer i perioden", aldrig "inaktiv".
- **Bevar "hvem" ordret** - også eksterne bureauer, Google-anbefalinger, system-bulk. Annotér ikke-primær forfatter i PER KUNDE.
- **PER PERSON: kun personens egne konti** med mindre andet bedes om.
- **Formatmatch det eksisterende Doc** - find det, aflæs dets stil, match måneds-header + datoformat + dansk. Skab ikke et nyt format.
- **Resolv changelog-Doc'et eksplicit** og bekræft mod mennesket ved tvivl - et fejl-resolvet Doc korrumperer en klients log.
- **`_Hvorfor:_`-placeholder altid** - API'et leverer hvad, mennesket leverer hvorfor.
- Dansk. Ingen emojis. Ingen tankestreger (komma, kolon, eller omformulér).
- Marker manglende/utroværdige data eksplicit. Opfind aldrig ændringer.
