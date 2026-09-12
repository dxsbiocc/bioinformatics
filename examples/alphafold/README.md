# AlphaFold MCP Examples

List available AlphaFold tools:

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
```

Look up predicted structures for a UniProtKB accession:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "alphafold_lookup",
    "arguments": {
      "accession": "P04637",
      "max_models": 10
    }
  }
}
```

Return only the canonical model and include model sequence text:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "alphafold_lookup",
    "arguments": {
      "accession": "P04637",
      "canonical_only": true,
      "include_sequence": true
    }
  }
}
```

Front-end consumers should render returned `records[]` from `display` first.
AlphaFold records expose `display.previews` entries such as:

- `structure_3d`: browser URL, PDB/mmCIF/BinaryCIF URLs, PAE URL, and confidence
  metadata.
- `download_manifest`: reviewable structure-file links.
- `sequence`: model sequence when requested.

