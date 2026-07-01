# Section contract: the canonical AI-Context layout

The one true section set for every client's AI-Context file (the `.md` linked from the master index) AND the local `clients/*.md` mirror. Both surfaces use the same headings so an agent can find the same thing in the same place on any client. This file is the source of truth for that layout; `insertion-and-resync.md` points here for the file shape.

Two audits over the client set found the `## Klientoverblik` block is already uniform everywhere, but the surrounding H2 sections drifted into two generations (an old scattered set with thin one-liners, and a newer consolidated set). This contract retires the scattered set by **folding**, never deleting content.

## Canonical H2 set

```
## Konti & links              # durable account facts: Google Ads ID, account link, Bing y/n, pacing-ark y/n
## Kontaktpersoner            # client-side + Inbound-side + partners (### subgroups OK)
## Kunderelation & noter      # soft relationship context, history, upsell posture
## Klientoverblik             # THE agent brief — the 5-part block below, kept clean and durable
    ### Overblik
    ### Hårde rammer (læs før du handler)
    ### Mål & konverteringer
    ### Sådan kører vi den
    ### Aktuel status & åbne håndtag
## Rapport                    # newest status-deck summary — own section, watermarked, replaced-with-latest
## Aftaleark & kundebrief     # link to the Aftaleark + durable facts folded from it
## Drive files                # ranked file index (### Important / ### Less relevant)
```

**Ordering (relaxed — reflects the real corpus).** These are the only allowed H2 sections, but the three durable-context sections (`## Konti & links`, `## Kontaktpersoner`, `## Kunderelation & noter`) and `## Klientoverblik` may appear in either arrangement relative to each other: in practice about a third of notes place `## Klientoverblik` *before* the contact/relation sections, and that is fine. Do NOT reorder an existing note just to move these around — it is a large, risky, low-value edit. What IS load-bearing and must hold:

- `## Rapport` sits **immediately after `## Klientoverblik`** (it is the watermarked report section this skill owns).
- `## Aftaleark & kundebrief` then `## Drive files` come **last**, in that order.
- `## Konti & links`, when present, comes first.

Not every client has every section (a thin client may omit `## Kunderelation & noter` or `## Rapport`). Omit an empty section rather than writing a stub. Never introduce a section outside this set, and never split `## Klientoverblik` into two.

## `## Klientoverblik` is fixed (do not restructure)

The 5 `###` subsections are the stable agent brief and are uniform across all clients. Keep them, in order, and only omit one if it would be genuinely empty. The timeless rule (`diff-classification.md`) governs what may live inside. This skill replaces the whole block in one piece (see `insertion-and-resync.md`); it never adds a 6th subsection or renames one.

## The fold-map (legacy H2 -> where it goes)

When migrating a note that still carries the old scattered set, fold each legacy H2 into a canonical home. Move the *durable* content; drop pure point-in-time one-liners per the timeless rule.

| Legacy H2 | Folds into | Note |
|---|---|---|
| `## Om virksomheden` | `### Overblik` | the "who they are" line |
| `## Budget` | `### Overblik` | budget/md is a durable fact; keep the number, drop spend history |
| `## Vigtigste kampagner` | `### Sådan kører vi den` (or `### Overblik`) | account structure / market focus |
| `## KPIer og mål` | `### Mål & konverteringer` | goals + conversion actions |
| `## Rapporter & logs` | superseded | the changelog link lives in `## Konti & links`; status decks live in `## Rapport` |
| `## Senest lavet` | `### Aktuel status & åbne håndtag` | recast as a durable lever, not "we did X last month" |
| `## To-dos & andre noter` | `### Aktuel status & åbne håndtag` | open levers only; drop stale to-dos |

**Fold, don't lose.** A thin legacy one-liner ("Link", "Vroom vroom") that carries no durable fact is dropped, not migrated. Anything with a real durable fact (a budget number, a contact, a naming convention, an open lever) moves to its canonical home. When in doubt whether a line is durable, keep it in `### Overblik` or `### Aktuel status` rather than deleting.

## Reconcile-flag: resolve by folding, never blind-delete

`## Reconcile-flag` / `### Reconcile-flag (YYYY-MM-DD)` is a sync artifact from `inbound-ads-clients-sync`, not a canonical section — but it is NOT noise. It routinely carries durable ground-truth decisions (a confirmed Google Ads account ID, why `stage` was omitted, a budget-split nuance, "Paid Search moved to another agency", a NEEDS-PICK HubSpot-ID caveat). Deleting it loses real curated context.

**On migration, resolve it:**
1. Read every bullet. For each, decide: is this a durable fact, or a spent one-time reconcile note?
2. **Durable facts fold to their canonical home:** a confirmed account/ID → `## Konti & links` (and it's usually already in frontmatter); a stage/why-omitted rationale, a "no longer running Paid Search", a budget nuance, a market/contact clarification → the matching `### Klientoverblik` subsection (`### Overblik`, `### Hårde rammer`, or `### Aktuel status & åbne håndtag`) or `## Kunderelation & noter`. A live "bør bekræftes"/NEEDS-PICK caveat → keep it as a one-line note in the most relevant durable spot so it isn't forgotten.
3. **Only genuinely spent notes** ("intet flag nødvendigt", "ingen konflikt", pure process-of-how-the-sync-ran) are dropped.
4. Then remove the `Reconcile-flag` heading. If folding leaves nothing, the whole section goes; if a bullet was durable, it now lives in a real section.

When unsure whether a bullet is durable, fold it rather than drop it. These appear only in the local `clients/*.md` mirror, not the Drive AI-Context file (the Drive file never had them).

## Migration mode (batches, not lazy)

The pilot (Dantaxi) is migrated by hand to prove the layout. The remaining notes are migrated in **explicit batches** on request — not opportunistically inside a normal `inb-ads-client-brief` run. A normal run edits only `## Klientoverblik` + `## Rapport` (its watermark sections) and does NOT silently refold the rest of a note. Folding the legacy H2s is a separate, deliberate migration pass so the diff stays reviewable.
