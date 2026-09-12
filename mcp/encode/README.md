# ENCODE MCP

Metadata-only MCP tools for ENCODE Portal functional genomics records.

## Tools

- `encode_experiment_lookup`: fetch one experiment by ENCSR accession.
- `encode_experiment_search`: search experiments with text and optional filters.
- `encode_biosample_lookup`: fetch one biosample by ENCBS accession.
- `encode_biosample_search`: search biosamples with text and optional filters.
- `encode_file_lookup`: fetch one file by ENCFF accession.
- `encode_file_manifest`: return a bounded metadata-only file manifest for an experiment.
- `encode_status`: inspect server configuration and optional network health.

All record responses preserve ENCODE portal/API links and use the shared
`bioinformatics.record.v1` display envelope for project cards, sample cards,
and download manifest previews.
