#!/usr/bin/env Rscript

script_args <- commandArgs(trailingOnly = FALSE)
script_file <- sub("^--file=", "", script_args[grep("^--file=", script_args)])
script_file <- if (length(script_file) > 0) normalizePath(script_file[[1]]) else normalizePath(".")
source(file.path(dirname(dirname(script_file)), "lib", "common.R"))

usage <- function() {
  cat(
    "Usage: ora_from_de.R --de-results results.tsv --gmt gene_sets.gmt --outdir outdir [options]\n",
    "\n",
    "Options:\n",
    "  --gene-column feature_id       Gene identifier column. Defaults to first column.\n",
    "  --padj-column auto             Adjusted p-value column, auto-detected when possible.\n",
    "  --pvalue-column auto           Raw p-value column, used only if adjusted p-values are absent.\n",
    "  --logfc-column auto            Log fold-change column, auto-detected when possible.\n",
    "  --fdr 0.05                     Significance threshold.\n",
    "  --logfc-threshold 0            Absolute logFC threshold for selected genes.\n",
    "  --direction all                Gene selection direction: all, up, or down.\n",
    "  --universe genes.tsv           Optional universe gene list; defaults to all DE result genes.\n",
    "  --universe-gene-column gene    Optional gene column for --universe.\n",
    "  --min-set-size 5               Minimum gene set size after intersecting universe.\n",
    "  --max-set-size 500             Maximum gene set size after intersecting universe.\n",
    sep = ""
  )
}

infer_column <- function(data, requested, candidates, label, required = TRUE) {
  if (!is.null(requested) && !identical(requested, "") && !identical(requested, "auto")) {
    require_columns(data, requested, label)
    return(requested)
  }

  found <- candidates[candidates %in% colnames(data)]
  if (length(found) > 0) {
    return(found[[1]])
  }

  if (required) {
    fail("Could not auto-detect %s column. Provide it explicitly.", label)
  }
  NULL
}

args <- parse_args()
if (isTRUE(args[["help"]])) {
  usage()
  quit(status = 0)
}

results_path <- arg_value(args, "de-results", required = TRUE)
gmt_path <- arg_value(args, "gmt", required = TRUE)
outdir <- arg_value(args, "outdir", required = TRUE)
gene_column <- arg_value(args, "gene-column", default = NULL)
padj_column <- arg_value(args, "padj-column", default = "auto")
pvalue_column <- arg_value(args, "pvalue-column", default = "auto")
logfc_column <- arg_value(args, "logfc-column", default = "auto")
direction <- arg_value(args, "direction", default = "all")
universe_path <- arg_value(args, "universe", default = NULL)
universe_gene_column <- arg_value(args, "universe-gene-column", default = NULL)
fdr <- as_number_arg(args, "fdr", 0.05)
logfc_threshold <- as_number_arg(args, "logfc-threshold", 0)
min_set_size <- as_integer_arg(args, "min-set-size", 5)
max_set_size <- as_integer_arg(args, "max-set-size", 500)

if (!direction %in% c("all", "up", "down")) {
  fail("--direction must be all, up, or down")
}
if (fdr <= 0 || fdr >= 1) {
  fail("--fdr must be between 0 and 1")
}
if (min_set_size < 1 || max_set_size < min_set_size) {
  fail("Invalid gene set size bounds")
}

ensure_dir(outdir)

results <- read_delimited(results_path)
genes <- standardize_feature_column(results, gene_column, label = "DE results")
padj_column <- infer_column(results, padj_column, c("padj", "FDR", "adj.P.Val", "qvalue", "q_value"), "adjusted p-value", required = FALSE)
pvalue_column <- infer_column(results, pvalue_column, c("pvalue", "PValue", "P.Value", "p_value", "pval"), "p-value", required = FALSE)
logfc_column <- infer_column(results, logfc_column, c("log2FoldChange", "logFC", "estimate", "log_fold_change"), "logFC", required = FALSE)

if (is.null(padj_column) && is.null(pvalue_column)) {
  fail("No adjusted or raw p-value column is available for selecting genes")
}

score_column <- if (!is.null(padj_column)) padj_column else pvalue_column
pvalues <- suppressWarnings(as.numeric(results[[score_column]]))
if (any(is.na(pvalues))) {
  fail("Selected p-value column contains non-numeric values: %s", score_column)
}

selected <- pvalues <= fdr
if (!is.null(logfc_column)) {
  logfc <- suppressWarnings(as.numeric(results[[logfc_column]]))
  if (any(is.na(logfc))) {
    fail("LogFC column contains non-numeric values: %s", logfc_column)
  }
  if (direction == "up") {
    selected <- selected & logfc >= logfc_threshold
  } else if (direction == "down") {
    selected <- selected & logfc <= -logfc_threshold
  } else if (logfc_threshold > 0) {
    selected <- selected & abs(logfc) >= logfc_threshold
  }
}

selected_genes <- normalize_ids(genes[selected])
if (length(selected_genes) == 0) {
  fail("No genes passed the selected thresholds")
}

universe <- if (!is.null(universe_path)) {
  read_gene_list(universe_path, universe_gene_column)
} else {
  normalize_ids(genes)
}

gene_sets <- read_gmt(gmt_path)
selected_genes <- intersect(selected_genes, universe)
universe_size <- length(universe)
selected_size <- length(selected_genes)

if (selected_size == 0) {
  fail("No selected genes remain after intersecting with the universe")
}

rows <- lapply(gene_sets, function(gene_set) {
  set_genes <- intersect(gene_set$genes, universe)
  set_size <- length(set_genes)
  if (set_size < min_set_size || set_size > max_set_size) {
    return(NULL)
  }

  overlap <- intersect(selected_genes, set_genes)
  overlap_size <- length(overlap)
  pvalue <- stats::phyper(overlap_size - 1, set_size, universe_size - set_size, selected_size, lower.tail = FALSE)
  contingency <- matrix(
    c(
      overlap_size,
      selected_size - overlap_size,
      set_size - overlap_size,
      universe_size - set_size - selected_size + overlap_size
    ),
    nrow = 2
  )
  odds_ratio <- tryCatch(unname(stats::fisher.test(contingency)$estimate), error = function(error) NA_real_)

  data.frame(
    gene_set = gene_set$name,
    description = gene_set$description,
    set_size = set_size,
    selected_size = selected_size,
    overlap_size = overlap_size,
    pvalue = pvalue,
    odds_ratio = odds_ratio,
    overlap_genes = paste(overlap, collapse = ","),
    stringsAsFactors = FALSE
  )
})

enrichment <- do.call(rbind, Filter(Negate(is.null), rows))
if (is.null(enrichment) || nrow(enrichment) == 0) {
  fail("No gene sets remained after universe and size filtering")
}
enrichment$padj <- stats::p.adjust(enrichment$pvalue, method = "BH")
enrichment <- enrichment[order(enrichment$padj, enrichment$pvalue), ]

selected_table <- data.frame(gene_id = selected_genes, stringsAsFactors = FALSE)
parameters <- data.frame(
  parameter = c(
    "score_column",
    "logfc_column",
    "direction",
    "fdr",
    "logfc_threshold",
    "universe_size",
    "selected_size",
    "min_set_size",
    "max_set_size"
  ),
  value = c(
    score_column,
    ifelse(is.null(logfc_column), "", logfc_column),
    direction,
    fdr,
    logfc_threshold,
    universe_size,
    selected_size,
    min_set_size,
    max_set_size
  ),
  stringsAsFactors = FALSE
)

write_tsv(enrichment, file.path(outdir, "ora_results.tsv"))
write_tsv(selected_table, file.path(outdir, "selected_genes.tsv"))
write_tsv(parameters, file.path(outdir, "run_parameters.tsv"))
writeLines(capture.output(sessionInfo()), file.path(outdir, "session_info.txt"))

info("Wrote ORA outputs to %s", outdir)
