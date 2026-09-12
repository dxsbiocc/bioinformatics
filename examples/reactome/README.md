# Reactome MCP Examples

Example MCP tool calls:

```json
{
  "name": "reactome_lookup",
  "arguments": {
    "stable_id": "R-HSA-5633007",
    "include_participants": true,
    "max_participants": 40
  }
}
```

```json
{
  "name": "reactome_search",
  "arguments": {
    "query": "TP53",
    "species": "Homo sapiens",
    "types": "Pathway",
    "max_results": 5
  }
}
```

```json
{
  "name": "reactome_pathways_for_identifier",
  "arguments": {
    "resource": "UniProt",
    "identifier": "P04637",
    "species": "9606",
    "max_results": 10
  }
}
```

The returned `structuredContent.records[]` values are front-end-ready pathway
records. Renderers should use `display.primary_url`, `display.actions`,
`display.hover`, and `display.previews` before inspecting tool-specific `data`.

