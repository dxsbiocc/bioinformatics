# Spatial Transcriptomics

Use this reference for prepared spatial transcriptomics data with expression
measurements linked to tissue coordinates, spots, segmented cells, imaging
channels, histology, or tissue annotations.

## Required Context

- Platform class: capture-based spots, bead-based arrays, imaging-based panels,
  sequencing-based in situ assays, or spatial single-cell/nucleus data.
- Observation unit: spot, bead, segmented cell, region of interest, field of
  view, section, donor, or sample.
- Inputs: expression matrix, spatial coordinates, image or morphology metadata,
  tissue mask, segmentation, sample metadata, and annotation layers.
- Matrix scale: raw counts, normalized values, transformed values, or model
  residuals.
- Intended question: spatial QC, domain discovery, spatially variable genes,
  tissue-region differential expression, deconvolution, neighborhood analysis, or
  spatial interaction hypotheses.

## Analysis Guidance

1. Validate expression-to-coordinate alignment, tissue image registration,
   sample or section identifiers, image orientation, and missing coordinates.
2. Inspect spatial library depth, detected genes, tissue coverage, background
   spots or cells, segmentation quality, edge effects, and section-level batch
   structure.
3. Filter observations using both molecular QC and spatial or tissue context;
   report whether observations outside tissue, low-quality regions, or ambiguous
   segmentations were removed.
4. Normalize with awareness of platform and observation unit. Preserve raw counts
   for methods that require them.
5. Use spatial coordinates and tissue annotations when interpreting clusters or
   domains; do not rely only on low-dimensional embeddings.
6. For spatially variable genes, domains, or tissue-region contrasts, account for
   spatial autocorrelation, sample structure, and section-level replication where
   possible.
7. For deconvolution or cell-type mapping, state the reference dataset, gene
   overlap, cell-type vocabulary, and uncertainty in mixed spots or ambiguous
   regions.

## Guardrails

- Do not treat neighboring spots, beads, or cells from one tissue section as
  independent biological replicates for sample-level claims.
- Do not combine platforms or sections without checking coordinate systems,
  resolution, normalization, and batch effects.
- Do not infer histological regions or cell types without either provided
  annotation, marker evidence, image context, or an explicit uncertainty label.
- Do not discard spatial coordinates during an analysis whose interpretation is
  spatial.

## Deliverables

Return executable analysis code, QC summaries, filtered object paths when
created, spatial coordinates retained in outputs, domain or cluster assignments,
spatially variable gene tables, deconvolution or neighborhood results when used,
image or annotation provenance, and limitations around spatial resolution,
replication, and registration quality.
