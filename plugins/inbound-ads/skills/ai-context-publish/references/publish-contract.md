# Subagent contract: build ONE client's AI Context Google Doc

Hand this to each per-client subagent verbatim, with the client's resolved inputs appended. This is the exact procedure proven on the 2026-06-10 batch (Dantaxi pilot + Capio/Alpha/CBCIT/Securitas/RUC).

## Hard rules

- **Create-once.** Call `create_file` for the Doc EXACTLY ONCE. There is NO delete/rename/update tool — a re-upload leaves an uncleanable duplicate. If a create fails or looks wrong, STOP and report; do NOT retry.
- **Google Doc, title NO .md suffix.** Title = `<Client Name> - <HubSpotID>`. Upload `contentMimeType: text/plain`, NO `disableConversionToGoogleType` flag → Drive makes a native Google Doc. (Do NOT use text/markdown.)
- **Real Æ Ø Å** in the Danish content — never aa/oe/ae. Grep before upload.
- **Never** call any Google Ads MCP. **Never** edit the vault note (read-only).
- Human-in-the-loop: only a context Doc to Drive, authorized for this batch.

## Inputs (appended per client)
Client display name; Google Ads ID; HubSpot company ID (+ matched domain); ClickUp folder ID; Drive CLIENT-folder ID; vault note path; `paid_search` value; changelog_file URL. The shared pacing-ark URL (same for all): https://docs.google.com/spreadsheets/d/1_zz92JGdM3zh8PE1xt7AsVCrOUlsQEI3XRbDS2qZljA/edit

## Steps

### 1. Find the ads subfolder (target parent)
`search_files` `parentId = '<CLIENT_FOLDER_ID>'`. Pick the ads folder by name priority: `Paid Search` > `Paid ads`/`Paid Ads` > `Google Bing Ads`/`Google/Bing Ads` > `Google Ads`. (`paid_search: yes`→Paid Search; `legacy-gba`→Google Bing Ads; `none`→alt-named or loose — use judgment.) If no ads subfolder exists, use the CLIENT top folder and note it. If the client folder is missing/ambiguous, STOP and report.

### 2. Create/reuse "AI Context" folder
`search_files` `parentId = '<ADS_FOLDER_ID>' and mimeType = 'application/vnd.google-apps.folder'`; if a folder titled exactly `AI Context` exists, reuse its id. Else `create_file` `title:"AI Context"`, `mimeType:"application/vnd.google-apps.folder"`, `parentId:<ADS_FOLDER_ID>`. Capture the id.

### 3. Build content from the vault note
Read the note fully. Transform:
- Drop YAML frontmatter.
- `[[wikilinks]]` → plain readable text; internal research links → "(Inbounds interne research)".
- Keep durable human sections that EXIST: Om virksomheden, Kontaktpersoner, Kunderelation & noter. **If the note has no such section (context folded into Klientoverblik), OMIT it — do NOT fabricate a header.**
- Carry the full `## Klientoverblik` VERBATIM (all ### subsections). It is already timeless — do not strip or re-add numbers.
- Include `## Drive files` as `## Drive-filer` with full URLs.
- Skip empty/placeholder vault sections (blank "Senest lavet", "Link", "Rapporter & logs", redundant "Konti & links" unless the Klientoverblik references it, empty "## Changelog" stub).

### 4. Fixed top-of-doc format (identical every client)
```
Sidst opdateret: <today YYYY-MM-DD>

# <Client Name> (<domain or vault title>) - AI Context

Operationelt AI-kontekstdokument for Google Ads-teamet og AI-agenter, der skal optimere eller bygge kampagner på denne konto. Genereret fra Inbounds interne klientnote <today>. Kontekst er tidsløs: konkrete performance-tal hører hjemme i de daterede audits/logs, ikke her.

ID / felt | Værdi
- Google Ads ID: <XXX-XXX-XXXX (numeric)>
- HubSpot company ID: <id> (<matched domain>)
- ClickUp folder ID: <id>
- Drive-mappe: <client drive_folder URL>
- Changelog / optimeringslog: <changelog_file URL, or "ingen">
- Specialist: <from note>
- Tier: <from note, or "-">
- Aftaleform: <from note, or "-">
- Valuta: <from note>
- Budget/md: <number from note> (vejledende - se budget-pacing-arket for aktuelt tal; arket er kilden til sandhed og kan ændre sig år for år): https://docs.google.com/spreadsheets/d/1_zz92JGdM3zh8PE1xt7AsVCrOUlsQEI3XRbDS2qZljA/edit
- Markeder: <from note>
- Andre ydelser: <from note, or omit line if none>
```
Then `## Om virksomheden`, `## Kontaktpersoner`, `## Kunderelation & noter` (each only if it exists), `## Klientoverblik` (verbatim, with its ### subsections), `## Drive-filer`. Inside Klientoverblik > Overblik, if there is a Budget bullet, append " - se budget-pacing-arket for det aktuelle tal (kilden til sandhed)" after the budget figure (no-op if no such bullet).

### 5. Create the Doc (ONCE)
`create_file` `title:"<Client Name> - <HubSpotID>"`, `parentId:<AI_CONTEXT_FOLDER_ID>`, `contentMimeType:"text/plain"`, `textContent:<full content>`. Capture id + viewUrl.

### 6. Verify (read-only — no second create)
`search_files` `parentId = '<AI_CONTEXT_FOLDER_ID>'`. Confirm exactly one Doc, correctly titled (no .md), mimeType `application/vnd.google-apps.document`. Flag (do NOT fix) any duplicate or pre-existing leftover.

## Report (one line)
`<Client>: created Doc <viewUrl> in AI Context folder <folderUrl> (under <ads folder name>). HubSpot <id> (<domain>). Flags: <duplicates / leftovers / no-ads-folder / none>.`
