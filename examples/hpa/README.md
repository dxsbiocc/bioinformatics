# Human Protein Atlas MCP Examples

The `hpa` MCP server exposes metadata-first Human Protein Atlas retrieval. It
returns shared `gene` records with HPA browser links, HPA JSON links,
expression-summary tables, cancer-prognostic tables when present, and grouped
Ensembl/UniProt cross-reference previews.

## Exact Gene Lookup

```json
{
  "name": "hpa_gene_lookup",
  "arguments": {
    "ensembl_id": "ENSG00000141510"
  }
}
```

Use this when an Ensembl gene ID is already known. The returned
`structuredContent.records[0].display.primary_url` opens the HPA gene page, and
`display.actions` includes the HPA JSON endpoint plus Ensembl/UniProt links
when available.

## Gene Search

```json
{
  "name": "hpa_search",
  "arguments": {
    "query": "TP53",
    "max_results": 5
  }
}
```

Use this for symbol, synonym, Ensembl ID, or free-text discovery. Search results
are bounded and normalized to the same front-end contract as exact lookups.
