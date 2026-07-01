# Phase 1a — landing-page (positionerings-udtræk)

Phase-1 research-trin. Tager én landingsside-URL og udtrækker et struktureret positioneringsbillede
(produkt, USP-kandidater, tone, CTA'er, trust-tal, aktivt tilbud, sprog) som JSON. Output forbruges af
`04-structuring` (Phase 2) og `05-rsa-copy` (Phase 3).

Denne reference ejer den **delte page-extraction-kontrakt**. `02-competitor` peger den samme
ekstraktion mod konkurrenters sider. Pipeline-mode-først; `research`-shell-skillet wrapper solo-mode.

## Hvorfor dette trin findes

Ad-teamet starter altid med landingssiden — alt copy skal matche siden for høj Quality Score, og alle
claims skal stå på siden (vi opfinder ikke tal). Som selvstændigt research-trin bygger structuring og
RSA på ét fælles, kontrolleret faktagrundlag i stedet for hver sin ad-hoc-læsning.

## Kontrakt — læs den først

Læs `${CLAUDE_SKILL_DIR}/references/page-extraction.md` — den definerer felterne, de tre firewall-regler
og output-formen, og den vinder ved enhver konflikt. `page-extraction-schema.json` (samme mappe) er
felt-kontrakten du udtrækker *mod*, ikke et argument til et værktøj.

## How it works (arkitektur — læs én gang)

`web_fetch` på URL'en → DU (modellen) udtrækker felterne fra det hentede sideindhold → de tre
firewall-regler anvendes → struktureret JSON emitteres. Ingen scripts, ingen CLI — `web_fetch` er et
indbygget værktøj der virker i Cowork.

**Verbatim-udtræk:** udtræk felterne fra det FAKTISKE sideindhold `web_fetch` returnerer, ikke fra et
resumé. Trust-tal og claims skal være ordrette fra siden (firewall-regel 1). Hvis `web_fetch` kun giver
et resumé uden de konkrete tal/claims, hent siden igen med en præcis instruktion om rå tekst med tal og
CTA'er intakt — gæt aldrig et tal.

## Trin 0 — Kontekst

At scrape en offentlig side er en read, ikke en ekstern write — ingen write-gate. Men oplys hvilken URL
du rammer. Dansk medmindre brugeren skriver engelsk.

## Trin 1 — Intake (minimal)

Det eneste påkrævede input er **URL'en**. I pipeline-mode arver du URL'en (og evt. forventet
annoncetekst-sprog) fra orkestratoren — spørg **ingenting**, kør direkte. Option-præsentation og
menneske-godkendelse af det udtrukne hører til Phase-2-gaten, ikke her: dette trin udtrækker kandidater,
mennesket vælger senere.

## Trin 2 — Scrape + udtræk

Kald `web_fetch` på `<final_url>` (bed om sidens fulde indhold — produkt/ydelse, USP'er, CTA'er,
trust-tal med konkrete tal, evt. tilbud + udløb, brand, sprog). Udfyld felterne i
`page-extraction-schema.json` ved at læse det hentede indhold. Kan siden ikke hentes: sig det og stop —
vi opfinder ikke felter. Anvend de tre firewall-regler fra kontrakten:

1. Trust-signaler er verbatim; `has_numbers` kun når der står et brugbart tal. Intet tal → tom liste.
2. Aktivt tilbud → `expiry` påkrævet (dato eller `"unknown"`).
3. `page_language` detekteres; sæt `language_note` hvis det kan afvige fra det valgte annoncesprog —
   skift aldrig sprog stiltiende.

## Trin 3 — Emit JSON

Skriv `landing-page-analysis.json` til kørslens artefakt-mappe. Stempl `scraped_at` efter kørslen. Sæt
`extraction_confidence` (`high`/`partial`/`low`) og `missing_fields` ærligt: `partial`/`low` når USP'er,
trust eller tilbud ikke kunne findes, med hullerne listet. (Lokal arbejdsfil, ikke ekstern write.)

## Trin 4 — Returnér

Returnér til orkestratoren: stien til JSON'en, en kort tabel over det udtrukne (produkt, top-3 USP'er,
tone, trust-tal, tilbud + udløb, sprog), hvilken URL der blev scrapet, og — hvis konfidens er
`partial`/`low` — hvad der mangler, så Phase-2-gaten ved hvad mennesket skal udfylde.

## Maintenance

Feltlisten, firewall-reglerne og JSON-formen bor ÉT sted: `page-extraction.md` +
`page-extraction-schema.json`. Ret kun dem; alle forbrugere (dette trin, `02-competitor`, RSA) følger med.
Henter via `web_fetch` (indbygget, virker i Cowork) — verbatim-reglen er ikke til forhandling.
