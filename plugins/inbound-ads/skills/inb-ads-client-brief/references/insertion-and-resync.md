# Writing the updated AI-Context file + the watermark

The mechanics for writing approved changes into the client's AI-Context file on Drive (the `.md` linked from the master index), and advancing the watermark. There is no local file and no frontmatter — everything is the Drive AI-Context file.

## The AI-Context file shape (what you are editing)

`inb-ads-context-publish` created the file. It starts with a `Sidst opdateret:` line, then an H1, an intro, an ID-block, durable sections, and the `## Klientoverblik` (with its ### subsections). The canonical section set + order is defined in `references/section-contract.md` (the source of truth for the layout, shared with the local `clients/*.md` mirror). Schematically:

```
Sidst opdateret: 2026-06-17

# <Klient> (<domæne>) - AI Context

<intro line>

ID / felt | Værdi
- Google Ads ID: ...
- HubSpot company ID: ...
- ...
- Changelog / optimeringslog: <link>
- Rapporter: <link>            # may be absent — this skill can add it

## Konti & links              # durable account facts (only if present)
## Kontaktpersoner            # (only if present)
## Kunderelation & noter      # soft relationship context (only if present)
## Klientoverblik             # <-- the block this skill replaces
### Overblik
### Hårde rammer (læs før du handler)
### Mål & konverteringer
### Sådan kører vi den
### Aktuel status & åbne håndtag
## Rapport                    # <-- own section; replaced when a NEW report is ingested (kept SEPARATE from Klientoverblik)
## Aftaleark & kundebrief     # (only if present, do not touch)
## Drive files                # (do not touch)
```

A normal run edits ONLY `## Klientoverblik` + `## Rapport` (+ the watermark/ID-block lines). It does NOT refold the other sections — retiring legacy scattered H2s (`## Om virksomheden`, `## Budget`, `## KPIer og mål`, ...) is a deliberate batch migration per `section-contract.md`, never a silent side-effect of a sync run.

## What this skill writes (and only this)

1. The `## Klientoverblik` block — replaced in full with the new one (approved TILFØJ + approved ERSTAT/FJERN applied).
2. The `## Rapport` section — replaced with the latest report summary, but ONLY when report-ingestion loaded a new deck. It is a standalone section (from `report-ingestion.md`), never merged into Klientoverblik and never touched by the Trin 4 diff. If it doesn't exist yet, insert it right after `## Klientoverblik`. If no new report this run, leave it untouched.
3. The `Sidst opdateret:` line — bumped to today on a clean run.
4. The `Seneste rapport læst:` line — updated to the just-ingested deck (title + id), only when a new report was loaded.
5. An ID-block `Rapporter:` line — added (or corrected) only if a report folder was found/confirmed and isn't already there.

Do NOT touch the H1, intro, the rest of the ID-block, `## Om virksomheden`, `## Kontaktpersoner`, `## Drive-filer`, or the changelog link. Never re-create the file.

## Klientoverblik block rules

- **Replace, never append.** Match from `## Klientoverblik` to the next `## ` heading and replace that whole block. Never leave two `## Klientoverblik` sections.
- Keep the 5-subsection structure (Overblik / Hårde rammer / Mål & konverteringer / Sådan kører vi den / Aktuel status & åbne håndtag). Omit a subsection only if it would be empty.
- **Intro/provenance line** at the top of Klientoverblik records the sync + per-source as-of:
  ```
  _Operationelt brief til en agent, der skal handle på denne konto. Kontekst sidst synket <YYYY-MM-DD> (Drive t.o.m. <dato>, HubSpot t.o.m. <dato>, rapporter t.o.m. <dato eller "ingen nyere fundet">). Opdateret fra <kilder læst denne kørsel>._
  ```
  When a source was partial, say so inline: `HubSpot t.o.m. <prior> — ikke synket denne kørsel`. This is the human-readable "when was this last updated, per source" surface.

## Watermark = the `Sidst opdateret:` line

There is no separate timestamp field anywhere. The file's own `Sidst opdateret:` line IS the watermark.
- **Read** it for the since-floor ("nyt siden <dato>").
- **Bump** it to today ONLY on a clean full-source run that the human approved changes on.
- **Partial-success:** if ANY of the three sources was partial (HubSpot 403, Drive socket-drop), do NOT bump it — leave the prior date, and record the per-source as-of in the provenance line so the next run re-pulls the gap. (You still wrote whatever edits the human approved; you just don't claim "fully synced through today".)
- **Bootstrap:** the file has no `Sidst opdateret:` line (older format) → treat the whole file as the since-floor, state the assumption in the overview, and add the line when you write.

## The write itself (Trin 6 — gated, findAndReplaceInDoc only)

One Drive MCP (`mcp__acc7a973-…`), and the AI-Context file is a Google **Doc**, so the write is a gated **`findAndReplaceInDoc`**. No auth probe, no second connector, no "copy-paste by default". Always gated: show the target Doc (name + link) + the exact new blocks, wait for `ja`, replace, confirm.

- **Replace surgically, one `findAndReplaceInDoc` per piece,** keeping the rest of the Doc intact: (a) the old `## Klientoverblik` block → new; (b) the old `## Rapport` section → new, ONLY if a new report was ingested; (c) the `Sidst opdateret:` line (old date → today); (d) the `Seneste rapport læst:` line if a new report was ingested; (e) the `Rapporter:` line if newly found. `findText` = the exact existing text with enough surrounding context to match **exactly once** (run `dryRun=true` first to confirm the count). This is the ONLY inline operation — do NOT use `updateTextFile`/`updateDocFromMarkdown`/`insertText`.
- **Inserting a section that doesn't exist yet** (e.g. the Doc has no `## Rapport`): `findAndReplaceInDoc` can't insert text, so make the insertion a *replacement of a unique anchor* — replace the tail of the `## Klientoverblik` block with "that same tail + `\n\n## Rapport\n\n<new section>`". Same trick to add a missing `Rapporter:` line (extend an adjacent ID-block line).
- **A `findText` that won't match** (the Doc's text differs from expected) → STOP for that piece and emit the **copy-paste-ready** block in a fenced code block, telling the human: "Åbn AI-Context-Doc'en `<navn>` (`<link>`) og erstat den viste sektion med dette." Never write a guess. This is the exception path, not the default.

Never create a duplicate file to "fix" a failed write (a duplicate can't be removed cleanly). If the file genuinely needs full re-creation, that's `inb-ads-context-publish`'s job (create-once).

## Output (Trin 7)

Report: the since-window, the three sources' as-of dates, counts added/replaced/removed, and the write outcome (`findAndReplaceInDoc`-written, or copy-paste-delivered for any piece whose `findText` didn't match). End with a `## Datakilder` block (tools called, IDs, the date window, any source that failed). No local log is written — everything lives in the updated Drive Doc.
