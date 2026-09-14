# Transcript, Isoform, and Splicing Analysis

Use this reference when the question targets transcript usage, isoform switching,
exon usage, alternative splicing, splice-junction usage, or polyadenylation.
These analyses are not ordinary gene-level differential expression.

## Analysis Types

- Alternative splicing: exon skipping, retained intron, alternative splice site,
  mutually exclusive exons, and junction usage.
- Differential transcript usage and isoform switching: changes in transcript
  proportions within a gene.
- Exon usage: differential exon contribution across conditions.
- Alternative polyadenylation: shifts in 3' end usage or polyA site preference.
- Splicing QTL: genotype-associated splice or transcript-usage differences.

## Inputs

- Junction counts, exon counts, transcript-level quantification, event tables,
  BAM-derived splice evidence, or quantifier outputs.
- Sample metadata, biological replicates, batch variables, and contrast
  definitions.
- Annotation version and event definitions. Results are highly annotation
  sensitive.

## Method Pointers

- rMATS, MAJIQ, SUPPA2, and LeafCutter are common for alternative splicing or
  junction/event analysis.
- DEXSeq supports exon usage modeling.
- DRIMSeq and IsoformSwitchAnalyzeR support transcript usage or isoform switch
  workflows.
- DaPars and QAPA-style workflows target alternative polyadenylation.

## Guardrails

- Do not infer splicing from a gene-level count matrix alone.
- Do not mix transcript IDs, gene IDs, exon IDs, and event IDs without preserving
  the mapping.
- Do not ignore read length, strandedness, annotation release, or junction
  filtering because they can change event calls.
- Do not treat isoform-level TPM changes as gene-level differential expression.

## Deliverables

Return event or transcript usage tables, event definitions, annotation source,
filtering rules, contrast direction, method limitations, and links back to gene
or pathway interpretation only when the mapping is clear.
