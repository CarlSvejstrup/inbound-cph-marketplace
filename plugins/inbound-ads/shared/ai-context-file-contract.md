# AI Context-fil — format-kontrakt (delt kilde til sandhed)

Den ENE kontrakt for, hvordan en klients "AI Context"-fil på Drive ser ud og hvilken filtype den er.
Både `inb-ads-context-publish` (opretter filen første gang) og `inb-ads-client-brief` (opdaterer den
løbende) skal følge denne fil, så de ikke driver fra hinanden.

## Filtype: native Google Doc (IKKE en rå .md)

Filen er et **native Google Doc**. Den oprettes IKKE med `disableConversionToGoogleType` / som rå
`.md`.

Hvorfor det er låst:
- `inb-ads-client-brief` opdaterer filen i sin helhed via `findAndReplaceInDoc`, som **kun** virker
  på et native Google Doc. En rå `.md` kan ikke redigeres in-place af det værktøj — det var en reel
  bug: en fil publiceret som `.md` kunne ikke opdateres af brief-skillet.
- Ground truth i Drive: 46 af 47 klienter ligger allerede som native Google Docs. Kun Deloitte (ny
  pilot) er en `.md`-outlier, eksplicit flagget som sådan i master-indekset.

Så: `inb-ads-context-publish` opretter et native Google Doc, og formatet matches visuelt til de
eksisterende filer (skelettet nedenfor), så en ny fil ser identisk ud med resten.

## Sektions-skelet (i rækkefølge)

Reproducér denne struktur, så nye filer ligner de eksisterende:

1. **Frontmatter-blok** (ikke en overskrift): `Sidst opdateret: YYYY-MM-DD` · `Rapporter: <mappe-link>`
   · `Seneste rapport læst: <navn> [id: ...]`
2. **Titel-linje:** `<Klient> (<domæne>) - AI Context`
3. **Formåls-linje** (én paragraf): "Operationel kontekst en agent/specialist læser før arbejde på
   kontoen. Kilde til sandhed for denne klient. Google Ads ID ..., HubSpot ...."
4. **`| Felt | Værdi |`-tabel:** Specialist, Tier, Aftaleform, Valuta, Budget/md, Markeder,
   Andre ydelser
5. **Konti & links** — Google Ads konto, Ads link, Bing, Budget pacing ark,
   Optimeringslog / changelog (link til det SEPARATE changelog-dokument)
6. **Kontaktpersoner** — Hos kunden / Hos InboundCPH / Øvrige samarbejdspartnere
7. **Kunderelation & noter** — fri prosa + "Durable aftalefakta (per Aftaleark, sidst ændret ...)"
8. **Klientoverblik** — det tidløse operationelle brief. Undersektioner: Overblik, Hårde rammer
   (læs før du handler), Mål & konverteringer, Sådan kører vi den (Navngivningskonvention,
   Kontostruktur, Kampagnetyper, Brandstemme), Aktuel status & åbne håndtag, Strategisk retning
9. **Rapport** — Kilde + hvad den dækker (erstattes ved hver ny rapport)
10. **Aftaleark & kundebrief** — link + durabel kontekst foldet ind
11. **Drive files** — rangeret: Important / Less relevant, hver `<navn> - <mappe>`

## Klientoverblik er TIDLØST

`Klientoverblik` indeholder ingen point-in-time tal (ingen ROAS/CPA/konverteringstal/antal/
LAST_30_DAYS). Nutids-domme skrives som håndtag ("hæv budget hvor capped", "brand-search betaler de
ikke for"), ikke som målinger. Konfigurerede indstillinger (tCPA, budgetlofter, budstrategi) hører
til — de er indstillinger, ikke målinger. Konkrete performance-tal bor i de daterede audits/rapporter,
og der linkes til dem.

## Master-indekset er en NATIVE TABEL

Master-klientindekset (`Inbound CPH — Google Ads klient-index (AI Context)`, id
`1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`) er en native tabel i et Google Doc. Redigér altid
celler via `editTableCell` / `findAndReplaceInDoc` — brug ALDRIG `insertText` på tabellen, det
ødelægger dens struktur.

## Sprog

Dansk gennemgående, med rigtige Æ Ø Å (aldrig ASCII-translitteration som aa/oe/ae). Engelsk kun for
marketing/tool-vokabular (ROAS, RSA, GA4 osv.).
