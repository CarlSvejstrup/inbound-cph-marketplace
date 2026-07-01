#!/usr/bin/env bash
# PreToolUse guardrail for Google Ads writes (Inbound CPH inbound-ads plugin).
#
# The hard, install-portable safety layer under the ads-writer agent. It matches on the
# tool's SHORT name (suffix), so it works regardless of the per-install MCP server UUID
# prefix (mcp__<uuid>__<toolname>). Reinforces the ads-writer prompt; never the only gate.
#
# Contract (Claude Code PreToolUse):
#   stdin  = JSON envelope with .tool_name and .tool_input
#   stdout = {"hookSpecificOutput":{"hookEventName":"PreToolUse",
#             "permissionDecision":"deny|ask|allow","permissionDecisionReason":"..."}}
#   exit 0 with that JSON drives the decision. Non-write tools fall through (allow).
#
# Policy (matches Carl's 2026-06-19 direction):
#   - BUDGET writes: HELD/blocked until the budget-guardrail ships. Toggle with the
#     INBOUND_ADS_BUDGET_GUARDRAIL env var (unset/"0" = held; "1" = shipped -> ask, so the
#     human still confirms every budget change of any size).
#   - OTHER account writes: "ask" -> Claude must surface the change and get explicit human
#     confirmation before it executes (the ads-writer protocol). Never auto-applied.
#   - Reads and non-Ads tools: allow (fall through).

set -euo pipefail

input="$(cat)"

# Extract tool name; degrade safely if jq is missing or input is malformed.
if command -v jq >/dev/null 2>&1; then
  tool_name="$(printf '%s' "$input" | jq -r '.tool_name // empty' 2>/dev/null || true)"
else
  # Minimal fallback: grep the tool_name value out of the JSON.
  tool_name="$(printf '%s' "$input" | sed -n 's/.*"tool_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
fi

# Nothing to inspect -> allow.
if [ -z "${tool_name:-}" ]; then
  exit 0
fi

# Short name = everything after the last "__" (handles mcp__<uuid>__toolname and bare names).
short="${tool_name##*__}"

emit() { # $1=decision  $2=reason
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"%s","permissionDecisionReason":"%s"}}\n' "$1" "$2"
  exit 0
}

# --- Budget writes: highest risk, held until the guardrail ships ---
case "$short" in
  update_campaign_budget|create_campaign_budget)
    if [ "${INBOUND_ADS_BUDGET_GUARDRAIL:-0}" = "1" ]; then
      emit "ask" "BUDGET WRITE ($short): every budget change requires a SECOND explicit human confirmation on top of the per-action gate. State old budget, new budget, and percentage change, then confirm the budget specifically before applying."
    else
      emit "deny" "BUDGET WRITE ($short) is BLOCKED: the budget-guardrail (summer backlog item 1) has not shipped. No budget change may be applied until it does. Non-budget writes are still available. Set INBOUND_ADS_BUDGET_GUARDRAIL=1 only once the guardrail is in place."
    fi
    ;;
esac

# --- Other account-mutating writes: require explicit human confirmation ---
case "$short" in
  add_keywords|add_negative_keywords|add_campaign_location_target|\
  remove_keyword|update_keyword|update_ad_status|update_ad_group_status|\
  update_ad_group_bid|update_campaign_status|update_campaign_bidding_strategy|\
  set_campaign_device_bid_modifier|create_campaign|create_ad_group|\
  create_responsive_search_ad|create_conversion_action|create_callout_assets|\
  create_sitelink_assets|create_structured_snippet_asset|link_assets_to_campaign|\
  apply_recommendation|dismiss_recommendation|upload_click_conversions)
    emit "ask" "GOOGLE ADS WRITE ($short): human-in-the-loop is mandatory. Restate the exact change (customer, entity, field, old -> new), show it as a proposal, and apply only after an explicit per-action confirmation. Route through the ads-writer agent."
    ;;
esac

# Everything else (reads, CSV generation, non-Ads tools) -> allow.
exit 0
