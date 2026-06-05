# Page-extraction contract (shared)

This is the **single source of truth** for extracting positioning data from a web page.
Three skills run this same extraction and must not drift:

- `landing-page-analyzer` — points it at the **client's** landing page.
- `competitor-research` — points it at each **competitor's** owned page.
- `responsive-search-ads` Trin 2 — currently scrapes the client page inline; will later
  consume `landing-page-analyzer`'s output instead (Phase-3 integration, not yet done).

The field list, the firewall rules, and the JSON shape below are canonical. If this file
and a skill disagree, this file wins. The machine-readable schema is
`page-extraction-schema.json` in this same directory (the field contract you extract against).

## What to extract

| Field | What it is |
|---|---|
| `product_service` | What the page sells (one line). |
| `brand` | `{ name, logo_text }` — brand identity. |
| `usp_candidates` | Differentiators the page leads with (list). |
| `tone` | One of: `formel`, `venlig-direkte`, `teknisk-praecis`, `energisk-inspirerende`. |
| `on_page_ctas` | Action phrases on the page ("Få et tilbud", "Bestil demo"). |
| `trust_signals` | List of `{ claim, has_numbers }` — review scores, customer counts, year established, certifications, awards. |
| `active_offer` | `{ present, text, expiry }` — a live promotion if one is on the page. |
| `page_language` | Detected language code (`da`, `en`, `sv`, `no`, ...). |

## The three firewall rules (load-bearing — do not relax)

These come from the shipped RSA skill and exist because breaking them causes real harm
(invented claims, auto-disapproved ads, silent language switches).

1. **Trust signals are verbatim and never invented.** Carry the exact on-page string in
   `claim`; set `has_numbers: true` only when the string contains a usable number. If the
   page has no numeric proof, the list is empty — do not synthesize "trusted by many".
   (RSA SKILL.md L174, L262: "Vi må IKKE finde på tal" / "Vi opfinder ikke claims".)

2. **Offer expiry is mandatory when an offer is present.** If `active_offer.present` is
   true, capture `expiry` as a date, or `"unknown"` if the page states no date. Downstream
   treats `"unknown"` as "do NOT put expiry-bound claims in ad copy" — because an expired
   offer in live ad text triggers Google auto-disapproval. (RSA SKILL.md L172.)

3. **Page language is detected, never assumed, and mismatches are surfaced.** Emit the
   detected `page_language`. If it may differ from the operator's chosen ad-text language,
   set `language_note`. Never silently switch language for downstream copy. (RSA L260.)

If the page cannot be fetched: say so and stop. Do not invent any field.

## Output JSON shape

```json
{
  "source_url": "https://...",
  "scraped_at": "<ISO-8601, stamp after the run>",
  "scrape_tool": "web_fetch + LLM extract",
  "product_service": "string",
  "brand": { "name": "string", "logo_text": "string|null" },
  "usp_candidates": ["string", "..."],
  "tone": "formel | venlig-direkte | teknisk-praecis | energisk-inspirerende",
  "on_page_ctas": ["string", "..."],
  "trust_signals": [
    { "claim": "4.8 stjerner fra 2.300 anmeldelser", "has_numbers": true }
  ],
  "active_offer": { "present": false, "text": "string|null", "expiry": "YYYY-MM-DD | unknown | null" },
  "page_language": "da",
  "language_note": "string|null",
  "extraction_confidence": "high | partial | low",
  "missing_fields": ["..."]
}
```

`extraction_confidence` and `missing_fields` are set honestly by the skill after reading
the scrape: `partial`/`low` when key fields (USPs, trust, offer) could not be found, with
the gaps listed in `missing_fields`. Downstream uses these to know how much human input
the structuring gate still needs.

## How to run the extraction

Fetch the page with the built-in **`web_fetch`** tool, then YOU (the model) extract the
fields below from the returned page content. The extraction is LLM reading, not a CLI flag,
and `web_fetch` works in Cowork (no CLI dependency).

Call `web_fetch` on the URL, asking for the page's full content (product/service, USPs,
on-page CTAs, trust signals **with their exact numbers**, any active offer + expiry, brand,
language). Then populate the output JSON shape, applying the three firewall rules. The
`page-extraction-schema.json` in this directory is the **field contract you extract against**
(and a validation target) — it is NOT passed to the tool.

**Verbatim guarantee (load-bearing).** Firewall rule 1 (trust signals verbatim, never
invented) depends on you reading the page's ACTUAL text. If a `web_fetch` response comes back
as a short summary that has dropped the concrete numbers/claims/CTAs, fetch again with an
explicit instruction to return the raw page text with those intact. Never fill a trust number
or offer from memory or inference — if the page content you got doesn't contain it, the field
is empty.

Reads are free under the write-gate; fetching a public page needs no approval, but disclose
which URL was hit. The fetched content is candidate data; the firewall is yours to enforce.
