#!/usr/bin/env Rscript

# Template-ID: heatmap-corr-grouped
#
# Purpose:
#   Draw a grouped lower-triangle correlation heatmap: variables are
#   ordered by a supplied group map, blocks are separated by gaps,
#   cell fill is a supplied rho, and stars mark supplied p cuts.
#   Group braces sit on the right.
#
# Inputs:
#   1) Long correlation table (one row per pair):
#        x, y, rho, p
#   2) Variable-to-group map:
#        var, group
#
# Output:
#   A PDF, PNG, or SVG grouped correlation heatmap.
#
# Dependencies:
#   ggplot2, readr, ggprism, scales
#
# Example:
#   Rscript plot.R example.tsv groups.tsv output.pdf
#
# Agent adaptation:
#   Edit only CONFIG (columns, p_stars, gap, palette, labels).
#   Upper vs lower display, or brace vs strip labels, is CONFIG —
#   not a new id. Do not compute Spearman here; supply rho and p.
#   An ungrouped square matrix is heatmap-signif; a two-set X-vs-Y
#   grid from sample rows is heatmap-two.
#
# Scientific assumptions:
#   rho and p are supplied. Stars are display cuts of p, not an
#   FDR adjustment performed in this script.

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

io <- parse_io_args(
    n_input = 2L,
    input_names = c("corr", "groups")
)

# -----------------------------------------------------------------------------
# CONFIG  (edit this block for a new dataset)
# -----------------------------------------------------------------------------
config <- list(
    columns = list(
        x = "x",
        y = "y",
        value = "rho",
        p = "p",
        var = "var",
        group = "group"
    ),
    p_stars = c(
        "***" = 1e-3,
        "**" = 1e-2,
        "*" = 5e-2
    ),
    triangle = "lower",
    gap = 0.55,
    palettes = list(
        fill = "Diverging.RdBu"
    ),
    fill_limits = c(-1, 1),
    labels = list(
        title = "",
        fill = "Correlation",
        x_size = 10,
        y_size = 10
    ),
    size = list(
        width = 8.6,
        height = 7.8
    )
)

load_packages(c("ggplot2", "readr", "ggprism", "scales"))

# -----------------------------------------------------------------------------
# DATA PREPARATION
# -----------------------------------------------------------------------------
corr <- read_table_auto(io$input[[1]])
grp <- read_table_auto(io$input[[2]])

cx <- config$columns$x
cy <- config$columns$y
cv <- config$columns$value
cp <- config$columns$p
gv <- config$columns$var
gg <- config$columns$group

require_columns(corr, list(x = cx, y = cy, value = cv, p = cp))
require_columns(grp, list(var = gv, group = gg))

corr[[cx]] <- as.character(corr[[cx]])
corr[[cy]] <- as.character(corr[[cy]])
corr[[cv]] <- as.numeric(corr[[cv]])
corr[[cp]] <- as.numeric(corr[[cp]])
grp[[gv]] <- as.character(grp[[gv]])
grp[[gg]] <- as.character(grp[[gg]])

if (anyDuplicated(grp[[gv]])) {
    stop("groups table must have unique var rows.", call. = FALSE)
}

# Preserve file order of groups / vars.
grp[[gg]] <- factor(grp[[gg]], levels = unique(grp[[gg]]))
grp <- grp[order(grp[[gg]]), , drop = FALSE]
vars <- grp[[gv]]
g_levels <- levels(grp[[gg]])

pos <- data.frame(
    var = vars,
    group = as.character(grp[[gg]]),
    stringsAsFactors = FALSE
)
# Numeric positions with gaps between groups.
gap <- as.numeric(config$gap)
if (!is.finite(gap) || gap < 0) gap <- 0.55
cursor <- 1
pos$i <- NA_real_
for (g in g_levels) {
    hit <- which(pos$group == g)
    pos$i[hit] <- cursor + seq_along(hit) - 1
    cursor <- cursor + length(hit) + gap
}

map_i <- setNames(pos$i, pos$var)
map_g <- setNames(pos$group, pos$var)

ok <- corr[[cx]] %in% vars & corr[[cy]] %in% vars &
    is.finite(corr[[cv]]) & is.finite(corr[[cp]]) & corr[[cp]] >= 0
if (any(!ok)) {
    message("Dropped ", sum(!ok), " corr row(s) outside groups or invalid.")
    corr <- corr[ok, , drop = FALSE]
}
if (!nrow(corr)) stop("No correlation rows left to plot.", call. = FALSE)

corr$ix <- unname(map_i[corr[[cx]]])
corr$iy <- unname(map_i[corr[[cy]]])
corr$gx <- unname(map_g[corr[[cx]]])
corr$gy <- unname(map_g[corr[[cy]]])

tri <- tolower(as.character(config$triangle[[1]]))
if (!tri %in% c("lower", "upper", "full")) {
    stop("config$triangle must be lower, upper, or full.", call. = FALSE)
}
# Intra-group: triangular. Inter-group: full rectangle (matches
# the grouped-block reference layout).
same_g <- corr$gx == corr$gy
if (identical(tri, "lower")) {
    keep <- (!same_g) | (corr$iy <= corr$ix)
} else if (identical(tri, "upper")) {
    keep <- (!same_g) | (corr$iy >= corr$ix)
} else {
    keep <- rep(TRUE, nrow(corr))
}
corr <- corr[keep, , drop = FALSE]

star_cuts <- sort(unlist(config$p_stars), decreasing = TRUE)
star_lab <- function(p) {
    out <- character(length(p))
    for (i in seq_along(star_cuts)) {
        hit <- is.finite(p) & p < star_cuts[[i]]
        out[hit] <- names(star_cuts)[[i]]
    }
    out
}
corr$star <- star_lab(corr[[cp]])
# No stars on diagonal self-correlations.
corr$star[corr[[cx]] == corr[[cy]]] <- ""

fill_lim <- as.numeric(config$fill_limits)
if (length(fill_lim) != 2L || any(!is.finite(fill_lim))) {
    fill_lim <- c(-1, 1)
}
fill_cols <- rev(palette_colors(config$palettes$fill))
outline <- "grey70"

# Brace annotation centres per group (right of matrix).
brace <- aggregate(
    i ~ group,
    data = pos,
    FUN = function(z) c(min = min(z), max = max(z), mid = mean(z))
)
brace_df <- data.frame(
    group = brace$group,
    ymin = brace$i[, "min"] - 0.35,
    ymax = brace$i[, "max"] + 0.35,
    y = brace$i[, "mid"],
    x = max(pos$i) + 1.25,
    stringsAsFactors = FALSE
)

# -----------------------------------------------------------------------------
# PLOT
# -----------------------------------------------------------------------------
p <- ggplot(corr, aes(x = ix, y = iy)) +
    geom_tile(
        aes(fill = .data[[cv]]),
        width = 0.92,
        height = 0.92,
        colour = "white",
        linewidth = 0.35
    ) +
    geom_text(
        aes(label = star),
        size = 3.2,
        colour = "grey10",
        na.rm = TRUE
    ) +
    scale_fill_gradientn(
        name = config$labels$fill,
        colours = fill_cols,
        limits = fill_lim,
        oob = scales::squish
    ) +
    scale_x_continuous(
        breaks = pos$i,
        labels = pos$var,
        expand = expansion(add = 0.6)
    ) +
    scale_y_continuous(
        breaks = pos$i,
        labels = pos$var,
        expand = expansion(add = 0.6)
    ) +
    coord_fixed(clip = "off") +
    # Right-hand group braces.
    geom_segment(
        data = brace_df,
        aes(x = x, xend = x, y = ymin, yend = ymax),
        inherit.aes = FALSE,
        colour = "grey20",
        linewidth = 0.55
    ) +
    geom_segment(
        data = brace_df,
        aes(x = x - 0.18, xend = x, y = ymin, yend = ymin),
        inherit.aes = FALSE,
        colour = "grey20",
        linewidth = 0.55
    ) +
    geom_segment(
        data = brace_df,
        aes(x = x - 0.18, xend = x, y = ymax, yend = ymax),
        inherit.aes = FALSE,
        colour = "grey20",
        linewidth = 0.55
    ) +
    geom_text(
        data = brace_df,
        aes(x = x + 0.35, y = y, label = group),
        inherit.aes = FALSE,
        angle = 270,
        hjust = 0.5,
        vjust = 0.5,
        size = 3.6,
        fontface = "bold",
        colour = "grey15"
    ) +
    labs(title = config$labels$title, x = NULL, y = NULL) +
    theme_prism(base_size = 12) +
    theme(
        panel.grid = element_blank(),
        plot.background = element_blank(),
        panel.background = element_blank(),
        legend.background = element_blank(),
        axis.line = element_blank(),
        axis.ticks.length = unit(0.15, "cm"),
        axis.text.x = element_text(
            angle = 90, hjust = 1, vjust = 0.5,
            size = config$labels$x_size
        ),
        axis.text.y = element_text(size = config$labels$y_size),
        plot.margin = margin(8, 28, 8, 8)
    )

# -----------------------------------------------------------------------------
# SAVE
# -----------------------------------------------------------------------------
save_ggplot(
    p, io$output,
    width = config$size$width,
    height = config$size$height
)
