# Ensembl MCP Server

The Ensembl MCP server wraps high-frequency Ensembl REST endpoints with
front-end-compatible bioinformatics records. It is metadata-first and read-only:
tools return stable URLs, hover payloads, and preview hints, but do not run
local analysis.

## Tools

- `ensembl_lookup`: fetch a stable ID such as `ENSG00000141510`.
- `ensembl_xrefs`: fetch bounded external cross-references for a stable ID.
- `ensembl_overlap_region`: fetch genes, transcripts, variants, or regulatory
  features overlapping a region such as `17:7661779-7687546`.
- `ensembl_variation`: fetch variation metadata for IDs such as `rs699`.
- `ensembl_status`: inspect local configuration and optional network health.

## Front-end Contract

The server emits shared record envelopes:

- `gene` for Ensembl genes.
- `genomic_feature` for non-gene stable IDs and region features.
- `variant` for Ensembl variation records.
- `identifier_conversion` for xref result sets.

Records include browser/API actions, hover metadata, and `table` or
`xref_groups` previews for transcripts, mappings, and external references.

