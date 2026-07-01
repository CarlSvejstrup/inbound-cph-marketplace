# Selection spec — script-first candidate sweep (negatives + new keywords)

Design record for moving the "which search terms become negatives / new keywords" decision from
**agent prose** to a **deterministic script sweep**, so nothing is silently dropped. The agent's
role shrinks to judgement *on top of* a guaranteed-complete list, never finding-or-losing.

Decided with Carl 2026-06-09. Status: SPEC (approve before building).

## The principle

> **The script owns "nothing is forgotten." The agent owns "how safe / how relevant."**

Today the agent both finds and judges, so a qualifying term can vanish with no trace (Carl hit
this: a `≥2 conv` term that never appeared as a new keyword). Fix: a script sweep over the
search-term rows produces the complete candidate set deterministically; the agent then annotates
(confidence, reason) but can never silently add or drop. Every candidate either lands in the
workbook or carries a script-provable reason it didn't.

This is a new module — `lib/sweep.py` — run by the search-term sub-agent BEFORE classification.
It consumes the already-pulled rows (`search_terms_query`) + the existing keyword map
(`keyword_map_query`, already in `lib/gaql/search_terms.py`). No new GAQL.

---

## New keywords — deterministic sweep

A search term becomes a **new-keyword candidate** iff BOTH hold (pure script, no agent):

1. `conversions >= WINNER_MIN_CONV` (default **2** — the inherited significance floor).
2. The normalised term matches **NO existing ENABLED keyword on ANY match type**
   (exact / phrase / broad). "No match overhauls" = Carl's call: only propose genuinely
   uncovered terms. Matching uses `keyword_map_query` rows; normalise both sides (lowercase,
   collapse whitespace, strip surrounding brackets/quotes) and compare on text equality.

**Then an OFFERING check splits the candidates (added 2026-06-10 — this was a real design hole).**
The whole Phase 0 premise is "classification is meaningless without knowing what the client sells",
yet winner selection used to skip the offering entirely — so an off-offering destination like
`zanzibar rejse` got recommended as a new keyword to a destination the client doesn't sell. The
root cause: **a conversion on a lead-gen account is a LEAD, not proof the search intent matched the
offering** (someone can land and sign up for something else). Significance discipline covers
volume; it does NOT cover attribution validity. So each candidate is checked against the offering
vocabulary (`offering_overlap`, the same `offering.md` tokens the negative bands use):

- **on-offering** (partial or full overlap, OR no offering context at all) → **"Nye keywords
  (vindere)"** tab, `Match type = Exact`, `Status = Paused`. Promotable.
- **off-offering** (has content words, none of which are offering vocabulary) → **"Vindere til
  gennemgang"** tab. Surfaced + flagged, **never auto-promoted**. The expert moves a confirmed one
  to the Nye keywords tab by hand.

**Flag, NOT gate.** A hard out-of-scope gate in the script would re-break the very guarantee this
sweep exists to give (nothing qualifying silently dropped) — and the offering-token signal is
heuristic, so gating on it would kill real winners. Flagging fails safe: a skipped agent review
leaves the term *visible but not promoted*, and it structurally cannot reach a CSV. With no offering
context (empty tokens, scrape failed) the check is a no-op and everything stays promotable.

**The token split is COARSE — the agent's bucket is the real catch (the `zanzibar højskole` case).**
The script's overlap test only catches a term with ZERO offering words. `zanzibar højskole` shares
`højskole`, so it scores *partial* and the script keeps it a promotable winner — the script cannot
know the *destination* is off-offering. Routing all partials to review would over-flag legitimate
ones (`københavn højskole`, `weekend højskole`). So the fix is `reconcile_winners_with_buckets()`:
after the agent assigns offering-grounded buckets, any winner the agent bucketed **IRRELEVANT**
(off-offering) or **PLACEMENT_PROBLEM** (relevant, wrong ad group) is **demoted** from `winners` to
`review_winners`. This also closes a coherence hole — without it the same term could be *promote* on
"Nye keywords" AND *IRRELEVANT* on "Alle søgetermer" in one workbook. The reconcile is OBLIGATORY in
the SKILL.md flow (Trin 2, after bucketing, before build). The script owns the easy token split; the
agent's richer offering read owns the hard cases like `zanzibar højskole`.

**Token-overlap quality (2026-06-10):** `offering_overlap` matches multi-word offering tokens via
n-grams (so `new zealand` / `costa rica` / `sri lanka` match as a UNIT, not as stray words) and
strips a generic stoplist (`rejse`, `unge`, `billig`, `dansk`, …) before judging overlap — without
both, single-word tokenisation + generic words made the proposed bands and the offering check noisy.
`degree` is computed over CONTENT tokens only, so `grupperejser bali` (bali on-offering) reads as a
full match, not "partial because of rejser".

**The agent may still** add a one-line Danish `Begrundelse` per row, and MAY flag a row it thinks
is wrong (e.g. "reelt jeres brand") in a `Agent-note` metadata column — but the row STAYS on its
tab. The expert deletes it if they agree; the script never withholds it.

**What the script records for transparency** — terms that hit `≥2 conv` but did not land on Nye
keywords go to one of two reference tabs with the deterministic reason:
- `already_covered: "<matched keyword>" (<match type>)` → **Sprunget over** — the legitimate, common case.
- `off_offering` → **Vindere til gennemgang** — converts, but looks outside the offering.

So a `≥2 conv` term is always on exactly one of three tabs (Nye keywords / Vindere til gennemgang /
Sprunget over), each with a script-provable reason. No more guessing why one fell off.

---

## Negative keywords — deterministic sweep + script-proposed confidence

A search term becomes a **negative candidate** iff BOTH hold (pure script):

1. `conversions == 0`.
2. `cost_dkk >= NEGATIVE_COST_FLOOR_DKK` (default **50** — matches the `annonce-optimering`
   MIN_IMPRESSIONS spirit; below this is too little data to judge).

→ Every term passing 1 + 2 is **guaranteed** on the "Negative keywords" tab as a candidate.
ONE list (Carl's call), each row **colour-coded by confidence**, sorted by `cost_dkk` desc.

### Confidence = RELEVANCE (Carl's axis), with data-thinness as a SEPARATE flag

The colour answers Carl's exact question: **"hvor sikker er agenten på at ordet trygt kan
blokeres"** — i.e. how clearly irrelevant the term is. That is a *relevance* axis. It is NOT the
same as "do we have enough data," which is a *significance* axis. Folding the two into one colour
(the first draft's mistake) would colour `wikipedia` with 3 clicks 🟡 just because clicks<5 — even
though it's obviously safe to block. So we keep them orthogonal:

**Colour = relevance band (agent-owned, script-proposed):**

| Band | Meaning (relevance to the client offering) |
|---|---|
| 🟢 GROEN | Clearly off-offering → safe to block (`wikipedia`, `job`, a competitor name) |
| 🟡 GUL | Loosely / partially related → check before blocking |
| 🔴 ROED | Looks relevant to the offering → probably should NOT be a negative (agent flags why) |

- **Script proposes** the band from a literal **offering-token overlap** test (the search-term
  stage already scrapes the offering for classification): no token overlap → propose 🟢; partial
  overlap → 🟡; strong overlap → 🔴. Token overlap is only a **hint, never a gate** — it is crude
  (`grupperejse bali` overlaps the offering yet may be a fine negative; a misspelling may be
  relevant yet share no token). So the agent freely up/downgrades with the richer language read
  ("'wikipedia' is pure info-search → 🟢" / "this is actually a product line → 🔴").
- **Agent override is logged:** a `Konfidens-justering` metadata column records
  `script: GUL -> agent: GROEN (grund: ...)`. Transparent both ways.

**Data-thinness = a SEPARATE column, not a colour.** A `Tynd data`-flag (metadata) is set by the
script when `clicks <= CLICK_CONF_FLOOR` (default 5) — the significance signal stays visible
(a 🟢 term with only 2 clicks reads "safe to block, but thin data") without letting click-count
override the relevance colour. The expert sees both axes independently.

### Why negatives are NOT symmetric with new keywords (the guardrail)

A negative blocks future traffic and is harder to undo than skipping a keyword. On Inbound's small
Danish accounts a `0 conv / 60 DKK` term may be seasonal, a broad-to-narrow conversion path, or
sub-significance. So the script **never auto-applies** a negative — it surfaces every candidate
with its numbers (cost, clicks, impressions) + the confidence colour; the **expert decides**.
"Nothing forgotten" (the sweep) + "nothing over-blocked" (colour + human gate) both hold.

---

## The "Alle søgetermer" overview tab (reference only, NEVER a CSV)

A full-picture tab so the expert sees everything spend went to, with the action tabs as distilled
subsets of it. Decided 2026-06-09.

- **Content:** every search term with `cost >= 5 DKK` — i.e. the whole `search_terms_query` pull
  (the 5 DKK spend floor is already the query default; ~177 rows on DSC). Sorted by `cost` desc.
- **Columns:** `Søgeterm`, `Kampagne`, `Ad group`, `Cost (DKK)`, `Klik`, `Konverteringer`, `CPA`,
  `Gruppe` (which bucket it fell in).
- **Colour = BUCKET** (the classification axis — distinct from the Negative tab's *confidence*
  axis; same visual language, two deliberately different meanings):
  | Colour | Bucket |
  |---|---|
  | 🟢 GROEN | VINDER (≥2 conv, not yet a keyword) |
  | 🔵 BLAA | RELEVANT (already covered / well-placed) |
  | 🟠 ORANGE | PLACEMENT_PROBLEM (relevant, wrong ad group) |
  | 🔴 ROED | IRRELEVANT (negative candidate) |
  | ⚪ GRAA | GRAENSE (borderline) |
- The two action tabs ("Nye keywords (vindere)", "Negative keywords") are **distilled subsets** of
  this overview — every actioned term traces back to a coloured row here.
- **NEVER becomes a CSV.** The tab is named `Alle søgetermer` — which matches NO `editor-csv-export`
  alias (the converter reads keywords from `Keywords`/`Keyword`/`Nye keywords (vindere)`, negatives
  from `Negative keywords`/`Negatives`). So it is structurally invisible to the converter. This is
  the same isolation guarantee as the `Sprunget over`, `Vindere til gennemgang`, and `Quality Score`
  tabs — **all four** reference tabs are alias-invisible. The round-trip test must confirm no row
  from any of them reaches `keywords.csv` or `negatives.csv`.

**Æ/Ø/Å is load-bearing here** — the `Gruppe` column + Danish campaign/term text (`Søgeterm`,
`Højskole`, `Grupperejser`) must survive. `review_workbook` writes the .xlsx with correct encoding
and `editor-csv-export` uses UTF-8-BOM (verified live today); keep that, and verify Danish chars
render in the overview tab specifically.

## Workbook changes (`review_workbook.py`)

The overview tab above, plus both action tabs gain metadata columns (light header, converter DROPS
them — Editor never sees them):

- **Nye keywords (vindere):** add `Agent-note` (optional). Editor columns unchanged.
- **Negative keywords:** add `Konfidens` (🟢/🟡/🔴 + GROEN/GUL/ROED text for accessibility) +
  `Klik` + `Impressions` + `Tynd data` + `Konfidens-justering`. The `Konfidens` cell gets the band
  colour fill. Editor columns (`Campaign / Level / Ad group / Negative keyword / Match type`)
  unchanged — so the `editor-csv-export` contract is untouched (it drops everything outside the
  Editor band).
- The filtered `≥2 conv` terms (the ones a script reason removed) go on a **SEPARATE tab named
  `Sprunget over`** — NOT as rows on "Nye keywords (vindere)". This is a hard requirement: the
  converter matches the keywords tab by alias (`Keywords` / `Keyword` / `Nye keywords (vindere)`),
  and `Sprunget over` does not match any alias, so those rows can never leak into `keywords.csv`.
  Putting them on the winners tab would import the very terms we deliberately filtered — the exact
  silent corruption this whole change exists to prevent.

**Converter impact:** the new **columns** are all metadata (the converter reads named Editor
columns and ignores the rest → never sees `Konfidens`/`Klik`/`Tynd data`/etc.). The Editor-bound
columns + the `editor-csv-export` keep-list don't change. The one real risk is the `Sprunget over`
content — safe ONLY because it's a separate, non-alias-matching tab. **Re-run the round-trip after
building and confirm `keywords.csv` contains zero `Sprunget over` terms.**

---

## Analysis window — default 90 days (decided 2026-06-09)

The selection sweep needs enough data that `≥2 conv` and `≥50 DKK` are signal, not noise. On
Inbound's small Danish accounts 30 days is often too thin, so the **default window is 90 days**
(3x the data → fewer `Tynd data` cases, stronger winner/waste signal). Intake still asks (always
an `AskUserQuestion`): `Sidste 90 dage (Anbefalet)` / `Sidste 30 dage` / `Andet (BETWEEN)`.

**Per-diagnostic window handling (the one gotcha):**
- **Search-terms + asset-hygiene** → `window_clause(window)` builds `BETWEEN '<start>' AND
  '<slut>'` for 90 days. Works as a GAQL `segments.date` clause.
- **Quality Score** → `LAST_90_DAYS` is NOT a valid literal for `get_quality_score_audit`
  (verified live: `INVALID_VALUE_WITH_DURING_OPERATOR`). `date_range_arg(window)` must build the
  `BETWEEN` tuple form for 90 days; its guard already raises on the bare `LAST_90_DAYS` literal.
  So the QS sub-agent passes the computed `BETWEEN` window, never the literal.

**The 50 DKK waste floor stays FIXED regardless of window** (decided 2026-06-09). Over 90 days the
sweep catches more candidates (a leak that summed to 50 DKK over 3 months is still surfaced — the
"nothing forgotten" goal). The `Tynd data` flag + the confidence colour handle the weak ones, and
nothing auto-applies (human gate), so over-capture is safe. A 50-DKK-over-90-days term is weaker
waste than 50-over-30 — that nuance is what the expert reads from cost + clicks, not a moving floor.

## Constants (top of `lib/sweep.py`, tunable per run)

```
WINNER_MIN_CONV          = 2      # a winner needs >= 2 conversions (inherited floor)
NEGATIVE_COST_FLOOR_DKK  = 50     # a negative candidate needs >= 50 DKK wasted, 0 conv
CLICK_CONF_FLOOR         = 5      # <= 5 clicks => set the separate `Tynd data` flag (NOT a colour)
```

All three are shown in the workbook "Laes mig" / Oversigt so the expert knows what was swept.

**Relevance-band precedence (deterministic, evaluate in this order):** strong offering-token
overlap → 🔴; else partial overlap → 🟡; else (no overlap) → 🟢. The `Tynd data` flag is set
independently (`clicks <= CLICK_CONF_FLOOR`) and never changes the colour. No ambiguity: each term
gets exactly one band + an independent thin-data boolean.

---

## What stays agent work (deliberately)

- The 5-bucket **taxonomy classification** (RELEVANT / VINDER / PLACEMENT_PROBLEM / IRRELEVANT /
  GRAENSE) still informs the agent's confidence override + the placement-problem routing. The
  script sweep is the *floor* (catch everything quantitative); the taxonomy is the *nuance* on top.
- **PLACEMENT_PROBLEM** routing (term is relevant but in the wrong ad group) stays agent-judged —
  it's not a simple cost/conv threshold. Such a term may be a `0 conv` negative-in-wrong-adgroup
  AND belong as a keyword elsewhere; the agent decides, the script just guarantees it's surfaced.

## Verification plan (when built)

1. Unit: feed synthetic search-term rows + a keyword map → assert the sweep catches exactly the
   qualifying terms, `already_covered` filters correctly on each match type, confidence bands map
   from the hard signals.
2. Live DSC: re-run the real search-term pull through `sweep.py`; confirm the `≥2 conv` terms
   that "went missing" before now either appear or are named in `Sprunget over` with the matched
   keyword (this directly answers Carl's original question).
3. Converter round-trip: build the workbook, run `editor-csv-export`, confirm the Editor CSVs are
   unchanged in shape (new metadata columns dropped, negatives still correct) AND that neither
   `keywords.csv` nor `negatives.csv` contains any row from the `Alle søgetermer` overview tab or
   the `Sprunget over` tab (both are alias-invisible — prove it, don't assume it).
4. Danish chars: confirm æ/ø/å render correctly in the overview tab's `Gruppe` column + term text,
   and survive the CSV round-trip (UTF-8 BOM).
5. Overview completeness: every row on the two action tabs traces to a coloured row in
   `Alle søgetermer` (the action tabs are strict subsets of the overview).
