# RCSB PDB MCP Server

This server wraps the RCSB PDB Data API and Search API for structure lookup,
discovery, and FASTA retrieval. It follows the public RCSB endpoints:

- `https://data.rcsb.org/rest/v1/core/...`
- `https://search.rcsb.org/rcsbsearch/v2/query`
- `https://www.rcsb.org/fasta/entry/{PDB_ID}/download`

## Tools

- `rcsb_lookup`: fetches a PDB entry and optional polymer/ligand summaries.
- `rcsb_search`: performs full-text Search API discovery and can hydrate top
  hits into structure records.
- `rcsb_fasta`: fetches entry FASTA.
- `rcsb_status`: reports configured capabilities and optional network health.

## Front-end Contract

`rcsb_lookup` and hydrated `rcsb_search` results return `protein_structure`
records with:

- `structure_3d` previews for structure viewers.
- `download_manifest` previews for PDB, mmCIF, and FASTA links.
- `table` previews for polymer entities when available.
- `citation_list` previews when RCSB returns citations.

The MCP returns URLs and metadata only. It does not download structure files or
render 3D views itself.

