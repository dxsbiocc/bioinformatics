# Human Protein Atlas MCP

The Human Protein Atlas MCP exposes metadata-first retrieval for HPA gene JSON
records and gene search downloads. It is designed for expression and protein
evidence previews, not for HTML scraping or bulk downloads.

## Tools

- `hpa_gene_lookup`: fetch one HPA gene by Ensembl gene ID.
- `hpa_search`: search HPA gene metadata with bounded results.
- `hpa_status`: inspect server capabilities and optional network health.

Returned records follow `schemas/record.schema.json` and use the shared
front-end `gene` component with table and cross-reference previews.

