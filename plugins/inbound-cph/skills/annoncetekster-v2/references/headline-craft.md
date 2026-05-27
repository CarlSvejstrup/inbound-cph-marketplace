# Headline craft — hvad der faktisk virker i Google Ads RSA (2025/2026)

Læs denne før du skriver annonceteksterne i Trin 4. Reglerne her er ikke smag — de er testede på millioner af annoncer og kobler direkte på Google's Ad Strength-score, disapproval-policies og dokumenterede CTR/CPA-forskelle.

## Mål: 15 headlines med semantisk diversitet

Generer 20-25 kandidater, vælg de 15 bedste. Det giver bedre variation end at presse præcis 15 ud i første forsøg.

## Headline-fordelingen (lås denne)

Brug denne fordeling for hver 15-headline-sæt. Det sikrer at Google's algoritme har råt materiale at teste på tværs af forskellige search-intentioner.

| Angle | Antal | Hvad det er | Dansk eksempel |
|---|---|---|---|
| Brand + keyword | 2 | Brandnavn + det vigtigste keyword | "Securitas alarmsystemer" |
| Keyword-led | 3 | Kerne-keyword først, gerne kort | "Køb alarmsystem i dag" |
| Benefit (outcome) | 3 | Hvad kunden får — resultatet | "Sov trygt om natten" |
| Feature (spec) | 2 | Konkret feature/teknologi | "24/7 overvågning og app" |
| Social proof (numeret) | 1 | Specifikt tal, ikke "mange kunder" | "Trusted by 50.000+ danskere" |
| Urgency / scarcity | 1 | Tidsbegrænset — kræver aktivt tilbud | "Tilbud slutter søndag" |
| CTA (specifik) | 1 | Konkret handling, IKKE "klik her" | "Gratis fragt over 500 kr" |
| Problem / garanti | 1 | Løser et problem eller fjerner risiko | "30 dages returret" |
| Location / segment | 1 | Geo eller målgruppe | "Alarmsystem i København" |

Hvis brugeren ikke har et aktivt tilbud → drop urgency, erstat med en ekstra benefit eller feature.

Hvis klienten ikke har et stort brand → drop den ene brand+keyword og læg den i benefit-bunken.

## Længde-variation

**Bland korte og lange headlines.** Optmyzr's studie på 1M annoncer: headlines <20 tegn hit $9.35 CPA vs $18.27 for længere. CTR 11.77% vs 10.52%. **Det betyder ikke "skriv kun korte"** — det betyder at **variation** (mix af 12-tegn og 28-tegn) slår et set hvor alt er presset op til 30 tegn.

Mål-mix per 15 headlines:
- 4-5 korte (<20 tegn)
- 6-7 mellem (20-26 tegn)
- 3-4 lange (27-30 tegn)

## Sentence case — altid

Skriv "Køb alarmsystem i dag", ikke "Køb Alarmsystem I Dag". Optmyzr måler 3.7× CPA-forskel mellem Sentence og Title case. Det er den enkleste vinder.

Undtagelser: brandnavne (Securitas), egennavne (København), forkortelser (RSA, GDPR).

## Keyword-tilstedeværelse

**Top-keyword skal stå i mindst 3 headlines.** Google's relevans-score løfter Ad Strength fra "Average" til "Good" når keywordet er synligt i annonceteksterne. Brug det i:
- 1 keyword-led headline (positionsfri)
- 1 brand+keyword headline
- 1 benefit eller location headline hvor det passer naturligt

Stuf det ikke ind hvor det er akavet — Google straffer også over-optimering.

## Brand placement

Hvis klienten har et anerkendt brand: læg brandnavnet i headline 1 eller 2 (eller pin det — se nedenfor). ATTN måler +15% Quality Score og -$0.08 CPC.

## Pinning — partial pinning vinder

Default: **pin intet**. Lad Google teste alle kombinationer.

Hvis brandet eller juridiske krav betyder noget skal stå først: pin **2-3 varianter** til position 1 (ikke kun een). Optmyzr: partial pinning slog både no-pin og full-pin på CPA $13.68 / CTR 11.88% / ROAS 365%. Full pinning skærer 75% af kombinations-rummet væk og dræber Ad Strength.

Skillet skriver IKKE pin-instruktioner i .xlsx — pinning sættes i Editor efter import. Nævn det i næste-skridt-blokken hvis klienten har brand-krav.

## Descriptions — 4 stk, hver står alene

Hver beskrivelse skal kunne påres med en hvilken som helst anden description. Skriv ikke sammenhængende sætninger over to descriptions — Google reorderer dem.

Default fordeling for 4 descriptions:
1. Benefit + CTA
2. Feature/proof
3. Trust + risiko-fjerner (garanti, returret)
4. Urgency eller sekundær benefit

## Forbud — auto-disapproval i 2026

Hvis teksten indeholder noget af det her, afviser Google annoncen.

- **Emojis, stjerner (★), pile (→), decorativ Unicode.** Ren tekst og standard-tegn.
- **Superlativer uden bevis:** "bedst", "#1", "garanteret", "billigst", "mirakel". Hvis klienten ER #1 på en målbar metric, skriv det specifikt ("Danmarks mest solgte X" hvis det dokumenterbart står på landingssiden).
- **"Klik her", "klik nu", "klik for mere".** Google's editorial policy afviser generiske CTAs uden context.
- **Konkurrent-brandnavne i headline-tekst.** 2026 trademark-policy: auto-disapproval.
- **Excessive caps ("BUY NOW") eller gentaget tegnsætning ("!!!").**
- **Priser eller tilbud der ikke står på landingssiden.** Hvis landingssiden ikke nævner "gratis fragt", må headline ikke love det.
- **Gentagne headlines** — næsten-identiske formuleringer svækker Ad Strength og dækker ikke nye search-intentioner.

## Patterns der konsistent vinder

- **Specifikke tal slår vage claims.** "Resultater på 7 dage" slog generisk benefit med 23% CTR (ATTN).
- **Numeret social proof.** "50.000+ kunder", "4.8 stjerner fra 2.300 anmeldelser" slår "tusindvis af tilfredse kunder" hver gang.
- **Question headlines:** brug sparsomt. Virker bedst på high-consideration / problem-aware searches ("Træt af falske alarmer?"). Ikke flere end 1 ud af 15.
- **Problem-løsning over feature-dump.** Headline om hvad kunden undgår/opnår slår headline om hvad produktet ER.

## Kvalitets-checks før arket bygges

Før du kører `fill-sheet.py`, gennemgå selv teksten:

1. **Top-keyword i ≥3 headlines?**
2. **Sentence case overalt?** (Tjek for stray Title Case.)
3. **Længde-variation?** Tæl korte/mellem/lange — undgå at alle 15 er 27-30 tegn.
4. **Nogen forbudte ord?** Scan for "bedst", "klik her", emojis, konkurrent-brands.
5. **Brand i position 1 eller 2** hvis brandet betyder noget?
6. **Hver description står alene?** Læs dem i tilfældig rækkefølge.
7. **Alle claims på landingssiden?** Ingen opfundne priser, garantier eller statistikker.

## Maintenance

Hvis Google ændrer disapproval-policy eller Ad Strength-vægtning, opdater denne fil. Kilder løbende re-checkes hvis CTR/CPA-ændringer er mere end 12 måneder gamle:

- [Google official: Your guide to RSAs](https://support.google.com/google-ads/answer/12159142?hl=en)
- [Optmyzr 1M-ad RSA performance study](https://www.optmyzr.com/blog/google-rsa-performance-study/)
- [ATTN Agency 15-headline framework](https://www.attnagency.com/blog/google-ads-responsive-search)
- [Google policy: punctuation and symbols](https://support.google.com/adspolicy/answer/14847994?hl=en)
- [Stub Group: 2026 trademark policy](https://stubgroup.com/blog/google-ads-new-trademark-policy/)
