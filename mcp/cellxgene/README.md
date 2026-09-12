# CELLxGENE MCP

The CELLxGENE MCP exposes metadata-first retrieval for public CELLxGENE
Discover collections. It is designed for dataset discovery and UI previews,
not for automatic H5AD transfer.

## Tools

- `cellxgene_collection_lookup`: fetch one public collection by UUID.
- `cellxgene_collections_search`: bounded keyword filtering over public
  collection metadata.
- `cellxgene_collection_assets`: build a metadata-only H5AD asset manifest.
- `cellxgene_status`: inspect server capabilities and optional network health.

Returned records follow `schemas/record.schema.json` and use shared front-end
components: `project` and `download_plan`.

