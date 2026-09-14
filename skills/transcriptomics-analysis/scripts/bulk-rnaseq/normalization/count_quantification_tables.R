#!/usr/bin/env Rscript

script_args <- commandArgs(trailingOnly = FALSE)
script_file <- sub("^--file=", "", script_args[grep("^--file=", script_args)])
script_file <- if (length(script_file) > 0) normalizePath(script_file[[1]]) else normalizePath(".")
source(file.path(dirname(dirname(script_file)), "lib", "common.R"))

usage <- function() {
  cat(
    "Usage: count_quantification_tables.R --counts counts.tsv --outdir outdir [options]\n",
    "\n",
    "Options:\n",
    "  --gene-column gene_id              Feature identifier column. Defaults to first non-numeric column.\n",
    "  --lengths gene_lengths.tsv         Optional feature length table for TPM and FPKM.\n",
    "  --length-feature-column gene_id    Feature identifier column in length table.\n",
    "  --length-column length             Feature length column.\n",
    "  --length-unit bp                   Length unit: bp or kb.\n",
    sep = ""
  )
}

args <- parse_args()
if (isTRUE(args[["help"]])) {
  usage()
  quit(status = 0)
}

counts_path <- arg_value(args, "counts", required = TRUE)
gene_column <- arg_value(args, "gene-column", default = NULL)
outdir <- arg_value(args, "outdir", required = TRUE)
lengths_path <- arg_value(args, "lengths", default = NULL)
length_feature_column <- arg_value(args, "length-feature-column", default = "gene_id")
length_column <- arg_value(args, "length-column", default = "length")
length_unit <- arg_value(args, "length-unit", default = "bp")

ensure_dir(outdir)

counts <- read_counts(counts_path, gene_column)
validate_nonnegative_counts(counts)

write_matrix_with_id(cpm_matrix(counts), file.path(outdir, "cpm.tsv"))
write_matrix_with_id(log_cpm(counts), file.path(outdir, "log_cpm.tsv"))

notes <- c(
  "Generated CPM and log-CPM from the supplied count matrix.",
  "Counts can be normalized forward to CPM/log-CPM, and to TPM/FPKM when feature lengths are available.",
  "TPM, FPKM, CPM, VST, rlog, or log-normalized matrices cannot be reliably converted back into raw counts for count-model differential expression.",
  "Do not multiply TPM/FPKM by library size and round values for DESeq2, edgeR, or limma-voom."
)

if (!is.null(lengths_path)) {
  feature_lengths <- read_feature_lengths(
    lengths_path,
    feature_column = length_feature_column,
    length_column = length_column,
    length_unit = length_unit
  )
  write_matrix_with_id(length_scaled_matrix(counts, feature_lengths, scale = "tpm"), file.path(outdir, "tpm.tsv"))
  write_matrix_with_id(length_scaled_matrix(counts, feature_lengths, scale = "fpkm"), file.path(outdir, "fpkm.tsv"))
  notes <- c(notes, "Generated TPM and FPKM using the provided feature lengths.")
} else {
  notes <- c(notes, "Skipped TPM and FPKM because no feature length table was supplied.")
}

writeLines(notes, file.path(outdir, "conversion_notes.txt"))

info("Wrote count-derived quantification tables to %s", outdir)
