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

Hver placering får et 0-100 risiko-tal bygget additivt af tre lokale signaler om SELVE SITET
(`scripts/score_placements.py`, se Trin 3): kendt junk-domæne, risikabel TLD, gambling-nøgleord i
navnet, plus app-netværk-trafik som et strukturelt (ikke site-specifikt) flag. Det er bevidst kun
disse — se "Redesign 2026-07-03" nedenfor for hvorfor performance-baserede signaler (forbrug uden
konvertering, CTR-anomali) er fjernet helt.

Banding:

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
