#!/usr/bin/env Rscript

script_args <- commandArgs(trailingOnly = FALSE)
script_file <- sub("^--file=", "", script_args[grep("^--file=", script_args)])
script_file <- if (length(script_file) > 0) normalizePath(script_file[[1]]) else normalizePath(".")
source(file.path(dirname(dirname(script_file)), "lib", "common.R"))

usage <- function() {
  cat(
    "Usage: pca_correlation.R --counts counts.tsv --metadata metadata.tsv --sample-column sample_id --outdir outdir [options]\n",
    "\n",
    "Options:\n",
    "  --gene-column gene_id       Feature identifier column. Defaults to first non-numeric column.\n",
    "  --top-variable 500          Number of most variable features used for PCA/correlation.\n",
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
outdir <- arg_value(args, "outdir", required = TRUE)
top_variable <- as_integer_arg(args, "top-variable", 500)

ensure_dir(outdir)

counts <- read_counts(counts_path, gene_column)
validate_nonnegative_counts(counts)
metadata <- read_metadata(metadata_path, sample_column)
metadata <- align_counts_metadata(counts, metadata)

log_counts <- log_cpm(counts)
feature_variance <- apply(log_counts, 1, stats::var)
usable_features <- names(feature_variance)[is.finite(feature_variance) & feature_variance > 0]

if (length(usable_features) < 2) {
  fail("Need at least two variable features for PCA and correlation analysis")
}

selected_features <- usable_features[
  order(feature_variance[usable_features], decreasing = TRUE)
][seq_len(min(top_variable, length(usable_features)))]

selected_matrix <- log_counts[selected_features, , drop = FALSE]
pca <- stats::prcomp(t(selected_matrix), center = TRUE, scale. = FALSE)
component_count <- min(10, ncol(pca$x))

pca_scores <- data.frame(
  sample_id = rownames(pca$x),
  pca$x[, seq_len(component_count), drop = FALSE],
  check.names = FALSE
)

metadata_extra <- metadata[rownames(pca$x), setdiff(colnames(metadata), sample_column), drop = FALSE]
if (ncol(metadata_extra) > 0) {
  pca_scores <- cbind(pca_scores, metadata_extra)
  colnames(pca_scores) <- make.unique(colnames(pca_scores), sep = "_")
}

pca_variance <- data.frame(
  component = paste0("PC", seq_along(pca$sdev)),
  variance = pca$sdev^2,
  variance_fraction = (pca$sdev^2) / sum(pca$sdev^2),
  stringsAsFactors = FALSE
)

feature_selection <- data.frame(
  feature_id = selected_features,
  variance = feature_variance[selected_features],
  stringsAsFactors = FALSE
)

sample_correlation <- stats::cor(selected_matrix, method = "pearson")

write_tsv(pca_scores, file.path(outdir, "pca_samples.tsv"))
write_tsv(pca_variance, file.path(outdir, "pca_variance.tsv"))
write_tsv(feature_selection, file.path(outdir, "selected_variable_features.tsv"))
write_matrix_with_id(sample_correlation, file.path(outdir, "sample_correlation.tsv"), id_name = "sample_id")

info("Wrote bulk RNA-seq exploratory outputs to %s", outdir)
