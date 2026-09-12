# BioStudies MCP Examples

These examples are metadata-first and front-end compatible. They return
`structuredContent.records[]` records for shared `project` and `download_plan`
renderers.

## Study Lookup

```json
{
  "name": "biostudies_study_lookup",
  "arguments": {
    "accession": "E-MTAB-6701",
    "include_files": true,
    "max_files": 10
  }
}
```

Use this for exact BioStudies or ArrayExpress accessions when project cards,
protocols, publications, repository links, and optional file previews are
needed.

## Search BioStudies

```json
{
  "name": "biostudies_search",
  "arguments": {
    "query": "single cell placenta",
    "max_results": 10
  }
}
```

## Search ArrayExpress

```json
{
  "name": "arrayexpress_search",
  "arguments": {
    "query": "single cell RNA-seq Homo sapiens",
    "max_results": 10
  }
}
```

## File Manifest

```json
{
  "name": "biostudies_file_manifest",
  "arguments": {
    "accession": "E-MTAB-6701",
    "max_files": 25
  }
}
```

The manifest is a planning artifact only. It exposes browser/API links and
safe HTTPS file URLs where BioStudies provides an HTTP download root, but it
does not start a download.
