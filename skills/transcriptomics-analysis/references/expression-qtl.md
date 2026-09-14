# Expression QTL and Transcriptome Genetics

Use this reference for eQTL, sQTL, isoform QTL, allele-specific expression QTL,
TWAS, PrediXcan/FUSION-style analyses, or colocalization between expression and
genetic association signals.

## Inputs

- Expression phenotype matrix at gene, transcript, splice, exon, or module level.
- Genotype dosage or variant matrix with sample IDs matching expression
  phenotypes.
- Covariates such as genotype principal components, sex, age, batch, PEER/SVA
  factors, hidden factors, library metrics, and known technical variables.
- Genomic coordinates, genome build, ancestry context, and cis-window definition.

## Method Pointers

- Matrix eQTL, FastQTL, QTLtools, and tensorQTL are common eQTL/sQTL engines.
- PEER, SVA, RUV, or genotype PCs may be used as covariates, but they must not
  absorb the biological signal of interest without review.
- TWAS and PrediXcan/FUSION-style workflows require trained expression prediction
  models and GWAS summary statistics.
- Colocalization methods such as coloc, eCAVIAR, or SuSiE-coloc require
  harmonized variants, LD awareness, and trait association summary statistics.

## Guardrails

- Do not run eQTL without matched genotype and expression samples.
- Do not mix genome builds, alleles, or variant identifiers without harmonizing
  and checking strand/allele orientation.
- Do not ignore population structure, relatedness, hidden confounders, or batch
  effects.
- Do not treat eQTL association as colocalization or causality without a
  dedicated model.
- Do not use gene expression residuals unless the covariate regression and
  retained signal are documented.

## Deliverables

Return phenotype and genotype sample matching summaries, covariate model,
cis/trans scope, multiple-testing strategy, significant QTL tables, diagnostic
plots or tables, and limitations around ancestry, sample size, LD, and
confounding.
