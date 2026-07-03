# Subagent contract: build ONE client's AI Context file

Hand this to each per-client subagent verbatim, with the client's resolved inputs appended. This is the exact procedure for building and publishing one client's AI Context file to Drive.

## Hard rules

- **Create-once.** Call the create tool for the file EXACTLY ONCE. There is NO delete/rename/update tool — a re-upload leaves an uncleanable duplicate. If a create fails or looks wrong, STOP and report; do NOT retry.
- **True `.md` file** (decided 2026-06-17, supersedes the old native-Doc format). Title WITH the `.md` suffix: `<Client Name> - <HubSpotID>`. Upload `contentMimeType: "text/markdown"` AND `disableConversionToGoogleType: true` → Drive keeps it a real Markdown file (the format a Cowork agent reads most cleanly). If `<HubSpotID>` is missing for a market, use the literal `ingen-HubSpot` in the title. (With the connected Drive MCP, `createTextFile` with a `.md` name + inline content produces the same true `.md`.)
- **Real Æ Ø Å** in the Danish content — never aa/oe/ae. Grep before upload.
- **Never** call any Google Ads MCP. **Never** edit the vault note (read-only).
- Human-in-the-loop: only a context file to Drive, authorized for this batch.

## Inputs (appended per client)
Client display name; Google Ads ID; HubSpot company ID (+ matched domain) + lifecycle stage; ClickUp folder ID; Drive CLIENT-folder ID; vault note path (if one exists); changelog_file URL (if any). The shared pacing-ark URL (same for all): https://docs.google.com/spreadsheets/d/1_zz92JGdM3zh8PE1xt7AsVCrOUlsQEI3XRbDS2qZljA/edit

## Steps

### 1. Target parent = the client ROOT folder
The AI Context folder ALWAYS lives at the top level of the client folder — NOT inside Paid Search or any other subfolder. The target parent is the client folder itself (`<CLIENT_FOLDER_ID>`). If the client folder is missing/ambiguous, STOP and report.

### 2. Create/reuse "AI Context" folder (at the client root)
`search_files parentId='<CLIENT_FOLDER_ID>' and mimeType='application/vnd.google-apps.folder'`; if a folder titled `AI Context` (or the lowercase `AI context` variant) exists, reuse its id. Else create it with `parentId:<CLIENT_FOLDER_ID>`. Capture the id.

### 3. Gather the source content (sweep the WHOLE client folder, not just Paid Search)
The context can live anywhere in the client folder — do not read only Paid Search.
- **If a canonical vault note exists** (`work/inbound-cph/clients/<slug>.md`): it is the primary source. Carry its `## Klientoverblik` VERBATIM (all ### subsections) — it is already timeless, do not strip or re-add numbers.
- **If it is a NEW client with no note yet:** originate the context from the Drive sources below.
- **Sweep these locations for relevant material** (list the client-root subfolders first, then open what is relevant): the client ROOT itself, plus subfolders like `Strategi og projektledelse`, `Forprojekt og salg`, `Grafik og design`, `Marketing automation`, `Tracking & CRO`, `SEO`, `Paid Social`, and `Paid Search`. Look specifically for:
  - onboarding / opstart docs and strategy decks (campaign structure, budget, bidding, KPI'er, naming convention),
  - the Aftaleark & kundebrief (scope, contacts, access, tech stack),
  - brand / tone-of-voice + persona / audience docs (feed ad-copy guidance),
  - **any reports** — status reports, deepdives, slutrapporter (often NOT in Paid Search).
- **Report every report you find** (name + link) back to the user so they know it exists — even when it lives outside Paid Search.
- Transform for the file: drop YAML frontmatter; `[[wikilinks]]` → plain readable text; internal research links → "(Inbounds interne research)"; skip empty/placeholder sections; exclude the Reconcile-flag, embedded changelog entries, and the `## Drive-filer` list.

### 4. Fixed document format
```
Sidst opdateret: <today YYYY-MM-DD>

# <Client Name> — AI Context (Google Ads)

<One-line purpose: operationel kontekst for <Client>s Google Ads-arbejde. Læs denne før arbejde på kontoen. Kontekst er tidsløs: konkrete performance-tal hører hjemme i de daterede audits/logs, ikke her.>

## ID'er & links

- Google Ads konto: <XXX-XXX-XXXX>
- HubSpot: <company name> — <id> (stage=<lifecyclestage>, domæne <domain>)
- ClickUp-mappe: <id>
- Drive-mappe: <client drive_folder URL>
- Changelog / optimeringslog: <changelog_file URL, or "ingen">
- Budget: vejledende <number> (se det fælles pacing-ark som kilde: https://docs.google.com/spreadsheets/d/1_zz92JGdM3zh8PE1xt7AsVCrOUlsQEI3XRbDS2qZljA/edit)
```
Then, in this order, only the sections that have content:
- `## Aftale` (scope / period / hours / specialists — from the Aftaleark)
- `## Kontaktpersoner` (client side + Inbound side; note practical rules e.g. Teams-not-Meet)
- `## Kunderelation & noter` (durable relationship facts)
- `## Klientoverblik` — verbatim from the note if one exists, else built to the same five-part shape: Overblik, Hårde rammer (læs før du handler), Mål & konverteringer, Sådan kører vi den, Aktuel status & åbne håndtag.
- `## Aftaleark & kundebrief (digest)` (source line + scope/access/tech-stack digest)
- `## Kildedokumenter` (links to the Drive source docs found in step 3, incl. any reports)

### 5. Create the file (ONCE)
Create `title:"<Client Name> - <HubSpotID>.md"`, `parentId:<AI_CONTEXT_FOLDER_ID>`, `contentMimeType:"text/markdown"`, `disableConversionToGoogleType:true`, content = the full text. Capture id + viewUrl. (Connected Drive MCP: `createTextFile` with the `.md` name + inline content.)

### 6. Verify (read-only — no second create)
`search_files parentId='<AI_CONTEXT_FOLDER_ID>'`. Confirm exactly one file, correctly titled (with `.md`), mimeType `text/markdown`. Flag (do NOT fix) any duplicate or pre-existing leftover.

## Report (one line)
`<Client>: created <viewUrl> in AI Context folder <folderUrl> (client root). HubSpot <id> (<domain>, stage=<x>). Reports found: <names+links / none>. Flags: <duplicates / leftovers / none>.`
