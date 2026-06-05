# inbound-cph-marketplace

Claude Code / Cowork plugin marketplace for Inbound CPH's Google Ads work. Ships **two plugins**, installed per user and updated via `/plugin update`:

- **`google-ads-setup`** — build a NEW Google Ads campaign end-to-end (research → structure → creative → assembled review workbook + Editor CSVs).
- **`google-ads-optimization`** — optimize a LIVE Google Ads account (paid-search audit, post-launch RSA asset-hygiene, search-terms analysis + negative-keyword mining).

Both share one operating contract (`CLAUDE.md`) and company context (`context/`). Everything is **read-only / recommend-only against Google Ads** — no skill writes to an account; humans import the artifacts after approval.

## Install

In Cowork (or any Claude Code surface), add the marketplace once, then install whichever plugin(s) you need:

```
/plugin marketplace add CarlSvejstrup/inbound-cph-marketplace
/plugin install google-ads-setup@inbound-cph
/plugin install google-ads-optimization@inbound-cph
```

The marketplace is named `inbound-cph`, so the install syntax is `<plugin>@inbound-cph`. Install both for the full build→operate→iterate loop (the `annonce-optimering` → `responsive-search-ads` gap-brief loop spans the two plugins via manual paste, so both must be present to close it).

## Skills shipped

### google-ads-setup (9 skills) — build a new campaign

| Skill | Purpose |
|---|---|
| `landing-page-analyzer` | Scrape a landing page → structured positioning JSON (USPs, tone, CTAs, trust, offer) |
| `competitor-research` | Competitor positioning from their own pages → differentiator list + "sea of sameness" map |
| `campaign-strategy` | Campaign settings (type, geo, networks, bidding, budget, tracking gate) as a decision object |
| `semrush-research` | **Gated** — keyword volume/difficulty/CPC + organic rankings + trends from Semrush MCP; degrades to theme-derived when no Semrush plan is connected |
| `structuring` | The Phase-2 gate: ad groups + keyword selection (Exact/Phrase) + client-specific negatives |
| `rsa-copywriter` | Writes RSAs for every ad group by reusing `responsive-search-ads` per group |
| `assets` | Sitelinks, callouts, structured snippets (lead forms are a manual UI step) |
| `assembler` | Merges all the above into Ian's 10-tab review workbook + per-entity Editor CSVs (no API push) |
| `responsive-search-ads` | The RSA copy engine: one ad group → an Editor-ready sheet with live `=LEN()` guards |

### google-ads-optimization (3 skills) — optimize a live account

| Skill | Purpose |
|---|---|
| `ads-audit` | Full paid-search audit → polished HTML slide deck + PDF |
| `annonce-optimering` | Post-launch RSA asset-hygiene diagnosis (champion-challenger coverage, dead-weight assets) → gap-brief |
| `search-terms` | Search-terms-report analysis → colour-coded sheet + import-ready negative-keyword list |

## Data integration

- **Google Ads MCP** — read-only. Live account data (campaigns, keywords, search terms, RSA assets, the MCC shared negative list). No writes, no API push.
- **Firecrawl** — landing-page + competitor scraping.
- **Drive connector** — Cowork's built-in `mcp__claude_ai_Google_Drive__*`; each user authorises once. Drive root via `userConfig.inbound_root_folder_id` in each `plugin.json`.
- **Semrush MCP** — optional, plan-gated; `semrush-research` uses it when available and degrades cleanly otherwise.

## Philosophy

**Hard rule: human-in-the-loop on every write.** Every skill stops at "here's the draft/artifact, confirm to apply." No skill pushes to a Google Ads account; the campaign-build output is a workbook + CSVs a human imports into Google Ads Editor after approval. The operating contract is in each plugin's `CLAUDE.md`, loaded automatically when a skill runs.

**Reading is free, writing is gated.** Skills read aggressively (Drive, Google Ads MCP, the web) without asking. Approval is required only at the moment bytes leave the agent.

**Skills are code.** Version-controlled, reviewed, distributed via the plugin update flow.

## Repo structure

```
.claude-plugin/
  marketplace.json                # marketplace "inbound-cph", lists both plugins
plugins/
  google-ads-setup/
    .claude-plugin/plugin.json
    CLAUDE.md                     # shared operating contract
    context/                      # about-inbound, drive-map, voice-house-style
    skills/                       # the 9 setup skills (see table above)
  google-ads-optimization/
    .claude-plugin/plugin.json
    CLAUDE.md                     # same contract (copy)
    context/
    skills/                       # ads-audit, annonce-optimering, search-terms
docs/
  project-status.md, session-handoff.md, ...
```

## Versioning + update flow

Each plugin uses **explicit semver** in its `plugin.json`. Bump it every time you ship changes to that plugin — pushing without bumping does nothing for users (Claude Code compares version strings, not SHAs).

After bumping and pushing:

1. Users open Cowork → marketplace panel.
2. Click `...` next to the **`inbound-cph`** marketplace → Refresh.
3. The relevant plugin's "Update" button lights up → click.

If marketplace metadata is stuck, the nuke-and-reinstall path:

```
/plugin marketplace remove inbound-cph
/plugin marketplace add CarlSvejstrup/inbound-cph-marketplace
/plugin install google-ads-setup@inbound-cph
/plugin install google-ads-optimization@inbound-cph
```

## Adding or editing a skill

```bash
# 1. Create the skill directory in the right plugin
mkdir -p plugins/<plugin>/skills/<skill-name>
# 2. Write SKILL.md (frontmatter: name, description; body: when-to-use, inputs, what-to-produce, rules)
# 3. Bump plugins/<plugin>/.claude-plugin/plugin.json version
# 4. Commit, push
# 5. Refresh marketplace + update in Cowork to test
```

Skill format follows Anthropic's universal SKILL.md spec; works across Cowork, Claude Code, Cursor, Codex.

## Cross-plugin note

`${CLAUDE_PLUGIN_ROOT}` resolves to a single plugin's directory, so a skill cannot reference files in a sibling plugin. That's why `responsive-search-ads` (the RSA engine that `rsa-copywriter` + `assembler` depend on in code) lives in `google-ads-setup` alongside its dependents. The `annonce-optimering` ↔ `responsive-search-ads` gap-brief loop crosses the plugin boundary, but it's manual paste (no code coupling), so it works as long as both plugins are installed.

## Language and tone

Defaults to **Danish** for user interaction. English preserved for marketing/tool vocabulary (SEO, ROAS, GA4, RSA, etc.). AI/ML jargon avoided when explaining the system — users are marketers, not engineers. Full rules in each plugin's `CLAUDE.md`.
