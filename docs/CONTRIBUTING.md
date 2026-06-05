# Contributing to inbound-cph-marketplace

## Quickstart

1. Clone the repo, create a branch.
2. `cp -r skills/_template skills/<your-skill>` (once the template exists).
3. Edit `SKILL.md`. Keep the universal format. Write a crisp description — it's how Claude decides whether to fire the skill.
4. Test in Cowork against a real client folder: run `scripts/sync-to-cowork.sh`, open Cowork, trigger the skill with one of its phrases.
5. Commit, push, open a PR.

## Skill format rules

Every skill lives in `skills/<name>/` with at minimum:

- `SKILL.md` with YAML frontmatter containing `name` and `description`
- Optional: `scripts/`, `examples/`, `references/`

The YAML frontmatter is what Claude reads to decide whether to use the skill. A bad description is the #1 cause of skills not triggering.

## Description-writing guide

The description must:
- State what the skill does in one sentence
- List the trigger phrases explicitly
- Mention the domain/context (what client type, what data)

Good: *"Generate a one-page briefing on a client by synthesising brand, voice, KPIs, client-memory.md, and the last 3 meetings. Use when the user asks for a client brief, handover doc, pre-meeting prep, or says 'brief me on <client>'."*

Bad: *"Makes a client brief."*

## CODEOWNERS

Any skill that:
- Writes to client data (Drive writes, memory updates)
- Calls external APIs with credentials
- Drafts client-facing copy

...requires review from Ian before merge.

## Testing before PR

Minimum checks:
1. Skill triggers on the phrases you listed
2. Skill doesn't hallucinate data when the client folder is empty or missing a file
3. Any `client-memory.md` append is well-formed (date, structured sections, newest-on-top convention)
4. Voice is on-brand for the test client (usually Nordkap in this repo's demo context)
