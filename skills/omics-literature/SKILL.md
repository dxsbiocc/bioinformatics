---
name: omics-literature
description: >-
  Find, screen, compare, and synthesize scholarly literature for genomics,
  transcriptomics, proteomics, metabolomics, and related bioinformatics
  questions. Use for evidence reviews, method comparisons, citation verification,
  and research-background summaries. Do not use for database-record retrieval,
  local data analysis, pipeline execution, or unsupported citation generation.
---

# Omics Literature

Build traceable evidence summaries from relevant scholarly sources while keeping
search, screening, and interpretation distinct.

## Workflow

1. Define the biological question, population or system, assay, method,
   comparison, date range, and desired evidence depth.
2. Construct focused search concepts and search appropriate scholarly sources.
   Prefer primary research and authoritative methods or reporting guidance.
   Use the `ncbi` MCP server's PubMed tools when available:
   `pubmed_search` for discovery, `pubmed_summaries` for citation metadata, and
   `pubmed_articles` or `pubmed_fetch` for abstracts and record details. Use
   `pmc_id_convert` when PMID, PMCID, DOI, or manuscript IDs need to be mapped
   for front-end citations or full-text availability checks.
3. Deduplicate results and screen titles, abstracts, and available full text
   against explicit inclusion and exclusion criteria.
4. Verify citation metadata and distinguish published articles, preprints,
   reviews, protocols, and retracted or corrected work.
5. Extract comparable evidence, including study design, sample size, assay,
   computational method, result, limitation, and relevance to the question.
6. Synthesize agreements, conflicts, evidence gaps, and practical implications
   with citations attached to the claims they support.

## Front-end Contract

For MCP literature records, prefer `structuredContent.records[]` and
`structuredContent.citations[]`. Citation chips should show `stable_id` such as
`PMID:36973787`, use `display.hover` for title, journal, authors, DOI, PMCID,
and URL details, and open `display.primary_url` or `url` only after a user
action. The shared schema is `schemas/record.schema.json`; TypeScript consumers
can use `types/record.ts`.

## Integrity

- Never fabricate citations, DOIs, quotations, methods, or study results.
- Separate source-reported findings from inference and recommendation.
- Do not treat citation count or journal prestige as evidence quality.
- Report inaccessible full text and uncertain metadata rather than filling gaps.

## Delivery

Return the search scope, screened evidence set, concise synthesis, key
limitations, and verified citation details in the format requested by the user.
