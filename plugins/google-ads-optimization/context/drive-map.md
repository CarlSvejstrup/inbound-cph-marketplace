# Inbound Drive map

The Inbound CPH Google Drive is the source of truth for all client work. Skills in this plugin assume this shape.

## How skills find Drive

This plugin does **not** bundle a Google Drive MCP. It relies on the Drive connector that Cowork provides built-in (`mcp__claude_ai_Google_Drive__*` tools). Each user authorises Drive once at the Cowork level; this plugin reuses that auth.

The root folder ID is configured via the plugin's `userConfig.inbound_root_folder_id`. Default: `17JwnWKToZSJUSCURjS9PzzBeqe6_gPfi` (the shared `inbound-cph/` folder). Users can override at install time if they have a different mount.

When a skill needs to read from Drive, it should use the Drive search/read tools and scope by parent folder ID = `${user_config.inbound_root_folder_id}`. From there, walk into `<client>/01-brand/`, `<client>/04-memory/`, etc.

## Root layout

The `inbound-cph/` folder contains one subfolder per client at the top level. Each subfolder name matches the client identifier used in skill invocations (e.g. client `nordkap-friluft` → folder `nordkap-friluft/`).

For demo and evaluation, the canonical client is **Nordkap Friluft**, in folder `nordkap-friluft/` (folder ID `1Ca6_V4v57h7NDVQS0NRI-yP47gh_QTa9`).

## Per-client folder shape

Every client folder follows this structure:

```
<client>/
  01-brand/
    brand.md          positioning, target customer, strategy
    voice.md          editorial voice rules (do/don't, banned words, register)
    kpis.md           metrics, current values, targets
  02-past-reports/    historical deliverables (PDFs, slides, sheets)
  03-meetings/        meeting notes, named YYYY-MM-DD-<topic>.md
  04-memory/
    client-memory.md  rolling institutional memory (newest first), the moat
  05-data/            CSVs, Semrush exports, snapshots
  06-decisions/       decision logs, named YYYY-MM-DD-<topic>.md
```

## Conventions

- Filenames in `03-meetings/` and `06-decisions/` start with ISO date `YYYY-MM-DD-` so they sort chronologically.
- `04-memory/client-memory.md` is append-only (newest at top). Never rewrite history.
- `01-brand/` files are slow-moving; if you find yourself wanting to update them often, the change probably belongs in `04-memory/` instead.
- Anything that does not fit one of the six folders probably belongs in `02-past-reports/` or `05-data/`, do not invent new top-level folders.

## When the shape is broken

If a client folder is missing one of the six subfolders, surface it to the user. Do not silently scaffold or guess. The shape is intentional and breaking it usually means the client was onboarded incorrectly.
