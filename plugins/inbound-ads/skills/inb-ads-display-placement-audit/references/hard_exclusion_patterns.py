"""
hard_exclusion_patterns.py — Inbound CPH's own standing exclusion rules for Display placements.

Source: Inbound's internally-used "Baggrund og ordliste" Doc + a "Google Display Network -
Baseline Negative Placement List" sheet (updated Feb 2026, both pasted into chat 2026-07-03;
Ian/Rikke's team has applied these manually before). The sheet's own cover note credits Lunio.ai's
100k Display Network Exclusion List (2025), DirectOM's Google Display Placement Exclusion List
(2025), and 2025-2026 industry research on MFA sites/ad arbitrage/gaming/kids content as sources.
These are NOT this skill's own judgment — they are Inbound's own standing list, used once or twice
a month across clients. A placement matching any of these gets `hard_exclusion: true` in
score_placements.py and lands directly in the report's "Anbefales fjernet" section with NO score,
NO web lookup, NO further review — the whole point of a hard-exclusion tier is that Inbound has
already decided these categories are unwanted regardless of which specific client is being audited.

This is intentionally separate from the softer, general-purpose junk_domains.tsv / gambling-keyword
signal in score_placements.py, which stays probabilistic (score + band) because it has no client
mandate behind it. Do not merge the two tiers — the distinction (client-confirmed standing rule vs.
this skill's own heuristic) is the whole reason hard-exclusion bypasses scoring at all.

Known gap, deliberately left open (2026-07-03): the source sheet's cover note also describes a
"High-Cost Low-Performance" category (premium publishers with high CPMs but low ROI for direct
advertisers — the sheet names NYT, CNN as examples) with an explicit caveat that these should
ONLY be excluded by budget-conscious advertisers NOT running brand-awareness campaigns. That
caveat means this category is conditional on campaign intent, not a blanket junk signal like
everything else in this file — it does not belong in hard-exclusion (which is meant to bypass
judgment entirely) even if the domain list is added later. No domain list for this category was
provided as of 2026-07-03; if one arrives, route it into score_placements.py as a new, separate,
lower-weight SCORING signal (lands in "unsure" for a human call) — never into this hard-exclusion
tier.
"""

import re

# "Ord til filter" — contains-match, case-insensitive, against the placement's domain/display_name.
# Deliberately broad substring matches (not word-boundaried) per the source doc's own "contains"
# instruction — e.g. "spil" inside "spilleautomat" or "kidz" inside "superkidzworld" should still hit.
KEYWORD_SUBSTRINGS = [
    "børn", "boern",
    "børnespil", "boernespil",
    "børnesange", "boernesange",
    "barn",
    "kid", "kids", "kidz",
    "spil",
    "gaming",
    "game",
    "quiz",
]

# ".io" is listed alongside the keywords in the source doc (not the TLD list below) — kept as a
# substring match here, matching the source's own placement of it under "Ord til filter".
KEYWORD_SUBSTRINGS.append(".io")

KEYWORD_PATTERN = re.compile(
    "|".join(re.escape(k) for k in KEYWORD_SUBSTRINGS),
    re.IGNORECASE,
)

# Foreign TLD list — "Bogstaver og url endelser for forskellige lande - filtrer på 'contains'".
# Source doc lists ~180 country-code TLDs INCLUDING Nordic/target-market ones (.dk is absent from
# the source list, but .se/.no/.fi are present, matching Inbound's own list verbatim). Applied as
# an exact-suffix match on the domain, same logic as RISKY_TLDS in score_placements.py, but this is
# a much larger, geography-based list rather than a "this TLD correlates with junk" list — it is a
# targeting-relevance filter (traffic from a market the client doesn't sell into), not a quality
# signal. Kept verbatim from the source doc, including entries that look unusual (.io, .to) because
# altering Inbound's own applied list defeats the purpose of matching what they already do by hand.
FOREIGN_TLDS = {
    ".ac", ".ad", ".ae", ".af", ".ag", ".ai", ".al", ".am", ".ao", ".aq", ".ar", ".as", ".at",
    ".au", ".aw", ".ax", ".az", ".ba", ".bb", ".bd", ".be", ".bf", ".bg", ".bh", ".bi", ".bj",
    ".bm", ".bn", ".bo", ".bq", ".br", ".bs", ".bt", ".bv", ".bw", ".by", ".bz", ".ca", ".cc",
    ".cd", ".cf", ".cg", ".ch", ".ci", ".ck", ".cl", ".cm", ".cn", ".cr", ".cu", ".cv", ".cw",
    ".cx", ".cy", ".cz", ".de", ".dj", ".dm", ".do", ".dz", ".ec", ".ee", ".eg", ".eh", ".er",
    ".es", ".et", ".fj", ".fk", ".fm", ".fo", ".fr", ".ga", ".gb", ".gd", ".ge", ".gf", ".gg",
    ".gh", ".gi", ".gl", ".gm", ".gn", ".gp", ".gq", ".gr", ".gs", ".gt", ".gu", ".gw", ".gy",
    ".hk", ".hm", ".hn", ".hr", ".ht", ".hu", ".id", ".ie", ".il", ".im", ".in", ".io", ".iq",
    ".ir", ".is", ".it", ".je", ".jm", ".jo", ".jp", ".ke", ".kg", ".kh", ".ki", ".km", ".kn",
    ".kp", ".kr", ".kw", ".ky", ".kz", ".la", ".lb", ".lc", ".li", ".lk", ".lr", ".ls", ".lt",
    ".lu", ".lv", ".ly", ".ma", ".mc", ".md", ".me", ".mf", ".mg", ".mh", ".mk", ".ml", ".mm",
    ".mn", ".mo", ".mp", ".mq", ".mr", ".ms", ".mt", ".mu", ".mv", ".mw", ".mx", ".my", ".mz",
    ".na", ".nc", ".ne", ".nf", ".ng", ".ni", ".nl", ".np", ".nr", ".nu", ".nz", ".om", ".pa",
    ".pe", ".pf", ".pg", ".ph", ".pk", ".pl", ".pm", ".pn", ".pr", ".ps", ".pt", ".pw", ".py",
    ".qa", ".re", ".ro", ".rs", ".ru", ".rw", ".sa", ".sb", ".sc", ".sd", ".sg", ".sh", ".si",
    ".sj", ".sk", ".sl", ".sm", ".sn", ".so", ".sr", ".ss", ".st", ".sv", ".sx", ".sy", ".sz",
    ".tc", ".td", ".tf", ".tg", ".th", ".tj", ".tk", ".tl", ".tm", ".tn", ".to", ".tr", ".tt",
    ".tv", ".tw", ".tz", ".ua", ".ug", ".um", ".us", ".uy", ".uz", ".va", ".vc", ".ve", ".vg",
    ".vi", ".vn", ".vu", ".wf", ".ws", ".xk", ".ye", ".yt", ".za", ".zm", ".zw",
}

# Nordic/target markets explicitly carved OUT of the foreign-TLD filter even though country-code
# TLDs are otherwise a blunt "not our market" signal. Danish agency clients routinely and
# legitimately show placements on Nordic-market sites; excluding .dk/.se/.no/.fi/.de/.uk by TLD
# alone would repeat the exact bt.dk/proff.no over-flagging mistake this skill was redesigned to
# avoid (proff.no is a .no site). None of these appear in the source doc's TLD list either.
_TLD_ALLOWLIST = {".dk", ".se", ".no", ".fi", ".de", ".uk", ".com", ".net", ".org"}
FOREIGN_TLDS = FOREIGN_TLDS - _TLD_ALLOWLIST

# Known consequence, kept intentionally (2026-07-03): .tv is Tuvalu's ccTLD and is in the source
# doc's own TLD list verbatim, so it stays in FOREIGN_TLDS. This means a legitimate site that
# happens to use a .tv vanity domain (a small minority of media/streaming brands do) would hard-
# exclude by TLD alone. User explicitly confirmed "exclude everything Inbound listed" over
# carving out individual TLDs on this skill's own judgment (2026-07-03 AskUserQuestion) — do not
# quietly remove .tv (or any other source-doc TLD) without asking again first.

# Non-Latin scripts — "Bogstaver ... filtrer på 'contains'". Source doc lists 11 alphabets
# (Hindi/Marathi Devanagari, Arabic, Bengali, Cyrillic, Urdu, Japanese Hiragana+Katakana, Telugu,
# Korean Hangul, Tamil) as individual characters. Represented here as Unicode block ranges rather
# than the literal character lists — equivalent coverage, far more compact, and immune to the
# source doc having sampled only some letters of each alphabet.
NON_LATIN_SCRIPT_RANGES = [
    (0x0900, 0x097F, "devanagari"),       # Hindi / Marathi
    (0x0600, 0x06FF, "arabic"),           # Arabic
    (0x0750, 0x077F, "arabic_supplement"),
    (0x0980, 0x09FF, "bengali"),
    (0x0400, 0x04FF, "cyrillic"),         # Russian
    (0x0500, 0x052F, "cyrillic_supplement"),
    (0x3040, 0x309F, "hiragana"),         # Japanese
    (0x30A0, 0x30FF, "katakana"),         # Japanese
    (0x0C00, 0x0C7F, "telugu"),
    (0x1100, 0x11FF, "hangul_jamo"),      # Korean
    (0xAC00, 0xD7AF, "hangul_syllables"),
    (0x0B80, 0x0BFF, "tamil"),
]


def matches_keyword(domain_or_name):
    """Contains-match against the børn/gaming/quiz keyword list. Case-insensitive."""
    if not domain_or_name:
        return None
    m = KEYWORD_PATTERN.search(domain_or_name)
    return m.group(0).lower() if m else None


def matches_foreign_tld(domain):
    """Exact-suffix match against the foreign-TLD list (Nordic/target markets excluded)."""
    if not domain:
        return None
    domain = domain.lower()
    for tld in FOREIGN_TLDS:
        if domain.endswith(tld):
            return tld
    return None


def matches_non_latin_script(text):
    """Returns the script name if any character in text falls in a non-Latin block, else None."""
    if not text:
        return None
    for ch in text:
        cp = ord(ch)
        for start, end, name in NON_LATIN_SCRIPT_RANGES:
            if start <= cp <= end:
                return name
    return None
