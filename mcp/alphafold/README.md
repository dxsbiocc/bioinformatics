# AlphaFold MCP

Local MCP server for AlphaFold DB access in the Bioinformatics plugin.

Implemented surfaces through the AlphaFold DB API:

- `alphafold_lookup`
- `alphafold_status`

The server is written with Python's standard library only. Optional environment
variables:

- `ALPHAFOLD_BASE_URL`
- `ALPHAFOLD_CONTACT`
- `ALPHAFOLD_TOOL`

The plugin loads this server through `../../.mcp.json`.

## Implementation layout

- `server.py`: stdio JSON-RPC/MCP entrypoint.
- `client.py`: AlphaFold API HTTP client and request pacing.
- `tools.py`: MCP tool schemas and handler registry.
- `records.py`: front-end-compatible protein structure record envelopes.
- `utils.py`: validation, provenance, and normalization helpers.

## Record contract

AlphaFold tools return `structuredContent.records[]` records using the shared
`../../schemas/record.schema.json` envelope and `protein_structure` display
component.

Structure records expose stable identifiers, browser URLs, and file links:

```json
{
  "schema_version": "bioinformatics.record.v1",
  "type": "protein.structure",
  "record_type": "alphafold_prediction",
  "database": "alphafold",
  "id": "AF-P04637-F1",
  "stable_id": "AlphaFold:AF-P04637-F1",
  "label": "AF-P04637-F1",
  "url": "https://alphafold.ebi.ac.uk/entry/P04637",
  "icon": "alphafold",
  "display": {
    "component": "protein_structure",
    "chip_label": "AF-P04637-F1",
    "primary_url": "https://alphafold.ebi.ac.uk/entry/P04637"
  }
}
```

Records include `display.previews` hints:

- `structure_3d`: AlphaFold browser URL plus PDB, mmCIF, BinaryCIF, PAE, and
  confidence metadata for a 3D viewer.
- `download_manifest`: reviewable structure-file download links. The MCP does
  not download files automatically.
- `sequence`: optional model sequence when `include_sequence` is true.

`alphafold_lookup` can return multiple records for one accession because
AlphaFold DB may return canonical and isoform models. Use `canonical_only: true`
to keep only the exact accession.

