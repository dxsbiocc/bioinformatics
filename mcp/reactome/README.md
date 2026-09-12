# Reactome MCP Server

The Reactome MCP server wraps the public Reactome ContentService with
front-end-compatible pathway records. It is metadata-first: tools return stable
Reactome URLs, browser actions, hover payloads, and preview hints, but they do
not execute downloads or local analysis.

## Tools

- `reactome_lookup`: fetch one pathway/event by stable ID such as
  `R-HSA-5633007`, optionally including participants.
- `reactome_search`: search Reactome by text, species, and type.
- `reactome_pathways_for_identifier`: map an external identifier such as a
  UniProt accession (`P04637`) to Reactome pathways via the mapping API.
- `reactome_status`: inspect local configuration and optional network health.

## Front-end Contract

Records use `display.component: "pathway"` and include:

- `display.primary_url` and `display.actions` for Reactome detail pages,
  Pathway Browser, and ContentService API links.
- `display.hover` for stable ID, class, species, participant count, reference
  count, and URL.
- `display.previews` with `network`, `table`, `citation_list`, and
  `xref_groups` hints when upstream data supports them.

Reactome API references used by this implementation:

- `data/query/{stableId}`
- `data/participants/{stableId}`
- `search/query`
- `data/mapping/{resource}/{identifier}/pathways`

