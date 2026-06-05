# Session handoff — 2026-06-05 (optimization-loop build)

## Current state (2026-06-05, end of session)

- **Branch:** `feat/optimization-loop` (NOT merged to main, NOT pushed). Commits `76eb7e3`,
  `e5236c3`, `39b9aed`, `fe514cd`.
- **Marketplace:** 3 plugins — `google-ads-setup` (9 skills), `google-ads-optimization`
  (2 skills), `google-ads-general` (2 skills). Repo
  https://github.com/CarlSvejstrup/inbound-cph-marketplace.
- **Built this session — the optimization loop** (`workflows/optimization-loop/`): a *local*
  Claude Code Workflow (NOT a Cowork plugin) that diagnoses a live account in parallel and
  produces ONE editable Excel workbook. Recommend-only.

### Optimization-loop build status

- **DONE + verified (unit):** the shared lib —
  - `lib/builders/load.py`: by-path loader of the skills' own `build()`, output cell-identical
    to their CLIs; RSA length/quality gates fire through it. **Skills NOT modified.**
  - `lib/gaql/*`: live-verified queries + the `LAST_90_DAYS`-isn't-a-literal guard.
  - `lib/gaql/quality_score.py` + `change_events.py`: verified against live DSC. QS is
    keyword-grain; change-history bulk-collapse + ≤29-day clamp verified.
  - `lib/builders/review_workbook.py`: the ONE editable `.xlsx` (Editor-header columns +
    metadata band + `#Original` for edit rows). Verified: account-level negative → blank
    Campaign; winners → Exact/Paused; `#Original` only on edit rows.
  - `SPEC.md` is the design contract; §3.5b is the column contract the converter is built on.
- **DONE + PASSED (workflow):** `smoke.workflow.js` proved the agent→Bash/MCP→schema-JSON
  pattern against live DSC (3069826320) — real analysis: 8 negatives (incl. a struktur
  self-competition finding on `grupperejser`), 6 winners, significance gate fired (601 conv →
  low_confidence=false). Saved as `fixtures/dsc-smoke-search-terms.json`.
- **PARTIAL (full run `wf_b215523d-8ef`):** launched 4 parallel diagnostics; **2 of 4 journaled
  a result before the session moved on** — QS (avg 6.4, 20 flagged keywords, matches the live
  probe) and measure (correct `is_baseline_run: true`). search-terms + asset-hygiene + the
  execute stage did NOT finish. **And that run used the OLD CSV execute stage** (pre-refactor),
  so its execute output is superseded regardless. The QS + measure stages are now validated
  through the real workflow, not just unit tests.
- **ARCHITECTURE CHANGE late in session (commit `fe514cd`):** the loop returns ONE editable
  Excel workbook, NOT CSVs (Carl's call: experts must edit + send to client before import). A
  separate converter skill (to be built in `google-ads-general`) does workbook → Editor CSV.
  The assembler was already Excel-only (`eb4ebd9`) and was NOT touched.

### The parked unknown

A full `loop.workflow.js` run that reaches the **execute stage and writes the workbook** has not
happened yet (the one full run predates the Excel refactor and didn't finish execute). That
end-to-end run — diagnostics → workbook with the right tabs/columns/`#Original` — is THE thing to
verify next. Re-run fresh (see `README.md`); the diagnostics are cheap to re-run.

### Next session — TWO tracks (Carl, 2026-06-05)

**Track 1 — SETUP (the one Carl most wants to nail).** The `google-ads-setup` campaign-build
suite. Goals:
- **Make it actually work end-to-end** — the live Cowork run is still the parked unknown for the
  build suite too.
- **Compare against what Ian built.** Ian sent a skill / something he created. Pull it, read it,
  and benchmark our setup flow against his — what does he do better, what do we, what to merge.
- **User-friendliness + UI.** Think about a UI layer (Ian made something here). Make the
  build flow less raw-skill, more guided.
- **The customer part.** Ian's thing includes a customer-facing piece. Figure out what the
  customer side of setup looks like for us.

**Track 2 — OPTIMIZATION (dial in + test).** The loop built this session. Goals:
- **Run it end-to-end** and see the workbook output (the parked unknown above).
- **Find what works / what doesn't** on a real account, and **where to optimize** the loop
  itself.
- Build the **workbook → Editor CSV converter skill** in `google-ads-general` (SPEC §3.5b is its
  interface; preserve `*#Original` columns, drop the metadata band).
- Then a **second run with `prior_run_dir`** set, to exercise the measure stage's
  proposed/applied/did-it-move comparison (not just baseline).

**Plumbing:** decide merge of `feat/optimization-loop` → main once the workbook run is verified;
refresh the stale M-series sections below + `docs/project-status.md` for the 3-plugin reality.

---

## Historical handoff — 2026-04-27 (v0.4.0, single-plugin era — STALE, kept for history)

- **Branch:** main, all changes pushed.
- **Latest version:** v0.4.0 (commit `9a3ba03`).
- **Repo:** https://github.com/CarlSvejstrup/inbound-cph-marketplace (public).
- **Plugin marketplace:** live, installable via `/plugin marketplace add CarlSvejstrup/inbound-cph-marketplace`.

## What changed this session

Started: a flat `skills/` repo with 3 SKILL.md files and stale tooling assumptions.

Shipped, in order:

1. **v0.1.0** — packaged as Claude Code plugin + marketplace. Added `.claude-plugin/marketplace.json`, `plugin.json`. GitHub repo created, public.
2. **v0.2.0** — added `voice-check` and `onboard` skills, plugin-root `CLAUDE.md` (operating contract), three context files (`about-inbound.md`, `drive-map.md`, `voice-house-style.md`).
3. **v0.2.1** — clarified that plugin CLAUDE.md is loaded via skills + local pointer, not auto-loaded by Cowork itself.
4. **v0.3.0** — Danish-default language rules, no AI/ML jargon, conversational onboard flow, guide.docx generated from markdown via `scripts/build-guide.sh` (pandoc).
5. **v0.3.1** — collapsed onboard from 7 steps to 3, added `userConfig.inbound_root_folder_id` for Drive scoping, drive-map updated to specify Cowork's built-in Drive connector.
6. **v0.3.2** — workspace-agnostic onboard. Dropped `01-brand/` detection. Cwd treated as general working hub across multiple clients (client data lives in Drive). ja/nej everywhere.
7. **v0.4.0** — Source attribution requirement: every skill output that synthesises from Drive must end with a `## Kilder` section. Every skill gets Trin 0 (load plugin CLAUDE.md) and Trin 1 (verify Drive). Local CLAUDE.md template inlines essential rules so free-form chat in workspace also gets context (not just skill invocations).

## How the plugin currently works

- **Marketplace manifest** at `.claude-plugin/marketplace.json` points to `./plugins/inbound-cph` as a single plugin.
- **Plugin** lives at `plugins/inbound-cph/` with: `CLAUDE.md` (operating contract), `context/` (3 files), `skills/` (5 skills), `.claude-plugin/plugin.json`.
- **Skills:** `client-brief`, `proactivity-scan`, `weekly-pulse`, `voice-check`, `onboard`.
- **Drive access:** via Cowork's built-in `mcp__claude_ai_Google_Drive__*`, scoped by `userConfig.inbound_root_folder_id` (default `17JwnWKToZSJUSCURjS9PzzBeqe6_gPfi`).
- **Language:** Danish default, English for marketing/tool terms, no AI/ML jargon when explaining the system.

## Architecture research — shared cloud layer (2026-04-27 evening)

**Problem:** Cowork's built-in Drive MCP is the bottleneck — slow appends, not conflict-safe, not bash-friendly. Affects `client-memory.md` most (every weekly-pulse and proactivity-scan appends). 17 specialists, mostly markdown, also occasional decks/PDFs, EU/GDPR required, must coexist with Google Workspace.

**Researched 6 options.** Compared on per-user setup time, latency, bash-friendliness, multi-user write conflicts, GW coexistence, cost, GDPR.

**Recommendation:** **keep Drive as canonical, ship a tiny EU-hosted append-helper service.**

- Cloudflare Worker (or Cloud Run, `europe-west1`) with one Google service account that has Editor on the Inbound Drive root.
- Endpoints: `POST /append`, `POST /prepend`, `GET /read`, `GET /grep` (server-side ripgrep over fetched cache).
- ETag-based conflict resolution (read-modify-write with `If-Match`, retry on 412).
- 60s in-memory read cache per file path so multi-skill sessions don't hit Drive repeatedly.
- Plugin skills call helper for writes; keep Drive MCP for ad-hoc reads initially.
- ~200 lines of Python, ~1 day to build, ~$5/mo (Workers free tier likely free).
- Onboarding stays one step: helper URL + shared API key baked into plugin config.

**Rejected and why:**

- **rclone/Dropbox mount per user:** sync lag (5-30s) + last-writer-wins silently corrupts `client-memory.md`. Failure mode invisible until quarter later when a permanent note vanishes.
- **Git for client data:** marketers can't resolve merge conflicts. Non-starter.
- **Notion / Obsidian Sync / Anytype:** fragments institutional memory across two systems; team keeps using Drive anyway. Two sources of truth = none.
- **Cloudflare R2 / S3 / Supabase Storage:** no native append; would need to rebuild the helper layer anyway. Skip.
- **GitHub Enterprise (for EU residency):** $21/user/mo = $357/mo for 17 users. Marketers still won't use git.

**Contrarian alternative if rejecting #1:** hybrid by domain. Skills + shared rules in git (already done via the plugin marketplace). Client memory stays in Drive + helper. Two substrates, each playing to its strength.

**Do NOT do:**

- rclone-mount Drive per user (silent corruption)
- Migrate client data to Notion / Obsidian (two sources of truth)
- Hand marketers git for memory updates
- Object storage without locking (rebuilds the helper badly)
- Wait for a "perfect" MCP — the helper is 200 lines, ship it Monday

**Status:** logged in `~/svejstrup-os/backlog/inbound-cph.md` under `## Decisions needed`. Not yet decided. No code written for the helper.

## Suggested next tasks

See `docs/project-status.md` for the full backlog. Top three for the next session:

1. **Test v0.4.0 end-to-end in Cowork** with a real client folder. Verify the `## Kilder` section actually appears, the Drive folder ID is picked up via userConfig, and free-form chat in the workspace honours the local CLAUDE.md.
2. **Decide on the cloud layer** (see Architecture research above). If green-lighting the helper, scope is ~1 day: Cloudflare Worker + service account + ETag-based append.
3. **Decide explicit-version vs commit-SHA mode.** Currently using explicit semver (need to bump every change). For a moving demo, commit-SHA might be lower-friction.
4. **Clean up stale docs** — `docs/CONTRIBUTING.md` and `docs/PUBLISHING.md` describe the pre-plugin sync-script flow.

## Resume commands

```bash
cd ~/code/personal/inbound-cph-marketplace
git status
git log --oneline -10
cat plugins/inbound-cph/.claude-plugin/plugin.json   # current version
```

To bump and ship a new version:

```bash
# 1. Edit files
# 2. Bump version in plugins/inbound-cph/.claude-plugin/plugin.json
# 3. If guide changed: ./scripts/build-guide.sh
# 4. Commit + push
# 5. In Cowork: marketplace ... → Refresh; plugin → Update
```

## Caveats / blockers

- **Marketplace UI sync is manual.** No background polling. Users must click `...` → Refresh on the marketplace card before the plugin's Update button enables. Documented in README.
- **Plugin CLAUDE.md not auto-loaded for free-form chat.** Worked around in v0.4.0 by inlining essentials into the local CLAUDE.md template, but anyone who installed before v0.4.0 and skipped `onboard` won't have the Drive root ID loaded automatically.
- **`docs/CONTRIBUTING.md` and `docs/PUBLISHING.md` are stale** (pre-plugin era). Don't follow them.
- **Cloud layer decision is open.** See Architecture research section. Affects whether v0.5.x can credibly ship faster `client-memory.md` writes.
