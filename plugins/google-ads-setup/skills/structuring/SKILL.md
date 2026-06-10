---
name: structuring
description: Byg en ny Google Ads-kampagnes kontostruktur som selvstændigt trin og aflever den som regneark (.xlsx) — ad groups (få, brede), keyword-selektion + match types (Exact + udvalgt Phrase, ALDRIG Broad), og klient-specifikke negative tilføjelser oven på Inbounds delte MCC-negativliste. Tynd indgang til structuring-referencen i campaign-build, kørt i solo-mode. Læser kun fra Google Ads MCP, pusher ALDRIG til kontoen. Brug når brugeren siger "byg kampagne-struktur", "structuring", "ad groups + keywords til [klient]", "lav keyword-strukturen", "strukturér kampagnen", eller vil have kontostrukturen som et selvstændigt stykke (ikke en fuld build). Svarer på dansk.
---

# structuring

Selvstændig indgang til **Phase 2 — structuring** i kampagne-builden. Bygger kontoarkitekturen og
afleverer den som et **`.xlsx`-regneark** (ad groups, keywords + match types, negatives — tabulært, så et
regneark passer bedre end prosa). Al logikken bor i campaign-build's reference — dette skill er en tynd
shell der kører den i **solo-mode** (producerer en regnearks-rapport i stedet for kun JSON til en pipeline).

Kilden til sandhed: `${CLAUDE_SKILL_DIR}/../campaign-build/references/04-structuring.md` (+ dens kontrakter
`structuring-rules.md` og `generelle-negative-eksempel.md` i samme references-mappe).

## Trin 1 — Saml input

Som selvstændigt skill arver du ingen Phase-1-output. Saml minimal intake: klientnavn + landingsside-URL +
tema/kampagnetype + geo. Har brugeren allerede et research-grundlag (JSON fra `research`-skillet), så læs
det fra arbejdsmappen i stedet for at gen-samle. Mangler landingsside-indsigt helt, kør
`01-landing-page`-mønstret inline som referencen beskriver.

## Trin 2 — Kør referencen

Følg `04-structuring.md` præcist — den vinder ved konflikt. Det indebærer: hent den delte negativliste
LIVE fra MCC'en (read-only GAQL), byg ad groups (få, brede), generér keywords med eksplicit Exact/Phrase
(aldrig Broad), og to negative-tiers + monitor-kandidater. Referencen skriver `structuring.json` til
arbejdsmappen.

## Trin 3 — Aflever regnearket (.xlsx)

Pak resultatet i én `.xlsx` (brug `xlsx`-skillet) med faner der spejler structuring-outputtet:
- **Ad groups:** navn | temperatur | #keywords | tema | landingsside (+ struktur-rationalet øverst).
- **Keywords:** ad group | keyword | match type (med volumen-disclaimer øverst — keywords er tema-afledte,
  validér i Keyword Planner).
- **Negatives:** den delte liste som ÉN reference-linje med det LIVE antal (ALDRIG de 277 enumereret) +
  klient-specifikke tilføjelser (term | match type | niveau | hvorfor) + monitor-first-kandidater separat.

At gemme til Drive er en gated write (bekræft før upload). Lokalt er fint.

## Safety

- **Read-only mod Google Ads.** Den live negativliste-pull er et read; ingen API-push, ingen konto-writes.
- **Match-type-låsen:** hver positiv keyword SKAL have Exact eller Phrase — blank/bart ord = Broad ved
  import. Verificér før aflevering.
- **Genudsend ALDRIG de 277 delte negativer** som rækker — de påføres by-reference. Ser du dem enumereret,
  er du drevet væk fra "add to this".
- **Gem til Drive = gated write.** **Logikken bor i referencen, ikke her** — ret `04-structuring.md` hvis
  reglerne ændrer sig.
