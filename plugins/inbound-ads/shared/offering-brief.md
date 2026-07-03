# Offering brief — Phase 0 ground truth

Any diagnostic or build skill that judges a client's Google Ads setup is only meaningful if the
**offering is established first**. "Is this term relevant?", "does this RSA angle fit?", "does this
landing page match the keyword?" — every one of these is a comparison against *what the client
actually sells*. If the offering is left implicit, the skill half-guesses it. Phase 0 makes it
explicit: establish what the client sells before classifying anything.

A **Phase 0 step runs FIRST** (before the skill's own diagnostics/build work), produces ONE
`offering.md` in the run dir, and that file grounds every downstream decision or sub-agent prompt.
Internal context (NOT a client-facing deliverable, NOT a workbook tab), built fresh each run.
Decided with Carl 2026-06-09.

## Why it grounds everything (example uses)

- **Search-term relevance:** turns "is `grupperejse bali` relevant?" from a guess into a lookup
  against what the client actually sells. Generates the `OFFERING_TOKENS` any negative-candidate
  logic scores against.
- **RSA angle grounding:** new challenger copy and angle-gap reads are grounded in the real
  offering + audience, not invented.
- **Quality Score landing-page read:** the ad-relevance and landing-page-experience judgement has
  the actual page content as context, so a low score is diagnosed against real copy, not assumed.

The same brief serves audits, onboarding analyses, quality-score reads, and copy work — one
grounding step, reused.

## Sources (both, cross-checked)

1. **Landing page(s)** — scrape the ad groups' `final_urls` (available from any `ad_group_ad`
   pull) via Firecrawl. The client's own words for what they sell + to whom.
2. **Account signals** — campaign names, ad-group names, and existing RSA headlines (from the
   pulls the skill already does). What they're *already advertising* is a strong offering signal
   and catches things the landing page omits (a destination they bid on without a dedicated page).
   Where the two disagree, note it — that's a real finding for the expert, not an error to hide.

## `offering.md` schema (the Phase 0 step fills this)

Danish prose + ONE machine-readable token block at the end. Keep it tight (the expert never edits
it, but it's fed into every prompt — concise = cheaper + sharper).

```markdown
# Virksomhedsprofil — <klient>

**Kilde:** <scraped URLs> + konto-signaler (kampagne-/ad-group-navne, RSA-headlines)
**Genereret:** <dato>

## Hvad de sælger
<2-5 lines: the actual services/products, in the client's own words. Be concrete — name the
product lines / categories / destinations, not "travel services".>

## Hvem det er for
<audience/segment — e.g. students / unge 18-35. This decides whether `ungdomsrejser` is
on-target and `pensionist-rejser` is not.>

## Geografi & sprog
<market + language — e.g. Danmark, dansk. (Drives the negative call on foreign-geo terms.)>

## Brand & navne-varianter
<brand name + its common misspellings/variants seen in the account — so the brand's own terms are
recognised as BRAND, not generic. Competitor brand names that appear, if any.>

## IKKE en del af tilbuddet (out-of-scope)
<explicit negatives gold: categories/intents the client does NOT serve. Generic off-intent
(gratis, selv/DIY, jobs, brugt, wikipedia/forum) PLUS client-specific ones the sources reveal
(e.g. a destination they dropped, a product they don't carry). A term hitting these is a
confident block candidate.>

## Konto vs. landingside (uoverensstemmelser)
<optional: where the account advertises something the landing page doesn't mention, or vice
versa. A real signal for the expert, not an error to hide.>

<!-- MACHINE-READABLE — parsed by any consumer that scores terms against the offering.
     Comma-separated, lowercase, Danish letters OK. These ARE the offering vocabulary (what a
     consumer treats as on-offering): product/category/destination words + brand variants.
     Do NOT put out-of-scope words here. -->
OFFERING_TOKENS: hoejskole, højskole, grupperejse, grupperejser, studierejse, studierejser, sabbatår, bali, thailand, ...
```

## The token contract

The `OFFERING_TOKENS:` line is the seam between this brief and any code that classifies terms. A
consumer parses it into a `set` of on-offering vocabulary and scores candidate terms against it.
This makes proposed classifications **deterministic** (same brief → same tokens → same proposed
result); the agent still overrides per-term with the richer prose read. Tokens are the
*on-offering* vocabulary only — a candidate sharing NO token with the offering scores as off-offering;
full overlap scores as on-offering.

**Why an explicit list, not agent-parsed prose:** determinism + auditability. The list is right
there in `offering.md`; if a proposed classification looks off, you can see exactly which tokens
drove it.

## Honest limits

- **Scrape can fail / be thin** (JS-only page, login wall). If Firecrawl returns little, fall back
  to account-signal-only and SAY SO in the brief's `Kilde` line — never fabricate an offering.
- **The brief is the agent's best read, not gospel.** It's internal context; the calls it grounds
  are still recommend-only and human-gated downstream. A wrong offering line biases the proposed
  result, but the expert reviews every recommendation before anything is applied.
- **Build fresh each run** for now (no cache). If it becomes a bottleneck, cache per client later
  (a decision about where it lives — deferred).
