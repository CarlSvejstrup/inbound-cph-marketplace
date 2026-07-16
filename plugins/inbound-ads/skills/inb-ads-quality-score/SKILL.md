---
name: inb-ads-quality-score
description: QS-deep-dive for én Google Ads-konto. Trækker QS på keyword-grain, klynger de værste keywords, mapper hver svag komponent til dens lever, og handler kun efter eksplicit bekræftelse. Landingsside/creative-fixes er anbefal-kun. Brug ved "tjek quality score", "kvalitetsscore", "hvorfor er QS lav", "QS-audit". Adskilt fra account-audit (rapporterer kun) og search-term/rsa-hygiene (andre dimensioner). Svarer på dansk.
---

# inb-ads-quality-score

Find de keywords hvor QS koster penge, hvilken komponent der trækker ned, og hvilken lever der faktisk flytter den. Read-only indtil enighed; kontoskrivning kun via ads-writer, bekræftet per handling.

To forbehold:

- QS er keyword-grain. Ingen ad-group- eller konto-QS — kun keyword-niveau.
- Landingsside er et flag (svag/gennemsnit/stærk), ikke en score. Find aldrig på et tal.
- Fuld kontrakt: `../../shared/quality-score-pull.md`.

## Trin 0 — Klient-kontekst først

Kør `../../shared/client-context-intake.md` før noget andet. Kræver Google Ads-adgang + customer_id.

Fire ting styrer analysen:

- Budstrategi (tCPA/tROAS/manuel) — afgør om en bud-lever giver mening.
- Hårde rammer — hvad du må røre.
- KPI'er — hvilke keywords der er værd at redde.
- Stage — ikke-kunde ≠ antag aktiv retainer.

## Trin 1 — Intake

- Klient + customer_id — bekræft mod AI Context; kun navn kendt → slå id op.
- Vindue — default ~90 dage. Tilbyd Sidste 90 dage, Sidste 30 dage, Andet.
- Output er in-chat som standard.

## Trin 2 — Træk QS

Uddeleger til ads-analyst (read-only): hent QS-data for customer_id i valgt vindue.

```python
from lib.quality_score import date_range_arg
date_range = date_range_arg((start, end))
```

Skriver aldrig til kontoen.

## Trin 3 — Normalisér

```python
from lib.quality_score import normalise_findings
norm = normalise_findings(raw_audit)
```

Giver keyword-grain fund: campaign, ad group, keyword, match type, QS, de tre komponenter, impressions, cost.

## Trin 4 — Klynge + lever-mapping

Klynge værste keywords efter fælles svaghed (ad group / komponent / landingsside).

Map komponent → lever:

- Annonce-relevans svag → RSA-rewrite (anbefal-kun → overlever til rsa-skills).
- Forventet CTR svag → keyword/match-type/struktur (Ads-write → Trin 5).
- Landingsside svag → LP-fix (klient-side, altid anbefal-kun).

Prioritér efter spend/impressions og KPI'er, ikke QS-tal alene. Alt er forslag, aldrig kommando.

## Trin 4.5 — Landingsside-tjek (opt-in)

Kør KUN hvis en klynge har keywords flaget landingsside-svag. Ellers spring over.

Spørg først: "[n] keywords trækkes ned af landingssiden. Vil du have jeg åbner siderne og tjekker hvorfor?" Kør kun ved ja.

Ved ja: hent hver distinkt LP-URL med WebFetch og bedøm to ting mod keyword + annonce-løfte:

- Message-match — leverer sidens H1/brødtekst/CTA det keyword'et og annoncen lover, eller er det en generisk side?
- Intent / konverteringssti — er sidetypen rigtig for søge-intentionen (transaktionelt keyword → ikke en blog-side), og er der en klar konverteringshandling?

Kommer siden tom/tynd tilbage (JS-render) → sig det, gæt ikke. Ingen numerisk LP-score. Fund er klient-side anbefalinger → føres ind i "Anbefal-kun"-tabellen i Trin 6, aldrig en konto-write.

## Trin 5 — Skriv-stien (HITL)

Bekræftede bud- eller keyword-ændringer rutes én ad gangen gennem ads-writer. Den genformulerer ændringen, beder om ja, skriver kun derpå.

tCPA/tROAS-konti: foreslå mål-/struktur-justering, ikke rå bud.

## Trin 6 — Output (fast skabelon)

Følger Inbounds **report house style** (beskrevet inline her; dybere forfatter-vejledning i
`inbound-skill-creator`): led med svaret, skjul plumbing (komponent-enum-navne, GAQL, tool-navne),
tilbyd dybden frem for at dumpe. Den faste skabelon nedenfor ER house-style-spinen for dette skill
(BLUF-overblik → handlinger delt i to spande → fund sorteret efter cost → forbehold i bunden). Kan
leveres "i chatten" (default, skabelonen nedenfor) eller "som side" (delbar artifact fra
`../../shared/report-template.html`) hvis brugeren vil dele den. Spørg kun hvis det ikke er oplyst.

Kun tabeller. QS-cellen farvekodes på sin egen skala: 🔴 1-3 · 🟡 4-6 · 🟢 7-10 (QS-tal, ikke
status-pill). Klynge-rækkens status-pill følger house-vokaben (🔴 koster penge nu · 🟠 hold øje ·
⚪ neutral).

```markdown
## QS-overblik — [Klient] ([customer_id])
Vindue: [dato–dato] · Gns. QS: [x]/10 · Keywords: [n]
🔴 [n] · 🟡 [n] · 🟢 [n]

## Værste klynger (sorteret efter cost)
| | Ad group | Keywords | QS | Komponent | Lever | Cost |
|---|---|---|---|---|---|---|
| 🔴 | [navn] | [kw, kw] | [x] | [relevans/ctr/lp] | [rewrite/match-type/lp-fix] | [kr] |

## Ads-side (→ ads-writer)
| Ad group/keyword | Ændring | Hvorfor |
|---|---|---|

## Anbefal-kun (LP/RSA)
| Ad group/keyword | Fund | Fix | Ejer |
|---|---|---|---|
```

LP-rækker (hvis Trin 4.5 kørt): Fund = hvad der ikke matcher (message-match / intent), Fix = konkret sideændring, Ejer = klient.

[Hvis lavt volumen] ⚠️ Lav sikkerhed — [n] keywords/[n] impressions.

Tom spand → "Ingen fund", ikke sprunget over. Ingen tekst før/efter tabellerne.

## Hårde regler

- Ingen kontoskrivning uden eksplicit ja.
- QS er keyword-grain; LP er et flag, aldrig en score.
- Lavt volumen → flag lav sikkerhed.
- LP/creative-fixes er altid anbefalinger, ikke writes.
- Landingsside-tjek (Trin 4.5) er opt-in, kun på LP-svage keywords, og ændrer aldrig kontoen — output er klient-side anbefalinger.
- Pausede kampagner ekskluderes, flages aldrig negativt.
