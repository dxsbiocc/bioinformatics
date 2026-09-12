# QuickGO MCP

QuickGO MCP wraps the official EBI QuickGO REST API for Gene Ontology terms and
GOA annotation evidence. It returns the shared bioinformatics `records[]`
contract so front-end consumers can render GO term cards, relation graphs,
annotation evidence tables, hover cards, and external links without constructing
QuickGO URLs themselves.

## Tools

- `quickgo_term_lookup`: fetch one GO term by ID, for example `GO:0006915`.
- `quickgo_term_search`: search GO terms by text, for example `apoptosis`.
- `quickgo_annotation_search`: search bounded annotation evidence rows by gene
  product, GO ID, taxon, or evidence code.
- `quickgo_term_children`: list child GO terms for a parent GO ID.
- `quickgo_status`: inspect configured capabilities and optional network
  health.

## Sources

- API base: `https://www.ebi.ac.uk/QuickGO/services`
- Browser base: `https://www.ebi.ac.uk/QuickGO`

The server uses only Python standard-library HTTP clients and exposes read-only
MCP tools.

