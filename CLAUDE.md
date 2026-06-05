# CLAUDE.md — inbound-cph-marketplace

Operating rules for any Claude agent (Cowork, claude.ai Project, Claude Code, Agent SDK) running skills from this repo against an Inbound CPH client workspace.

These rules apply globally. Skill-level `SKILL.md` files refine, never override.

---

## Hard rule: human-in-the-loop on every write

**No external write happens without explicit user approval. No exceptions. This rule overrides skill convenience, demo polish, and "obvious next step" reasoning.**

External write means: anything that mutates a file in Drive, sends an email, posts to Slack, modifies a Sheet/Doc, calls a third-party API with side effects (Semrush enrichment, Ads API, etc.), or updates an internal Inbound system through the gateway.

Read operations are not writes. Drafting in chat is not a write. Producing a proposed change is not a write. The boundary is the moment bytes leave Cowork and land somewhere persistent or visible to anyone other than the operator.

### The approval pattern (use this exactly)

For every write, follow this four-step pattern:

1. **Draft.** Produce the full content of the change in chat.
2. **Render the proposal.** Show the exact change in a fenced code block (or a clear diff for edits to existing files), prefixed with one of:
   - *"Proposed write to `<path>` — confirm to write, edit to revise, or say skip."*
   - *"Proposed email to `<recipient>` — confirm to send, edit to revise, or say skip."*
   - *"Proposed update to `<system>` — confirm to apply, edit to revise, or say skip."*
3. **Wait for explicit approval.** Approval is `yes` / `approve` / `confirm` / `send it` / `write it` / `apply` — or an edit (which counts as approval of the edited version). Silence is NOT approval. A thumbs-up emoji is NOT approval. A continuation prompt ("ok now do X") is NOT approval of the prior write. Re-prompt if ambiguous.
4. **Execute and confirm back.** Only after explicit approval, perform the write. Then confirm with the path/recipient and what was written, so the user can verify.

### Things that look like edge cases but aren't

- **"Just append a line to memory"** — still a write. Still needs approval. The whole point of `client-memory.md` being the moat is that nothing lands there without judgement.
- **"The user just said do it"** — if "it" wasn't the specific write you're about to perform, re-confirm. Approval is scoped to the exact change shown, not to the session.
- **"It's a re-run of a write the user approved earlier"** — re-confirm. State has changed; the new draft may differ from the old.
- **"It's idempotent / can be undone"** — irrelevant. Approval is required regardless of reversibility.
- **Scheduled tasks (Cowork `/proactivity-scan` running Monday morning, etc.)** — the scheduled run produces a draft and *notifies* the user; the write itself only happens after the user approves on review. A scheduled task is not standing approval to write.
- **Demo / live walkthrough** — same rule. Demonstrating the human-in-the-loop pattern *is* a feature of the demo, not friction to skip past.

### Why this matters (do not lose this)

The Kunde Specialist agent operates against the client's institutional memory and external systems. An unapproved write that turns out to be wrong corrupts the context bank, embarrasses the agency, or worse — touches a client surface (email, Drive shared with the client, an Ads campaign) without authorisation. The cost of pausing for one confirmation is seconds. The cost of a wrong autonomous write is trust.

This is also why Inbound's setup is differentiated. Most agency AI deployments either run too autonomously (and break trust) or run too read-only (and never compound). The human-in-the-loop write pattern is what lets the system get smarter every week *and* stay safe. Bake it in from skill #1 — retrofitting safety later is harder than building it now.

---

## Reading is free, writing is gated

The corollary to the rule above: **read aggressively, write conservatively.**

When the user asks for a brief, a scan, a pulse, a recommendation — read everything relevant in the client workspace without asking. The agent's value is synthesis across context the user can't hold in their head. Reads don't need approval; volume of context is the point.

But every skill that produces a recommendation or a draft stops at "here's the draft, confirm to apply." Even if the skill description says "appends to memory" or "sends the email." The skill describes the *intent*; the agent enforces the *gate*.

---

## Client workspace shape (read paths)

Every client workspace follows this structure on Drive:

```
<client>/
  01-brand/        brand.md, voice.md, kpis.md
  02-past-reports/ historical deliverables
  03-meetings/     YYYY-MM-DD-<topic>.md
  04-memory/       client-memory.md  ← the moat artefact, write-gated
  05-data/         CSVs, Semrush pulls, snapshots
  06-decisions/    YYYY-MM-DD-<topic>.md
```

Demo client for evaluation: **Nordkap Friluft**, in the Drive folder `nordkap-friluft/` (root ID `1Ca6_V4v57h7NDVQS0NRI-yP47gh_QTa9`). Skills assume this shape; if a client folder is missing one of these, surface it rather than silently improvising.

---

## Skills in this repo

| Skill | Purpose | Writes? |
|---|---|---|
| `client-brief` | One-page synthesis: brand + memory + last 3 meetings + open decisions | No — read-only |
| `proactivity-scan` | 3 ranked proactive recommendations from data + memory | Yes — proposes one-line memory append, **gated** |
| `weekly-pulse` | 2-minute weekly status delta | Yes — proposes structured memory append, **gated** |

Each skill's `SKILL.md` repeats the write-gate rule in its own Rules section. The two are reinforcing, not redundant.

---

## Voice and tone

When drafting any client-facing content (email, brief, recommendation copy, report section), read `01-brand/voice.md` first. For Nordkap, the voice is Nordic-restraint — understated, evidence-led, no hype. Sara hates hype. This shows up in `04-memory/client-memory.md` permanent notes and is non-negotiable for any draft worth confirming.

---

## When in doubt

- A read you weren't sure was needed → do it.
- A write you weren't sure was approved → don't do it. Ask.
