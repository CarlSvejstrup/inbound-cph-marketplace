# Offering brief — Phase 0 ground truth for the loop

The loop's classification (is a term a winner, a negative, on-offering?) only means something if
the **offering is established first**. The taxonomy (`lib/classify/taxonomy.md`) literally defines
IRRELEVANT as "does not fit the client's offering (grounded in the scraped offering)" — so the
offering is an *assumed input*. Before this brief, the search-term agent half-guessed it. Phase 0
makes it explicit.

Decided with Carl 2026-06-09. A **Phase 0 sub-agent runs FIRST** (before the three diagnostics),
builds ONE `offering.md` in the run dir, and that file is fed into every downstream sub-agent's
prompt. Internal context (NOT a workbook tab), built fresh each run.

## Why it grounds everything, not just search-terms

- **Search-terms:** turns "is `grupperejse bali` relevant?" from a guess into a lookup against what
  DSC actually sells. Generates the `OFFERING_TOKENS` the sweep's proposed negative-bands use.
- **Asset-hygiene / RSA challengers:** the angle-gap brief + new challenger copy are grounded in
  the real offering + audience, not invented.
- **Quality Score:** the landing-page relevance read has the page content as context.

## Sources (both, cross-checked)

1. **Landing page(s)** — scrape the ad groups' `final_urls` (already pulled by
   `ad_group_ads_query`) via Firecrawl. The client's own words for what they sell + to whom.
2. **Account signals** — campaign names, ad-group names, and existing RSA headlines (from the
   pulls the diagnostics already do). What they're *already advertising* is a strong offering
   signal and catches things the landing page omits (a destination they bid on without a
   dedicated page). Where the two disagree, note it — that's a real finding for the expert.

## `offering.md` schema (the Phase 0 agent fills this)

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
<audience/segment — e.g. DSC = students / unge 18-35. This decides whether `ungdomsrejser` is
on-target and `pensionist-rejser` is not.>

## Geografi & sprog
<market + language — e.g. Danmark, dansk. (Drives the negative call on foreign-geo terms.)>

## Brand & navne-varianter
<brand name + its common misspellings/variants seen in the account — so `danskstudiecenter`,
`dsc` are recognised as BRAND, not generic. Competitor brand names that appear, if any.>

## IKKE en del af tilbuddet (out-of-scope)
<explicit negatives gold: categories/intents the client does NOT serve. Generic off-intent
(gratis, selv/DIY, jobs, brugt, wikipedia/forum) PLUS client-specific ones the sources reveal
(e.g. a destination they dropped, a product they don't carry). A term hitting these is a
confident GROEN block.>

## Konto vs. landingside (uoverensstemmelser)
<optional: where the account advertises something the landing page doesn't mention, or vice
versa. A real signal for the expert, not an error to hide.>

<!-- MACHINE-READABLE — parsed by sweep.parse_offering_tokens(). Comma-separated, lowercase,
     Danish letters OK. These ARE the offering vocabulary (what the sweep treats as on-offering
     when proposing negative-bands): product/category/destination words + brand variants.
     Do NOT put out-of-scope words here. -->
OFFERING_TOKENS: hoejskole, højskole, grupperejse, grupperejser, studierejse, studierejser, sabbatår, bali, thailand, ...
```

## The token contract (brief -> sweep)

The `OFFERING_TOKENS:` line is the seam to `sweep.py`. `sweep.parse_offering_tokens(md_text)`
extracts it into the `set` that `sweep_negatives(rows, offering_tokens)` consumes. This makes the
proposed negative-band **deterministic** (same brief → same tokens → same proposed colours); the
agent still overrides per-term with the richer read. Tokens are the *on-offering* vocabulary only —
a negative candidate sharing NO token with the offering → proposed GROEN; full overlap → ROED.

**Why an explicit list, not agent-parsed prose:** determinism + auditability. The list is right
there in `offering.md`; if the proposed bands look off, you can see exactly which tokens drove them.

## Honest limits

- **Scrape can fail / be thin** (JS-only page, login wall). If Firecrawl returns little, fall back
  to account-signal-only and SAY SO in the brief's `Kilde` line — never fabricate an offering.
- **The brief is the agent's best read, not gospel.** It's internal context; the relevance calls
  it grounds are still recommend-only and human-gated downstream. A wrong offering line biases the
  *proposed* bands, but the expert reviews every negative before anything is blocked.
- **Build fresh each run** for now (no cache). If it becomes a bottleneck, cache per client later
  (a decision about where it lives — deferred).
