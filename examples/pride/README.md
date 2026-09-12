# PRIDE MCP Examples

Lookup a PRIDE project:

```json
{
  "name": "pride_project_lookup",
  "arguments": {
    "accession": "PXD001357"
  }
}
```

Lookup a project and include a bounded file preview:

```json
{
  "name": "pride_project_lookup",
  "arguments": {
    "accession": "PXD001357",
    "include_files": true,
    "max_files": 5
  }
}
```

Search PRIDE projects:

```json
{
  "name": "pride_project_search",
  "arguments": {
    "query": "Listeria",
    "max_results": 5
  }
}
```

Build a metadata-only file manifest:

```json
{
  "name": "pride_project_files",
  "arguments": {
    "accession": "PXD001357",
    "max_files": 10
  }
}
```

