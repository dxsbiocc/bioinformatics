#!/usr/bin/env Rscript

script_args <- commandArgs(trailingOnly = FALSE)
script_file <- sub("^--file=", "", script_args[grep("^--file=", script_args)])
script_file <- if (length(script_file) > 0) normalizePath(script_file[[1]]) else normalizePath(".")
source(file.path(dirname(dirname(script_file)), "lib", "common.R"))

usage <- function() {
  cat(
    "Usage: pre_de_qc.R --metadata metadata.tsv --sample-column sample_id --condition-column condition --outdir outdir (--counts counts.tsv | --expression expression.tsv) [options]\n",
    "\n",
    "Options:\n",
    "  --gene-column gene_id              Feature identifier column. Defaults to first non-numeric column.\n",
    "  --covariates batch,sex             Optional comma-separated covariates to assess against top PCs.\n",
    "  --matrix-scale auto                Recorded expression scale when using --expression.\n",
    "  --already-log2                     Treat --expression values as already log2-transformed.\n",
    "  --pseudocount 1                    Pseudocount before log2 transform for positive expression.\n",
    "  --top-variable 500                 Number of most variable features used for PCA/correlation.\n",
    "  --min-samples-per-group 2          Minimum biological samples expected per condition.\n",
    "  --min-sample-correlation 0.6       Warning threshold for minimum sample correlation.\n",
    "  --outlier-z 3.5                    Robust z-score warning threshold for sample QC metrics.\n",
    sep = ""
  )
}

robust_z <- function(values) {
  values <- as.numeric(values)
  center <- stats::median(values, na.rm = TRUE)
  scale <- stats::mad(values, center = center, constant = 1.4826, na.rm = TRUE)
  if (!is.finite(scale) || scale == 0) {
    scale <- stats::sd(values, na.rm = TRUE)
  }
  if (!is.finite(scale) || scale == 0) {
    return(rep(0, length(values)))
  }
  (values - center) / scale
}

append_warning <- function(warnings, severity, check, detail) {
  rbind(
    warnings,
    data.frame(severity = severity, check = check, detail = detail, stringsAsFactors = FALSE)
  )
}

pc_association <- function(pca_scores, metadata, terms) {
  rows <- list()
  pc_columns <- grep("^PC[0-9]+$", colnames(pca_scores), value = TRUE)
  pc_columns <- head(pc_columns, 5)

  for (term in terms) {
    if (!term %in% colnames(metadata)) {
      next
    }
    term_values <- metadata[pca_scores$sample_id, term]
    if (length(unique(term_values[!is.na(term_values)])) < 2) {
      next
    }

    for (pc in pc_columns) {
      data <- data.frame(
        pc_value = pca_scores[[pc]],
        term_value = term_values,
        stringsAsFactors = FALSE
      )
      if (!is.numeric(data$term_value)) {
        data$term_value <- factor(data$term_value)
      }

      fit <- tryCatch(stats::lm(pc_value ~ term_value, data = data), error = function(error) NULL)
      if (is.null(fit)) {
        next
      }
      fit_summary <- summary(fit)
      anova_table <- tryCatch(stats::anova(fit), error = function(error) NULL)
      p_value <- if (!is.null(anova_table) && "Pr(>F)" %in% colnames(anova_table)) {
        anova_table[["Pr(>F)"]][[1]]
      } else {
        NA_real_
      }

      rows[[length(rows) + 1]] <- data.frame(
        term = term,
        component = pc,
        r_squared = fit_summary$r.squared,
        p_value = p_value,
        stringsAsFactors = FALSE
      )
    }
  }

  if (length(rows) == 0) {
    return(data.frame(term = character(), component = character(), r_squared = numeric(), p_value = numeric()))
  }
  do.call(rbind, rows)
}

args <- parse_args()
if (isTRUE(args[["help"]])) {
  usage()
  quit(status = 0)
}

counts_path <- arg_value(args, "counts", default = NULL)
expression_path <- arg_value(args, "expression", default = NULL)
if (is.null(counts_path) && is.null(expression_path)) {
  fail("Provide either --counts or --expression")
}
if (!is.null(counts_path) && !is.null(expression_path)) {
  fail("Provide only one of --counts or --expression for this preflight run")
}

metadata_path <- arg_value(args, "metadata", required = TRUE)
sample_column <- arg_value(args, "sample-column", required = TRUE)
condition_column <- arg_value(args, "condition-column", required = TRUE)
gene_column <- arg_value(args, "gene-column", default = NULL)
covariates <- split_csv_arg(args, "covariates")
matrix_scale <- arg_value(args, "matrix-scale", default = "auto")
already_log2 <- isTRUE(args[["already-log2"]])
outdir <- arg_value(args, "outdir", required = TRUE)
pseudocount <- as_number_arg(args, "pseudocount", 1)
top_variable <- as_integer_arg(args, "top-variable", 500)
min_samples_per_group <- as_integer_arg(args, "min-samples-per-group", 2)
min_sample_correlation <- as_number_arg(args, "min-sample-correlation", 0.6)
outlier_z <- as_number_arg(args, "outlier-z", 3.5)

if (pseudocount < 0) {
  fail("--pseudocount must be non-negative")
}

ensure_dir(outdir)

metadata <- read_metadata(metadata_path, sample_column)
require_columns(metadata, condition_column, "Metadata")

if (!is.null(counts_path)) {
  matrix <- read_counts(counts_path, gene_column)
  validate_nonnegative_counts(matrix)
  metadata <- align_counts_metadata(matrix, metadata)
  analysis_matrix <- log_cpm(matrix)
  matrix_label <- "counts"
  matrix_scale <- "raw_counts"
  sample_qc <- data.frame(
    sample_id = colnames(matrix),
    total_signal = colSums(matrix),
    detected_features = colSums(matrix > 0),
    zero_fraction = colMeans(matrix == 0),
    stringsAsFactors = FALSE
  )
} else {
  matrix <- read_feature_matrix(expression_path, gene_column, label = "Expression matrix")
  metadata <- align_counts_metadata(matrix, metadata)
  matrix_label <- "expression"
  if (already_log2) {
    analysis_matrix <- matrix
  } else {
    validate_nonnegative_matrix(matrix)
    analysis_matrix <- log2(matrix + pseudocount)
  }
  sample_qc <- data.frame(
    sample_id = colnames(matrix),
    total_signal = colSums(matrix),
    detected_features = colSums(matrix > 0),
    zero_fraction = colMeans(matrix == 0),
    stringsAsFactors = FALSE
  )
}

sample_qc$total_signal_robust_z <- robust_z(sample_qc$total_signal)
sample_qc$detected_features_robust_z <- robust_z(sample_qc$detected_features)
sample_qc$condition <- metadata[sample_qc$sample_id, condition_column]

feature_variance <- apply(analysis_matrix, 1, stats::var)
usable_features <- names(feature_variance)[is.finite(feature_variance) & feature_variance > 0]
if (length(usable_features) < 2) {
  fail("Need at least two variable features for pre-DE PCA and correlation")
}
selected_features <- usable_features[
  order(feature_variance[usable_features], decreasing = TRUE)
][seq_len(min(top_variable, length(usable_features)))]
selected_matrix <- analysis_matrix[selected_features, , drop = FALSE]

pca <- stats::prcomp(t(selected_matrix), center = TRUE, scale. = FALSE)
component_count <- min(10, ncol(pca$x))
pca_scores <- data.frame(
  sample_id = rownames(pca$x),
  pca$x[, seq_len(component_count), drop = FALSE],
  check.names = FALSE
)
pca_scores <- cbind(
  pca_scores,
  metadata[pca_scores$sample_id, c(condition_column, covariates), drop = FALSE]
)
colnames(pca_scores) <- make.unique(colnames(pca_scores), sep = "_")

pca_variance <- data.frame(
  component = paste0("PC", seq_along(pca$sdev)),
  variance = pca$sdev^2,
  variance_fraction = (pca$sdev^2) / sum(pca$sdev^2),
  stringsAsFactors = FALSE
)

sample_correlation <- stats::cor(selected_matrix, method = "pearson")
sample_correlation_summary <- data.frame(
  sample_id = colnames(sample_correlation),
  min_correlation = NA_real_,
  median_correlation = NA_real_,
  stringsAsFactors = FALSE
)
for (sample_id in sample_correlation_summary$sample_id) {
  values <- sample_correlation[, sample_id]
  values <- values[names(values) != sample_id]
  sample_correlation_summary[sample_correlation_summary$sample_id == sample_id, "min_correlation"] <- min(values, na.rm = TRUE)
  sample_correlation_summary[sample_correlation_summary$sample_id == sample_id, "median_correlation"] <- stats::median(values, na.rm = TRUE)
}

group_counts <- as.data.frame(table(metadata[[condition_column]]), stringsAsFactors = FALSE)
colnames(group_counts) <- c(condition_column, "sample_count")

assessed_terms <- unique(c(condition_column, covariates))
pca_association <- pc_association(pca_scores, metadata, assessed_terms)

warnings <- data.frame(severity = character(), check = character(), detail = character(), stringsAsFactors = FALSE)
small_groups <- group_counts[group_counts$sample_count < min_samples_per_group, , drop = FALSE]
if (nrow(small_groups) > 0) {
  warnings <- append_warning(
    warnings,
    "severe",
    "group_sample_count",
    paste("Condition group(s) below minimum sample count:", paste(small_groups[[condition_column]], collapse = ", "))
  )
}

outlier_samples <- sample_qc[
  abs(sample_qc$total_signal_robust_z) > outlier_z |
    abs(sample_qc$detected_features_robust_z) > outlier_z,
  ,
  drop = FALSE
]
if (nrow(outlier_samples) > 0) {
  warnings <- append_warning(
    warnings,
    "review",
    "sample_uniformity",
    paste("Sample(s) with outlying total signal or detected features:", paste(outlier_samples$sample_id, collapse = ", "))
  )
}

low_correlation <- sample_correlation_summary[sample_correlation_summary$min_correlation < min_sample_correlation, , drop = FALSE]
if (nrow(low_correlation) > 0) {
  warnings <- append_warning(
    warnings,
    "review",
    "sample_correlation",
    paste("Sample(s) below minimum correlation threshold:", paste(low_correlation$sample_id, collapse = ", "))
  )
}

condition_assoc <- pca_association[pca_association$term == condition_column, , drop = FALSE]
if (nrow(condition_assoc) > 0) {
  top_condition_r2 <- max(condition_assoc$r_squared[condition_assoc$component %in% c("PC1", "PC2")], na.rm = TRUE)
  if (is.finite(top_condition_r2) && top_condition_r2 < 0.1) {
    warnings <- append_warning(
      warnings,
      "note",
      "pca_condition_signal",
      "Condition does not explain much variance in PC1/PC2; review whether the expected biology should dominate PCA."
    )
  }
}

covariate_assoc <- pca_association[pca_association$term %in% covariates, , drop = FALSE]
if (nrow(covariate_assoc) > 0 && nrow(condition_assoc) > 0) {
  condition_top <- max(condition_assoc$r_squared, na.rm = TRUE)
  covariate_top <- max(covariate_assoc$r_squared, na.rm = TRUE)
  if (is.finite(condition_top) && is.finite(covariate_top) && covariate_top > condition_top) {
    warnings <- append_warning(
      warnings,
      "review",
      "pca_covariate_signal",
      "A covariate explains more top-PC variance than the condition; check batch or confounding before DE."
    )
  }
}

if (nrow(warnings) == 0) {
  warnings <- append_warning(warnings, "ok", "pre_de_qc", "No automatic pre-DE QC warnings were triggered; visual review is still required.")
}

decision <- data.frame(
  item = c(
    "review_required",
    "matrix_used_for_pca",
    "selected_features",
    "condition_column",
    "instruction"
  ),
  value = c(
    "true",
    paste(matrix_label, matrix_scale, sep = ":"),
    length(selected_features),
    condition_column,
    "Review sample_qc.tsv, pca_samples.tsv, pca_variance.tsv, sample_correlation.tsv, pca_association.tsv, and pre_de_warnings.tsv before running DE with --qc-reviewed."
  ),
  stringsAsFactors = FALSE
)

write_tsv(sample_qc, file.path(outdir, "sample_qc.tsv"))
write_tsv(group_counts, file.path(outdir, "group_sample_counts.tsv"))
write_tsv(pca_scores, file.path(outdir, "pca_samples.tsv"))
write_tsv(pca_variance, file.path(outdir, "pca_variance.tsv"))
write_matrix_with_id(sample_correlation, file.path(outdir, "sample_correlation.tsv"), id_name = "sample_id")
write_tsv(sample_correlation_summary, file.path(outdir, "sample_correlation_summary.tsv"))
write_tsv(pca_association, file.path(outdir, "pca_association.tsv"))
write_tsv(data.frame(feature_id = selected_features, variance = feature_variance[selected_features]), file.path(outdir, "selected_variable_features.tsv"))
write_tsv(warnings, file.path(outdir, "pre_de_warnings.tsv"))
write_tsv(decision, file.path(outdir, "pre_de_decision.tsv"))

info("Wrote pre-DE QC outputs to %s", outdir)
