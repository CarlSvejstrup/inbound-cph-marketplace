# Phase 3a — rsa-copy (annoncetekster per ad group)

Phase-3-creative-trin (parallelt med `06-assets`). Tager den godkendte `structuring.json` (N ad groups,
hver med navn, URL, vinkler og keyword-seeds) og producerer RSA-annoncetekster for HVER ad group ved at
**genbruge det shippede `inb-ads-rsa-copy`-skill** én gang per ad group. Output (`rsa-manifest.json`
+ per-ad-group `ads-*.json`) forbruges af `07-assembler` (Phase 4).

**Tyndt orkestrerings-trin — ingen copywriting-logik her.** Al copywriting-intelligens og alle
kvalitets-gates (15 headlines / 4 descriptions / 2 paths under Googles hårde grænser 30/90/15,
vinkel-taksonomi, headline-craft) bor i `inb-ads-rsa-copy` (`fill-sheet.py` + `references/
headline-craft.md`), aldrig duplikeret her. Dette er den ENE reference der peger UD til et andet skill —
det er bevidst: `inb-ads-rsa-copy` er script-tungt og genbruges på tværs af plugins (optimization-
loopet afhænger af det), så dets logik bor i sit eget skill, ikke i en campaign-build-reference.

## Hvorfor genbrug frem for duplikering

`inb-ads-rsa-copy` er allerede den verificerede RSA-copy-motor (live tegntælling, rød over-længde-CF,
Editor-konvention, Drive-round-trip). At kopiere dens logik ind her ville skabe to kilder til samme
sandhed der kan glide fra hinanden. I stedet kaldes skillet per ad group, og dette trin samler kun
resultaterne til et manifest `07-assembler` kan flette.

## Trin 0 — Kontekst

Læs den godkendte `structuring.json` fra artefakt-mappen. For HVER ad group bruger du: `name`,
`landing_page_url`, `angles[]`, `keyword_seeds_for_rsa[]`, `paths`. Dansk medmindre brugeren skriver
engelsk. Pipeline-mode: kør for alle ad groups uden at gen-spørge; vinkel/hypotese er allerede i
structuring-outputtet.

## Trin 1 — Kald inb-ads-rsa-copy per ad group

For hver ad group i `structuring.json`: kør `inb-ads-rsa-copy`-skillet med ad group'ens URL, vinkler
og keyword-seeds som intake, så det producerer RSA-tekster (≥1 RSA) for netop den gruppe. Lad skillet eje
sine egne grænser og gates — du injicerer kun input og fanger output. Skriv hver ad group's resultat som
`ads-<adgroup-slug>.json` i artefakt-mappen.

`ads-*.json`-formen (det `07-assembler` læser):
```json
{
  "ad_group": "Erhvervsrengoering",
  "final_url": "https://acme.dk/ydelse",
  "ads": [
    { "vinkel": "fast pris", "hypotese": "pris-fokus konverterer",
      "final_url": "https://acme.dk/ydelse", "paths": ["rengoering", "kontor"],
      "headlines": ["...", "..."], "descriptions": ["...", "..."] }
  ]
}
```

`ad_group` SKAL matche structuring-ad-group-navnet verbatim — `assemble.py` hard-fejler hvis en RSA
peger på en ad group structuring ikke kender (ads.csv ville referere en ikke-eksisterende gruppe).

## Trin 2 — Emit manifestet

Skriv `rsa-manifest.json` til artefakt-mappen — listen over hver ad group's `ads-*.json` med absolutte
stier (relative stier kørt fra forkert cwd er den hyppigste assembler-fejl):

```json
{
  "campaign": "IC | GSN | AI-SEO",
  "rsa_artifacts": [
    { "ad_group": "Erhvervsrengoering", "ads_json": "/abs/sti/ads-erhvervsrengoering.json" }
  ]
}
```

`campaign` SKAL matche kampagnenavnet i de andre tre shapes (join-nøgle).

## Trin 3 — Returnér

Returnér: antal ad groups dækket, antal RSA'er i alt, og en note om ad groups uden RSA (hvis nogen — de
ships som keywords-only og fanges som launch-gate i tab 08 af assembleren). Flag hvis en ad group's
copy-generering fejlede, så mennesket ved hvilke der mangler annoncer.

## Maintenance

- **Ingen copywriting-regler her.** De bor i `inb-ads-rsa-copy`. Ændrer Google grænserne eller
  ændrer vinkel-taksonomien sig: ret `inb-ads-rsa-copy`, ikke denne fil.
- Manifest-formen + `ads-*.json`-formen spejler hvad `assemble.py` (`_rsa_rows`) læser — hold dem i sync
  når Phase 4 ændres.
