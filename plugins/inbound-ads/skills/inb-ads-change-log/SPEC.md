# inb-ads-change-log - design rationale

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

## Why it writes back (and how)

An earlier version of this skill delivered a copy-paste block, on the belief that the Drive tooling could only create new files. That was wrong for the Inbound Google Drive MCP (`mcp__acc7a973-...`), which exposes **`findAndReplaceInDoc`** - the same surgical inline write that `inb-ads-client-brief` already uses to maintain the AI-Context Docs. So the skill writes the entry directly into the client's changelog Doc, and copy-paste is now only the fallback.

Two constraints shape the mechanics:

1. **Native Google Doc only.** `findAndReplaceInDoc` cannot edit a raw `.md`, a `.docx`, or a Sheet. Trin 4 therefore verifies the mimetype before committing to a write, and falls back to copy-paste when the changelog isn't a native Doc. This is the same correctness dependency documented in `../../shared/ai-context-file-contract.md`.

2. **Replace, never insert.** `findAndReplaceInDoc` has no insert operation, so an insertion is expressed as replacing a unique anchor with "the new block + that anchor". The anchor ladder in Trin 6 (current month header → topmost month header → existing date line → title) covers the real shapes these Docs take, and every anchor is `dryRun`-verified to match exactly once before the real write. A non-unique anchor is the one way this could corrupt a log, so it is gated twice: unique-match verification, then the human's `ja`.

### Why not `insertText`

The connector *does* expose `insertText`, which inserts at an arbitrary position and would express the insertion directly instead of as an anchor replacement. It is deliberately not used: it takes a computed 1-based **index** into the Doc, and index arithmetic against a live client log is the failure mode that silently lands an entry mid-paragraph. The anchor-replace path is uglier to read but has no arithmetic in it at all — you name text that exists, and the tool finds it. Same reasoning excludes `updateGoogleDoc` (replaces the entire doc, i.e. deletes the log) and `updateDocFromMarkdown` (`replace` does the same; `append` lands at the END, but the changelog is reverse-chronological).

### Native bullets, applied after placement

The written entry uses real Google Docs bullets, not literal `- ` hyphens, because a hyphen typed into a Doc stays a hyphen and reads as sloppy next to the specialist's own formatting. `createParagraphBullets` does this natively and is also index-free — it targets paragraphs by `textToFind`. So the write is two calls: place the block as plain lines, then bulletize the action lines (never the date line or month header). Bulletizing is a formatting step on already-correct text, so a failure there is reported and left alone rather than triggering a rollback or the copy-paste fallback.

The old objection about `read_file_content` returning unstable "natural language representation" doesn't apply here, because nothing is round-tripped. The Doc is read only to learn its format and locate an anchor; the write touches that anchor and leaves the rest of the Doc untouched.

## Why format-match instead of a clean template

The changelog is a living human doc with an established style (reverse-chronological, `## Juni 2026` headers, `DD.MM.YYYY` entries, Danish, non-primary authors annotated in parentheses). Imposing a new format would make the auto-entries visually foreign and create friction at paste time. The skill reads the doc first, matches its style, and inserts newest-first under the current month.

## Doc resolution is the risk surface

There is no single canonical changelog location - across clients it's been seen inside Paid Search, under the legacy "Google/Bing Ads" name, under "#4 - Google Ads", and at folder top-level. The skill can't read the vault's `changelog_file` IDs (it runs in Cowork, not the vault), so it resolves by searching the client folder for the doc by name pattern, and **confirms the resolved doc (name + ID + path) with the human before writing**. A misresolved doc is the failure mode that would corrupt a client's log, so the gate shows the target Doc and the exact anchor being replaced, not just the entry.

## Scope discipline

Per-person defaults to the person's *own* accounts (from the `responsible` mapping), not all 200+ in the MCC - it keeps the loop small and matches the intent ("their book"). The exhaustive variant (all accounts filtered by email) exists for the rare case of catching changes a person made on an account they don't formally own; it's opt-in because it's a much larger loop.
