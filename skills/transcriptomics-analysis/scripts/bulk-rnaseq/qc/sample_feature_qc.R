#!/usr/bin/env Rscript

script_args <- commandArgs(trailingOnly = FALSE)
script_file <- sub("^--file=", "", script_args[grep("^--file=", script_args)])
script_file <- if (length(script_file) > 0) normalizePath(script_file[[1]]) else normalizePath(".")
source(file.path(dirname(dirname(script_file)), "lib", "common.R"))

usage <- function() {
  cat(
    "Usage: sample_feature_qc.R --counts counts.tsv --metadata metadata.tsv --sample-column sample_id --outdir outdir [options]\n",
    "\n",
    "Options:\n",
    "  --gene-column gene_id       Feature identifier column. Defaults to first non-numeric column.\n",
    "  --group-column condition    Optional metadata column to copy into sample QC output.\n",
    "  --min-count 10              Count threshold for feature filter summary.\n",
    "  --min-samples 2             Minimum samples meeting --min-count.\n",
    sep = ""
  )
}

args <- parse_args()
if (isTRUE(args[["help"]])) {
  usage()
  quit(status = 0)
}

counts_path <- arg_value(args, "counts", required = TRUE)
metadata_path <- arg_value(args, "metadata", required = TRUE)
sample_column <- arg_value(args, "sample-column", required = TRUE)
gene_column <- arg_value(args, "gene-column", default = NULL)
group_column <- arg_value(args, "group-column", default = NULL)
outdir <- arg_value(args, "outdir", required = TRUE)
min_count <- as_number_arg(args, "min-count", 10)
min_samples <- as_integer_arg(args, "min-samples", 2)

ensure_dir(outdir)

counts <- read_counts(counts_path, gene_column)
validate_nonnegative_counts(counts)
metadata <- read_metadata(metadata_path, sample_column)
metadata <- align_counts_metadata(counts, metadata)

if (!is.null(group_column)) {
  require_columns(metadata, group_column, "Metadata")
}

sample_qc <- data.frame(
  sample_id = colnames(counts),
  total_counts = colSums(counts),
  detected_features = colSums(counts > 0),
  zero_fraction = colMeans(counts == 0),
  stringsAsFactors = FALSE
)

if (!is.null(group_column)) {
  sample_qc[[group_column]] <- metadata[[group_column]]
}

feature_pass <- rowSums(counts >= min_count) >= min_samples
feature_qc <- data.frame(
  feature_id = rownames(counts),
  total_counts = rowSums(counts),
  detected_samples = rowSums(counts > 0),
  mean_count = rowMeans(counts),
  max_count = apply(counts, 1, max),
  pass_filter = feature_pass,
  stringsAsFactors = FALSE
)

summary_table <- data.frame(
  metric = c(
    "features",
    "samples",
    "total_counts",
    "median_library_size",
    "median_detected_features",
    "features_passing_filter",
    "min_count",
    "min_samples"
  ),
  value = c(
    nrow(counts),
    ncol(counts),
    sum(counts),
    stats::median(colSums(counts)),
    stats::median(colSums(counts > 0)),
    sum(feature_pass),
    min_count,
    min_samples
  ),
  stringsAsFactors = FALSE
)

write_tsv(sample_qc, file.path(outdir, "sample_qc.tsv"))
write_tsv(feature_qc, file.path(outdir, "feature_qc.tsv"))
write_tsv(summary_table, file.path(outdir, "matrix_summary.tsv"))
write_matrix_with_id(log_cpm(counts), file.path(outdir, "log_cpm.tsv"))

if (!is.null(group_column)) {
  group_counts <- as.data.frame(table(metadata[[group_column]]), stringsAsFactors = FALSE)
  colnames(group_counts) <- c(group_column, "sample_count")
  write_tsv(group_counts, file.path(outdir, "group_sample_counts.tsv"))
}

info("Wrote bulk RNA-seq QC outputs to %s", outdir)
