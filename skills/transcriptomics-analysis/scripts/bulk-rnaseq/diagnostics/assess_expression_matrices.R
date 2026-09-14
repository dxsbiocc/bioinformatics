#!/usr/bin/env Rscript

script_args <- commandArgs(trailingOnly = FALSE)
script_file <- sub("^--file=", "", script_args[grep("^--file=", script_args)])
script_file <- if (length(script_file) > 0) normalizePath(script_file[[1]]) else normalizePath(".")
source(file.path(dirname(dirname(script_file)), "lib", "common.R"))

usage <- function() {
  cat(
    "Usage: assess_expression_matrices.R --outdir outdir [matrix inputs]\n",
    "\n",
    "Matrix inputs:\n",
    "  --counts counts.tsv             Raw or estimated count matrix.\n",
    "  --tpm tpm.tsv                   TPM matrix.\n",
    "  --fpkm fpkm.tsv                 FPKM matrix.\n",
    "  --cpm cpm.tsv                   CPM matrix.\n",
    "  --log-expression log.tsv        Already log-transformed expression matrix.\n",
    "  --matrix expression.tsv         Generic matrix when the scale is uncertain.\n",
    "\n",
    "Options:\n",
    "  --matrix-scale auto             Declared scale for --matrix.\n",
    "  --gene-column gene_id           Feature identifier column. Defaults to first non-numeric column.\n",
    "  --normality-max-values 5000     Maximum values sampled for Shapiro-Wilk tests.\n",
    sep = ""
  )
}

args <- parse_args()
if (isTRUE(args[["help"]])) {
  usage()
  quit(status = 0)
}

outdir <- arg_value(args, "outdir", required = TRUE)
gene_column <- arg_value(args, "gene-column", default = NULL)
matrix_scale <- arg_value(args, "matrix-scale", default = "auto")
normality_max_values <- as_integer_arg(args, "normality-max-values", 5000)

ensure_dir(outdir)

inputs <- list(
  list(name = "counts", path = arg_value(args, "counts", default = NULL), declared_scale = "raw_counts"),
  list(name = "tpm", path = arg_value(args, "tpm", default = NULL), declared_scale = "tpm"),
  list(name = "fpkm", path = arg_value(args, "fpkm", default = NULL), declared_scale = "fpkm"),
  list(name = "cpm", path = arg_value(args, "cpm", default = NULL), declared_scale = "cpm"),
  list(name = "log_expression", path = arg_value(args, "log-expression", default = NULL), declared_scale = "log_expression"),
  list(name = "matrix", path = arg_value(args, "matrix", default = NULL), declared_scale = matrix_scale)
)

inputs <- Filter(function(item) !is.null(item$path), inputs)
if (length(inputs) == 0) {
  fail("Provide at least one matrix input")
}

matrices <- list()
assessment_rows <- list()
sample_rows <- list()

for (input in inputs) {
  matrix <- read_feature_matrix(input$path, gene_column, label = paste(input$name, "matrix"))
  matrices[[input$name]] <- matrix
  assessment_rows[[input$name]] <- matrix_distribution_metrics(
    matrix,
    matrix_name = input$name,
    declared_scale = input$declared_scale,
    normality_max_values = normality_max_values
  )
  sample_rows[[input$name]] <- sample_distribution_metrics(
    matrix,
    matrix_name = input$name,
    normality_max_values = normality_max_values
  )
}

assessment <- do.call(rbind, assessment_rows)
sample_assessment <- do.call(rbind, sample_rows)
recommendation <- recommend_bulk_de_method(assessment)

consistency_rows <- list()
if (length(matrices) > 1) {
  matrix_names <- names(matrices)
  pairs <- utils::combn(matrix_names, 2, simplify = FALSE)
  consistency_rows <- lapply(pairs, function(pair) {
    left <- matrices[[pair[[1]]]]
    right <- matrices[[pair[[2]]]]
    data.frame(
      matrix_a = pair[[1]],
      matrix_b = pair[[2]],
      same_samples = identical(colnames(left), colnames(right)),
      same_features = identical(rownames(left), rownames(right)),
      shared_sample_count = length(intersect(colnames(left), colnames(right))),
      shared_feature_count = length(intersect(rownames(left), rownames(right))),
      stringsAsFactors = FALSE
    )
  })
}
consistency <- if (length(consistency_rows) > 0) {
  do.call(rbind, consistency_rows)
} else {
  data.frame(
    matrix_a = character(),
    matrix_b = character(),
    same_samples = logical(),
    same_features = logical(),
    shared_sample_count = integer(),
    shared_feature_count = integer()
  )
}

notes <- c(
  "Differential expression method selection is based on matrix scale first, not on converting normalized values into counts.",
  "When raw or estimated counts and TPM/FPKM/CPM are all available for the same samples, use counts for DESeq2, edgeR, or limma-voom.",
  "Use TPM/FPKM/CPM/log-expression matrices for QC, summaries, visualization, or a documented normalized-expression fallback only when counts cannot be recovered.",
  "Raw counts are expected to be discrete, skewed, zero-inflated, and non-normal; failing a normality test is not a reason to avoid count models.",
  "For normalized-expression fallback, check whether values are already log-transformed. If not, use an explicit log2 transform with a recorded pseudocount.",
  "Shapiro-Wilk tests on expression matrices are descriptive and sample-size sensitive; interpret them with skewness, quantiles, zeros, and matrix scale."
)

write_tsv(assessment, file.path(outdir, "matrix_distribution_assessment.tsv"))
write_tsv(sample_assessment, file.path(outdir, "sample_distribution_assessment.tsv"))
write_tsv(consistency, file.path(outdir, "matrix_consistency.tsv"))
write_tsv(recommendation, file.path(outdir, "method_recommendation.tsv"))
writeLines(notes, file.path(outdir, "diagnostic_notes.txt"))

info("Wrote expression matrix diagnostics to %s", outdir)
