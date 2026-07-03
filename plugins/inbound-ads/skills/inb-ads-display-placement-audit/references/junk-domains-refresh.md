# junk_domains.tsv — genopfriskning

`references/junk_domains.tsv` er skillets EGEN generelle heuristik: ~9.834 domæner
(gambling + MFA/clickbait-proxy + scam), bygget fra Blocklist Project + Steven Black's hosts,
begge fri licens. Det er et statisk snapshot, ikke en live feed — genopfrisk med jævne mellemrum
(hver par måneder, eller når skillets false-negative-rate på oplagt junk ser ud til at stige, et
tegn på at snapshottet er ved at blive forældet).

**Den fulde, kanoniske genopfrisknings-kommando (inline bash), proveniens og licenser bor i
`references/junk_domains_SOURCES.md`** — ret aldrig proceduren to steder. Kør bash-blokken derfra;
den henter de fire upstream-lister, uddrager domænerne, differ Steven Black-varianterne mod
base-listen, og skriver en frisk `domain<TAB>category`-fil.

Kort opsummering af hvad kommandoen gør (detaljer + eksakt bash i SOURCES-filen):

- `gambling` — Blocklist Project `gambling.txt` + Steven Black's gambling-only delta (diffet mod
  base-hosts så den ikke duplikerer base-ad/malware-listen).
- `mfa_clickbait` — Steven Black's `fakenews`-delta (nærmeste fri proxy for made-for-advertising /
  content-farm; se SOURCES for hvorfor der ikke findes en dedikeret MFA-liste).
- `scam_fraud` — Blocklist Project `scam.txt`.

Bevidst IKKE bundlet: Blocklist Projects `fraud.txt` (~196k entries, for stor og støjende) og
`redirect.txt` (mest URL-shortenere). Bliv false-negatives på scam et reelt problem, er `fraud.txt`
første sted at kigge — men hent den som et separat on-demand-opslag, bundlér den ikke helt.

Dette er skillets generelle heuristik og skal IKKE forveksles med det hårde ekskluderingslag
(`hard_exclusions.tsv` + `hard_exclusion_patterns.py`, se `references/hard-exclusions-catalog.md`),
som er Inbounds eget klient-bekræftede standing filter og opdateres manuelt, ikke via denne fetch.
