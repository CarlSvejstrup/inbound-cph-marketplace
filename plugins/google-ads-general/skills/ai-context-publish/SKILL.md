---
name: ai-context-publish
description: Publish per-client "AI Context" documents to Google Drive for Inbound CPH's Google Ads clients, and maintain a master client-index. For each client it resolves the client's IDs (Google Ads, HubSpot company, ClickUp folder), finds the client's paid-search/Google-Ads folder in Drive, creates an "AI Context" subfolder, and writes ONE Google Doc named "<Client Name> - <HubSpotID>" holding the client's operational context (the cleaned Klientoverblik brief + IDs + Drive-file links). Then builds a client-index document listing every client with all IDs, Drive link, AI Context file, and changelog. Reads the vault clients/*.md notes as the content source; never touches a Google Ads account (no Ads MCP). Human-in-the-loop on every Drive write. Danish content. Use when the user says "byg AI Context", "publicér klientkontekst til Drive", "AI Context-mapper", "opdater client-index", or asks to push the per-client context notes into Drive.
---

# ai-context-publish

Publish Inbound CPH's per-client operational context into Google Drive, so the Google Ads team and AI agents (e.g. in Cowork) can read a client's context where the work happens, and maintain one master index across all clients.

This skill **does not analyse or optimise a Google Ads account** and never calls the Ads MCP. It is a vault-to-Drive publishing operation: it reads the canonical client notes in the vault and writes context documents to Drive.

All client-facing content is **Danish**.

## Why this skill is shaped the way it is (read once)

1. **The Drive connector cannot delete, rename, or update a file in place.** Its only write tools are `create_file` (and `copy_file`). There is NO trash, NO move, NO content-update. Consequences, baked into every step:
   - **Create-once.** Call `create_file` for a given Doc EXACTLY ONCE. Never re-upload "to fix" — a re-upload leaves a duplicate you cannot remove programmatically. If a create fails or looks wrong, STOP and report; do not retry.
   - **Idempotency by search-first.** Before creating a folder, `search_files` for it and reuse if it exists. Before creating a Doc, the AI Context folder must be empty of that client's Doc.
   - Cleanup of any stray/leftover file is a **Drive-UI step for the human** — surface it as a flag, never attempt it.

2. **Format = true `.md` file (decided 2026-06-17 run).** Upload `contentMimeType: "text/markdown"` AND `disableConversionToGoogleType: true`, title WITH the `.md` suffix: `<Client Name> - <HubSpotID>.md`. This keeps it a real Markdown file (the format an AI agent in Cowork reads most cleanly). Carl explicitly chose this over a native Google Doc (a Doc renders cleaner in the Drive UI, but "Open in Docs" on a .md spawns a stray `.docx`, which he dislikes; and the Doc shows `#`/`|` as literal noise). If `<HubSpotID>` is missing for a market, use the literal `ingen-HubSpot` in the title (e.g. `GSGroup SE - ingen-HubSpot.md`). NOTE: `create_file` intermittently returns a generic "Internal error" — when it does, **search the folder before retrying** (the create usually did NOT happen, but verify, never blind-retry).

3. **The content is already-cleaned, timeless context.** The source is each client's `## Klientoverblik` in `work/inbound-cph/clients/<slug>.md`, which was deliberately stripped of point-in-time performance (no ROAS/CPA/CTR/counts/LAST_30_DAYS). Carry it VERBATIM. Never re-add live numbers. Configured settings (tCPA/budget caps), naming conventions, and structural caveats stay. See the vault rule [feedback-inbound-klientoverblik-timeless-only] and `references/klientoverblik-build-contract.md` in the vault.

   **EXCLUDE from the published file (decided 2026-06-17):** the YAML frontmatter; any `### Reconcile-flag` block or `<!-- RECONCILE ... -->` comment (internal audit only); any embedded changelog entries or `## Changelog` section (keep only the changelog_file LINK in the ID-block — changelog stays a SEPARATE doc); the `## Drive files` / `## Drive-filer` list (Carl: omit entirely); and empty placeholder sections. INCLUDE the ID-block with **ClickUp folder ID + HubSpot lifecycle stage** (omit the stage line only when the folder is untagged and stage is unknown), plus the durable human sections + full Klientoverblik + the Aftaleark digest.

   **Ground truth = the Drive folder name.** The "A - Kunder" client folders are now named `<Name> - [HubSpotID] (stage=<lifecyclestage>)`. That bracketed HubSpot ID + stage is authoritative; adopt it and flag any disagreement vs other sources. Untagged plain folders carry no stage — record "stage ikke tagget" and source the ID from the domain-matched HubSpot record.

4. **Real Æ Ø Å, always.** Danish output uses real æ ø å Æ Ø Å — never ASCII transliteration (aa/oe/ae). Grep your content before uploading.

5. **Human-in-the-loop.** Drive writes are external writes. Confirm scope with the user before a batch. Never touch a Google Ads account. Read the vault notes read-only — do not edit them.

## ID resolution (per client)

Each client needs three IDs plus links. Sources:

- **Google Ads ID, Drive client-folder, changelog_file, specialist/tier/budget/markeder:** the vault note frontmatter + body (`work/inbound-cph/clients/<slug>.md`). The vault is the source of truth — read it first.
- **HubSpot company ID:** resolve via the HubSpot MCP `crm_search_companies` (filter `name CONTAINS_TOKEN "<client>"`, properties `name, domain, hs_object_id, lifecyclestage`). **Many clients have multiple company records** (parent groups, country entities, billing entities). **Match by the client's actual Ads/website domain** (e.g. Dantaxi → the `dantaxi.dk` record, not the `moovegroup.com` one; Capio → `capio.dk`, not `capio.com`-lead or `cfrhospitaler.dk`-lead). If you cannot confidently match a domain, do NOT guess — flag it as NEEDS-PICK in the index with the candidate IDs and ask. A `lifecyclestage` of `lead` on the sole exact-name match (e.g. Roskilde Universitet, no domain set) is an acceptable use with a note, not a wrong entity.
- **ClickUp folder ID:** clients are FOLDERS under the `Kundespace` space (id `90080212431`). Use `clickup_get_workspace_hierarchy` with `space_ids:["90080212431"]`, `max_depth:2`, and read the client's folder id (e.g. Dantaxi → `90080593462`). Use the **client folder ID**, not a sub-list. Some vault clients map to a differently-named ClickUp folder (e.g. "A&Til - FTFa", "Handyman (GSGroup)", "Julemærkefonden", "Lime Technologies", "Rambøll", "Secure First") — match on the org, not the exact string.

## The shared budget-pacing-ark

Budget is NOT hard-coded as a standalone number. Every Doc references the agency's shared budget-pacing-ark (so it can be updated centrally; it may change year to year):
`https://docs.google.com/spreadsheets/d/1_zz92JGdM3zh8PE1xt7AsVCrOUlsQEI3XRbDS2qZljA/edit`
Keep the note's budget figure as "vejledende" + point to the ark as source of truth. (Confirm this is still the current ark with the user if the year has rolled over.)

## Workflow

### Part A — per-client AI Context Doc

For a batch, **divide clients across subagents (one client per subagent)** using the exact contract in `references/publish-contract.md`. Hand each subagent the client's resolved IDs + Drive client-folder ID + note path. Each subagent:

1. **Find the canonical client folder.** Prefer the renamed `<Name> - [HubSpotID] (stage=)` folder in "A - Kunder" (resolve by `title contains '<name>'`); fall back to the old plain-named folder only if no renamed one exists. The note's `drive_folder` frontmatter is the fallback. If missing/ambiguous, STOP and ask.
2. **Create/reuse the "AI Context" folder.** `search_files parentId='<CLIENT_FOLDER_ID>' and mimeType='application/vnd.google-apps.folder'`. **Ian already creates these folders himself and drops his own files in them** (e.g. DBI's holds his Projektoverblik + Optimeringslog + Demo-brief) — REUSE the existing one; our uniquely-named file sits alongside his. Watch for case variants: Ian used **"AI context"** (lowercase c) on InboundCPH — reuse it rather than spawn a near-duplicate. Note: Ian places the folder at the **client-folder root**, not inside Paid Search — follow that. Only create a new "AI Context" folder if none exists.
3. **Build the content** from the vault note (see `references/publish-contract.md`): `Sidst opdateret` line at top, H1 + intro, ID-block (with ClickUp folder ID + lifecycle stage + changelog LINK + pacing-ark on Budget), durable human sections that exist, `## Klientoverblik` verbatim, `## Aftaleark & kundebrief` digest. Drop YAML frontmatter; convert `[[wikilinks]]` to plain text; skip empty sections. EXCLUDE the Reconcile-flag, embedded changelog entries, and the Drive-filer list (see point 3 in "Why this skill is shaped...").
4. **Create the file ONCE** as a true `.md`: title `<Client Name> - <HubSpotID>.md`, `contentMimeType: "text/markdown"`, `disableConversionToGoogleType: true`. Search the folder for that exact title FIRST; if it exists, STOP (don't duplicate).
5. **Verify read-only** (`search_files` the AI Context folder: exactly one correctly-named file, mimeType `text/markdown`). Flag any duplicate/leftover for human cleanup; never try to delete.

**Shared-Drive-folder clients** (Lime ×6, GSGroup ×4, Nemco ×3, Retriever ×4 + Infomedia, Julemærket ×2, PhoneAlone ×2, DI ×2): ONE AI Context folder per shared Drive folder, holding all siblings' `.md` files (one per sibling, distinct title `<Client> - <HubSpotID>.md`, each with its own market Ads ID). EDC is the exception: Erhverv + Projekt share a HubSpot company but live in SEPARATE subfolders, so each gets its own AI Context folder. Clients with no own folder get their file in the shared folder + a note.

**Batch sizing (learned 2026-06-17):** keep concurrent subagents ≤6, and give a shared-group subagent at most ~4-6 files. The Drive connector drops the socket on long multi-create runs — a subagent that creates 6 files in one go often dies mid-run (it usually finishes the creates but the report is lost). When that happens, re-list the folder, find which files exist, and re-dispatch ONLY the missing ones with the existing folder ID supplied (skip folder creation).

After each batch, run an **independent verification sweep** (don't trust subagent self-reports): `search_files` across all the batch's AI Context folder IDs and confirm exactly one correctly-typed `.md` per expected sibling, no duplicates.

### Part B — the master client-index

After the AI Context Docs exist (so every row can link its real Doc), build ONE `client-index` Google Doc (or Sheet if the user prefers tabular) and upload it to the index folder the user specifies (the default used 2026-06-10 was `https://drive.google.com/drive/folders/1pKJINC4BHwN7aUmWRkak5ZwsXhj8rt2d`). Columns per client:
`Klient | Google Ads ID | HubSpot ID | ClickUp folder ID | Drive-mappe | AI Context-fil | Changelog`.
Include a `Sidst opdateret` line at top. Mark NEEDS-PICK HubSpot rows and skipped/no-folder clients honestly. Create-once; if updating later, you cannot overwrite — coordinate a UI replace or create a dated new version.

## Hard rules recap

- `create_file` ONCE per file; no delete/rename/update tool exists. On a generic "Internal error", SEARCH the folder before retrying (don't blind-retry — risk of permanent duplicate).
- True `.md`: title WITH `.md`, `contentMimeType: "text/markdown"` + `disableConversionToGoogleType: true`.
- EXCLUDE from the published file: frontmatter, Reconcile-flag, embedded changelog entries, Drive-filer list. INCLUDE ClickUp ID + stage in the ID-block.
- Ground truth = the `<Name> - [HubSpotID] (stage=)` Drive folder name; flag disagreements, never silently overwrite.
- Reuse Ian's existing "AI Context" folder (watch for the "AI context" lowercase variant); it lives at the client-folder root.
- HubSpot ID matched by domain; flag (don't guess) on ambiguity. ClickUp = client folder ID under Kundespace.
- Klientoverblik carried verbatim; never re-add performance numbers. Real Æ Ø Å. Budget references the shared pacing-ark.
- Batch ≤6 subagents, ≤~6 creates each (socket drops on long runs); re-list + re-dispatch only the missing files on failure.
- Some Drive folders are not writable by the connector (e.g. Rikke's "AI - Google ads 🤖" returned a generic internal error on every create). If a target folder rejects writes, surface it and ask for an alternative — don't keep retrying.
- Never call the Ads MCP. Never edit the vault note. Human-in-the-loop on Drive writes.

## After the run (Dual-Output)

Log the batch in the vault: a line in today's `daily/YYYY-MM-DD.md`, and if the IDs (HubSpot/ClickUp) were newly resolved, consider persisting them into the client notes' frontmatter (separate task) so the next run doesn't re-resolve. Note any NEEDS-PICK HubSpot rows and leftover-file cleanups in `backlog/inbound-cph.md`.
