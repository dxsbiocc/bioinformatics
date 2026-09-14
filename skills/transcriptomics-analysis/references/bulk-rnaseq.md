# Bulk RNA-seq

Use this reference for prepared bulk RNA-seq gene, transcript, exon, or feature
expression matrices with sample metadata.

## Required Context

- Observation unit: biological sample, pooled sample, technical replicate, or
  lane-level intermediate.
- Matrix scale: raw counts, estimated counts, TPM/FPKM, CPM, variance-stabilized
  values, or other transformed values.
- Available matrices: when raw counts and TPM/FPKM/CPM/log-expression matrices
  coexist, record all of them and use raw or estimated counts as the primary
  input for differential expression.
- Experimental design: condition, batch, paired structure, blocking factors,
  continuous covariates, and intended contrasts.
- Replicate structure: biological replicates are required for inferential
  differential expression.
- Annotation: gene identifier namespace, genome build, annotation release, and
  duplicate or multi-mapped feature handling.

## Analysis Guidance

1. Validate sample names across expression matrix and metadata before modeling.
2. Summarize library sizes, detected genes, count distributions, composition
   shifts, outliers, and missing metadata.
3. Before differential expression, review sample uniformity, group sample
   counts, PCA structure, sample correlations, matrix scale, and design
   confounding. Treat this as a gate, not a decorative plot.
4. Filter lowly expressed features using rules compatible with the smallest
   group or contrast of interest, and report before/after counts.
5. Select differential expression methods from the matrix scale. Raw or
   estimated counts can use count-aware methods; TPM, FPKM, CPM, VST, rlog, and
   log-normalized matrices cannot be treated as raw counts.
6. Inspect the distribution and transformation state before modeling. Determine
   whether values are discrete raw counts, positive normalized expression, or
   already log-transformed values; do not assume normality.
7. Include batch, pairing, sex, donor, or other known covariates when the design
   supports them. Flag confounding when a covariate is inseparable from the
   contrast.
8. Use transformed values for QC, PCA, clustering, heatmaps, and correlation;
   use the model-appropriate count scale for inference.
9. Report log-fold-change direction, reference level, adjusted p-value method,
   filtering thresholds, model formula, and contrast definition.
10. For downstream interpretation, route gene-set enrichment, coexpression,
    splicing, fusion/event, or QTL questions to their dedicated transcriptomics
    references instead of stretching ordinary differential expression beyond its
    evidence.

## Pre-DE QC Gate

Differential expression scripts must not be the first analysis step. Before
running DESeq2, edgeR, limma-voom, or the normalized-expression limma fallback:

- Run matrix diagnostics when the scale is uncertain or multiple expression
  matrices are present.
- Run sample/feature QC and pre-DE PCA/correlation checks.
- Review whether samples are broadly comparable in library size or signal,
  detected features, zero fraction, and sample-sample correlation.
- Review whether PCA is consistent with known condition, batch, donor, pairing,
  or other covariates. PCA separation by condition is supportive but not
  required; unexpected batch or outlier structure must be explained.
- Check condition group sample counts and biological replication before making
  inferential claims.

Reusable differential expression scripts require `--qc-reviewed`. Passing that
flag means the QC, PCA, sample-correlation, matrix-scale, and design checks have
been inspected and unresolved issues are accepted or addressed.

## Input Priority and Distribution Checks

Use matrix type, provenance, and distribution diagnostics to choose the analysis
path:

- If a raw or estimated count matrix is available alongside TPM, FPKM, CPM, VST,
  rlog, or log-expression matrices, use the count matrix for DESeq2, edgeR, or
  limma-voom. Do not convert normalized matrices back to counts.
- If only TPM, FPKM, CPM, or log-expression values are available, first determine
  whether values are already log2-transformed. Use a documented log-expression
  linear-model fallback only when count or quantifier outputs cannot be
  recovered.
- Raw counts are not expected to be normally distributed. They are usually
  discrete, right-skewed, heteroscedastic, and often sparse; normality tests on
  raw counts should not drive the method away from count models.
- For normalized-expression fallback, inspect quantiles, skewness, zero
  fraction, QQ correlation, and Shapiro-Wilk summaries. If positive TPM/FPKM/CPM
  values are strongly skewed, log2-transform with an explicit pseudocount before
  linear modeling.
- If a matrix has negative values or a small bounded range, treat it as already
  transformed, residualized, or scaled until provenance confirms otherwise.

## Differential Expression Method Selection

For raw or estimated integer-like counts, the common first-line choices are:

- DESeq2: robust default for ordinary two-group or multifactor bulk RNA-seq
  differential expression from counts.
- edgeR: count-model analysis with strong support for small sample sizes,
  complex designs, and quasi-likelihood testing.
- limma-voom: count-aware linear modeling after estimating the mean-variance
  relationship; useful for larger studies and complex linear designs.

For TPM, FPKM, CPM, or already log-transformed expression matrices, do not run
DESeq2, edgeR, or limma-voom as if the values were counts. Prefer recovering the
original count matrix or quantifier output. If only normalized expression is
available, a limma analysis on log2 expression may be used as a documented
fallback, but report it as normalized-expression analysis with weaker
assumptions than count-model differential expression.

## Count and Normalized Matrix Conversion

- Counts -> CPM or log-CPM is valid when library sizes are available from the
  count matrix.
- Counts + feature lengths -> TPM or FPKM can be generated for expression
  summaries and visualization.
- TPM/FPKM/CPM/logCPM/VST/rlog -> raw counts is not reliably reversible. Do not
  multiply normalized values by a library size and round them for count-model
  differential expression.
- Transcript-level quantifier outputs from tools such as Salmon or kallisto can
  often be imported into gene-level count-like summaries with appropriate
  length handling. Final TPM-only matrices are not enough for that recovery.

## Script Groups

Use the reusable scripts under `scripts/bulk-rnaseq/` when the inputs and
experimental design match the script contract:

- `qc/sample_feature_qc.R` writes sample QC, feature QC, matrix summary, optional
  group sample counts, and log-CPM tables.
- `qc/pre_de_qc.R` writes pre-DE sample QC, group sample counts, PCA scores,
  explained variance, sample correlations, PCA associations with condition or
  covariates, selected variable features, warnings, and a review-required
  decision table.
- `diagnostics/assess_expression_matrices.R` compares provided count, TPM, FPKM,
  CPM, log-expression, or unknown-scale matrices; writes distribution summaries,
  normality diagnostics, input consistency checks, and method recommendations.
- `normalization/count_quantification_tables.R` writes CPM and log-CPM from
  counts, and TPM/FPKM when a feature length table is supplied. It also writes
  conversion notes that explicitly forbid normalized-to-count back-conversion.
- `exploratory/pca_correlation.R` writes PCA scores, explained variance,
  selected variable features, and sample-correlation tables from log-CPM values.
- `differential-expression/deseq2.R` runs DESeq2 on integer-like raw counts and
  writes differential expression results, normalized counts, variance-stabilized
  counts, run parameters, result summary, and session info.
- `differential-expression/edgeR.R` runs edgeR quasi-likelihood differential
  expression on integer-like raw counts and writes result, normalized CPM,
  log-CPM, parameters, and session info.
- `differential-expression/limma_voom.R` runs limma-voom on integer-like raw
  counts and writes result, voom log-CPM, parameters, and session info.
- `differential-expression/log_expression_limma.R` is a fallback for TPM, FPKM,
  CPM, or log-expression matrices when counts cannot be recovered. It writes
  method limitations and must not be described as count-model inference.
- `enrichment/ora_from_de.R` runs thresholded over-representation analysis from a
  DE result table and a GMT file.
- `enrichment/preranked_gsea.R` runs lightweight preranked GSEA from signed gene
  ranks and a GMT file.
- `coexpression/correlation_modules.R` builds exploratory gene-correlation
  modules, module eigengenes, module-trait associations, and hub-feature
  rankings.

Most scripts expect a count matrix, metadata table, sample identifier column,
and output directory. The normalized-expression fallback expects TPM, FPKM, CPM,
or log-expression values instead of counts. Prefer copying or adapting the
script into the project when the analysis needs project-specific formulas,
filtering, annotation joins, or reporting conventions.

## Guardrails

- Do not perform inferential differential expression without biological
  replication; provide descriptive fold changes and limitations instead.
- Do not use TPM/FPKM as a drop-in replacement for count input to count-based
  differential expression models.
- Do not collapse technical replicates without stating the rule.
- Do not remove an outlier sample unless the objective QC reason and downstream
  impact are reported.

## Deliverables

Return executable analysis code, normalized or transformed matrices when
created, QC tables, PCA or clustering coordinates when relevant, differential
expression result tables, model formulas, contrast definitions, and known
limitations.
