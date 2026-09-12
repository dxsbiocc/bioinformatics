# RNAcentral MCP Server

This MCP server wraps the public RNAcentral REST API for metadata-first RNA
entry lookup, bounded search, and cross-reference retrieval.

## Tools

- `rnacentral_entry_lookup`: fetch one RNAcentral URS entry, optionally scoped
  to an NCBI TaxID.
- `rnacentral_search`: run a bounded text search over RNAcentral RNA entries.
- `rnacentral_xrefs`: fetch bounded external database cross-references for one
  URS identifier.
- `rnacentral_status`: inspect local configuration and optional network health.

The implementation uses documented RNAcentral API patterns:

- `rna/<URS>/`
- `rna/<URS>/<taxid>/`
- `rna/<URS>/xrefs/`
- `rna/?q=<query>&page_size=<n>`

The server returns metadata and links only; it does not download files or open
external pages. Sequence data returned by RNAcentral is exposed through the
shared `sequence` preview contract for front-end rendering.

