# Phase 3b — assets (sitelinks, callouts, structured snippets)

Phase-3-creative-trin (parallelt med `05-rsa-copy`). Genererer kampagne-assets — **sitelinks, callouts,
structured snippets** — fra `01-landing-page`-output + intake, og emitterer dem som ét struktureret objekt
der spejler Ians skeleton tab 07. Output forbruges af `07-assembler` (fylder tab 07 + Editor asset-CSV).

Pipeline-mode-først; `assets`-shell-skillet wrapper solo-mode.

## Designprincip — to korrekthed-firewalls, ikke pynt

Hold det enkelt, MEN to ting er korrekthed, ikke polish (begge i
`${CLAUDE_SKILL_DIR}/references/asset-rules.md` — læs den, den vinder ved konflikt):

1. **Opfind ALDRIG asset-tekst.** Callouts, sitelink-beskrivelser og snippet-værdier er FAKTUELLE claims.
   Generér KUN fra `01-landing-page`-output (`usp_candidates`, `trust_signals` verbatim,
   `product_service`, `on_page_ctas`, `active_offer`, `tone`) + intake. Aldrig en plausibel men ugrounded
   callout ("Markedsledende", "Bedste pris"). Trust-tal verbatim fra siden/intake. Hver callout + snippet
   SKAL have et `grounded_in`-felt der navngiver analyzer-feltet claimet kom fra; ingen grounding → emit
   ikke.
2. **Sitelink-URL'er er IKKE udledelige fra den skrabne side.** Tab 07's sitelinks peger på ANDRE sider
   (`/ai-seo-audit/`, `/kontakt/`) end den ene landingsside Phase 1 skrabede. At opfinde stier er samme
   fejlklasse som at opfinde keyword-volumen. Kilde dem bevidst: operator-leveret (default). Valgfrit hvis
   firecrawl-CLI'en findes: `firecrawl map <domæne>` for rigtige URL'er operatøren vælger fra. Kan en URL
   ikke bekræftes: UDELAD sitelinket — ship aldrig en gættet URL.

## Hård regel — INGEN API-push, gated writes

Ingen Google Ads API-push, ingen eksterne writes herfra (objektet emitteres; `07-assembler` renderer
CSV/workbook). En valgfri `firecrawl map` (URL-discovery, kun hvis CLI'en findes) er en read — men oplys
hvilket domæne der mappes.

## Trin 0 — Kontekst

Læs `references/asset-rules.md` — de verificerede Editor-CSV-fakta, de to firewalls og output-formen.
Dansk medmindre brugeren skriver engelsk.

## Trin 1 — Indlæs input

Forbrug `landing-page-analysis.json` (`product_service`, `usp_candidates`, `trust_signals`,
`active_offer`, `on_page_ctas`, `tone`) + `campaign-strategy.json` `campaign` (kampagnenavn) fra
artefakt-mappen. Bemærk: analyzeren har INTET `services`-listefelt — snippet-værdier kræver operator-input
(Trin 4). Solo-mode standalone: saml minimal intake (URL + klient) og kør `01-landing-page`-mønstret.
Default **attachment level = campaign** (tab 07 er alt campaign-niveau).

## Trin 2 — Sitelinks (Firewall B gælder)

Sitelinks skal pege på rigtige sider. Spørg operatøren om sitelink-targets (tekst + URL), ELLER tilbyd —
hvis firecrawl-CLI'en findes — `firecrawl map <domæne>`. Til hver sitelink: kort tekst (~25 tegn
praktisk), Final URL (bekræftet), og valgfrit 2 beskrivelses-linjer (par — begge eller ingen) grounded i
sidens budskab. Kan en URL ikke bekræftes: udelad. Sæt `url_source` per sitelink (operator-supplied /
firecrawl-map / omitted-unconfirmed).

## Trin 3 — Callouts (Firewall A gælder)

Korte fordel-/trust-fraser (~25 tegn praktisk), HVER grounded i analyzer-output. Eksempler: "20 års
SEO-erfaring" (← trust_signal), "HubSpot-partner" (← USP), "Ingen binding" (← offer/USP). Map hver callout
til sit analyzer-felt i `grounded_in`. 4-10 callouts typisk.

## Trin 4 — Structured snippets (header UNVERIFIED — flag)

Header SKAL være en af Googles foruddefinerede headers (fx Services, Platforms, Brands), første bogstav
stort — opfind ikke en header. Værdier: korte navneord-fraser. **Værdierne er en LISTE som den
enkelt-side-analyzer IKKE kan levere** — så ground listen i `product_service`-dekomponering operatøren
bekræfter, ELLER en operator-leveret service-liste. Opfind aldrig en 5-punkts liste fra én linje.
- **Editor-kolonnen til selve headeren er UNVERIFIED** (sandsynligvis `Subject`, muligvis `Header`) OG
  værdi-delimiteren for `Snippet Values` er UNVERIFIED (semikolon er den generelle regel, ikke bekræftet
  for netop denne kolonne). Begge læses i ÉT build-time Editor-round-trip. Sæt `header_column_unverified:
  true`. Værdi-KOLONNEN `Snippet Values` ER verificeret (kun delimiteren er ukendt).

## Trin 5 — Lead forms (manuelt UI-trin)

Lead forms er IKKE CSV-importerbare i Editor (verificeret negativ). Emit INGEN række. Vil operatøren have
en lead form: sig at den oprettes i Google Ads UI'et, ikke via denne CSV. Sæt `lead_form.csv_importable:
false` i objektet med noten.

## Trin 6 — Emit objektet

Skriv `assets.json` (formen i §3 af reference-filen) til artefakt-mappen. Indeholder `campaign`,
`attachment_level`, `sitelinks[]`, `callouts[]`, `structured_snippets[]`, `lead_form` (csv_importable
false), `content_firewall`-bekræftelse, og `snippet_header_note`. Hver callout + snippet har `grounded_in`.

## Trin 7 — Returnér

Returnér en kort tabel per asset-type: sitelinks (tekst | URL | url_source), callouts (tekst |
grounded_in), structured snippets (header | værdier | grounded_in). Plus: bekræft firewall'en ("Alle
assets grounded i landingssiden/intake; intet opfundet"), flag UNVERIFIED snippet-header-kolonnen +
build-time-round-trip, nævn lead forms som manuelt UI-trin hvis relevant, og list eventuelle udeladte
sitelinks (URL kunne ikke bekræftes).

## Risici / noter

- **Firewall A er den hyppigste drift:** en asset-generator vil gerne fylde med plausible callouts. Hver
  eneste skal have `grounded_in`. Tom grounding = drop.
- **Firewall B:** gæt ALDRIG en sitelink-sti fra én skrabet side. Operator eller firecrawl map.
- **Snippet-header-kolonnen** er det ene reelle Editor-ukendte — flag det, hardcode det ikke.
- **Lead forms** = manuelt. Prøv aldrig en CSV-række.
- Assets er campaign-niveau by default; account-niveau via literal `<Account-level>` i Campaign.

## Maintenance

Alle Editor-CSV-fakta + firewalls + output-form bor i `references/asset-rules.md`. Snippet-header-
kolonnenavnet skal verificeres via Editor-round-trip og opdateres fra UNVERIFIED (hold i sync med
`07-assembler`). v1 dækker sitelinks/callouts/structured snippets — andre asset-typer branches senere.
