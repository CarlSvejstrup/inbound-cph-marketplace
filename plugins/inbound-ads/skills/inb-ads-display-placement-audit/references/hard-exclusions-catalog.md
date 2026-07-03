# Hårdt ekskluderingslag — Inbound's eget standing filter, ikke skillets heuristik

Dette er det fulde katalog bag det hårde ekskluderingslag. SKILL.md-kroppen har en kort
opsummering (hard-exclusion-liste tjekkes først; ethvert match → anbefales fjernet, intet websøg).
Læs denne fil hvis Inbound reviderer listen, eller hvis du er i tvivl om hvad der hører hjemme i det
hårde lag vs. et almindeligt scoringssignal.

Inbound har selv brugt en manuel ekskluderingsliste én til to gange om måneden på tværs af klienter
(kilde: intern Doc + regneark, indlæst 2026-07-03). Den er bundlet i skillet som to filer:

- **`references/hard_exclusions.tsv`** — 191 konkrete domæner i kategorier som gaming-portaler,
  børneindhold, MFA-quiz/listicle/opskrift/kupon/content-farm-sites, dating-sites, sports-medier,
  parkerede domæner. Inkluderer bevidst også store, kendte platforme (twitch.tv, roblox.com,
  pinterest.com, medium.com, wordpress.com, wix.com, espn.com, tinder.com, dictionary.com, msn.com,
  vimeo.com m.fl.) — det ER Inbound's eget valg, ikke en fejl. Se filens header-kommentar hvis denne
  liste nogensinde skal genovervejes.
- **`references/hard_exclusion_patterns.py`** — tre yderligere matchtyper fra samme kilde:
  1. **Nøgleord** ("børn", "spil", "gaming", "game", "quiz", "kid(s/z)", "barn", ".io") —
     contains-match, case-insensitive, mod domæne + display_name.
  2. **Fremmede TLD'er** (~170 landekoder fra Inbound's liste) — exact-suffix match. `.dk .se .no
     .fi .de .uk .com .net .org` er bevidst UNDTAGET denne liste (selv om nogle af dem er
     landekoder) for ikke at gentage bt.dk/proff.no-fejlen — Nordisk/target-market-trafik er
     forventet, ikke mistænkelig.
  3. **Ikke-latinske skrifttegn** (11 alfabeter fra kildedokumentet: Hindi/Marathi Devanagari,
     Arabisk, Bengali, Kyrillisk, Urdu, Japansk Hiragana/Katakana, Telugu, Koreansk Hangul, Tamil)
     — matcher ét enkelt tegn i domæne eller display_name.

## Hvorfor det er adskilt fra junk_domains.tsv

Denne liste er BEVIDST adskilt fra det almindelige `junk_domains.tsv`-blocklist-signal: den
almindelige blocklist er skillets egen, generelle heuristik (probabilistisk, går ind i scoringen).
Det hårde lag er Inbound's EGET, klient-bekræftede standing-valg — derfor omgår det scoring helt i
stedet for at lægge point til. Bland aldrig de to lag sammen.

Provenance-note (Mainstream rows-beslutningen 2026-07-03): hele Inbounds liste, inkl. store
platforme som twitch.tv/roblox.com, blev bevidst gjort til et hårdt match, ikke et scoringssignal.

## Kendt, bevidst hul — "High-Cost Low-Performance"

Kildearket (dateret feb. 2026) nævner også en kategori for dyre, høj-CPM premium-medier med lav ROI
for direkte annoncører (arket navngiver selv NYT og CNN som eksempler) — MEN med en eksplicit note
om at disse kun bør ekskluderes hvis kunden er budget-bevidst og IKKE kører brand-awareness-kampagner.
Det er en kontekstafhængig afvejning, ikke et junk-signal, og hører derfor ALDRIG hjemme i det hårde
lag selv hvis en konkret domæneliste dukker op senere — den skal i så fald ind som et separat, blødt
scoringssignal (lander i "usikker" til et menneskeligt kald), aldrig som en automatisk fjernelse.
Ingen domæneliste for denne kategori er modtaget endnu (2026-07-03) — byg ikke en op af gæt.

## Sidste sikkerhedsnet, billigt og uden opslag

Før du skriver rapporten, kast et hurtigt blik over lav-bånd-listen (den skal jo vises kort i
rapporten alligevel). Springer et domænenavn i øjnene som gambling/spil/voksenindhold på trods af
nul scriptsignaler, nævn det som en fodnote — forvent at dette sjældent sker, fordi banding-reglen
er designet til at fange den slags allerede.

## Vedligehold

Opdatér `hard_exclusions.tsv` + `hard_exclusion_patterns.py` direkte hvis Inbound reviderer deres
liste — spørg først om nye kategorier skal være hårde ekskluderinger eller almindelige
scoringssignaler, bland aldrig de to lag sammen uden eksplicit brugervalg.
