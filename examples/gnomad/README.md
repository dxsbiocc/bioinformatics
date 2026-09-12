# gnomAD Examples

Example MCP tool calls:

```json
{"name":"gnomad_variant_lookup","arguments":{"variant_id":"1-230710048-A-G","dataset":"gnomad_r4","max_populations":12}}
```

```json
{"name":"gnomad_gene_lookup","arguments":{"gene_id":"ENSG00000141510","reference_genome":"GRCh38"}}
```

Use the returned `structuredContent.records[]` for app rendering. Variant
records expose allele-frequency, population-frequency, transcript-consequence,
and cross-reference previews. Gene records expose constraint metrics,
transcripts, and cross-reference previews.
