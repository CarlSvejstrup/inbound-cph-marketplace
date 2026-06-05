export const meta = {
  name: 'optimization-loop',
  description: 'Diagnose a live Google Ads account across parallel dimensions (measure-since-last-run, search terms, asset hygiene, quality score), then chain the findings into Google Ads Editor import CSVs (negatives, keyword expansion, RSA challengers) plus an executive summary for human review. Read-only against Ads, local CSV writes only, recommend-only: the human imports each CSV in Editor and hits Post. SEMrush enrichment is gated and never required.',
  phases: [
    { title: 'Diagnose', detail: 'parallel: measure + search-terms + asset-hygiene + quality-score' },
    { title: 'Execute', detail: 'one agent builds the Editor CSVs + executive summary' },
  ],
}

// ---------------------------------------------------------------------------
// args (Date.now() is unavailable in the sandbox - everything time/account
// related comes in here):
//   { customer_id, client_name, today, window_start, window_end,
//     run_dir, prior_run_dir, repo_root, landing_page_url }
// ---------------------------------------------------------------------------
const a = args || {}
const customerId = a.customer_id || '3069826320'
const clientName = a.client_name || 'Dansk Studie Center'
const today = a.today || '2026-06-05'
const start = a.window_start || '2026-03-07'
const end = a.window_end || '2026-06-05'
const repoRoot = a.repo_root || '/Users/carlschmidt-svejstrup/code/personal/inbound-cph-demo'
const runDir = a.run_dir || `${repoRoot}/workflows/optimization-loop/runs/${today}-${customerId}`
const priorRunDir = a.prior_run_dir || null            // null on the first ever run -> baseline
const landingPageUrl = a.landing_page_url || ''        // grounds IRRELEVANT calls + QS LP check
const libDir = `${repoRoot}/workflows/optimization-loop/lib`

// ---------------------------------------------------------------------------
// Inline JS-literal schemas (the sandboxed JS cannot load lib/schemas/*.json).
// Mirror SPEC section 3.
// ---------------------------------------------------------------------------
const SEARCH_TERM_FINDINGS = {
  type: 'object',
  required: ['account_id', 'window', 'low_confidence', 'negatives', 'winners', 'placement_problems'],
  properties: {
    account_id: { type: 'string' },
    window: { type: 'object', required: ['start', 'end'], properties: { start: { type: 'string' }, end: { type: 'string' } } },
    low_confidence: { type: 'boolean' },
    account_conversions: { type: 'number' },
    negatives: {
      type: 'array',
      items: {
        type: 'object',
        required: ['keyword', 'match_type', 'level', 'reason'],
        properties: {
          keyword: { type: 'string' },
          match_type: { type: 'string', enum: ['EXACT', 'PHRASE'] },
          level: { type: 'string', enum: ['ad_group', 'campaign', 'account'] },
          campaign: { type: ['string', 'null'] },
          ad_group: { type: ['string', 'null'] },
          wasted_spend_dkk: { type: 'number' },
          reason: { type: 'string' },
        },
      },
    },
    winners: {
      type: 'array',
      items: {
        type: 'object',
        required: ['term', 'campaign', 'ad_group', 'already_exact', 'reason'],
        properties: {
          term: { type: 'string' },
          campaign: { type: 'string' },
          ad_group: { type: 'string' },
          conversions: { type: 'number' },
          cpa_dkk: { type: ['number', 'null'] },
          already_exact: { type: 'boolean' },
          reason: { type: 'string' },
        },
      },
    },
    placement_problems: {
      type: 'array',
      items: {
        type: 'object',
        required: ['term', 'reason', 'detail'],
        properties: {
          term: { type: 'string' },
          reason: { type: 'string', enum: ['struktur', 'intent'] },
          detail: { type: 'string' },
        },
      },
    },
  },
}

const ASSET_HYGIENE_FINDINGS = {
  type: 'object',
  required: ['account_id', 'ad_groups', 'dead_weight', 'gap_brief'],
  properties: {
    account_id: { type: 'string' },
    ad_groups: {
      type: 'array',
      items: {
        type: 'object',
        required: ['campaign', 'ad_group', 'rsa_count', 'challenger_flag', 'missing_angles'],
        properties: {
          campaign: { type: 'string' },
          ad_group: { type: 'string' },
          rsa_count: { type: 'number' },
          challenger_flag: { type: 'boolean' },
          missing_angles: { type: 'array', items: { type: 'string' } },
        },
      },
    },
    dead_weight: {
      type: 'array',
      items: {
        type: 'object',
        required: ['campaign', 'ad_group', 'field_type', 'text', 'impressions'],
        properties: {
          campaign: { type: 'string' },
          ad_group: { type: 'string' },
          field_type: { type: 'string', enum: ['HEADLINE', 'DESCRIPTION'] },
          text: { type: 'string' },
          impressions: { type: 'number' },
        },
      },
    },
    gap_brief: {
      type: 'array',
      items: {
        type: 'object',
        required: ['campaign', 'ad_group', 'missing_angles', 'suggestion'],
        properties: {
          campaign: { type: 'string' },
          ad_group: { type: 'string' },
          missing_angles: { type: 'array', items: { type: 'string' } },
          suggestion: { type: 'string' },
        },
      },
    },
  },
}

const QS_FINDINGS = {
  type: 'object',
  required: ['account_id', 'average_quality_score', 'spend_by_qs', 'flagged_keywords'],
  properties: {
    account_id: { type: 'string' },
    average_quality_score: { type: ['number', 'null'] },
    spend_by_qs: {
      type: 'array',
      items: { type: 'object', required: ['qs', 'keyword_count'], properties: { qs: { type: 'number' }, keyword_count: { type: 'number' } } },
    },
    flagged_keywords: {
      type: 'array',
      items: {
        type: 'object',
        required: ['campaign', 'ad_group', 'keyword', 'quality_score', 'landing_page_quality', 'lp_below_average'],
        properties: {
          campaign: { type: 'string' },
          ad_group: { type: 'string' },
          keyword: { type: 'string' },
          match_type: { type: 'string' },
          quality_score: { type: 'number' },
          creative_quality: { type: 'string' },
          landing_page_quality: { type: 'string' },
          expected_ctr: { type: 'string' },
          impressions: { type: 'number' },
          cost: { type: 'number' },
          lp_below_average: { type: 'boolean' },
        },
      },
    },
  },
}

const CHANGE_DELTAS = {
  type: 'object',
  required: ['account_id', 'is_baseline_run', 'proposed_last_run', 'applied_since_last', 'affected_metric_deltas'],
  properties: {
    account_id: { type: 'string' },
    is_baseline_run: { type: 'boolean' },
    prior_run_date: { type: ['string', 'null'] },
    proposed_last_run: { type: 'array', items: { type: 'object' } },
    applied_since_last: { type: 'array', items: { type: 'object' } },
    affected_metric_deltas: {
      type: 'array',
      items: {
        type: 'object',
        required: ['campaign', 'metric', 'before', 'after', 'delta_pct', 'significant'],
        properties: {
          campaign: { type: 'string' },
          ad_group: { type: ['string', 'null'] },
          metric: { type: 'string', enum: ['cpa', 'cvr', 'ctr'] },
          before: { type: 'number' },
          after: { type: 'number' },
          delta_pct: { type: 'number' },
          significant: { type: 'boolean' },
        },
      },
    },
  },
}

const CSV_BUNDLE = {
  type: 'object',
  required: ['negatives_csv_path', 'keyword_expansion_csv_path', 'rsa_csv_path', 'executive_summary_md', 'wrote_run_recommendations'],
  properties: {
    negatives_csv_path: { type: ['string', 'null'] },
    keyword_expansion_csv_path: { type: ['string', 'null'] },
    rsa_csv_path: { type: ['string', 'null'] },
    executive_summary_md: { type: 'string' },
    wrote_run_recommendations: { type: 'boolean' },
  },
}

// Shared operating-rules preamble for every agent.
const RULES = `
Hard rules (Inbound operating contract):
- READ-ONLY against Google Ads. Never write/pause/mutate the account. Never push the API.
- Paused campaigns are intentional - excluded at the query level, never flagged as negative.
- Significance discipline: on these small Danish accounts, never claim confidence the data
  cannot support. If account conversions < 10 in the window, flag low_confidence and be
  conservative. A "winner" needs >= 2 conversions. Never judge an asset on per-asset CVR.
- Cost is micros -> DKK = cost_micros / 1_000_000.
- Danish for any human-facing copy (the executive summary). Structured field values can be ASCII.
- The lib/ code is the single source of truth. Run it; do not reinvent queries or builders.
`.trim()

// ===========================================================================
phase('Diagnose')

// --- Stage A: measure + 3 diagnostics, all in parallel ---------------------
const [measure, searchTerms, assetHygiene, qs] = await parallel([
  // 1) MEASURE (Phase 0): three sources, baseline-aware.
  () => agent(`
${RULES}

You are the MEASURE stage of the Inbound CPH optimization loop for ${clientName}
(customer_id ${customerId}). Window ${start}..${end}. Today is ${today}.

Prior run dir: ${priorRunDir === null ? 'NONE (this is the first run -> BASELINE)' : priorRunDir}

THREE sources (see ${repoRoot}/workflows/optimization-loop/SPEC.md section 3.4):
1. What we proposed last run: ${priorRunDir === null
    ? 'no prior run -> this is a BASELINE run. Set is_baseline_run=true, proposed_last_run=[].'
    : `read ${priorRunDir}/recommendations.json (the loop's own prior recommendations).`}
2. What was actually applied: call the Google Ads MCP get_change_history(customer_id=${customerId},
   lookback_days=29) (the hard ceiling; 30 errors). Then collapse bulk uploads:
   run \`python3 -c\` importing ${libDir}/gaql/change_events.py and call collapse() on the rows.
   Mark each collapsed action matched_a_proposal if it lines up with source 1.
3. Did it move: for the touched campaigns/ad groups, pull before-vs-after CPA/CVR/CTR with two
   windowed GAQL calls (campaign metrics are NOT limited to 29 days). Gate every delta by
   significance (significant=false when conversion volume is too low). Report directionally.

If this is a baseline run: skip sources 2 and 3, just set is_baseline_run=true and capture the
current state. Return ChangeDeltas.
`, { label: 'measure', phase: 'Diagnose', schema: CHANGE_DELTAS, agentType: 'general-purpose' }),

  // 2) SEARCH-TERMS (identical pattern to the verified smoke test).
  () => agent(`
${RULES}

You are the SEARCH-TERM diagnostic for ${clientName} (customer_id ${customerId}), window
${start}..${end}.${landingPageUrl ? ` Client landing page: ${landingPageUrl} (scrape via Firecrawl to ground IRRELEVANT calls).` : ''}

STEP 1 - read the exact queries (single source of truth, live-verified; do not invent fields):
  cat ${libDir}/gaql/search_terms.py
STEP 2 - run search_terms_query (BETWEEN ${start}..${end}) AND keyword_map_query against the
  account via the Ads MCP run_custom_gaql. Filter test/dup campaigns (/w2m|test|vol 2/i) from the
  keyword map before judging struktur placement.
STEP 3 - classify each term using ${libDir}/classify/taxonomy.md (RELEVANT / VINDER /
  PLACEMENT_PROBLEM[struktur|intent] / IRRELEVANT / GRAENSE), honouring the significance rules.
STEP 4 - return SearchTermFindings: negatives (IRRELEVANT + struktur), winners (converting, not
  yet exact), placement_problems, plus account_id/window/low_confidence/account_conversions.
`, { label: 'search-terms', phase: 'Diagnose', schema: SEARCH_TERM_FINDINGS, agentType: 'general-purpose' }),

  // 3) ASSET-HYGIENE (annonce-optimering logic; structural only).
  () => agent(`
${RULES}

You are the ASSET-HYGIENE diagnostic for ${clientName} (customer_id ${customerId}), window
${start}..${end}. This is STRUCTURAL hygiene, NOT a profit/CVR judgement (per-asset CVR is
confounded + sub-significance - never render or rank on it).

STEP 1 - read the exact queries:
  cat ${libDir}/gaql/asset_view.py
STEP 2 - run asset_view_query (window ${start}..${end}) AND rsa_count_query via the Ads MCP.
  Count distinct RSA ids per (campaign, ad_group).
STEP 3 - per ad group: rsa_count, challenger_flag (rsa_count < 2). Classify each served asset's
  angle (taxonomy in ${libDir}/classify/taxonomy.md: benefit/trust/urgency/CTA/feature/
  keyword-led/brand/location/garanti); missing_angles = angles with no served asset. Dead-weight
  = assets under ~50 impressions (a coverage fact, not a CVR dom).
STEP 4 - return AssetHygieneFindings incl. the gap_brief (per ad group: missing_angles +
  a concrete challenger suggestion).
`, { label: 'asset-hygiene', phase: 'Diagnose', schema: ASSET_HYGIENE_FINDINGS, agentType: 'general-purpose' }),

  // 4) QUALITY SCORE (keyword grain; LP is a flag, not a score).
  () => agent(`
${RULES}

You are the QUALITY-SCORE diagnostic for ${clientName} (customer_id ${customerId}).

STEP 1 - call the Ads MCP get_quality_score_audit(customer_id=${customerId},
  date_range='LAST_30_DAYS'). (LAST_90_DAYS is NOT a valid literal - it errors. For a 90-day view
  pass a concrete "BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'" string instead.)
STEP 2 - normalise: run \`python3 -c\` importing ${libDir}/gaql/quality_score.py and call
  normalise_findings(audit) on the tool's response. QS is KEYWORD grain - never fabricate an
  ad-group QS. The three components are categorical labels; landing_page_quality is a FLAG, never
  a numeric score.${landingPageUrl ? ` Optionally scrape ${landingPageUrl} via Firecrawl to add context for LP-below-average keywords (observation only).` : ''}
STEP 3 - return QualityScoreFindings (average_quality_score, spend_by_qs, flagged_keywords with
  lp_below_average).
`, { label: 'quality-score', phase: 'Diagnose', schema: QS_FINDINGS, agentType: 'general-purpose' }),
])

log(`Diagnose done. baseline=${measure?.is_baseline_run} | ` +
    `${(searchTerms?.negatives || []).length} negatives, ${(searchTerms?.winners || []).length} winners | ` +
    `${(assetHygiene?.ad_groups || []).filter(g => g.challenger_flag).length} ad groups need a challenger | ` +
    `${(qs?.flagged_keywords || []).length} low-QS keywords`)

// --- Barrier -> Stage B: one execute agent builds CSVs + summary -----------
phase('Execute')

const execPayload = JSON.stringify({ measure, searchTerms, assetHygiene, qs })

const bundle = await agent(`
${RULES}

You are the EXECUTE stage of the Inbound CPH optimization loop for ${clientName}
(customer_id ${customerId}), window ${start}..${end}, today ${today}.

You receive all diagnostic findings as JSON below. Build the Editor-import CSVs by running the
loop's builder library (single source of truth - do not hand-write CSVs or RSA columns):

RUN DIR (create it): ${runDir}

1) NEGATIVES CSV -> ${runDir}/negatives.csv
   python3 importing ${libDir}/builders/editor_csv.py, call build_negatives_csv(negatives, out).
   Use searchTerms.negatives (+ any SEMrush competitor-waste if present, else none).

2) KEYWORD-EXPANSION CSV -> ${runDir}/keyword_expansion.csv
   build_keyword_expansion_csv(winners, out) with searchTerms.winners. It skips already_exact and
   sets new keywords to Paused. Conservative - promote proven winners, never aggressively scale.

3) RSA CSV -> ${runDir}/rsa_challengers.csv (only if any ad group has challenger_flag or
   missing_angles). For each such ad group, write challenger RSA text grounded in
   assetHygiene.gap_brief + ${repoRoot}/plugins/google-ads-setup/skills/responsive-search-ads/references/headline-craft.md
   (apply its rules as VARIATION + tiebreakers, NOT as hard <20-char ceilings; keep the validated
   "ignore Ad Strength" stance). Build the sheet by importing ${libDir}/builders/load.py and
   calling build_rsa(ads, out) - it enforces the skill's own length + quality gates. New ads are
   Paused; NEVER emit a Removed row for an old ad. If no ad group needs one, set rsa_csv_path=null.

4) PERSIST THIS RUN -> ${runDir}/recommendations.json
   Write a compact JSON of what you recommended this run (negatives, winners, rsa ad groups, qs
   flags) so the NEXT run's measure stage can read it as "what we proposed last run". Set
   wrote_run_recommendations=true.

5) EXECUTIVE SUMMARY (Danish, markdown) - executive_summary_md. Structure:
   - "Siden sidst" (from measure): ${measure?.is_baseline_run ? 'this is a BASELINE run - say so, no prior to compare.' : 'what was applied + what moved, each with an honest significance flag.'}
   - "Denne kørsel fandt": N negatives (X DKK spild), M vindere, K ad groups uden challenger, QS-flag.
   - "I hver CSV" + the exact Editor steps (Konto > Importer > Fra fil > gennemgå grøn/gul > Send).
   - Honest caveats: low_confidence if set; SEMrush absent (gated); QS LP = flag not score.
   - A "## Kilder" block listing the MCP tools + any Firecrawl URLs used.

Return CsvBundle (the three paths or null, executive_summary_md, wrote_run_recommendations).
DIAGNOSTIC FINDINGS JSON:
${execPayload}
`, { label: 'execute', phase: 'Execute', schema: CSV_BUNDLE, agentType: 'general-purpose' })

log(`Execute done. negatives=${bundle?.negatives_csv_path ? 'yes' : 'no'} | ` +
    `expansion=${bundle?.keyword_expansion_csv_path ? 'yes' : 'no'} | ` +
    `rsa=${bundle?.rsa_csv_path ? 'yes' : 'no'} | recs persisted=${bundle?.wrote_run_recommendations}`)

return {
  account_id: customerId,
  client: clientName,
  window: { start, end },
  is_baseline_run: measure?.is_baseline_run || false,
  diagnostics: { measure, searchTerms, assetHygiene, qs },
  bundle,
}
