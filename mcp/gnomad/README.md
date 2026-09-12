# gnomAD MCP Server

This server exposes compact gnomAD GraphQL retrieval tools for variant
frequencies and gene constraint summaries. Results are metadata-first and return
shared `records[]` envelopes for app-side cards, hover previews, links, tables,
and cross-reference groups.

## Tools

- `gnomad_variant_lookup`: fetch one variant such as `1-230710048-A-G` from a
  gnomAD dataset such as `gnomad_r4`.
- `gnomad_gene_lookup`: fetch one Ensembl gene ID such as `ENSG00000141510`
  using a reference genome such as `GRCh38`.
- `gnomad_status`: inspect server configuration and optionally run a small
  metadata network check.

The MCP returns gnomAD browser URLs and GraphQL API URLs as click targets. It
does not download bulk data.

