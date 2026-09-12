#!/usr/bin/env Rscript

# Template-ID: boxplot-differential-bg
#
# Purpose:
#   Draw grouped boxplots with a pale category background and a
#   within-category significance label.
#
# Inputs:
#   A table with one row per observation. Default example:
#     - gene: category label
#     - exprs: numeric value
#     - group: comparison group
#
# Output:
#   A PDF, PNG, or SVG boxplot with background panels.
#
# Dependencies:
#   ggplot2, readr, ggpubr, ggprism
#
# Example:
#   Rscript plot.R example.tsv output.pdf
#
# Agent adaptation:
#   For a new table, edit only CONFIG (column names and labels).
#   Edit DATA PREPARATION to change category order or background
#   rectangles.
#   Edit PLOT only when the chart geometry or styling must change.
#
# Scientific assumptions:
#   Each row is one observation of a numeric value in a category
#   and group.
#   Background rectangles are a display aid, not additional data.
#   Significance labels compare groups within each category.

local({
    file_arg <- grep("^--file=", commandArgs(FALSE), value = TRUE)
    if (!length(file_arg)) {
        stop("Run this file with Rscript.", call. = FALSE)
    }
    dir <- dirname(normalizePath(sub("^--file=", "", file_arg[[1]])))
    for (i in seq_len(8)) {
        candidate <- file.path(dir, "lib", "common.R")
        if (file.exists(candidate)) {
            source(normalizePath(candidate), chdir = FALSE)
            return(invisible())
        }
        parent <- dirname(dir)
        if (identical(parent, dir)) break
        dir <- parent
    }
    stop("Cannot find scripts/lib/common.R", call. = FALSE)
})

io <- parse_io_args()

# -----------------------------------------------------------------------------
# CONFIG  (edit this block for a new dataset)
# -----------------------------------------------------------------------------
config <- list(
    columns = list(
        x = "gene",
        y = "exprs",
        group = "group"
    ),
    labels = list(
        title = "",
        x = "",
        y = "Gene expression level"
    )
)

load_packages(c("ggplot2", "readr", "ggpubr", "ggprism"))

# -----------------------------------------------------------------------------
# DATA PREPARATION
# -----------------------------------------------------------------------------
df <- read_table_auto(io$input)
require_columns(df, config$columns)
x_col <- config$columns$x
y_col <- config$columns$y
group_col <- config$columns$group

df[[x_col]] <- factor(df[[x_col]], levels = unique(df[[x_col]]))
df[[group_col]] <- factor(df[[group_col]], levels = unique(df[[group_col]]))
df[[y_col]] <- as.numeric(df[[y_col]])

x_unique <- levels(df[[x_col]])
fill_data <- data.frame(
    xmin = seq_along(x_unique) - 0.5,
    xmax = seq_along(x_unique) + 0.5,
    ymin = -Inf,
    ymax = Inf
)
fill_data[[x_col]] <- x_unique

# -----------------------------------------------------------------------------
# PLOT
# -----------------------------------------------------------------------------
colour_values <- c(
    "#8F499C", "#4185BE", "#6DC067", "#F6DB35", "#F78822"
)

p <- ggplot(df, aes(
    x = .data[[x_col]],
    y = .data[[y_col]],
    colour = .data[[group_col]]
)) +
    geom_rect(
        data = fill_data,
        aes(
            xmin = xmin,
            xmax = xmax,
            ymin = ymin,
            ymax = ymax,
            fill = .data[[x_col]]
        ),
        linetype = "dashed",
        colour = "#caccd1",
        alpha = 0.2,
        show.legend = FALSE,
        inherit.aes = FALSE
    ) +
    geom_boxplot(outlier.shape = NA) +
    geom_point(
        position = position_jitterdodge(
            jitter.width = 0.15,
            dodge.width = 0.7
        ),
        size = 1,
        alpha = 0.6
    ) +
    stat_compare_means(
        aes(group = .data[[group_col]]),
        label = "p.signif",
        hide.ns = TRUE,
        show.legend = FALSE
    ) +
    scale_colour_manual(values = colour_values) +
    scale_fill_manual(values = colour_values) +
    scale_y_continuous(expand = c(0, 0)) +
    scale_x_discrete(expand = c(0, 0)) +
    guides(x = guide_prism_bracket()) +
    labs(
        title = config$labels$title,
        x = config$labels$x,
        y = config$labels$y
    ) +
    theme_prism() +
    theme(
        plot.background = element_blank(),
        axis.text = element_text(face = "bold", size = 8),
        axis.title.y = element_text(size = 10, face = "bold"),
        strip.text = element_text(face = "bold"),
        strip.background = element_rect(fill = "#6dc067"),
        panel.grid = element_blank(),
        panel.background = element_blank()
    )

# -----------------------------------------------------------------------------
# SAVE
# -----------------------------------------------------------------------------
save_ggplot(p, io$output)
