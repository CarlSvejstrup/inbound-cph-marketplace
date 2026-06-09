# Session handoff — 2026-06-09 (Excel→CSV converter shipped; loop made converter-ready)

## Current state (2026-06-09, end of session)

- **Branch:** `main` (commits `7b31bf1`, `6b0bc78`, `ceb59ca` — all on main, repo automation
  fast-forwards feature branches to main; orphaned `feat/*` branches are harmless leftovers).
  NOT manually pushed (`main == origin/main` was set by the automation; do not push by hand).
- **Marketplace:** 3 plugins — `google-ads-setup` (9 skills, v1.2.0), `google-ads-optimization`
  (2 skills), `google-ads-general` (**3 skills** now, v1.1.0). Repo
  https://github.com/CarlSvejstrup/inbound-cph-marketplace.

### Shipped + verified this session — `editor-csv-export` (the Excel→CSV converter)

A new **plugin skill** `plugins/google-ads-general/skills/editor-csv-export/` (this is the "build
another skill that turns Excel into CSV for Editor" Carl asked for). Pure transform: ONE confirmed
`.xlsx` in → up to 6 per-entity Editor import CSVs out. No API push, re-runs both hard guards.

- **Reads BOTH workbook dialects on one contract** (the key design win):
  - **assembler** (campaign-build, full new campaign) → 6 CSVs.
  - **optimization-loop** review workbook (subset) → 3 CSVs (negatives, keywords, ads).
  - `read_tab` matches tab names by alias (tolerant of `NN ` prefix). ≥1 entity tab required;
    campaign-settings no longer mandatory.
- **Target schema = assembler-contract §5** (traces to Ian's real skeleton, NOT the lossy public
  Editor docs). Negatives `Type` derived from `Level` (`Campaign negative` / `Negative`),
  bracket/quote negative form, `<Account-level>` for assets, UTF-8 BOM (Danish æ/ø/å).
- **Both §6 guards re-run at the converter boundary** (no Broad/blank positive keyword; recompute
  RSA 30/90/15) — verified to fire (exit 1, zero CSVs) on BOTH dialects.
- **Verified end-to-end** against a synthetic assembler workbook (6 CSVs, every §5 branch +
  both guards) AND a synthetic loop workbook (3 CSVs, account-level fan-out, no RSA `#Original`),
  with the assembler path unregressed. Contract + smoke invariants in
  `references/editor-csv-contract.md`.

### Loop changes this session (made the loop workbook converter-ready)

- `lib/builders/review_workbook.py`:
  - Negatives tab now speaks the **same vocabulary as the assembler's tab 04**
    (`Campaign / Level / Ad group / Negative keyword / Match type`) → one converter, no fork.
  - **Account-level negatives fan out** to one `Campaign negative` row per active campaign (pass
    `active_campaigns`) + a Laes-mig note offering the shared-list alternative (Editor CSV has no
    account level). Decision 2026-06-09.
  - **RSA-edit-in-place path REMOVED.** Every RSA is now a NET-NEW challenger (`Paused`).
    Rationale: editing a live RSA resets its learning (RSAs effectively immutable, SPEC §6.4), and
    Editor CSV can't reliably match an RSA → an `#Original` edit row risks a silent duplicate or
    clobbered headlines. The converter keeps a general `#Original` passthrough (correct for
    editable entities like a keyword's bid/URL) but the loop never emits one for RSAs.
- `SPEC.md` §3.5b / §4 / §6.4, `README.md`, `loop.workflow.js` execute prompt all updated to the
  net-new-RSA + fan-out reality.

### Still DONE from before (unchanged, still valid)

- `lib/gaql/*` (+ QS keyword-grain + change_events ≤29-day clamp) verified against live DSC.
- `smoke.workflow.js` PASSED against live DSC (3069826320).
- `lib/builders/load.py` (by-path loader) exists but is **DEAD CODE** — the Excel-refactor execute
  stage calls only `review_workbook.py`, never the loader. (This is what de-risked the loop→plugin
  port: no cross-plugin imports remain.)

### THE headline open item — the loop is still NOT a plugin

Carl's top ask this session was **"I want it as a plugin!"** The *converter* shipped as a plugin
skill ✅, but the **optimization loop itself is still `workflows/optimization-loop/`, a local Claude
Code Workflow — NOT a Cowork plugin.** This was a deliberate sequencing call (ship + verify the
converter first; port the loop after its end-to-end run clears), so it is **deferred, not done.**
Good news: the Excel refactor already removed the original blocker (the dead `load.py` cross-plugin
coupling), so the port is now realistic — a skill runs in the main loop and CAN spawn agents /
invoke skills, unlike a Workflow agent. Porting plan: move the `lib/` (gaql + review_workbook) into
a new `google-ads-optimization` skill, run the diagnostics sequentially or via sub-agents, bundle
`headline-craft.md`. **Port VALIDATED logic** — clear the two gates below first.

### Two trust gates before the loop runs on a live account

1. **The parked unknown (still open):** a full `loop.workflow.js` run that reaches the **execute
   stage and writes the workbook** has never completed. Drive `review_workbook.py` directly (pure
   function, seconds) to eyeball workbooks — done this session — but the full diagnostics→execute
   chain on a live account is unverified. Re-run fresh (see `README.md`); diagnostics are cheap.
2. **The Editor edit-row round-trip (NEW gate):** no CSV has been imported into real Editor yet.
   The honest acceptance test is one manual import. Because the converter's `#Original` passthrough
   is the riskiest piece, the round-trip must **specifically import an edit row** (not just net-new
   negatives/keywords) and confirm Editor matches + edits in place + does NOT clobber unspecified
   headlines. (The loop sidesteps this for RSAs by going net-new; it still matters if any future
   editable-entity tab uses `#Original`.) Also resolve the UNVERIFIED snippet-header CSV column
   name on the same round-trip.

### Next session — TWO tracks (Carl, 2026-06-05, still current)

**Track 1 — SETUP (the one Carl most wants to nail).** The `google-ads-setup` campaign-build suite.
- **Make it actually work end-to-end** — the live Cowork run is still the parked unknown here too.
- **Compare against what Ian built.** Pull Ian's skill, benchmark our setup flow against it.
- **User-friendliness + UI** (Ian made something here) + **the customer-facing part**.

**Track 2 — OPTIMIZATION (dial in + test).** The loop.
- **Port it to a plugin** (the headline item above) once validated.
- **Run it end-to-end** (gate 1) and the **Editor edit-row round-trip** (gate 2).
- **Find what works / what doesn't** on a real account; where to optimize the loop itself.
- Then a **second run with `prior_run_dir`** set, to exercise the measure stage's
  proposed/applied/did-it-move comparison (not just baseline).

**Plumbing:** refresh the stale M-series sections below + `docs/project-status.md` for the
3-plugin / converter reality.

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
