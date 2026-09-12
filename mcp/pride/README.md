# PRIDE Archive MCP

PRIDE Archive MCP wraps the official EBI PRIDE Archive REST API for
proteomics project discovery, project metadata, and metadata-only project file
manifests. It returns the shared bioinformatics `records[]` contract so
front-end consumers can render project cards, citation/reference previews,
instrument and organism tables, download manifest previews, hover cards, and
external links.

## Tools

- `pride_project_lookup`: fetch one PRIDE/ProteomeXchange project by PXD
  accession.
- `pride_project_search`: search PRIDE projects by keyword with bounded result
  counts.
- `pride_project_files`: return a bounded metadata-only file manifest for one
  project. No file transfer is started.
- `pride_status`: inspect configured capabilities and optional network health.

## Sources

- API base: `https://www.ebi.ac.uk/pride/ws/archive/v2`
- Browser base: `https://www.ebi.ac.uk/pride/archive`

FTP file locations are preserved in `data.files[].locations[].raw_url`. When a
PRIDE FTP URL can be mirrored safely for user clicking, the MCP exposes an
HTTPS URL under `download_url`.

