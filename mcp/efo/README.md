# EFO MCP Server

This MCP server wraps the EBI OLS4 API for Experimental Factor Ontology (EFO)
term resolution, text search, and bounded ontology expansion.

## Tools

- `efo_term_lookup`: fetch one term by CURIE, underscore ID, or full IRI.
- `efo_term_search`: search EFO terms through OLS4.
- `efo_term_children`: fetch bounded child terms for one term.
- `efo_term_descendants`: fetch bounded descendant terms for one term.
- `efo_status`: inspect local configuration and optional network health.

The implementation uses OLS4 paths such as:

- `search?q=<query>&ontology=efo`
- `ontologies/efo/terms/<double-encoded-iri>`
- `ontologies/efo/terms/<double-encoded-iri>/children`
- `ontologies/efo/terms/<double-encoded-iri>/descendants`

The server returns metadata and links only. Records use the shared
`ontology_term` component with table, network, xref group, and text previews.

