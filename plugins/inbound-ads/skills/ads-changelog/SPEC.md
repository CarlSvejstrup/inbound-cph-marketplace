# ads-changelog - design rationale

Companion to `SKILL.md` (the runnable contract). This file is the why.

## Problem

Inbound's ads team keeps a manual changelog/optimeringslog per client on Drive. It's valuable - it carries the *why* and the off-platform work (mails, meetings, sheets) - but its completeness depends entirely on the specialist remembering to write it. The factual half ("changed budget on 7 campaigns, added 557 negatives") is tedious to reconstruct from memory and often gets compressed to "budgettjek" or skipped.

Google Ads already records every account mutation in its `change_event` resource (the **Tools → Change history** panel). This skill turns that into a pre-filled changelog entry, so the human's job shrinks from *reconstruct what I clicked* to *add why + paste*.

## Why two modes

- **Per customer** answers "what happened on this account this week" - the natural unit of the existing changelog (one doc per client).
- **Per person** answers "what did Caroline/Rikke change across her whole book" - a manager/oversight view, and a faster way for one specialist to log a week that spanned many accounts. It fans out to each touched client's doc, so the per-client changelogs stay the source of truth either way.

Both converge on per-client changelog entries. Per-person is just a different entry point that loops the person's accounts and filters each by their email.

## Three findings from the live runs that shaped the contract

1. **30-day ceiling is real and load-bearing.** `change_event` rejects `lookback_days = 30` with `START_DATE_TOO_OLD`; 29 is the max. There is no API path to older history. This is the *one* place the API is strictly worse than the Drive changelog (which has full history back to last November). Consequence: this is a scheduled-snapshot tool, not a backfill tool. Run it weekly/daily so changes are captured before they age out.

2. **Bulk-save noise is ~20x.** On Lime SE, Rikke's "561 changes" were a single negative-keyword paste - all 561 events share one timestamp. Across her week, ~973 raw events collapsed to ~51 real actions. Reporting raw counts would massively overstate effort and make the entry unreadable. The skill collapses on (timestamp, resource_type) and reports "added negative-keyword list (N terms)".

3. **The user filter works server-side.** Verified with a negative test: filtering Capio (100% Caroline) for Rikke's email returned empty, while Caroline's filter returned her rows. So "what did person X do" is a genuine GAQL query, not client-side guessing. Confirmed it correctly excludes client-made and agency-made changes (Light-Point was edited by the client's own login that week; it stayed out of Rikke's digest).

## Why draft-to-paste, not write-back

The Google Drive connector exposes `create_file` (new file only - no `fileId` to target an existing doc) and `copy_file`. There is **no append/update/insert tool** for Drive (only Slack canvas has one). So in-place append to the existing changelog Doc is impossible through current tooling.

Even if a write-back existed, `read_file_content` returns "a natural language representation" whose format is explicitly not stable, so you can't safely round-trip a formatted Doc through read → reconstruct → overwrite without flattening it. Draft-to-paste sidesteps both problems and is fully human-in-the-loop compliant: the heavy lifting is automated, the human pastes.

If the connector ever gains an append/update tool, Trin 6 upgrades to the gated four-step write (show target doc + block, wait for explicit approval, write, confirm). The contract is written so that's a localized change.

## Why format-match instead of a clean template

The changelog is a living human doc with an established style (reverse-chronological, `## Juni 2026` headers, `DD.MM.YYYY` entries, Danish, non-primary authors annotated in parentheses). Imposing a new format would make the auto-entries visually foreign and create friction at paste time. The skill reads the doc first, matches its style, and inserts newest-first under the current month.

## Doc resolution is the risk surface

There is no single canonical changelog location - across clients it's been seen inside Paid Search, under the legacy "Google/Bing Ads" name, under "#4 - Google Ads", and at folder top-level. The skill can't read the vault's `changelog_file` IDs (it runs in Cowork, not the vault), so it resolves by searching the client folder for the doc by name pattern, and **confirms the resolved doc (name + ID + path) with the human before drafting**. A misresolved doc is the failure mode that would corrupt a client's log, so the gate shows the target, not just the entry.

## Scope discipline

Per-person defaults to the person's *own* accounts (from the `responsible` mapping), not all 200+ in the MCC - it keeps the loop small and matches the intent ("their book"). The exhaustive variant (all accounts filtered by email) exists for the rare case of catching changes a person made on an account they don't formally own; it's opt-in because it's a much larger loop.
