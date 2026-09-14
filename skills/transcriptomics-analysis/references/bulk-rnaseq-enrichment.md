# Bulk RNA-seq Enrichment

Use this reference after differential expression or ranked gene statistics are
available. Enrichment is downstream interpretation, not a substitute for a valid
differential-expression model.

## Inputs

- Differential expression table with gene identifiers, adjusted p-values, and
  preferably signed statistics or log fold changes.
- Gene set collection such as GO, KEGG, Reactome, Hallmark, custom signatures, or
  pathway GMT files.
- Explicit identifier namespace for both DE results and gene sets. Do not mix
  symbols, Ensembl IDs, Entrez IDs, and aliases without a mapping step.
- Background universe, ideally all genes tested in the differential-expression
  model after filtering.

## Method Choice

- Use over-representation analysis when the question starts from a thresholded
  gene list. Report threshold, direction, universe, and gene-set size filters.
- Use preranked GSEA when the question uses all genes and a signed ranking
  statistic. Prefer signed test statistics over adjusted p-values alone.
- Use GSVA or ssGSEA-like sample-level scores when comparing pathway activity
  across samples, but treat those as a new sample-level matrix that still needs
  design-aware modeling.

## Script Support

- `scripts/bulk-rnaseq/enrichment/ora_from_de.R` runs a lightweight
  hypergeometric ORA from a DE table and GMT file.
- `scripts/bulk-rnaseq/enrichment/preranked_gsea.R` runs a lightweight
  preranked GSEA from signed ranks and GMT gene sets.

These scripts use local files and base R only. For publication-critical pathway
analyses, prefer maintained packages such as `fgsea`, `clusterProfiler`, or
`limma` gene-set tests when they are already available in the project.

## Guardrails

- Do not use significant genes as both foreground and universe.
- Do not run enrichment before checking ID mapping loss.
- Do not compare enrichment across contrasts when different filtering or
  background universes were used unless that difference is explicit.
- Do not over-interpret broad redundant gene sets without checking leading-edge
  or overlap genes.

## Deliverables

Return enrichment tables, selected gene lists or ranked input provenance,
background universe, gene-set version/source, identifier mapping summary, and
limitations.
