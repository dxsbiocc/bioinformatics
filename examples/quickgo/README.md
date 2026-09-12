# QuickGO MCP Examples

Lookup a GO term:

```json
{
  "name": "quickgo_term_lookup",
  "arguments": {
    "go_id": "GO:0006915"
  }
}
```

Search GO terms:

```json
{
  "name": "quickgo_term_search",
  "arguments": {
    "query": "apoptosis",
    "max_results": 5
  }
}
```

Search GOA annotation evidence for a protein:

```json
{
  "name": "quickgo_annotation_search",
  "arguments": {
    "gene_product_id": "UniProtKB:P04637",
    "taxon_id": 9606,
    "max_results": 10
  }
}
```

List child terms:

```json
{
  "name": "quickgo_term_children",
  "arguments": {
    "go_id": "GO:0006915",
    "max_children": 10
  }
}
```

