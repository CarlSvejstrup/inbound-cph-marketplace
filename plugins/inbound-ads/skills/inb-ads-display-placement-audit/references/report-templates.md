# Rapport-skabeloner — Trin 5

SKILL.md-kroppen har en kort opsummering af default-visningen (de to tabeller) og hvornår man
uddyber. Denne fil holder de fulde skabeloner, den uddybede 5-sektions-rapport og et eksempel-output.

## Generelle regler (gælder begge visninger)

**Målgruppen er en ikke-teknisk Google Ads-ekspert, ikke en analytiker.** De kender ikke GAQL,
"criterion_id", "score" som begreb, eller navne som `zero_conv_at_spend`. De ved hvad en placering
er, hvad gambling/klikfarme er, og hvad de vil gøre ved dem: ekskludere eller lade være. Rapporten
skal læses som en kollegas anbefaling, ikke som et system-output — **ingen interne signalnavne,
ingen "Score"-tal som selvstændig kolonne.** Hvis du skriver en sætning en marketingmedarbejder
ville spørge "hvad betyder det?" til, omskriv den.

**Global dedup-regel:** flere placering×kampagne-rækker på SAMME domæne slås sammen til ÉN linje
(læg forbrug sammen) — vis aldrig samme domæne to gange.

**Eksperten redigerer altid i chatten** — fjern rækker, flyt noget mellem sektionerne, uanset om det
er default- eller uddybet visning. Skillet foreslår; mennesket dømmer den endelige liste.

## Standard-output er BARE, ikke det fulde skema (redesign 2026-07-03)

**Default er kort.** Eksperten kører dette skill én-to gange om måneden og vil se hvad der skal
fjernes og hvad der er tvivlsomt — ikke en afhandling. Vis KUN to sektioner som standard:

```markdown
## Display-placement-audit — <klient> — <vindue>

### 🚫 Anbefales fjernet (<N> steder, <samlet forbrug> kr)
| Sted | Forbrug | Klik | Konv | Hvorfor |
|---|---|---|---|---|
| **<domæne>** | <forbrug> kr | <klik> | <konv> | <3-6 ord, fx "på Inbounds gaming-liste"> |

### 🤔 Værd at kigge på (<N> steder, <samlet forbrug> kr)
| Sted | Forbrug | Klik | Konv | Hvorfor |
|---|---|---|---|---|
| **<domæne>** | <forbrug> kr | <klik> | <konv> | <3-6 ord, fx "risikabel endelse, ikke websøgt"> |

Bekræft de <N> fjernelser for at skrive dem til kontoen, eller sig til hvis du vil justere listen
eller se flere detaljer.
```

Det er hele default-svaret. Ingen indledende "Kort sagt"-afsnit, ingen "Ingen problemer
fundet"-sektion, ingen PMax-afsnit, ingen "Allerede håndteret"-afsnit, ingen afsluttende konklusion
i prosa — kun de to tabeller plus én linje der beder om bekræftelse. "Hvorfor"-kolonnen er PRÆCIS
nok til at eksperten kan handle (kategori-navn, kort begrundelse), aldrig en hel sætning.

**"Anbefales fjernet" inkluderer BÅDE hard_exclusion- og high-bånd** i samme tabel — begge er
allerede besluttede, forskellen (Inbounds egen liste vs. skillets scoring) er en
implementeringsdetalje eksperten ikke behøver se i default-visningen. Brug "Hvorfor"-kolonnen til at
antyde kilden kort ("på Inbounds ekskl.-liste" vs. "blocklist-match") kun hvis det er nyttigt, ellers
bare kategorien.

**"Værd at kigge på" viser KUN dem der reelt kræver et menneskeligt blik** — dvs. `tier3_eligible`
(blev websøgt) ELLER blocklist/gambling-keyword-hits der sprang køen (se Trin 4). Placeringer i
"unsure" der ligger under loftet og ALDRIG blev websøgt, samles i én linje for sig i bunden af samme
tabel: "+<K> steder til, samme mønster men ikke tjekket enkeltvis (under loft), tilsammen <sum> kr —
spørg om fuld liste hvis relevant." Drop dem aldrig helt, men lad dem heller ikke fylde tabellen ud
enkeltvis.

## Uddybet visning — kun når eksperten selv beder om det

Triggerord: "uddyb", "mere detaljer", "hvorfor er de her", "vis mig alt", "hvad med PMax/allerede
håndteret", eller en direkte forespørgsel om ét specifikt domæne. Byg da den fulde 5-sektions
rapport (nedenfor) — men KUN de sektioner der faktisk blev efterspurgt, medmindre eksperten
eksplicit vil have hele skemaet ("vis mig alt" / "uddyb hele rapporten").

Den fulde skabelon, samme struktur som før redesignet, brugt on-demand:

```markdown
### 🚫 Anbefales fjernet — uddybet
Grupér i almindeligt-sprog-underkategorier (gambling/spil, content-farme/klikfarme, Inbounds
standing-liste-kategorier, osv.). For hver: domæne, hvad det er (1 linje), forbrug, konv, og KILDEN
til flaget (Inbounds ekskluderingsliste vs. blocklist vs. websøgt).

### 🤔 Værd at kigge på — uddybet
For hver: hvorfor tvivlsom, blev den websøgt eller ej, og hvad websøget i så fald viste.

### ✅ Ingen problemer fundet ELLER allerede korrekt vurderet legitimt
- **Normal trafik**: "<N> steder havde intet mistænkeligt at bemærke — normal Display-trafik, ingen
  handling. Samlet forbrug: <sum> kr."
- **Bekræftede falske alarmer** (websøgt og renset): navngiv dem individuelt: "**<domæne>** — så
  mistænkeligt ud pga. <hvorfor>, men et websøg viste <hvad det faktisk er>. Anbefales IKKE fjernet."

### ⚠️ Kan ikke fjernes automatisk (Performance Max)
Performance Max-annoncer viser desværre ikke hvilke sider de kører på med samme detalje, og Google
tillader ikke at blokere specifikke sider på PMax-kampagner. Ingen PMax-data denne kørsel er en
gyldig, forventet tilstand: "Performance Max indgår ikke i denne visning (platform-begrænsning)."

### Allerede håndteret
"Jeres eksisterende blokeringer og periodens trafik overlapper kun på <N> sted(er) — det er
forventeligt, blokeringerne dækker typisk andre kanaler end dem der er aktive lige nu." (Lavt overlap
er normalt, ikke et problem — sig det ligeud.)
```

De to ærlige forbehold (børneindhold ikke automatisk detekteret; ikke al gambling fanges) nævnes
KUN i den uddybede visning, ikke i default-svaret — de er kontekst, ikke handling.

## Eksempel-output (baseret på live-verificering, DBI, med det korte default-skabelon)

**Default-svaret** — kun de to tabeller, ingen prosa:

```
## Display-placement-audit — DBI — sidste 90 dage

### 🚫 Anbefales fjernet (18 steder, ~145 kr)
| Sted | Forbrug | Klik | Konv | Hvorfor |
|---|---|---|---|---|
| **nlcbplaywhelotto.com** | 0,6 kr | 0 | 0 | lotteri-side (gambling-nøgleord) |
| **lottosociety.com** | 0 kr | 0 | 0 | lotteri-side (gambling-nøgleord) |
| **tippetips.info** | 3,9 kr | 0 | 0 | betting-tips (gambling-nøgleord) |
| **enjoygrid.top** | 39,5 kr | 3 | 0 | content-farm, risikabel endelse |
| **pastimehub.top** | 14,1 kr | 1 | 0 | content-farm, risikabel endelse |
| **poiy.online** | 10,2 kr | 1 | 0 | content-farm, risikabel endelse |
| **promocodes.club** | 10,5 kr | 0 | 0 | content-farm, risikabel endelse |
| **friv.com** | 8,2 kr | 2 | 0 | på Inbounds ekskl.-liste (gaming) |
| **kizi.com** | 4,1 kr | 0 | 0 | på Inbounds ekskl.-liste (kids) |
| **randomsite.ru** | 2,0 kr | 0 | 0 | på Inbounds ekskl.-liste (fremmed TLD) |
| +8 steder til, samme mønster (.top/.xyz/.club-endelser), tilsammen ~53 kr | | | | |

### 🤔 Værd at kigge på (12 steder, ~64 kr)
| Sted | Forbrug | Klik | Konv | Hvorfor |
|---|---|---|---|---|
| **bestenrezepte.top** | 22 kr | 4 | 0 | risikabel endelse, websøgt — inkonklusivt |
| +11 steder til, samme mønster men ikke tjekket enkeltvis (under loft), tilsammen ~42 kr | | | | |

Bekræft de 18 fjernelser for at skrive dem til kontoen, eller sig til hvis du vil justere listen
eller se flere detaljer.
```

**Hvis eksperten beder om uddybning** ("uddyb 'værd at kigge på'"), tilføjes kun den efterspurgte
sektion, fx:

```
### 🤔 Værd at kigge på — uddybet
- bestenrezepte.top — tysk opskrifts-aggregator, lav kvalitet men ikke gambling/scam. Websøgt,
  inkonklusivt. Jeres kald. 22 kr, 4 klik, 0 konv.
- +11 steder til, samme mistænkelige navnemønster (.online/.top-endelser) men ikke websøgt
  enkeltvis (lå under opslagsloftet, alle under 3 kr hver).
```
