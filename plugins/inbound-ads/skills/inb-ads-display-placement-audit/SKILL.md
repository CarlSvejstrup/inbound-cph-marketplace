---
name: inb-ads-display-placement-audit
description: Audit en kundes LIVE Google Ads Display-placeringer (websites, apps, YouTube) for junk som gambling, MFA/clickbait og low-quality apps, scorer hver placering 0-100 ud fra gratis lokale signaler og foreslår negative placeringer, med PMax-fund som forslag-kun og kontoskrivning udelukkende efter eksplicit bekræftelse via ads-writer-agenten.
---

# inb-ads-display-placement-audit

Find ud af **hvor** en klients Display-annoncer (og Performance Max, hvor synligt) rent faktisk
bliver vist på tværs af Googles annoncenetværk, score hver placering for junk-risiko, og — efter
eksplicit bekræftelse — ekskludér de bekræftede fra kontoen via `ads-writer`.

## Baggrund

Display-annoncer vises på tredjeparts-websites, apps og YouTube, valgt af Googles algoritme ud fra
targeting, ikke en søgning. En live-verificering mod en rigtig Inbound-konto (Dantaxi, 2026-07-01)
viste Display-annoncer kørende på `euro-jackpot.net`, `danskelotto.com` (lotteri), `petsim99.co`
(børne-spil-site) og en håndfuld content-farm-domæner — alt sammen forbrug uden en eneste
konvertering.

**Scoring, ikke en binær dom — men få, håndfaste signaler, ikke en punkt-maskine.** Hver placering
får et 0-100 risiko-tal bygget additivt af tre lokale signaler om SELVE SITET
(`scripts/score_placements.py`, se Trin 3): kendt junk-domæne, risikabel TLD, gambling-nøgleord i
navnet, plus app-netværk-trafik som et strukturelt (ikke site-specifikt) flag. Det er bevidst kun
disse — se "Redesign 2026-07-03" nedenfor for hvorfor performance-baserede signaler (forbrug uden
konvertering, CTR-anomali) er fjernet helt.

- **Høj (≥70 som standard):** afgøres af lokale data alene, intet opslag nødvendigt. Typisk et
  direkte blocklist-match, evt. lagt sammen med en risikabel TLD.
- **Usikker (alt med mindst ét signal, der ikke rammer høj-grænsen):** fx en risikabel TLD alene,
  eller et gambling-nøgleord i navnet. Kun de øverste ~15-20 efter FORBRUG (se Trin 4) får et
  websøg; resten markeres "kræver manuel gennemgang". Fordi signalerne nu er få og specifikke, er
  denne gruppe langt mindre end før — typisk under 10-15 placeringer på en almindelig konto, ikke
  hundredvis.
- **Lav (ingen signaler overhovedet):** ingen blocklist-match, ingen risikabel TLD, intet
  gambling-nøgleord, intet app-netværk-flag. Det inkluderer nu ALLE normale sites uanset hvor lidt
  de konverterer på Display — det er forventet adfærd, ikke et risikotegn. Intet at gennemgå.

Verificeret live (Dantaxi, re-test 2026-07-01): den gamle banding (score < 30 → lav) lod
`spil2vind.dk` (reel dansk gambling-side) forsvinde tavst, fordi dens eneste signal
(`gambling_keyword_in_domain`, vægt 15) ikke alene nåede 30. Med den nuværende regel lander den
korrekt i usikker-gruppen.

**Redesign 2026-07-03 — for skarpt, ikke "for meget flagget".** En live-kørsel på DBI viste at
`bt.dk`, `proff.no` og `mentedidactica.com` — alle sammen legitime, store sites — landede i
"usikker" udelukkende fordi de brugte penge uden at konvertere på Display, eller havde en
CTR-anomali. Det er ikke junk, det er helt normal Display-adfærd: lav CTR og lav konvertering er
reglen, ikke undtagelsen, for banner-annoncer på store sider. At bruge det som et risikosignal
producerede en stor, useriøs "usikker"-bunke fyldt med sund fornuft-tilfælde i stedet for reelle
kandidater. De to signaler (`zero_conv_at_spend`, `ctr_too_low`/`ctr_too_high`) er derfor fjernet
helt fra scriptet — de sagde noget om KONTOENS performance, ikke om SITETS kvalitet, og de to ting
er ikke det samme. Tilbage er kun signaler der faktisk identificerer sitet: er det på en kendt
junk-liste, har det en risikabel endelse, hedder det noget med gambling, eller er det app-trafik.

Cost-first er den anden del af samme fix: rapporten og websøgs-loftet prioriterer nu efter FORBRUG,
ikke efter score (se Trin 4-5) — eksperten skal bruge tiden der hvor pengene faktisk er, ikke der
hvor et scoretal tilfældigvis er højest.

Høj-grænsen (70) og loftet (15-20) er parametre eksperten kan justere per kørsel ("vær strengere
denne gang"), ikke faste konstanter. Der er bevidst intet separat "lav-grænse"-parameter — "lav"
betyder nu udelukkende "nul signaler".

**Ingen permanent negativliste bygges af dette skill.** Blocklisten, TLD-reglerne og
scoringslogikken bor bundlet i skillet (`references/junk_domains.tsv`), ikke skrevet til en delt
Google Ads shared_set automatisk. Hver kørsel er selvstændig: læser 90 dages data, scorer med
skillets egne regler, viser rapporten, og skriver kun de negativer eksperten bekræfter for netop
den kørsel. Vil eksperten proppe dem ind i en eksisterende delt liste, er det et bevidst valg taget
i selve kørslen.

**Kendt hul — børneindhold:** ingen gratis, aktivt vedligeholdt liste over børne-content-domæner
findes. Skillet fanger noget af det indirekte via app-netværk-flaget, men detekterer ikke
børneindhold direkte. Sig det højt i outputtet.

**Kendt hul — blocklisten rammer ikke alt gambling.** Community-DNS-blocklister (Blocklist Project,
Steven Black) fanger casino/betting-brands, men misser typisk legitimt udseende
lotteri-resultat-sider — `euro-jackpot.net` og `danskelotto.com` scorede 0 på blocklist-match alene
i testen. Scriptet har et navnemønster-baseret backstop for dette, men det er lavpræcision — læs
domænenavnene i den lave/usikre gruppe med sund fornuft, ikke kun tallet.

**PMax-begrænsning (platform-fakta):** Google Ads API'en understøtter ikke direkte
placement-exclusion på Performance Max-kampagner. Skillet kan læse PMax-placeringsdata, men PMax-fund
er forslag-kun og skrives aldrig til kontoen. Marker det per fund i rapporten: "PMax — kun forslag,
kan ikke auto-skrives."

**Skrevet til eksperten, ikke til en analytiker (gælder HELE skillet, ikke kun rapport-trinnet).**
De der bruger dette skill kender Google Ads som fagområde, men ikke GAQL, "criterion_id", interne
score-tal, eller signalnavne som `zero_conv_at_spend`. Det gælder alt brugervendt tekst — intake-
spørgsmål, statusbeskeder undervejs, bekræftelses-prompten før en skrivning, og selve rapporten.
Skriv som du ville forklare det til en kollega over kaffen: hvad der er fundet, hvorfor det er et
problem, og hvad de kan gøre ved det. Interne detaljer (GAQL, score, criterion-ID'er) er
implementeringsdetaljer der styrer HVORDAN skillet arbejder — de skal ALDRIG lække ud i noget
brugeren læser.

## Forudsætning

Google Ads MCP + et `customer_id`. Ingen MCP → sig det og stop. Svar på dansk (engelsk hvis
brugeren skriver engelsk).

## Trin 0 — Hent klient-kontekst (AI Context) først

Før al anden handling på en navngiven klient — og før det første Google Ads MCP-kald — hent
klientens AI Context-fil ind i din kontekst. Læsning, aldrig gated, men obligatorisk.

1. Er klienten uklar, spørg før du fortsætter.
2. Åbn master-klientindekset i Drive via Drive-connectoren: `search_files` efter Google Doc'en
   `Inbound CPH — Google Ads klient-index (AI Context)` (id
   `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`, "A - Kunder"-mappen). Læs den
   (`read_file_content`) — den mapper klient → Google Ads ID, Stage, Drive-mappe, AI Context-fil.
3. Find klientens række, notér Stage — en ikke-`customer`-stage betyder ingen aktiv retainer, vægt
   anbefalinger derefter.
4. Åbn klientens AI Context-`.md` via Drive-linket. Hårde rammer (læs før du foreslår en
   eksklusion), pausede-kampagner-intention (pausede kampagner er bevidste hos Inbound — ekskludér
   dem fra analysen, flag dem aldrig som fund), og om klienten faktisk kører app-annoncer (relevant
   for app-netværk-signalet, se Trin 3).
5. Først derefter går du videre til intake og Google Ads-læsning.

Har klienten ingen AI Context-fil endnu: sig det, fortsæt med hvad du kan samle (Ads MCP alene), men
flag hullet.

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
(Pausede kampagner er bevidste hos Inbound — `campaign.status = 'ENABLED'` ekskluderer dem, flag
dem aldrig som fund.)

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

Skriv agentens fund til en `placements.json` efter skemaet i toppen af
`scripts/score_placements.py`, og kør:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/score_placements.py \
  --in placements.json --out scored.json \
  --high-threshold <fra Trin 1, default 70> \
  --tier3-cap <fra Trin 1, default 20>
```
(Bevidst intet `--low-threshold`-flag, jf. "Baggrund".)

Scriptet gør præcis dette og intet mere (samme filosofi som `slim.py` i
`inb-ads-search-term-analyse` — koden regner, modellen dømmer):
- Matcher hvert domæne mod det bundlede `references/junk_domains.tsv` (~9.834 domæner, gambling +
  MFA/clickbait-proxy + scam, kilder og licens i `references/junk_domains_SOURCES.md`).
- Flager risikable TLD'er (`.top .xyz .icu .club .online .cfd .sbs .bond .win .rest .mom .cn`).
- Flager et gambling/betting-nøgleord literal i domænenavnet (lavpræcision-backstop, se Baggrund).
- Flager al app-netværk-trafik som strukturelt risikabel (uanset det enkelte site/apps kvalitet —
  små skærme + spil-UI'er giver ved-et-uheld-klik).
- Krydstjekker mod de allerede-ekskluderede fra Trin 2 (sætter `already_excluded: true` — foreslå
  aldrig noget der allerede er blokeret).
- Sorterer den usikre gruppe efter FORBRUG (ikke score) og markerer hvilke der er inden for
  tier-3-loftet — cost-first, se "Redesign 2026-07-03" i Baggrund.

**Bevidst IKKE med:** performance-signaler som forbrug-uden-konvertering eller CTR-anomali. Lav
konvertering og lav CTR er normalt for Display — det er ikke bevis på junk, kun bevis på at Display
konverterer dårligere end Search. At score på det producerede falske positiver på store, legitime
sites (bt.dk, proff.no) i en live-test. Scriptet dømmer kun sitet selv, aldrig hvordan det
performede.

Læs `scored.json`. Høj-bånd behøver intet websøg (allerede afgjort af stærke signaler). Lav-bånd
betyder nu udelukkende "nul signaler ramte" — intet at gennemgå, intet websøg. Al reel tvivl, selv
fra ét enkelt svagt signal, lander i den usikre gruppe — det er dér arbejdet foregår.

**Sidste sikkerhedsnet, billigt og uden opslag:** før du skriver rapporten, kast et hurtigt blik
over lav-bånd-listen (den skal jo vises kort i rapporten alligevel). Springer et domænenavn i
øjnene som gambling/spil/voksenindhold på trods af nul scriptsignaler, nævn det som en fodnote —
forvent at dette sjældent sker, fordi banding-reglen er designet til at fange den slags allerede.

## Trin 4 — Websøg kun på den usikre gruppe (tier 3, loft-begrænset)

For hver placering med `tier3_eligible: true` i `scored.json` (de øverste ~15-20 i den usikre
gruppe, sorteret efter FORBRUG — cost-first, se Baggrund):

1. Foretræk et websøg ("hvad er [domæne] for et site") frem for et rå side-fetch. Billigere,
   hurtigere, og mere robust mod cloaking/bot-blokering — gambling- og MFA-sites bruger ofte netop
   dét til at undgå scrapere. Et fetch der bliver blokeret er i sig selv et svagt "måske
   junk"-signal.
2. Fald kun tilbage til et direkte fetch hvis søgningen ikke giver noget brugbart.
3. Giv placeringen en kort dansk vurdering ud fra resultatet: "gambling-site", "content-farm/
   clickbait", "legitimt nyhedssite, sandsynligvis fejlplaceret targeting", osv. Dette er
   model-dømmekraft — brug sund fornuft, ikke kun et keyword-match.

Loftet er bevidst — et websøg koster mere end et lokalt scoretjek, og det holder omkostningen nede
på en konto med hundredvis af usikre placeringer. Sig altid i rapporten hvor mange der blev slået
op vs. hvor mange der ligger som "kræver manuel gennemgang".

**Undtagelse — blocklist- og gambling-nøgleord-hits springer altid køen, uanset loft.** Sorteringen
er nu cost-first, så et lavt-forbrug gambling-fund kan i princippet stadig havne under loftet bag
høj-forbrug placeringer der kun har en risikabel-TLD eller slet intet signal. En placering der
scorer via `blocklist:*` eller `gambling_keyword_in_domain` skal altid med i websøgs-runden, uanset
dens `tier3_rank` og uanset forbrug — disse to signaler peger specifikt på gambling/junk-kategori og
fortjener altid et opslag, uanset hvor lidt der er brugt. Filtrér `scored.json` på `"blocklist:"`
eller `"gambling_keyword_in_domain"` i `signals`, tilføj dem til websøgs-runden selvom
`tier3_eligible` er `false`, og nævn eksplicit i rapporten at de blev prioriteret ud over loftet.

## Trin 5 — Byg den rangerede rapport (i chatten, ikke .xlsx som default)

**Output er en markdown-tabel i selve chat-svaret, ikke en fil.** Byg kun en `.xlsx` hvis brugeren
eksplicit beder om det (typisk fordi de vil sende den til en kunde til godkendelse — en anden
brugssituation end den interne ekspert-gennemgang dette skill primært er til).

**Målgruppen er en ikke-teknisk Google Ads-ekspert, ikke en analytiker.** De kender ikke GAQL,
"criterion_id", "score" som begreb, eller navne som `zero_conv_at_spend`. De ved hvad en placering
er, hvad gambling/klikfarme er, og hvad de vil gøre ved dem: ekskludere eller lade være. Rapporten
skal læses som en kollegas anbefaling, ikke som et system-output — **ingen interne signalnavne,
ingen "Score"-tal som selvstændig kolonne, ingen "unikke placering×kampagne-kombinationer"-sprog.**
Hvis du skriver en sætning en marketingmedarbejder ville spørge "hvad betyder det?" til, omskriv den.

Grupér efter **hvorfor** en placering er et problem, ikke efter det interne score-bånd. Brug almindeligt
sprog for kategorien (gambling/spil, mistænkelige småsider, pakke-sporing/støj, osv.) og lad
score/signaler blive til den bagvedliggende BEGRUNDELSE i prosa — aldrig en synlig kolonne.

### Fast rapport-skabelon (brug PRÆCIS disse 5 sektioner, i denne rækkefølge, altid)

Dette er ikke et løst eksempel — det er den bindende struktur. Samme overskrifter, samme
rækkefølge, samme emoji, hver gang, uanset klient eller kørsel. Konsistens på tværs af kørsler
betyder mere end at finpudse ordlyden per gang; en ekspert der kører skillet på flere klienter skal
kunne genkende rapporten uden at læse den forfra hver gang.

**Global regel for alle 5 sektioner:** flere placering×kampagne-rækker på SAMME domæne slås sammen
til ÉN linje i rapporten (læg forbrug sammen, nævn "flere kampagner" hvis relevant) — vis aldrig
samme domæne to gange i samme sektion. Domænet er hvad eksperten handler på, ikke rækken.

```markdown
## Display-placement-audit — <klient> — <vindue>

**Kort sagt:** annoncerne har vist sig på <N> forskellige steder i perioden. <M> af dem bør I
overveje at fjerne — <kort hvorfor, fx "gambling-sider og useriøse klikfarme">. Resten er enten
fint, eller I har allerede blokeret det.

### 🚫 Anbefales fjernet — <N> steder, <samlet forbrug> kr
Placeringer hvor et lokalt signal ELLER et websøg gjorde konklusionen tydelig nok til at anbefale
en handling. Grupér i almindeligt-sprog-underkategorier (gambling/spil, content-farme/klikfarme,
useriøse apps, osv.) — ikke efter score.

Gambling og spil
- **<domæne>** — <hvad det er, én linje, fx "dansk lotteri-side">. <forbrug> kr brugt, <konv> konv.

Useriøse/content-farme
- **<domæne>** — <hvad det er>. <forbrug> kr brugt, <konv> konv.
- (Er der mange ens content-farm-fund: "+N steder til på samme mønster (`.top`/`.xyz`-endelser),
  se den fulde liste hvis I vil have alle med i skrivningen" — men navngiv altid mindst de 3-5
  dyreste enkeltvis, saml aldrig ALT under ét "+N til".)

### 🤔 Værd at kigge på — <N> steder, <samlet forbrug> kr
Reelt tvetydige tilfælde: et svagt signal (fx en risikabel endelse) uden et bekræftende websøg,
enten fordi websøget var inkonklusivt ELLER fordi placeringen lå uden for opslags-loftet. Eksperten
tager stilling, ikke skillet.
- **<domæne>** — <kort hvorfor det er tvivlsomt, og om det blev websøgt eller ej>. <forbrug> kr.
- (Placeringer under loftet, aldrig websøgt: saml dem i én linje "+N steder til, samme
  navnemønster men ikke websøgt (under loft) — se fuld liste ved behov", medmindre en enkelt af
  dem har mærkbart forbrug og fortjener sin egen linje.)

### ✅ Ingen problemer fundet ELLER allerede korrekt vurderet legitimt
To slags rækker samlet i én sektion — begge betyder "ingen handling":
- **Normal trafik** (langt de fleste): "<N> steder havde intet mistænkeligt at bemærke — normal
  Display-trafik, ingen handling. Samlet forbrug: <sum> kr."
- **Bekræftede falske alarmer** (websøgt og renset): navngiv dem individuelt, aldrig kun i summen,
  fordi de så ellers ligner et gæt: "**<domæne>** — så mistænkeligt ud pga. <hvorfor>, men et
  websøg viste <hvad det faktisk er>. Anbefales IKKE fjernet."

### ⚠️ Kan ikke fjernes automatisk (Performance Max)
Performance Max-annoncer viser desværre ikke hvilke sider de kører på med samme detalje, og
Google tillader ikke at blokere specifikke sider på PMax-kampagner. Vi kan ikke gøre noget ved
dette teknisk — kun nævne det hvis noget virker påfaldende. Ingen PMax-data denne kørsel er en
gyldig, forventet tilstand — sig det som en kendsgerning, ikke en fejl: "Performance Max indgår
ikke i denne visning (platform-begrænsning)."

### Allerede håndteret
I har allerede blokeret <N> steder på denne konto tidligere (fx en liste kaldet "Web
placeringer"). De optræder ikke igen ovenfor. Hvis overlap mellem jeres eksisterende
eksklusioner og periodens faktiske trafik er lavt (de fleste blokerede domæner/kanaler dukker
slet ikke op i perioden), sig det ligeud — det er en normal og forventet observation, ikke et
problem: "Jeres eksisterende blokeringer og periodens trafik overlapper kun på <N> sted(er) — det
er forventeligt, blokeringerne dækker typisk andre kanaler end dem der er aktive lige nu."
```

**Under de 5 sektioner, altid, i denne rækkefølge:**
1. En kort dansk konklusion i 2-4 sætninger, almindeligt sprog — de vigtigste mønstre, samlet
   forbrug i "anbefales fjernet", og at børneindhold er et kendt blindt punkt vi ikke kan opdage
   automatisk endnu (skriv DET som "vi kan endnu ikke opdage børneindhold automatisk", ikke som en
   teknisk fodnote om manglende datasæt).
2. Én sætning om hvor mange placeringer der blev slået op via websøg vs. hvor mange der ligger
   uverificeret pga. loftet (samme tal som i "værd at kigge på", men sagt i ord: "Vi har slået de
   <M> dyreste tvivlsomme steder op enkeltvis; resten (<K> steder, tilsammen <sum> kr) har samme
   mistænkelige navnemønster men er ikke tjekket enkeltvis endnu.").
3. **Eksperten redigerer her, i chatten** — fjern rækker, flyt noget fra "værd at kigge på" til
   "fjern det", eller omvendt. Skillet foreslår; mennesket dømmer den endelige liste.

**Ingen sektion droppes, selv når den er tom.** Er der fx ingen PMax-data, eller nul allerede
håndterede overlap, skriv sektionen alligevel med den ærlige "0/ingen"-besked (se skabelon-teksten
ovenfor) — en manglende sektion ligner en fejl, en sektion der siger "ingen fund her" er tydelig.

## Trin 6 — Bekræft, så skriv (human-in-the-loop, ingen undtagelse)

Når eksperten har sagt hvilke rækker der skal ekskluderes (implicit "kør med rapporten som den
står" tæller også, hvis intet blev ændret), byg den endelige liste og vis den én gang mere som et
eksplicit forslag før noget rammer kontoen:

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
   UI'et: domæne/app/kanal + type + anbefalet niveau (kampagne vs. delt liste, se nedenfor) +
   match/eksklusionstype.
3. Nævn at dette er en midlertidig begrænsning i værktøjssættet — når/hvis MCP'en får en
   `add_negative_placement`-lignende funktion, opdatér dette trin til at bruge den direkte.

Finder `ads-writer` faktisk en fungerende write-vej (fx et generisk mutate-værktøj), brug den —
ovenstående er en dokumenteret antagelse pr. build-tidspunkt, ikke en hård regel om aldrig at prøve.

**Kampagne vs. delt liste — spørg, gæt aldrig.** For hver bekræftet ekskludering: spørg eksperten
om den skal gå på den specifikke kampagne eller ind i en eksisterende delt negativliste på kontoen
(vis hvilke delte `NEGATIVE_PLACEMENTS`-lister der allerede findes fra Trin 2, fx "Web
placeringer", "Børneplaceringer"). Det er en klient- og situationsafhængig beslutning eksperten
selv skal tage i øjeblikket.

## Trin 7 — Output

Lever, i almindeligt sprog (samme regel som Trin 5 — ingen interne termer):
1. **Rapporten** (Trin 5) — allerede vist i chatten.
2. **Hvad der faktisk skete ved skrivningen** — hvilke sider/apps/kanaler blev rent faktisk
   blokeret, om det landede på selve kampagnen eller en delt liste, og — hvis Google Ads-værktøjet
   ikke understøttede det endnu — at I i stedet får en færdig liste til at indsætte manuelt i
   Google Ads Editor.
3. **De to ærlige forbehold, skrevet så alle forstår dem:** "vi kan endnu ikke opdage
   børneindhold automatisk" og "nogle rigtige gambling-/lotteri-sider bliver muligvis ikke fanget
   automatisk — hold øje med mistænkelige navne i den brede liste, ikke kun i 'anbefales fjernet'."
   PMax nævnes kort: "Performance Max viser desværre ikke placeringer detaljeret nok til at vi kan
   foreslå noget der."
4. **Hvor tallene kommer fra** — én kort sætning, ikke en teknisk logliste: "Data er hentet direkte
   fra jeres Google Ads-konto (placeringsrapporten for perioden) og krydstjekket mod jeres
   eksisterende blokeringer, så I ikke får de samme forslag to gange."

## Eksempel-output (fra live-verificering, DBI, kørt 2026-07-03 med det faste skabelon)

Alle 5 sektioner er med, i den faste rækkefølge, også der hvor der ikke var noget at rapportere
(Performance Max, Allerede håndteret) — det er skabelonens pointe, ikke noget der udelades for at
holde svaret kort.

```
Display-placement-audit klar — DBI, sidste 90 dage.

Kort sagt: annoncerne har vist sig på ~9.300 forskellige steder i perioden. 15 af dem bør I
overveje at fjerne — gambling-/lotteri-sider og useriøse content-farme. Resten er enten fint,
eller allerede blokeret.

🚫 Anbefales fjernet (15 steder, ~131 kr brugt):
Gambling og spil
- nlcbplaywhelotto.com — lotteri-resultatside, Trinidad & Tobago. 0,6 kr, 0 konv.
- lottosociety.com — thailandsk aktie-lotteri-side. 0 kr, 0 konv.
- tippetips.info — norsk betting-tips-side. 3,9 kr, 0 konv.

Useriøse content-farme/klikfarker
- enjoygrid.top — tom content-farm-skabelon, intet reelt indhold. 39,5 kr, 0 konv.
- pastimehub.top — samme skabelon som enjoygrid.top. 14,1 kr, 0 konv.
- poiy.online — spundet finans-fyld-indhold på flere underdomæner. 10,2 kr, 0 konv.
- promocodes.club — generisk rabatkode-side. 10,5 kr, 0 konv.
- +8 steder til på samme mønster (`.top`/`.xyz`/`.club`-endelser, tomme skabelon-sider),
  tilsammen ~53 kr — se fuld liste hvis I vil have alle med i skrivningen.

🤔 Værd at kigge på (38 steder, ~76 kr brugt):
- bestenrezepte.top — tysk opskrifts-aggregator, lav kvalitet men ikke gambling/scam. Websøgt,
  inkonklusivt. Jeres kald.
- +37 steder til, samme mistænkelige navnemønster (`.online`/`.top`-endelser) men ikke websøgt
  enkeltvis (lå under opslagsloftet, alle under 2 kr hver) — se fuld liste ved behov.

✅ Ingen problemer fundet eller bekræftet legitimt:
- ~9.250 steder havde intet mistænkeligt at bemærke — normal Display-trafik, ingen handling.
  Samlet forbrug: 9.751 kr.
- tipsbladet.dk — så mistænkeligt ud pga. ordet "tips" i navnet, men et websøg viste at det er et
  etableret dansk fodboldmedie (Better Collective). Anbefales IKKE fjernet.
- intipseleb.com — samme mønster, viste sig at være et etableret indonesisk kendismedie.
  Anbefales IKKE fjernet.

⚠️ Performance Max: ingen PMax-data i denne visning (platform-begrænsning) — ikke fordi der intet
kører, men fordi Google Ads ikke deler placeringsdata for PMax med samme detalje.

Allerede håndteret: jeres tre delte negativlister overlappede kun med periodens faktiske trafik på
1 sted — det er forventeligt, blokeringerne dækker typisk andre kanaler end dem der er aktive lige
nu.

Vi har slået de 20 dyreste/mest mistænkelige steder op enkeltvis; resten (38 steder, ~76 kr) har
samme mistænkelige navnemønster men er ikke tjekket enkeltvis endnu.

Bekræft de 15 anbefalede fjernelser for at skrive dem til kontoen, eller sig til hvis I vil justere
listen først.
```

## Hårde grænser

- Skriv kun til kontoen efter eksplicit bekræftelse — ingen undtagelse.
- Foreslå aldrig noget der allerede er ekskluderet — krydstjek er obligatorisk (Trin 2 + 3).
- Byg aldrig en permanent/delt liste automatisk — kun de bekræftede negativer for netop denne
  kørsel skrives; hvilken delt liste (hvis nogen) er et eksplicit valg eksperten tager per kørsel.
- Pausede kampagner flages aldrig som et fund — de er bevidste hos Inbound.
- PMax-fund skrives aldrig — kun forslag, platform-begrænsning.
- Børneindhold-dækning er ikke påstået — intet gratis signal findes, sig det højt.
- Æ Ø Å altid i alt dansk output — aldrig ASCII-translitteration.
- Lyv aldrig om en skrivning der ikke skete — mangler write-vejen i MCP'en, sig det og lever det
  manuelle fald-tilbage.

## Maintenance

- `scripts/score_placements.py` — den eneste deterministiske del. Matcher blocklist, TLD,
  gambling-nøgleord, app-flag, allerede-ekskluderet-tjek — bevidst KUN site-signaler, ingen
  performance-signaler (forbrug/konvertering/CTR blev fjernet 2026-07-03, se Baggrund). Ingen
  model-dømmekraft heri; ret aldrig scoringen til at "dømme" i stedet for at signalere, og tilføj
  ikke et performance-baseret signal igen uden at genoverveje hele "Redesign 2026-07-03"-afsnittet.
- `references/junk_domains.tsv` — 9.834 domæner (gambling + MFA-proxy + scam), bygget fra Blocklist
  Project + Steven Black's hosts, begge fri licens. Se `junk_domains_SOURCES.md` for fuld
  proveniens, licenser, og genopfrisknings-kommando. Statisk snapshot, ikke en live feed —
  genopfrisk med jævne mellemrum.
- Får Google Ads MCP'en en dedikeret negative-placement write-værktøj: opdatér Trin 6's
  platform-hul-sektion til at bruge den direkte i stedet for det manuelle fald-tilbage.
- Bevidst ingen: automatisk delt-liste-bygning, xlsx som default-output, gæt på
  kampagne-vs-delt-liste-niveau. Det er eksplicitte valg fra brugeren om at bevare menneskelig
  kontrol her — automatisér dem ikke.
