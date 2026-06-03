# Structuring rules (the Phase-2 gate)

Single source of truth for how the `structuring` skill turns Phase-1 research into a
Google Ads account architecture: ad groups, keyword selection + match types, and
client-specific negative additions. All numbers here are verified (2026-06-03, three
source-cited research passes + two live data-source checks). If SKILL.md and this file
disagree, this file wins.

---

## 1. Ad groups — fewer, broader (Rikke-confirmed)

Rikke's instinct is correct: use **fewer, broader ad groups** so the account gathers data
better. State the mechanism at the RIGHT level so the skill explains itself.

**Two levels, do not conflate them:**

- **Campaign / bid-strategy level — conversion pooling.** Smart Bidding (Maximize
  Conversions, Target CPA) pools conversions at the campaign level, NOT per ad group.
  Floor to exit learning: **~30 conversions / 30 days** (hard min ~15 for Target CPA;
  ~50 for Target ROAS). So merging ad groups inside one campaign does NOT give the bidder
  more conversion data — the campaign already pooled it.
- **Ad-group level — RSA impression density.** The genuine payoff of consolidating ad
  groups: each group's RSAs cross a rough **~2,000 impressions/month** floor before
  asset-level performance signal becomes meaningful, and you avoid keyword cannibalization
  between near-duplicate groups. (The ~2,000 figure is a **practitioner heuristic, NOT an
  official Google number** — treat it as directional.)

**The guardrail (defensible default the skill builds to):**

| Rule | Value | Basis |
|---|---|---|
| Ad group = | one tight theme / one intent / one landing page | Ad Relevance → Quality Score |
| Min keywords/group | > 1 (NO single-keyword ad groups) | SKAGs dead post-2018 (close variants + Smart Bidding + RSAs) |
| Soft band | ~5-15 keywords/group | practitioner consensus — NOT an official Google number |
| Split when | one RSA can't be genuinely relevant to every keyword in the group | protects Ad Relevance |
| Merge when | a theme-sibling group sits below ~2,000 impr/mo | RSA asset-signal floor |

**Self-explanation string (use verbatim in output):**
> "Fewer, broader ad groups concentrate impressions so each ad group's RSAs build up enough
> serving volume (rule of thumb ~2,000 impr/month) for asset-level signal, and reduce
> keyword cannibalization. Smart Bidding's conversion learning happens at the campaign level
> (~30 conv/30d), so we don't split into many campaigns. We stop consolidating when one RSA
> can no longer be relevant to every keyword in a group — that protects Ad Relevance and
> Quality Score. Exact + selected Phrase keeps the consolidation benefit intact; the only
> thing we forgo vs broad match is automated query discovery, which we recover via manual
> search-terms mining."

(The ~2,000 impr/month and the ~15 Target-CPA minimum are practitioner heuristics; ~30
conv/30d and ~50 for Target ROAS are roughly Google-published. Don't present the heuristics
as Google fact in client output.)

This OVERRIDES the blueprint's tight 3-5-keyword single-intent rule. Same precedence as
Ian's no-Broad override: real Inbound practice beats the generic blueprint.

**Trap to avoid:** the consolidation/hagakure method is, in the literature, almost always
paired with broad match + Smart Bidding. Inbound locked no-Broad. Consolidation here is
achieved via **fewer ad groups, NOT by unlocking broad**. Keeping Exact/Phrase preserves
the data-aggregation benefit fully; it only narrows automated query discovery.

---

## 2. Keywords — LLM-generated, theme-derived, NO volume grounding

Verified live 2026-06-03: for a **net-new** account there is no machine keyword-volume
source in this stack.
- Google Ads MCP exposes only existing-campaign keyword data (`keyword_view` GAQL,
  `get_keyword_performance`, search-terms report). There is **no Keyword Planner
  ideas/volume surface** (KeywordPlanIdeaService is not a GAQL resource).
- Semrush MCP `keyword_research` is plan-gated (no data) — verified Phase 1.

So generate keyword candidates from the **landing-page-analyzer + competitor-research
output + theme**. Group them by intent into the ad groups from §1.

**Honesty rule (load-bearing):** generated keywords are **theme-derived, NOT
volume-ranked**. The skill MUST say so and route volume validation to the human (Keyword
Planner in the Google Ads UI). Keywords are fairer to generate than negatives or
trust-claims — but only if the gap is stated explicitly.

**Match types — Exact + selected Phrase only, NO Broad** (Ian's tab 01).
- CRITICAL (verified, Editor answer 47635): a **blank match-type column OR a bare keyword
  term defaults to BROAD** on Editor import. Emit an explicit `Exact` or `Phrase` value on
  EVERY keyword row — never blank, never bare — or the lock is silently violated.
- Default the bulk to **Exact** (tightest control); promote a term to **Phrase** only when
  the searcher's intent has meaningful word-order/qualifier variation worth capturing.
- The campaign-temperature taxonomy (Brand / Product / Generic) from ads-notes informs
  which terms to include and how aggressive copy will be — Brand = warmest, Generic = cold
  high-volume. Tag each ad group with its temperature.

---

## 3. Negatives — ADD to the inherited MCC list, never re-dump it

The canonical cross-account generic negative list is an **MCC shared negative keyword
list**, NOT a Drive file and NOT something the skill regenerates:

- **`"Generelle negative søgeord"`** — shared_set id **`6688642473`**, **277 members**
  (242 broad / 34 phrase / 1 exact), in the **Inbound CPH Clients MCC (`1138360630`)**.

**The skill emits client-specific additions ONLY — not the 277.** The shared list is
applied **by reference** as a launch-gate step, never as inline CSV rows.

- **Apply-by-reference launch step:** "Attach shared negative list 'Generelle negative
  søgeord' (id 6688642473) to the new campaign." (Shared-list-via-CSV import is UNVERIFIED;
  another reason not to emit the 277 as rows.)
- **Pull the 277 live as context** (do NOT bake a static snapshot into the repo — the
  agency edits the master; a snapshot drifts):
  ```
  SELECT shared_criterion.keyword.text, shared_criterion.keyword.match_type
  FROM shared_criterion WHERE shared_set.id = 6688642473
  ```
  run against customer_id `1138360630`. Use it as the "already-covered" set so the LLM does
  NOT regenerate `gratis`/`job`/`guide`/`wiki` etc. as if they were novel.
  If the MCC isn't reachable in the run, fall back to the documented example snapshot in
  `references/generelle-negative-eksempel.md` (example only — the live list is canonical).

**Match-type rule for negatives (do NOT confuse with the positive no-Broad lock):**
- The no-Broad lock is for POSITIVE keywords only. For NEGATIVES, broad is the correct
  default — negative broad blocks any query containing all the words (in any order). Leave
  inherited negatives as-is; never normalize them to phrase/exact.
- Negative match types behave differently from positive (verified, Google answer 2453972):
  | Negative type | Blocks | Does NOT block |
  |---|---|---|
  | broad (bare text) | queries containing ALL the words, any order | plurals/singulars, synonyms, close variants, word subsets |
  | phrase (`"..."`) | the words in order (extra words OK) | plurals/singulars, synonyms, out-of-order |
  | exact (`[...]`) | only the exact term | everything else |
  - Casing + **misspellings are auto-handled** since 2024 — do NOT generate misspelling
    variants (wasted effort).
  - Plurals/singulars + synonyms are NOT auto-handled — emit **singular+plural pairs and
    key synonyms explicitly** (the live list already does: `guide/guider/guides`,
    `bog/bøger`).

**Two tiers + monitor (mirrors Ian's tabs 04 + 05):**
1. Inherited shared list — applied by reference (the 277, launch-gate step).
2. Researched client-specific additions — campaign-level, generated from the client's
   business (what would waste this client's spend that the generic list misses).
3. Monitor-first candidates — speculative negatives NOT committed up front; watched via the
   search-terms report first. A negative is a hard block with no expansion safety net, so
   an over-broad negative silently kills good traffic. Standard loop: launch with the
   conservative generic block + vetted client additions, then mine search terms weekly and
   add observed waste in verified batches.

**Limits (safe build-time caps, verified):** 10,000 negatives/campaign; 5,000 per shared
list; 20 shared lists/account. (A 2025 report claims the shared-list cap doubled to 10,000
but Google hasn't confirmed — use 5,000 as the safe cap.)

---

## 4. Editor CSV encoding (what the assembler will emit; structuring just tags it)

structuring produces the structured object; the Phase-4 assembler renders CSVs. But
structuring must tag each row with the fields the assembler needs, so the rules are here.

- **English headers**, regardless of Editor install language (verified, answer 57747):
  "headers must be in English" for auto-recognition; capitalization/spacing don't matter.
  Non-English forces a manual remap step — so emit English.
- **Keyword rows:** `Campaign`, `Ad group`, `Keyword`, `Match type` (value `Exact`/
  `Phrase` — never blank), `Status`. Identity key = campaign + ad group + keyword + match
  type.
- **Negative rows** (client-specific additions only): Editor carries the negative flag in
  the `Type` column — `Type=Negative` for ad-group-level, `Type=Campaign negative` for
  campaign-level (verified, answer 57747). Match type via bracket/quote/plain syntax on the
  keyword text, OR the explicit column — pick ONE per file (mixing throws errors).
- **Encoding:** UTF-8 CSV for a programmatic writer; the UTF-16/Unicode-Text guidance
  (answer 56368) is an Excel-roundtrip workaround. Danish æ/ø/å make encoding load-bearing.
- **match_type casing:** emit capitalized `Exact`/`Phrase`/`Broad` in the object. The
  Phase-4 assembler must normalize case before comparing/writing the Editor value (Editor
  itself accepts case-insensitive match-type words per answer 57747).

---

## 5. Output object shape (consumed by rsa-copywriter + assembler)

```json
{
  "campaign": "IC | GSN | AI-SEO",
  "ad_groups": [
    {
      "name": "AI SEO bureau",
      "temperature": "Generic",
      "landing_page_url": "https://...",
      "theme": "one-line intent of this group",
      "keywords": [
        { "text": "ai seo bureau", "match_type": "Exact" },
        { "text": "ai seo konsulent", "match_type": "Phrase" }
      ],
      "angles": ["benefit: ...", "trust: ...", "CTA: ..."],
      "keyword_seeds_for_rsa": ["ai seo", "ai synlighed"]
    }
  ],
  "negatives": {
    "inherited_shared_list": {
      "apply_by_reference": true,
      "shared_set_id": "6688642473",
      "name": "Generelle negative søgeord",
      "mcc_customer_id": "1138360630",
      "note": "Applied as a launch-gate step, NOT emitted as CSV rows."
    },
    "client_specific_additions": [
      { "text": "gratis [client term]", "match_type": "Broad", "level": "campaign", "why": "..." }
    ],
    "monitor_first_candidates": [
      { "text": "...", "why": "watch in search-terms report before committing" }
    ]
  },
  "keyword_volume_disclaimer": "Keywords are theme-derived, NOT volume-ranked. Validate volume in Keyword Planner before launch.",
  "structure_rationale": "<the §1 self-explanation string>"
}
```

`angles` + `keyword_seeds_for_rsa` are the semantic content Phase-3 rsa-copywriter
consumes — this is why creative is downstream of the gate, not a peer.
