---
name: rsa-copywriter
description: Phase-3-trinnet i campaign-build der laver RSA-annoncetekster for HVER ad group fra Phase-2 structuring-output, ved at genbruge den shippede responsive-search-ads-skill ad group for ad group. Tynd orkestrator — al copywriting-intelligens og kvalitets-gates bor i responsive-search-ads (fill-sheet.py + headline-craft.md), aldrig duplikeret her. Brug når brugeren siger "lav RSA'er til hele kampagnen", "rsa-copywriter", "annoncetekster til alle ad groups", eller fortsætter en campaign-build-kørsel efter structuring er godkendt. Svarer på dansk.
---

# rsa-copywriter

Phase-3-creative-trinnet i **campaign-build**. Tager den godkendte Phase-2 structuring-output
(N ad groups, hver med navn, URL, vinkler og keyword-seeds) og producerer RSA-annoncetekster
for HVER ad group ved at **genbruge den shippede `responsive-search-ads`-skill** én gang per
ad group. Output (per-ad-group ark/ads.json) forbruges af **assembler** (Phase 4).

## Designprincip — tynd orkestrator, INGEN duplikeret copy-logik

Dette skill skriver IKKE sin egen copywriting. Al copywriting-intelligens og alle
kvalitets-gates bor i `responsive-search-ads` og vinder hver konflikt:
- `responsive-search-ads/references/headline-craft.md` — angle-mix, Sentence case,
  længde-variation, banned words, disapproval-policy.
- `responsive-search-ads/fill-sheet.py` — de hårde gates (exit 1 længde, exit 2 kvalitet).
- `responsive-search-ads/sheet_layout.py` — ark-layoutet + LEN-formler.

rsa-copywriter's ENESTE nye logik er **per-ad-group-loopet**: structuring giver N ad groups,
responsive-search-ads håndterer flere RSA'er inden for ÉN ad group. Så dette skill itererer
ad groups → kører den shippede RSA-skill per gruppe → samler stierne til assembler. Hvis du
finder dig selv i at omskrive headline-regler eller længde-gates ind i en ny fil: stop — det
er en fork.

## Hvordan genbruget virker — data ind, ikke kode-ændring

I en kædet kørsel leverer Phase 1 + Phase 2 allerede det `responsive-search-ads`-intaken
ellers ville SPØRGE om. Lever det som **svarene** på intaken (kontekst-niveau), så den
shippede skill ikke spørger fra bunden — INGEN kode-ændring i den shippede skill:

| responsive-search-ads intake-felt | Kommer fra (chained) |
|---|---|
| Klient + URL | structuring `campaign` + ad group `landing_page_url` (eller campaign-strategy) |
| Kampagnenavn | structuring `campaign` (allerede Inbound-navngivet) |
| Ad group-navn | structuring ad group `name` |
| Antal RSA'er + led-vinkler (Kald 1, spm 4) | ad group `angles` → led-vinkler (1 RSA default, eller én per distinkt vinkel) |
| Top-keywords (Kald 4, spm 4) | ad group `keyword_seeds_for_rsa` (+ `keywords[].text`) |
| USP / tilbud / trust-tal / tone (Kald 4) | landing-page-analyzer JSON (`usp_candidates`, `active_offer`, `trust_signals`, `tone`) |

**Re-scrape er harmløs redundans, ikke en fejl.** Hvis den shippede RSA-skill scraper siden
igen (dens Trin 2), gør det ikke noget — det giver bare samme data. Den valgfrie Q5-optimering
(giv analyzer-JSON i stedet for inline-scrape) er KUN værd at lave hvis wrapping ikke kan
levere dataene — og hvis du nogensinde rører `responsive-search-ads`, behold standalone-stien
+ gap-brief-loopet intakt og re-smoke-test begge. Carl: "mainly reuse it" = letteste adapter,
ikke en anden copywriting-motor.

## Hård regel — INGEN API-push, gated writes

Som hele campaign-build: ingen Google Ads API-push. Ark-writes (lokalt + Drive) er gated bag
eksplicit bekræftelse — men i en kædet kørsel samles bekræftelsen typisk på Phase-4-assembly,
så spørg orkestratoren om writes skal ske per ad group nu eller udskydes til assembly. Read-only
MCP (top-annonce-læring i RSA Trin 2.5) er fint.

## When to use

Trigger-fraser: "lav RSA'er til hele kampagnen", "rsa-copywriter", "annoncetekster til alle ad
groups", "creative-trinnet", eller automatisk som Phase-3-trin efter structuring er godkendt.
Til ÉN ad group standalone: brug `responsive-search-ads` direkte — dette skill er til
fan-out over hele structuren.

## Trin 0 — Kontekst

Læs `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` (write-gate + sprog). Læs den shippede skills
`${CLAUDE_PLUGIN_ROOT}/skills/responsive-search-ads/SKILL.md` — det er motoren du orkestrerer;
dens Trin 4 + `references/headline-craft.md` er copy-sandheden. Dansk medmindre brugeren
skriver engelsk.

## Trin 1 — Indlæs structuring-output

Forbrug Phase-2 structuring-objektet (`structuring.json` fra kørslens artefakt-mappe, eller
indsat manuelt). Hver ad group har: `name`, `temperature`, `landing_page_url`, `theme`,
`keywords[{text, match_type}]`, `angles[]`, `keyword_seeds_for_rsa[]`. Plus campaign-niveau:
`campaign`, og landing-page-analyzer-JSON hvis kædet (USP/trust/offer/tone).

Mangler structuring (standalone fejl-kald): sig at rsa-copywriter kræver godkendt
structuring-output, og peg på `responsive-search-ads` for enkelt-ad-group-arbejde.

## Trin 2 — Per-ad-group loop (det eneste nye)

For HVER ad group i `ad_groups`:
1. Map ad group'ens felter til `responsive-search-ads`-intaken (tabellen ovenfor). Brug
   `angles` til at forvælge Kald-1-spm-4 (antal RSA'er + led-vinkler): 1 RSA default, eller
   én RSA per distinkt vinkel hvis gruppen har flere klare led-vinkler. Brug
   `keyword_seeds_for_rsa` som top-keywords (top-keyword i ≥3 headlines — RSA-reglen).
2. Kør `responsive-search-ads`-flowet for den ad group: dens Trin 3 (læs headline-craft.md),
   Trin 4 (generer + obligatorisk vinkel-audit PER RSA), Trin 5 (`fill-sheet.py`). Brug det
   bekræftede kampagnenavn + ad group-navnet fra structuring.
3. Skriv den ad group's `ads.json` og kør `fill-sheet.py` → ét ark per ad group:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/responsive-search-ads/fill-sheet.py \
     --ads adgroup-<n>.json --out "RSA - <klient> - <ad-group> - <YYYY-MM-DD>.xlsx"
   ```
   Gates køres af scriptet (exit 1 længde / exit 2 kvalitet) — overstyr ALDRIG stiltiende.
4. Behold ad group'ens landing_page_url som final_url (hver ad group kan have sin egen side).

**Loop-disciplin:** kør gates per ad group; en gruppe der fejler exit 2 rettes før du går
videre — ikke batch-springes over. Ved mange ad groups: rapportér fremgang (gruppe i af N).

## Trin 3 — Saml til assembler

Lever en manifest over alle producerede ad-group-ark + deres ads.json, så Phase-4 assembler
kan flette dem til workbook + Editor RSA-CSV. Form:

```json
{
  "campaign": "IC | GSN | AI-SEO",
  "rsa_artifacts": [
    { "ad_group": "AI SEO bureau", "ads_json": "adgroup-1.json", "xlsx": "RSA - ... .xlsx", "n_rsas": 1, "final_url": "https://..." }
  ],
  "copy_rules_source": "responsive-search-ads/references/headline-craft.md (verbatim)",
  "gates_passed": "fill-sheet.py per ad group (exit 0)"
}
```

## Trin 4 — Output

Lever per ad group: ad group-navn | #RSA'er | led-vinkler | sti til ark | gate-status. Plus
en linje der bekræfter at copy-reglerne kom fra `headline-craft.md` (ikke duplikeret) og at
hver ad group bestod gatene. Flag eventuelle ad groups der krævede `--allow-quality-warnings`
med begrundelse. Bed om write-bekræftelse hvis arkene gemmes nu (ellers udskudt til assembly).

## Risici / noter

- **Fork-faren** er den vigtigste: hvis du nogensinde kopierer en headline-regel eller en gate
  ind her, har du gaflet motoren. Al copy-logik bliver i `responsive-search-ads`.
- **Vinkel-mapping:** structuring `angles` er led-vinkler per ad group; de mapper til RSA Kald-1
  spm-4. Map til den nærmeste taksonomi-vinkel (benefit/trust/urgency/CTA/feature/keyword/brand/
  location/garanti) hvis navngivningen afviger — samme som gap-brief-mapping i RSA.
- **Gap-brief-loopet er separat:** `annonce-optimering` → `responsive-search-ads` gap-brief er
  en POST-launch-loop på en LIVE konto. rsa-copywriter er PRE-launch fra structuring. Bland dem
  ikke; en ny kampagne har ingen live-assets at diagnosticere endnu.
- **Q5 (consume analyzer-JSON in-place):** valgfri, kun hvis wrapping ikke kan levere data.
  Default: lever data som intake-svar, rør ikke den shippede skill. Hold den note levende til
  Phase 4/orkestrator.

## Maintenance

- Dette skill har bevidst ingen scripts og ingen references — det orkestrerer
  `responsive-search-ads`. Ændrer den shippede skill sit intake- eller ads.json-format, opdatér
  mapping-tabellen her.
- v1 er Search RSA-only (matcher den shippede skill). Andre annonce-typer branches når
  responsive-search-ads understøtter dem.
