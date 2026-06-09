# Classification taxonomy (shared reference for the loop's diagnostic agents)

Single source of the classification rules the loop's agents apply. Lifted from the
field-tested taxonomy in `plugins/google-ads-optimization/skills/search-terms/SKILL.md`
(adopted from a real Inbound user template, Dansk Studie Center). The loop's search-term
agent uses this; the asset-hygiene agent uses the angle taxonomy at the bottom.

## Search-term buckets (one per term, priority order)

A **keyword** is what you bid on; a **search term** is what the user actually typed, matched
via match types + Google close variants. The search terms report is where spend leaks.

1. **PLACEMENT_PROBLEM** (priority 1) — relevant for the client but lands in the wrong place.
   Set `placement_reason`:
   - **struktur** — the term (normalised) exists as an ENABLED keyword in 2+ ad groups, or in a
     *different* ad group than the one it served here. Pulling traffic from its canonical home.
     **Filter test/duplicate campaigns first** (`/w2m|test|vol 2/i`) — a keyword's presence in a
     test campaign is not a legitimate "correct home". The structural check only nominates;
     pick the canonical home (Destination over Generisk, Brand over non-Brand, exact-intent over
     catch-all) and recommend a negative in the others.
   - **intent** — relevant, lives in one ad group, but the ad group's ad/LP do not address the
     search intent. Compare the term against the ad group's top headlines + final URL.
2. **IRRELEVANT** — does not fit the client's offering (grounded in the scraped offering) or is
   clear off-intent (gratis, selv/DIY, jobs/stilling, brugt, wikipedia/forum, competitor). →
   negative keyword. Name the offending token in the reason.
3. **VINDER** — converts well and is **not already its own exact keyword**: `conversions >= 1`
   AND `cpa <= account_cpa * 1.0` (when account_cpa is reliable) else `conversions >= 2`. →
   promote to exact (control bid + quality).
4. **RELEVANT (godt placeret)** — matches the offering and is correctly placed (already exact, or
   on-intent and well-located). **No action.** Never tell the user to "add as keyword" for a term
   that already triggers via an equal EXACT keyword — that contradiction was exposed in the live
   test.
5. **GRAENSE** — generic/ambiguous, cannot be confidently assigned. Flag for manual review.
   Honest bucket; do not force.

A term that is both convertible and mis-placed is **PLACEMENT_PROBLEM** (placement is the more
actionable fix).

## Significance discipline (non-negotiable — the spine of the loop)

On Inbound's small Danish accounts, do not claim confidence the data cannot support:
- `account_cpa` is reliable only if `account_conversions >= 10`; else fall back and flag
  `low_confidence`.
- A VINDER needs `>= 2` conversions; never promote a "winner" resting on 1.
- Compute ROAS only if the account has any conversion value; never on a zero-value account.
- This mirrors `annonce-optimering`'s hard-won lesson (per-asset CVR is confounded +
  sub-significance) and `search-terms`' `WINNER_MIN_CONV` / low-confidence flag.

## Recommended-negative levels

- **ad group** for PLACEMENT_PROBLEM (block the precise term in the wrong group).
- **account / shared list** for generic IRRELEVANT tokens.
- **campaign** for client-specific irrelevant.
- Match type: EXACT for placement fixes (precise term), PHRASE for generic-irrelevant tokens.

## Angle taxonomy (for asset-hygiene gap-briefs)

Each RSA asset is classified into one angle; an ad group missing an angle gets it flagged as a
gap (fed to the RSA builder). Same taxonomy as
`responsive-search-ads/references/headline-craft.md`:

`benefit` · `trust` · `urgency` · `CTA` · `feature` · `keyword-led` · `brand` · `location` ·
`garanti`

The gap-brief lists, per ad group, which angles have no served asset + a one-line suggestion for
the challenger headlines that would fill them.
