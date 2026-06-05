# Semrush research contract (Phase-1, gated)

Single source of truth for the `semrush-research` skill: what it pulls from the Semrush MCP,
the JSON it emits, how it degrades when the plan-gate fires, and the bindings that are
**UNVERIFIED until Semrush access exists**. If SKILL.md and this file disagree, this file wins.

> **STATUS — gated, spec-now / bind-on-access (2026-06-05).** Carl does not yet have a Semrush
> plan with MCP access. Verified live: every Semrush report returns a plan-gate stub instead
> of data. So this skill is a **working gated skeleton** — it detects the gate, degrades
> cleanly, and is wired into Phase 1 — but every report name, parameter, and field binding
> below is **UNVERIFIED** and must be confirmed via a real discover→schema→execute pass the
> first session access lands. Do NOT assert any field shape as fact until then. This is the
> exact discipline that the `--schema-file`, phantom `services`, and `.xlsx`-import errors
> taught: never bind to an unseen MCP surface.

---

## 1. The MCP shape (verified) + the gate (verified)

The Semrush MCP uses a **discover → schema → execute** pattern:
1. A discovery tool per family (`keyword_research`, `organic_research`, `trends_research`, …)
   returns the available report names. **Call it with no args first.**
2. `get_report_schema(report=...)` returns that report's parameters.
3. `execute_report(report=..., params={...})` runs it.

**The gate (verified live 2026-06-05):** with no plan, EVERY call returns a stub:
> "If you can see this response, the user does not have a Semrush plan that includes MCP
> access… inform the user that their current plan does not support this feature…"

**Per-family gating (inferred from the stub's routing text, NOT separately probed).** A single
`keyword_research()` probe returned a stub whose own text routes to TWO different plan pages
depending on the family:
- **Traffic analytics** (`trends_research`) → `https://www.semrush.com/analytics/traffic/trends-api`
- **Everything else** (keyword, organic) → `https://www.semrush.com/mcp-access`

That routing rule implies access is **per-report-family, not one global boolean** — but it was
NOT confirmed by probing `trends_research()` separately and watching it route to the traffic
page. The design consequence is safe either way (degrade per family, no global flag), so:
treat access as per-family, detect the stub per family, degrade independently. Do NOT model a
single `semrush_available` flag. **Confirm by probing trends separately on access (see §5).**

---

## 2. What v1 pulls (SETUP only — UNVERIFIED report names)

Three families, mapped to the Phase-1 need. Report names below are PLACEHOLDERS — bind to the
real names returned by each discovery tool on access.

| Family | Why (which downstream gap it fills) | Likely reports (UNVERIFIED) |
|---|---|---|
| **keyword_research** | Fills the proven Phase-2 gap: real **search volume, difficulty, CPC** for the keyword candidates structuring generates. Today those are theme-derived, "validate in Keyword Planner." | volume / difficulty / CPC, related keywords, questions, SERP features |
| **organic_research** | What the client's domain ALREADY ranks for → seeds + validates structuring's keyword set + landing-page-analyzer positioning. Also keyword-gap vs competitors (future). | organic keywords for a domain, competitors, keyword gap |
| **trends_research** | Geo distribution + seasonality → campaign-strategy's geo-targeting + budget-timing. **Separate access tier (see §1).** | traffic by geo, trend over time |

**NOT in v1:** paid-keyword / ad-copy reports (those are competitive *ad* intel → an
optimization-plugin concern, deferred); the cross-client substrate (parked H2).

---

## 3. Output JSON shape (consumed by structuring + campaign-strategy)

```json
{
  "domain": "https://...",
  "seed_terms": ["...", "..."],
  "geo": "DK",
  "semrush_access": {
    "keyword": "available | gated | error",
    "organic": "available | gated | error",
    "trends":  "available | gated | error"
  },
  "keyword_data": [
    { "keyword": "ai seo bureau", "volume": null, "difficulty": null, "cpc_dkk": null,
      "source": "semrush | UNAVAILABLE", "verified": false }
  ],
  "organic_keywords": [
    { "keyword": "...", "position": null, "url": "...", "source": "semrush | UNAVAILABLE" }
  ],
  "trends": { "geo_split": null, "seasonality": null, "source": "semrush | UNAVAILABLE" },
  "gate_notice": "Semrush <family> unavailable on current plan — see <plan page>. Downstream uses the theme-derived fallback.",
  "fallback_used": true
}
```

- `verified: false` until a real run binds the field — flip to true only after access +
  smoke-test. Numeric fields are `null` while gated.
- `source` per row makes the provenance honest: a keyword is `semrush` (volume-backed) or
  `UNAVAILABLE` (still theme-derived, validate in Keyword Planner).

---

## 4. Degradation (mandatory — Semrush enriches, never blocks)

1. Call the discovery tool for each needed family.
2. **If the response is the plan-gate stub:** mark that family `gated` in `semrush_access`,
   set its data to `UNAVAILABLE`/`null`, and continue. The build does NOT stop.
3. **Surface the gate notice SEPARATELY** — the stub itself instructs "do not merge the
   subscription message with other tool results." So report it as its own line, not folded
   into the keyword table. Use the plan page the stub returned (per family).
4. Downstream (structuring keyword generation, campaign-strategy geo/budget) runs on the
   existing **theme-derived fallback** exactly as it does today with Semrush absent. This
   skill only ADDS volume grounding when available.

The structuring keyword path MUST still work with this skill returning all-`UNAVAILABLE`.
That is already true (structuring generates theme-derived keywords + the volume disclaimer).

---

## 5. Bind-on-access checklist (run the first session Semrush works)

1. `keyword_research()` / `organic_research()` / `trends_research()` with no args → record the
   REAL report names. Replace the §2 placeholders.
2. `get_report_schema(report=<real name>)` for each → record the REAL params (domain? db?
   geo code format? phrase?).
3. `execute_report(...)` a real query for a known client → record the REAL field names +
   shapes. Replace the §3 `keyword_data`/`organic_keywords`/`trends` field bindings.
4. **Wire each consumer's intake to read `semrush-research.json`** — this is the step that
   actually makes the data flow, and nothing does it today: structuring SKILL.md Trin 0
   (add `semrush-research.json` to the inputs it consumes) and campaign-strategy intake (read
   `trends` for geo/budget-timing). Without this, real emitted data is never picked up.
5. Smoke-test the full skill against one real client; flip `verified: true` on bound fields.
6. Reconcile the §6 touchpoints from "future enhancement" to "live, with fallback."
7. Re-confirm per-family gating held — probe `trends_research()` separately and watch which
   plan page it routes to (did trends need a separate tier?).

---

## 6. Touchpoints to reconcile (don't fork the story)

Three downstream skills relate to this one. When this skill binds on access, each gains an
"…or Semrush via `semrush-research` if available" branch — they gain a branch, they don't get
contradicted. The generation/relationship notes are already added; the **intake wiring** (which
makes data actually flow) is the §5.4 bind-on-access step, NOT done while gated:
- `structuring/references/structuring-rules.md` §2 — generation note added (consume
  `keyword_data[]` rows with `source: semrush`). **Intake wiring (Trin 0 input list) deferred to
  §5.4.**
- `campaign-strategy/SKILL.md` — consumes `trends` for geo-targeting + budget-timing. **No note
  or intake wiring yet — both deferred to §5.4** (don't wire while the data is all-`null`).
- `competitor-research/SKILL.md` — upgrade note added (`organic_research` → optional discovery
  source; stays Firecrawl-primary). No intake change needed (it's a discovery enrichment).

These stay TRUE while gated; the branches + intake wiring activate only once bound.

---

## 7. Hard rules

- **Read-only.** Semrush reports are reads; no external writes, no API push (campaign-build
  rule). Disclose which domain/keyword was queried.
- **Never a dependency.** Semrush enriches Phase-1 research; its absence never blocks the build.
- **Setup-only in v1.** Optimization-plugin use (organic keyword-gap + competitor ad copy into
  search-terms/ads-audit) is deferred — and note the cross-plugin boundary: `${CLAUDE_PLUGIN_ROOT}`
  resolves only within one plugin, so optimization would need its own copy/skill, not a shared
  reference into setup.
