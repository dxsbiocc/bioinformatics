# HMDB MCP

This MCP wraps the HMDB `unearth/q` search endpoint for compact, app-renderable
metabolite, protein, disease, and pathway retrieval.

Tools:

- `hmdb_search`: search any supported HMDB category.
- `hmdb_metabolite_search`: search HMDB metabolites and return `compound` records.
- `hmdb_protein_search`: search HMDB proteins and return `protein` records.
- `hmdb_disease_search`: search HMDB diseases and return `dataset` records.
- `hmdb_pathway_search`: search HMDB pathways and return `pathway` records.
- `hmdb_status`: inspect server configuration and optional network health.

HMDB may return a Cloudflare browser challenge to non-browser runtimes. The MCP
detects that condition and returns an explicit error instead of pretending that
no records were found.

