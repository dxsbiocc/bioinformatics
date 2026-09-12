# RNAcentral MCP Examples

Look up a species-specific RNA entry:

```json
{
  "rnacentral_id": "URS000075C808",
  "taxid": 9606
}
```

Search RNAcentral:

```json
{
  "query": "HOTAIR",
  "max_results": 5
}
```

Fetch cross-references:

```json
{
  "rnacentral_id": "URS000075C808",
  "max_results": 10
}
```

The returned records include front-end-compatible links, hover metadata,
sequence previews, grouped cross-references, and table previews.

