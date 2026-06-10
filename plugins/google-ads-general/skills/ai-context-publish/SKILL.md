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

2. **Format = native Google Doc, NOT a .md file.** Uploading `text/markdown` caused conversion problems and occasional duplicate-Doc artifacts. The reliable path is: upload `contentMimeType: text/plain` with NO `disableConversionToGoogleType` flag, so Drive converts the plain text into a native Google Doc. Title carries **no `.md` suffix**: `<Client Name> - <HubSpotID>`. (Markdown `#`/`-`/`|` in the body render as literal text in the Doc — that is expected and acceptable; keep them for readable structure.)

3. **The content is already-cleaned, timeless context.** The source is each client's `## Klientoverblik` in `work/inbound-cph/clients/<slug>.md`, which was deliberately stripped of point-in-time performance (no ROAS/CPA/CTR/counts/LAST_30_DAYS). Carry it VERBATIM. Never re-add live numbers. Configured settings (tCPA/budget caps), naming conventions, and structural caveats stay. See the vault rule [feedback-inbound-klientoverblik-timeless-only] and `references/klientoverblik-build-contract.md` in the vault.

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

1. **Find the target subfolder.** The Doc goes in an "AI Context" subfolder INSIDE the client's paid-search/Google-Ads folder, NOT loose in the client top folder. `search_files` with `parentId = '<CLIENT_FOLDER_ID>'`; pick the ads folder by name priority: `Paid Search` > `Paid ads`/`Paid Ads` > `Google Bing Ads`/`Google/Bing Ads` > `Google Ads`. Frontmatter `paid_search` hints which (`yes` / `legacy-gba` / `none`). If there is genuinely no ads subfolder (ads files loose at top level), use the client top folder and flag it. If the client folder is missing/ambiguous, STOP and ask.
2. **Create/reuse the "AI Context" folder** inside that ads folder (search-first; reuse if present).
3. **Build the content** from the vault note per the fixed format (see `references/publish-contract.md` and `references/doc-template.md`): `Sidst opdateret` line at the very top, H1 + intro, ID table (with pacing-ark on the Budget line), then the durable human sections that exist, then the `## Klientoverblik` verbatim, then `## Drive-filer` with full URLs. Drop YAML frontmatter; convert `[[wikilinks]]` to plain text; skip empty vault sections (don't fabricate missing headers).
4. **Create the Doc ONCE** as a native Google Doc, title `<Client Name> - <HubSpotID>` (no .md), `contentMimeType: text/plain`.
5. **Verify read-only** (`search_files` the AI Context folder: exactly one correctly-named Doc, mimeType `application/vnd.google-apps.document`). Flag any duplicate or pre-existing leftover for human cleanup; never try to delete.

**Shared-Drive-folder clients** (Lime ×6, GSGroup ×4, Nemco ×3, Retriever ×4 + Infomedia, Julemærket ×2, PhoneAlone ×2): one AI Context folder per shared Drive folder, holding all the siblings' Docs (one Doc per sibling, each with its own IDs). Clients with no own folder (e.g. Phone Alone Sverige points at PhoneAlone) get their Doc in the shared folder and a note; clients with no folder at all are skipped + flagged in the index.

After each batch, run an **independent verification sweep** (don't trust subagent self-reports): `search_files` across all the batch's AI Context folder IDs and confirm exactly one correctly-typed Doc per folder.

### Part B — the master client-index

After the AI Context Docs exist (so every row can link its real Doc), build ONE `client-index` Google Doc (or Sheet if the user prefers tabular) and upload it to the index folder the user specifies (the default used 2026-06-10 was `https://drive.google.com/drive/folders/1pKJINC4BHwN7aUmWRkak5ZwsXhj8rt2d`). Columns per client:
`Klient | Google Ads ID | HubSpot ID | ClickUp folder ID | Drive-mappe | AI Context-fil | Changelog`.
Include a `Sidst opdateret` line at top. Mark NEEDS-PICK HubSpot rows and skipped/no-folder clients honestly. Create-once; if updating later, you cannot overwrite — coordinate a UI replace or create a dated new version.

## Hard rules recap

- `create_file` ONCE per Doc; no delete/rename/update tool exists; never retry a create.
- Google Doc, title without `.md`, via `text/plain` (auto-convert).
- HubSpot ID matched by domain; flag (don't guess) on ambiguity.
- ClickUp = client folder ID under Kundespace.
- AI Context folder lives inside the ads subfolder, not the client root.
- Klientoverblik carried verbatim; never re-add performance numbers.
- Real Æ Ø Å. Budget references the shared pacing-ark.
- Never call the Ads MCP. Never edit the vault note. Human-in-the-loop on Drive writes.

## After the run (Dual-Output)

Log the batch in the vault: a line in today's `daily/YYYY-MM-DD.md`, and if the IDs (HubSpot/ClickUp) were newly resolved, consider persisting them into the client notes' frontmatter (separate task) so the next run doesn't re-resolve. Note any NEEDS-PICK HubSpot rows and leftover-file cleanups in `backlog/inbound-cph.md`.
