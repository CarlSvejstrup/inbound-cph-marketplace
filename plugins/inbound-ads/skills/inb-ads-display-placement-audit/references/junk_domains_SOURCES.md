# junk_domains.tsv — provenance and licensing

`junk_domains.tsv` is a flat `domain<TAB>category` file, 9,834 unique domains, compiled
2026-07-01 for Tier 1 (free, offline) matching in `scripts/score_placements.py`. It is a
static snapshot, not a live feed — see "Refreshing" below for how to update it.

## Sources (all free, all license-compatible with internal agency tooling)

| Category tag | Source | License | What was pulled |
|---|---|---|---|
| `gambling` | [Blocklist Project — gambling.txt](https://github.com/blocklistproject/Lists) | Unlicense (public domain) | Full list as published |
| `gambling` | [Steven Black's hosts — gambling extension](https://github.com/StevenBlack/hosts) | MIT | `alternates/gambling/hosts` diffed against the plain base list — only the gambling-specific additions were kept (the merged variant otherwise duplicates the base ad/malware list) |
| `mfa_clickbait` | [Steven Black's hosts — fakenews extension](https://github.com/StevenBlack/hosts) | MIT | Same diff-against-base technique. This is the closest free proxy for made-for-advertising/clickbait/content-farm domains — see the "known gap" note below |
| `scam_fraud` | [Blocklist Project — scam.txt](https://github.com/blocklistproject/Lists) | Unlicense (public domain) | Full list as published |

Deliberately **not** bundled: Blocklist Project's `fraud.txt` (196,080 entries, ~5.7MB —
too large and too noisy for a marketing-agency tool; would dwarf the skill package and
risks false positives at that volume) and `redirect.txt` (108,685 entries — mostly URL
shorteners, weak signal for "junk ad placement" specifically). If false negatives on scam
domains become a real problem in practice, `fraud.txt` is the first place to look, but pull
it as a separate on-demand lookup rather than bundling it wholesale.

## Known gap: no MFA-specific or kids-content list exists (research finding, not an oversight)

Research done before this skill was built (2026-07-01) found no free, actively-maintained,
downloadable domain list specifically for "made-for-advertising" (MFA) sites. Jounce
Media's MFA methodology (the industry-standard classifier, used by GroupM/DV/IAS) is
proprietary and not published. Adalytics.io publishes narrative reports naming individual
example sites but no structured list. The `fakenews` tag above is the best available free
proxy — it catches clickbait/disinformation-adjacent domains, which overlaps with MFA
behavior but is not the same category, and it does not catch bland-named professional MFA
operations that were built specifically to evade naive detection (e.g.
`daily-stuff.com`-style names).

**Kids-content has no free signal source at all** — not in this bundle, not found anywhere
in the underlying research. The skill relies on the "all-app-network-traffic" heuristic and
Google's own placement-category exclusions to catch some of this indirectly (see
`SKILL.md`), but does not claim to detect kids-content placements directly. Flag this
limitation in the audit output rather than pretending a heuristic covers it.

## Refreshing this file

These upstream lists update continuously (Steven Black's hosts is near-daily; Blocklist
Project updates on change). This bundled copy is a point-in-time snapshot — re-running the
fetch is cheap and safe:

```bash
# gambling: BLP explicit list + Steven Black's gambling-only delta (diffed against base)
curl -sL https://raw.githubusercontent.com/blocklistproject/Lists/master/gambling.txt -o /tmp/g_blp.txt
curl -sL https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts -o /tmp/base_sb.txt
curl -sL https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/gambling/hosts -o /tmp/g_sb.txt

# fakenews: Steven Black delta only (BLP has no fakenews-equivalent list)
curl -sL https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/fakenews/hosts -o /tmp/fn_sb.txt

# scam: BLP explicit list
curl -sL https://raw.githubusercontent.com/blocklistproject/Lists/master/scam.txt -o /tmp/s_blp.txt

extract() { grep -E '^0\.0\.0\.0|^127\.0\.0\.1' "$1" | awk '{print $2}' | grep -vE '^(localhost|local|broadcasthost|ip6-|255\.|::)' | sort -u; }
extract /tmp/base_sb.txt > /tmp/base_domains.txt
comm -23 <(extract /tmp/g_sb.txt) /tmp/base_domains.txt > /tmp/g_sb_delta.txt
comm -23 <(extract /tmp/fn_sb.txt) /tmp/base_domains.txt > /tmp/fn_sb_delta.txt

{
  awk '{print $0"\tgambling"}' <(cat <(extract /tmp/g_blp.txt) /tmp/g_sb_delta.txt | sort -u)
  awk '{print $0"\tmfa_clickbait"}' /tmp/fn_sb_delta.txt
  awk '{print $0"\tscam_fraud"}' <(extract /tmp/s_blp.txt)
} | sort -u -t$'\t' -k1,1 > junk_domains.tsv
```

Re-run maybe every few months, or when the audit skill's false-negative rate on obvious
junk seems to be climbing (a sign the bundled snapshot is going stale).
