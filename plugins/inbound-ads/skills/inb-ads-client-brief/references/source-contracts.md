# Source contracts: the three expert subagents

Hand each subagent its block VERBATIM, with the client's resolved inputs + the since-date appended. Each subagent returns **only structured findings** (the schema below) — never raw file dumps into the main context. All three are **read-only**. Dispatch them concurrently (one message, three tool calls).

Shared inputs handed to every subagent: client display name, the since-date (`YYYY-MM-DD`, = the AI-Context file's `Sidst opdateret`), and the relevant ID(s) read from the index row + the AI-Context file (authoritative over any MCP payload).

---

## Drive-expert

**Tools:** ONLY the Inbound Google Drive MCP (`mcp__acc7a973-…`): `search` (rawQuery for date/mime filters), `listFolder`, `readGoogleDoc`, and the deck readers (`getGoogleSlidesContent`; PDF via `convertPdfToGoogleDoc` → `readGoogleDoc` → `deleteItem`). This is the ONE Drive MCP for everything — reads here, and the single inline write (`findAndReplaceInDoc`) in the main skill's Trin 6. Never create a duplicate file.

**Inputs:** the client's Drive-folder ID (from the index row's "Drive-mappe" link), the since-date, and any report-folder link already noted in the AI-Context file (may be absent).

### A. New/changed documents
1. `listFolder(folderId='<Drive-folder ID>')`, or `search(rawQuery=true, query="'<Drive-folder ID>' in parents and trashed=false")`. Recurse into subfolders (a folder result → list/search that subfolder id again). For shared-folder clients (Lime/Retriever/GSGroup/Nemco/Julemærket/PhoneAlone/DI/EDC — see the index "Noter" + "Delte mapper" section) note which market each doc belongs to.
2. Filter to `modifiedTime > '<since>T00:00:00Z'` (RFC-3339 UTC) — pass it directly in the rawQuery. The listing returns `modifiedTime` + `createdTime`.
3. `readGoogleDoc` the in-window docs. Skip files older than the window.

Drive rawQuery reminder (single-quote string values; combine with `and`/`or`):
```
'<folder id>' in parents and modifiedTime > '2026-06-17T00:00:00Z' and trashed=false
```

### C. Reports (HIGH PRIORITY — status/statusmøde decks)
Reports are monthly status decks. **The folder is the reliable anchor, not the file type** — verified across clients, the report folder is the client-folder subfolder named `#1 - Præsentationer og statusmøder` / `#1 - Statusmøder og -rapporter` / `#1 - Præsentationer & statusmøder` (a `#1 -` prefix + "sentation"/"statusm"). It sits in the MAIN client folder, NOT in Paid Search. Inside it, a given month's deck may exist as a **native Google Slide** (`application/vnd.google-apps.presentation`), an **uploaded PowerPoint** (`application/vnd.openxmlformats-officedocument.presentationml.presentation`, often with no file extension), and/or a **PDF export** — all three coexist. Decks are titled `YYYY-MM - <Klient> ...`, so **pick the newest by the `YYYY-MM` in the title** (more reliable than `modifiedTime`, which re-exports muddy). Prefer a readable form in this order for the newest month: native Slide → PPTX → PDF.

- **If a report folder is already noted in the AI-Context file:** go straight to it — `listFolder(folderId='<report-folder id>')` (list everything, no mime filter). Pick the newest deck by title-date. Read it via the deck readers (Slides direct; PPTX/PDF via convert — see `report-ingestion.md`). For the diff, only decks newer than the since-date count; for the overview, always summarize the latest deck.
- **If no report folder is noted yet (find, then let the main skill propose persisting it):** list the client folder's subfolders and pick the report folder by name (`search rawQuery`):
  ```
  '<Drive-folder id>' in parents and mimeType = 'application/vnd.google-apps.folder' and (name contains 'sentation' or name contains 'statusm' or name contains 'Møder' or name contains 'statusrapport')
  ```
  (`title contains 'sentation'` catches "Præsentation" + ASCII "Praesentation"; `statusm` catches "statusmøder"/"statusmoeder"; "Møder" is a real variant — Julemærket, Novo Nordisk.) If several match, take the `#1` one (hyphen OR en-dash `#1 –`); **ignore any titled `OLD - ...`** (legacy). **Fallback:** if no `#1` folder exists, look for year-based `<Klient> møder 20XX` folders and take the newest year (EDC Erhverv). Some clients genuinely have no status-deck folder (DI, CBCIT, HRS, Kirkens Korshær, Kbh Listefabrik, Ramboll) → return `status: none` gracefully. Return the folder (id + exact title + path + the newest deck found inside) for the main skill to confirm and write into the AI-Context file (Trin 5/6). Do NOT write anything from inside the subagent.
- **Extraction is delegated to `report-ingestion.md`** and runs ONLY when the newest deck is newer than the AI-Context file's `Seneste rapport læst` watermark (conversion is expensive — never re-ingest an already-loaded deck). That file owns the *how* (PDF → `convertPdfToGoogleDoc` → `readGoogleDoc` → `deleteItem` the temp Doc; native Slides → `getGoogleSlidesContent`; the split-sandbox `downloadFile` caveat) and the skip-gate. The Drive-expert's job here is only to locate the folder + identify the newest deck (title + id + yyyymm + mime) and report whether it beats the watermark.
- **Extract** durable content only: what was reported/agreed, named levers/next-steps, closed/opened håndtag — never raw metrics (a deck is a point-in-time artifact; recast verdicts as levers, feed conclusions to the diff).
- Unparseable/locked deck → return the link + "kunne ikke læses", never fabricate its contents.

### Resilience
The Drive connector drops the socket on long multi-read runs. On a drop: return what you gathered + `partial: true` with which step was cut. No blind-retry.

### Return schema (Drive-expert)
```json
{
  "source": "drive",
  "partial": false,
  "new_docs": [{"title": "", "id": "", "modified": "YYYY-MM-DD", "market": "", "summary": "one-line what-changed"}],
  "report_folder": {"status": "already_noted | candidate_found | none", "id": "", "name": "", "path": ""},
  "newest_report": {"title": "", "id": "", "yyyymm": "", "mime": "pdf|pptx|slides", "newer_than_watermark": true},
  "notes": "anything the main skill needs (shared-folder caveats, unreadable files). Report EXTRACTION + the ## Rapport summary is done by report-ingestion.md only when newer_than_watermark is true — not returned here."
}
```

---

## HubSpot-expert

**Tools:** HubSpot MCP (`mcp__d759f42a-…`): `crm_get_company`, `notes_search`, `emails_search`, `calls_search`, `meetings_search`, `tasks_search`, `crm_get_associations`. **Never** `engagement_details_*` (403 on the user token).

**Inputs:** the client's HubSpot ID (from the index row), the since-date.

1. Optionally confirm the company with `crm_get_company(<HubSpot ID>)` (name + domain — sanity-check it's the right org; the index "Noter" flags clients with HubSpot duplicates).
2. For each engagement type, search with the company-association filter + a recency filter. The documented workaround is an `associations.company` EQ filter (NOT `engagement_details`). **The recency filter MUST be `hs_createdate`, not `hs_lastmodifieddate`.** Pattern:
   ```
   filterGroups: [{ filters: [
     { propertyName: "associations.company", operator: "EQ", value: "<HubSpot ID>" },
     { propertyName: "hs_createdate", operator: "GT", value: "<since epoch ms or ISO>" }
   ]}]
   ```
   Run it for `notes_search`, `emails_search`, `calls_search`, `meetings_search`, `tasks_search`.
   **Why `hs_createdate` and not `hs_lastmodifieddate` (hard lesson):** HubSpot bulk-touches `hs_lastmodifieddate` on re-index. On 2026-06-30 that produced **141 false positives** — months-old mail returned as "new" — and only date-spot-checking caught it; `hs_createdate` gave the real 3 new mails. `hs_createdate` = when the object was actually created = the true "new since" signal. Use `hs_lastmodifieddate` ONLY as secondary confirmation, never as the sole/primary "new" filter. If a type errors on `hs_createdate`, drop to that type's own creation field (`createdAt`), never to a modified field; or fetch + filter client-side on the creation timestamp.
3. **Decode IDs to labels:** lifecycle-stage and deal-stage come back as numeric ids — map them to human labels (don't surface raw ids). Validate by object COUNT, not aggregate counters (e.g. `num_contacted_notes` can inflate vs readable note objects).
4. Collapse to human-readable activity: "3 mails med Natasha (seneste 2026-06-19, om Tinderbox-budget)", "1 note: statusmøde booket".

On any search error → `partial: true`, name which type failed. Mark HubSpot partial so the watermark is not advanced.

### Return schema (HubSpot-expert)
```json
{
  "source": "hubspot",
  "partial": false,
  "company": {"id": "", "name": "", "domain": "", "lifecycle_stage_label": ""},
  "activity": [{"type": "email|note|call|meeting|task", "date": "YYYY-MM-DD", "summary": "", "with": ""}],
  "notes": ""
}
```

---

## Ads-expert (light)

**Tools:** Google Ads MCP (`mcp__8829fa4d-…`): `get_change_summary`, `get_change_history`, optionally `run_custom_gaql` against `change_event`. Read-only. Light — the deep change-history belongs in `inb-ads-change-log`, not here.

**Inputs:** the client's Google Ads ID (from the index row), the since-date, the client's known campaign-name pattern (from the AI-Context file's Klientoverblik) for the mis-route check.

1. `get_change_summary(customer_id=<Google Ads ID>, lookback_days=29)` (or `get_change_history`). **`lookback_days` MUST be ≤ 29** — 30 hard-errors `START_DATE_TOO_OLD`.
2. **Bulk-collapse** on (timestamp, resource_type): one Editor upload writes many rows with the same timestamp — report as one action with a count, never N actions.
3. **Mis-route vagt (critical):** the MCP has returned a DIFFERENT account's data under a given `customer_id`. Sanity-check the returned campaign names / account identity against this client (the index row's Google Ads ID is the authoritative key). If it doesn't match → DISCARD the payload; the overview's "what changed" line then just says "ingen verificerbar Ads-ændring i vinduet".

Only durable facts for the overview's "what changed on the account" line — no metrics into anything that lands in Klientoverblik.

### Return schema (Ads-expert)
```json
{
  "source": "ads",
  "partial": false,
  "identity_ok": true,
  "recent_changes": [{"date": "YYYY-MM-DD", "action": "collapsed human-readable change", "by": "email"}],
  "notes": ""
}
```

---

## The Trin 6 write (single MCP, findAndReplaceInDoc only)

There is ONE Drive MCP (`mcp__acc7a973-…`) and the AI-Context file is a Google **Doc**, so the write is a gated **`findAndReplaceInDoc`** — no auth probe, no second connector, no copy-paste-first default. Full mechanics live in `insertion-and-resync.md`. In short:

- Show the target Doc + exact new blocks, wait for `ja`.
- Replace surgically, one `findAndReplaceInDoc` per block: (a) old `## Klientoverblik` → new; (b) old `## Rapport` → new (only if a new report was ingested); (c) `Sidst opdateret:` / `Rapporter:` / `Seneste rapport læst:` lines. Optionally `dryRun=true` first to confirm each `findText` matches exactly once.
- Inserting a section that doesn't exist yet: `findAndReplaceInDoc` can't insert, so fold the new section INTO a replacement of a unique adjacent anchor (e.g. replace the end of the Klientoverblik block with "that text + the new `## Rapport`").
- A `findText` that won't match → STOP, show the human the copy-paste block for that piece; never write a guess.
- Never create a duplicate file to "fix" a failed write (a duplicate can't be removed cleanly).
