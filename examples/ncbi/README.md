# NCBI MCP Examples

These examples show the intended metadata-first calls. They can be used by
agents, tests, and front-end developers without inventing database-specific URL
rules.

## PubMed Search

```json
{
  "tool": "pubmed_search",
  "arguments": {
    "query": "single-cell RNA-seq tumor microenvironment",
    "max_results": 5,
    "sort": "pub_date",
    "include_summaries": true
  },
  "read": ["structuredContent.records", "structuredContent.citations"]
}
```

Render citations from `records[].display` and inline reference chips from
`citations[]`. Use `stable_id` values such as `PMID:36973787` as visible labels.
Use `records[].display.previews` for citation-list widgets when present.

## GEO Download Plan

```json
{
  "tool": "geo_download_plan",
  "arguments": {
    "accession": "GSE100",
    "include_samples": true
  },
  "read": ["structuredContent.manifest", "structuredContent.records"]
}
```

The manifest contains the GEO browser URL, family SOFT link, series matrix link,
supplementary-file directory, sample accessions, platform, BioProject, and
PubMed IDs. `records[].display.previews` includes a `download_manifest` hint.
It does not download files.

## SRA Download Plan

```json
{
  "tool": "sra_download_plan",
  "arguments": {
    "query": "SRR7039034",
    "threads": 8,
    "prefetch_outdir": "data/sra",
    "fastq_outdir": "data/fastq"
  },
  "read": ["structuredContent.manifest.items", "structuredContent.records"]
}
```

Each run item keeps SRA, Run Browser, Run Selector, BioProject, and BioSample
links. Suggested `prefetch`, `fasterq-dump`, and `vdb-validate` commands are
stored as strings under `runs[].commands`; the matching record preview is a
review-only `download_manifest`.

## Omics Sample Sheet

```json
{
  "tool": "omics_sample_sheet",
  "arguments": {
    "source": "auto",
    "query": "GSE100"
  },
  "read": ["structuredContent.columns", "structuredContent.rows", "structuredContent.records"]
}
```

Use this before pipeline work to get a compact GEO sample table or SRA run table
with stable column keys and row-level links. The returned record exposes a
`table` preview using the same columns and bounded rows.

## Runtime Status

```json
{
  "tool": "tool_runtime_status",
  "arguments": {
    "tools": ["prefetch", "fasterq-dump", "fastqc", "multiqc", "salmon"],
    "check_versions": false
  },
  "read": ["structuredContent.tools", "structuredContent.records"]
}
```

The result tells whether tools are discoverable on `PATH`. Version checks are
optional and only run known safe version flags.
