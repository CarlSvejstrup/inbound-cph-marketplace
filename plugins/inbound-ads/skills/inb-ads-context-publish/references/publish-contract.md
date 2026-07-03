# Subagent contract: build ONE client's AI Context file

Hand this to each per-client subagent verbatim, with the client's resolved inputs appended. This is the exact procedure for building and publishing one client's AI Context file to Drive.

## Hard rules

- **Create-once.** Call the create tool for the file EXACTLY ONCE. There is NO delete/rename/update tool — a re-upload leaves an uncleanable duplicate. If a create fails or looks wrong, STOP and report; do NOT retry.
- **Native Google Doc** (source of truth: `../../shared/ai-context-file-contract.md`). The file is a native Google Doc, NOT a raw `.md`. Create it with `createDocFromMarkdown` (native-Doc create path — renders the markdown headings + `| Felt | Værdi |` table as native Doc formatting, matching the existing files) with `name: "<Client Name> - <HubSpotID>"` (NO `.md` suffix), `parentFolderId: <AI_CONTEXT_FOLDER_ID>`, `markdown` = the full text below. Do NOT pass `disableConversionToGoogleType` — that would leave a raw `.md` that `inb-ads-client-brief` cannot update in place via `findAndReplaceInDoc` (the real bug this format fixes). If `<HubSpotID>` is missing for a market, use the literal `ingen-HubSpot` in the title.
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
**Follow the section skeleton in `../../shared/ai-context-file-contract.md` verbatim** — it is the shared source of truth for the file shape, so a new Doc looks identical to the existing 46. Build the `markdown` for `createDocFromMarkdown` to that skeleton: a `Sidst opdateret: <today YYYY-MM-DD>` frontmatter block, the title line `<Client Name> (<domæne>) - AI Context`, the one-paragraph purpose line, the `| Felt | Værdi |` table (Specialist, Tier, Aftaleform, Valuta, Budget/md, Markeder, Andre ydelser — rendered natively by `createDocFromMarkdown`), then the H2 sections below in the contract's order, only the ones with content:

- **Konti & links** — Google Ads konto `<XXX-XXX-XXXX>`, Ads link, Bing, Budget pacing-ark, Optimeringslog / changelog (link to the SEPARATE changelog doc, or "ingen"). Budget stays "vejledende <number>" pointing at the shared pacing-ark as source of truth: https://docs.google.com/spreadsheets/d/1_zz92JGdM3zh8PE1xt7AsVCrOUlsQEI3XRbDS2qZljA/edit
- **Kontaktpersoner** — Hos kunden / Hos InboundCPH / Øvrige samarbejdspartnere (note practical rules e.g. Teams-not-Meet).
- **Kunderelation & noter** — durable relationship facts + "Durable aftalefakta (per Aftaleark ...)".
- **Klientoverblik** — verbatim from the note if one exists, else built to the same five-part shape: Overblik, Hårde rammer (læs før du handler), Mål & konverteringer, Sådan kører vi den, Aktuel status & åbne håndtag. Timeless-only per the shared contract.
- **Rapport** — source + what it covers (replaced on each new report; kept SEPARATE from Klientoverblik).
- **Aftaleark & kundebrief** — link + durable facts folded in.
- **Kildedokumenter** — the ranked source-doc index (Important / Less relevant), each `<navn> - <mappe>`, for the docs found in step 3 (incl. any reports). This is the contract's "Drive files" slot. NOTE the deliberate publish divergence: do NOT carry the vault note's own `## Drive-filer` list into the file (Carl: omit that local-mirror list entirely — see SKILL.md exclusions); the Kildedokumenter list here is the freshly-gathered source-doc index, not the note's mirror list.

Record the resolved HubSpot company id + stage + domain and the ClickUp folder id inside the relevant lines (Konti & links / Kunderelation) so an agent has them without leaving the Doc.

### 5. Create the file (ONCE) — native Google Doc
`createDocFromMarkdown` with `name:"<Client Name> - <HubSpotID>"` (NO `.md` suffix), `parentFolderId:<AI_CONTEXT_FOLDER_ID>`, `markdown` = the full text above. Do NOT pass `disableConversionToGoogleType` — the file must land as a native Google Doc so `inb-ads-client-brief` can update it in place via `findAndReplaceInDoc`. Capture the returned `documentId` + `url`, and check `warnings`.

### 6. Verify (read-only — no second create)
`search_files parentId='<AI_CONTEXT_FOLDER_ID>'`. Confirm exactly one file, correctly titled (NO `.md` suffix), mimeType `application/vnd.google-apps.document` (a native Doc). Flag (do NOT fix) any duplicate or pre-existing leftover.

## Report (one line)
`<Client>: created <viewUrl> in AI Context folder <folderUrl> (client root). HubSpot <id> (<domain>, stage=<x>). Reports found: <names+links / none>. Flags: <duplicates / leftovers / none>.`
