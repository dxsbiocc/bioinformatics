---
name: transcriptomics-analysis
description: >-
  Analyze prepared transcriptomics matrices and sample metadata for bulk RNA-seq,
  single-cell or single-nucleus RNA-seq, and spatial transcriptomics. Use for
  transcriptome-specific QC, normalization, dimensionality reduction, clustering,
  differential expression, annotation, spatial domains, and interpretation. Do
  not use for raw FASTQ/BAM processing, public dataset retrieval, literature
  review, general statistics without transcriptomics context, or figure-only
  rendering from existing results.
---

# Transcriptomics Analysis

Turn prepared transcriptomics measurements into reproducible, biologically
interpretable results while preserving the observation unit, replicate structure,
and assay-specific assumptions.

## Routing

Read only the reference that matches the data and question:

- For bulk RNA-seq count matrices, read
  [references/bulk-rnaseq.md](references/bulk-rnaseq.md).
- For bulk RNA-seq pathway or gene-set interpretation after differential
  expression, read
  [references/bulk-rnaseq-enrichment.md](references/bulk-rnaseq-enrichment.md).
- For bulk RNA-seq coexpression, module, hub-gene, or module-trait questions,
  read
  [references/bulk-rnaseq-coexpression.md](references/bulk-rnaseq-coexpression.md).
- For transcript usage, isoform switching, exon usage, alternative splicing, or
  polyadenylation, read
  [references/transcript-isoform-splicing.md](references/transcript-isoform-splicing.md).
- For fusion genes, RNA editing, circular RNA, allele-specific expression, or
  aberrant RNA events, read
  [references/fusion-rna-events.md](references/fusion-rna-events.md).
- For eQTL, sQTL, TWAS, transcriptome-genetics, or colocalization questions, read
  [references/expression-qtl.md](references/expression-qtl.md).
- For single-cell or single-nucleus RNA-seq matrices, read
  [references/single-cell-rnaseq.md](references/single-cell-rnaseq.md).
- For spatial transcriptomics with coordinates, spots, cells, images, or tissue
  annotations, read
  [references/spatial-transcriptomics.md](references/spatial-transcriptomics.md).

If the task is only a generic statistical operation such as PCA, correlation,
clustering, or multiple-testing explanation without transcriptomics-specific
decisions, use `omics-analysis` instead.

## Shared Workflow

1. Identify organism, gene annotation, feature identifiers, matrix scale, sample
   or cell metadata, biological replicates, batch variables, and intended
   contrasts or biological questions.
2. Confirm whether the matrix contains raw counts, normalized values, transformed
   values, TPM/FPKM, or model residuals before choosing methods.
3. Inspect sample or cell quality, library depth, feature detection, missingness,
   duplicated identifiers, outliers, batch structure, and design confounding.
4. Choose normalization, filtering, dimensionality reduction, clustering,
   differential testing, and annotation methods that match the assay class.
5. Preserve source inputs and write derived artifacts, code, parameters, QC
   summaries, and result tables to separate project-local outputs.
6. Verify row and column identities, contrast direction, replicate handling,
   adjusted p-values, and agreement between reported summaries and result files.

## Reusable Code

Use scripts only when they match the requested assay and design. For bulk
RNA-seq, the reusable code is grouped under `scripts/bulk-rnaseq/`:

- `lib/` contains shared input parsing, count-matrix validation, metadata
  alignment, and table-writing utilities.
- `diagnostics/` contains matrix-scale, distribution, log-transform, and method
  selection checks. Run this before differential expression when matrix scale is
  uncertain or multiple expression matrices are available.
- `qc/` contains sample-level and feature-level QC summaries, including a
  pre-differential-expression gate for sample uniformity, PCA structure, group
  sample counts, and sample correlations.
- `normalization/` contains count-derived CPM, log-CPM, TPM, and FPKM table
  generation. It must not be used to infer raw counts from normalized values.
- `exploratory/` contains PCA, variable-feature selection, and sample
  correlation tables.
- `differential-expression/` contains count-model differential expression
  scripts plus a limited normalized-expression fallback when raw counts are not
  available. These scripts require `--qc-reviewed` after the relevant QC and PCA
  outputs have been inspected.
- `enrichment/` contains local ORA and lightweight preranked GSEA from
  differential-expression tables and GMT gene sets.
- `coexpression/` contains exploratory correlation-module analysis from
  transformed sample-level expression matrices.

## Integrity

- Do not invent replicates, covariates, contrasts, cell labels, tissue labels, or
  significance thresholds.
- Do not treat cells, nuclei, spots, or technical replicates as independent
  biological replicates for sample-level claims.
- Do not silently remove samples, cells, spots, or genes; report filtering rules
  and before/after counts.
- Do not run differential expression on a matrix scale that is unsuitable for
  the chosen model.
- If the design cannot identify the requested effect, state that limitation
  rather than forcing an analysis.

## Scope

This skill begins with prepared expression matrices, count tables, AnnData,
Seurat objects, SummarizedExperiment objects, or equivalent metadata-rich
analysis inputs. Raw read processing and quantification belong to
`omics-pipeline`; public dataset discovery belongs to `omics-database`; paper
search belongs to `omics-literature`; final figure rendering belongs to
`omics-visualization`.
