# Ensembl MCP Examples

Example MCP tool calls:

```json
{
  "name": "ensembl_lookup",
  "arguments": {
    "ensembl_id": "ENSG00000141510",
    "expand": true,
    "include_xrefs": true,
    "max_xrefs": 20
  }
}
```

```json
{
  "name": "ensembl_overlap_region",
  "arguments": {
    "species": "homo_sapiens",
    "region": "17:7661779-7687546",
    "features": ["gene", "variation"],
    "max_results": 10
  }
}
```

```json
{
  "name": "ensembl_variation",
  "arguments": {
    "species": "homo_sapiens",
    "variant_id": "rs699"
  }
}
```

Renderers should consume `structuredContent.records[]` and prefer
`display.primary_url`, `display.actions`, `display.hover`, and
`display.previews` before inspecting tool-specific `data`.

