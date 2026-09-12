# ClinVar MCP Examples

Example MCP tool calls:

```json
{
  "name": "clinvar_lookup",
  "arguments": {
    "identifier": "VCV000037390"
  }
}
```

```json
{
  "name": "clinvar_search",
  "arguments": {
    "terms": "BRCA1 pathogenic",
    "max_results": 5,
    "hydrate": true
  }
}
```

Renderers should consume `structuredContent.records[]` and prefer
`display.primary_url`, `display.actions`, `display.hover`, and
`display.previews` before inspecting tool-specific `data`.

