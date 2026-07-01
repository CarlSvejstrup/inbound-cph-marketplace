# Hooks — Google Ads write guardrail

`google-ads-write-guardrail.sh` is a **PreToolUse** hook: the hard safety layer under the
`ads-writer` agent. It intercepts every Google Ads MCP tool call and decides allow / ask / deny
by the tool's **short name** (the suffix after the last `__`), so it works regardless of the
per-install MCP connector UUID prefix (`mcp__<uuid>__<toolname>`).

## Policy

| Tool class | Decision |
|---|---|
| Budget writes (`update_campaign_budget`, `create_campaign_budget`) | **deny** while the budget-guardrail is unshipped; **ask** (second confirm, any size) once shipped |
| Other account writes (add/update/remove/create/apply/dismiss/set/link/upload) | **ask** — mandatory per-action human confirmation |
| Reads, `generate_campaign_build_csv`, non-Ads tools | **allow** (fall through) |

This reinforces the `ads-writer` prompt; it is never the only gate. It also protects against a
write attempted from anywhere else (a skill, a stray call), not just the writer agent.

## Enabling it

Wired in this repo's `.claude/settings.json` via a broad `mcp__.*__.*` matcher (the script does the
suffix decision). When running skills from this repo with Claude Code, it is active automatically.

**For distributed seats (Cowork / other machines):** plugin-bundled agents cannot carry hooks, so a
seat that will perform Google Ads writes must enable this hook in its own settings — point a
PreToolUse `mcp__.*__.*` matcher at this script. Read-only use (the `ads-analyst` / `drive-knowledge`
paths) does not require the hook.

## Flipping the budget guardrail on

Budget writes stay **blocked** until the budget-guardrail (summer backlog item 1) ships. When it
does, set the env var so budget writes switch from `deny` to `ask` (still a second explicit confirm):

```
INBOUND_ADS_BUDGET_GUARDRAIL=1
```

Leave it unset until the guardrail is actually in place.
