# Asset rules (Phase-3 creative — campaign assets)

Single source of truth for generating Google Ads campaign **assets** (extensions):
sitelinks, callouts, structured snippets. Lead forms are a manual UI step (not CSV-importable).
All Editor-CSV facts verified 2026-06-03 against Google's official Editor docs; UNVERIFIED items
are flagged explicitly. If SKILL.md and this file disagree, this file wins.

Mirrors Ian's skeleton tab 07 (Sitelink / Callout / Structured snippet rows).

---

## 1. The two correctness firewalls (load-bearing — do not relax)

These are the same class of rule as the RSA "never invent claims" firewall. Breaking them
ships false claims into ad infrastructure.

**Firewall A — never fabricate asset content.** Callouts ("20 års SEO-erfaring"), sitelink
descriptions, and structured-snippet values are FACTUAL CLAIMS. Generate them ONLY from the
landing-page-analyzer output (its actual fields: `usp_candidates`, `trust_signals` verbatim
with `has_numbers`, `product_service`, `on_page_ctas`, `active_offer`, `tone`) + explicit
intake. NEVER synthesize a plausible-sounding
callout ("Markedsledende", "Bedste pris") that isn't grounded. Trust numbers are verbatim from
the page or intake — never invented (same rule as RSA SKILL.md L174/L262). This is the MOST
likely drift in an asset generator: generic plausible callouts. Resist it.

**Firewall B — sitelink Final URLs are NOT derivable from the one scraped page.** Tab 07's
sitelinks point to OTHER pages (`/ai-seo-audit/`, `/ai-seo-pilot/`, `/kontakt/`) — distinct
from the single landing page Phase 1 scraped. So sitelink destination URLs CANNOT be inferred
and inventing paths is the same error class as fabricating keyword volume. Source them
consciously:
  - **Operator-supplied** (default): ask the operator for the sitelink targets (text + URL).
  - **Firecrawl site-map** (optional): `firecrawl map <domain>` to discover real URLs, then the
    operator picks which become sitelinks. Use the proven Firecrawl pattern; never guess a path.
  - If a sitelink's URL can't be confirmed, OMIT the sitelink — do not ship a guessed URL.

---

## 2. Editor CSV encoding — VERIFIED facts

Editor uses ONE flat column namespace; an asset row is identified by **which cells are
populated** (NOT by the `Type` column — `Type` only carries keyword match types + negative
flags + bid-strategy types, verified answer 57747). English headers auto-map on any install.

**Attachment level** (verified verbatim, answer 56368):
- **Campaign-level** (DEFAULT for this skill — tab 07 shows all campaign-level): `Campaign`
  populated, `Ad group` blank.
- **Ad-group-level:** both `Campaign` + `Ad group` populated.
- **Account-level:** literal string `<Account-level>` in the `Campaign` column.
- **Shared (library) asset:** both `Campaign` + `Ad group` blank.

### Sitelink (verified, answer 57747 + 56366)

| Column | Carries |
|---|---|
| `Sitelink text` | clickable link text |
| `Final URL` | destination (see Firewall B — NOT from the scraped page) |
| `Description line 1` | optional desc line 1 |
| `Description line 2` | optional desc line 2 |

Descriptions are optional but used as a PAIR (both lines or neither).

### Callout (verified, answer 57747)

| Column | Carries |
|---|---|
| `Callout text` | the callout text (one field only) |

### Structured snippet (PARTIALLY UNVERIFIED — read carefully)

| Column | Carries | Status |
|---|---|---|
| `Snippet Values` | the list of values | VERIFIED as a recognized header (answer 57747); no description cell |
| header column | the predefined header ("Services", "Platforms", ...) | **UNVERIFIED** — likely `Subject`, possibly `Header`; NOT documented |

- The header value MUST be one of Google's predefined headers, first letter capitalized
  (verified concept, answer 10702623). Don't invent a header like "Vores fordele".
- Values delimited by **semicolon** within the cell (general rule verified answer 56368;
  applying it to `Snippet Values` specifically is UNVERIFIED — confirm by round-trip).
- **BUILD-TIME CHECK:** in Editor, create one structured snippet manually → Export → CSV →
  read the exact header-column name + value delimiter. Two-minute round-trip = ground truth.
  Until then, emit `Snippet Values` + the header in a column flagged for verification.

### Lead form — NOT CSV-importable (verified negative)

No official Editor doc shows a lead-form CSV create path. Editor only EDITS existing lead
forms; "CSV" in that context = exporting submitted leads, not creating the asset. **The skill
treats lead forms as a MANUAL UI step and emits NO row for them.** If the operator wants a
lead form, say it's created in the Google Ads UI, not via this CSV.

---

## 3. Output object shape (consumed by assembler)

```json
{
  "campaign": "IC | GSN | AI-SEO",
  "attachment_level": "campaign",
  "sitelinks": [
    { "text": "AI SEO audit", "final_url": "https://inboundcph.dk/ai-seo-audit/",
      "desc_line_1": "Se jeres AI-synlighed", "desc_line_2": "Få klar prioritering",
      "url_source": "operator-supplied | firecrawl-map | omitted-unconfirmed" }
  ],
  "callouts": [
    { "text": "20 års SEO-erfaring", "grounded_in": "trust_signals: 'Etableret ...'" }
  ],
  "structured_snippets": [
    { "header": "Services", "header_column_unverified": true,
      "values": ["AI SEO", "GEO", "AI Search", "SEO", "Google Ads"],
      "grounded_in": "product_service + operator-supplied service list (analyzer has no list field)" }
  ],
  "lead_form": { "csv_importable": false, "note": "Manual UI step — Editor does not import lead forms via CSV." },
  "content_firewall": "All text grounded in landing-page-analyzer output / intake; nothing fabricated. Trust numbers verbatim.",
  "snippet_header_note": "Header column name UNVERIFIED — build-time Editor round-trip needed."
}
```

`grounded_in` is mandatory on every callout + snippet — it names the analyzer field (or
operator intake) the claim came from. If a piece of text has no `grounded_in`, it must NOT be
emitted (Firewall A).

**Note — structured-snippet values are a LIST the single-page analyzer cannot supply.** The
analyzer's `product_service` is a one-line string, and there is NO `services` list field. So a
snippet's value list must come from `product_service` decomposition the operator confirms, OR
an operator-supplied service list. Do NOT invent a 5-item service list from a one-line string —
ask the operator if the analyzer can't ground it.

---

## 4. Limits + Danish character economy

- Callout text, sitelink text: keep tight (Google truncates long assets on small screens).
  Sitelink text ~25 chars practical; callout ~25 chars practical. Danish compound words bite —
  same economy discipline as RSA headlines.
- Structured-snippet values: short noun phrases, 3-10 values typical.
- UTF-8 encoding (Danish æ/ø/å load-bearing); the assembler emits the CSV.
