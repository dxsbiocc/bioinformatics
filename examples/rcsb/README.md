# RCSB PDB MCP Examples

Look up a PDB entry:

```json
{
  "pdb_id": "4HHB",
  "include_entities": true,
  "include_ligands": true
}
```

Search RCSB PDB and hydrate top hits:

```json
{
  "query": "hemoglobin",
  "max_results": 5,
  "fetch_records": true
}
```

Fetch entry FASTA:

```json
{
  "pdb_id": "4HHB"
}
```

Front-end consumers should render `structuredContent.records[]`. Structure
records expose `protein_structure` components with `structure_3d`,
`download_manifest`, `table`, and citation previews when available.

