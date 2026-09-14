fail <- function(..., call. = FALSE) {
  stop(sprintf(...), call. = call.)
}

info <- function(...) {
  message(sprintf(...))
}

parse_args <- function(argv = commandArgs(trailingOnly = TRUE)) {
  args <- list()
  i <- 1

  while (i <= length(argv)) {
    token <- argv[[i]]
    if (!startsWith(token, "--")) {
      fail("Unexpected positional argument: %s", token)
    }

    item <- substring(token, 3)
    if (grepl("=", item, fixed = TRUE)) {
      parts <- strsplit(item, "=", fixed = TRUE)[[1]]
      key <- parts[[1]]
      value <- paste(parts[-1], collapse = "=")
      args[[key]] <- value
      i <- i + 1
    } else if (i == length(argv) || startsWith(argv[[i + 1]], "--")) {
      args[[item]] <- TRUE
      i <- i + 1
    } else {
      args[[item]] <- argv[[i + 1]]
      i <- i + 2
    }
  }

  args
}

arg_value <- function(args, name, default = NULL, required = FALSE) {
  value <- args[[name]]
  if (is.null(value) || identical(value, "")) {
    if (required) {
      fail("Missing required argument --%s", name)
    }
    return(default)
  }
  value
}

as_number_arg <- function(args, name, default) {
  value <- arg_value(args, name, default = as.character(default))
  parsed <- suppressWarnings(as.numeric(value))
  if (is.na(parsed)) {
    fail("--%s must be numeric, got: %s", name, value)
  }
  parsed
}

as_integer_arg <- function(args, name, default) {
  value <- as_number_arg(args, name, default)
  if (value != as.integer(value)) {
    fail("--%s must be an integer, got: %s", name, value)
  }
  as.integer(value)
}

split_csv_arg <- function(args, name) {
  value <- arg_value(args, name, default = "")
  if (identical(value, "")) {
    return(character())
  }
  trimws(strsplit(value, ",", fixed = TRUE)[[1]])
}

normalize_ids <- function(ids) {
  unique(as.character(ids[!is.na(ids) & ids != ""]))
}

ensure_dir <- function(path) {
  if (!dir.exists(path)) {
    dir.create(path, recursive = TRUE, showWarnings = FALSE)
  }
  if (!dir.exists(path)) {
    fail("Could not create output directory: %s", path)
  }
}

read_delimited <- function(path) {
  if (!file.exists(path)) {
    fail("Input file does not exist: %s", path)
  }

  ext <- tolower(tools::file_ext(path))
  sep <- if (ext %in% c("csv")) "," else "\t"

  read.table(
    path,
    sep = sep,
    header = TRUE,
    quote = "\"",
    comment.char = "",
    check.names = FALSE,
    stringsAsFactors = FALSE
  )
}

read_gene_list <- function(path, gene_column = NULL) {
  data <- read_delimited(path)
  if (!is.null(gene_column) && !identical(gene_column, "")) {
    require_columns(data, gene_column, "Gene list")
    return(normalize_ids(data[[gene_column]]))
  }
  normalize_ids(data[[1]])
}

read_gmt <- function(path) {
  if (!file.exists(path)) {
    fail("GMT file does not exist: %s", path)
  }

  lines <- readLines(path, warn = FALSE)
  lines <- lines[nzchar(lines)]
  if (length(lines) == 0) {
    fail("GMT file is empty: %s", path)
  }

  sets <- lapply(lines, function(line) {
    parts <- strsplit(line, "\t", fixed = TRUE)[[1]]
    if (length(parts) < 3) {
      fail("Invalid GMT line for gene set %s", parts[[1]])
    }
    list(
      name = parts[[1]],
      description = parts[[2]],
      genes = normalize_ids(parts[-c(1, 2)])
    )
  })

  names(sets) <- vapply(sets, function(item) item$name, character(1))
  sets
}

require_columns <- function(data, columns, label) {
  missing <- setdiff(columns, colnames(data))
  if (length(missing) > 0) {
    fail("%s is missing required column(s): %s", label, paste(missing, collapse = ", "))
  }
}

read_feature_matrix <- function(path, gene_column = NULL, label = "Expression matrix") {
  data <- read_delimited(path)
  if (ncol(data) < 2) {
    fail("%s must contain a feature column and at least one sample column", label)
  }

  if (!is.null(gene_column) && !identical(gene_column, "")) {
    require_columns(data, gene_column, label)
    feature_id <- as.character(data[[gene_column]])
    data[[gene_column]] <- NULL
  } else {
    first_column <- data[[1]]
    numeric_first <- !any(is.na(suppressWarnings(as.numeric(first_column))))
    if (numeric_first) {
      fail("Could not infer feature column. Provide --gene-column explicitly.")
    }
    feature_id <- as.character(first_column)
    data <- data[-1]
  }

  if (any(is.na(feature_id)) || any(feature_id == "")) {
    fail("Feature identifiers must be non-empty")
  }
  if (anyDuplicated(feature_id)) {
    duplicated_ids <- unique(feature_id[duplicated(feature_id)])
    fail("Feature identifiers must be unique. Examples: %s", paste(head(duplicated_ids, 5), collapse = ", "))
  }
  if (anyDuplicated(colnames(data))) {
    fail("Sample columns in %s must be unique", label)
  }

  numeric_data <- lapply(data, function(column) suppressWarnings(as.numeric(column)))
  bad_columns <- names(numeric_data)[vapply(numeric_data, function(column) any(is.na(column)), logical(1))]
  if (length(bad_columns) > 0) {
    fail("%s contains non-numeric values in sample column(s): %s", label, paste(bad_columns, collapse = ", "))
  }

  matrix <- as.matrix(as.data.frame(numeric_data, check.names = FALSE))
  rownames(matrix) <- feature_id
  matrix
}

read_counts <- function(path, gene_column = NULL) {
  read_feature_matrix(path, gene_column, label = "Count matrix")
}

read_metadata <- function(path, sample_column) {
  metadata <- read_delimited(path)
  require_columns(metadata, sample_column, "Metadata")
  if (anyDuplicated(colnames(metadata))) {
    fail("Metadata columns must be unique")
  }

  sample_id <- as.character(metadata[[sample_column]])
  if (any(is.na(sample_id)) || any(sample_id == "")) {
    fail("Sample identifiers in metadata column %s must be non-empty", sample_column)
  }
  if (anyDuplicated(sample_id)) {
    duplicated_ids <- unique(sample_id[duplicated(sample_id)])
    fail("Sample identifiers must be unique. Examples: %s", paste(head(duplicated_ids, 5), collapse = ", "))
  }

  rownames(metadata) <- sample_id
  metadata
}

align_counts_metadata <- function(counts, metadata) {
  missing_metadata <- setdiff(colnames(counts), rownames(metadata))
  if (length(missing_metadata) > 0) {
    fail("Metadata is missing sample(s) from the count matrix: %s", paste(missing_metadata, collapse = ", "))
  }

  extra_metadata <- setdiff(rownames(metadata), colnames(counts))
  if (length(extra_metadata) > 0) {
    info("Ignoring metadata row(s) not present in the count matrix: %s", paste(extra_metadata, collapse = ", "))
  }

  metadata[colnames(counts), , drop = FALSE]
}

validate_nonnegative_counts <- function(counts, require_integer = FALSE) {
  if (any(!is.finite(counts))) {
    fail("Count matrix contains non-finite values")
  }
  if (any(counts < 0)) {
    fail("Count matrix contains negative values")
  }
  if (require_integer && any(abs(counts - round(counts)) > sqrt(.Machine$double.eps))) {
    fail("This analysis requires integer-like raw counts")
  }
}

validate_nonnegative_matrix <- function(matrix, label = "Expression matrix") {
  if (any(!is.finite(matrix))) {
    fail("%s contains non-finite values", label)
  }
  if (any(matrix < 0)) {
    fail("%s contains negative values", label)
  }
}

finite_values <- function(matrix) {
  values <- as.numeric(matrix)
  values[is.finite(values)]
}

sample_vector <- function(values, max_values = 5000) {
  values <- values[is.finite(values)]
  if (length(values) <= max_values) {
    return(values)
  }
  index <- unique(round(seq(1, length(values), length.out = max_values)))
  values[index]
}

fraction_integer_like <- function(values) {
  values <- values[is.finite(values)]
  if (length(values) == 0) {
    return(NA_real_)
  }
  mean(abs(values - round(values)) <= sqrt(.Machine$double.eps))
}

safe_shapiro_p <- function(values, max_values = 5000) {
  values <- sample_vector(values, max_values)
  if (length(values) < 3 || length(unique(values)) < 3) {
    return(NA_real_)
  }
  tryCatch(stats::shapiro.test(values)$p.value, error = function(error) NA_real_)
}

safe_skewness <- function(values) {
  values <- values[is.finite(values)]
  if (length(values) < 3) {
    return(NA_real_)
  }
  centered <- values - mean(values)
  scale <- stats::sd(values)
  if (!is.finite(scale) || scale == 0) {
    return(NA_real_)
  }
  mean(centered^3) / scale^3
}

safe_excess_kurtosis <- function(values) {
  values <- values[is.finite(values)]
  if (length(values) < 4) {
    return(NA_real_)
  }
  centered <- values - mean(values)
  scale <- stats::sd(values)
  if (!is.finite(scale) || scale == 0) {
    return(NA_real_)
  }
  mean(centered^4) / scale^4 - 3
}

safe_qq_correlation <- function(values, max_values = 5000) {
  values <- sort(sample_vector(values, max_values))
  if (length(values) < 3 || stats::sd(values) == 0) {
    return(NA_real_)
  }
  theoretical <- stats::qnorm(stats::ppoints(length(values)), mean = mean(values), sd = stats::sd(values))
  suppressWarnings(stats::cor(values, theoretical))
}

near_one_million_fraction <- function(column_sums, tolerance = 0.05) {
  if (length(column_sums) == 0) {
    return(NA_real_)
  }
  mean(abs(column_sums - 1e6) / 1e6 <= tolerance)
}

infer_bulk_matrix_scale <- function(matrix, declared_scale = "auto") {
  declared_scale <- tolower(gsub("-", "_", declared_scale))

  values <- finite_values(matrix)
  if (length(values) == 0) {
    return("unknown")
  }

  negative_fraction <- mean(values < 0)
  zero_fraction <- mean(values == 0)
  integer_fraction <- fraction_integer_like(values)
  maximum <- max(values)
  minimum <- min(values)
  column_sums <- colSums(matrix)
  million_fraction <- near_one_million_fraction(column_sums)

  if (negative_fraction > 0) {
    return("log_expression_or_residuals")
  }
  if (integer_fraction >= 0.99 && maximum > 50 && zero_fraction > 0.01) {
    return("raw_counts_or_estimated_counts")
  }
  if (million_fraction >= 0.8 && integer_fraction < 0.99) {
    return("tpm_or_cpm")
  }
  if (minimum >= 0 && maximum <= 50 && integer_fraction < 0.99) {
    return("log_expression")
  }
  if (minimum >= 0 && integer_fraction < 0.99) {
    return("normalized_expression")
  }

  "ambiguous"
}

matrix_distribution_metrics <- function(matrix, matrix_name, declared_scale = "auto", normality_max_values = 5000) {
  values <- finite_values(matrix)
  if (length(values) == 0) {
    fail("%s contains no finite numeric values", matrix_name)
  }

  column_sums <- colSums(matrix)
  nonnegative <- all(values >= 0)
  log_values <- if (nonnegative) log2(values + 1) else values

  data.frame(
    matrix_name = matrix_name,
    declared_scale = declared_scale,
    inferred_scale = infer_bulk_matrix_scale(matrix, declared_scale),
    features = nrow(matrix),
    samples = ncol(matrix),
    min = min(values),
    q25 = unname(stats::quantile(values, 0.25, names = FALSE)),
    median = stats::median(values),
    mean = mean(values),
    q75 = unname(stats::quantile(values, 0.75, names = FALSE)),
    p95 = unname(stats::quantile(values, 0.95, names = FALSE)),
    p99 = unname(stats::quantile(values, 0.99, names = FALSE)),
    max = max(values),
    zero_fraction = mean(values == 0),
    negative_fraction = mean(values < 0),
    integer_like_fraction = fraction_integer_like(values),
    median_column_sum = stats::median(column_sums),
    min_column_sum = min(column_sums),
    max_column_sum = max(column_sums),
    columns_near_one_million_fraction = near_one_million_fraction(column_sums),
    raw_value_shapiro_p = safe_shapiro_p(values, normality_max_values),
    raw_value_skewness = safe_skewness(values),
    raw_value_excess_kurtosis = safe_excess_kurtosis(values),
    raw_value_qq_correlation = safe_qq_correlation(values, normality_max_values),
    log2p1_or_current_shapiro_p = safe_shapiro_p(log_values, normality_max_values),
    log2p1_or_current_skewness = safe_skewness(log_values),
    log2p1_or_current_excess_kurtosis = safe_excess_kurtosis(log_values),
    log2p1_or_current_qq_correlation = safe_qq_correlation(log_values, normality_max_values),
    stringsAsFactors = FALSE
  )
}

sample_distribution_metrics <- function(matrix, matrix_name, normality_max_values = 5000) {
  rows <- lapply(colnames(matrix), function(sample_id) {
    values <- matrix[, sample_id]
    finite <- values[is.finite(values)]
    log_values <- if (all(finite >= 0)) log2(finite + 1) else finite

    data.frame(
      matrix_name = matrix_name,
      sample_id = sample_id,
      min = min(finite),
      median = stats::median(finite),
      mean = mean(finite),
      max = max(finite),
      zero_fraction = mean(finite == 0),
      integer_like_fraction = fraction_integer_like(finite),
      shapiro_p = safe_shapiro_p(finite, normality_max_values),
      skewness = safe_skewness(finite),
      excess_kurtosis = safe_excess_kurtosis(finite),
      qq_correlation = safe_qq_correlation(finite, normality_max_values),
      log2p1_or_current_shapiro_p = safe_shapiro_p(log_values, normality_max_values),
      stringsAsFactors = FALSE
    )
  })

  do.call(rbind, rows)
}

recommend_bulk_de_method <- function(assessment) {
  count_like <- assessment$matrix_name == "counts" |
    assessment$declared_scale %in% c("raw_counts", "estimated_counts", "counts") |
    assessment$inferred_scale == "raw_counts_or_estimated_counts"
  usable_count <- count_like &
    assessment$negative_fraction == 0 &
    assessment$integer_like_fraction >= 0.99

  if (any(usable_count)) {
    count_rows <- assessment[usable_count, , drop = FALSE]
    primary <- if ("counts" %in% count_rows$matrix_name) "counts" else count_rows$matrix_name[[1]]
    return(data.frame(
      decision = c(
        "primary_input",
        "differential_expression_methods",
        "normalized_matrices",
        "normality_interpretation"
      ),
      value = c(
        primary,
        "DESeq2, edgeR, or limma-voom from the count matrix",
        "Use TPM/FPKM/CPM/log-expression only for summaries, QC, visualization, or documented fallback when counts are absent",
        "Raw counts are expected to be non-normal; do not force normality before count-model differential expression"
      ),
      stringsAsFactors = FALSE
    ))
  }

  if (any(count_like)) {
    count_rows <- assessment[count_like, , drop = FALSE]
    primary <- if ("counts" %in% count_rows$matrix_name) "counts" else count_rows$matrix_name[[1]]
    return(data.frame(
      decision = c(
        "primary_input",
        "differential_expression_methods",
        "preferred_action",
        "normality_interpretation"
      ),
      value = c(
        primary,
        "Do not run DESeq2, edgeR, or limma-voom until the count matrix is verified as non-negative integer-like counts",
        "Check matrix provenance; recover the true raw or estimated count matrix instead of converting normalized expression",
        "Distribution diagnostics can flag suspicious input, but raw counts are still not expected to be normally distributed"
      ),
      stringsAsFactors = FALSE
    ))
  }

  normalized_like <- assessment$declared_scale %in% c("tpm", "fpkm", "cpm", "log_expression", "normalized_expression") |
    assessment$inferred_scale %in% c("tpm_or_cpm", "log_expression", "normalized_expression", "log_expression_or_residuals")

  if (any(normalized_like)) {
    normalized_rows <- assessment[normalized_like, , drop = FALSE]
    primary <- normalized_rows$matrix_name[[1]]
    return(data.frame(
      decision = c(
        "primary_input",
        "differential_expression_methods",
        "preferred_action",
        "normality_interpretation"
      ),
      value = c(
        primary,
        "Use log_expression_limma.R only as a normalized-expression fallback",
        "Recover raw counts or transcript-level quantifier output if count-model inference is required",
        "Assess whether the matrix is already log-transformed; if not, log2-transform normalized positive values before linear modeling"
      ),
      stringsAsFactors = FALSE
    ))
  }

  data.frame(
    decision = c("primary_input", "differential_expression_methods", "preferred_action"),
    value = c(
      "undetermined",
      "No differential expression method selected automatically",
      "Clarify matrix scale before analysis"
    ),
    stringsAsFactors = FALSE
  )
}

log_cpm <- function(counts, prior_count = 1) {
  validate_nonnegative_counts(counts)
  library_sizes <- colSums(counts)
  if (any(library_sizes <= 0)) {
    fail("Every sample must have a positive library size")
  }

  cpm <- t(t(counts) / library_sizes * 1e6)
  log2(cpm + prior_count)
}

cpm_matrix <- function(counts) {
  validate_nonnegative_counts(counts)
  library_sizes <- colSums(counts)
  if (any(library_sizes <= 0)) {
    fail("Every sample must have a positive library size")
  }

  t(t(counts) / library_sizes * 1e6)
}

length_scaled_matrix <- function(counts, feature_lengths_kb, scale = c("tpm", "fpkm")) {
  scale <- match.arg(scale)
  validate_nonnegative_counts(counts)

  if (any(!is.finite(feature_lengths_kb)) || any(feature_lengths_kb <= 0)) {
    fail("Feature lengths must be finite positive values")
  }
  missing_lengths <- setdiff(rownames(counts), names(feature_lengths_kb))
  if (length(missing_lengths) > 0) {
    fail("Feature length table is missing feature(s): %s", paste(head(missing_lengths, 10), collapse = ", "))
  }

  lengths <- feature_lengths_kb[rownames(counts)]
  rate <- counts / lengths

  if (identical(scale, "tpm")) {
    denominator <- colSums(rate)
    if (any(denominator <= 0)) {
      fail("Every sample must have positive length-scaled expression to compute TPM")
    }
    return(t(t(rate) / denominator * 1e6))
  }

  library_sizes_millions <- colSums(counts) / 1e6
  if (any(library_sizes_millions <= 0)) {
    fail("Every sample must have a positive library size to compute FPKM")
  }
  t(t(rate) / library_sizes_millions)
}

read_feature_lengths <- function(path, feature_column, length_column, length_unit = "bp") {
  lengths <- read_delimited(path)
  require_columns(lengths, c(feature_column, length_column), "Feature length table")

  feature_id <- as.character(lengths[[feature_column]])
  length_value <- suppressWarnings(as.numeric(lengths[[length_column]]))
  if (any(is.na(feature_id)) || any(feature_id == "")) {
    fail("Feature identifiers in length table must be non-empty")
  }
  if (anyDuplicated(feature_id)) {
    duplicated_ids <- unique(feature_id[duplicated(feature_id)])
    fail("Feature length table identifiers must be unique. Examples: %s", paste(head(duplicated_ids, 5), collapse = ", "))
  }
  if (any(is.na(length_value)) || any(!is.finite(length_value)) || any(length_value <= 0)) {
    fail("Feature length column %s must contain finite positive values", length_column)
  }

  if (length_unit == "bp") {
    length_value <- length_value / 1000
  } else if (length_unit != "kb") {
    fail("--length-unit must be bp or kb")
  }

  stats::setNames(length_value, feature_id)
}

write_tsv <- function(data, path, row.names = FALSE) {
  write.table(
    data,
    file = path,
    sep = "\t",
    quote = FALSE,
    row.names = row.names,
    col.names = TRUE,
    na = ""
  )
}

write_matrix_with_id <- function(matrix, path, id_name = "feature_id") {
  data <- data.frame(id = rownames(matrix), matrix, check.names = FALSE)
  colnames(data)[1] <- id_name
  write_tsv(data, path)
}

standardize_feature_column <- function(data, feature_column = NULL, label = "Table") {
  if (!is.null(feature_column) && !identical(feature_column, "")) {
    require_columns(data, feature_column, label)
    return(as.character(data[[feature_column]]))
  }
  as.character(data[[1]])
}

sanitize_model_columns <- function(metadata, columns) {
  require_columns(metadata, columns, "Metadata")
  safe_names <- make.names(colnames(metadata), unique = TRUE)
  mapping <- stats::setNames(safe_names, colnames(metadata))
  sanitized <- metadata
  colnames(sanitized) <- safe_names
  list(metadata = sanitized, mapping = mapping)
}

prepare_de_model <- function(metadata, covariates, condition_column, reference_level, contrast_level) {
  required_model_columns <- c(covariates, condition_column)
  require_columns(metadata, required_model_columns, "Metadata")

  condition_values <- as.character(metadata[[condition_column]])
  if (any(is.na(condition_values)) || any(condition_values == "")) {
    fail("Condition column %s contains missing or empty values", condition_column)
  }
  if (!reference_level %in% condition_values) {
    fail("Reference level %s is not present in %s", reference_level, condition_column)
  }
  if (!contrast_level %in% condition_values) {
    fail("Contrast level %s is not present in %s", contrast_level, condition_column)
  }

  condition_levels <- unique(condition_values)
  safe_condition_levels <- make.names(condition_levels, unique = FALSE)
  if (anyDuplicated(safe_condition_levels)) {
    fail("Condition levels are not unique after R name sanitization")
  }
  condition_level_map <- stats::setNames(safe_condition_levels, condition_levels)

  for (column in required_model_columns) {
    if (is.character(metadata[[column]])) {
      metadata[[column]] <- factor(metadata[[column]])
    }
  }
  metadata[[condition_column]] <- factor(
    condition_level_map[condition_values],
    levels = condition_level_map[condition_levels]
  )
  metadata[[condition_column]] <- stats::relevel(
    metadata[[condition_column]],
    ref = condition_level_map[[reference_level]]
  )

  sanitized <- sanitize_model_columns(metadata, required_model_columns)
  model_metadata <- sanitized$metadata
  model_terms <- unname(sanitized$mapping[required_model_columns])
  condition_term <- unname(sanitized$mapping[[condition_column]])
  design_formula <- stats::reformulate(model_terms)
  design <- stats::model.matrix(design_formula, model_metadata)

  if (qr(design)$rank < ncol(design)) {
    fail("Design matrix is not full rank. Check confounded conditions, batches, or covariates.")
  }

  contrast_level_safe <- condition_level_map[[contrast_level]]
  reference_level_safe <- condition_level_map[[reference_level]]
  contrast_coefficient <- paste0(condition_term, contrast_level_safe)
  if (!contrast_coefficient %in% colnames(design)) {
    fail("Could not identify contrast coefficient %s in design columns: %s", contrast_coefficient, paste(colnames(design), collapse = ", "))
  }

  list(
    metadata = model_metadata,
    design_formula = design_formula,
    design = design,
    condition_term = condition_term,
    reference_level_safe = reference_level_safe,
    contrast_level_safe = contrast_level_safe,
    contrast_coefficient = contrast_coefficient,
    condition_level_map = condition_level_map
  )
}

write_de_run_parameters <- function(path, design_formula, condition_column, reference_level, contrast_level,
                                    covariates, min_count = NA, min_samples = NA, fdr = NA,
                                    features_before_filter = NA, features_after_filter = NA,
                                    matrix_scale = "raw_counts") {
  run_parameters <- data.frame(
    parameter = c(
      "matrix_scale",
      "design_formula",
      "condition_column",
      "reference_level",
      "contrast_level",
      "covariates",
      "min_count",
      "min_samples",
      "fdr",
      "features_before_filter",
      "features_after_filter"
    ),
    value = c(
      matrix_scale,
      paste(deparse(design_formula), collapse = " "),
      condition_column,
      reference_level,
      contrast_level,
      paste(covariates, collapse = ","),
      min_count,
      min_samples,
      fdr,
      features_before_filter,
      features_after_filter
    ),
    stringsAsFactors = FALSE
  )
  write_tsv(run_parameters, path)
}

require_qc_review <- function(args, method_name) {
  if (isTRUE(args[["qc-reviewed"]])) {
    return(invisible(TRUE))
  }

  message("Pre-differential-expression QC review is required before running ", method_name, ".")
  message("Run and review the relevant preflight outputs first, for example:")
  message("  scripts/bulk-rnaseq/diagnostics/assess_expression_matrices.R")
  message("  scripts/bulk-rnaseq/qc/pre_de_qc.R")
  message("Check sample uniformity, group sample counts, PCA structure, sample correlations, matrix scale, and design confounding.")
  message("After unresolved QC issues are accepted or addressed, rerun this script with --qc-reviewed.")
  quit(status = 2, save = "no")
}
