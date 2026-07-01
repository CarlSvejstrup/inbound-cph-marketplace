# CLAUDE.md — inbound-cph-marketplace

Operating rules for any Claude agent (Cowork, claude.ai Project, Claude Code, Agent SDK) running skills from this repo against Inbound CPH's Google Ads work.

This repo is a **marketplace with one plugin, `inbound-ads`**, covering Inbound CPH's full Google Ads lifecycle. Its skills group into three jobs:
- **Build a NEW campaign** — `campaign-build` (orchestrator) + `research`, `structuring`, `assets`, `responsive-search-ads`. Ends in a polished, client-shareable review workbook (Excel-only).
- **Optimize a LIVE account** — `soegeterm-analyse`, `search-term`, `annonce-optimering`, `optimering-loop` (RSA asset-hygiene, search-terms, the whole diagnose-to-workbook loop).
- **Standalone deliverables** — `ads-audit-report`, `ads-changelog`, `editor-csv-export` (the shared converter: a confirmed review workbook from EITHER `campaign-build`'s `assembler` OR `optimering-loop` → Editor import CSVs), `ai-context-publish`, `kontekst-opdater`, `opstart-analyse`.

This repo-root `CLAUDE.md` is the canonical operating contract, loaded via `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` when a skill runs. Skill-level `SKILL.md` files refine it, never override.

---

## Hard rule: human-in-the-loop on every write

**No external write happens without explicit user approval. No exceptions. This rule overrides skill convenience, demo polish, and "obvious next step" reasoning.**

External write means: anything that mutates a file in Drive, sends an email, posts to Slack, modifies a Sheet/Doc, or calls a third-party API with side effects. **Most skills are read-only / recommend-only against Google Ads** — the campaign-build output (the `assembler` workbook, Excel-only) and the optimization-loop output (the `review_workbook`) are review Excels; after a human confirms one, the shared `editor-csv-export` converts it to the Editor CSVs a human imports into Google Ads Editor. **Direct Google Ads writes are allowed only through the `ads-writer` agent, and only per-action HITL-confirmed** (direction set 2026-06-19) — no skill calls a Google Ads write tool itself. `display-placement-audit` is the first skill that routes a confirmed change through `ads-writer` instead of ending in a workbook.

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
- **"Push the campaign to the Ads account"** — never. There is no API-push path in this suite by design; the human imports the CSVs into Editor. (Verified constraint: Google Ads Editor imports CSV, not .xlsx; the workbook is the review layer, the CSVs are the import layer.)
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

Pure transforms that never touch a specific client's account or context (e.g. `editor-csv-export` converting an already-confirmed workbook) may skip this — but if a skill takes a client name as input, it preloads.

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
| `campaign-build` | Orchestrator: runs the Phase 1→4 pipeline (a subagent per phase reference) → the 10-tab review workbook. The pipeline (landing-page + competitor + strategy + structuring + RSA + assets + assembler) lives inside as `references/` + `scripts/assemble.py` | Gated — file/Drive save |
| `research` | Phase 1 standalone: landing-page positioning + competitor analysis + campaign strategy/settings → `.docx` | No — read-only |
| `structuring` | Phase-2 gate: ad groups + keywords (Exact/Phrase) + client-specific negatives → `.xlsx` | Gated — sheet save |
| `assets` | Phase 3: sitelinks, callouts, structured snippets (lead forms = manual UI) → `.xlsx` | Gated — sheet save |
| `responsive-search-ads` | RSA copy engine: one ad group → Editor-ready sheet with live `=LEN()`. Reused by `campaign-build` per group; consumes `annonce-optimering`'s gap-brief | Gated — sheet save |

### Optimize a live account

| Skill | Purpose | Writes? |
|---|---|---|
| `soegeterm-analyse` | Lean search-terms analysis → one colour-coded `.xlsx` with live FILTER action-sheets | Gated — sheet save |
| `search-term` | The conversational variant: talks findings through, then writes agreed negatives/keywords to Editor CSVs | Gated — CSV save |
| `annonce-optimering` | Post-launch RSA asset-hygiene → gap-brief (fed back into `responsive-search-ads`) | Gated — sheet save |
| `optimering-loop` | The whole diagnose-to-workbook loop in one go: search-terms + asset-hygiene + Quality Score → one editable review workbook | Gated — file/Drive save |
| `display-placement-audit` | Scores Display Network placements 0-100 for junk risk (gambling, MFA/clickbait, low-quality apps) via a bundled free blocklist + account signals; capped web lookups only for genuine toss-ups; ranked in-chat report (not .xlsx by default) | Gated — direct Google Ads write via `ads-writer` (PMax findings are suggestion-only, cannot write) |

### Standalone deliverables

| Skill | Purpose | Writes? |
|---|---|---|
| `ads-audit-report` | Full paid-search audit → HTML slide deck + PDF | Gated — file/Drive save |
| `ads-changelog` | Change-history → format-matched changelog draft | Gated — Drive paste |
| `ai-context-publish` | Publish per-client AI Context Docs to Drive + master client-index (vault→Drive, no Ads MCP) | Gated — Drive create (create-once) |
| `kontekst-opdater` | Per-client AI-context UPDATE + PM-overview (all on Drive): start in the master index, open the client's AI-Context file, pull what's new since its `Sidst opdateret` (Drive docs, HubSpot, status decks), critical TILFØJ/ERSTAT/FJERN diff into the Klientoverblik, write the updated AI-Context file in place (gws) or hand back a copy-paste block | Gated — Drive file write (diff-approved, gws-or-fallback) |
| `editor-csv-export` | Shared converter: a confirmed review workbook from `campaign-build`'s `assembler` OR `optimering-loop` → per-entity Editor import CSVs (pure transform, re-runs no-Broad + length guards) | Gated — file/Drive save |

Each skill's `SKILL.md` repeats the write-gate rule in its own Rules section. They are reinforcing, not redundant. All Google Ads MCP use is read-only.

---

## Skill coupling note

All skills now live in one plugin (`inbound-ads`), so `${CLAUDE_PLUGIN_ROOT}` resolves to a directory they all share — no cross-plugin file-reference limitation applies. `campaign-build` reuses `responsive-search-ads`'s RSA engine directly, and both `campaign-build` and `optimering-loop` feed the shared `editor-csv-export` converter. The `annonce-optimering` ↔ `responsive-search-ads` gap-brief loop is manual paste (no code coupling) between two sibling skills, so it closes the build→operate→iterate loop with a single plugin installed.

---

## Agents

Three bundled subagents live in `plugins/inbound-ads/agents/`. Each inherits the session's tools (so it can reach the user-connected Google Ads / Drive / HubSpot connectors) and strips file-writing tools; role and read/write intent are enforced by the system prompt, and Google Ads writes are enforced by a PreToolUse hook (below).

- **`ads-analyst`** — read-only account analyst. Every diagnostic skill (`ads-audit-report`, `soegeterm-analyse`, `annonce-optimering`, `opstart-analyse`, the diagnostic half of `optimering-loop`) dispatches account reading to it. Recommend-only; proposes changes for `ads-writer` to apply, never writes itself.
- **`ads-writer`** — the ONLY agent that writes to a Google Ads account, under strict per-action human-in-the-loop. Budget writes are held until the budget-guardrail ships, then require a second confirm for any change. Skills route confirmed changes through it.
- **`drive-knowledge`** — read-across-sources knowledge worker (Drive + HubSpot + Ads change-history). Used by `kontekst-opdater` / `ai-context-publish` / the future `context-update`. Read-only; timeless-only.

### The write guardrail (hard safety)

`hooks/google-ads-write-guardrail.sh` is a **PreToolUse** hook wired in `.claude/settings.json`. It matches on the tool's SHORT name (suffix after the last `__`), so it is install-portable regardless of the per-install MCP connector UUID. Budget writes → **deny** until the guardrail ships (then **ask**, second confirm); other Google Ads writes → **ask** (mandatory confirmation); reads + `generate_campaign_build_csv` + non-Ads tools → allow. It fires for ANY caller, not just `ads-writer`, and reinforces (never replaces) the agent prompts. **Scope limit:** the hook covers Google Ads tool names only — the read-only-ness of `ads-analyst` (web) and `drive-knowledge` (Drive/HubSpot) rests on their prompts and the calling skills' own write gates, not this hook.

---

## Voice and tone

Defaults to **Danish** for user interaction. English preserved for marketing/tool vocabulary (SEO, ROAS, GA4, RSA, etc.). Avoid AI/ML jargon when explaining the system — users are marketers, not engineers. Client-facing ad copy follows the client's own voice, never invented.

---

## When in doubt

- A read you weren't sure was needed → do it.
- A write you weren't sure was approved → don't do it. Ask.
- A push to a Google Ads account → never. Emit artifacts; the human imports.
