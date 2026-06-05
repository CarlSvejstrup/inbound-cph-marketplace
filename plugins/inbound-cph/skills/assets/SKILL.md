---
name: assets
description: Generér Google Ads kampagne-assets (sitelinks, callouts, structured snippets) fra Phase-1 landing-page-analyzer-output + intake, som struktureret objekt til kampagne-byggeren. Phase-3-creative-trin i campaign-build. To hårde firewalls: opfind ALDRIG asset-tekst (kun grounded i analyzer/intake), og sitelink-URL'er er IKKE udledelige fra den skrabne side (operator-leveret eller Firecrawl-map). Lead forms er et manuelt UI-trin (ikke CSV-importerbart). Brug når brugeren siger "lav assets", "sitelinks + callouts", "extensions til kampagnen", eller fortsætter campaign-build efter structuring. Svarer på dansk.
---

# assets

Phase-3-creative-trinnet i **campaign-build** (parallelt med rsa-copywriter). Genererer
kampagne-assets — **sitelinks, callouts, structured snippets** — fra Phase-1
landing-page-analyzer-output + intake, og emitterer dem som ét struktureret objekt der spejler
Ians skeleton tab 07. Output forbruges af **assembler** (Phase 4, fylder tab 07 + Editor
asset-CSV).

## Designprincip — to korrekthed-firewalls, ikke pynt

Carl: "just make" — så hold det enkelt. MEN to ting er korrekthed, ikke polish (begge i
`references/asset-rules.md`, læs den, den vinder ved konflikt):

1. **Opfind ALDRIG asset-tekst.** Callouts, sitelink-beskrivelser og snippet-værdier er
   FAKTUELLE claims. Generér KUN fra landing-page-analyzer-output (dens faktiske felter:
   `usp_candidates`, `trust_signals` verbatim, `product_service`, `on_page_ctas`,
   `active_offer`, `tone`) + intake. Aldrig en plausibel men
   ugrounded callout ("Markedsledende", "Bedste pris"). Trust-tal verbatim fra siden/intake —
   aldrig opfundet (samme regel som RSA). Hver callout + snippet SKAL have et `grounded_in`-felt
   der navngiver analyzer-feltet claimet kom fra; ingen grounding → emit ikke.

2. **Sitelink-URL'er er IKKE udledelige fra den skrabne side.** Tab 07's sitelinks peger på
   ANDRE sider (`/ai-seo-audit/`, `/kontakt/`) end den ene landingsside Phase 1 skrabede. At
   opfinde stier er samme fejlklasse som at opfinde keyword-volumen. Kilde dem bevidst:
   operator-leveret (default), eller `firecrawl map <domæne>` → operatøren vælger. Kan en URL
   ikke bekræftes: UDELAD sitelinket — ship aldrig en gættet URL.

## Hård regel — INGEN API-push, gated writes

Som hele campaign-build: ingen Google Ads API-push, ingen eksterne writes fra dette skill (det
emitterer et objekt; assembler renderer CSV/workbook). `firecrawl map` (URL-discovery) er en
read, ikke en write — men oplys hvilket domæne der mappes.

## When to use

Trigger-fraser: "lav assets", "sitelinks + callouts", "extensions til kampagnen", "structured
snippets", eller automatisk som Phase-3-trin (parallelt med rsa-copywriter) efter structuring.

## Trin 0 — Kontekst

Læs `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` (write-gate + sprog). Læs
`${CLAUDE_PLUGIN_ROOT}/skills/assets/references/asset-rules.md` — de verificerede Editor-CSV-
fakta, de to firewalls og output-formen. Dansk medmindre brugeren skriver engelsk.

## Trin 1 — Indlæs input

Forbrug landing-page-analyzer-JSON (dens faktiske felter: `product_service`, `usp_candidates`,
`trust_signals`, `active_offer`, `on_page_ctas`, `tone`) + campaign-strategy `campaign`
(kampagnenavn). Bemærk: analyzeren har INTET `services`-listefelt — snippet-værdier kræver
operator-input (se Trin 4). Kædet
fra campaign-build: læs fra kørslens artefakt-mappe. Standalone: saml minimal intake (URL +
klient) og kør landing-page-analyzer-mønstret.

Default **attachment level = campaign** (tab 07 er alt campaign-niveau).

## Trin 2 — Sitelinks (Firewall B gælder)

Sitelinks skal pege på rigtige sider. Spørg operatøren om sitelink-targets (tekst + URL), ELLER
tilbyd `firecrawl map <domæne>` for at finde rigtige URL'er operatøren kan vælge fra. Til hver
sitelink: kort tekst (~25 tegn praktisk), Final URL (bekræftet), og valgfrit 2 beskrivelses-
linjer (par — begge eller ingen) grounded i sidens budskab. Kan en URL ikke bekræftes: udelad.
Sæt `url_source` per sitelink (operator-supplied / firecrawl-map / omitted-unconfirmed).

## Trin 3 — Callouts (Firewall A gælder)

Korte fordel-/trust-fraser (~25 tegn praktisk), HVER grounded i analyzer-output. Eksempler fra tab 07:
"20 års SEO-erfaring" (← trust_signal), "HubSpot-partner" (← USP), "Ingen binding" (← offer/USP).
Map hver callout til sit analyzer-felt i `grounded_in`. Opfind ikke en callout der lyder godt
men ikke står på siden. 4-10 callouts typisk.

## Trin 4 — Structured snippets (header UNVERIFIED — flag)

Header SKAL være en af Googles foruddefinerede headers (fx Services, Platforms, Brands), første
bogstav stort — opfind ikke en header. Værdier: korte navneord-fraser. **Værdierne er en LISTE
som den enkelt-side-analyzer IKKE kan levere** (`product_service` er én linje, intet
`services`-felt findes) — så ground listen i `product_service`-dekomponering operatøren
bekræfter, ELLER en operator-leveret service-liste. Opfind aldrig en 5-punkts liste fra én linje.
- **Editor-kolonnen til selve headeren er UNVERIFIED** (sandsynligvis `Subject`, muligvis
  `Header`) OG værdi-delimiteren for `Snippet Values` er UNVERIFIED (semikolon er den generelle
  regel, men ikke bekræftet for netop denne kolonne). Begge læses i ÉT build-time Editor-round-
  trip (opret manuelt → Export CSV → læs kolonnenavn + delimiter). Sæt `header_column_unverified:
  true`. Værdi-KOLONNEN `Snippet Values` ER verificeret (kun delimiteren er ukendt).

## Trin 5 — Lead forms (manuelt UI-trin)

Lead forms er IKKE CSV-importerbare i Editor (verificeret negativ). Emit INGEN række. Hvis
operatøren vil have en lead form: sig at den oprettes i Google Ads UI'et, ikke via denne CSV.
Sæt `lead_form.csv_importable: false` i objektet med noten.

## Trin 6 — Emit objektet

Skriv det strukturerede objekt (formen i §3 af reference-filen) til kørslens artefakt-mappe
(fx `assets.json`). Indeholder `campaign`, `attachment_level`, `sitelinks[]`, `callouts[]`,
`structured_snippets[]`, `lead_form` (csv_importable false), `content_firewall`-bekræftelse, og
`snippet_header_note`. Hver callout + snippet har `grounded_in`.

## Trin 7 — Output

Lever en kort tabel per asset-type: sitelinks (tekst | URL | url_source), callouts (tekst |
grounded_in), structured snippets (header | værdier | grounded_in). Plus:
- Bekræft firewall'en: "Alle assets grounded i landingssiden/intake; intet opfundet."
- Flag UNVERIFIED snippet-header-kolonnen + build-time-round-trip.
- Nævn lead forms som manuelt UI-trin hvis relevant.
- Liste eventuelle udeladte sitelinks (URL kunne ikke bekræftes).

## Risici / noter

- **Firewall A er den hyppigste drift:** en asset-generator vil gerne fylde med plausible
  callouts. Hver eneste skal have `grounded_in`. Tom grounding = drop.
- **Firewall B:** gæt ALDRIG en sitelink-sti fra én skrabet side. Operator eller firecrawl map.
- **Snippet-header-kolonnen** er det ene reelle Editor-ukendte — flag det, hardcode det ikke.
- **Lead forms** = manuelt. Prøv aldrig en CSV-række.
- Assets er campaign-niveau by default (tab 07). Ad-group-niveau kun hvis operatøren beder
  (begge Campaign + Ad group udfyldt); account-niveau via literal `<Account-level>` i Campaign.

## Maintenance

- Alle Editor-CSV-fakta + firewalls + output-form bor i `references/asset-rules.md`. Ret kun den.
- Snippet-header-kolonnenavnet skal verificeres via Editor-round-trip og opdateres fra UNVERIFIED
  til verificeret når det er gjort (hold i sync med assembler Phase 4).
- v1 dækker sitelinks/callouts/structured snippets. Andre asset-typer (price, promotion, image,
  call) branches senere — verificér hver enkelts Editor-kolonner først.
