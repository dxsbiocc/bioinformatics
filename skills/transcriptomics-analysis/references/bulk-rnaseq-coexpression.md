# Bulk RNA-seq Coexpression

Use this reference for gene-gene correlation, module discovery, module-trait
association, and hub-gene exploration from a bulk expression matrix.

## Inputs

- Sample-level expression matrix with enough biological samples to estimate
  correlations. Coexpression is usually underpowered with very small cohorts.
- Metadata with condition, batch, donor, time, phenotype, or other traits to
  associate with modules.
- A transformed expression scale such as log-CPM, VST, rlog, or log2 TPM/FPKM.
  Raw counts should be transformed before correlation.
- Filtering rule for low or uninformative genes before correlation.

## Method Choice

- Use simple correlation modules for quick exploratory structure and handoff to
  visualization.
- Use WGCNA or similar weighted network methods when the study has enough
  samples, needs soft-threshold selection, module merging, and more formal
  hub-gene analysis.
- Use module eigengenes or first principal components for module-trait
  association, and model known covariates when the biological claim depends on
  them.

## Script Support

`scripts/bulk-rnaseq/coexpression/correlation_modules.R` creates lightweight
hierarchical correlation modules, module eigengenes, module-trait associations,
hub-feature rankings, and selected-variable-feature tables using base R.

This script is intentionally exploratory. For final WGCNA-style claims, create a
project-specific analysis that records soft-threshold choice, signed/unsigned
network type, module merging, trait modeling, and sample outlier handling.

## Guardrails

- Do not run coexpression on raw counts without transformation.
- Do not claim causal regulation from correlation modules.
- Do not interpret hub genes without checking expression level, annotation,
  batch association, and module robustness.
- Do not trust modules built from too few samples or dominated by a technical
  covariate.

## Deliverables

Return module assignments, module eigengenes, module-trait association tables,
hub-feature rankings, filtering choices, matrix scale, and limitations around
sample size and confounding.
