# UniProt MCP

Local MCP server for UniProt access in the Bioinformatics plugin.

Implemented surfaces through the UniProt REST API:

- `uniprot_search`
- `uniprot_lookup`
- `uniprot_fasta`
- `uniprot_status`

The server is written with Python's standard library only. Optional environment
variables:

- `UNIPROT_BASE_URL`
- `UNIPROT_CONTACT`
- `UNIPROT_TOOL`

The plugin loads this server through `../../.mcp.json`.

## Implementation layout

- `server.py`: stdio JSON-RPC/MCP entrypoint.
- `client.py`: UniProt REST HTTP client and request pacing.
- `tools.py`: MCP tool schemas and handler registry.
- `records.py`: front-end-compatible UniProtKB record envelopes.
- `previews.py`: shared preview hints for sequence, feature, structure,
  interaction, citation, and cross-reference widgets.
- `urls.py`: UniProt-adjacent URL builders for UniProtKB, AlphaFold, STRING,
  RCSB PDB, Reactome, PubMed, GO, and NCBI Gene links.
- `utils.py`: validation, provenance, and normalization helpers.

## Record contract

UniProt tools return `structuredContent.records[]` records using the shared
`../../schemas/record.schema.json` envelope and `protein` display component.
Search results include `pagination.total`, `pagination.next_url`, and
`pagination.next_cursor` when UniProt returns those headers.

Protein records expose stable identifiers and browser URLs:

```json
{
  "schema_version": "bioinformatics.record.v1",
  "type": "protein",
  "record_type": "uniprotkb_entry",
  "database": "uniprotkb",
  "id": "P04637",
  "stable_id": "UniProtKB:P04637",
  "label": "P04637",
  "url": "https://www.uniprot.org/uniprotkb/P04637/entry",
  "icon": "uniprot",
  "display": {
    "component": "protein",
    "chip_label": "P04637",
    "primary_url": "https://www.uniprot.org/uniprotkb/P04637/entry"
  }
}
```

The MCP returns URLs only. The app decides whether to open a browser, preview a
sequence, or offer a download action.

For richer detail panes, protein records may include `display.sections` entries
for overview, function, features, keywords, comments, cross references, and
literature. Large upstream arrays are bounded by `max_features`, `max_comments`,
and cross-reference ID limits; `include_raw: true` preserves raw upstream JSON
when needed for inspection.

Protein and FASTA records may also include `display.previews` entries. These are
database-backed front-end hints, not UI code. Current preview kinds include:

- `sequence`: UniProtKB FASTA URL and sequence metadata.
- `feature_track`: bounded UniProt sequence feature rows and tracks.
- `structure_3d`: AlphaFold DB or RCSB PDB links when the UniProt entry has
  those cross-references.
- `network`: STRING interaction-network seed when the UniProt entry has a
  STRING cross-reference.
- `citation_list`: PubMed IDs and UniProt literature references.
- `xref_groups`: grouped cross-reference summary.
