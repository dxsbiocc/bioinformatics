#!/usr/bin/env Rscript

script_args <- commandArgs(trailingOnly = FALSE)
script_file <- sub("^--file=", "", script_args[grep("^--file=", script_args)])
script_file <- if (length(script_file) > 0) normalizePath(script_file[[1]]) else normalizePath(".")
source(file.path(dirname(dirname(script_file)), "lib", "common.R"))

usage <- function() {
  cat(
    "Usage: limma_voom.R --counts counts.tsv --metadata metadata.tsv --sample-column sample_id --condition-column condition --reference-level control --contrast-level treated --outdir outdir [options]\n",
    "\n",
    "Options:\n",
    "  --gene-column gene_id       Feature identifier column. Defaults to first non-numeric column.\n",
    "  --covariates batch,sex      Optional comma-separated covariates placed before condition in the design.\n",
    "  --min-count 10              Count threshold for prefiltering.\n",
    "  --min-samples 2             Minimum samples meeting --min-count.\n",
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

if (!requireNamespace("edgeR", quietly = TRUE)) {
  fail("The edgeR R package is required for this script")
}
if (!requireNamespace("limma", quietly = TRUE)) {
  fail("The limma R package is required for this script")
}

counts_path <- arg_value(args, "counts", required = TRUE)
metadata_path <- arg_value(args, "metadata", required = TRUE)
sample_column <- arg_value(args, "sample-column", required = TRUE)
condition_column <- arg_value(args, "condition-column", required = TRUE)
reference_level <- arg_value(args, "reference-level", required = TRUE)
contrast_level <- arg_value(args, "contrast-level", required = TRUE)
gene_column <- arg_value(args, "gene-column", default = NULL)
covariates <- split_csv_arg(args, "covariates")
outdir <- arg_value(args, "outdir", required = TRUE)
min_count <- as_number_arg(args, "min-count", 10)
min_samples <- as_integer_arg(args, "min-samples", 2)
fdr <- as_number_arg(args, "fdr", 0.05)

if (fdr <= 0 || fdr >= 1) {
  fail("--fdr must be between 0 and 1")
}
require_qc_review(args, "limma-voom")

ensure_dir(outdir)

counts <- read_counts(counts_path, gene_column)
validate_nonnegative_counts(counts, require_integer = TRUE)
counts <- round(counts)
storage.mode(counts) <- "integer"

metadata <- read_metadata(metadata_path, sample_column)
metadata <- align_counts_metadata(counts, metadata)
model <- prepare_de_model(metadata, covariates, condition_column, reference_level, contrast_level)

keep <- rowSums(counts >= min_count) >= min_samples
if (sum(keep) == 0) {
  fail("No features passed the prefilter: count >= %s in at least %s samples", min_count, min_samples)
}

y <- edgeR::DGEList(counts = counts[keep, , drop = FALSE], samples = model$metadata)
y <- edgeR::calcNormFactors(y)
voom_fit <- limma::voom(y, design = model$design, plot = FALSE)
fit <- limma::lmFit(voom_fit, design = model$design)
fit <- limma::eBayes(fit)

result_table <- limma::topTable(
  fit,
  coef = model$contrast_coefficient,
  number = Inf,
  sort.by = "P"
)
result_table <- data.frame(feature_id = rownames(result_table), result_table, check.names = FALSE)
result_table <- result_table[order(result_table$adj.P.Val, result_table$P.Value, na.last = TRUE), ]

write_tsv(result_table, file.path(outdir, "limma_voom_results.tsv"))
write_matrix_with_id(voom_fit$E, file.path(outdir, "voom_log_cpm.tsv"))
write_de_run_parameters(
  file.path(outdir, "run_parameters.tsv"),
  model$design_formula,
  condition_column,
  reference_level,
  contrast_level,
  covariates,
  min_count,
  min_samples,
  fdr,
  nrow(counts),
  nrow(result_table),
  matrix_scale = "raw_counts"
)
writeLines(capture.output(summary(result_table$adj.P.Val < fdr, na.rm = TRUE)), file.path(outdir, "fdr_summary.txt"))
writeLines(capture.output(sessionInfo()), file.path(outdir, "session_info.txt"))

info("Wrote limma-voom outputs to %s", outdir)
