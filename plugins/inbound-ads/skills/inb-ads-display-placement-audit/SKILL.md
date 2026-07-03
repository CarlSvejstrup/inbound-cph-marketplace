---
name: inb-ads-display-placement-audit
description: Audit en kundes LIVE Google Ads Display-placeringer (websites, apps, YouTube) for junk som gambling, MFA/clickbait og low-quality apps, scorer hver placering 0-100 ud fra gratis lokale signaler og foreslår negative placeringer, med PMax-fund som forslag-kun og kontoskrivning udelukkende efter eksplicit bekræftelse via ads-writer-agenten.
---

# inb-ads-display-placement-audit

Find ud af **hvor** en klients Display-annoncer (og Performance Max, hvor synligt) rent faktisk
bliver vist på tværs af Googles annoncenetværk, score hver placering for junk-risiko, og — efter
eksplicit bekræftelse — ekskludér de bekræftede fra kontoen via `ads-writer`.

## Baggrund (kort)

Display-annoncer vises på tredjeparts-sites, apps og YouTube valgt af Googles algoritme, ikke af en
søgning — så junk (gambling, content-farme, low-quality apps) sniger sig ind. Skillet scorer hver
placering 0-100 additivt af **kun site-signaler** (`scripts/score_placements.py`, se Trin 3): kendt
junk-domæne, risikabel TLD, gambling-nøgleord i navnet, plus app-netværk-trafik som strukturelt
flag. Performance-signaler (forbrug-uden-konvertering, CTR-anomali) er BEVIDST fjernet — lav CTR/konv
er normal Display-adfærd, ikke junk, og at score på det producerede falske positiver på store
legitime sites (bt.dk, proff.no). Prioritering er cost-first: tid og websøg går efter FORBRUG, ikke
efter scoretal.

**Ærlige huller (sig dem højt i outputtet):** børneindhold detekteres ikke direkte (intet gratis
signal findes; fanges kun indirekte via app-flag + hard-exclusion-kids-kategori), og blocklisten
fanger ikke alt gambling (legitimt udseende lotteri-sider glipper — læs navnene med sund fornuft).
**PMax-fund er forslag-kun og skrives aldrig** (platform-fakta: API'en tillader ikke
placement-exclusion på PMax).

**Skrevet til eksperten, ikke en analytiker (gælder HELE skillet):** GAQL, criterion-ID'er, score-tal
og signalnavne som `zero_conv_at_spend` er implementeringsdetaljer — de må ALDRIG lække ud i noget
brugeren læser (intake, statusbeskeder, bekræftelses-prompt, rapport).

Fuld begrundelse for scoring-filosofien, banding, de to redesigns 2026-07-03, og hvorfor hvert
fjernet signal blev fjernet: læs `references/design-decisions.md`. Rør aldrig scoringen uden at læse
den fil.

## Forudsætning

Google Ads MCP + et `customer_id`. Ingen MCP → sig det og stop. Svar på dansk (engelsk hvis brugeren
skriver engelsk).

## Trin 0 — Hent klient-kontekst (AI Context) først

Kør `../../shared/client-context-intake.md` som allerførste trin — før intake og før det første
Google Ads MCP-kald. Det er en læsning (aldrig gated), men obligatorisk: sådan arver du ID'er,
kontakter, hårde rammer, budstrategi-norm, KPI'er og pausede-kampagners-intention i stedet for at
auditere blindt. Den fil holder også reglen om delte Drive-mapper (Lime, Retriever/Infomedia,
GSGroup, Nemco, Julemærket, PhoneAlone, DI → vælg rækken for det specifikke marked) og fallback når
en klient endnu ikke har en AI Context-fil.

To ting fra AI Context er direkte relevante her: pausede kampagner er bevidste hos Inbound (ekskludér
dem fra analysen, flag dem aldrig som fund), og om klienten faktisk kører app-annoncer (relevant for
app-netværk-signalet, Trin 3). En Stage ≠ `customer` betyder ingen aktiv retainer — vægt
anbefalinger derefter.

## Trin 1 — Intake (ét `AskUserQuestion`-kald)

Udled så meget som muligt fra samtalen først. Saml resten i ét kald:

1. **Klient + `customer_id`** — bekræft hvis nævnt; ellers slå op i vault `clients/*.md`
   (`google_ads_id`-feltet) eller kør `list_accessible_accounts` og bekræft.
2. **Analysevindue** — default sidste 90 dage (ikke 30 — Display-placeringer akkumulerer langsomt,
   og en 90-dages rude er nødvendig for at fange lavvolumen-junk). `run_custom_gaql` mod
   `detail_placement_view` accepterer `BETWEEN '<start>' AND '<slut>'` — `LAST_90_DAYS` er ikke et
   gyldigt GAQL-literal i en `WHERE`-clause på dette view (kun nogle få faste literals som
   `LAST_30_DAYS` virker direkte).
3. **Scope** — hele kontoen eller specifik kampagne.
4. **Score-tærskler** (tilbyd default, lad brugeren justere): høj-grænse (default 70), loft for
   websøg (default 15-20). Bevidst ingen separat "lav-grænse" at stille — "lav risiko" betyder nul
   signaler, ikke et tal under en grænse. "Brug default" er et gyldigt svar.
5. **Skriv-destination for bekræftede negativer** — direkte til kontoen via ads-writer (standard)
   eller kun rapportér, skriv intet.

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
(Pausede kampagner er bevidste hos Inbound — `campaign.status = 'ENABLED'` ekskluderer dem, flag dem
aldrig som fund.)

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
For hver `NEGATIVE_PLACEMENTS`-shared_set fundet, hent dens medlemmer via `shared_criterion` for det
fulde billede af hvad der allerede er blokeret. Verificeret gotcha: GAQL på denne MCP afviser `OR` i
WHERE — brug `IN (...)`, ikke `type = 'X' OR type = 'Y'`.

Agenten returnerer strukturerede fund: rå placeringsliste + liste over allerede-ekskluderede
domæner/apps/kanaler. `ads-analyst` er read-only og skriver aldrig.

## Trin 3 — Score placeringerne (deterministisk, ingen model-dom endnu)

Skriv agentens fund til en `placements.json` efter skemaet i toppen af `scripts/score_placements.py`,
og kør:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/score_placements.py \
  --in placements.json --out scored.json \
  --high-threshold <fra Trin 1, default 70> \
  --tier3-cap <fra Trin 1, default 20>
```
(Bevidst intet `--low-threshold`-flag, jf. Baggrund.)

Scriptet gør præcis dette og intet mere (samme filosofi som `slim.py` i `inb-ads-search-term-analyse`
— koden regner, modellen dømmer):

- **Tjekker først Inbound's eget hårde ekskluderingskatalog** (`references/hard_exclusions.tsv` +
  `references/hard_exclusion_patterns.py`). Ethvert match ("hard_exclusion"-bånd) springer HELE
  resten af scoringen OG websøget over og går direkte til "anbefales fjernet" — fordi Inbound selv
  allerede har besluttet kategorien, ikke en heuristik. Fuld liste + kategorier + provenance:
  `references/hard-exclusions-catalog.md`. Bland aldrig dette lag sammen med det almindelige
  blocklist-signal nedenfor.
- Matcher hvert domæne mod det bundlede `references/junk_domains.tsv` (~9.834 domæner, gambling +
  MFA/clickbait-proxy + scam; se `references/junk-domains-refresh.md`).
- Flager risikable TLD'er (`.top .xyz .icu .club .online .cfd .sbs .bond .win .rest .mom .cn`).
- Flager et gambling/betting-nøgleord literal i domænenavnet (lavpræcision-backstop, se Baggrund).
- Flager al app-netværk-trafik som strukturelt risikabel (uanset det enkelte site/apps kvalitet —
  små skærme + spil-UI'er giver ved-et-uheld-klik).
- Krydstjekker mod de allerede-ekskluderede fra Trin 2 (sætter `already_excluded: true` — foreslå
  aldrig noget der allerede er blokeret; går forud for hård-ekskludering).
- Sorterer den usikre gruppe efter FORBRUG (ikke score) og markerer hvilke der er inden for
  tier-3-loftet — cost-first.

**Bevidst IKKE med:** performance-signaler (forbrug-uden-konvertering, CTR-anomali). Scriptet dømmer
kun sitet selv, aldrig hvordan det performede (se `references/design-decisions.md` for hvorfor).

**Banding kort:** hård-ekskludering og høj-bånd (≥70) er allerede afgjort → intet websøg. Lav-bånd =
nul signaler → intet at gennemgå. Al reel tvivl, selv fra ét svagt signal, lander i den usikre
gruppe — det er dér arbejdet foregår. Fuld banding-forklaring i `references/design-decisions.md`.

## Trin 4 — Websøg kun på den usikre gruppe (tier 3, loft-begrænset)

For hver placering med `tier3_eligible: true` i `scored.json` (de øverste ~15-20 i den usikre gruppe,
sorteret efter FORBRUG — cost-first):

1. Foretræk et websøg ("hvad er [domæne] for et site") frem for et rå side-fetch. Billigere,
   hurtigere, og mere robust mod cloaking/bot-blokering — gambling- og MFA-sites bruger ofte netop
   dét til at undgå scrapere. Et fetch der bliver blokeret er i sig selv et svagt "måske junk"-signal.
2. Fald kun tilbage til et direkte fetch hvis søgningen ikke giver noget brugbart.
3. Giv placeringen en kort dansk vurdering ud fra resultatet: "gambling-site", "content-farm/
   clickbait", "legitimt nyhedssite, sandsynligvis fejlplaceret targeting", osv. Dette er
   model-dømmekraft — brug sund fornuft, ikke kun et keyword-match.

Loftet er bevidst — et websøg koster mere end et lokalt scoretjek, og det holder omkostningen nede på
en konto med hundredvis af usikre placeringer. Sig altid i rapporten hvor mange der blev slået op vs.
hvor mange der ligger som "kræver manuel gennemgang".

**Undtagelse — blocklist- og gambling-nøgleord-hits springer altid køen, uanset loft.** Sorteringen
er cost-first, så et lavt-forbrug gambling-fund kan i princippet havne under loftet bag høj-forbrug
placeringer med kun risikabel-TLD eller intet signal. En placering der scorer via `blocklist:*` eller
`gambling_keyword_in_domain` skal altid med i websøgs-runden, uanset `tier3_rank` og forbrug — disse
to signaler peger specifikt på gambling/junk og fortjener altid et opslag. Filtrér `scored.json` på
`"blocklist:"` eller `"gambling_keyword_in_domain"` i `signals`, tilføj dem til websøgs-runden selvom
`tier3_eligible` er `false`, og nævn eksplicit i rapporten at de blev prioriteret ud over loftet.

## Trin 5 — Byg den rangerede rapport (i chatten, ikke .xlsx som default)

**Output er markdown i selve chat-svaret, ikke en fil.** Byg kun en `.xlsx` hvis brugeren eksplicit
beder om det (typisk fordi de vil sende den til en kunde til godkendelse).

**Default er KORT — kun to tabeller, ingen prosa.** Eksperten kører dette skill én-to gange om
måneden og vil se hvad der skal handles på, ikke læse en afhandling:

1. **🚫 Anbefales fjernet** — inkluderer BÅDE hard_exclusion- og high-bånd i samme tabel (begge
   allerede besluttede). Kolonner: Sted / Forbrug / Klik / Konv / Hvorfor (3-6 ord, aldrig en hel
   sætning, ingen interne signalnavne, ingen "Score"-kolonne).
2. **🤔 Værd at kigge på** — KUN dem der reelt kræver et menneskeligt blik (`tier3_eligible` = websøgt,
   ELLER blocklist/gambling-keyword-hits der sprang køen). Under-loft-placeringer der aldrig blev
   websøgt samles i ÉN linje i bunden ("+K steder til, samme mønster men ikke tjekket enkeltvis …").

Afslut med én linje der beder om bekræftelse. **Global dedup:** samme domæne over flere kampagner
slås sammen til én linje (læg forbrug sammen) — vis aldrig samme domæne to gange.

**Uddybet visning — kun on-demand.** Triggerord: "uddyb", "mere detaljer", "hvorfor er de her", "vis
mig alt", "hvad med PMax/allerede håndteret", eller forespørgsel om ét specifikt domæne. Byg da den
fulde 5-sektions-rapport (anbefales fjernet uddybet / værd at kigge på uddybet / ingen problemer +
falske alarmer / PMax-kan-ikke-fjernes / allerede håndteret) — men KUN de efterspurgte sektioner. De
to ærlige forbehold (børneindhold, ikke-alt-gambling) nævnes kun her, ikke i default-svaret.

Den fulde default- og uddybede skabelon, alle regler, og et komplet eksempel-output (DBI):
`references/report-templates.md`. Eksperten redigerer altid i chatten — skillet foreslår, mennesket
dømmer den endelige liste.

## Trin 6 — Bekræft, så skriv (human-in-the-loop, ingen undtagelse)

Når eksperten har sagt hvilke rækker der skal ekskluderes (implicit "kør med rapporten som den står"
tæller også, hvis intet blev ændret), byg den endelige liste og vis den én gang mere som et eksplicit
forslag før noget rammer kontoen:

> **Foreslået ændring på `<klientens navn>`:**
> - Bloker **euro-jackpot.net** (website) på kampagnen "<kampagne>"
> - Bloker **spil2vind.dk** (website) på kampagnen "<kampagne>"
> - [gentag for hver bekræftet placering — brug altid "bloker X (website/app/YouTube-kanal) på
>   kampagnen Y", aldrig de tekniske typenavne PLACEMENT/MOBILE_APPLICATION/YOUTUBE_CHANNEL]
>
> Bekræft for at skrive, ret for at revidere, eller sig skip.

Kun et klart "ja"/"bekræft"/"skriv" udløser skrivningen. Tavshed, en emoji, eller "ok fortsæt" på
noget andet tæller ikke som bekræftelse — spørg igen.

Dispatchér den bekræftede liste til `ads-writer`-agenten (den eneste agent der må skrive til en
Google Ads-konto i denne plugin). Giv den `customer_id` + den præcise, bekræftede ændring per
placering.

**Kendt platform-hul (verificeret 2026-07-01):** denne Google Ads MCP har `add_negative_keywords`
(kun keyword-tekst) men ingen tilsvarende værktøj for placeringer, apps eller
YouTube-kanaler/videoer. `run_custom_gaql` er en GAQL-læsevej, ikke en mutate-mekanisme. Hvis
`ads-writer` afprøver værktøjssættet og finder samme hul, degradér ærligt frem for at foregive en
skrivning skete:

1. Sig det tydeligt: "Google Ads MCP'en har ingen skrive-vej for negative placeringer endnu — jeg
   kan ikke skrive dette direkte til kontoen."
2. Aflever i stedet den bekræftede liste som en kopiér-klar manuel liste til Google Ads Editor eller
   UI'et: domæne/app/kanal + type + anbefalet niveau (kampagne vs. delt liste) + match/eksklusionstype.
3. Nævn at dette er en midlertidig begrænsning i værktøjssættet — når/hvis MCP'en får en
   `add_negative_placement`-lignende funktion, opdatér dette trin til at bruge den direkte.

Finder `ads-writer` faktisk en fungerende write-vej (fx et generisk mutate-værktøj), brug den —
ovenstående er en dokumenteret antagelse pr. build-tidspunkt, ikke en hård regel om aldrig at prøve.

**Kampagne vs. delt liste — spørg, gæt aldrig.** For hver bekræftet ekskludering: spørg eksperten om
den skal gå på den specifikke kampagne eller ind i en eksisterende delt negativliste på kontoen (vis
hvilke delte `NEGATIVE_PLACEMENTS`-lister der allerede findes fra Trin 2, fx "Web placeringer",
"Børneplaceringer"). Det er en klient- og situationsafhængig beslutning eksperten selv skal tage.

## Trin 7 — Output

Lever, i almindeligt sprog (samme regel som Trin 5 — ingen interne termer):

1. **Rapporten** (Trin 5) — allerede vist i chatten.
2. **Hvad der faktisk skete ved skrivningen** — hvilke sider/apps/kanaler blev rent faktisk blokeret,
   om det landede på selve kampagnen eller en delt liste, og — hvis Google Ads-værktøjet ikke
   understøttede det endnu — at I i stedet får en færdig liste til at indsætte manuelt i Google Ads
   Editor.
3. **De to ærlige forbehold, skrevet så alle forstår dem:** "vi kan endnu ikke opdage børneindhold
   automatisk" og "nogle rigtige gambling-/lotteri-sider bliver muligvis ikke fanget automatisk —
   hold øje med mistænkelige navne i den brede liste, ikke kun i 'anbefales fjernet'." PMax nævnes
   kort: "Performance Max viser desværre ikke placeringer detaljeret nok til at vi kan foreslå noget
   der."
4. **Hvor tallene kommer fra** — én kort sætning, ikke en teknisk logliste: "Data er hentet direkte
   fra jeres Google Ads-konto (placeringsrapporten for perioden) og krydstjekket mod jeres
   eksisterende blokeringer, så I ikke får de samme forslag to gange."

## Hårde grænser

- Skriv kun til kontoen efter eksplicit bekræftelse — ingen undtagelse. Al skrivning går gennem
  `ads-writer`-agenten, aldrig direkte.
- Foreslå aldrig noget der allerede er ekskluderet — krydstjek er obligatorisk (Trin 2 + 3).
- Byg aldrig en permanent/delt liste automatisk — kun de bekræftede negativer for netop denne kørsel
  skrives; hvilken delt liste (hvis nogen) er et eksplicit valg eksperten tager per kørsel.
- Pausede kampagner flages aldrig som et fund — de er bevidste hos Inbound.
- PMax-fund skrives aldrig — kun forslag, platform-begrænsning.
- Børneindhold-dækning er ikke påstået udover det hårde ekskluderingslags kids-kategori — intet
  komplet gratis signal findes, sig det højt i den uddybede visning.
- Æ Ø Å altid i alt dansk output — aldrig ASCII-translitteration.
- Lyv aldrig om en skrivning der ikke skete — mangler write-vejen i MCP'en, sig det og lever det
  manuelle fald-tilbage.
- Default-rapporten er de to korte tabeller (Trin 5) — udvid aldrig til det fulde 5-sektions-skema
  medmindre eksperten selv beder om uddybning.

## Maintenance

- `scripts/score_placements.py` — den eneste deterministiske del. Tjekker først det hårde
  ekskluderingslag, derefter blocklist, TLD, gambling-nøgleord, app-flag, allerede-ekskluderet-tjek —
  bevidst KUN site-signaler, ingen performance-signaler (forbrug/konvertering/CTR blev fjernet
  2026-07-03). Ingen model-dømmekraft heri; ret aldrig scoringen til at "dømme" i stedet for at
  signalere, og tilføj ikke et performance-baseret signal igen uden at genlæse
  `references/design-decisions.md`.
- `references/junk_domains.tsv` — skillets EGEN generelle heuristik (~9.834 domæner). Statisk
  snapshot, ikke en live feed. Proveniens, licenser og genopfrisknings-kommando:
  `references/junk-domains-refresh.md` (fuld bash i `references/junk_domains_SOURCES.md`).
- `references/hard_exclusions.tsv` + `references/hard_exclusion_patterns.py` — Inbounds EGET,
  klient-bekræftede standing ekskluderingslag (191 domæner + nøgleord + ~170 fremmede TLD'er + 11
  ikke-latinske skriftsystemer), indlæst 2026-07-03. Omgår scoring helt. Opdatér disse filer direkte
  hvis Inbound reviderer deres liste — spørg først om nye kategorier skal være hårde ekskluderinger
  eller almindelige scoringssignaler, bland aldrig de to lag sammen uden eksplicit brugervalg. Fuld
  katalog + "High-Cost Low-Performance"-hullet: `references/hard-exclusions-catalog.md`.
- Får Google Ads MCP'en en dedikeret negative-placement write-værktøj: opdatér Trin 6's
  platform-hul-sektion til at bruge den direkte i stedet for det manuelle fald-tilbage.
- Bevidst ingen: automatisk delt-liste-bygning, xlsx som default-output, gæt på
  kampagne-vs-delt-liste-niveau, fuld 5-sektions-rapport som default. Det er eksplicitte valg fra
  brugeren om at bevare menneskelig kontrol og kort output — automatisér/udvid dem ikke.
