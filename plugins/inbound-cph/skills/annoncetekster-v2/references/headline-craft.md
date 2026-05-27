# Headline craft — hvad der faktisk virker i Google Ads RSA (2025/2026)

Laes denne foer du skriver copy i Trin 4. Reglerne her er ikke smag — de er testede paa millioner af annoncer og kobler direkte paa Google's Ad Strength-score, disapproval-policies og dokumenterede CTR/CPA-forskelle.

## Maal: 15 headlines med semantisk diversitet

Generer 20-25 kandidater, vaelg de 15 bedste. Det giver bedre variation end at presse praecis 15 ud i foerste forsoeg.

## Headline-fordelingen (laas denne)

Brug denne fordeling for hver 15-headline-saet. Det sikrer at Google's algoritme har raat materiale at teste paa tvaers af forskellige search-intentioner.

| Angle | Antal | Hvad det er | Dansk eksempel |
|---|---|---|---|
| Brand + keyword | 2 | Brandnavn + det vigtigste keyword | "Securitas alarmsystemer" |
| Keyword-led | 3 | Kerne-keyword foerst, gerne kort | "Koeb alarmsystem i dag" |
| Benefit (outcome) | 3 | Hvad kunden faar — resultatet | "Sov trygt om natten" |
| Feature (spec) | 2 | Konkret feature/teknologi | "24/7 overvaagning og app" |
| Social proof (numeret) | 1 | Specifikt tal, ikke "mange kunder" | "Trusted by 50.000+ danskere" |
| Urgency / scarcity | 1 | Tidsbegraenset — kraever aktivt tilbud | "Tilbud slutter soendag" |
| CTA (specifik) | 1 | Konkret handling, IKKE "klik her" | "Gratis fragt over 500 kr" |
| Problem / garanti | 1 | Loeser et problem eller fjerner risiko | "30 dages returret" |
| Location / segment | 1 | Geo eller maalgruppe | "Alarmsystem i Koebenhavn" |

Hvis brugeren ikke har et aktivt tilbud → drop urgency, erstat med en ekstra benefit eller feature.

Hvis klienten ikke har et stort brand → drop den ene brand+keyword og laeg den i benefit-bunken.

## Laengde-variation

**Bland korte og lange headlines.** Optmyzr's studie paa 1M annoncer: headlines <20 tegn hit $9.35 CPA vs $18.27 for laengere. CTR 11.77% vs 10.52%. **Det betyder ikke "skriv kun korte"** — det betyder at **variation** (mix af 12-tegn og 28-tegn) slaar et set hvor alt er presset op til 30 tegn.

Maal-mix per 15 headlines:
- 4-5 korte (<20 tegn)
- 6-7 mellem (20-26 tegn)
- 3-4 lange (27-30 tegn)

## Sentence case — altid

Skriv "Koeb alarmsystem i dag", ikke "Koeb Alarmsystem I Dag". Optmyzr maaler 3.7× CPA-forskel mellem Sentence og Title case. Det er den enkleste vinder.

Undtagelser: brandnavne (Securitas), egennavne (Koebenhavn), forkortelser (RSA, GDPR).

## Keyword-tilstedevaerelse

**Top-keyword skal staa i mindst 3 headlines.** Google's relevans-score loefter Ad Strength fra "Average" til "Good" naar keywordet er synligt i copy. Brug det i:
- 1 keyword-led headline (positionsfri)
- 1 brand+keyword headline
- 1 benefit eller location headline hvor det passer naturligt

Stuf det ikke ind hvor det er akavet — Google straffer ogsaa over-optimering.

## Brand placement

Hvis klienten har et anerkendt brand: laeg brandnavnet i headline 1 eller 2 (eller pin det — se nedenfor). ATTN maaler +15% Quality Score og -$0.08 CPC.

## Pinning — partial pinning vinder

Default: **pin intet**. Lad Google teste alle kombinationer.

Hvis brandet eller juridiske krav betyder noget skal staa foerst: pin **2-3 varianter** til position 1 (ikke kun een). Optmyzr: partial pinning slog baade no-pin og full-pin paa CPA $13.68 / CTR 11.88% / ROAS 365%. Full pinning skaerer 75% af kombinations-rummet vaek og draeber Ad Strength.

Skillet skriver IKKE pin-instruktioner i .xlsx — pinning saettes i Editor efter import. Naevn det i naeste-skridt-blokken hvis klienten har brand-krav.

## Descriptions — 4 stk, hver staar alene

Hver beskrivelse skal kunne paares med en hvilken som helst anden description. Skriv ikke sammenhaengende saetninger over to descriptions — Google reorderer dem.

Default fordeling for 4 descriptions:
1. Benefit + CTA
2. Feature/proof
3. Trust + risiko-fjerner (garanti, returret)
4. Urgency eller sekundaer benefit

## Forbud — auto-disapproval i 2026

Hvis copy'en indeholder noget af det her, afviser Google annoncen.

- **Emojis, stjerner (★), pile (→), decorativ Unicode.** Ren tekst og standard-tegn.
- **Superlativer uden bevis:** "bedst", "#1", "garanteret", "billigst", "mirakel". Hvis klienten ER #1 paa en maalbar metric, skriv det specifikt ("Danmarks mest solgte X" hvis det dokumenterbart staar paa landingssiden).
- **"Klik her", "klik nu", "klik for mere".** Google's editorial policy afviser generiske CTAs uden context.
- **Konkurrent-brandnavne i headline-tekst.** 2026 trademark-policy: auto-disapproval.
- **Excessive caps ("BUY NOW") eller gentaget tegnsaetning ("!!!").**
- **Priser eller tilbud der ikke staar paa landingssiden.** Hvis landingssiden ikke naevner "gratis fragt", maa headline ikke loeve det.
- **Gentagne headlines** — næsten-identiske formuleringer staelker Ad Strength og daekker ikke nye search-intentioner.

## Patterns der konsistent vinder

- **Specifikke tal slaar vage claims.** "Resultater paa 7 dage" slog generisk benefit med 23% CTR (ATTN).
- **Numeret social proof.** "50.000+ kunder", "4.8 stjerner fra 2.300 anmeldelser" slaar "tusindvis af tilfredse kunder" hver gang.
- **Question headlines:** brug sparsomt. Virker bedst paa high-consideration / problem-aware searches ("Traet af falske alarmer?"). Ikke flere end 1 ud af 15.
- **Problem-loesning over feature-dump.** Headline om hvad kunden undgaar/opnaar slaar headline om hvad produktet ER.

## Kvalitets-checks foer arket bygges

Foer du koerer `fill-sheet.py`, gennemgaa selv copy'en:

1. **Top-keyword i ≥3 headlines?**
2. **Sentence case overalt?** (Tjek for stray Title Case.)
3. **Laengde-variation?** Tael korte/mellem/lange — undgaa at alle 15 er 27-30 tegn.
4. **Nogen forbudte ord?** Scan for "bedst", "klik her", emojis, konkurrent-brands.
5. **Brand i position 1 eller 2** hvis brandet betyder noget?
6. **Hver description staar alene?** Laes dem i tilfaeldig raekkefoelge.
7. **Alle claims paa landingssiden?** Ingen opfundne priser, garantier eller statistikker.

## Maintenance

Hvis Google aendrer disapproval-policy eller Ad Strength-vaegtning, opdater denne fil. Kilder loebende re-checkes hvis CTR/CPA-aenstrings er mere end 12 maaneder gamle:

- [Google official: Your guide to RSAs](https://support.google.com/google-ads/answer/12159142?hl=en)
- [Optmyzr 1M-ad RSA performance study](https://www.optmyzr.com/blog/google-rsa-performance-study/)
- [ATTN Agency 15-headline framework](https://www.attnagency.com/blog/google-ads-responsive-search)
- [Google policy: punctuation and symbols](https://support.google.com/adspolicy/answer/14847994?hl=en)
- [Stub Group: 2026 trademark policy](https://stubgroup.com/blog/google-ads-new-trademark-policy/)
