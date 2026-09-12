# CELLxGENE MCP Examples

These examples are metadata-first and front-end compatible. They return
`structuredContent.records[]` records for shared `project` and `download_plan`
renderers.

## Collection Lookup

```json
{
  "name": "cellxgene_collection_lookup",
  "arguments": {
    "collection_id": "db468083-041c-41ca-8f6f-bf991a070adf",
    "max_datasets": 20
  }
}
```

Use this for exact CELLxGENE Discover collection UUIDs when collection cards,
dataset tables, ontology labels, publication metadata, explorer links, and H5AD
asset previews are needed.

## Search Collections

```json
{
  "name": "cellxgene_collections_search",
  "arguments": {
    "query": "human retina",
    "max_results": 10,
    "max_datasets": 10
  }
}
```

The search is bounded metadata filtering over the public collections list.
Prefer exact collection lookup when a collection UUID is already known.

## Asset Manifest

```json
{
  "name": "cellxgene_collection_assets",
  "arguments": {
    "collection_id": "db468083-041c-41ca-8f6f-bf991a070adf",
    "max_datasets": 20
  }
}
```

The manifest is a planning artifact only. It exposes CELLxGENE collection,
dataset explorer, and H5AD asset links, but it does not start a download.
