# UniProt MCP Examples

List available UniProt tools:

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
```

Search reviewed human TP53 records:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "uniprot_search",
    "arguments": {
      "query": "gene:TP53",
      "organism": "9606",
      "reviewed": true,
      "max_results": 5
    }
  }
}
```

Continue a paginated search with the returned `pagination.next_cursor`:

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "tools/call",
  "params": {
    "name": "uniprot_search",
    "arguments": {
      "query": "gene:TP53",
      "organism": "9606",
      "cursor": "NEXT_CURSOR_FROM_PREVIOUS_RESPONSE",
      "max_results": 5
    }
  }
}
```

Look up a UniProtKB accession:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "uniprot_lookup",
    "arguments": {
      "accession": "P04637",
      "include_features": true,
      "feature_types": ["Domain", "Region", "Modified residue"],
      "max_features": 50
    }
  }
}
```

Front-end consumers should render the returned `records[]` from `display` first.
UniProt protein records can include `display.previews` entries such as:

- `sequence`: FASTA URL and sequence metadata.
- `feature_track`: bounded sequence feature tracks and rows.
- `structure_3d`: AlphaFold DB or RCSB PDB links when cross-references exist.
- `network`: STRING interaction-network seed when a STRING cross-reference
  exists.
- `citation_list`: PubMed IDs and UniProt literature references.
- `xref_groups`: grouped external database references.

Fetch FASTA for a UniProtKB accession:

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "uniprot_fasta",
    "arguments": {
      "accession": "P04637"
    }
  }
}
```
