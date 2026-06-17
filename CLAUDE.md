# CLAUDE.md — inbound-cph-marketplace

Operating rules for any Claude agent (Cowork, claude.ai Project, Claude Code, Agent SDK) running skills from this repo against Inbound CPH's Google Ads work.

This repo is a **marketplace with three plugins**:
- **`google-ads-setup`** — build a NEW Google Ads campaign end-to-end (research → structure → creative → a polished, client-shareable review workbook; Excel-only).
- **`google-ads-optimization`** — optimize a LIVE Google Ads account (RSA asset-hygiene, search-terms).
- **`google-ads-general`** — standalone deliverables (audit reports, change-logs, and `editor-csv-export`: the shared converter — a confirmed review workbook from EITHER setup's `assembler` OR the optimization-loop → Editor import CSVs).

Each plugin also carries its own `CLAUDE.md` (a copy of the same operating contract) loaded via `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` when a skill runs. This repo-root file is the canonical version; the plugin copies refine, never override. Skill-level `SKILL.md` files refine further, never override.

---

## Hard rule: human-in-the-loop on every write

**No external write happens without explicit user approval. No exceptions. This rule overrides skill convenience, demo polish, and "obvious next step" reasoning.**

External write means: anything that mutates a file in Drive, sends an email, posts to Slack, modifies a Sheet/Doc, or calls a third-party API with side effects. **Google Ads is never written to — every skill is read-only / recommend-only against the account.** Both the campaign-build output (the `assembler` workbook, Excel-only) and the optimization-loop output (the `review_workbook`) are review Excels; after a human confirms one, the shared `editor-csv-export` converts it to the Editor CSVs a human imports into Google Ads Editor; the optimization skills only diagnose and recommend.

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

### google-ads-setup — build a new campaign

| Skill | Purpose | Writes? |
|---|---|---|
| `landing-page-analyzer` | Scrape a landing page → structured positioning JSON | No — read-only |
| `competitor-research` | Competitor positioning from their own pages → differentiator map | No — read-only |
| `campaign-strategy` | Campaign settings as a decision object (tab 01) | No — emits an object |
| `semrush-research` | **Gated** keyword volume/difficulty/CPC + organic + trends; degrades to theme-derived | No — read-only |
| `structuring` | Phase-2 gate: ad groups + keywords (Exact/Phrase) + client-specific negatives | No — emits an object |
| `rsa-copywriter` | RSAs for every ad group, reusing `responsive-search-ads` per group | Gated — sheet save |
| `assets` | Sitelinks, callouts, structured snippets (lead forms = manual UI) | No — emits an object |
| `assembler` | Merges all four shapes → polished 10-tab review workbook (Excel-only, NO CSV, NO API push) | Gated — file/Drive save |
| `responsive-search-ads` | RSA copy engine: one ad group → Editor-ready sheet with live `=LEN()` | Gated — sheet save |

### google-ads-optimization — optimize a live account

| Skill | Purpose | Writes? |
|---|---|---|
| `annonce-optimering` | Post-launch RSA asset-hygiene → gap-brief | Gated — sheet save |
| `search-terms` | Search-terms analysis → sheet + negative-keyword list | Gated — sheet save |

### google-ads-general — standalone deliverables

| Skill | Purpose | Writes? |
|---|---|---|
| `ads-audit-report` | Full paid-search audit → HTML slide deck + PDF | Gated — file/Drive save |
| `ads-changelog` | Change-history → format-matched changelog draft | Gated — Drive paste |
| `editor-csv-export` | Shared converter: a confirmed review workbook from setup's `assembler` OR the optimization-loop → per-entity Editor import CSVs (pure transform, re-runs no-Broad + length guards) | Gated — file/Drive save |

Each skill's `SKILL.md` repeats the write-gate rule in its own Rules section. They are reinforcing, not redundant. All Google Ads MCP use is read-only.

---

## Cross-plugin note

`${CLAUDE_PLUGIN_ROOT}` resolves to a single plugin's directory, so a skill cannot reference files in a sibling plugin. `responsive-search-ads` lives in `google-ads-setup` because `rsa-copywriter` + `assembler` depend on it in code. The `annonce-optimering` ↔ `responsive-search-ads` gap-brief loop crosses the plugin boundary, but it's manual paste (no code coupling) — both plugins must be installed to close the build→operate→iterate loop.

---

## Voice and tone

Defaults to **Danish** for user interaction. English preserved for marketing/tool vocabulary (SEO, ROAS, GA4, RSA, etc.). Avoid AI/ML jargon when explaining the system — users are marketers, not engineers. Per-plugin `context/voice-house-style.md` carries Inbound's house voice; client-facing ad copy follows the client's own voice, never invented.

---

## When in doubt

- A read you weren't sure was needed → do it.
- A write you weren't sure was approved → don't do it. Ask.
- A push to a Google Ads account → never. Emit artifacts; the human imports.
