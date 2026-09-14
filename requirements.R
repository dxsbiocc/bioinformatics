#!/usr/bin/env Rscript
# Dependency declaration and installer for the R plotting scripts under
# skills/omics-visualization/ and skills/transcriptomics-analysis/.
#
# The Python MCP servers under mcp/ have no dependencies (see pyproject.toml);
# this file exists because the visualization/analysis skills shell out to R
# scripts that do. Run it once per environment:
#
#   Rscript requirements.R
#
# It is idempotent - already-installed packages are skipped.

cran_packages <- c(
  "ggplot2", "patchwork", "jsonlite", "yaml", "readr", "circlize",
  "ggprism", "ggnewscale", "ggvenn", "geomtextpath", "ggforce", "ggpubr",
  "gghalves", "quantreg", "ggbeeswarm", "ggrepel", "ggsignif", "ggh4x",
  "ggridges", "gtable", "ggtern", "scales", "sf", "hexbin", "ggraph",
  "tidygraph", "survival", "survminer", "ggExtra", "aplot", "cli",
  "rsvg", "remotes", "BiocManager"
)

# Bioconductor-only packages (installed via BiocManager, which also handles
# CRAN packages but is only strictly required for these).
bioc_packages <- c(
  "DESeq2", "edgeR", "limma", "ComplexHeatmap", "SummarizedExperiment"
)

# Not on CRAN or Bioconductor; installed from their GitHub source.
github_packages <- list(
  ggideogram = "dxsbiocc/ggideogram",
  gground    = "dxsbiocc/gground",
  ggsvg      = "coolbutuseless/ggsvg",
  ggsankey   = "davidsjoberg/ggsankey",
  linkET     = "Hy4m/linkET",
  ggcor      = "houyunhuang/ggcor",
  ggmagnify  = "hughjonesd/ggmagnify",
  waffle     = "hrbrmstr/waffle" # removed from CRAN 2025-09-09
)

installed <- function(pkg) requireNamespace(pkg, quietly = TRUE)

missing_cran <- Filter(Negate(installed), cran_packages)
if (length(missing_cran) > 0) {
  install.packages(missing_cran, repos = "https://cloud.r-project.org")
}

if (!installed("BiocManager")) {
  install.packages("BiocManager", repos = "https://cloud.r-project.org")
}
missing_bioc <- Filter(Negate(installed), bioc_packages)
if (length(missing_bioc) > 0) {
  BiocManager::install(missing_bioc, update = FALSE, ask = FALSE)
}

for (pkg in names(github_packages)) {
  if (!installed(pkg)) {
    remotes::install_github(github_packages[[pkg]])
  }
}

cat("All R dependencies for the omics-visualization and transcriptomics-analysis skills are installed.\n")
