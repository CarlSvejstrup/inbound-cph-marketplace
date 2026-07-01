# Diff classification: TILFØJ / ERSTAT / FJERN

How the skill turns "what's new since last sync" **from Drive documents + HubSpot + Ads** into proposed edits to the AI-Context file's `## Klientoverblik`. This file covers the diff + the confirm-gating; the timeless rule below is the skill's own contract (it matches how the AI-Context files were originally built by `ai-context-publish`).

**Report content is out of scope here.** Status-deck (rapport) content does NOT go through this diff — it gets its own standalone `## Rapport` section via `report-ingestion.md`, kept separate from Klientoverblik. Only the three live sources above feed the ADD/REPLACE/REMOVE diff.

## What is editable

The skill edits **only the AI-Context file on Drive** (the `.md` linked from the index). Within it:

| Part of the AI-Context file | Editable? | Gate |
|---|---|---|
| `## Klientoverblik` (all ### subsections) | Always | TILFØJ batched; ERSTAT/FJERN per-item |
| ID-block lines that are durable + now wrong (e.g. a changed contact, a newly-found `Rapporter:` link) | Only on strong new evidence | ERSTAT/add per-item |
| The `Sidst opdateret:` line | Always (the watermark) | bumped on a clean run |
| Any other section (Om virksomheden, Drive-filer, the changelog LINK) | Not touched by this skill | — |

"Strong new evidence" = a dated, authoritative source (a status deck, a CRM contact change, a new doc) that directly contradicts or supersedes the current text. A vague mention is NOT strong evidence — propose nothing, or propose a TILFØJ note, never a silent overwrite.

## The three buckets

- **TILFØJ (addition):** a new durable fact not yet in the brief (a new festival campaign, a new conversion action, a new contact, a new structural caveat, a newly-found report folder). Append-only, low-risk. **Lighter gate:** show all proposed additions, apply after one batched `ja`/`vælg numre`/`nej`.
- **ERSTAT (replacement):** a current line is now wrong/outdated and a newer source gives the corrected value (a changed contact email, a superseded bid-strategy norm, an updated budget cap). **Hard gate:** show the exact current text + the proposed replacement + the source; one explicit confirm per item (or an explicitly-listed set). Never under a blanket yes.
- **FJERN (deletion):** a current line is stale/closed/superseded with no replacement (an "åbent håndtag" the latest deck marks done, a splittest that concluded, a contact who left). **Hard gate:** show the exact text to remove + why (with source); one explicit confirm per item.

**Be critical, not destructive.** The skill's job on ERSTAT/FJERN is to *propose* and *argue* ("rapporten fra maj markerer Jylland-vs-Sjælland-splittesten som afsluttet → foreslår FJERN af håndtaget"), then let the human decide. Never drop or rewrite a curated line silently. Default to surfacing rather than acting when uncertain.

## The timeless guard on TILFØJ (runs before any addition is shown)

The Klientoverblik is **durable operating context, not a performance snapshot**. Every proposed TILFØJ must pass: **"om 3 måneder med en ændret konto — er dette stadig SANDT, eller bare FORÆLDET?"**

**Refuse to propose adding (merely stale):**
- Any live metric: ROAS, CPA, CPC, CTR, spend figures, conversion/click/impression counts, "% spild", impression-share %, "X enabled / Y aktive kampagner", any `LAST_30_DAYS` performance block.
- Present-tense performance verdicts even with the number stripped — "Jylland er profitabel", "konkurrenterne er dyre og ineffektive". De-numbering does not make these durable; it makes them stale-without-evidence (worse).

**Recast, don't drop:** turn a useful stale verdict into a durable LEVER:
- "Jylland er profitabel" → "hæv budget hvor markeder er profitable-men-capped — verificér aktuel tilstand først".
- "CPA landede på 18 kr." → drop entirely (a measurement, no durable form).

**Always keep / OK to add (still true after the account changes):** naming conventions, bid-strategy NORMS, market focus, contacts, budget/md, tier, agreement terms; qualitative structural intent ("PMax spiller awareness-rolle"); structural tracking caveats describing how the account is *configured* ("TOP 2 dobbelttæller") — timeless until fixed, no metric attached; durable open levers/to-dos.

**Settings vs measurements (the one over-strip trap):** a *configured* tCPA/tROAS/budget cap is a SETTING and is durable ("tCPA sat til 20 kr." stays). A *measured* CPA/ROAS is a snapshot, strip it ("CPA landede på 18 kr." goes).

## The review table (what the human sees)

One Danish table, then the gated confirms:

```
| # | Type   | Sektion              | Nuværende                        | Foreslået                         | Kilde                         |
|---|--------|----------------------|----------------------------------|-----------------------------------|-------------------------------|
| 1 | TILFØJ | Sådan kører vi den   | (mangler)                        | Tinderbox-festivalkampagne tilføjet | Drive: 2026-06-20 festival-ark |
| 2 | ERSTAT | Overblik → Kontakt   | Natasha (nbn@moovegroup.com)     | Natasha (nbn@dantaxi.dk)          | HubSpot: kontakt opdateret 2026-06-19 |
| 3 | FJERN  | Åbne håndtag         | "5-ugers splittest afventer grønt lys" | (fjernes — markeret afsluttet) | Rapport: maj-statusdeck       |
```

Then: "TILFØJ: skal jeg tilføje 1? (ja/vælg/nej)" → batched. "ERSTAT/FJERN: bekræft hvert punkt — fjern 3? erstat 2?" → per-item. Apply only the approved ones into the new `## Klientoverblik` block (written to the AI-Context file in Trin 6).
