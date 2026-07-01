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
`listFolder(folderId=<report-folder id>)` (or `search` rawQuery `'<report-folder id>' in parents and trashed = false`).
Decks are titled `YYYY-MM - <Klient> ...`. **Pick the newest by the `YYYY-MM` in the title** (not `modifiedTime` — re-exports muddy it). A given month often appears as BOTH a PDF and an uploaded PPTX (same title, different mime) — that's fine, prefer native Slides, then PPTX, then PDF (all three are readable, see step 3).

**An `#1` folder can be a decoy.** Verified 2026-07-01 across the client set: some `#1 - Statusmøder` folders are EMPTY or hold only 2022-23 files while the live decks sit elsewhere (SecureFirst → `Paid Search`; Julemærket → `Google Ads/2026 - <Klient> - Møder`; some clients have a `Statusmøder/Statusmøder 2026` subfolder, a `a - Månedlige statusmøder` subfolder, or a `GEO Henning` subfolder). If the mapped/`#1` folder is empty or has no recent `YYYY-MM` deck, DRILL into its subfolders and search the client tree (`Paid Search`, `Google Ads/`, year-subfolders) before concluding "none". Only after that search comes up empty do you report no report. Also skip non-decks that share the folder (an `.mp3` workshop recording, a GEO/AI-visibility sales pitch that isn't a Paid Search status) and title-date lies (a file named `2026-05` whose content is March) — cite the title, state the real period.

### 2. Is it new? (the skip gate)
Compare the newest deck against `Seneste rapport læst` in the AI-Context file:
- Same title/ID → **already ingested, STOP.** Do not download/convert/read. Report "seneste rapport (<title>) er allerede indlæst — springer over."
- Different / no watermark line → proceed to ingest.

### 3. Convert to readable text
- **PDF present (the norm for recent reports):** `convertPdfToGoogleDoc(fileId=<pdf id>, newName="ZZ-TEMP <klient> rapport ekstraktion (delete me)")` → returns a temp Doc id. Then `readGoogleDoc(documentId=<temp id>, format="text")` (paginate with `readGoogleDocPaginated` if long). Verified 2026-07-01 on Dantaxi's juni deck: extraction is clean, readable Danish (full agenda, SEO, "Google Ads — Siden sidst", performance, next steps).
- **PPTX (a true Office file — common: Nemco, Capio, MMAKE, A&Til, Alpha, DNV):** `getGoogleSlidesContent` REJECTS it and `convertPdfToGoogleDoc` does not accept it. Two working paths, verified 2026-07-01 in bulk:
  1. **Re-upload with conversion (preferred, always works):** `downloadFile(fileId)` into the connector's own sandbox, then re-upload with `convertToGoogleFormat: true` + the explicit PPTX mimeType (`application/vnd.openxmlformats-officedocument.presentationml.presentation`) to produce a temp native Slides file → `getGoogleSlidesContent(presentationId=<temp id>)` → `deleteItem` the temp. (The connector's `/tmp` is a separate filesystem from the main shell, so the download stays inside the connector — that's fine here, the re-upload reads from the same sandbox.)
  2. **Convert the PDF twin** if the same month also exists as a PDF: use the PDF path above instead.
- **Native Google Slides deck** (many clients, e.g. Lime, GSGroup, Retriever): read directly with `getGoogleSlidesContent(presentationId=<id>)` — no conversion needed. This is the cheapest; prefer it when the month exists as native Slides.

### 4. Clean up the temp Doc (mandatory)
If you created a `ZZ-TEMP ...` conversion Doc in step 3, **delete it immediately** after reading: `deleteItem(itemId=<temp id>)` (moves to trash). Never leave conversion artifacts in Drive — that is the create-once clutter anti-pattern. One temp Doc, read it, trash it.

### 5. Extract the report summary (its OWN section — NOT the Klientoverblik diff)
Report content lives in a dedicated **`## Rapport`** section in the AI-Context file and is kept **entirely separate** from `## Klientoverblik`. Report-ingestion does NOT feed the Trin 4 TILFØJ/ERSTAT/FJERN diff and does NOT edit Klientoverblik — this keeps report insights traceable to their source and easy to find again, and keeps Klientoverblik as the clean durable operating context.

From the deck text, build a compact Danish summary of the newest report:
- **Keep:** what was reported/agreed, decisions, named next-steps and open levers ("Uberficering-splittest forlænget til 6. juli", "Customer Match — aftalt at vente"), structural/strategy changes, new campaigns/experiments, contact or scope changes.
- **Drop the numbers where they're just a snapshot** — a `## Rapport`-sektion må godt referere hvad rapporten konkluderede kvalitativt, men undgå at kopiere en mur af performance-tal (spend/CTR/CPC/impressions/clicks/ROAS/share%); det er en rapport-oversigt, ikke en gengivelse af hele decket. Behold datoen/perioden rapporten dækker.

### 6. Section format (replace-with-latest)
`## Rapport` holds the **latest** report only — REPLACE the whole section each run (matches the single `Seneste rapport læst` watermark). Shape:

```
## Rapport

_Kilde: <deck-titel> (<link>). Læst <YYYY-MM-DD>. Dækker <periode fra decket>._

- <kort punkt: hvad blev rapporteret/besluttet>
- <næste skridt / aftale>
- <strukturel/strategi-ændring>
```

(If Carl later wants a running history instead of latest-only, append newest-on-top under dated sub-headers rather than replacing — but default is latest-only.)

### 7. Watermark
Update (or add) the `Seneste rapport læst: <titel> [id: <fil-id>]` line, as part of the same gated write that writes `## Rapport` (Trin 6 of the main skill). So the next run's step 2 skips this deck.

## Return to the caller (structured)
```json
{
  "newest_report": {"title": "", "id": "", "yyyymm": "", "mime": "pdf|pptx|slides"},
  "already_ingested": false,
  "extracted": true,
  "rapport_section_md": "## Rapport\n\n_Kilde: ..._\n\n- ...",
  "watermark_line": "Seneste rapport læst: 2026-06 - Dantaxi Statusrapport (juni 2026) SEO&SEM [id: 1Vx3Mdo...]",
  "temp_doc_cleaned": true,
  "note": "PPTX-only + split sandbox → link surfaced, not extracted"  // only when relevant
}
```
