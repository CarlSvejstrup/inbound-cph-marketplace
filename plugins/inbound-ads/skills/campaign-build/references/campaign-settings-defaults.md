# Campaign settings — Inbound house defaults (locked)

These are Inbound's locked campaign-settings conventions, taken verbatim from the AI-SEO
skeleton Ian had built (`InboundCPH_AI-SEO_Google-Ads-kampagneskelet.xlsx`, tab "01 Campaign
settings", row 2, 2026-06-02). The `campaign-strategy` skill reproduces these as the
**recommended defaults** for a new Search lead-gen campaign. On any conflict with generic
best practice, these win.

The 19 columns collapse into 6 coupled decision clusters. Locked default = Ian's row-2 value.

## Cluster A — Campaign type + Goal (the frame)

| Setting | Locked default | Driving signal |
|---|---|---|
| Campaign type | **Search** | Operator intent. B2B lead-gen → Search. v1 is Search-only. |
| Goal | **Leads** | Operator-stated objective; drives the bidding/conversion cluster. |
| Campaign state | **Paused** | Always emit the literal Editor status value `Paused` (Enabled/Paused/Removed). The paused-until-QA philosophy stays in the launch-gate prose; the imported value is just `Paused`. Never ship Enabled. |

## Cluster B — Bidding ↔ Volume ↔ Budget (the only real computation — see strategy logic)

| Setting | Locked default | Driving signal |
|---|---|---|
| Bidding strategy | **Maximize Conversions** | Cold-start default — no conversion history → cannot set a sane Target CPA. |
| Target CPA switch rule | **"Consider Target CPA only after roughly 30 conversions/month"** | Conversion volume. Strategy STATES the rule; it does not flip the bid at launch. |
| Budget recommendation | **"500 DKK/day initial test; adjust after Keyword Planner volume and first 14 days of data"** | Expected CPC × target clicks/day, sized to reach the ~30-conv threshold; review at 14 days. |

Target ROAS is NOT a peer default — it is the value-based path (Shopping/e-comm with
conversion values). N/A for this Leads template; surface only if the client tracks revenue
per conversion.

## Cluster C — Conversion action (two-part — do not flatten)

| Setting | Locked default |
|---|---|
| Primary conversion action | **"Alle Hubspot formular"** |
| Do not optimize toward | **"Form submit - Estimer projekt until tracking is fixed"** |

One decision, two columns: what to optimize toward + an explicit exclusion until its
tracking is verified.

## Cluster D — Targeting (locked gates, not soft preferences)

| Setting | Locked default | Note |
|---|---|---|
| Location | **Denmark** | Operator-confirmable. |
| Location option | **Presence: people in or regularly in Denmark** | Presence-only. A launch-gate Must-pass. |
| Languages | **Danish, English** | Audience-targeting language (who Google serves) — a DIFFERENT axis from RSA copy language (defaults Danish). Do not conflate. |
| Networks | **Google Search only; Search Partners off; Display off** | Partners off + Display off are both Must-pass gates. |
| Ad rotation | **Optimize** | House default. |
| Ad schedule | **All days at launch; review by hour/day after statistically useful data** | No dayparting at launch. |
| AI Max for Search | **Do not enable at launch; evaluate after clean conversion and search-term data** | Off at launch. |
| Start match types | **Exact + selected Phrase only; no Broad at launch** | LOCKED. Consumed by the Phase-2 structuring skill (which assigns match types per keyword); strategy only declares the policy. |

## Cluster E — Tracking prerequisite + Account/Campaign identity

| Setting | Locked default | Note |
|---|---|---|
| Tracking prerequisite | **Verify HubSpot form fires in Google Ads AW-921001998 before enabling campaign** | Strategy DECLARES the gate and forces state = Paused; Phase-4 QA enforces it as a Critical Must-pass. |
| Account ID | resolve via `list_accessible_accounts` match on client name | Don't type by hand. |
| Campaign name | follow Inbound naming template (below) | Ian's own AI-SEO name `IC \| GSN \| AI-SEO` is 3 tokens; the RSA template is 5. Reproduce the operator's confirmed name, offer the 5-token form as recommended. |

## Campaign naming template (reused from responsive-search-ads)

Search/Shopping/pMax: `IC | NETVÆRK | Målretning | Kampagnenavn | Eventuelt`
- NETVÆRK: `GSN`, `Shopping`, `pMax`
- Målretning: `Brand`, `Product`, `Generic`
- Examples: `IC | GSN | Generic | Alarmsystemer`, `IC | GSN | Brand | Securitas`

## Bidding/budget logic (the strategy chain)

1. No conversion history → **Maximize Conversions** (cold-start; can't set a meaningful CPA).
2. Size the budget to REACH the tCPA threshold (~30 conv/month):
   - clicks/day ≈ (30 ÷ 30) ÷ expected CVR
   - daily budget ≈ clicks/day × expected CPC (from Keyword Planner / Google Ads MCP)
   - compare against the 500 DKK/day default; if the math says it can't plausibly buy
     ~1 conv/day at the client's CPC/CVR, FLAG it rather than silently emitting 500.
3. Reassess at 14 days (budget note + launch-QA "Should pass").
4. Flip to Target CPA only after ~30 conv/month is actually observed (emit as a rule for later).
5. Target ROAS only when conversions carry revenue values (N/A here).

If the MCP / Keyword Planner CPC is unavailable (brand-new client, no account yet), fall
back to the locked 500 DKK/day WITH a flag that it is an untuned default — same
graceful-degradation as RSA Trin 2.5 when MCP is absent.
