# Single-cell and Single-nucleus RNA-seq

Use this reference for prepared scRNA-seq or snRNA-seq count matrices, AnnData,
Seurat objects, or equivalent cell-by-gene data with cell and sample metadata.

## Required Context

- Assay type: single-cell or single-nucleus RNA-seq, chemistry, paired modalities
  if present, and whether ambient RNA correction or doublet detection was
  already performed.
- Matrix scale: raw counts, normalized counts, log-normalized values, residuals,
  integrated embeddings, or corrected assays.
- Metadata: sample, donor, condition, batch, library, cell/nucleus barcode,
  cluster labels, cell-type annotations, and QC metrics.
- Biological unit for inference: donor or sample, not individual cells.
- Intended question: QC, integration, clustering, annotation, marker discovery,
  composition shifts, or differential expression.

## Analysis Guidance

1. Validate cell barcode uniqueness, feature identifiers, metadata alignment,
   sample labels, and assay layers before analysis.
2. Inspect per-cell library size, detected genes, mitochondrial or ribosomal
   fraction, unspliced or intronic signal when relevant, doublet scores, ambient
   RNA indicators, and sample-level cell recovery.
3. Filter cells and genes with explicit thresholds, but prefer data-informed
   thresholds over fixed defaults when quality varies by sample or chemistry.
4. Normalize and identify highly variable genes for dimensionality reduction;
   keep raw counts or model-suitable layers available for downstream inference.
5. Use PCA, neighborhood graphs, UMAP or t-SNE, and clustering as exploratory
   structure, then validate clusters with marker genes, metadata enrichment, and
   sample representation.
6. Treat batch integration as a correction for representation and visualization;
   avoid using integrated values as the default substrate for differential
   expression unless the method explicitly supports it.
7. Prefer pseudobulk or mixed-model approaches for condition-level differential
   expression across donors or samples. Cell-level marker tests are descriptive
   unless the inference target is explicitly cell-level.

## Guardrails

- Do not treat thousands of cells from the same donor as thousands of independent
  biological replicates.
- Do not assign definitive cell types from a single marker without checking
  marker panels and tissue context.
- Do not compare conditions in a cluster that lacks representation from enough
  biological samples per condition.
- Do not hide sample imbalance behind merged UMAPs; report sample and condition
  composition.

## Deliverables

Return executable analysis code, filtered object or matrix paths when created,
QC summaries, embeddings, cluster assignments, marker tables, annotation
rationale, pseudobulk tables when used, differential expression tables, and
limitations around replication, batch, and annotation confidence.
