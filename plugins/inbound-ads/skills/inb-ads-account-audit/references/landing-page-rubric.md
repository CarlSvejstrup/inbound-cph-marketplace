# Landingsider via web_fetch: relevans-rubrik

Kontrakten for Landingsider-modulet i account-auditten (SKILL.md § 4 citerer denne fil). Alt her er read-only læsning af offentlige sider via `web_fetch` — ingen skrivning.

## URL-udvælgelse

1. Udtræk alle unikke final URLs fra `get_ad_performance`.
2. Deduplikér.
3. Tag de **10 hyppigste** (efter hvor mange annoncer/ad groups de peger fra).

## Pr. URL: kald web_fetch og vurdér

For hver af de 10 URLs, kald `web_fetch` og notér:

- **Loader siden?** Ingen fejl (4xx/5xx, timeout, tom respons). En død eller fejlende side er et kritisk fund.
- **Primær overskrift + CTA-tekst** — udtræk **ordret fra siden** (aldrig parafraseret eller opfundet).
- **Mobiloptimering** — er der en `viewport` meta-tag til stede? Notér ja/nej som proxy for mobiltilpasning.
- **Relevans ift. annonce** — hold landingssidens overskrift op mod den tilsvarende annonce-overskrift for det ad group der peger på URL'en. Er der klart match mellem søgeintention → annonce → landingsside, eller er der et brud (annoncen lover X, siden handler om Y)?

## Rubrik: hvad "relevant" betyder

Bedøm hver side langs modulets tjekliste (SKILL.md § 6.2 → Landingsider):

- Er landingssiden **relevant for søgeordene** der udløser annoncen?
- Er den tilpasset **hvor brugeren er i købsrejsen** (topfunnel-info vs. konverteringsklar)?
- Er siden **nem at navigere**?
- Er **indholdet relevant** for det annoncen lover?
- **Loader den hurtigt for mobilbrugere**?

## Honesty-flag (obligatorisk)

`web_fetch` giver statisk sideindhold, ikke en fuld UX- eller hastigheds-audit. Skriv aldrig en påstand du ikke kan se i den hentede side. Landingsider-slidet skal altid bære manuel-review-banneret (SKILL.md § 6.3) fordi den endelige kreativ-/UX-dom kræver menneskelig gennemgang ud over de strukturelle signaler web_fetch giver.
