# Session handoff — 2026-04-27 (evening update)

## Current state

- **Branch:** main, all changes pushed.
- **Latest version:** v0.4.0 (commit `9a3ba03`).
- **Repo:** https://github.com/CarlSvejstrup/inbound-cph-demo (public).
- **Plugin marketplace:** live, installable via `/plugin marketplace add CarlSvejstrup/inbound-cph-demo`.

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
cd ~/code/personal/inbound-cph-demo
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
