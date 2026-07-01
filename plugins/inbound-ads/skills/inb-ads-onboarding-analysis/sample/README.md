# Sample output — real end-to-end live run

These two files are the output of an actual end-to-end run of `inb-ads-onboarding-analysis` against the live
Dantaxi account (414-979-1707) on 2026-06-10. Not a mock, not a hand-built subset , the full skill
flow produced them.

- `findings-example.json` — the assembled findings object from the run. All **35 points across all
  9 modules (A-I)**, each with a status (ok/warn/critical/no_data) and a Danish finding grounded in
  live Google Ads data (user-access roles, conversion-action values, ad_strength distribution,
  network settings, keyword match-types, QS, etc.).
- `Opstartsanalyse - Dantaxi (live-run) - 2026-06-10.docx` — the .docx `build_docx.py` produced
  from that JSON. Two layers:
  - **Checklist / indholdsfortegnelse** up top: all 35 points with **two checkboxes per point** ,
    an **Agent** column the skill fills (✓ = agent reached a verdict / ☐ = couldn't assess) and an
    **Ekspert** column for the specialist to tick by hand after review.
  - **Detail tables per module**: the status (OK/warn/critical) + the concrete finding per point.
  The agent checkbox means "did the agent walk the point", NOT "is it OK" , a critical finding
  shows ✓ in the Agent column and red Kritisk in the detail. The agent proposes, the expert disposes.
  Note: only **judgment** points (the agent's opinion , is the copy good? is broad controlled?) get
  an Ekspert checkbox. **Lookup** points (factual reads , does an extension exist? is display select
  off?) have a blank Ekspert cell, because there's nothing to re-verify. Each point's `kind`
  (`lookup`/`judgment`) is set in `references/analysearbejdet.md`.

This run's tally: 3 critical / 15 warn / 16 OK / 1 no_data; agent checklist 34 ✓ / 1 ☐ (point 8
Location extension = N/A for a taxi service, correctly no_data).

## How the run worked (the orchestration this proves)

The full SKILL.md flow ran, not a shortcut:
1. **Phase 0 offering sub-agent** scraped the landing pages + account signals → high-confidence
   profile (caught that Uber is a partner not a competitor, and that 9+ pax bus transport is
   out-of-scope).
2. **Parallel verification sub-agents** covering all 9 modules, each pulling its own GAQL via
   `run_custom_gaql` (ENABLED campaigns only), returning clean per-module JSON.
3. **Assembly** merged the 9 module objects + headline findings → this findings JSON.
4. **`build_docx.py`** rendered the .docx.
5. The run **stopped at the gated Drive-write proposal** , it did not upload (human-in-the-loop).

## Regenerate

```bash
python3 ../lib/build_docx.py --in findings-example.json \
  --out "Opstartsanalyse - Dantaxi (live-run) - 2026-06-10.docx"
```

The overblik band (OK / kan forbedres / kritisk / mangler data counts) is computed by the builder
from the module items , it is not read from the JSON, so it always matches the rendered rows. The
checklist coverage line ("X af 35 behandlet") is likewise computed.
