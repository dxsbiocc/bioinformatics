# EFO MCP Examples

Look up a term:

```json
{
  "term_id": "EFO:0000270"
}
```

Search EFO:

```json
{
  "query": "asthma",
  "max_results": 5
}
```

Fetch descendants:

```json
{
  "term_id": "MONDO:0004979",
  "max_results": 10
}
```

Returned records include EFO/OLS4 browser links, API provenance, synonyms,
definitions, cross-references, and ontology relation previews.

