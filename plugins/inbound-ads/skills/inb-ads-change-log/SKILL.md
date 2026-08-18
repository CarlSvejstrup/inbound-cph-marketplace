---
name: inb-ads-change-log
description: Skriver en kort, punktopstillet changelog-indførsel direkte ind i klientens Drive-optimeringslog via gated findAndReplaceInDoc, bygget på Google Ads' egen ændringshistorik (change_event), enten per kunde eller per specialist på tværs af dennes konti.
---

# inb-ads-change-log

Byg en kort, punktopstillet changelog-indførsel direkte fra Google Ads' indbyggede ændringshistorik (`change_event`-ressourcen, samme data som **Værktøjer → Ændringshistorik** i UI'et), og skriv den ind i klientens optimeringslog/changelog på Drive.

Skillet automatiserer den faktuelle halvdel af changelog-arbejdet (hvad blev ændret, hvornår, af hvem). Mennesket tilføjer kun **hvorfor**.

Read-only mod Google Ads. Skillet **skriver derimod direkte ind i changelog-Doc'et på Drive** via `findAndReplaceInDoc`, gated bag én eksplicit bekræftelse (se Trin 0 og Trin 6).

Fuld designbegrundelse: `SPEC.md` i denne mappe. Denne fil er den kørbare kontrakt.

## Hvornår

Triggerfraser: "lav changelog", "ads-ændringslog", "log hvad der er lavet på [kunde]", "hvad har [person] lavet", "hvad lavede Rikke i denne uge", "ugentlig ændringslog", "optimeringslog fra Ads", "log ændringerne", "changelog for [kunde]".

## Kontekst

To begreber:
- **change_event** = Google Ads' egen revisionslog over hver skrivning til kontoen (oprettet/opdateret/fjernet ressource, hvilke felter, hvornår, af hvilken bruger-email). Kontoens log, ikke teamets.
- **changelog / optimeringslog** = Doc'et på Drive hvor specialisten skriver hvad de lavede *og hvorfor*, plus off-platform arbejde (mails, møder, sheets). Menneskets arbejdslog.

`change_event` er en delmængde af changelog'ens konto-mutérende del, i finere kornstørrelse og uden "hvorfor". Skillet skriver den faktuelle del fra `change_event` ind i changelog'en i dens eget format og efterlader en `Hvorfor:`-bullet mennesket fylder ud, plus plads til off-platform arbejde.

To hårde grænser fra API'et, som skal siges højt i outputtet:
1. **30-dages loft.** `change_event` rækker kun ~30 dage tilbage. `lookback_days` skal være ≤ 29 (30 kaster `START_DATE_TOO_OLD`). Tom periode = "ingen ændringer i vinduet", ikke "konto inaktiv". Det er det eneste sted API'et er ringere end changelog'en (som har fuld historik) - skillet er derfor et kør-på-skema-værktøj: snapshot før ændringerne falder ud af vinduet.
2. **Bulk-støj.** Én Editor-upload skriver mange `change_event`-rækker med samme timestamp (561 negative keywords = 1 indsæt, ikke 561 handlinger). Rå optælling overdriver arbejdet ~20x på bulk-dage. Kollaps altid på timestamp+ressourcetype og rapportér som én handling ("tilføjede negativ-liste (557 ord)").

## Trin 0 - Kontekst og skrivegrænse

Klientmapper findes på Drive via `search` scoped til klientmappen under `${user_config.inbound_root_folder_id}` (navnemønster + placering varierer per klient - se Trin 4). Alt på dansk medmindre brugeren skriver engelsk.

**Skrivegrænse.** Skillet skriver ind i klientens eksisterende changelog-Doc med to inline-værktøjer på den Inbound Google Drive MCP (`mcp__acc7a973-...`), begge **indeks-frie**:

- **`findAndReplaceInDoc`** placerer blokken (samme surgiske vej som `inb-ads-client-brief` bruger på AI-Context-filen).
- **`createParagraphBullets`** med `textToFind` gør de indsatte linjer til **native Google Docs-bullets**.

Connectoren har også `insertText`, men det kræver et beregnet 1-baseret **indeks** i Doc'et. Brug det ikke her: forkert indekstælling lander tekst midt i et afsnit i en levende klientlog, og de to værktøjer ovenfor løser opgaven uden indeksregning. Samme grund til at `updateGoogleDoc` og `updateDocFromMarkdown` er forbudte - `replace` sletter hele loggen, og `append` lander nederst, mens changelog'en er omvendt kronologisk.

To konsekvenser, som styrer Trin 4 og Trin 6:

- **Doc'et skal være et native Google Doc.** `findAndReplaceInDoc` kan ikke redigere en rå `.md` eller en `.docx`. Er changelog'en ikke et native Doc, falder skillet tilbage til copy-paste-levering og siger det højt (Trin 6, fallback).
- **`findAndReplaceInDoc` kan ikke indsætte, kun erstatte.** Ny tekst foldes derfor ind i en erstatning af et **unikt anker**: erstat ankeret med "ankeret + den nye blok". Det er bevidst valgt frem for `insertText`, netop for at undgå indeksregning. Ankervalg i Trin 6.

**Human-in-the-loop er hård:** vis target-Doc (navn + ID + link) plus den præcise blok, vent på et eksplicit `ja`, skriv så, og bekræft tilbage. Ét gate-spørgsmål per Doc, ikke per linje. Skriv aldrig et Doc du ikke har vist. Opret aldrig en dublet-fil for at "rette" en fejlet skrivning.

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

### Kortheds-reglerne (hårde - de afgør outputtets kvalitet)

Changelog'en skal kunne skimmes på ti sekunder. Derfor:

- **Én bullet = én handling = én linje.** Aldrig prosa, aldrig to sætninger i samme bullet, aldrig en bullet der fortsætter på næste linje. (Bullets bliver native Docs-bullets i Trin 6; her handler det kun om indholdet.)
- **Max 6 bullets per dato.** Er der flere, rul de mindste sammen til én ("øvrige justeringer: bud på 12 keywords, 3 assets skiftet").
- **Max ~10 ord per bullet.** Start med et udsagnsord i datid (Tilføjede, Justerede, Pausede, Fjernede, Redigerede). Ingen indledende fyld ("Jeg har i dag...", "Der blev...").
- **Ét kampagnenavn per bullet, forkortet.** Er navnet langt, klip til det genkendelige led (`NEW IC | GSN | Generic | LGOLCRM | SE` → `GSN Generic SE`). Er handlingen på tværs af flere, skriv antallet ("på 4 kampagner") frem for at liste dem.
- **Ingen tal uden betydning.** Behold antal der viser omfang (557 negative ord), drop dem der ikke gør (event-ID'er, micros, ressourcenavne).
- **Ingen plumbing.** Aldrig `change_event`-feltnavne, enums (`CAMPAIGN_CRITERION`), ressource-stier eller `amountMicros` i den skrevne blok.

## Trin 4 - Find changelog-dokumentet (per kunde)

For hver konto med aktivitet: find klientens changelog/optimeringslog-Doc på Drive via connectoren. Navnemønstret og placeringen varierer per klient: "Optimeringslog", "changelog", "[Klient] Google Ads log", ofte inde i en **Paid Search**-mappe, men også under den ældre "Google/Bing Ads", "#4 - Google Ads", eller på klientmappens topniveau.

1. `search` efter navnemønster (`optimeringslog`, `changelog`, `ads log`) scoped til klientmappen under `${user_config.inbound_root_folder_id}`. Prioritér AI Context-filens changelog-link (Trin 0.5) som første kandidat.
2. Hvis flere kandidater eller ingen sikker match: vis kandidaterne (navn + ID + mappesti + sidst ændret) og bed mennesket bekræfte hvilket Doc, **før** du skriver. Et fejl-resolvet Doc korrumperer klientens log.
3. **Verificér filtypen.** `findAndReplaceInDoc` virker kun på et native Google Doc (`application/vnd.google-apps.document`). Læs mimetype fra søgeresultatet, eller kald `getDocumentInfo` på ID'et. Er det en `.docx`, en rå `.md` eller et Sheet: skriv ikke - gå til Trin 6's fallback (copy-paste) og sig hvorfor.
4. `readGoogleDoc` på det bekræftede Doc for at aflæse:
   - **formatet**: måneds-header-stil, datoformat, og om loggens eksisterende handlingslinjer bruger native bullets (og i så fald hvilket preset - match det i Trin 6, ellers `BULLET_DISC_CIRCLE_SQUARE`);
   - **ankeret**: den præcise tekst der markerer "øverst under aktuelle måned" (se Trin 6);
   - **dubletter**: står dagens dato allerede i loggen? Så udvid den eksisterende dato-blok i stedet for at lave en ny.

### Fejlfinding - changelog-Doc'et

- **Flere changelog-docs (gammel + ny):** klienter migrerer ofte fra en ældre log ("Google/Bing Ads") til en nyere ("Optimeringslog") - begge kan stadig ligge i mappen. Skriv aldrig blindt i den nyeste. Vis begge kandidater (navn + ID + sti + sidst ændret) og bed mennesket bekræfte den aktive, før du udkaster. Prioritér AI Context-filens changelog-link som den kanoniske, hvis den peger på én.
- **Søgning giver ingen match:** udvid navnemønstret (`log`, `optimering`, `historik`) og søg bredere i klientmappen inkl. undermapper. Stadig intet: sig det, lever udkastet uden target-Doc (blokken er brugbar i sig selv), og bed mennesket pege på det rigtige Doc eller bekræfte at ingen log findes endnu. Opfind aldrig et Doc-ID.

## Trin 5 - Formatmatch (kort + punktopstillet)

Match changelog'ens eksisterende stil (verificeret fra Capio-loggen som kanonisk eksempel), og hold blokken kort:

- Omvendt kronologisk, nyeste øverst.
- **Måneds-header**: `Juni 2026`. Findes headeren for den aktuelle måned ikke i Doc'et, skal den med i blokken (se ankervalg i Trin 6).
- **Datolinje**: `DD.MM.YYYY` (fx `04.06.2026`), derunder **kun punktopstilling** - én bullet per handling, jf. kortheds-reglerne i Trin 3.
- **Bullets bliver native Google Docs-bullets**, ikke bogstavelige bindestreger. Selve indsættelsen sker som rene tekstlinjer (én handling per linje, uden `- ` foran); bagefter gør `createParagraphBullets` dem til rigtige bullets (Trin 6, trin 3). Skriv derfor ALDRIG `- ` i `replaceText` - så ender du med en bindestreg *inde i* en native bullet.
- Dansk, kort, faktuelt. Ingen emojis, ingen tankestreger (brug komma/kolon). Æ Ø Å skrives som rigtige bogstaver, aldrig `ae`/`oe`/`aa`.
- **`Hvorfor:`-bullet** til sidst i hver dato-blok, fordi API'et ikke kender hvorfor: linjen `Hvorfor: (udfyld)`, bulletiseret sammen med de øvrige. Én bullet, ikke en sektion.
- I PER KUNDE med flere forfattere: annotér ikke-primær forfatter i parentes på datolinjen ("(Rikke)"), som changelog'en gør.
- **Ingen indledning, ingen opsummering, ingen note om værktøjet inde i Doc'et.** Alt meta (30-dages loft, datakilder, optælling) hører i chatten, ikke i klientens log.

Teksten du indsætter (rene linjer, ingen bindestreger - Lime SE, Rikke, uge):

```
03.06.2026 (Rikke)
Tilføjede negativ-liste (557 ord) til GSN Generic SE
Justerede budget på 4 kampagner
Pausede GSN Brand SE
Hvorfor: (udfyld)
```

Sådan ser det ud i Doc'et efter bulletiseringen (datolinjen forbliver almindelig tekst, de fire handlingslinjer bliver native bullets):

```
03.06.2026 (Rikke)
  • Tilføjede negativ-liste (557 ord) til GSN Generic SE
  • Justerede budget på 4 kampagner
  • Pausede GSN Brand SE
  • Hvorfor: (udfyld)
```

## Trin 6 - Skriv blokken ind i changelog-Doc'et (gated, KUN findAndReplaceInDoc)

Skrivningen sker i to indeks-frie kald på den Inbound Google Drive MCP (`mcp__acc7a973-...`): først **`findAndReplaceInDoc`** der placerer teksten, så **`createParagraphBullets`** der gør handlingslinjerne til native bullets. Brug hverken `insertText` (kræver indeksregning), `updateGoogleDoc` eller `updateDocFromMarkdown` (sletter loggen hhv. lander nederst).

`findAndReplaceInDoc` kan ikke indsætte, kun erstatte, så placeringen bliver **en erstatning af et unikt anker**: `findText` = ankeret, `replaceText` = "den nye blok + ankeret" (blokken skal øverst, så den kommer *før* ankeret).

### Ankervalg (i denne rækkefølge)

1. **Måneds-headeren for den aktuelle måned findes** → anker = headerlinjen.
   `findText`: `Juni 2026`
   `replaceText`: `Juni 2026\n\n<ny blok>`
2. **Måneden findes ikke** (ny måned siden sidste indførsel) → anker = den nuværende øverste måneds-header, og den nye måned lægges foran.
   `findText`: `Maj 2026`
   `replaceText`: `Juni 2026\n\n<ny blok>\n\nMaj 2026`
3. **Dagens dato står allerede i loggen** → anker = den eksisterende datolinje, og de nye bullets lægges *efter* den (udvid blokken frem for at lave en dublet-dato).
   `findText`: `03.06.2026 (Rikke)`
   `replaceText`: `03.06.2026 (Rikke)\n<nye bullets>`
4. **Doc'et er tomt eller har ingen brugbar struktur** → anker = dokumentets titel-/overskriftslinje, blokken lægges under den. Er der intet unikt anker overhovedet: gå til fallback.

Ankeret skal matche **præcis én gang**. Kør altid `findAndReplaceInDoc` med `dryRun=true` først og læs antal matches: 0 → vælg et andet anker; >1 → udvid `findText` med omkringliggende kontekst til det er unikt. Skriv aldrig på et anker du ikke har dry-run'et.

### Skrivesekvensen (efter godkendelse)

1. **`findAndReplaceInDoc`** med `dryRun=true` på ankeret. Bekræft præcis ét match.
2. **`findAndReplaceInDoc`** rigtigt: `findText` = ankeret, `replaceText` = blokken (rene linjer, ingen `- `) + ankeret, jf. ankervalget ovenfor.
3. **`createParagraphBullets`** per indsat handlingslinje: `textToFind` = linjens egen tekst (den er unik nok - den er lige skrevet), `bulletPreset` = det preset resten af loggen bruger, ellers `BULLET_DISC_CIRCLE_SQUARE`. **Bulletisér kun handlingslinjerne + `Hvorfor:`-linjen** - datolinjen og måneds-headeren skal forblive almindelig tekst.
4. **Verificér** med `readGoogleDoc` at blokken står ét sted, under den rigtige måned, med bullets. Gør den ikke det, sig det ordret - ryd aldrig op med et nyt gæt-kald.

Fejler trin 3 (bulletiseringen), er teksten allerede skrevet og korrekt placeret: sig at bullets ikke kunne påføres, og lad blokken stå som rene linjer. Rul aldrig trin 2 tilbage for at "prøve igen".

### Gaten (obligatorisk, ét spørgsmål per Doc)

Vis, før du skriver:
1. **Target-Doc**: navn + ID + link + mappesti.
2. **Ankeret** du erstatter, og hvor blokken lander ("øverst under Juni 2026").
3. **Den præcise blok** i en kodeblok, vist som den kommer til at se ud i Doc'et (dvs. med bullets, jf. Trin 5's andet eksempel) - ikke som de rene indsættelseslinjer. Mennesket skal kunne genkende resultatet, ikke mekanikken.
4. Spørg: *"Skriver jeg denne blok ind i [Doc-navn]? (ja/nej)"*

Skriv først på et eksplicit `ja`. Derefter: kør skrivesekvensen ovenfor, og **bekræft tilbage** med link til Doc'et og antal erstatninger. Fejler kaldet, sig det ordret og skift til fallback - lav aldrig en ny fil, og forsøg aldrig et bredere `findText` uden at spørge igen.

### PER PERSON - fan-out

Ét Doc, ét anker, én gate, én skrivning **per berørt kunde**. Kør dem sekventielt og bekræft hver for sig; batch aldrig flere Docs bag ét `ja`. Kunder uden aktivitet får ingen skrivning og nævnes kun i chat-resuméet.

### Fallback - copy-paste (når skrivning ikke er mulig)

Falder tilbage til udkast-til-indsæt hvis: Doc'et ikke er et native Google Doc, intet unikt anker kan findes, `findAndReplaceInDoc` fejler, changelog-Doc'et slet ikke kan resolves, eller mennesket svarer nej. Så: lever blokken i en kodeblok - her MED `- ` foran hver handlingslinje, så den er brugbar som copy-paste - sig hvorfor der ikke blev skrevet, og hvor den skal indsættes. Blokken er brugbar i sig selv.

(En fejlet bulletisering er derimod ikke en fallback-grund: teksten står rigtigt, kun formateringen mangler.)

## Trin 7 - Output

Afslut med:
1. **Skrive-udfald:** hvilke Docs der blev skrevet (navn + link + antal erstatninger), og hvilke der faldt tilbage til copy-paste og hvorfor.
2. **Ærligt resumé:** distinkte handlinger pr. konto (ikke rå event-tal), berørte vs. uberørte konti, og perioden eksplicit.
3. **`## Datakilder`**: MCP-værktøjer kaldt (`get_change_history` / `run_custom_gaql` mod `change_event`, Drive `search` + `readGoogleDoc` + `findAndReplaceInDoc` + `createParagraphBullets`), konto-ID'er, og det konkrete dato-vindue.
4. **30-dages note:** mind om at alt før vinduet ikke kan hentes - kør skemalagt (ugentligt/dagligt) for at fange ændringer før de falder ud.

**Form på chat-svaret (IKKE selve changelog-blokkene):** de skrevne blokke skal blive ved med at være
**formatmatchede til klientens egen log** (Trin 5) - dét er en hård regel og røres ikke af noget her. Men
teksten *rundt om* dem i chatten følger Inbounds **report house style** (beskrevet inline her; dybere
forfatter-vejledning i `inbound-skill-creator`) i komprimeret form: led med en **verdikt-linje**
(status-chip + "N ændringer i perioden, netto-effekt") foran blokken, og lever resumé (punkt 2) og
datakilder (punkt 3) som en skanbar footer. Skjul plumbing (`change_event`-felter, resource-type-enums)
- oversæt til handlinger i menneskesprog, som skillet allerede gør. Status-pills på resuméet:
🟢 skrevet · 🟠 delvis (kilde fejlede, eller copy-paste-fallback) · 🔵 info. Dette skill er som standard
**kun i chatten** (gate + bekræftelse); ingen artifact-variant. Æ Ø Å altid.
