# Open Targets MCP Server

This MCP server wraps the public Open Targets Platform GraphQL API for compact,
front-end-compatible retrieval.

## Tools

- `opentargets_target_lookup`: fetch a target by Ensembl gene ID, including
  associated diseases, overall scores, datasource scores, datatype scores, and
  browser links.
- `opentargets_disease_lookup`: fetch a disease or phenotype by Open Targets
  disease ID such as `MONDO_0004979`, including associated targets and ontology
  cross-references.
- `opentargets_search`: search target and disease entities and return clickable
  Open Targets hits.
- `opentargets_status`: inspect local configuration and optionally run a small
  metadata network check.

## Front-end Records

Results return `structuredContent.records[]` with shared record envelopes:

- target lookup -> `display.component = "gene"`
- disease lookup -> `display.component = "dataset"`
- search -> `display.component = "identifier_conversion"`

Each record includes `display.primary_url`, clickable `display.actions`, hover
fields, table previews for associations or search hits, and grouped
cross-reference previews. MCP output provides rendering hints only; the Codex
app owns visual rendering and link opening.
