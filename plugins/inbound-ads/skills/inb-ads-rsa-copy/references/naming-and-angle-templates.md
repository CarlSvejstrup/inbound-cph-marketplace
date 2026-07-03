# Navngivnings-skabeloner + vinkel-audit-tabel

To ting bor her: (1) de fulde navngivnings-skabeloner med felt-værdier (brugt i Trin 1, Kald 2-3, til at bygge kampagnenavnet), og (2) den obligatoriske vinkel-audit-tabel (udfyldes i Trin 4 FØR `ads.json` skrives). Body'en i SKILL.md holder metoden; de store tabeller bor her.

---

## Del 1 — Navngivnings-skabeloner

Saml intake-svarene efter den skabelon som matcher kampagnetypen. Vis ALTID resultatet til brugeren via et `AskUserQuestion` med strengen som første option `(Anbefalet)` — brugeren kan overstyre via "Other".

### Search / Shopping / pMax
Skabelon: `IC | NETVÆRK | Målretning | Kampagnenavn | Eventuelt`

| Felt | Mulige værdier (vis som options) |
|---|---|
| NETVÆRK | `GSN` (Google Search Network), `Shopping`, `pMax` |
| Målretning | `Brand`, `Product`, `Generic`, `brand products` (kun Shopping) |
| Kampagnenavn | fri tekst (produkt/tema) |
| Eventuelt | fri tekst eller `(ingen)` — typisk brandnavn |

Eksempler:
- `IC | GSN | Brand | Securitas`
- `IC | GSN | Product | Alarmsystemer`
- `IC | GSN | Generic | Alarmsystemer`
- `IC | Shopping | Generic | Alarmsystemer`
- `IC | Shopping | brand products | Alarmsystemer`
- `IC | pMax | Generic | Alarmsystemer`

### Display / YouTube / Demand Gen
Skabelon: `IC | FORMAT | KAMPAGNENAVN | MÅLRETNING`

| Felt | Mulige værdier |
|---|---|
| FORMAT | `GDN` (Google Display Network), `YT` (YouTube), `DG` (Demand Gen) |
| KAMPAGNENAVN | fri tekst (kampagne/tema) |
| MÅLRETNING | `Reach`, `Retargeting`, `Awareness`, `Consideration`, `Conversion` (eller fri tekst via "Other") |

Eksempler:
- `IC | GDN | Webinarer | Reach`
- `IC | YT | Bliv grønnere sammen | Retargeting`
- `IC | DG | Gratis introforløb | Retargeting`

### Audience
Skabelon: `YYYY-MD - IC - Audience type - Audience navn`

| Felt | Værdi |
|---|---|
| YYYY-MD | Indeværende år + måned uden ledende nul (fx `2025-1`, ikke `2025-01`). Brug dagens dato som default. **Bemærk:** eksemplerne fra Inbound bruger `2025-01` med ledende nul — spørg brugeren om begge varianter via AskUserQuestion. |
| Audience type | `Custom Intent`, `Retargeting`, `Affinity`, `In-Market`, `Similar`, `Lookalike` (eller fri tekst) |
| Audience navn | fri tekst (fx "Søgninger på HR system", "Alle besøgende") |

Eksempler:
- `2025-01 - IC - Custom Intent - Søgninger på HR system`
- `2025-01 - IC - Retargeting - Alle besøgende`

---

## Del 2 — Obligatorisk vinkel-audit (udfyld FØR du skriver `ads.json`)

Vinkel-mixet kan ikke tjekkes mekanisk af scriptet (det er semantisk), så **du** skal selv dokumentere det. Skriv denne tabel ud i dit svar før arket bygges. Mål-kolonnen er fra `../../shared/headline-craft.md`; "Faktisk" er dit sæt. **Enhver afvigelse skal have en grund på én linje** — ellers retter du sættet.

| Vinkel | Mål | Faktisk | Grund hvis afvigelse |
|---|---|---|---|
| Brand + keyword | 2 | ? | |
| Keyword-led | 3 | ? | |
| Benefit / udbytte | 3 | ? | |
| Feature / spec | 2 | ? | |
| Social proof / trust | 1 | ? | |
| Urgency | 0-1 | ? | |
| CTA (specifik) | 1 | ? | |
| Garanti / risiko | 1 | ? | |
| Location / segment | 1 | ? | |

Målene er en **consumer-default** (alarm-eksemplet) og bøjer sig efter branchen — se "Vinkel-mix pr. branche" i `../../shared/headline-craft.md`. Eksempel på en legitim afvigelse: et B2B-compliance/certificerings-produkt må gerne være trust-tungt (3 i stedet for 1) og udelade urgency/garanti — skriv da grunden, fx "trust-tungt: compliance-vertikal, akkreditering ER købsargumentet". En afvigelse uden grund er en fejl, ikke en stil.

**Med flere RSA'er skrives auditen PER RSA** — N annoncer → N audit-tabeller (én per annonce) i dit svar. Hver RSA skal selvstændigt opfylde mixet og længde-variationen.
