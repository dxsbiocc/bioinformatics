---
name: omics-analysis
description: >-
  Analyze prepared omics count matrices, abundance tables, assay measurements,
  and sample metadata. Use for cross-omics or general statistical analysis such
  as quality assessment, normalization decisions, dimensionality reduction,
  clustering, differential testing, enrichment-ready result generation, and
  statistical interpretation. Do not use for transcriptomics-specific bulk
  RNA-seq, single-cell RNA-seq, or spatial transcriptomics analysis, raw-read
  processing, public-database retrieval, literature review, or visualization-only
  requests when analysis results already exist.
---

# Omics Analysis

Turn prepared omics measurements and experimental metadata into reproducible,
statistically defensible results. Keep analysis decisions explicit and preserve
the original inputs.

## Workflow

1. Identify the assay, observation unit, feature identifiers, measurement scale,
   sample metadata, biological replicates, experimental design, and intended
   contrast. Do not proceed with inferential analysis while these are ambiguous.
2. Inspect missingness, library or sample depth, distributions, duplicated
   identifiers, batch structure, outliers, and design confounding.
3. Choose transformations, normalization, filtering, statistical models, and
   multiple-testing correction that match the assay and design. Explain choices
   that materially affect interpretation.
4. Write project-local, editable analysis code and retain intermediate tables
   needed to reproduce the final result.
5. Verify model assumptions, contrast direction, row counts, identifier mapping,
   adjusted p-values, and agreement between reported summaries and result files.
6. Deliver result tables, executable source, QC findings, analysis parameters,
   and limitations. Route figure-only follow-up work to a visualization skill.

## Integrity

- Never invent replicates, covariates, contrasts, thresholds, or statistical
  significance.
- Do not treat technical replicates as independent biological replicates.
- Do not silently remove samples or features; report rules and before/after
  counts.
- Preserve raw inputs and write derived artifacts to separate paths.
- If the design cannot identify the requested effect, report the limitation
  instead of forcing a model.

## Scope

This skill begins with prepared matrices or tables. Raw FASTQ/BAM processing and
repeatable workflow orchestration belong to `omics-pipeline`; dataset discovery
belongs to `omics-database`; paper search belongs to `omics-literature`.
Transcriptomics-specific analysis belongs to `transcriptomics-analysis`.
