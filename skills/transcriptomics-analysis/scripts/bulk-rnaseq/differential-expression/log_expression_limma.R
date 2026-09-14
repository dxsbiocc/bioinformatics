#!/usr/bin/env Rscript

script_args <- commandArgs(trailingOnly = FALSE)
script_file <- sub("^--file=", "", script_args[grep("^--file=", script_args)])
script_file <- if (length(script_file) > 0) normalizePath(script_file[[1]]) else normalizePath(".")
source(file.path(dirname(dirname(script_file)), "lib", "common.R"))

usage <- function() {
  cat(
    "Usage: log_expression_limma.R --expression tpm.tsv --metadata metadata.tsv --sample-column sample_id --condition-column condition --reference-level control --contrast-level treated --outdir outdir [options]\n",
    "\n",
    "Options:\n",
    "  --gene-column gene_id       Feature identifier column. Defaults to first non-numeric column.\n",
    "  --covariates batch,sex      Optional comma-separated covariates placed before condition in the design.\n",
    "  --matrix-scale TPM          Recorded matrix scale, for example TPM, FPKM, CPM, or log2TPM.\n",
    "  --already-log2              Treat expression values as already log2-transformed.\n",
    "  --pseudocount 1             Pseudocount used before log2 transform.\n",
    "  --fdr 0.05                  FDR threshold recorded in run parameters.\n",
    "  --qc-reviewed               Required: confirms pre-DE QC, PCA, sample correlation, and design checks were reviewed.\n",
    sep = ""
  )
}

args <- parse_args()
if (isTRUE(args[["help"]])) {
  usage()
  quit(status = 0)
}

if (!requireNamespace("limma", quietly = TRUE)) {
  fail("The limma R package is required for this script")
}

expression_path <- arg_value(args, "expression", required = TRUE)
metadata_path <- arg_value(args, "metadata", required = TRUE)
sample_column <- arg_value(args, "sample-column", required = TRUE)
condition_column <- arg_value(args, "condition-column", required = TRUE)
reference_level <- arg_value(args, "reference-level", required = TRUE)
contrast_level <- arg_value(args, "contrast-level", required = TRUE)
gene_column <- arg_value(args, "gene-column", default = NULL)
covariates <- split_csv_arg(args, "covariates")
matrix_scale <- arg_value(args, "matrix-scale", default = "normalized_expression")
already_log2 <- isTRUE(args[["already-log2"]])
outdir <- arg_value(args, "outdir", required = TRUE)
pseudocount <- as_number_arg(args, "pseudocount", 1)
fdr <- as_number_arg(args, "fdr", 0.05)

if (fdr <= 0 || fdr >= 1) {
  fail("--fdr must be between 0 and 1")
}
if (pseudocount < 0) {
  fail("--pseudocount must be non-negative")
}
require_qc_review(args, "normalized-expression limma fallback")

ensure_dir(outdir)

expression <- read_feature_matrix(expression_path, gene_column, label = "Expression matrix")
if (!already_log2) {
  validate_nonnegative_matrix(expression, label = "Expression matrix")
  expression <- log2(expression + pseudocount)
}

features_before_filter <- nrow(expression)
finite_variance <- apply(expression, 1, stats::var)
keep <- is.finite(finite_variance) & finite_variance > 0
if (sum(keep) == 0) {
  fail("No variable features are available for limma analysis")
}
expression <- expression[keep, , drop = FALSE]

metadata <- read_metadata(metadata_path, sample_column)
metadata <- align_counts_metadata(expression, metadata)
model <- prepare_de_model(metadata, covariates, condition_column, reference_level, contrast_level)

fit <- limma::lmFit(expression, design = model$design)
fit <- limma::eBayes(fit, trend = TRUE)
result_table <- limma::topTable(
  fit,
  coef = model$contrast_coefficient,
  number = Inf,
  sort.by = "P"
)
result_table <- data.frame(feature_id = rownames(result_table), result_table, check.names = FALSE)
result_table <- result_table[order(result_table$adj.P.Val, result_table$P.Value, na.last = TRUE), ]

method_note <- c(
  "This script is a fallback for normalized expression matrices such as TPM, FPKM, CPM, or already log-transformed values.",
  "It does not recover raw counts and should not be presented as a count-model analysis.",
  "Prefer DESeq2, edgeR, or limma-voom from raw or estimated counts when count matrices are available.",
  "If raw counts and normalized expression are both available, use the raw count matrix for differential expression and reserve normalized expression for summaries or visualization."
)

write_tsv(result_table, file.path(outdir, "log_expression_limma_results.tsv"))
write_matrix_with_id(expression, file.path(outdir, "log_expression_matrix.tsv"))
write_de_run_parameters(
  file.path(outdir, "run_parameters.tsv"),
  model$design_formula,
  condition_column,
  reference_level,
  contrast_level,
  covariates,
  min_count = NA,
  min_samples = NA,
  fdr = fdr,
  features_before_filter = features_before_filter,
  features_after_filter = nrow(result_table),
  matrix_scale = matrix_scale
)
writeLines(method_note, file.path(outdir, "method_limitations.txt"))
writeLines(capture.output(summary(result_table$adj.P.Val < fdr, na.rm = TRUE)), file.path(outdir, "fdr_summary.txt"))
writeLines(capture.output(sessionInfo()), file.path(outdir, "session_info.txt"))

info("Wrote fallback limma outputs to %s", outdir)
