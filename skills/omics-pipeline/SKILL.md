---
name: omics-pipeline
description: >-
  Plan, build, run, and troubleshoot reproducible omics data-processing
  pipelines from raw or intermediate assay files. Use for FASTQ/BAM/CRAM,
  sequencing QC, trimming, alignment, quantification, variant or feature
  generation, workflow orchestration, and environment capture. Do not use for
  literature review, public-record lookup, figure-only work, or downstream
  biological interpretation from an already prepared result table.
---

# Omics Pipeline

Create reproducible workflows that transform raw or intermediate assay files
into documented analysis-ready artifacts without overwriting source data.

## Workflow

1. Identify assay type, input files, sample relationships, reference build,
   library design, strandedness or barcodes, expected outputs, compute
   environment, and resource constraints.
2. For public GEO/SRA inputs, use the NCBI MCP planning tools before execution:
   `geo_download_plan` or `sra_download_plan` to prepare metadata-only download
   manifests, and `omics_sample_sheet` to derive a front-end-ready sample table.
   Use `tool_runtime_status` to check whether expected command-line tools are
   already available on `PATH` before solving environments manually.
3. Validate file readability, naming, pairing, sample-sheet consistency,
   checksums when available, and reference compatibility before execution.
4. Choose maintained tools and define explicit stages, inputs, outputs,
   dependencies, checkpoints, and failure boundaries.
5. Implement the workflow in project-local, reviewable source with pinned or
   recorded versions and parameters. Reuse existing project conventions when
   they are sound.
6. Run the smallest meaningful validation first, then execute the requested
   scope while preserving logs, QC reports, and provenance.
7. Verify expected outputs, sample counts, mapping or quantification metrics,
   failed samples, resumability, and handoff into downstream analysis.

## Safety and reproducibility

- Never overwrite raw sequencing or assay inputs.
- Do not mix reference assemblies, annotation releases, or incompatible sample
  identifiers silently.
- Do not download large references or datasets unless required by the requested
  run and within the user's authorized scope.
- Record commands, versions, parameters, checksums when available, and all
  deviations from the planned workflow.
- Stop downstream stages when an upstream validation or QC gate fails.

## Delivery

Return workflow source, sample sheet, environment or version record, commands or
run instructions, output locations, QC summary, failures, and known gaps.
