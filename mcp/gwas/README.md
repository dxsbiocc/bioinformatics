# GWAS Catalog MCP Server

This server exposes metadata-first GWAS Catalog REST API v2 retrieval tools for
variant, mapped-gene, and trait association evidence.

## Tools

- `gwas_variant_lookup`: fetch a SNP record and association evidence by rsID,
  for example `rs699`.
- `gwas_gene_lookup`: fetch association evidence filtered by `mapped_gene`, for
  example `BRCA1`.
- `gwas_trait_search`: fetch association and study evidence by trait query, for
  example `asthma`.
- `gwas_status`: inspect server configuration and optionally run a small
  metadata network check.

Results return shared `records[]` envelopes with clickable GWAS Catalog,
PubMed, SNP, and API links. Association rows are bounded by `max_results`; this
server does not download summary statistics.

