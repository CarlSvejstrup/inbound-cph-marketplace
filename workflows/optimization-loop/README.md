# optimization-loop

A **local Claude Code Workflow** that diagnoses a live Google Ads account across parallel
dimensions, then chains the findings into Google Ads Editor import CSVs for human review.

This is a Carl-local dev/ops harness, **not** a Cowork product. It reuses the shipped skills'
logic (`search-terms`, `annonce-optimering`, `responsive-search-ads`) as a single source of
truth without modifying them; the skills ship to Cowork independently. Full design rationale:
[`SPEC.md`](./SPEC.md).

## What it does

`parallel([measure, search-terms, asset-hygiene, quality-score])` → barrier → one `execute`
agent → returns a CSV bundle + a Danish executive summary.

- **Measure** (Phase 0): what we proposed last run (from the prior run dir) + what was applied
  (`get_change_history`, ≤29 days, bulk-collapsed) + did it move (before/after metric deltas,
  significance-gated). Baseline-aware: the first run just captures a baseline.
- **Search terms**: classifies every term (RELEVANT / VINDER / PLACEMENT_PROBLEM / IRRELEVANT /
  GRAENSE), grounded in the scraped offering, with significance discipline.
- **Asset hygiene**: champion-challenger coverage, dead-weight assets, angle-gap brief.
  Structural only, never a per-asset CVR judgement.
- **Quality score**: keyword-grain (no fabricated ad-group QS); LP is a flag, not a score.
- **Execute**: builds **ONE editable Excel workbook** (`Optimering - <client> - <date>.xlsx`)
  with tabs for negatives, winner-keywords, and RSA challengers. Each tab has Editor-header
  columns (the converter keeps) + review-metadata columns (the converter drops). Every RSA is a
  NET-NEW challenger (never an in-place edit — editing resets learning); account-level negatives
  fan out to one campaign-level row per active campaign. Writes `recommendations.json` for the
  next run's measure. The converter (`editor-csv-export`) reads this workbook AND the campaign
  -build assembler's — one shared per-entity CSV target.

**Recommend-only, Excel-first.** No Google Ads API writes, no Drive writes. The expert **edits
the workbook** (and can send it to the client), then runs a separate converter skill (in
`google-ads-general`) that turns the confirmed workbook into Editor CSVs, then imports those in
Editor, reviews the green/yellow diff, and hits Post. Editor imports CSV not `.xlsx` (answer
30564) — which is why the converter exists. The workbook-edit + the Post are the human gates.

## Run it

```js
Workflow({
  scriptPath: "<repo>/workflows/optimization-loop/loop.workflow.js",
  args: {
    customer_id: "3069826320",            // the Google Ads account
    client_name: "Dansk Studie Center",
    today: "2026-06-05",                  // sandbox has no Date.now(); pass it
    window_start: "2026-03-07",
    window_end: "2026-06-05",
    repo_root: "<repo>",
    run_dir: "<repo>/workflows/optimization-loop/runs/2026-06-05-3069826320",
    prior_run_dir: null,                  // null = first run -> baseline; else the last run dir
    landing_page_url: "https://danskstudiecenter.dk/"
  }
})
```

Cadence: **≤29 days** (the change-history window ceiling). Point `prior_run_dir` at the last
run's dir so the measure stage can compare. Iterate on the script with `resumeFromRunId` so
cached `agent()` calls don't re-run.

## Smoke test

`smoke.workflow.js` is a one-agent probe of the search-term stage. It is how the
agent→Bash/MCP→schema-JSON pattern was first verified against live DSC. Run it to re-validate
the pattern after any change to `lib/gaql/search_terms.py` or the classification taxonomy. The
last passing result is `fixtures/dsc-smoke-search-terms.json`.

## Layout

```
loop.workflow.js     # the full orchestrator (the thing you run)
smoke.workflow.js    # one-agent search-term probe (pattern verification)
SPEC.md              # design contract + the execution model + all the locked decisions
lib/
  gaql/              # live-verified GAQL + the two new pulls (QS, change_events)
  classify/          # shared 5-bucket + angle taxonomy + significance rules
  builders/          # by-path loader of the skills' build() + the new Editor CSV builder
  schemas/           # the §3 JSON contracts as docs (NOT loaded at runtime)
fixtures/            # last passing smoke result, for regression
runs/                # per-run output dirs (CSVs + recommendations.json) — gitignored
```

## The execution model (important)

The Workflow JS is **sandboxed**: no filesystem, no Python, no `require()`. It only spawns
agents and passes JSON. So all `lib/` code runs **inside agents** (each agent runs the Python
via Bash and returns schema-validated JSON), schemas are inline JS literals, file I/O is done by
agents, and time/account values come in via `args`. See `SPEC.md` §2.
