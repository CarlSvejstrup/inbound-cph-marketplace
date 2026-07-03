# Design-beslutninger — hvorfor scoringen ser ud som den gør

Denne fil holder den fulde begrundelse bag skillets scoring-filosofi og de to redesigns fra
2026-07-03. SKILL.md-kroppen har en kort opsummering; læs denne fil hvis du overvejer at ændre
scoringen, tilføje et signal, eller forstå hvorfor et bestemt signal blev fjernet.

## Hvad Display-placeringer er

Display-annoncer vises på tredjeparts-websites, apps og YouTube, valgt af Googles algoritme ud fra
targeting, ikke en søgning. En live-verificering mod en rigtig Inbound-konto (Dantaxi, 2026-07-01)
viste Display-annoncer kørende på `euro-jackpot.net`, `danskelotto.com` (lotteri), `petsim99.co`
(børne-spil-site) og en håndfuld content-farm-domæner — alt sammen forbrug uden en eneste
konvertering.

## Scoring, ikke en binær dom — men få, håndfaste signaler, ikke en punkt-maskine

Hver placering får et 0-100 risiko-tal bygget additivt af lokale signaler om SELVE SITET
(`scripts/score_placements.py`, se Trin 3): kendt junk-domæne, risikabel TLD, gambling-nøgleord i
navnet, app-netværk-trafik som et strukturelt (ikke site-specifikt) flag, og — gen-indført
2026-07-04, se "Redesign 2026-07-04" nedenfor — forbrug-uden-konvertering som en SVAG tiebreaker
der kun tæller oveni et allerede eksisterende signal. Se "Redesign 2026-07-03" for hvorfor
performance-signaler først blev fjernet helt, og "Redesign 2026-07-04" for hvorfor én kom tilbage
i en anden, ufarlig form.

Banding (grænser opdateret 2026-07-04):

- **Høj (≥50 som standard, sænket fra 70):** afgøres af lokale data alene, intet opslag
  nødvendigt. Typisk et direkte blocklist-match, eller flere signaler lagt sammen (risikabel TLD +
  gambling-nøgleord, eller et signal + tiebreaker).
- **Usikker (alt med mindst ét signal, der ikke rammer høj-grænsen):** fx en risikabel TLD alene,
  et gambling-nøgleord i navnet, evt. med tiebreakeren oveni. Kun de øverste ~15-20 efter FORBRUG
  (se Trin 4) får et websøg; resten markeres "kræver manuel gennemgang". Denne gruppe er bevidst
  bredere igen efter 2026-07-04 — se nedenfor for hvorfor.
- **Lav (ingen signaler overhovedet):** ingen blocklist-match, ingen risikabel TLD, intet
  gambling-nøgleord, intet app-netværk-flag. Tiebreakeren kan IKKE alene løfte en placering ud af
  "lav" — den udløses kun oveni et andet signal. Almindelige sites med højt forbrug og nul
  konvertering (bt.dk-typen) lander derfor stadig her — forventet adfærd, ikke et risikotegn.

Verificeret live (Dantaxi, re-test 2026-07-01): den gamle banding (score < 30 → lav) lod
`spil2vind.dk` (reel dansk gambling-side) forsvinde tavst, fordi dens eneste signal
(`gambling_keyword_in_domain`, vægt 15) ikke alene nåede 30. Med den nuværende regel lander den
korrekt i usikker-gruppen.

## Redesign 2026-07-03 — for skarpt, ikke "for meget flagget"

En live-kørsel på DBI viste at `bt.dk`, `proff.no` og `mentedidactica.com` — alle sammen legitime,
store sites — landede i "usikker" udelukkende fordi de brugte penge uden at konvertere på Display,
eller havde en CTR-anomali. Det er ikke junk, det er helt normal Display-adfærd: lav CTR og lav
konvertering er reglen, ikke undtagelsen, for banner-annoncer på store sider. At bruge det som et
risikosignal producerede en stor, useriøs "usikker"-bunke fyldt med sund fornuft-tilfælde i stedet
for reelle kandidater. De to signaler (`zero_conv_at_spend`, `ctr_too_low`/`ctr_too_high`) er derfor
fjernet helt fra scriptet — de sagde noget om KONTOENS performance, ikke om SITETS kvalitet, og de
to ting er ikke det samme. Tilbage er kun signaler der faktisk identificerer sitet: er det på en
kendt junk-liste, har det en risikabel endelse, hedder det noget med gambling, eller er det
app-trafik.

Cost-first er den anden del af samme fix: rapporten og websøgs-loftet prioriterer nu efter FORBRUG,
ikke efter score (se Trin 4-5) — eksperten skal bruge tiden der hvor pengene faktisk er, ikke der
hvor et scoretal tilfældigvis er højest.

Høj-grænsen (70) og loftet (15-20) er parametre eksperten kan justere per kørsel ("vær strengere
denne gang"), ikke faste konstanter. Der er bevidst intet separat "lav-grænse"-parameter — "lav"
betyder nu udelukkende "nul signaler".

## Redesign 2026-07-03, del 2 — hårdt ekskluderingslag + kortere output

Efter det første redesign (over) kom to yderligere justeringer, samme dag:

1. Inbound har selv en manuel ekskluderingsliste de bruger én-to gange om måneden på tværs af
   klienter (kilde: intern Doc + regneark) — den er nu bundlet direkte i skillet som et fjerde,
   hårdere bånd (`references/hard_exclusions.tsv` + `references/hard_exclusion_patterns.py`, se
   `references/hard-exclusions-catalog.md`), der springer scoring og websøg helt over fordi det er
   et klient-bekræftet valg, ikke en heuristik.
2. Standard-rapporten er gjort markant kortere — kun "anbefales fjernet" og "værd at kigge på" som
   tabeller med domæne/forbrug/klik/konv/kort-hvorfor, ingen prosa-konklusion, ingen
   PMax/allerede-håndteret-sektioner medmindre eksperten selv beder om uddybning (se Trin 5).
   Begrundelsen er brugsmønsteret: skillet køres én-to gange om måneden af en ekspert der vil se
   hvad der skal handles på, ikke læse en rapport.

## Redesign 2026-07-04 — bevidst bredere net, eksplicit brugerdirektiv

Efter at have kørt skillet i praksis kom feedback: det narrowede script fra 2026-07-03 lod nu reel
junk glide igennem som "lav" — for stramt i den anden retning. Brugerens eksplicite direktiv: false
negatives (junk der forbliver usynligt) koster mere end false positives (et par ekstra legitime
sites i "usikker" til et hurtigt menneskeligt kig). To ændringer, begge i `score_placements.py`:

1. **`zero_conv_at_spend` genindført, men KUN som en svag tiebreaker.** Vægt 8, og — kritisk
   forskel fra versionen fjernet 2026-07-03 — den udløses ALDRIG standalone. Den tæller kun oveni
   et allerede eksisterende site-signal (`score_placement()`: tjekker `if signals and cost_micros
   >= floor and conversions == 0`). Den gamle version anvendte samme logik på ALLE placeringer
   uafhængigt af andre signaler, hvilket er præcis hvorfor den fangede bt.dk/proff.no/
   mentedidactica.com — store, legitime sites hvor lav Display-konvertering er normalt, ikke et
   symptom. Den nye version kan aldrig alene flytte en signal-fri placering ud af "lav"; den kan
   kun skubbe en placering der allerede har en anden grund til mistanke lidt højere op.
2. **`--high-threshold` sænket fra 70 til 50.** Gør det lettere for kombinerede signaler (risikabel
   TLD + gambling-nøgleord, eller ét signal + tiebreakeren) at nå "høj"-båndet uden at kræve et
   direkte blocklist-match alene.

**Hvorfor dette ikke er det samme fejltrin som 2026-07-03:** forskellen er gating, ikke vægt. Den
gamle fejl var at lade et performance-signal afgøre båndet PÅ EGEN HÅND. Den nye tiebreaker kan
aldrig gøre det — den kræver et site-identitets-signal at hægte sig på, præcis som
gambling-nøgleord- og TLD-signalerne allerede krævede før 2026-07-03 blev tegnet forkert.

**Sund fornuft er stadig et krav, ikke en efterretning.** Sænket høj-grænse og en bredere "usikker"
gruppe betyder flere kandidater at kigge på, ikke flere automatiske fjernelser. Et etableret dansk
medie- eller erhvervssite skal ALDRIG anbefales fjernet i rapporten bare fordi det rammer et enkelt
svagt signal + tiebreakeren — Trin 5's "værd at kigge på"-sektion findes netop til den slags, og
modellen skal stadig anvende dømmekraft før noget lander i "anbefales fjernet". Testet direkte mod
bt.dk/proff.no/normalsite.dk (høj forbrug, nul konvertering, ingen site-signaler) — de forbliver i
"lav" efter denne ændring, som de skal.

## Ingen permanent negativliste bygges af dette skill

Blocklisten, TLD-reglerne og scoringslogikken bor bundlet i skillet (`references/junk_domains.tsv`),
ikke skrevet til en delt Google Ads shared_set automatisk. Hver kørsel er selvstændig: læser 90
dages data, scorer med skillets egne regler, viser rapporten, og skriver kun de negativer eksperten
bekræfter for netop den kørsel. Vil eksperten proppe dem ind i en eksisterende delt liste, er det et
bevidst valg taget i selve kørslen.

## Kendte huller (honest gaps)

- **Børneindhold:** ingen gratis, aktivt vedligeholdt liste over børne-content-domæner findes.
  Skillet fanger noget af det indirekte via app-netværk-flaget og det hårde ekskluderingslags
  kids-kategori, men detekterer ikke børneindhold direkte. Sig det højt i outputtet.
- **Blocklisten rammer ikke alt gambling.** Community-DNS-blocklister (Blocklist Project, Steven
  Black) fanger casino/betting-brands, men misser typisk legitimt udseende lotteri-resultat-sider —
  `euro-jackpot.net` og `danskelotto.com` scorede 0 på blocklist-match alene i testen. Scriptet har
  et navnemønster-baseret backstop for dette, men det er lavpræcision — læs domænenavnene i den
  lave/usikre gruppe med sund fornuft, ikke kun tallet.
- **PMax-begrænsning (platform-fakta):** Google Ads API'en understøtter ikke direkte
  placement-exclusion på Performance Max-kampagner. Skillet kan læse PMax-placeringsdata, men
  PMax-fund er forslag-kun og skrives aldrig til kontoen. Marker det per fund i rapporten: "PMax —
  kun forslag, kan ikke auto-skrives."

## Skrevet til eksperten, ikke til en analytiker (gælder HELE skillet)

De der bruger dette skill kender Google Ads som fagområde, men ikke GAQL, "criterion_id", interne
score-tal, eller signalnavne som `zero_conv_at_spend`. Det gælder alt brugervendt tekst — intake-
spørgsmål, statusbeskeder undervejs, bekræftelses-prompten før en skrivning, og selve rapporten.
Skriv som du ville forklare det til en kollega over kaffen: hvad der er fundet, hvorfor det er et
problem, og hvad de kan gøre ved det. Interne detaljer (GAQL, score, criterion-ID'er) er
implementeringsdetaljer der styrer HVORDAN skillet arbejder — de skal ALDRIG lække ud i noget
brugeren læser.
