---
name: inb-ads-context-publish
description: Initial publish of per-client "AI Context" files (and the master client-index) to Google Drive for Inbound CPH's Google Ads clients, resolving each client's Google Ads/HubSpot/ClickUp IDs and writing one create-once Drive doc with timeless operational context per human-approved write, versus inb-ads-client-brief which revises an already-published file.
---

# inb-ads-context-publish

Publish Inbound CPH's per-client operational context into Google Drive, so the Google Ads team and AI agents (e.g. in Cowork) can read a client's context where the work happens, and maintain one master index across all clients. This is the **initial creation** pass — for ongoing incremental updates to an already-published AI Context file, use `inb-ads-client-brief` instead.

This skill does not analyse or optimise a Google Ads account and never calls the Ads MCP. It reads the canonical client notes in the vault and writes context documents to Drive. All client-facing content is Danish.

## Constraints that shape every step

**The Drive connector cannot delete, rename, or update a file in place** — its only write tools are `create_file` and `copy_file`. So: call `create_file` for a given Doc EXACTLY ONCE. Never re-upload "to fix" a mistake — a re-upload leaves a duplicate you cannot remove programmatically. If a create fails or looks wrong, stop and report; do not retry blindly. Before creating a folder, `search_files` for it and reuse if it exists; before creating a Doc, confirm the AI Context folder doesn't already hold that client's file. `create_file` intermittently returns a generic "Internal error" — when it does, search the folder before retrying, since the create usually did NOT happen but you must verify, never blind-retry. Cleanup of any stray/leftover file is a Drive-UI step for the human — surface it as a flag, never attempt it yourself.

**Format = true `.md` file** (decided 2026-06-17). Upload `contentMimeType: "text/markdown"` AND `disableConversionToGoogleType: true`, title WITH the `.md` suffix: `<Client Name> - <HubSpotID>.md`. Carl chose this over a native Google Doc deliberately — "Open in Docs" on a .md spawns a stray `.docx` he dislikes, and a Doc renders `#`/`|` as literal noise. If `<HubSpotID>` is missing for a market, use the literal `ingen-HubSpot` in the title (e.g. `GSGroup SE - ingen-HubSpot.md`).

**Content is already-cleaned, timeless context.** The source is each client's `## Klientoverblik` in `work/inbound-cph/clients/<slug>.md`, deliberately stripped of point-in-time performance (no ROAS/CPA/CTR/counts/LAST_30_DAYS). Carry it verbatim — never re-add live numbers. Configured settings (tCPA/budget caps), naming conventions, and structural caveats stay. See vault rule `[feedback-inbound-klientoverblik-timeless-only]` and `references/klientoverblik-build-contract.md` in the vault.

Exclude from the published file: YAML frontmatter; any `### Reconcile-flag` block or `<!-- RECONCILE ... -->` comment (internal audit only); embedded changelog entries or a `## Changelog` section (keep only the changelog_file LINK in the ID-block — the changelog stays a separate doc); the `## Drive files` / `## Drive-filer` list (Carl: omit entirely); empty placeholder sections. Include the ID-block with ClickUp folder ID + HubSpot lifecycle stage (omit the stage line only when the folder is untagged and stage is unknown), plus the durable human sections that exist + full Klientoverblik + the Aftaleark digest.

**Ground truth = the Drive folder name.** "A - Kunder" client folders are named `<Name> - [HubSpotID] (stage=<lifecyclestage>)`. That bracketed HubSpot ID + stage is authoritative; adopt it and flag any disagreement vs other sources. Untagged plain folders carry no stage — record "stage ikke tagget" and source the ID from the domain-matched HubSpot record.

Danish output uses real æ ø å Æ Ø Å, never ASCII transliteration (aa/oe/ae) — grep your content before uploading. Drive writes are external writes: confirm scope with the user before a batch, never touch a Google Ads account, and read the vault notes read-only.

## ID resolution (per client)

- **Google Ads ID, Drive client-folder, changelog_file, specialist/tier/budget/markeder:** from the vault note frontmatter + body (`work/inbound-cph/clients/<slug>.md`) — the vault is the source of truth, read it first.
- **HubSpot company ID:** resolve via HubSpot MCP `crm_search_companies` (filter `name CONTAINS_TOKEN "<client>"`, properties `name, domain, hs_object_id, lifecyclestage`). Many clients have multiple company records (parent groups, country entities, billing entities) — match by the client's actual Ads/website domain (e.g. Dantaxi → `dantaxi.dk`, not `moovegroup.com`; Capio → `capio.dk`, not the `capio.com`-lead or `cfrhospitaler.dk`-lead record). If you cannot confidently match a domain, do NOT guess — flag it as NEEDS-PICK in the index with the candidate IDs and ask. A `lifecyclestage` of `lead` on the sole exact-name match (e.g. Roskilde Universitet, no domain set) is acceptable with a note, not a wrong entity.
- **ClickUp folder ID:** clients are folders under the `Kundespace` space (id `90080212431`). Use `clickup_get_workspace_hierarchy` with `space_ids:["90080212431"]`, `max_depth:2`, and read the client's folder id (e.g. Dantaxi → `90080593462`) — use the client folder ID, not a sub-list. Some vault clients map to a differently-named ClickUp folder (e.g. "A&Til - FTFa", "Handyman (GSGroup)", "Julemærkefonden", "Lime Technologies", "Rambøll", "Secure First") — match on the org, not the exact string.

## The shared budget-pacing-ark

Budget is never hard-coded as a standalone number. Every Doc references the agency's shared budget-pacing-ark (updated centrally, may change year to year):
`https://docs.google.com/spreadsheets/d/1_zz92JGdM3zh8PE1xt7AsVCrOUlsQEI3XRbDS2qZljA/edit`
Keep the note's budget figure as "vejledende" and point to the ark as source of truth. Confirm this is still the current ark with the user if the year has rolled over.

## Workflow

### Part A — per-client AI Context Doc

For a batch, divide clients across subagents (one client per subagent) using the exact contract in `references/publish-contract.md`. Hand each subagent the client's resolved IDs + Drive client-folder ID + note path.

When a client's context needs gathering across sources (Drive reports, HubSpot mail/notes, Google Ads change history) before publishing, delegate that source fan-out to the `drive-knowledge` agent via the Task tool — it reads Drive/HubSpot/Ads change-history since the watermark and returns a consolidated, source-attributed summary. It is read-only across all sources and honours the timeless-only rule. This skill still owns the Drive write: the create-once `.md` build + the human-in-the-loop `create_file` publish stay here. If `drive-knowledge` cannot be dispatched, gather inline instead.

Each per-client subagent:

1. **Find the canonical client folder.** Prefer the renamed `<Name> - [HubSpotID] (stage=)` folder in "A - Kunder" (resolve by `title contains '<name>'`); fall back to the old plain-named folder only if no renamed one exists. The note's `drive_folder` frontmatter is the fallback. If missing/ambiguous, stop and ask.
2. **Create/reuse the "AI Context" folder.** `search_files parentId='<CLIENT_FOLDER_ID>' and mimeType='application/vnd.google-apps.folder'`. Ian already creates these folders himself and drops his own files in them (e.g. DBI's holds his Projektoverblik + Optimeringslog + Demo-brief) — reuse the existing one, our uniquely-named file sits alongside his. Watch for case variants: Ian used "AI context" (lowercase c) on InboundCPH — reuse it rather than spawn a near-duplicate. Ian places the folder at the client-folder root, not inside Paid Search — follow that. Only create a new folder if none exists.
3. **Build the content** from the vault note (see `references/publish-contract.md`): `Sidst opdateret` line at top, H1 + intro, ID-block (ClickUp folder ID + lifecycle stage + changelog link + pacing-ark on Budget), durable human sections that exist, `## Klientoverblik` verbatim, `## Aftaleark & kundebrief` digest. Drop YAML frontmatter; convert `[[wikilinks]]` to plain text; skip empty sections; exclude the Reconcile-flag, embedded changelog entries, and the Drive-filer list per the constraints above.
4. **Create the file ONCE** as a true `.md`: title `<Client Name> - <HubSpotID>.md`, `contentMimeType: "text/markdown"`, `disableConversionToGoogleType: true`. Search the folder for that exact title first; if it exists, stop rather than duplicate.
5. **Verify read-only**: `search_files` the AI Context folder for exactly one correctly-named file, mimeType `text/markdown`. Flag any duplicate/leftover for human cleanup; never try to delete it.

**Shared-Drive-folder clients** (Lime ×6, GSGroup ×4, Nemco ×3, Retriever ×4 + Infomedia, Julemærket ×2, PhoneAlone ×2, DI ×2): one AI Context folder per shared Drive folder, holding all siblings' `.md` files (one per sibling, distinct title `<Client> - <HubSpotID>.md`, each with its own market Ads ID). EDC is the exception: Erhverv + Projekt share a HubSpot company but live in separate subfolders, so each gets its own AI Context folder. Clients with no own folder get their file in the shared folder plus a note.

**Batch sizing** (learned 2026-06-17): keep concurrent subagents ≤6, and give a shared-group subagent at most ~4-6 files. The Drive connector drops the socket on long multi-create runs — a subagent creating 6 files in one go often dies mid-run (usually finishes the creates but loses the report). When that happens, re-list the folder, find which files exist, and re-dispatch only the missing ones with the existing folder ID supplied (skip folder creation).

After each batch, run an independent verification sweep — don't trust subagent self-reports: `search_files` across all the batch's AI Context folder IDs and confirm exactly one correctly-typed `.md` per expected sibling, no duplicates.

### Part B — the master client-index

After the AI Context Docs exist (so every row can link its real Doc), build ONE `client-index` Google Doc (or Sheet if the user prefers tabular) and upload it to the index folder the user specifies (default used 2026-06-10: `https://drive.google.com/drive/folders/1pKJINC4BHwN7aUmWRkak5ZwsXhj8rt2d`). Columns per client:
`Klient | Google Ads ID | HubSpot ID | ClickUp folder ID | Drive-mappe | AI Context-fil | Changelog`.
Include a `Sidst opdateret` line at top. Mark NEEDS-PICK HubSpot rows and skipped/no-folder clients honestly. Create-once — if updating later you cannot overwrite, so coordinate a UI replace or create a dated new version.

Some Drive folders are not writable by the connector (e.g. Rikke's "AI - Google ads 🤖" returned a generic internal error on every create). If a target folder rejects writes, surface it and ask for an alternative rather than keep retrying.

#### Adding ONE new client to an already-published master index (the common single-client case)

When the master `client-index` Doc already exists (currently `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`) and you only need to add one new client's row, you CANNOT re-create the Doc (create-once). The index is a **native Google Docs table** in a converted `.md` Doc, so:

- **`insertText` at a row-boundary index does NOT work** — the connector counts indices through table cells, so any index lands *inside* a cell and splits an existing row's content (e.g. it once split a client's AI Context URL in half). **Do not use `insertText` to add a row.** If you already did and mangled a cell, repair it with `findAndReplaceInDoc` matching a fragment *within a single cell* (no `|` chars — `|` are rendered cell borders, not literal text, so any find-string containing `|` returns 0 matches).
- **`findAndReplaceInDoc` cannot add a row either** — it can't match across cell borders. Use it only for in-cell repairs.
- **The supported path is `editTableCell` into a pre-existing empty row at the bottom of the table.** Get the row layout from `getGoogleDocContent` (empty rows render as `|  |  |  |  |  |  |  |  |`). The table's `tableStartIndex` is the index where the header row begins (the `| Klient | ...` line). Row 0 = header, row 1 = the `| --- |` separator, rows 2..N = client rows; the first empty row is the next index. Fill all 8 columns of that row via `editTableCell` (one call per `columnIndex` 0-7): `Klient | Google Ads ID | HubSpot ID | ClickUp folder | Stage | Drive-mappe | AI Context-fil | Noter`. Then re-read to verify the row landed in one clean row with no cell split, and no existing row was overwritten.
- **If there are no empty rows left**, do NOT try to grow the table (the connector has no insert-row tool). STOP and tell the user: "The master index table is full — please add a few empty rows at the bottom of the Doc, then I'll fill them." **Give the user the Doc link so they can do it** (e.g. `https://docs.google.com/document/d/<index-id>/edit`). Once they've added rows, fill via `editTableCell` as above.
- Keep the row order convention loose: appending at the bottom empty rows is fine (the table is no longer strictly alphabetical once you append) — the index is a lookup table, not a sorted list. Bump the top `Sidst opdateret` line if you touch it.

## After the run (Dual-Output)

Log the batch in the vault: a line in today's `daily/YYYY-MM-DD.md`, and if the IDs (HubSpot/ClickUp) were newly resolved, consider persisting them into the client notes' frontmatter (separate task) so the next run doesn't re-resolve. Note any NEEDS-PICK HubSpot rows and leftover-file cleanups in `backlog/inbound-cph.md`.
