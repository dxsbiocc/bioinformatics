# STRING MCP Examples

Map identifiers to STRING IDs:

```json
{
  "identifiers": ["TP53", "MDM2"],
  "species": 9606
}
```

Fetch a small protein interaction network:

```json
{
  "identifiers": "TP53",
  "species": 9606,
  "limit": 10
}
```

Front-end consumers should render `structuredContent.records[]`. Interaction
results expose a `protein_network` record plus a `network` preview whose
`data.nodes` and `data.edges` arrays are ready for graph widgets.

