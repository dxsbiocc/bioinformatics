# MetaboLights MCP

The MetaboLights MCP exposes metadata-first retrieval for public
metabolomics studies. It uses MetaboLights WS for exact study/file lookups and
EBI Search for text discovery.

## Tools

- `metabolights_study_lookup`: fetch one `MTBLS` study with optional bounded
  file preview.
- `metabolights_search`: search MetaboLights studies through EBI Search.
- `metabolights_file_manifest`: fetch a metadata-only file manifest.
- `metabolights_status`: inspect server capabilities and optional network
  health.

Returned records follow `schemas/record.schema.json` and use the shared
front-end `project` and `download_plan` components with table, citation-list,
download-manifest, and cross-reference previews.
