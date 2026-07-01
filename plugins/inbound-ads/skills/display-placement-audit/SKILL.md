---
name: display-placement-audit
description: Audit en kundes LIVE Google Ads Display-placeringer (websites, apps, YouTube-kanaler/videoer) for uønskede/junk-placeringer - gambling, MFA/clickbait, low-quality apps - og foreslå negative placeringer klar til at skrive direkte til kontoen. Scorer HVER placering 0-100 ud fra gratis lokale signaler (bundlet blocklist, risikable TLD'er, konto-performance, app-netværk), løser de fleste sager uden nettet, og bruger kun et loft-begrænset websøg på de reelt tvivlsomme (ikke alle). Leverer en rangeret markdown-rapport i chatten (IKKE .xlsx som default), lader eksperten redigere/fjerne rækker, og skriver FØRST til kontoen efter eksplicit bekræftelse - via ads-writer-agenten, MED et ærligt fald-tilbage til manuel Editor-liste hvis Google Ads MCP'en ikke har en write-vej for den konkrete placeringstype. Bygger INGEN permanent/delt negativliste - kun de bekræftede negativer for netop denne kørsel. PMax-fund er forslag-kun (API'en understøtter ikke direkte placement-exclusion på PMax). Brug når brugeren siger "display-placeringer", "GDN-audit", "hvor kører vores display-annoncer", "find gambling/betting placeringer", "uønskede sites", "placement-audit", "ekskluder junk-placeringer", "tjek Display Network", eller vil rydde op i hvor en klients bannerannoncer bliver vist. Svarer på dansk.
---

# display-placement-audit

Find ud af **hvor** en klients Display-annoncer (og Performance Max, hvor synligt) rent faktisk
bliver vist på tværs af Googles annoncenetværk, score hver placering for junk-risiko, og — efter
eksplicit bekræftelse — ekskludér de bekræftede fra kontoen. Dette er skillets første version, der
faktisk skriver til en Google Ads-konto (via `ads-writer`), ikke kun anbefaler.

## Hvorfor skillet er formet sådan (læs dette først)

Display Network-annoncer vises ikke på Googles søgeresultater — de vises på tredjeparts-websites,
apps og YouTube, valgt af Googles algoritme ud fra targeting, ikke en søgning. Algoritmen har ikke
altid god smag: en live-verificering mod en rigtig Inbound-konto (Dantaxi, 2026-07-01) viste
Display-annoncer kørende på `euro-jackpot.net`, `danskelotto.com` (lotteri), `petsim99.co`
(børne-spil-site) og en håndfuld content-farm-domæner — alt sammen reelt forbrug uden en eneste
konvertering. Det er ikke en hypotetisk risiko, det sker lige nu på tværs af konti.

**Scoring, ikke en binær dom.** Hver placering får et 0-100 risiko-tal bygget additivt af billige
lokale signaler (`scripts/score_placements.py` — se Trin 3). Tre bånd styrer hvor meget arbejde der
lægges i hver placering:

- **Høj (≥70 som standard):** afgøres af lokale data alene, intet opslag nødvendigt.
- **Lav (<30 som standard):** afgøres af lokale data alene, intet opslag nødvendigt.
- **Usikker (30-69):** den ENESTE gruppe der udløser et websøg — og selv der kun for de øverste
  ~15-20 (efter forbrug), for at holde omkostningen nede. Resten af den usikre gruppe markeres
  "kræver manuel gennemgang" i stedet for at blive gættet på.

Grænserne (70/30) og loftet (15-20) er **parametre eksperten kan justere per kørsel** ("vær
strengere denne gang"), ikke faste konstanter gemt i logik.

**Ingen permanent negativliste bygges af dette skill.** Bruger har ikke pt. mandat til at
etablere en organisation-bred standard-ekskluderingsliste — det er en større beslutning end dette
skill tager for brugeren. Blocklisten, TLD-reglerne og scoringslogikken bor **bundlet inde i
skillet** (`references/junk_domains.tsv`), ikke skrevet ud til en delt Google Ads shared_set
automatisk. Hver kørsel er selvstændig: læser 90 dages data, scorer med skillets egne bundlede
regler, viser rapporten, og skriver KUN de specifikke negativer eksperten bekræfter for netop den
kørsel. Vil eksperten proppe de bekræftede negativer ind i en eksisterende delt liste på kontoen
(fx "Web placeringer"), er det en bevidst beslutning taget i selve kørslen — ikke en automatik.

**Ærlig hul: børneindhold har intet gratis signal.** Research forud for dette skill (2026-07-01)
fandt ingen gratis, aktivt vedligeholdt liste over børne-content-domæner. Skillet fanger noget af
det indirekte via app-netværk-flaget og Googles egne placement-kategori-ekskluderinger, men
påstår IKKE at detektere børneindhold direkte. Sig det højt i outputtet — fabrikér aldrig et
signal der ikke findes.

**Ærlig hul: bundlet blocklist rammer ikke alt gambling.** Samme live-verificering viste at
community-DNS-blocklister (Blocklist Project, Steven Black) er bygget til at fange
casino/betting-**brands**, og typisk misser legitimt udseende lotteri-resultat-sites (en officiel
lottos egen resultatside tælles ikke som "malicious" af en DNS-blocklist-vedligeholder).
`euro-jackpot.net` og `danskelotto.com` scorede 0 på blocklist-match alene i testen. Scriptet har
et navne-mønster-baseret backstop for dette (se `score_placements.py`), men det er lavpræcision —
**læs altid domænenavnene i den lave/usikre gruppe med sund fornuft**, ikke kun tallet. Google
Ads' egen intuition ("ligner det her et gambling-site?") slår stadig scriptet på grænsetilfælde.

## PMax-begrænsning (platform-fakta, ikke et design-valg)

Google Ads API'en understøtter **ikke** direkte placement-exclusion på Performance Max-kampagner.
Skillet kan læse PMax-placeringsdata (hvor synlig den er — ofte mindre granulær end ren Display),
men PMax-fund er **forslag-kun** og skrives ALDRIG til kontoen. Marker dette tydeligt i rapporten
per fund: "PMax — kun forslag, kan ikke auto-skrives." Kun rene Display-kampagner kan faktisk få
skrevet negativer af dette skill.

## Forudsætning

Google Ads MCP + et `customer_id`. Ingen MCP → sig det og stop. Svar på dansk (engelsk hvis
brugeren skriver engelsk).

## Trin 0 — Hent klient-kontekst (AI Context) FØRST

Før al anden handling på en navngiven klient — og FØR det første Google Ads MCP-kald — skal du
hente klientens AI Context-fil ind i din kontekst. Det er en læsning (aldrig gated), men
obligatorisk: sådan arver du alt Inbound ved om klienten (ID'er, hårde rammer, pausede-kampagner-
intention, hvilke kampagnetyper klienten faktisk kører) i stedet for at audit'e blindt.

1. **Identificér klienten.** Er det uklart, spørg hvilken klient før du fortsætter.
2. **Åbn master-klientindekset i Drive** via Drive-connectoren: `search_files` efter Google Doc'en
   `Inbound CPH — Google Ads klient-index (AI Context)` (id `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`,
   "A - Kunder"-mappen). Læs den (`read_file_content`). Den mapper klient → Google Ads ID, Stage,
   Drive-mappe, AI Context-fil.
3. **Find klientens række**, notér **Stage** — en ikke-`customer`-stage betyder ingen aktiv
   retainer, vægt anbefalinger derefter.
4. **Åbn klientens AI Context-`.md`** via Drive-linket og tag den ind i kontekst. Hårde rammer
   (læs før du foreslår en eksklusion), pausede-kampagner-intention (pausede kampagner er bevidste
   hos Inbound — ekskludér dem fra analysen, flag dem aldrig som fund), og om klienten faktisk
   kører app-annoncer (relevant for app-netværk-signalet, se Trin 3).
5. **Først derefter** går du videre til intake og Google Ads-læsning.

Har klienten ingen AI Context-fil endnu: sig det, fortsæt med hvad du kan samle (Ads MCP alene),
men flag hullet. Spring aldrig opslaget stille over.

## Trin 1 — Intake (ét `AskUserQuestion`-kald)

Udled så meget som muligt fra samtalen først. Saml i ét kald:

1. **Klient + `customer_id`** — bekræft hvis nævnt; ellers slå op i vault `clients/*.md`
   (`google_ads_id`-feltet) eller kør `list_accessible_accounts` og bekræft.
2. **Analysevindue** — **default sidste 90 dage** (ikke 30 — Display-placeringer akkumulerer
   langsomt, og en 90-dages rude er nødvendig for at fange lavvolumen-junk der ikke ville nå
   signifikans på 30 dage). `run_custom_gaql` mod `detail_placement_view` accepterer
   `BETWEEN '<start>' AND '<slut>'` — beregn datoerne, `LAST_90_DAYS` er ikke et gyldigt
   GAQL-literal i en `WHERE`-clause på dette view (kun nogle få faste literals som `LAST_30_DAYS`
   virker direkte).
3. **Scope** — `Hele kontoen` eller `Specifik kampagne`.
4. **Score-tærskler** (tilbyd default, lad brugeren justere): `Høj-grænse (default 70)`,
   `Lav-grænse (default 30)`, `Loft for websøg (default 15-20)`, `Nul-konv-forbrugsgulv (default
   20 kr/valuta-ækvivalent)`. Sig "brug default" er et gyldigt svar — spørg ikke pedantisk hvis
   brugeren bare vil køre den.
5. **Skriv-destination for bekræftede negativer** — `Direkte til kontoen via ads-writer (standard)`
   eller `Kun rapportér, skriv intet` (fx hvis eksperten kun vil se billedet uden at handle endnu).

## Trin 2 — Hent placeringsdata + eksisterende ekskluderinger

Uddeleger konto-læsningen til `ads-analyst`-agenten (read-only) via Task-værktøjet. Giv den det
bekræftede `customer_id`, vinduet og scopet fra Trin 1, og bed den køre:

**Placeringsdata (Display + PMax hvor synligt):**
```sql
SELECT detail_placement_view.display_name,
       detail_placement_view.group_placement_target_url,
       detail_placement_view.placement_type,
       campaign.id, campaign.name, campaign.advertising_channel_type,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM detail_placement_view
WHERE segments.date BETWEEN '<start>' AND '<slut>'
  AND campaign.status = 'ENABLED'
ORDER BY metrics.cost_micros DESC
```
(Pausede kampagner er bevidste hos Inbound — `campaign.status = 'ENABLED'` ekskluderer dem, flag
dem aldrig som et fund.)

**Eksisterende negative placeringer** (så skillet aldrig genforeslår noget der allerede er
ekskluderet):
```sql
SELECT campaign_criterion.criterion_id, campaign_criterion.type, campaign_criterion.negative,
       campaign.name, shared_set.name
FROM campaign_criterion
WHERE campaign_criterion.type IN ('PLACEMENT', 'YOUTUBE_CHANNEL', 'YOUTUBE_VIDEO', 'MOBILE_APPLICATION')
```
```sql
SELECT shared_set.id, shared_set.name, shared_set.type, shared_set.status
FROM shared_set
WHERE shared_set.type = 'NEGATIVE_PLACEMENTS'
```
For hver `NEGATIVE_PLACEMENTS`-shared_set fundet, hent dens medlemmer via `shared_criterion` for
det fulde billede af hvad der allerede er blokeret. **Verificeret gotcha:** GAQL på denne MCP
afviser `OR` i WHERE — brug `IN (...)` som ovenfor, ikke `type = 'X' OR type = 'Y'`.

Agenten returnerer strukturerede fund: rå placeringsliste + liste over allerede-ekskluderede
domæner/apps/kanaler. `ads-analyst` er read-only og skriver aldrig — den henter kun.

## Trin 3 — Score placeringerne (deterministisk, ingen model-dom endnu)

Skriv agentens fund til en `placements.json` efter skemaet i toppen af
`scripts/score_placements.py`, og kør:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/score_placements.py \
  --in placements.json --out scored.json \
  --high-threshold <fra Trin 1, default 70> \
  --low-threshold <fra Trin 1, default 30> \
  --tier3-cap <fra Trin 1, default 20> \
  --zero-conv-floor <fra Trin 1, default 20>
```

Scriptet gør PRÆCIS dette og intet mere (samme filosofi som `slim.py` i `soegeterm-analyse` — koden
regner, modellen dømmer):
- Matcher hvert domæne mod det bundlede `references/junk_domains.tsv` (~9.834 domæner, gambling +
  MFA/clickbait-proxy + scam, kilder og licens i `references/junk_domains_SOURCES.md`).
- Flager risikable TLD'er (`.top .xyz .icu .club .online .cfd .sbs .bond .win .rest .mom .cn`).
- Flager et gambling/betting-nøgleord literal i domænenavnet (lavpræcision-backstop for et
  verificeret hul — se afsnittet ovenfor).
- Flager nul-konvertering-ved-forbrug (dit tunbare gulv) og CTR-anomalier (for lav ELLER
  mistænkeligt høj ved reelt volumen).
- Flager al app-netværk-trafik som strukturelt risikabel (uanset det enkelte site/apps kvalitet —
  små skærme + spil-UI'er giver ved-et-uheld-klik, en egenskab ved inventar-typen).
- Krydstjekker mod de allerede-ekskluderede fra Trin 2 (sætter `already_excluded: true` — foreslå
  ALDRIG noget der allerede er blokeret).
- Sorterer den usikre gruppe efter forbrug og markerer hvilke der er inden for tier-3-loftet.

Læs `scored.json`. Fordel dig selv: høj-bånd og lav-bånd behøver **intet websøg** — kun den usikre
gruppe (inden for loftet) skal videre til Trin 4, det er dét loftet er der for at spare.

**Men "intet websøg" betyder ikke "ingen læsning".** Live-test (Dantaxi, 2026-07-01) viste at
selv efter TLD- og nøgleords-signalerne kan et reelt gambling-site (`spil2vind.dk`) lande i
lav-båndet, fordi dets forbrug var spredt over flere rækker og ingen enkelt række krydsede
nul-konv-gulvet. Scriptet er additivt og lokalt — det ser IKKE mønstre på tværs af rækker, og det
har ingen fuldstændig ordliste. Så: **skim domænenavnene i lav-båndet med sund fornuft, gratis,
uden opslag**, før du skriver rapporten. Et domænenavn der åbenlyst betyder gambling/spil/casino på
dansk ELLER engelsk, men som scoren satte lavt, skal stadig nævnes i rapporten (fx som en note under
lav-bånd-tabellen: "bemærk: X ligner et gambleside på trods af lav score, tjek"), ikke bare forsvinde
tavst. Det er billigt (et blik, ikke et opslag) og det er præcis den slags fejl der reelt sker på
skæve, spredte konti.

## Trin 4 — Websøg KUN på den usikre gruppe (tier 3, loft-begrænset)

For hver placering med `tier3_eligible: true` i `scored.json` (de øverste ~15-20 efter forbrug i
den usikre gruppe — resten af den usikre gruppe får IKKE et opslag, de markeres "kræver manuel
gennemgang" i rapporten):

1. **Foretræk et websøg** ("hvad er [domæne] for et site") frem for et rå side-fetch. Det er
   billigere, hurtigere, og mere robust mod cloaking/bot-blokering — gambling- og MFA-sites bruger
   ofte netop dét til at undgå scrapere. Et fetch der bliver blokeret er i sig selv et svagt
   "måske junk"-signal, ikke en fejl at ignorere.
2. **Fald kun tilbage til et direkte fetch** hvis søgningen ikke giver noget brugbart.
3. Ud fra resultatet, giv placeringen en kort dansk vurdering: "gambling-site", "content-farm/
   clickbait", "legitimt nyhedssite, sandsynligvis fejlplaceret targeting", osv. Dette ER
   model-dømmekraft — brug sund fornuft, ikke kun et keyword-match.

**Loftet er bevidst, ikke en fejl.** Et websøg koster mere end et lokalt scoretjek. At begrænse
det til top-N efter forbrug fanger den handlingsbare hale (der hvor pengene faktisk går hen) uden
at eksplodere i omkostning på en konto med hundredvis af usikre placeringer. Sig altid i rapporten
hvor mange der blev slået op vs. hvor mange der ligger som "kræver manuel gennemgang".

## Trin 5 — Byg den rangerede rapport (i chatten, IKKE .xlsx som default)

**Output er en markdown-tabel i selve chat-svaret, ikke en fil.** Kun byg en `.xlsx` hvis brugeren
eksplicit beder om det (typisk fordi de vil sende den til en kunde til godkendelse — det er en
anden brugssituation end den interne ekspert-gennemgang dette skill primært er til).

Rapportens form, sorteret efter score (højeste først), grupperet i tre sektioner:

```markdown
## Display-placement-audit — <klient> — <vindue>

### 🔴 Høj risiko (score ≥ <tærskel>) — <N> placeringer, <total forbrug> kr
| Placering | Type | Kampagne | Score | Signaler | Forbrug | Konv | Handling |
|---|---|---|---|---|---|---|---|
| euro-jackpot.net | Website | IC \| GDN \| Reach | 85 | blocklist:gambling, gambling_keyword_in_domain | 13 kr | 0 | Ekskludér |

### 🟡 Usikker — slået op (<M> af <total usikre>, resten kræver manuel gennemgang)
| Placering | Type | Kampagne | Score | Websøg-vurdering | Forbrug | Konv | Handling |
|---|---|---|---|---|---|---|---|
| ... | ... | ... | 45 | "Dansk nyhedssite, formentlig fejlplaceret bred targeting" | 87 kr | 0 | Anbefal IKKE ekskludér |

### ⚪ Lav risiko (score < <tærskel>) — <N> placeringer, samlet <total forbrug> kr
(Kort opsummeret, ikke radvist — det er støjen der IKKE skal handles på.)

### ⚠️ PMax-fund (forslag-kun — kan ikke auto-skrives)
| Placering | Kampagne | Score | Anbefaling |
|---|---|---|---|

### Allerede ekskluderet (<N> placeringer) — vist for gennemsigtighed, foreslås ikke igen
```

Under tabellerne: en kort dansk konklusion (2-4 linjer — de vigtigste mønstre, samlet spildt
forbrug i høj-gruppen, det ærlige forbehold om børneindhold + blocklist-blind-spot fra ovenfor).

**Eksperten redigerer HER, i chatten** — fjern rækker, flyt en "usikker" til "ekskludér", ret en
"høj" til "behold" hvis de kender konteksten bedre end scoren. Skillet foreslår; mennesket dømmer
den endelige liste.

## Trin 6 — Bekræft, så skriv (human-in-the-loop, ingen undtagelse)

Når eksperten har sagt hvilke rækker der skal ekskluderes (implicit "kør med rapporten som den
står" tæller også, hvis intet blev ændret), byg den ENDELIGE liste og vis den én gang mere som et
eksplicit forslag før noget rammer kontoen:

> **Foreslået skrivning til `<customer_id>`:**
> - Ekskludér `<domæne/app/kanal>` som negativ placering på `<kampagne>` (type: PLACEMENT /
>   MOBILE_APPLICATION / YOUTUBE_CHANNEL)
> - [gentag for hver bekræftet række]
>
> Bekræft for at skrive, ret for at revidere, eller sig skip.

Kun et klart "ja"/"bekræft"/"skriv" udløser skrivningen. Tavshed, en emoji, eller "ok fortsæt" på
noget andet tæller IKKE som bekræftelse — spørg igen.

**Dispatchér den bekræftede liste til `ads-writer`-agenten** (den eneste agent der må skrive til en
Google Ads-konto i denne plugin). Giv den `customer_id` + den præcise, bekræftede ændring per
placering.

### Kendt platform-hul: der findes IKKE en dedikeret "tilføj negativ placering"-værktøj i denne
### Google Ads MCP (verificeret 2026-07-01)

Denne MCP-server har `add_negative_keywords` (kun keyword-tekst) men **ingen tilsvarende værktøj
for placeringer, apps eller YouTube-kanaler/videoer**. `run_custom_gaql` er en GAQL-læsevej, ikke
en mutate-mekanisme — Google Ads-writes går gennem separate mutate-RPC'er, ikke GAQL. Hvis
`ads-writer` afprøver værktøjssættet og finder samme hul (ingen write-vej for `campaign_criterion`
negative placements), SKAL skillet degradere ærligt frem for at foregive en skrivning skete:

1. Sig det tydeligt: "Google Ads MCP'en har ingen skrive-vej for negative placeringer endnu — jeg
   kan ikke skrive dette direkte til kontoen."
2. Aflever i stedet den bekræftede liste som en **kopiér-klar manuel liste** klar til Google Ads
   Editor eller UI'et: domæne/app/kanal + type + anbefalet niveau (kampagne vs. delt liste — se
   nedenfor) + match/eksklusionstype.
3. Nævn at dette er en midlertidig begrænsning i værktøjssættet, ikke en permanent skilebegrænsning
   — når/hvis MCP'en får en `add_negative_placement`-lignende funktion, opdatér dette trin til at
   bruge den direkte.

Hvis `ads-writer` FAKTISK finder en fungerende write-vej (fx et generisk mutate-værktøj der ikke
var synligt i research forud for dette skill), brug den — dette afsnit er en dokumenteret
antagelse pr. build-tidspunkt, ikke en hård regel om at aldrig prøve.

### Kampagne vs. delt liste — spørg, gæt aldrig

For hver bekræftet ekskludering: spørg eksperten om den skal gå på **den specifikke kampagne**
eller ind i en **eksisterende delt negativliste** på kontoen (vis hvilke delte
`NEGATIVE_PLACEMENTS`-lister der allerede findes fra Trin 2, fx "Web placeringer",
"Børneplaceringer"). Gæt aldrig standardvalget — det er en klient- og situationsafhængig
beslutning som eksperten selv skal tage i øjeblikket, ikke noget skillet forudbestemmer.

## Trin 7 — Output

Lever:
1. **Rapporten** (Trin 5) — allerede vist i chatten.
2. **Skrive-resultatet** — hvad blev faktisk ekskluderet, hvor (kampagne/delt liste), og eventuelt
   det manuelle Editor-fald-tilbage hvis write-vejen manglede.
3. **Det ærlige forbehold** gentaget kort: børneindhold uden signal, blocklist-blind-spot på
   lotteri/betting-resultatsider, PMax er forslag-kun.
4. **Kilder** — MCP-værktøjer brugt, `references/junk_domains_SOURCES.md` for blocklist-licenser.

## Eksempel-output (fra live-verificering, Dantaxi 2026-07-01)

```
Display-placement-audit klar: Dantaxi (4149791707), sidste 90 dage.

🔴 Høj risiko (2 placeringer, 13 kr forbrugt, 0 konv):
- petsim99.co (Roblox-lignende børnespil-community) — anbefalet ekskluderet
- [content-farm-domæne] — anbefalet ekskluderet

🟡 Usikker, slået op (3 af 3 — under loftet):
- euro-jackpot.net — websøg: "Officiel dansk lotteri-resultatside" → gambling-adjacent,
  anbefalet ekskluderet på trods af lav blocklist-score (kendt blind spot, se ovenfor)
- danskelotto.com — samme mønster, anbefalet ekskluderet
- wrestlezone.com — websøg: "legitimt sports-nyhedssite" → anbefalet IKKE ekskluderet, sandsynligvis
  bare bred targeting-fejlplacering, ikke junk i sig selv

⚪ Lav risiko: 24 placeringer, 380 kr samlet — ingen handling anbefalet.

Bekræft ovenstående 4 ekskluderinger for at skrive til kontoen, eller ret listen.
```

## Hård sandheds-grænse

- **Skriv kun til kontoen efter eksplicit bekræftelse — ingen undtagelse, ingen "brugeren sagde
  vist ja tidligere".**
- **Foreslå aldrig noget der allerede er ekskluderet.** Krydstjek er obligatorisk (Trin 2 + 3).
- **Byg aldrig en permanent/delt liste automatisk.** Kun de bekræftede negativer for netop denne
  kørsel skrives; hvilken delt liste (hvis nogen) er et eksplicit valg eksperten tager per kørsel.
- **Pausede kampagner flages aldrig som et fund** — de er bevidste hos Inbound.
- **PMax-fund skrives aldrig** — kun forslag, platform-begrænsning, ikke skillets valg.
- **Børneindhold-dækning er ikke påstået** — intet gratis signal findes, sig det højt.
- **Æ Ø Å altid** i alt dansk output — aldrig ASCII-translitteration.
- **Lyv aldrig om en skrivning der ikke skete.** Hvis write-vejen mangler i MCP'en, sig det og
  lever det manuelle fald-tilbage — påstå aldrig kontoen blev opdateret.

## Maintenance

- `scripts/score_placements.py` — den ENESTE deterministiske del. Matcher blocklist, TLD, nøgleord-
  mønster, forbrug/CTR-signaler, app-flag, allerede-ekskluderet-tjek. Ingen model-dømmekraft heri;
  ret aldrig scoringen til at "dømme" i stedet for at signalere.
- `references/junk_domains.tsv` — 9.834 domæner (gambling + MFA-proxy + scam), bygget fra
  Blocklist Project + Steven Black's hosts, begge fri licens. Se `junk_domains_SOURCES.md` for
  fuld proveniens, licenser, og genopfrisknings-kommando. Dette er en statisk snapshot, ikke en
  live feed — genopfrisk den med jævne mellemrum (kommandoen står i SOURCES-filen).
- Hvis Google Ads MCP'en får en dedikeret negative-placement write-værktøj: opdatér Trin 6's
  "kendt platform-hul"-sektion til at bruge den direkte i stedet for det manuelle fald-tilbage.
- Bevidst INGEN: automatisk delt-liste-bygning, xlsx som default-output, gæt på kampagne-vs-delt-
  liste-niveau. Hvis du fristes til at automatisere en af disse: lad være, det var et eksplicit
  valg fra brugeren om at bevare menneskelig kontrol her.
