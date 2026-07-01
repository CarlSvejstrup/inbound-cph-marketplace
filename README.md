# inbound-cph-marketplace

Claude Code / Cowork plugin marketplace for Inbound CPH's Google Ads work. Ships **one plugin, `inbound-ads`**, installed per user and updated via `/plugin update`. Its skills cover the full lifecycle, grouped into three jobs:

- **Build a NEW campaign** — `inb-ads-campaign-build` (orchestrator) + `inb-ads-rsa-copy`. `inb-ads-campaign-build` runs the Phase 1→4 pipeline (a subagent per phase reference) and by default **creates the campaign directly in the account** via the `ads-writer` agent — HITL-gated per action, started paused (recommended) or active per the user's choice. The 10-tab Excel review workbook is now **opt-in** (when the client must approve the setup first). The phases live only as references inside `inb-ads-campaign-build`.
- **Optimize a LIVE account** — `inb-ads-search-term-analyse` (merged from the former `soegeterm-analyse` + `search-term`), `inb-ads-rsa-hygiene`, `inb-ads-optimization-loop`, `inb-ads-display-placement-audit` (post-launch RSA asset-hygiene + search-terms analysis / negative-keyword mining + the whole diagnose-to-workbook loop + GDN placement junk-audit).
- **Standalone deliverables** — `inb-ads-account-audit`, `inb-ads-change-log`, `inb-ads-editor-csv-export` (the shared converter: a confirmed review workbook from EITHER `inb-ads-campaign-build` OR `inb-ads-optimization-loop` → Google Ads Editor import CSVs), `inb-ads-context-publish`, `inb-ads-client-brief`, `inb-ads-onboarding-analysis`.

All skills share one operating contract (`CLAUDE.md`). Every external write is **human-in-the-loop, confirmed per action** — no skill writes to a Google Ads account autonomously. Direct Google Ads writes are allowed only through the `ads-writer` agent behind the write-guardrail hook; `inb-ads-campaign-build` now creates campaigns directly this way, and the review-workbook + Editor-CSV path remains for when a human prefers to import after approval.

## Install

In Cowork (or any Claude Code surface), add the marketplace once, then install the plugin:

```
/plugin marketplace add CarlSvejstrup/inbound-cph-marketplace
/plugin install inbound-ads@inbound-cph
```

The marketplace is named `inbound-cph`, so the install syntax is `inbound-ads@inbound-cph`. Because every skill now lives in one plugin, the full build→operate→iterate loop (including the `inb-ads-rsa-hygiene` → `inb-ads-rsa-copy` gap-brief manual paste) closes with a single install.

## Skills shipped

`inbound-ads` ships **12 skills** in one plugin, grouped by job.

### Build a new campaign

| Skill | Purpose |
|---|---|
| `inb-ads-campaign-build` | Orchestrator — runs the Phase 1→4 pipeline (a subagent per phase reference), then **by default creates the campaign directly in the Google Ads account** via the `ads-writer` agent (HITL-gated per action, started paused (recommended) or active per the user's choice). Ian's polished 10-tab Excel review workbook is now **opt-in** — produced when the client must approve the setup first, after which `inb-ads-editor-csv-export` makes the Editor CSVs. The full pipeline (landing-page, competitor, strategy, structuring, RSA, assets, assembler) lives inside as `references/` + `scripts/assemble.py`; the former standalone phase skills were removed (their logic already lived here) |
| `inb-ads-rsa-copy` | The RSA copy engine: one ad group → an Editor-ready sheet with live `=LEN()` guards. Reused by `inb-ads-campaign-build` per group; runnable standalone |

### Optimize a live account

| Skill | Purpose |
|---|---|
| `inb-ads-search-term-analyse` | Search-terms-report analysis → one colour-coded `.xlsx` with live FILTER action-sheets (Negativ/Vinder), or the conversational variant that surfaces the interesting findings, talks them through, and writes the agreed negatives/new keywords straight into Google Ads Editor import CSVs (merged from the former `soegeterm-analyse` + `search-term`) |
| `inb-ads-rsa-hygiene` | Post-launch RSA asset-hygiene diagnosis (champion-challenger coverage, dead-weight assets) → gap-brief fed back into `inb-ads-rsa-copy` |
| `inb-ads-optimization-loop` | The whole diagnose-to-workbook loop in one go: search-terms + asset-hygiene + Quality Score → one editable Excel review workbook |
| `inb-ads-display-placement-audit` | Scores Display Network placements 0-100 for junk risk (gambling, MFA/clickbait, low-quality apps) via a bundled free blocklist + account signals → ranked in-chat report, then writes confirmed negative placements directly via `ads-writer` |

### Standalone deliverables

| Skill | Purpose |
|---|---|
| `inb-ads-account-audit` | Full paid-search audit → polished HTML slide deck + rendered PDF report |
| `inb-ads-change-log` | Build a changelog/optimeringslog entry from Google Ads' own change history (per client, or per specialist across their accounts) → format-matched draft to paste into the client's Drive changelog |
| `inb-ads-editor-csv-export` | The **shared** converter for both workflows: a confirmed review workbook — from `inb-ads-campaign-build`'s `assembler` (full new campaign) OR `inb-ads-optimization-loop`'s `review_workbook` (subset) → the per-entity Google Ads Editor import CSVs. Reads both dialects on one contract. Pure transform, re-runs the no-Broad + length guards, never pushes to the account |
| `inb-ads-context-publish` | Publish per-client AI Context Docs to Drive + maintain the master client-index (vault→Drive, no Ads MCP; create-once) |
| `inb-ads-client-brief` | Project-manager brief on one client (who they are, recent work, status, open threads) + on-demand AI-context update, all on Drive: pull what's new since the file's `Sidst opdateret` (Drive docs, HubSpot, status decks) with HITL-gated TILFØJ/ERSTAT/FJERN, write the updated file in place |
| `inb-ads-onboarding-analysis` | New-client onboarding: the 35-point ClickUp Analysearbejdet account review → a `.docx` checklist report in the client's Drive folder |

## Data integration

- **Google Ads MCP** — reads are free (campaigns, keywords, search terms, RSA assets, the MCC shared negative list). Writes are allowed only through the `ads-writer` agent, HITL-gated per action behind the write-guardrail hook; no skill calls a Google Ads write tool itself.
- **Firecrawl** — landing-page + competitor scraping.
- **Drive connector** — Cowork's built-in `mcp__claude_ai_Google_Drive__*`; each user authorises once. Drive root via `userConfig.inbound_root_folder_id` in each `plugin.json`.
- **Semrush MCP** — optional, plan-gated; `inb-ads-campaign-build`'s research phase uses it when available and degrades to theme-derived keywords otherwise.

## Philosophy

**Hard rule: human-in-the-loop on every write.** Every skill stops at "here's the change, confirm to apply" and executes only after explicit per-action approval. Direct Google Ads writes are allowed only through the `ads-writer` agent (behind the write-guardrail hook) — `inb-ads-campaign-build` now creates campaigns directly this way by default, started paused (recommended) or active per the user's choice, and can instead deliver a review workbook + CSVs for a human to import into Google Ads Editor when the client must approve first. Budget writes stay gated behind the guardrail hook + `INBOUND_ADS_BUDGET_GUARDRAIL`, requiring explicit per-action confirmation. The operating contract is in each plugin's `CLAUDE.md`, loaded automatically when a skill runs.

**Reading is free, writing is gated.** Skills read aggressively (Drive, Google Ads MCP, the web) without asking. Approval is required only at the moment bytes leave the agent.

**Skills are code.** Version-controlled, reviewed, distributed via the plugin update flow.

## Repo structure

```
.claude-plugin/
  marketplace.json                # marketplace "inbound-cph", lists the one plugin
CLAUDE.md                         # the shared operating contract (repo root)
plugins/
  inbound-ads/
    .claude-plugin/plugin.json    # name "inbound-ads", version, userConfig
    agents/                       # ads-analyst, ads-writer, drive-knowledge
    hooks/                        # PreToolUse write guardrail (bundled with the plugin)
      hooks.json                  # wires the guardrail; fires automatically on install
      google-ads-write-guardrail.sh
      README.md                   # hook policy
    skills/                       # all 12 skills (see tables above)
    _archive/                     # retired skills, kept for reference
docs/
  project-status.md, session-handoff.md, ...
```

## Agents

Three bundled subagents in `plugins/inbound-ads/agents/`, dispatched by the skills:

| Agent | Role |
|---|---|
| `ads-analyst` | Read-only account analyst + web research. The reusable read worker every diagnostic skill dispatches to. Recommend-only, never writes. |
| `ads-writer` | The **only** agent that writes to a Google Ads account, under strict per-action human-in-the-loop. `inb-ads-campaign-build` routes its direct campaign creation through this agent. Budget writes stay gated behind the write-guardrail hook + `INBOUND_ADS_BUDGET_GUARDRAIL`, requiring explicit per-action confirmation. |
| `drive-knowledge` | Read-across-sources worker (Drive + HubSpot + Ads change-history) for the client-context skills. Read-only, timeless-only. |

Each inherits the session's tools (to reach the user-connected connectors) and strips file-writing; read/write intent is enforced by prompt, and Google Ads writes by the guardrail hook.

### Write guardrail (hard safety)

`plugins/inbound-ads/hooks/google-ads-write-guardrail.sh` is a **PreToolUse** hook **bundled in the plugin** (wired via `plugins/inbound-ads/hooks/hooks.json`). It ships with the plugin and fires automatically on every install — no per-seat setup. It gates every Google Ads write by the tool's short name, install-portable regardless of the per-install connector UUID. Budget writes: **deny** until `INBOUND_ADS_BUDGET_GUARDRAIL=1`, then **ask** (per-action confirm). Other writes (including `inb-ads-campaign-build`'s direct campaign creation): **ask**. Reads + CSV generation + non-Ads tools: allow. It fires for any caller. (Plugin-*root* hooks are supported; agent-frontmatter hooks are not, which is why the guardrail lives here rather than in an agent file.)

## Versioning + update flow

The plugin uses **explicit semver** in its `plugin.json`. Bump it every time you ship changes — pushing without bumping does nothing for users (Claude Code compares version strings, not SHAs).

After bumping and pushing:

1. Users open Cowork → marketplace panel.
2. Click `...` next to the **`inbound-cph`** marketplace → Refresh.
3. The `inbound-ads` "Update" button lights up → click.

If marketplace metadata is stuck, the nuke-and-reinstall path:

```
/plugin marketplace remove inbound-cph
/plugin marketplace add CarlSvejstrup/inbound-cph-marketplace
/plugin install inbound-ads@inbound-cph
```

## Adding or editing a skill

```bash
# 1. Create the skill directory
mkdir -p plugins/inbound-ads/skills/<skill-name>
# 2. Write SKILL.md (frontmatter: name, description; body: when-to-use, inputs, what-to-produce, rules)
# 3. Bump plugins/inbound-ads/.claude-plugin/plugin.json version
# 4. Commit, push
# 5. Refresh marketplace + update in Cowork to test
```

Skill format follows Anthropic's universal SKILL.md spec; works across Cowork, Claude Code, Cursor, Codex.

## Skill coupling note

All 12 skills live in one plugin, so `${CLAUDE_PLUGIN_ROOT}` resolves to a directory they all share — there's no cross-plugin file-reference limitation. `inb-ads-campaign-build` reuses the `inb-ads-rsa-copy` RSA engine directly (via its internal pipeline references), and both `inb-ads-campaign-build` and `inb-ads-optimization-loop` feed the shared `inb-ads-editor-csv-export` converter. The `inb-ads-rsa-hygiene` ↔ `inb-ads-rsa-copy` gap-brief loop is manual paste (no code coupling) between two sibling skills, so a single install closes the full build→operate→iterate loop.

## Language and tone

Defaults to **Danish** for user interaction. English preserved for marketing/tool vocabulary (SEO, ROAS, GA4, RSA, etc.). AI/ML jargon avoided when explaining the system — users are marketers, not engineers. Full rules in each plugin's `CLAUDE.md`.
