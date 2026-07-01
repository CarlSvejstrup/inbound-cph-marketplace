# CLAUDE.md — inbound-cph-marketplace

Operating rules for any Claude agent (Cowork, claude.ai Project, Claude Code, Agent SDK) running skills from this repo against Inbound CPH's Google Ads work.

This repo is a **marketplace with one plugin, `inbound-ads` (12 skills)**, covering Inbound CPH's full Google Ads lifecycle. Its skills group into three jobs:
- **Build a NEW campaign** — `inb-ads-campaign-build` (orchestrator) + `inb-ads-rsa-copy`. `inb-ads-campaign-build` runs the Phase 1→4 pipeline and by default **creates the campaign directly in the account** via the `ads-writer` agent (HITL-gated per action, started paused (recommended) or active per the user's choice); the 10-tab Excel review workbook is now **opt-in** (when the client must approve the setup first). The phases live only as references inside `inb-ads-campaign-build`.
- **Optimize a LIVE account** — `inb-ads-search-term-analyse` (merged from the former soegeterm-analyse + search-term), `inb-ads-rsa-hygiene`, `inb-ads-optimization-loop`, `inb-ads-display-placement-audit` (RSA asset-hygiene, search-terms, the whole diagnose-to-workbook loop, GDN placement junk-audit).
- **Standalone deliverables** — `inb-ads-account-audit`, `inb-ads-change-log`, `inb-ads-editor-csv-export` (the shared converter: a confirmed review workbook from EITHER `inb-ads-campaign-build` OR `inb-ads-optimization-loop` → Editor import CSVs), `inb-ads-context-publish`, `inb-ads-client-brief`, `inb-ads-onboarding-analysis`.

This repo-root `CLAUDE.md` is the canonical operating contract, loaded via `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` when a skill runs. Skill-level `SKILL.md` files refine it, never override.

---

## Hard rule: human-in-the-loop on every write

**No external write happens without explicit user approval. No exceptions. This rule overrides skill convenience, demo polish, and "obvious next step" reasoning.**

External write means: anything that mutates a file in Drive, sends an email, posts to Slack, modifies a Sheet/Doc, or calls a third-party API with side effects — **including any write to a Google Ads account**. **Direct Google Ads writes are allowed only through the `ads-writer` agent, and only per-action HITL-confirmed** (direction set 2026-06-19) — no skill calls a Google Ads write tool itself. **`inb-ads-campaign-build` now creates campaigns directly by default** (2026-07-01): it routes campaign creation through `ads-writer`, HITL-gated per action, started **paused** (safe, recommended) or **active** per the user's choice. Its 10-tab Excel review workbook is now **opt-in** — used only when the client must approve the setup first, after which the shared `inb-ads-editor-csv-export` converts a confirmed workbook to the Editor CSVs a human imports into Google Ads Editor. The optimization-loop output (the `review_workbook`) follows the same opt-in review path. **Budget writes stay gated behind the write-guardrail hook + `INBOUND_ADS_BUDGET_GUARDRAIL`, requiring explicit per-action confirmation.** `inb-ads-display-placement-audit` also routes its confirmed negative placements through `ads-writer`.

Read operations are not writes. Drafting in chat is not a write. Producing a proposed change is not a write. The boundary is the moment bytes leave the agent and land somewhere persistent or visible to anyone other than the operator.

### The approval pattern (use this exactly)

For every write, follow this four-step pattern:

1. **Draft.** Produce the full content of the change in chat.
2. **Render the proposal.** Show the exact change in a fenced code block (or a clear diff for edits), prefixed with one of:
   - *"Proposed write to `<path>` — confirm to write, edit to revise, or say skip."*
   - *"Proposed upload to Drive `<folder>` — confirm to upload, edit to revise, or say skip."*
   - *"Proposed email to `<recipient>` — confirm to send, edit to revise, or say skip."*
3. **Wait for explicit approval.** Approval is `yes` / `approve` / `confirm` / `send it` / `write it` / `apply` — or an edit (which counts as approval of the edited version). Silence is NOT approval. A thumbs-up emoji is NOT approval. A continuation prompt ("ok now do X") is NOT approval of the prior write. Re-prompt if ambiguous.
4. **Execute and confirm back.** Only after explicit approval, perform the write. Then confirm with the path/recipient and what was written, so the user can verify.

### Things that look like edge cases but aren't

- **"Just save the sheet to Drive"** — still a write. Still needs approval (covers both the local file and the Drive upload).
- **"The user just said do it"** — if "it" wasn't the specific write you're about to perform, re-confirm. Approval is scoped to the exact change shown, not to the session.
- **"It's a re-run of a write the user approved earlier"** — re-confirm. State has changed; the new draft may differ.
- **"It's idempotent / can be undone"** — irrelevant. Approval is required regardless of reversibility.
- **"Push the campaign to the Ads account"** — allowed, but ONLY through the `ads-writer` agent and ONLY per-action HITL-confirmed. `inb-ads-campaign-build` does this by default (started paused unless the user chooses active); each write is proposed and confirmed before it executes, and budget writes wait on the guardrail (`INBOUND_ADS_BUDGET_GUARDRAIL`). No skill writes autonomously or in bulk without per-action confirmation. The review-workbook → Editor-CSV path remains available for when a human prefers to import after client approval (Google Ads Editor imports CSV, not .xlsx; the workbook is the review layer, the CSVs the import layer).
- **Scheduled tasks** — a scheduled run produces a draft and *notifies*; the write only happens after the user approves on review. Not standing approval.
- **Demo / live walkthrough** — same rule. Demonstrating the human-in-the-loop pattern *is* a feature, not friction.

### Why this matters (do not lose this)

These skills operate against the client's institutional memory (Drive) and live Google Ads accounts. An unapproved write that turns out wrong corrupts a client's Drive, embarrasses the agency, or touches a client surface without authorisation. The cost of pausing for one confirmation is seconds; the cost of a wrong autonomous write is trust. This human-in-the-loop pattern is what lets the system stay safe while compounding. Bake it in from skill #1.

---

## Hard rule: preload the client's AI Context first

**Every skill that acts on a named client MUST load that client's AI Context file into its working context BEFORE doing anything else (research, audit, build, optimization, export).** This is a read, so it is never gated — but it is mandatory. It is how a skill inherits everything Inbound knows about the client (IDs, contacts, hard rammer, naming convention, bid-strategy norm, KPIs, paused-campaign intent) instead of starting blind.

The procedure (do this as step 0):

1. **Identify the client (the "customer").** Take the client the user names (their input — a name, domain, or account). If it is missing or ambiguous, ask which client before proceeding.
2. **Open the master client-index in Drive** via the Drive connector (`search_files` for the Google Doc titled `Inbound CPH — Google Ads klient-index (AI Context)`; current id `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`, in the "A - Kunder" Drive folder). Read it (`read_file_content`). It maps every client to its Google Ads ID, HubSpot ID, ClickUp folder, **Stage**, Drive-mappe, and **AI Context-fil** link.
3. **Find the client's row**, resolving by name/domain/Ads-ID. Note the **Stage** (customer / lead / opportunity / "ikke tagget") — a non-`customer` stage means it is not a closed paying account; weight recommendations accordingly and never assume an active retainer. For shared-folder groups (Lime, Retriever/Infomedia, GSGroup, Nemco, Julemærket, PhoneAlone, DI), pick the row for the specific market/account.
4. **Open the client's AI Context `.md`** via its Drive link from the index row (`read_file_content`) and pull it into your working context. This file holds the operational brief: IDs, contacts, hard rammer (read before you act), goals/KPIs, naming convention, how-we-run-it, and the changelog/optimeringslog link (read the changelog doc too if the task needs change history — it is kept separate, linked from the AI Context file).
5. **Only then** start the skill's real work, treating the AI Context as ground truth for client facts.

If the client has no row in the index or no AI Context file yet, say so and proceed with whatever context you can gather (Drive folder, Ads MCP) — but flag the gap. Never silently skip the lookup.

Pure transforms that never touch a specific client's account or context (e.g. `inb-ads-editor-csv-export` converting an already-confirmed workbook) may skip this — but if a skill takes a client name as input, it preloads.

---

## Reading is free, writing is gated

The corollary: **read aggressively, write conservatively.**

When the user asks for research, an audit, a structure, or a draft — read everything relevant (Drive, Google Ads MCP, the web via Firecrawl, Semrush when available) without asking. The agent's value is synthesis across context the user can't hold in their head. Reads don't need approval; volume of context is the point.

But every skill that produces an artifact or recommendation stops at "here's the draft/workbook/CSV, confirm to save." The skill describes the *intent*; the agent enforces the *gate*.

---

## Skills in this repo

### Build a new campaign

| Skill | Purpose | Writes? |
|---|---|---|
| `inb-ads-campaign-build` | Orchestrator: runs the Phase 1→4 pipeline (a subagent per phase reference), then **by default creates the campaign directly in the account** via `ads-writer` (started paused (recommended) or active per the user's choice). The 10-tab Excel review workbook is **opt-in** (client-approval-first path). The pipeline (landing-page + competitor + strategy + structuring + RSA + assets + assembler) lives inside as `references/` + `scripts/assemble.py`; the former standalone phase skills were removed | Gated — direct Google Ads write via `ads-writer`, per-action HITL (budget writes behind the guardrail); OR gated file/Drive save in review-workbook mode |
| `inb-ads-rsa-copy` | RSA copy engine: one ad group → Editor-ready sheet with live `=LEN()`. Reused by `inb-ads-campaign-build` per group; consumes `inb-ads-rsa-hygiene`'s gap-brief; runnable standalone | Gated — sheet save |

### Optimize a live account

| Skill | Purpose | Writes? |
|---|---|---|
| `inb-ads-search-term-analyse` | Search-terms analysis → one colour-coded `.xlsx` with live FILTER action-sheets, or talk findings through and write agreed negatives/keywords to Editor CSVs (merged from the former `soegeterm-analyse` + `search-term`) | Gated — sheet/CSV save |
| `inb-ads-rsa-hygiene` | Post-launch RSA asset-hygiene → gap-brief (fed back into `inb-ads-rsa-copy`) | Gated — sheet save |
| `inb-ads-optimization-loop` | The whole diagnose-to-workbook loop in one go: search-terms + asset-hygiene + Quality Score → one editable review workbook | Gated — file/Drive save |
| `inb-ads-display-placement-audit` | Scores Display Network placements 0-100 for junk risk (gambling, MFA/clickbait, low-quality apps) via a bundled free blocklist + account signals; capped web lookups only for genuine toss-ups; ranked in-chat report (not .xlsx by default) | Gated — direct Google Ads write via `ads-writer` (PMax findings are suggestion-only, cannot write) |

### Standalone deliverables

| Skill | Purpose | Writes? |
|---|---|---|
| `inb-ads-account-audit` | Full paid-search audit → HTML slide deck + PDF | Gated — file/Drive save |
| `inb-ads-change-log` | Change-history → format-matched changelog draft | Gated — Drive paste |
| `inb-ads-context-publish` | Publish per-client AI Context Docs to Drive + master client-index (vault→Drive, no Ads MCP) | Gated — Drive create (create-once) |
| `inb-ads-client-brief` | Project-manager brief on one client + on-demand AI-context UPDATE (all on Drive): start in the master index, open the client's AI-Context file, brief on it, pull what's new since its `Sidst opdateret` (Drive docs, HubSpot, status decks), critical TILFØJ/ERSTAT/FJERN diff into the Klientoverblik, write the updated AI-Context file in place (gws) or hand back a copy-paste block | Gated — Drive file write (diff-approved, gws-or-fallback) |
| `inb-ads-editor-csv-export` | Shared converter: a confirmed review workbook from `inb-ads-campaign-build`'s `assembler` OR `inb-ads-optimization-loop` → per-entity Editor import CSVs (pure transform, re-runs no-Broad + length guards) | Gated — file/Drive save |

Each skill's `SKILL.md` repeats the write-gate rule in its own Rules section. They are reinforcing, not redundant. All Google Ads MCP use is read-only.

---

## Skill coupling note

All skills now live in one plugin (`inbound-ads`), so `${CLAUDE_PLUGIN_ROOT}` resolves to a directory they all share — no cross-plugin file-reference limitation applies. `inb-ads-campaign-build` reuses `inb-ads-rsa-copy`'s RSA engine directly, and both `inb-ads-campaign-build` and `inb-ads-optimization-loop` feed the shared `inb-ads-editor-csv-export` converter. The `inb-ads-rsa-hygiene` ↔ `inb-ads-rsa-copy` gap-brief loop is manual paste (no code coupling) between two sibling skills, so it closes the build→operate→iterate loop with a single plugin installed.

---

## Agents

Three bundled subagents live in `plugins/inbound-ads/agents/`. Each inherits the session's tools (so it can reach the user-connected Google Ads / Drive / HubSpot connectors) and strips file-writing tools; role and read/write intent are enforced by the system prompt, and Google Ads writes are enforced by a PreToolUse hook (below).

- **`ads-analyst`** — read-only account analyst. Every diagnostic skill (`inb-ads-account-audit`, `inb-ads-search-term-analyse`, `inb-ads-rsa-hygiene`, `inb-ads-onboarding-analysis`, the diagnostic half of `inb-ads-optimization-loop`) dispatches account reading to it. Recommend-only; proposes changes for `ads-writer` to apply, never writes itself.
- **`ads-writer`** — the ONLY agent that writes to a Google Ads account, under strict per-action human-in-the-loop. `inb-ads-campaign-build` routes its default direct campaign creation through it (started paused unless the user chooses active). Budget writes stay gated behind the write-guardrail hook + `INBOUND_ADS_BUDGET_GUARDRAIL`, requiring explicit per-action confirmation. Skills route confirmed changes through it.
- **`drive-knowledge`** — read-across-sources knowledge worker (Drive + HubSpot + Ads change-history). Used by `inb-ads-client-brief` / `inb-ads-context-publish`. Read-only; timeless-only.

### The write guardrail (hard safety)

`plugins/inbound-ads/hooks/google-ads-write-guardrail.sh` is a **PreToolUse** hook **bundled in the plugin** (wired via `plugins/inbound-ads/hooks/hooks.json`), so it ships with the plugin and fires automatically on every install with no per-seat setup. It matches on the tool's SHORT name (suffix after the last `__`), so it is install-portable regardless of the per-install MCP connector UUID. Budget writes → **deny** until `INBOUND_ADS_BUDGET_GUARDRAIL=1` (then **ask**, per-action confirm); other Google Ads writes (including `inb-ads-campaign-build`'s direct campaign creation) → **ask** (mandatory confirmation); reads + `generate_campaign_build_csv` + non-Ads tools → allow. It fires for ANY caller, not just `ads-writer`, and reinforces (never replaces) the agent prompts. **Scope limit:** the hook covers Google Ads tool names only — the read-only-ness of `ads-analyst` (web) and `drive-knowledge` (Drive/HubSpot) rests on their prompts and the calling skills' own write gates, not this hook.

---

## Voice and tone

Defaults to **Danish** for user interaction. English preserved for marketing/tool vocabulary (SEO, ROAS, GA4, RSA, etc.). Avoid AI/ML jargon when explaining the system — users are marketers, not engineers. Client-facing ad copy follows the client's own voice, never invented.

---

## When in doubt

- A read you weren't sure was needed → do it.
- A write you weren't sure was approved → don't do it. Ask.
- A push to a Google Ads account → only through `ads-writer`, only per-action HITL-confirmed (budget writes behind the guardrail). If unsure whether a specific change is confirmed, don't write — re-confirm.
