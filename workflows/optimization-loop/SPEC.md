# Optimization Loop — SPEC

Single source of truth for the Google Ads optimization loop: a **local Claude Code
Workflow** that diagnoses a live account across several dimensions in parallel, then
chains the findings into a single editable Excel workbook for the expert to review, edit, and
(via a separate converter skill) turn into Google Ads Editor CSVs.

Status: **spec / build-in-progress.** This document is the design contract; the runnable
script is `loop.workflow.js` in this folder.

---

## 0. What this is, and what it is not

**It is** a *Carl-local orchestration harness* for running optimization passes against
Inbound's live accounts, fast, in parallel, end-to-end. It is the thing that proves the
loop works on real Danish accounts before any of it is offered to the ads team.

**It is not** a Cowork product. The Workflow tool is a Claude Code construct; it does not
install into the Cowork plugin marketplace. The *skills* the loop reuses (`search-terms`,
`annonce-optimering`, `responsive-search-ads`) remain installable Cowork plugin skills and
ship independently. A local orchestrator does not make the skills local.

**Decisions locked (2026-06-05):**
- Runtime: **Claude Code Workflow** (local, parallel fan-out).
- Scope this build: **orchestrator + two new pieces** (QS-diagnostic + measure-phase).
  SEMrush stays a *gated optional enrichment*, never a dependency.
- Apply model: **editable Excel workbook → expert edits → converter skill → Editor CSV →
  human imports.** Recommend-only. No API writes. The loop returns ONE `.xlsx` (so the expert
  can edit it and send it to the client); a separate converter skill (in `google-ads-general`)
  turns the confirmed workbook into Editor CSVs; the human imports those in Editor, reviews the
  green/yellow diff, and hits Post. The workbook-edit + the Post are the human gates. This is the
  ceiling, not a temporary step. (Updated 2026-06-05 from "loop emits CSVs directly" — the expert
  needs to edit + share before import.)
- Reuse mechanism: **one source of truth, no black-box invocation, no duplication.** The
  Workflow reaches the skills' *actual* builder code (`build()` in each `build-sheet.py` /
  `fill-sheet.py`) by loading it **directly by file path** (`importlib`). It does not copy the
  code and it does not refactor the skills. The skills stay self-contained so they keep
  installing into Cowork unchanged; the Workflow is repo-local and never ships, so it can point
  straight at the skill files. New logic the skills don't have (the two new GAQL pulls, the
  review-workbook builder) lives in `lib/`. A Workflow `agent()` cannot invoke a plugin skill, hence
  by-path load of the deterministic builders + agent-driven classification on top.

  > **Why not refactor the skills into shims that import a shared lib?** Because Cowork plugins
  > install as self-contained single-root directories, and the three skills span **two** plugin
  > roots (`search-terms` + `annonce-optimering` in `google-ads-optimization`;
  > `responsive-search-ads` in `google-ads-setup`). There is no location all three *shipped*
  > skills could import from at Cowork runtime, so a shim refactor would break them on install.
  > The by-path loader delivers the same single-source guarantee without that breakage.

---

## 1. Why the architecture is shaped this way (read once — it is the load-bearing part)

### 1.1 The black-box constraint that forced the library extraction

The first instinct was: the orchestrator calls `search-terms`, `annonce-optimering`, and
`responsive-search-ads` as black boxes and chains their outputs. **This does not work.**
Skills are invoked via the `Skill` tool in the *main loop*. A Workflow `agent()` spawns a
subagent whose tool set does not include skill invocation. There is no precedent anywhere in
the repo of an agent invoking a skill; the pattern is always the reverse (skills spawn
agents).

So "chain the existing skills" had to become **"chain the existing *logic*."** The reusable
core of each skill is extracted into `workflows/optimization-loop/lib/`, the skills are
refactored to import from there, and the Workflow imports the same modules. Composition
without invocation. This is the only way to honour "compose, don't rebuild" given the
constraint, and it sidesteps the cross-plugin `${CLAUDE_PLUGIN_ROOT}` path problem entirely:
nothing imports across plugin roots, because the shared logic lives in one neutral place and
data crosses stage boundaries as JSON.

### 1.2 Two halves: deterministic builders vs. LLM classification

Looking at the actual scripts, each skill splits cleanly into two parts:

- **Deterministic, already parameterized by JSON** — the `build-sheet.py` /
  `fill-sheet.py` / `sheet_layout.py` builders. They take a documented JSON schema and emit
  a coloured `.xlsx`. These extract verbatim into `lib/builders/`. The orchestrator produces
  the same JSON and calls the same builder.
- **LLM-driven, currently living in skill prose** — the classification itself (which term
  is IRRELEVANT vs VINDER; which angle is missing; how to write a headline). This is *not*
  in the scripts. In the loop it becomes the work of a Workflow `agent()`, prompted with the
  **shared taxonomy / rules reference** (`lib/refs/`). The agent classifies; the builder
  builds. Keeping these separate is what lets the deterministic guarantees (length limits,
  colour scales, significance floors) stay enforced in code while the judgement stays in the
  model.

### 1.3 The significance discipline is inherited, not reinvented

Every stage that touches conversions inherits the rule the `annonce-optimering` live test
(2026-05-29) bought: **on Inbound's low-volume Danish accounts, do not claim statistical
confidence the data cannot support.** Concretely:
- `WINNER_MIN_CONV = 2` and a low-confidence flag when `account_conversions < 10` (from
  `search-terms`).
- No per-asset CVR judgement (confounded + sub-significance) — structural/coverage signals
  only (from `annonce-optimering`).
- The measure-phase (§4 Phase 0) must run on a cadence (monthly for most accounts) where the
  before/after delta is signal, not noise.

This is the spine of the whole loop. Any stage that outputs a confidence-laden claim must
gate it behind these thresholds.

---

## 2. Repo layout

```
workflows/optimization-loop/
  SPEC.md                      # this file
  loop.workflow.js             # the runnable Workflow script (meta.name = "optimization-loop")
  lib/
    gaql/
      search_terms.py          # the search_term_view + keyword_view + ad_group_ad pulls
      asset_view.py            # the ad_group_ad_asset_view + RSA-count pulls
      quality_score.py         # NEW: QS component pulls (three-level labels + spend-by-QS)
      change_events.py         # NEW(ish): change_event pull — reuses ads-changelog's query
    classify/
      taxonomy.md              # shared classification taxonomy (5 search-term buckets + angle types)
    refs/
      headline_craft.md        # symlink/copy of responsive-search-ads/references/headline-craft.md
    builders/
      search_terms_sheet.py    # extracted from search-terms/build-sheet.py
      asset_hygiene_sheet.py   # extracted from annonce-optimering/build-sheet.py
      review_workbook.py       # NEW: the ONE editable Excel deliverable (Editor-header columns +
                               #        review metadata + #Original for edits). Converter -> CSV later.
    schemas/
      *.json                   # the JSON contracts in §3, as human DOCS only (see execution model)
  fixtures/
    dsc-baseline.json          # a real captured run for resume + regression
  README.md                    # how to run it locally
```

### Execution model (read this before reading any phase) — the Workflow JS is sandboxed

`loop.workflow.js` runs in a **sandbox: no filesystem, no Python, no `require()`/Node APIs.**
It can ONLY: spawn `agent()`s, pass JSON between them, and use plain JS built-ins. Therefore:

- **Nothing in `lib/` is called by the JS.** Every Python invocation (`load.py`,
  `review_workbook.py`, the GAQL strings) runs **inside an `agent()`** via Bash. The agent receives
  findings JSON in its prompt, runs the script, and returns schema-validated JSON.
- **Schemas are inline JS literals** in `loop.workflow.js`, passed as `agent(prompt, {schema})`.
  The `lib/schemas/*.json` files are documentation of the §3 contracts, not loaded at runtime.
- **All file I/O is done by an agent**, not the JS: reading the prior run dir (cold-start
  source 1), writing the review workbook, writing this run's recommendations.
- **`Date.now()` / `new Date()` are unavailable.** Today's date, the analysis window,
  `customer_id`, and the absolute run-dir path are passed in via the Workflow `args` parameter.

**The existing skills are NOT modified.** `lib/builders/load.py` is not a copy of their code —
it is a thin **by-path loader** that loads each skill's own `build()` from its real file via
`importlib.util.spec_from_file_location`, run **by the execute agent** (not the JS). One source
of truth (the skill file itself), zero duplication. The skills stay self-contained and keep
installing into Cowork unchanged; their smoke tests stay green by construction.

Wrinkle handled by the loader: the RSA builder (`fill-sheet.py`) imports a sibling module
(`sheet_layout.py`), so the loader prepends that skill's directory to `sys.path` before loading
it. `search-terms/build-sheet.py` and `annonce-optimering/build-sheet.py` are self-contained.

---

## 3. The inter-stage data contracts (where the spec earns its keep)

Skills today emit human artifacts (xlsx, a chat-printed gap-brief). A loop needs **machine
hand-offs**. Every stage emits validated JSON (the Workflow `agent()` `schema` option forces
this). These are the contracts.

### 3.1 `SearchTermFindings` (Skill 1 output)
```jsonc
{
  "account_id": "string",
  "window": { "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" },
  "low_confidence": false,                 // true when account_conversions < 10
  "negatives": [                           // -> review_workbook Negative keywords tab
    { "keyword": "string", "match_type": "EXACT|PHRASE",
      "level": "ad_group|campaign|account", "campaign": "string", "ad_group": "string|null",
      "wasted_spend_dkk": 0, "reason": "string" }
  ],
  "winners": [                             // -> review_workbook Nye keywords tab
    { "term": "string", "campaign": "string", "ad_group": "string",
      "conversions": 0, "cpa_dkk": 0, "already_exact": false, "reason": "string" }
  ],
  "placement_problems": [                  // surfaced in summary, NOT auto-applied (needs human routing)
    { "term": "string", "reason": "struktur|intent", "detail": "string" }
  ]
}
```

### 3.2 `AssetHygieneFindings` (Skill 2 output — annonce-optimering logic)
```jsonc
{
  "account_id": "string",
  "ad_groups": [
    { "campaign": "string", "ad_group": "string", "rsa_count": 1,
      "challenger_flag": true,             // rsa_count < 2
      "missing_angles": ["urgency", "CTA"] }  // angle taxonomy from refs
  ],
  "dead_weight": [                         // recommend-to-cut, surfaced in summary
    { "campaign": "string", "ad_group": "string", "field_type": "HEADLINE|DESCRIPTION",
      "text": "string", "impressions": 0 }
  ],
  "gap_brief": [                           // -> feeds Skill 6 (RSA) directly
    { "campaign": "string", "ad_group": "string",
      "missing_angles": ["string"], "suggestion": "string" }
  ]
}
```

### 3.3 `QualityScoreFindings` (Skill 3 — NEW)

**Grain: KEYWORD, not ad group (live-verified 2026-06-05).** Quality Score exists at keyword
grain in Google Ads; there is no native ad-group QS. `get_quality_score_audit` returns
account distribution + the 20 worst *keywords* with their three component labels. Reporting
a fabricated "ad-group QS" would be the exact grain error the critique flagged (per-asset vs
search-term). So we report flagged keywords with the ad group they sit in.

```jsonc
{
  "account_id": "string",
  "average_quality_score": 6.4,
  "spend_by_qs": [ { "qs": 1, "keyword_count": 11 } ],   // QS 1-10 -> keyword count, for the chart
  "flagged_keywords": [                                   // KEYWORD grain (verified shape)
    { "campaign": "string", "ad_group": "string", "keyword": "string", "match_type": "EXACT|PHRASE",
      "quality_score": 1,                                 // overall keyword QS, 1-10
      "creative_quality":     "BELOW_AVERAGE|AVERAGE|ABOVE_AVERAGE",
      "landing_page_quality": "BELOW_AVERAGE|AVERAGE|ABOVE_AVERAGE",
      "expected_ctr":         "BELOW_AVERAGE|AVERAGE|ABOVE_AVERAGE",
      "impressions": 0, "cost": 0,
      "lp_below_average": true }                          // convenience flag: LP is the actionable lever
  ]
}
```
**Hard limits baked into the contract (verified):**
- The three components are *categorical labels only* (`BELOW_AVERAGE|AVERAGE|ABOVE_AVERAGE`).
  The API does not expose a finer score. `landing_page_quality` is reported as a label + the
  keyword's context, never as a numeric "LP score". Promising more is the over-confidence the
  critique flagged.
- The overall `quality_score` 1-10 IS available (used for `spend_by_qs`). Having that number
  does **not** loosen the LP-experience caveat: 1-10 is the overall keyword score; the LP
  component stays a categorical flag.
- `LAST_90_DAYS` is **not** a valid date literal for this tool (verified: raised
  `INVALID_VALUE_WITH_DURING_OPERATOR`). Use `LAST_30_DAYS` or a concrete BETWEEN window.

### 3.4 `ChangeDeltas` (Skill 0 / measure-phase — NEW, see §4)

**Three distinct sources, not one** (the decomposition that resolves cold-start AND the
29-day limit at once):
1. **What we proposed last run** — the loop persists its own recommendations to the run dir
   at Phase 3. Run 1 writes it, run 2 reads it. This is the real cold-start fix; the loop
   never depends on change history to reconstruct its own actions.
2. **What was actually applied** — `get_change_history` (≤29 days, verified; bulk-collapsed).
   Confirms the human posted it + catches out-of-loop changes. Goes blind past day 29 → the
   loop's cadence must be ≤29 days (see §4).
3. **Did it move the metric** — a two-window metrics pull (before vs after the change date).
   NOT bound by the 29-day limit (campaign/ad_group metrics have long history), so it is a
   *separate* pull, gated by the same significance floor as the rest of the loop.

```jsonc
{
  "account_id": "string",
  "is_baseline_run": false,                // true on run 1 — sources 2/3 skipped, baseline captured
  "prior_run_date": "YYYY-MM-DD|null",
  "proposed_last_run": [                    // source 1: read from the prior run dir
    { "type": "negative|winner|rsa|qs_flag", "campaign": "string", "ad_group": "string|null",
      "detail": "string" }
  ],
  "applied_since_last": [                   // source 2: collapsed get_change_history
    { "date": "YYYY-MM-DD", "user_email": "string", "resource_type": "string",
      "operation": "CREATE|UPDATE|REMOVE", "count": 0, "campaigns": ["string"],
      "ad_groups": ["string"], "matched_a_proposal": false }   // did we propose this? (loop-attribution)
  ],
  "affected_metric_deltas": [               // source 3: two-window pull on touched entities
    { "campaign": "string", "ad_group": "string|null",
      "metric": "cpa|cvr|ctr", "before": 0, "after": 0, "delta_pct": 0,
      "significant": false }                // false when conv volume too low — report directionally only
  ]
}
```

### 3.5 `WorkbookBundle` (final execution output) — Excel only, NOT CSV

**Decision (2026-06-05): the loop returns ONE editable Excel workbook, not CSVs.** The ads
expert edits the workbook, can send it to the client, then runs a **separate converter skill**
(in `google-ads-general`) that does workbook → Editor CSV. This mirrors the assembler, already
made Excel-only (commit `eb4ebd9`: "the workbook is a lossless superset; the converter produces
the CSVs"). Google Ads Editor imports CSV, not `.xlsx` (Editor answer 30564) — which is exactly
why the converter exists. The loop never emits CSVs and never writes to the account.

```jsonc
{
  "workbook_path": "string",               // the one .xlsx deliverable
  "tabs": ["string"],                       // which entity tabs got rows
  "counts": { "negatives": 0, "winners": 0, "rsa_new": 0, "rsa_edits": 0 },
  "executive_summary_md": "string",         // Danish human-facing brief (see §5)
  "wrote_run_recommendations": true         // recommendations.json persisted for next run's measure
}
```

### 3.5b The workbook column contract (the interface the converter is built against)

`lib/builders/review_workbook.py` builds the workbook. Tabs: **Laes mig** (instructions),
**Negative keywords**, **Nye keywords (vindere)**, **RSA challengers**. Each entity tab splits
its columns into two bands:

- **EDITOR-BOUND columns** — exact Google Ads Editor header spelling (Editor answer 57747:
  headers are English, case/space-insensitive). Dark-blue header. **The converter KEEPS these.**
- **METADATA columns** — review context (Niveau, Spildt budget, Begrundelse, Konverteringer, CPA,
  AEndringstype). Light-blue header. **The converter DROPS these.** Never go to Editor.

Editor-bound header sets (the converter's KEEP list, exact spelling):
- **Negative keywords:** `Campaign`, `Ad group`, `Keyword`, `Match type` (Match type carries the
  Negative / Campaign negative distinction; account-level → blank Campaign + Ad group).
- **Nye keywords (vindere):** `Campaign`, `Ad group`, `Keyword`, `Match type` (always `Exact`),
  `Status` (`Paused`).
- **RSA challengers:** `Campaign`, `Ad group`, `Ad type`, `Final URL`, `Path 1`, `Path 2`,
  `Headline 1`…`Headline 15`, `Description 1`…`Description 4`, `Status`.

**`#Original` — editing EXISTING entities (the loop's distinguishing need vs the assembler):**
The assembler builds NEW campaigns (all net-new, Paused, no `#Original`). The loop optimises a
LIVE account, so some rows EDIT an existing entity. Editor's `<Column>#Original` convention
(answer 57747) matches an edit to the existing entity and preserves its history instead of
creating a duplicate. So a `Headline 1#Original` / `Final URL#Original` column carrying the
current live value appears **only on edit rows**; net-new rows have none. **The converter MUST
preserve any `*#Original` column verbatim** — it is the difference between "edit in place" and
"create a duplicate". Verified: `#Original` columns appear iff an edit row is present, blank on
net-new rows.

---

## 4. The loop phases (the Workflow shape)

**Shape:** `parallel([measure, search_terms, asset_hygiene, qs])` → barrier → one
`execute` agent → return `{csv paths, summary}`. The measure phase and the three
diagnostics are mutually independent (none consumes another's output — only the final
summary needs them together), so they run as **one parallel fan-out**, not sequential
phases. The barrier after diagnose is genuinely justified: the bundle + executive summary
are an all-results-needed synthesis. Execute is **one** agent (the builders are fast
deterministic local Python; three agents would be needless), already gated by the barrier.

Each agent runs the relevant `lib/` code via Bash and returns schema-validated JSON (see
the execution-model note in §2 — the JS itself runs no Python).

### Stage A (parallel) — Measure (what happened since last run) — NEW
Three sources (see §3.4), each its own pull:
- **Source 1 — what we proposed:** read the prior run dir's persisted recommendations. Pure
  local file read.
- **Source 2 — what was applied:** `get_change_history(lookback_days ≤ 29)`, then
  `change_events.collapse()`. Mark each collapsed action `matched_a_proposal` if it lines up
  with source 1 (this is how the loop attributes movement to its own advice vs. out-of-loop
  edits).
- **Source 3 — did it move:** a two-window metrics pull (before vs after the change date) on
  the touched campaigns/ad groups. Separate pull, **not** bound by 29 days. Every delta gated
  by the significance floor; report directionally ("CPA down 18%, not yet significant"), never
  as a causal win.
- **Cold start:** on run 1 there is no prior. Phase 0 runs as *pure baseline capture* — record
  current metrics, emit `is_baseline_run: true`, skip sources 2 and 3. Without this the loop
  breaks on first run.
- **Cadence consequence (hard):** source 2 goes blind past day 29 (verified ceiling). The loop
  must run on a **≤29-day cadence** (every 3-4 weeks), not "monthly" (30/31 days is already
  over). If a run is later than 29 days, the change-confirmation half degrades — say so in the
  summary, do not silently under-report.
- Emits `ChangeDeltas`. Feeds the executive summary.

### Stage A (parallel) — the three diagnostics (run alongside Measure)
All four agents in Stage A run concurrently in one `parallel()`:
- **Search-term agent** → `SearchTermFindings` (runs `lib/gaql/search_terms.py` queries via the
  Ads MCP; classification using `lib/classify/taxonomy.md`).
- **Asset-hygiene agent** → `AssetHygieneFindings` (`lib/gaql/asset_view.py`; structural only).
- **QS agent** → `QualityScoreFindings` (calls `get_quality_score_audit`, normalises via
  `lib/gaql/quality_score.py`, scrapes flagged keywords' LPs via Firecrawl).
- **(Gated) SEMrush agent** — only spawned if a SEMrush plan with MCP access is detected.
  Mirrors `semrush-research`: detect the plan-gate, degrade to nothing, never block. Enriches
  negatives (competitor waste) + expansion (competitor gaps); never required.

### Barrier → Stage B — Execute (one agent, builds the workbook + summary)
A single execute agent receives all Stage-A findings JSON, assembles the
`review_workbook.build()` input, and builds **one editable `.xlsx`** (tabs: Laes mig, Negative
keywords, Nye keywords (vindere), RSA challengers):
- **Negatives** from `SearchTermFindings.negatives` (+ optional SEMrush waste) → Negative
  keywords tab (Editor columns + Niveau/Spildt budget/Begrundelse metadata; account-level →
  blank Campaign).
- **Winners** from `SearchTermFindings.winners` (already_exact skipped) → Nye keywords tab,
  promoted to `Exact`, `Paused`. Conservative: never "aggressively scale" on 2-3 conversions.
- **RSA challengers** for each ad group with `challenger_flag` or `missing_angles` → RSA tab,
  grounded in `assetHygiene.gap_brief` + `headline-craft.md` (variation + tiebreakers, hard
  Editor length limits respected). New challengers `Paused`. A *rewrite* of an existing ad uses
  `#Original` columns (§3.5b) so Editor edits in place; never a `Removed` row (§6).
- Writes this run's recommendations to the run dir (cold-start source 1 for next run).
- Returns `WorkbookBundle` (the `.xlsx` path + counts + the executive summary).

### Return — the human gates are outside the Workflow
The Workflow returns `WorkbookBundle`. The **main agent outside the Workflow** presents the
workbook + summary. The expert **edits the workbook** (and may send it to the client), runs the
converter skill (workbook → Editor CSV), imports the CSVs in Editor, reviews the green/yellow
diff, and hits Post. Those are the HITL gates (§6). The Workflow performs no Drive write and no
API push.

---

## 5. The executive summary (Phase 3 output)

A short markdown brief the human reads before importing. Structure:
- **Since last run** (from Phase 0): what was posted, what moved, what didn't — each with a
  significance honest-flag.
- **This run found**: N negatives (X DKK wasted), M winners to promote, K ad groups needing a
  challenger, the QS-flagged ad groups.
- **What's in each CSV** + the exact Editor steps (Account > Import > From file > review
  green/yellow > Post).
- **Honest caveats**: low-confidence flag if `account_conversions < 10`; SEMrush absent if
  gated; QS LP-experience is a flag + page, not a score.
- **`## Kilder`** — every data source actually read (MCP tools, Firecrawl URLs).

Danish by default (matches every Inbound skill).

---

## 6. HITL × Workflow (the part that needs an explicit rule)

Per-skill Drive write-gates **cannot fire interactively mid-Workflow** — there is no
conversational turn inside a running script to ask "confirm to write". Resolution, matching the
locked "workbook → expert edits → converter → Editor" decision:

1. **Every stage runs local-only.** No Drive writes, no Sheets, no gates. All intermediate
   artifacts (`SearchTermFindings`, etc.) and the final workbook are written to a local run
   directory. Nothing leaves the machine during the run.
2. **Two human gates, both outside the Workflow.** (a) The expert **edits the returned workbook**
   — deletes rows they disagree with, adjusts text/bids, decides which challengers ship — then
   runs the converter skill. (b) After import, the expert reviews Editor's green/yellow diff and
   **hits Post**. The Post is the final approval, on Google's own diff surface. The workbook-edit
   step is a real, deliberate gate the expert controls — it is the reason the loop returns Excel,
   not CSV.
3. **No API writes, ever.** The loop never calls a Google Ads mutate. The repo `CLAUDE.md`
   human-in-the-loop rule holds unchanged.
4. **The `Removed+Enabled` trap.** Never set an old ad to `Removed` + a new one to `Enabled` in
   one import (resets the new ad's learning, drops the old ad's data). The loop emits new
   challengers as `Paused`; for a *rewrite* of an existing ad it uses the `#Original` convention
   (§3.5b) so Editor edits in place, never duplicating. The human decides pause-vs-remove.

### v2 (not built this session): gated negative-keyword apply
Negative keywords are the one maximally-reversible change. A future version may offer a single
explicit "apply these N negatives?" gate that writes them via the API behind one confirmation.
Flagged here so the contract anticipates it; **not in scope now.** Everything else stays
workbook-and-converter only.

---

## 7. Build order (this session)

1. **Scaffold** `workflows/optimization-loop/` + this SPEC. ✅
2. **Write `lib/builders/load.py`** — the by-path loader that imports each skill's `build()`
   from its real file (handling the RSA `sys.path` wrinkle). The skills are NOT modified. Prove
   it by loading + calling each `build()` from the loader and diffing the output against the
   baseline smoke-test artifacts (must be byte-identical — this is the "one source of truth"
   proof).
3. **Write `lib/gaql/`** — lift the verified GAQL from the skill SKILL.md files (all field
   shapes already live-verified; do not re-invent).
4. **Build the two new GAQL pulls** — `quality_score.py` (three-level labels + spend-by-QS,
   reuse ads-audit's QS query) and `change_events.py` (reuse ads-changelog's pull + collapse).
5. **Write `review_workbook.py`** — the ONE editable `.xlsx`: Editor-header columns (the
   converter's keep-list) + review metadata (drop-list) + `#Original` for edit rows.
6. **Write `loop.workflow.js`** — `meta` block (pure literal), one `parallel()` fan-out of 4
   (measure baseline-aware + 3 diagnostics) → barrier → one execute agent → return the bundle.
   Each `agent()` gets an **inline JS-literal `schema`** (the JS cannot load `lib/schemas/`;
   those `.json` are docs). Date/window/`customer_id`/run-dir come in via `args`. **De-risk
   first:** before all phases, write a one-agent version that runs the search-terms GAQL
   against DSC and returns `SearchTermFindings`; confirm the JSON validates. If the default
   workflow subagent lacks Bash, set `agentType: 'general-purpose'`. That one run proves the
   pattern; then iterate with `resumeFromRunId` so cached `agent()` calls don't re-run.
7. **Capture a baseline fixture** against one real account (DSC `3069826320` is the
   live-verified one) for resume + regression.
8. **Dry-run** end-to-end against that account, local-only, no writes. Inspect the workbook
   (tabs, Editor-header columns, metadata band, `#Original` on any edit rows) + the exec summary.

### Verification gates (honest)
- After step 2: each existing skill's smoke test passes unchanged. If any drifts, the
  extraction broke a contract — fix before proceeding.
- After step 6: a `--baseline` run produces `is_baseline_run: true` and no delta crash.
- After step 8: the workbook opens cleanly, the Editor-bound columns carry exact Editor header
  spelling, `#Original` appears only on edit rows, and the converter (when built) can map the
  keep-band → Editor CSV. **End-to-end against a real account is the gate that matters — the
  per-stage logic is verified, the full chain is the parked unknown until this passes.**

---

## 8. What this loop deliberately does NOT do

- **No SEMrush dependency.** Gated enrichment only; absence never blocks (verified gated
  2026-06-05).
- **No CVR judgement on thin data.** Significance floors inherited from the existing skills.
- **No hardcoded copywriting magic numbers as laws.** The Optmyzr-derived numbers in
  `headline_craft.md` are applied as the existing skill applies them (variation + tiebreakers),
  not as `<20-char` hard ceilings. The one validated rule (ignore Ad Strength) is kept.
- **No API writes.** Editable Excel workbook → expert edits → converter skill → Editor CSV →
  human imports is the ceiling.
- **No Cowork install.** This is a local dev harness; the skills ship to Cowork separately.

---

## 9. Cross-references
- Critique that produced this design: `work/inbound-cph/operations/decks/2026-06-05-optimization-loop-critique.html` (vault).
- Existing skills reused: `plugins/google-ads-optimization/skills/{search-terms,annonce-optimering}`,
  `plugins/google-ads-setup/skills/responsive-search-ads`.
- Measure-phase logic source: `plugins/google-ads-general/skills/ads-changelog`.
- QS pull source: `plugins/google-ads-general/skills/ads-audit-report`.
- Operating contract (HITL, Kilder, language): the shared plugin `CLAUDE.md`.
