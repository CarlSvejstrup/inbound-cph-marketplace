# Writing the updated AI-Context file + the watermark

The mechanics for writing approved changes into the client's AI-Context file on Drive (the `.md` linked from the master index), and advancing the watermark. There is no local file and no frontmatter — everything is the Drive AI-Context file.

## The AI-Context file shape (what you are editing)

`ai-context-publish` created the file. It starts with a `Sidst opdateret:` line, then an H1, an intro, an ID-block, durable sections, and the `## Klientoverblik` (with its ### subsections). Schematically:

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

## Om virksomheden            # (only if present)
## Kontaktpersoner            # (only if present)
## Klientoverblik             # <-- the block this skill replaces
### Overblik
### Hårde rammer
### Mål & konverteringer
### Sådan kører vi den
### Aktuel status & åbne håndtag
## Drive-filer                # (do not touch)
```

## What this skill writes (and only this)

1. The `## Klientoverblik` block — replaced in full with the new one (approved TILFØJ + approved ERSTAT/FJERN applied).
2. The `Sidst opdateret:` line — bumped to today on a clean run.
3. An ID-block `Rapporter:` line — added (or corrected) only if a report folder was found/confirmed and isn't already there.

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

## The write itself (Trin 6 — gated, gws-or-fallback)

This is the only write. It goes through the gws probe + fallback (`source-contracts.md` capability matrix). Always gated: show the target file (name + link) + the exact new block, wait for `ja`, write, confirm. Never `create_file` a duplicate via the Drive connector to "fix" a failed gws write.

- **Authed + writable:** gated update of the file's `## Klientoverblik` section. Prefer a **surgical `findAndReplaceInDoc`** of the old Klientoverblik block → the new one (keeps the rest of the file intact), plus a `findAndReplaceInDoc` on the `Sidst opdateret:` line (old date → today) and the `Rapporter:` line if added. `updateTextFile` (full new content) is acceptable if you reconstruct the entire file faithfully, but the surgical replace is safer (less chance of dropping an untouched section). Scope each `findText` tightly (include enough surrounding text to match exactly once).
- **Not authed / 403 / any error:** do not write. Emit the **copy-paste-ready** new block in one fenced code block — the new `## Klientoverblik` (+ the new `Sidst opdateret:` line + any `Rapporter:` line) — and tell the human: "Åbn AI-Context-filen `<navn>` (`<link>`) og erstat `## Klientoverblik`-sektionen (og opdatér `Sidst opdateret`-linjen) med dette." Point to `ai-context-publish` for a full republish, noting its **create-once** caveat (a true republish needs a manual Drive-UI delete of the old file first, since the Drive connector can't overwrite).

## Output (Trin 7)

Report: the since-window, the three sources' as-of dates, counts added/replaced/removed, and the write outcome (gws-written vs copy-paste-delivered). End with a `## Datakilder` block (tools called, IDs, the date window, any source that failed). No local log is written — everything lives in the updated Drive file.
