# ClinVar MCP Server

The ClinVar MCP server wraps NLM Clinical Tables search and NCBI E-utilities
ClinVar summaries with front-end-compatible `variant` records.

## Tools

- `clinvar_search`: search Clinical Tables variants and hydrate top hits
  through ClinVar ESummary.
- `clinvar_lookup`: fetch a ClinVar variation by numeric UID or VCV accession.
- `clinvar_status`: inspect local configuration and optional network health.

## Front-end Contract

Records use `display.component: "variant"` and include ClinVar browser links,
E-utilities links, gene/dbSNP actions, hover metadata, and previews:

- `table` for genomic locations.
- `table` for supporting RCV/SCV submissions.
- `xref_groups` for ClinVar, NCBI Gene, dbSNP, and other xrefs.

The implementation intentionally avoids relying on the currently unstable NCBI
Variation beta ClinVar endpoints for core behavior.

