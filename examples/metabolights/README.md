# MetaboLights MCP Examples

The `metabolights` MCP server exposes metadata-first metabolomics study
retrieval. It returns shared `project` and `download_plan` records with
MetaboLights browser/API links, assay and protocol tables, publication previews,
and bounded file manifests.

## Exact Study Lookup

```json
{
  "name": "metabolights_study_lookup",
  "arguments": {
    "accession": "MTBLS1",
    "include_files": true,
    "max_files": 25
  }
}
```

Use this when the `MTBLS` accession is known. The returned
`structuredContent.records[0].display.primary_url` opens the MetaboLights study
page, and `display.previews` can include study summary, assays, publications,
cross-references, and a metadata-only file manifest.

## Study Discovery

```json
{
  "name": "metabolights_search",
  "arguments": {
    "query": "diabetes",
    "max_results": 5
  }
}
```

Use this for metabolomics study discovery through EBI Search.

## File Manifest

```json
{
  "name": "metabolights_file_manifest",
  "arguments": {
    "accession": "MTBLS1",
    "max_files": 25
  }
}
```

The manifest is metadata-only. It exposes safe links for review, but does not
download data.
