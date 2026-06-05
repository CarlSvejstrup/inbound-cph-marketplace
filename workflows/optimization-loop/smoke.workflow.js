export const meta = {
  name: 'optimization-loop-smoke',
  description: 'De-risk probe: one agent runs the search-terms GAQL against a live account via the Google Ads MCP and returns schema-validated SearchTermFindings. Proves the agent->Bash/MCP->schema-JSON pattern before building the full loop.',
  phases: [
    { title: 'Probe', detail: 'one search-term diagnostic agent against the live account' },
  ],
}

// args: { customer_id, window_start, window_end, repo_root }
const a = args || {}
const customerId = a.customer_id || '3069826320'        // DSC, the live-verified account
const start = a.window_start || '2026-03-07'
const end = a.window_end || '2026-06-05'
const repoRoot = a.repo_root || '/Users/carlschmidt-svejstrup/code/personal/inbound-cph-demo'

phase('Probe')

// Inline JS-literal schema (the JS cannot load lib/schemas/*.json). Mirrors §3.1 SearchTermFindings.
const SEARCH_TERM_FINDINGS = {
  type: 'object',
  required: ['account_id', 'window', 'low_confidence', 'negatives', 'winners', 'placement_problems'],
  properties: {
    account_id: { type: 'string' },
    window: {
      type: 'object',
      required: ['start', 'end'],
      properties: { start: { type: 'string' }, end: { type: 'string' } },
    },
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

const prompt = `
You are the search-term diagnostic stage of the Inbound CPH optimization loop. This is a
READ-ONLY diagnostic run against a LIVE Google Ads account. You write nothing to the account
and nothing to Drive.

Account (customer_id): ${customerId}
Analysis window: ${start} to ${end}
Repo root: ${repoRoot}

STEP 1 — get the exact GAQL. Run this and read it (the queries are the single source of truth,
already live-verified; do not invent field names):
  cat ${repoRoot}/workflows/optimization-loop/lib/gaql/search_terms.py

STEP 2 — run the search-terms query against the account using the Google Ads MCP tool
run_custom_gaql (customer_id=${customerId}). Use the BETWEEN window ${start}..${end}. The query
already enforces campaign.status='ENABLED' and the 5 DKK spend floor. Pull the keyword_map_query
too so you can detect struktur placement problems. Cost is micros -> DKK = cost_micros/1e6.

STEP 3 — classify each term into the taxonomy (RELEVANT / VINDER / PLACEMENT_PROBLEM /
IRRELEVANT / GRAENSE) using the rules you can infer from the query comments and standard PPC
sense. SIGNIFICANCE DISCIPLINE (non-negotiable): if total account conversions in the window is
under 10, set low_confidence=true and be conservative — do not promote a "winner" resting on
1-2 conversions; a VINDER needs >=2 conversions. Paused campaigns are intentional, never
flagged.

STEP 4 — return ONLY the structured object: the recommended negatives (IRRELEVANT +
struktur-placement terms, with level + wasted spend), the winners (converting, not yet exact),
and any placement_problems. Set account_id, window, low_confidence, account_conversions.

This is a smoke test: a small, honest result is the goal. If the account has little spend in the
window, returning few or zero items with low_confidence=true is a CORRECT result, not a failure.
`.trim()

const findings = await agent(prompt, {
  label: `search-terms:${customerId}`,
  phase: 'Probe',
  schema: SEARCH_TERM_FINDINGS,
  agentType: 'general-purpose',   // ensure Bash + MCP access
})

log(`Smoke probe returned: ${(findings?.negatives || []).length} negatives, ` +
    `${(findings?.winners || []).length} winners, ` +
    `${(findings?.placement_problems || []).length} placement problems, ` +
    `low_confidence=${findings?.low_confidence}`)

return findings
