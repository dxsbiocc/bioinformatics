#!/usr/bin/env Rscript

script_args <- commandArgs(trailingOnly = FALSE)
script_file <- sub("^--file=", "", script_args[grep("^--file=", script_args)])
script_file <- if (length(script_file) > 0) normalizePath(script_file[[1]]) else normalizePath(".")
source(file.path(dirname(dirname(script_file)), "lib", "common.R"))

usage <- function() {
  cat(
    "Usage: preranked_gsea.R --ranked-table results.tsv --gmt gene_sets.gmt --outdir outdir [options]\n",
    "\n",
    "Options:\n",
    "  --gene-column feature_id       Gene identifier column. Defaults to first column.\n",
    "  --rank-column auto             Ranking column; auto-detects stat, t, Wald, or logFC-like columns.\n",
    "  --min-set-size 10              Minimum gene set size after intersecting ranked genes.\n",
    "  --max-set-size 500             Maximum gene set size after intersecting ranked genes.\n",
    "  --permutations 1000            Gene-label permutations for approximate p-values.\n",
    "  --seed 1                       Random seed.\n",
    sep = ""
  )
}

infer_rank_column <- function(data, requested) {
  if (!is.null(requested) && !identical(requested, "") && !identical(requested, "auto")) {
    require_columns(data, requested, "Ranked table")
    return(requested)
  }

  candidates <- c("stat", "t", "WaldStatistic", "score", "log2FoldChange", "logFC")
  found <- candidates[candidates %in% colnames(data)]
  if (length(found) == 0) {
    fail("Could not auto-detect rank column. Provide --rank-column explicitly.")
  }
  found[[1]]
}

calc_es <- function(ranked_genes, ranks, hit_genes, exponent = 1) {
  hits <- ranked_genes %in% hit_genes
  hit_count <- sum(hits)
  miss_count <- length(hits) - hit_count
  if (hit_count == 0 || miss_count == 0) {
    return(list(es = NA_real_, leading_edge = character()))
  }

  hit_weights <- abs(ranks)^exponent
  hit_weights[!hits] <- 0
  hit_norm <- sum(hit_weights)
  running <- cumsum(ifelse(hits, hit_weights / hit_norm, -1 / miss_count))
  max_i <- which.max(running)
  min_i <- which.min(running)

  if (abs(running[[max_i]]) >= abs(running[[min_i]])) {
    es <- running[[max_i]]
    leading_edge <- ranked_genes[seq_len(max_i)][hits[seq_len(max_i)]]
  } else {
    es <- running[[min_i]]
    leading_edge <- ranked_genes[seq(from = min_i, to = length(ranked_genes))][hits[seq(from = min_i, to = length(ranked_genes))]]
  }

  list(es = es, leading_edge = leading_edge)
}

args <- parse_args()
if (isTRUE(args[["help"]])) {
  usage()
  quit(status = 0)
}

ranked_path <- arg_value(args, "ranked-table", required = TRUE)
gmt_path <- arg_value(args, "gmt", required = TRUE)
outdir <- arg_value(args, "outdir", required = TRUE)
gene_column <- arg_value(args, "gene-column", default = NULL)
rank_column <- arg_value(args, "rank-column", default = "auto")
min_set_size <- as_integer_arg(args, "min-set-size", 10)
max_set_size <- as_integer_arg(args, "max-set-size", 500)
permutations <- as_integer_arg(args, "permutations", 1000)
seed <- as_integer_arg(args, "seed", 1)

if (min_set_size < 1 || max_set_size < min_set_size) {
  fail("Invalid gene set size bounds")
}
if (permutations < 0) {
  fail("--permutations must be non-negative")
}

ensure_dir(outdir)
set.seed(seed)

ranked <- read_delimited(ranked_path)
genes <- standardize_feature_column(ranked, gene_column, label = "Ranked table")
rank_column <- infer_rank_column(ranked, rank_column)
ranks <- suppressWarnings(as.numeric(ranked[[rank_column]]))
if (any(!is.finite(ranks))) {
  fail("Rank column contains missing or non-finite values: %s", rank_column)
}

ranked_data <- data.frame(gene_id = genes, rank = ranks, stringsAsFactors = FALSE)
ranked_data <- ranked_data[!is.na(ranked_data$gene_id) & ranked_data$gene_id != "", , drop = FALSE]
ranked_data <- ranked_data[order(abs(ranked_data$rank), decreasing = TRUE), ]
ranked_data <- ranked_data[!duplicated(ranked_data$gene_id), , drop = FALSE]
ranked_data <- ranked_data[order(ranked_data$rank, decreasing = TRUE), ]

ranked_genes <- ranked_data$gene_id
ranks <- ranked_data$rank
gene_sets <- read_gmt(gmt_path)

rows <- list()
leading_rows <- list()
for (gene_set in gene_sets) {
  set_genes <- intersect(gene_set$genes, ranked_genes)
  set_size <- length(set_genes)
  if (set_size < min_set_size || set_size > max_set_size) {
    next
  }

  observed <- calc_es(ranked_genes, ranks, set_genes)
  if (!is.finite(observed$es)) {
    next
  }

  null_es <- numeric(permutations)
  if (permutations > 0) {
    for (i in seq_len(permutations)) {
      sampled_genes <- sample(ranked_genes, set_size)
      null_es[[i]] <- calc_es(ranked_genes, ranks, sampled_genes)$es
    }
    pvalue <- (sum(abs(null_es) >= abs(observed$es), na.rm = TRUE) + 1) / (permutations + 1)
    same_sign <- null_es[sign(null_es) == sign(observed$es)]
    nes_denominator <- mean(abs(same_sign), na.rm = TRUE)
    normalized_es <- if (is.finite(nes_denominator) && nes_denominator > 0) observed$es / nes_denominator else NA_real_
  } else {
    pvalue <- NA_real_
    normalized_es <- NA_real_
  }

  rows[[length(rows) + 1]] <- data.frame(
    gene_set = gene_set$name,
    description = gene_set$description,
    set_size = set_size,
    enrichment_score = observed$es,
    normalized_enrichment_score = normalized_es,
    pvalue = pvalue,
    leading_edge_size = length(observed$leading_edge),
    leading_edge_genes = paste(observed$leading_edge, collapse = ","),
    stringsAsFactors = FALSE
  )

  if (length(observed$leading_edge) > 0) {
    leading_rows[[length(leading_rows) + 1]] <- data.frame(
      gene_set = gene_set$name,
      gene_id = observed$leading_edge,
      stringsAsFactors = FALSE
    )
  }
}

gsea <- if (length(rows) > 0) do.call(rbind, rows) else NULL
if (is.null(gsea) || nrow(gsea) == 0) {
  fail("No gene sets remained after ranked-gene intersection and size filtering")
}
gsea$padj <- stats::p.adjust(gsea$pvalue, method = "BH")
gsea <- gsea[order(gsea$padj, gsea$pvalue), ]

leading_edge <- if (length(leading_rows) > 0) {
  do.call(rbind, leading_rows)
} else {
  data.frame(gene_set = character(), gene_id = character())
}

parameters <- data.frame(
  parameter = c("rank_column", "ranked_genes", "min_set_size", "max_set_size", "permutations", "seed"),
  value = c(rank_column, length(ranked_genes), min_set_size, max_set_size, permutations, seed),
  stringsAsFactors = FALSE
)

notes <- c(
  "This is a lightweight preranked GSEA implementation using gene-label permutations.",
  "For publication-critical analyses, prefer a maintained GSEA implementation such as fgsea or clusterProfiler when available.",
  "Use signed statistics or signed log-fold-change ranks; do not rank by adjusted p-value alone."
)

write_tsv(gsea, file.path(outdir, "preranked_gsea_results.tsv"))
write_tsv(leading_edge, file.path(outdir, "leading_edge_genes.tsv"))
write_tsv(parameters, file.path(outdir, "run_parameters.tsv"))
writeLines(notes, file.path(outdir, "method_notes.txt"))
writeLines(capture.output(sessionInfo()), file.path(outdir, "session_info.txt"))

info("Wrote preranked GSEA outputs to %s", outdir)
