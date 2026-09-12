# GWAS Catalog Examples

Example MCP tool calls:

```json
{"name":"gwas_variant_lookup","arguments":{"rs_id":"rs699","max_results":5}}
```

```json
{"name":"gwas_gene_lookup","arguments":{"gene":"BRCA1","max_results":5}}
```

```json
{"name":"gwas_trait_search","arguments":{"trait":"asthma","max_results":5}}
```

Use `structuredContent.records[]` for app rendering. Records expose table
previews for associations and studies, citation-list previews for PubMed
evidence, and grouped cross-reference previews for EFO traits, SNPs, genes, and
publications.
