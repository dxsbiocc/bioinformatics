# STRING MCP Server

This server wraps the public STRING API for protein identifier mapping and
protein-protein association previews. It uses the official JSON endpoints
documented at `https://string-db.org/help/api/` and returns
front-end-compatible records under `structuredContent.records`.

## Tools

- `string_map`: resolves gene symbols, UniProt accessions, or other protein
  identifiers to STRING IDs.
- `string_interactions`: resolves seed identifiers and returns an app-renderable
  protein interaction network with nodes, edges, STRING scores, hover metadata,
  and external URLs.
- `string_status`: reports configured capabilities and optional network health.

## Front-end Contract

Use `records[]` first. `string_map` returns `identifier_conversion` records.
`string_interactions` returns a `protein_network` record with:

- `display.primary_url` pointing to the STRING browser page.
- `display.previews[]` containing a `network` preview with `data.nodes` and
  `data.edges`.
- a `table` preview for top interactions.
- hover fields and actions that the app can render without database-specific
  URL construction.

The MCP does not render graphs itself and does not download bulk data.

## Environment

- `STRING_BASE_URL`: override the API base URL. Default:
  `https://string-db.org/api`.
- `STRING_CALLER_IDENTITY`: caller identity parameter sent to STRING. Default:
  `codex-bioinformatics-string-mcp`.
- `STRING_TOOL`: user agent tool name.
- `STRING_CONTACT`: optional contact used in the user agent.
