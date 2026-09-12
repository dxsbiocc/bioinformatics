---
name: omics-search
description: >-
  Route omics-related public knowledge searches across literature and database
  retrieval surfaces. Use when the user asks broadly to search NCBI, PubMed,
  public bioinformatics records, accessions, datasets, or identifiers and the
  target is not yet clear. Do not use for local data analysis, pipeline
  execution, or figure generation.
---

# Omics Search

Resolve broad public-search requests into the narrower retrieval skill and MCP
tool surface that matches the user's intent.

## Routing

1. If the request is about papers, abstracts, evidence, citation metadata,
   method comparison, or PubMed results, route to `omics-literature` and use the
   `ncbi` MCP server's PubMed tools when available.
2. If the request is about biological records, accessions, identifier mapping,
   sequence or protein records, datasets, samples, runs, or repository metadata,
   route to `omics-database`. Use non-literature NCBI MCP tools when those
   database surfaces are added. For sequencing repositories, prefer
   `bioproject_lookup`, `biosample_lookup`, `sra_lookup`, or `sra_search` before
   broader web search.
3. If the user needs both papers and database records, keep the result sets
   separate and preserve the source database, query, retrieval date, and stable
   identifiers for each item.

## Front-end Contract

When returning MCP search results, prefer the shared `records[]` envelope and
preserve `display`, `links`, `identifiers`, `citation`, and `related` fields.
The renderer contract lives in `docs/frontend-record-rendering.md`, the JSON
Schema in `schemas/record.schema.json`, and TypeScript types in
`types/record.ts`.

## Boundaries

- This is a routing skill, not an analysis workflow.
- Do not synthesize literature claims without `omics-literature`.
- Do not treat PubMed records as database annotations for genes, proteins, or
  pathways without explicit evidence and source separation.
- Do not bulk-download records without estimating scope and confirming the
  requested data boundary.
