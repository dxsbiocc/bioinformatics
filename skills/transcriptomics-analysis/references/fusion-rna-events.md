# Fusion and RNA Event Analysis

Use this reference when the task asks for fusion genes, chimeric transcripts,
RNA editing, circular RNA, allele-specific expression, or aberrant transcript
events. These analyses usually need read-level or variant-level evidence, not
only an expression matrix.

## Analysis Types

- Gene fusion or chimeric transcript detection.
- RNA editing and RNA-DNA mismatch events.
- Circular RNA detection and differential circRNA abundance.
- Allele-specific expression and imprinting-like expression imbalance.
- Aberrant expression or aberrant splicing outlier detection.

## Inputs

- Aligned reads, chimeric junctions, splice junctions, split reads, discordant
  pairs, variant calls, phased genotype, or event-specific count tables.
- Sample metadata, tumor/normal status when relevant, replicate or cohort
  structure, and reference genome/annotation release.
- Evidence thresholds for supporting reads, mapping quality, blacklists, and
  recurrent artifacts.

## Method Pointers

- STAR-Fusion, Arriba, FusionCatcher, and related tools are common fusion
  callers.
- REDItools and SPRINT-style workflows are common for RNA editing.
- CIRI, DCC, and find_circ-style workflows are common for circular RNA.
- GATK ASEReadCounter or similar allele-count workflows support ASE when genotype
  data are available.
- OUTRIDER and FRASER target aberrant expression or splicing outliers.

## Guardrails

- Do not call fusions, circRNAs, editing, or ASE from a gene expression matrix
  alone.
- Do not report a fusion without junction evidence, breakpoint annotation,
  supporting read counts, and artifact filtering.
- Do not interpret RNA editing without considering genomic variants, mapping
  artifacts, repeats, strand, and base-quality filters.
- Do not compare event counts across samples without normalization and detection
  sensitivity checks.

## Deliverables

Return event tables with evidence counts, filtering thresholds, annotation and
reference versions, candidate prioritization, validation needs, and limitations
around read support and false positives.
