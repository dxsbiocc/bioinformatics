#!/usr/bin/env Rscript

script_args <- commandArgs(trailingOnly = FALSE)
script_file <- sub("^--file=", "", script_args[grep("^--file=", script_args)])
script_file <- if (length(script_file) > 0) normalizePath(script_file[[1]]) else normalizePath(".")
source(file.path(dirname(dirname(script_file)), "lib", "common.R"))

usage <- function() {
  cat(
    "Usage: correlation_modules.R --metadata metadata.tsv --sample-column sample_id --outdir outdir (--counts counts.tsv | --expression expression.tsv) [options]\n",
    "\n",
    "Options:\n",
    "  --gene-column gene_id           Feature identifier column. Defaults to first non-numeric column.\n",
    "  --trait-columns condition,batch  Optional comma-separated metadata traits to associate with modules.\n",
    "  --matrix-scale auto             Recorded scale when using --expression.\n",
    "  --already-log2                  Treat --expression values as already log2-transformed.\n",
    "  --pseudocount 1                 Pseudocount before log2 transform for positive expression.\n",
    "  --top-variable 2000             Number of most variable features used for modules.\n",
    "  --module-count 6                Number of hierarchical modules to cut.\n",
    sep = ""
  )
}

trait_association <- function(eigengenes, metadata, traits) {
  rows <- list()
  if (length(traits) == 0) {
    return(data.frame(module = character(), trait = character(), r_squared = numeric(), p_value = numeric()))
  }

  for (module in setdiff(colnames(eigengenes), "sample_id")) {
    for (trait in traits) {
      if (!trait %in% colnames(metadata)) {
        next
      }
      data <- data.frame(
        eigengene = eigengenes[[module]],
        trait_value = metadata[eigengenes$sample_id, trait],
        stringsAsFactors = FALSE
      )
      if (!is.numeric(data$trait_value)) {
        data$trait_value <- factor(data$trait_value)
      }
      if (length(unique(data$trait_value[!is.na(data$trait_value)])) < 2) {
        next
      }

      fit <- tryCatch(stats::lm(eigengene ~ trait_value, data = data), error = function(error) NULL)
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
        module = module,
        trait = trait,
        r_squared = fit_summary$r.squared,
        p_value = p_value,
        stringsAsFactors = FALSE
      )
    }
  }

  if (length(rows) == 0) {
    return(data.frame(module = character(), trait = character(), r_squared = numeric(), p_value = numeric()))
  }
  associations <- do.call(rbind, rows)
  associations$padj <- stats::p.adjust(associations$p_value, method = "BH")
  associations[order(associations$padj, associations$p_value), ]
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
  fail("Provide only one of --counts or --expression")
}

metadata_path <- arg_value(args, "metadata", required = TRUE)
sample_column <- arg_value(args, "sample-column", required = TRUE)
gene_column <- arg_value(args, "gene-column", default = NULL)
trait_columns <- split_csv_arg(args, "trait-columns")
matrix_scale <- arg_value(args, "matrix-scale", default = "auto")
already_log2 <- isTRUE(args[["already-log2"]])
outdir <- arg_value(args, "outdir", required = TRUE)
pseudocount <- as_number_arg(args, "pseudocount", 1)
top_variable <- as_integer_arg(args, "top-variable", 2000)
module_count <- as_integer_arg(args, "module-count", 6)

if (module_count < 2) {
  fail("--module-count must be at least 2")
}
if (pseudocount < 0) {
  fail("--pseudocount must be non-negative")
}

ensure_dir(outdir)

metadata <- read_metadata(metadata_path, sample_column)
if (length(trait_columns) > 0) {
  require_columns(metadata, trait_columns, "Metadata")
}

if (!is.null(counts_path)) {
  matrix <- read_counts(counts_path, gene_column)
  validate_nonnegative_counts(matrix)
  metadata <- align_counts_metadata(matrix, metadata)
  analysis_matrix <- log_cpm(matrix)
  matrix_used <- "counts:log_cpm"
} else {
  matrix <- read_feature_matrix(expression_path, gene_column, label = "Expression matrix")
  metadata <- align_counts_metadata(matrix, metadata)
  if (already_log2) {
    analysis_matrix <- matrix
  } else {
    validate_nonnegative_matrix(matrix)
    analysis_matrix <- log2(matrix + pseudocount)
  }
  matrix_used <- paste("expression", matrix_scale, sep = ":")
}

feature_variance <- apply(analysis_matrix, 1, stats::var)
usable_features <- names(feature_variance)[is.finite(feature_variance) & feature_variance > 0]
if (length(usable_features) < 3) {
  fail("Need at least three variable features for coexpression modules")
}

selected_features <- usable_features[
  order(feature_variance[usable_features], decreasing = TRUE)
][seq_len(min(top_variable, length(usable_features)))]
selected_matrix <- analysis_matrix[selected_features, , drop = FALSE]
feature_correlation <- stats::cor(t(selected_matrix), method = "pearson")
feature_correlation[is.na(feature_correlation)] <- 0

distance <- stats::as.dist(1 - feature_correlation)
tree <- stats::hclust(distance, method = "average")
module_count <- min(module_count, length(selected_features))
module_id <- stats::cutree(tree, k = module_count)
module_label <- paste0("module_", module_id)

module_assignments <- data.frame(
  feature_id = selected_features,
  module = module_label,
  variance = feature_variance[selected_features],
  stringsAsFactors = FALSE
)

eigengenes <- data.frame(sample_id = colnames(selected_matrix), stringsAsFactors = FALSE)
hub_rows <- list()
for (module in sort(unique(module_label))) {
  module_features <- module_assignments$feature_id[module_assignments$module == module]
  module_matrix <- selected_matrix[module_features, , drop = FALSE]
  if (nrow(module_matrix) == 1) {
    eigengene <- as.numeric(scale(module_matrix[1, ], center = TRUE, scale = FALSE))
  } else {
    pca <- stats::prcomp(t(module_matrix), center = TRUE, scale. = FALSE)
    eigengene <- pca$x[, 1]
  }
  eigengenes[[module]] <- eigengene

  membership <- apply(module_matrix, 1, function(values) suppressWarnings(stats::cor(values, eigengene)))
  hub_rows[[length(hub_rows) + 1]] <- data.frame(
    feature_id = names(membership),
    module = module,
    module_membership = membership,
    abs_module_membership = abs(membership),
    stringsAsFactors = FALSE
  )
}

hub_features <- do.call(rbind, hub_rows)
hub_features <- hub_features[order(hub_features$module, -hub_features$abs_module_membership), ]
associations <- trait_association(eigengenes, metadata, trait_columns)

parameters <- data.frame(
  parameter = c("matrix_used", "top_variable", "selected_features", "module_count", "trait_columns"),
  value = c(matrix_used, top_variable, length(selected_features), module_count, paste(trait_columns, collapse = ",")),
  stringsAsFactors = FALSE
)

notes <- c(
  "This script creates lightweight correlation modules by hierarchical clustering.",
  "It is not a replacement for a full WGCNA analysis with soft-threshold selection and module merging.",
  "Use modules as exploratory structure unless the analysis is expanded and validated for the study design."
)

write_tsv(module_assignments, file.path(outdir, "module_assignments.tsv"))
write_tsv(eigengenes, file.path(outdir, "module_eigengenes.tsv"))
write_tsv(hub_features, file.path(outdir, "hub_features.tsv"))
write_tsv(associations, file.path(outdir, "module_trait_association.tsv"))
write_tsv(data.frame(feature_id = selected_features, variance = feature_variance[selected_features]), file.path(outdir, "selected_variable_features.tsv"))
write_tsv(parameters, file.path(outdir, "run_parameters.tsv"))
writeLines(notes, file.path(outdir, "method_notes.txt"))
writeLines(capture.output(sessionInfo()), file.path(outdir, "session_info.txt"))

info("Wrote coexpression module outputs to %s", outdir)
