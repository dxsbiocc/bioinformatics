# BioStudies MCP

The BioStudies MCP exposes metadata-first retrieval for EBI BioStudies and the
ArrayExpress view of BioStudies. It is designed for dataset discovery and UI
previews, not for automatic bulk data transfer.

## Tools

- `biostudies_study_lookup`: fetch one study by accession, for example
  `E-MTAB-6701`, with optional bounded file previews.
- `biostudies_search`: search BioStudies with a keyword.
- `arrayexpress_search`: search the ArrayExpress subset.
- `biostudies_file_manifest`: build a metadata-only file manifest with safe
  HTTPS links when BioStudies exposes an HTTP root.
- `biostudies_status`: inspect server capabilities and optional network health.

Returned records follow `schemas/record.schema.json` and use shared
front-end components: `project` and `download_plan`.

