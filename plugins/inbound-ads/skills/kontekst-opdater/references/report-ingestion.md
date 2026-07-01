# Report ingestion (called only when a NEW report exists)

The skill invokes this sub-routine **only** when the newest deck in the client's report folder is newer than what's already been ingested. Ingesting a status deck is the richest "what was recently done/agreed" input, but it is expensive (download/convert/read a big file), so it must never run when the latest report was already absorbed. Everything here uses the Workspace MCP (`mcp__acc7a973-…`) — the connector with in-place read/convert/delete.

## The watermark: `Seneste rapport læst`

Track which deck has already been ingested with a line in the client's AI-Context file, in the ID-block:

```
Seneste rapport læst: 2026-06 - Dantaxi Statusrapport (juni 2026) SEO&SEM [id: 1Vx3Mdo...]
```

- **Title + file ID** — the title carries the `YYYY-MM`, the ID is the exact-match key (survives a re-export/rename).
- This is DISTINCT from:
  - `Rapporter:` (the report FOLDER link — where to look),
  - `Sidst opdateret:` (the whole-context watermark — the since-floor for Drive/HubSpot/Ads).
- If the line is absent (never ingested a report for this client): treat as "nothing ingested yet" → the newest report is always new.

## Step-by-step

### 1. Find the newest deck
`search` (rawQuery) the report folder:
```
'<report-folder id>' in parents and trashed = false
```
Decks are titled `YYYY-MM - <Klient> ...`. **Pick the newest by the `YYYY-MM` in the title** (not `modifiedTime` — re-exports muddy it). A given month often appears as BOTH a PDF and an uploaded PPTX (same title, different mime) — that's fine, prefer the PDF for extraction (see step 3).

### 2. Is it new? (the skip gate)
Compare the newest deck against `Seneste rapport læst` in the AI-Context file:
- Same title/ID → **already ingested, STOP.** Do not download/convert/read. Report "seneste rapport (<title>) er allerede indlæst — springer over."
- Different / no watermark line → proceed to ingest.

### 3. Convert to readable text
- **PDF present (the norm for recent reports):** `convertPdfToGoogleDoc(fileId=<pdf id>, newName="ZZ-TEMP <klient> rapport ekstraktion (delete me)")` → returns a temp Doc id. Then `readGoogleDoc(documentId=<temp id>, format="text")` (paginate with `readGoogleDocPaginated` if long). Verified 2026-07-01 on Dantaxi's juni deck: extraction is clean, readable Danish (full agenda, SEO, "Google Ads — Siden sidst", performance, next steps).
- **Only a PPTX (no PDF):** `convertPdfToGoogleDoc` does NOT accept PPTX. Fall back to `downloadFile(fileId, localPath="/tmp/<name>.pptx")` into the connector's own sandbox, then extract with the pptx skill IF that skill runs in the same sandbox. NOTE (env caveat, 2026-07-01): the Workspace connector's `/tmp` is a SEPARATE filesystem from the main agent shell — a `downloadFile` there is NOT visible to local Bash/Read. So in a split-sandbox environment, prefer the PDF+convert path; if only a PPTX exists, surface the link and say the deck couldn't be auto-extracted rather than guessing.
- **Native Google Slides deck** (some clients, e.g. Lime): read directly with `getGoogleSlidesContent(presentationId=<id>)` — no conversion needed.

### 4. Clean up the temp Doc (mandatory)
If you created a `ZZ-TEMP ...` conversion Doc in step 3, **delete it immediately** after reading: `deleteItem(itemId=<temp id>)` (moves to trash). Never leave conversion artifacts in Drive — that is the create-once clutter anti-pattern. One temp Doc, read it, trash it.

### 5. Extract DURABLE content only
From the deck text, pull what belongs in the Klientoverblik (feed to the diff in the main skill's Trin 4), NOT the metrics:
- **Keep:** what was reported/agreed, decisions, named next-steps and open levers ("Uberficering-splittest forlænget til 6. juli", "Customer Match — aftalt at vente"), structural/strategy changes, new campaigns/experiments, contact or scope changes.
- **Drop (timeless rule):** all performance numbers — spend, CTR, CPC, impressions, clicks, installs, conversions, ROAS, share %, month-over-month deltas. A deck is a point-in-time snapshot; recast a useful verdict as a durable lever, never copy the number. (See `diff-classification.md` timeless guard.)

### 6. Record the new watermark
After the main skill has applied the approved diff, update (or add) the `Seneste rapport læst:` line in the AI-Context file to the just-ingested deck's title + id (part of the same gated write that updates Klientoverblik + `Sidst opdateret`). So the next run's step 2 correctly skips it.

## Return to the caller (structured)
```json
{
  "newest_report": {"title": "", "id": "", "yyyymm": "", "mime": "pdf|pptx|slides"},
  "already_ingested": false,
  "extracted": true,
  "durable_points": ["Uberficering-splittest Jylland forlænget til 6. juli", "Customer Match aftalt udskudt", "..."],
  "temp_doc_cleaned": true,
  "note": "PPTX-only + split sandbox → link surfaced, not extracted"  // only when relevant
}
```
