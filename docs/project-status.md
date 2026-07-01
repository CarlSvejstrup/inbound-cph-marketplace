# Project status — inbound-cph-marketplace

Single source of truth for what's shipped vs what's open. Update at the end of every substantive session.

Last updated: 2026-07-01, after the skill-slug rename + search-skill merge.

> **2026-07-01 — skill-slug rename + search-skill merge (`inbound-ads` v3.2.0, current roster).** All skills were renamed to `inb-ads-*` slugs, and the two search skills (`soegeterm-analyse` + `search-term`) were MERGED into one, dropping the count from 16 to **15 skills**. The current roster is: **Build** — `inb-ads-campaign-build`, `inb-ads-campaign-research`, `inb-ads-campaign-structure`, `inb-ads-campaign-assets`, `inb-ads-rsa-copy`; **Optimize** — `inb-ads-search-term-analyse` (the merged search skill), `inb-ads-rsa-hygiene`, `inb-ads-optimization-loop`, `inb-ads-display-placement-audit`; **Standalone** — `inb-ads-account-audit`, `inb-ads-change-log`, `inb-ads-editor-csv-export`, `inb-ads-context-publish`, `inb-ads-context-update`, `inb-ads-onboarding-analysis`. Bundled agents (`ads-analyst`, `ads-writer`, `drive-knowledge`) and the write-guardrail hook are unchanged. The dated notes and milestone sections below name the OLD pre-rename slugs (`ads-audit`, `search-terms`, `annoncetekster`, `campaign-build`, etc.) and are kept verbatim as historical record — do not retro-rename them.

> **2026-07-01 — bundled agents + write guardrail (`inbound-ads` v3.1.0).** Added three subagents under `plugins/inbound-ads/agents/`: `ads-analyst` (read-only account analyst + web research, the reusable read worker), `ads-writer` (the sole HITL-gated account-write path; budget writes held until the guardrail ships, then second-confirm for any change), and `drive-knowledge` (read-across Drive/HubSpot/Ads-history worker). Each inherits the session's connectors and strips file-writing; read/write intent is by prompt. Hard write-safety is a PreToolUse hook (`hooks/google-ads-write-guardrail.sh`, wired in `.claude/settings.json`) that gates Google Ads writes by short tool name (install-portable, no UUID) — deny on budget until the guardrail ships, ask on other writes. Verified: frontmatter well-formed, hook decision paths smoke-tested (deny/ask/allow). NOT yet run in Cowork; skills not yet wired to dispatch to the agents (follow-up). Repo also moved to `~/code/work/inbound-cph-marketplace/`.

> **2026-07-01 — plugin consolidation.** The three plugins (`google-ads-setup`, `google-ads-optimization`, `google-ads-general`) were merged into a single plugin, **`inbound-ads`** (now v3.1.0), on branch `feat/inbound-ads-merge`. All 15 skills now live under `plugins/inbound-ads/skills/` (git history preserved via `git mv`). Install is now `/plugin install inbound-ads@inbound-cph`. The two former cross-plugin dependencies (`editor-csv-export` ← `campaign-build`/`optimering-loop`, and `annonce-optimering` ↔ `responsive-search-ads`) are now intra-plugin. Milestone/version notes below that name the old plugins are historical and describe the pre-merge layout.

## Milestones

### M1 — Plugin marketplace bootstrap
**Status:** Done

- Repo on GitHub (public): `CarlSvejstrup/inbound-cph-marketplace`
- `.claude-plugin/marketplace.json` valid
- `plugins/inbound-cph/.claude-plugin/plugin.json` valid
- Installable via `/plugin marketplace add CarlSvejstrup/inbound-cph-marketplace`
- Versioning: explicit semver, currently v0.9.0

### M2 — Core skills
**Status:** Done (5 skills currently on disk after a working-tree cleanup)

> Note (2026-05-29): the six original client-facing skills (`client-brief`, `proactivity-scan`, `weekly-pulse`, `voice-check`, `onboard`) were removed from the working tree in a separate cleanup and are not part of the current build. They remain recoverable from git history if needed. The five skills below are what ships now.

- `ads-audit` — full Google Ads paid search audit, outputs HTML slide deck + PDF (v0.4.0)
- `search-terms` — focused Google Ads search terms analysis for one client (v0.8.0). Read-only: pulls `search_term_view` via GAQL (cost-desc, ENABLED only, explicit BETWEEN window) with triggering keyword + match type; pulls the `keyword_view` map (test/duplicate campaigns filtered: `/w2m|test|vol 2/i`) for structural placement detection; pulls `ad_group_ad` for each ad group's final URL + top headlines for intent detection; scrapes the client's landing page via Firecrawl to ground relevance calls. Five buckets: **RELEVANT** (godt placeret, no action), **VINDER** (converts, not yet exact -> promote), **PLACEMENT_PROBLEM** with sub-types `struktur` (keyword exists in another production ad group) or `intent` (served ad group's ad/LP do not address the search intent), **IRRELEVANT** (not in the client's offering -> negative), **GRAENSE** (manual). Synthesises an import-ready negatives list. Output is an eight-tab colour-coded `.xlsx` built by `build-sheet.py` (openpyxl) — Placement-problem tab carries three extra columns (Placement-aarsag / Ad-group LP / Top annonce-tema). Uploaded via the Drive connector or saved locally — same xlsx mechanic as annoncetekster, no `gws`/Sheets API, runs in Cowork. The exact analysis window flows into Oversigt + filename. Taxonomy adopted from a field-tested user template (Dansk Studie Center); v0.7 added VINDER + landing-page grounding; v0.8 added dynamic period + intent half of PLACEMENT_PROBLEM + RELEVANT-as-no-action — all three forced by issues found in the live DSC test. GAQL fields (`segments.keyword.info.*`, `keyword_view`, `ad_group_ad.ad.responsive_search_ad.headlines`, `final_urls`, ctr-as-fraction, GAQL `LAST_90_DAYS`-is-not-a-literal) and micros/grain handling verified against a live account; `build-sheet.py` smoke-tested across all eight tabs incl. extra columns. Not yet run end-to-end against a full real account with the Firecrawl + LLM + intent passes.
- `annoncetekster` (renamed from `rsa-copy`) — landing page to Editor-ready RSA ad-copy sheet (v0.5.0). Builds a fresh `.xlsx` each run from a bundled `template.xlsx` (generated by `build-template.py`, openpyxl) that carries live `=LEN()` formulas + red over-length conditional formatting; `fill-sheet.py` fills only the text cells (15 headlines + 4 descriptions + 2 paths) under Google's hard limits (30/90/15) and validates lengths. Saves to Drive via the connector's `create_file` (user picks folder via `parentId`) OR locally. Danish-by-default output. Runs in Cowork AND locally — no `gws`, no clone, no Sheets API; scripts self-bootstrap openpyxl so it works on any machine. Verified end-to-end: template build, fill + length-guard, and Drive upload round-trip keeping `=LEN()` live.
- `responsive-search-ads` — higher-quality RSA copy: extended intake (USP hierarchy, active offer + expiry, trust numbers, brand voice/banned words, top keywords from MCP), an optional **Trin 2.5** that learns *messaging* from the client's top ENABLED RSAs via `run_custom_gaql` (commit `1f811cc`) with a strict messaging-vs-formatting firewall (inherit USPs/hooks/CTA phrasing, never casing/length/keyword-density — `headline-craft.md` + script gates win), and enforced write rules from `references/headline-craft.md`. `fill-sheet.py` hard-gates length limits + a quality gate (≥4 short headlines, no near-dupes). Same Cowork-native xlsx mechanic as `annoncetekster`.
- `annonce-optimering` — post-launch RSA **asset-hygiene diagnostic** (read-only, recommend-only). Pulls per-asset data via `run_custom_gaql` on `ad_group_ad_asset_view` (ENABLED only) + an `ad_group_ad` RSA count. Reports structural facts that hold without significance: champion-challenger coverage (ad groups with <2 RSA → build a challenger), dead-weight assets (never-served / sub-`MIN_IMPRESSIONS` impressions), and angle-coverage gaps per ad group → a **gap-brief** fed back into `responsive-search-ads` (closes the build→operate→iterate loop). **Deliberately NOT a Winners/Hidden Gems/Money Pits/Losers matrix:** a live test (2026-05-29, DSC `3069826320` + a high-volume account) proved Google's `performance_label` is always NOT_APPLICABLE/PENDING on Inbound's low-volume accounts, and per-asset CTR/CVR is confounded (an RSA attributes the same click/conversion to every served asset → impossible 68% per-asset CTRs) and far below significance. So Google's label is shown only when BEST/GOOD/LOW (else "ikke nok data endnu"), and any CVR hint is gated behind a hard significance floor (else "utilstrækkelig data"). Four-tab colour-coded `.xlsx` via `build-sheet.py` (openpyxl, self-bootstrap), Drive or local. GAQL field shape verified live; `LAST_90_DAYS`-isn't-a-literal (use BETWEEN) reconfirmed. `build-sheet.py` smoke-tested across all four tabs incl. label-masking. Not yet run end-to-end against a full account with the angle-classification pass.
- `ads-aendringslog` — **changelog generator from Google Ads' own change-history** (read-only against Ads; does NOT write to Drive). Added 2026-06-05 (google-ads-optimization v1.1.0). Two modes: **per customer** (all `change_event`s on one account in a window) and **per person** (filter `change_event.user_email` server-side across the specialist's accounts, fan out to each touched client's changelog). Collapses bulk-save noise (events sharing one timestamp+resource-type = one Editor action → "tilføjede negativ-liste (557 ord)", not 557 lines), preserves the actor verbatim (incl. external agencies, Google Recommendations, system bulk), and appends a `_Hvorfor:_` placeholder since `change_event` carries *what* not *why*. **Delivery is draft-to-paste, not write-back:** the Drive connector exposes only `create_file` (new file) / `copy_file` — no append/update tool for an existing Doc — so the skill resolves the client's changelog Doc (search by name pattern, confirm name+ID+path with the human), reads its style, and hands back a format-matched block (reverse-chron, `## Måned ÅÅÅÅ` header, `DD.MM.ÅÅÅÅ`, Danish, non-primary author in parens) for the human to paste newest-first. Built to run on a schedule (daily/weekly) because `change_event` only spans ~30 days (`lookback_days` ≤ 29; empty window ≠ inactive). Verified live during design: user-email filter works server-side (negative test: filtering Capio for an absent user returned `[]`), bulk-collapse confirmed (Rikke's week = ~973 raw events → ~51 distinct actions; Lime SE's 561 events = 1 paste), 30-day ceiling confirmed (`lookback_days=30` → `START_DATE_TOO_OLD`). Connector write-tool surface confirmed (no Drive append/update). SKILL.md + SPEC.md written; not yet dry-run end-to-end inside Cowork against a live changelog Doc.

### M3 — Operating contract
**Status:** Done

- Plugin-root `CLAUDE.md` with: write-gate, Drive access (with default folder ID), source attribution rules, language/tone rules, workspace shape
- Local `CLAUDE.md.template` inlines essentials so workspace free-form chat also has them
- Three `context/*.md` files (`about-inbound`, `drive-map`, `voice-house-style`)

### M4 — User docs and onboarding
**Status:** Done

- `onboard` skill (3-step Danish flow with one ja/nej)
- `guide.docx` generated from `guide.md` via `scripts/build-guide.sh` (pandoc)
- Workspace-agnostic — onboard treats cwd as general working hub across multiple clients

### M5 — Drive integration
**Status:** Partial

- Plugin uses Cowork's built-in `mcp__claude_ai_Google_Drive__*` connector
- `userConfig.inbound_root_folder_id` declared with default
- Skills declare Trin 1 (verify Drive) before working
- **Not tested end-to-end against a real client folder in Cowork.** Need to confirm the userConfig is actually prompted on install, the folder ID is read correctly by skills, and Drive search/read works as expected.
- No fallback if Drive is unreachable beyond "stop and ask user to log in"

### M6 — Source attribution
**Status:** Done

- Plugin CLAUDE.md `## Source attribution` section defines the canonical format
- All four content skills require `## Kilder` block at end of output
- Example outputs in each skill include sample Kilder blocks

## Open work / backlog

### High priority

- **End-to-end test in Cowork against Nordkap folder.** Confirm: marketplace install, userConfig prompt, Drive read, source attribution appears, language defaults to Danish. Until this is done, M5 is theoretical.
- **Decide versioning mode.** Explicit semver vs commit-SHA. Document choice in README.
- **Pilot `kontekst-opdater` (google-ads-general) on Dantaxi + Capio.** New skill (added 2026-06-24): per-client AI-context update + PM-overview, all on Drive — start in the master index, open the client's AI-Context file, diff what's new since its `Sidst opdateret` (Drive docs / HubSpot / status decks) with TILFØJ/ERSTAT/FJERN HITL-gating, write the updated AI-Context file in place. Untested end-to-end. Verify: index entry-point read, parallel source subagents, report folder find-then-note-in-file, `Sidst opdateret` watermark read+bump, and the gws-or-fallback file write. Known blocker: the gws/Workspace MCP (`acc7a973-…`) needed for the in-place file write is currently `needs_reauth` + personal-auth (may 403 on Inbound files) — the skill degrades to a copy-paste block until that's resolved.

### Medium priority

- **Clean up `docs/CONTRIBUTING.md` and `docs/PUBLISHING.md`.** Pre-plugin era, currently misleading. Either rewrite or delete; the README and this status doc cover most of what they tried to.
- **Add a `_template/` skill** so authors copying the structure for a new skill have a starting point. Should include the standard Trin 0 / Trin 1 / Kilder boilerplate.
- **Consider splitting marketplace.json from plugin** if more plugins ship later (e.g. inbound-internal vs inbound-client). Currently a single-plugin marketplace.

### Low priority / future

- `/inbound-cph:capture` — lightweight append-to-memory after meetings (mentioned in README roadmap)
- `/inbound-cph:monthly-report` — graduate the `inbound-report` skill into this plugin
- `/inbound-cph:competitive-pulse` — Semrush + Ahrefs delta on competitor keyword movement
- `/inbound-cph:meeting-prep` — pre-call kit (calendar event + last 3 meeting notes + open decisions)
- `/inbound-cph:decision-log` — capture a decision with structured frontmatter, propose write to `06-decisions/`

### Out of scope (for now)

- Scaffolding new client Drive folders (data hygiene problem, belongs in onboarding ops, not the agent)
- Drive write-back beyond `client-memory.md` appends (e.g. creating new meeting notes from chat) — wait until M5 is solid
- Multi-marketplace setup, dependencies on other plugins, MCP servers bundled in-plugin

## Repo hygiene

- `.gitignore` excludes `.DS_Store` and `.claude/` (local Claude Code workspace dir)
- `clients/nordkap-friluft/output/*.pptx` — demo output, not part of plugin, stays in repo for reference
- Pandoc required for guide.docx rebuild (`brew install pandoc`)
- README updated 2026-04-27 to cover v0.4.0 (Drive integration, source attribution, version flow)

## Versioning history

| Version | Date | Highlights |
|---|---|---|
| 0.1.0 | 2026-04-26 | Initial plugin packaging |
| 0.2.0 | 2026-04-27 | voice-check, onboard, context files |
| 0.2.1 | 2026-04-27 | Doc clarification on CLAUDE.md loading |
| 0.3.0 | 2026-04-27 | Danish default, conversational onboard, guide.docx |
| 0.3.1 | 2026-04-27 | Collapsed onboard, userConfig for Drive folder |
| 0.3.2 | 2026-04-27 | Workspace-agnostic onboard, ja/nej |
| 0.4.0 | 2026-04-27 | Source attribution + reliable context loading |
