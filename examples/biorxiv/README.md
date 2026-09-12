# bioRxiv/medRxiv MCP Examples

Use `biorxiv_preprint_lookup` when you know a DOI:

```json
{
  "server": "biorxiv",
  "doi": "10.1101/2020.09.09.20191205"
}
```

Use `biorxiv_preprint_interval` for bounded recent preprints:

```json
{
  "server": "medrxiv",
  "start_date": "2026-09-01",
  "end_date": "2026-09-07",
  "max_results": 10
}
```

Use `biorxiv_publication_lookup` to find formal-publication linkage:

```json
{
  "server": "biorxiv",
  "doi": "10.1101/2020.09.09.20191205"
}
```

Returned records follow the shared front-end contract. Renderers should consume
`records[].display.hover`, `records[].display.actions`, and
`records[].display.previews` before inspecting database-specific `data`.

