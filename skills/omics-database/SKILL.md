---
name: omics-database
description: >-
  Discover and retrieve authoritative bioinformatics database records, public
  omics datasets, accessions, sequences, annotations, and identifier mappings.
  Use when a request depends on public repository metadata or stable biological
  identifiers. Do not use for scholarly literature synthesis, local statistical
  analysis, raw-data pipeline execution, or unsupported bulk downloads.
---

# Omics Database

Resolve biological entities and public datasets against authoritative database
records, using documented APIs or export mechanisms and preserving provenance.

## Workflow

1. Identify the entity type, organism, identifier namespace, assembly or release
   when relevant, requested fields, and acceptable data scope.
2. Select the authoritative source for the record or dataset. Prefer primary
   repositories over secondary summaries. PubMed literature discovery belongs to
   `omics-literature`; non-literature NCBI records belong behind the existing
   `ncbi` MCP server as Gene, Nucleotide, SRA, BioSample, GEO, BioProject, or
   related Entrez database tools. UniProtKB protein records and FASTA sequences
   belong behind the `uniprot` MCP server. Use `geo_series` for exact GEO Series
   accessions such as `GSE100`; use `geo_search` for broader GEO DataSets
   discovery. Use `gene_lookup` for GeneID/symbol resolution, `taxonomy_lookup`
   for organism and TaxID resolution, `pmc_id_convert` for PMID/PMCID/DOI
   mapping, and `bioproject_lookup`, `biosample_lookup`, `sra_lookup`, or
   `sra_search` for public sequencing project/sample/run metadata. Use
   `uniprot_search` for UniProtKB protein discovery, `uniprot_lookup` for exact
   accessions such as `P04637`, and `uniprot_fasta` for metadata-first sequence
   retrieval. UniProt records expose app-renderable `protein` records with
   bounded features, feature tracks, keywords, comments, literature links, and
   grouped cross-references for detail panes. UniProt records also expose
   `display.previews` hints for sequence, feature-track, 3D-structure,
   STRING-network, citation-list, and grouped cross-reference widgets when the
   underlying database response contains those identifiers. Use
   `geo_download_plan` for a GSE
   download manifest,
   `sra_download_plan` for an SRA run manifest and command suggestions, and
   `omics_sample_sheet` when a front-end-ready GEO or SRA sample table is needed
   before pipeline work. Use `ncbi_link` or `ncbi_related_records` for
   cross-database Entrez relationships. NCBI records expose `display.previews`
   hints for PubMed citation lists, GEO/SRA download manifests, sample-sheet
   tables, grouped Entrez cross-references, SRA run tables, and runtime text
   summaries when the normalized response contains those data. Use
   `alphafold_lookup` for AlphaFold DB predicted protein structures from a
   UniProt accession; AlphaFold records expose `protein_structure` display
   records with `structure_3d`, `download_manifest`, and optional `sequence`
   previews. Use `rcsb_lookup` for experimental PDB structures such as `4HHB`,
   `rcsb_search` for RCSB PDB full-text structure discovery, and `rcsb_fasta`
   for PDB entry FASTA. RCSB records expose `protein_structure` display records
   with `structure_3d`, `download_manifest`, polymer/ligand `table`, citation,
   and optional `sequence` previews. Use `string_map` to resolve gene symbols,
   UniProt accessions, or other protein identifiers to STRING IDs, and use
   `string_interactions` for protein-protein association networks. STRING
   interaction results expose `protein_network` records with browser URLs,
   graph nodes, graph edges, combined scores, evidence-channel scores, and
   `network`/`table` preview hints for app-side rendering. Use
   `reactome_lookup` for exact Reactome pathway/event stable IDs such as
   `R-HSA-5633007`, `reactome_search` for pathway discovery by text, and
   `reactome_pathways_for_identifier` to map identifiers such as UniProt
   accessions to Reactome pathways. Reactome records expose `pathway` display
   records with browser URLs, participant network/table previews,
   citation-list previews, and grouped Reactome identifiers for app-side
   rendering. Use `ensembl_lookup` for Ensembl stable IDs such as
   `ENSG00000141510`, `ensembl_xrefs` for bounded external cross-reference
   groups, `ensembl_overlap_region` for genes/transcripts/variants overlapping
   genomic coordinates, and `ensembl_variation` for variants such as `rs699`.
   Ensembl records expose `gene`, `genomic_feature`, `variant`, and
   `identifier_conversion` display records with browser/API URLs, hover fields,
   transcript/mapping tables, and grouped cross-reference previews. Use
   `clinvar_lookup` for exact ClinVar numeric variation IDs or VCV accessions
   such as `VCV000037390`, and `clinvar_search` for ClinVar variant discovery
   through NLM Clinical Tables with NCBI ClinVar ESummary hydration. ClinVar
   records expose `variant` display records with clinical significance, review
   status, gene/dbSNP links, locations, supporting RCV/SCV submissions, and
   grouped cross-reference previews. Use `gnomad_variant_lookup` for gnomAD
   variant IDs such as `1-230710048-A-G` when population allele frequencies,
   exome/genome counts, or transcript consequences are needed, and use
   `gnomad_gene_lookup` for Ensembl gene IDs such as `ENSG00000141510` when
   gnomAD constraint metrics are needed. gnomAD records expose `variant` and
   `gene` display records with browser URLs, frequency/constraint tables,
   bounded transcript rows, and grouped cross-reference previews. Use
   `gwas_variant_lookup` for rsIDs such as `rs699` when variant-to-trait GWAS
   evidence is needed, `gwas_gene_lookup` for mapped-gene association evidence
   such as `BRCA1`, and `gwas_trait_search` for disease or phenotype queries
   such as `asthma`. GWAS Catalog records expose `variant`, `gene`, and
   `dataset` display records with association tables, study tables, PubMed
   evidence previews, EFO trait links, SNP links, and grouped cross-reference
   previews. Use `opentargets_target_lookup` for Ensembl gene IDs such as
   `ENSG00000141510` when target-to-disease association scores and datasource
   evidence breadth are needed, `opentargets_disease_lookup` for Open Targets
   disease IDs such as `MONDO_0004979` when disease-to-target evidence ranking
   is needed, and `opentargets_search` to resolve text such as `TP53` or
   `asthma` to target/disease identifiers. Open Targets records expose `gene`,
   `dataset`, and `identifier_conversion` display records with browser links,
   association tables, datasource/datatype score tables, ontology xrefs, and
   grouped cross-reference previews. Use `chembl_molecule_lookup` for exact
   ChEMBL molecule IDs such as `CHEMBL25`, `chembl_molecule_search` for
   compound discovery by name such as `imatinib`, `chembl_target_lookup` for
   ChEMBL targets such as `CHEMBL1824`, `chembl_assay_lookup` for assay
   metadata such as `CHEMBL1217643`, `chembl_document_lookup` for ChEMBL source
   documents such as `CHEMBL1212834`, `chembl_activity_search` for bounded
   bioactivity measurements by molecule or target, and
   `chembl_mechanism_search` for mechanism-of-action rows. Use
   `chembl_drug_indications` for molecule-to-indication evidence such as
   `CHEMBL25`, including EFO/HPO terms, MeSH terms, maximum indication phase,
   and upstream evidence references. ChEMBL records expose `compound`,
   `protein`, and `dataset` display records with chemical structure previews,
   molecule properties, target-component tables, assay metadata, activity,
   mechanism, or indication tables, source-document citation records, grouped
   cross-references, and ChEMBL browser/API links.
   Use `pubchem_compound_lookup` for PubChem CIDs or exact names such as
   `2244` or `aspirin`, `pubchem_compound_search` to resolve names/synonyms to
   PubChem CIDs, `pubchem_assay_summary` for BioAssay AIDs such as `1706`, and
   `pubchem_substance_lookup` for Substance IDs such as `4594`. PubChem records
   expose `compound` and `dataset` display records with chemical structure
   previews, property tables, descriptions, synonyms, BioAssay summary tables,
   Substance depositor metadata, grouped cross-references, and PubChem
   browser/PUG REST links. Use `quickgo_term_lookup` for exact GO identifiers
   such as `GO:0006915`, `quickgo_term_search` for Gene Ontology term
   discovery, `quickgo_term_children` for child term traversal, and
   `quickgo_annotation_search` for bounded GOA evidence rows by UniProt/gene
   product, GO term, taxon, or evidence code. QuickGO records expose
   `ontology_term` and `dataset` display records with GO definitions,
   synonyms, ontology relation network previews, annotation evidence tables,
   grouped cross-references, PubMed/GO_REF links, and QuickGO browser/API
   links. Use `pride_project_lookup` for exact PRIDE/ProteomeXchange accessions
   such as `PXD001357`, `pride_project_search` for proteomics project
   discovery, and `pride_project_files` for a metadata-only PRIDE file
   manifest. PRIDE records expose `project` and `download_plan` display records
   with project descriptions, protocols, organisms, instruments, experiment
   types, publication references, bounded file manifests, HTTPS file links where
   PRIDE FTP locations are mirrorable, and PRIDE browser/API links. Use
   `biostudies_study_lookup` for exact BioStudies or ArrayExpress accessions
   such as `E-MTAB-6701`, `biostudies_search` for broad BioStudies discovery,
   `arrayexpress_search` for ArrayExpress-focused functional genomics datasets,
   and `biostudies_file_manifest` for a metadata-only BioStudies file manifest.
   BioStudies records expose `project` and `download_plan` display records with
   study descriptions, release dates, organisms, study types, protocols,
   publication references, external repository links such as ENA or Expression
   Atlas, bounded file manifests, HTTPS download links, and BioStudies
   browser/API links. Use `cellxgene_collection_lookup` for exact CELLxGENE
   Discover collection UUIDs, `cellxgene_collections_search` for bounded
   metadata filtering across public single-cell collections, and
   `cellxgene_collection_assets` for a metadata-only H5AD asset manifest.
   CELLxGENE records expose `project` and `download_plan` display records with
   collection descriptions, DOI/publication metadata, authors, dataset tables,
   organism/tissue/disease/cell type/assay ontology labels, explorer URLs,
   H5AD asset links, and CELLxGENE browser/API links. Use `hpa_gene_lookup` for
   exact Human Protein Atlas Ensembl gene IDs such as `ENSG00000141510`, and
   `hpa_search` for HPA gene metadata discovery by symbol, synonym, Ensembl ID,
   or free text. HPA records expose `gene` display records with HPA browser/API
   links, RNA/protein expression summaries, subcellular localization, antibody
   reliability, cancer prognostic tables when available, and UniProt/Ensembl
   cross-reference previews. Use `metabolights_study_lookup` for exact
   MetaboLights accessions such as `MTBLS1`, `metabolights_search` for
   metabolomics study discovery through EBI Search, and
   `metabolights_file_manifest` for a metadata-only MetaboLights file manifest.
   MetaboLights records expose `project` and `download_plan` display records
   with study designs, organism labels, assays, protocols, publications,
   bounded file manifests, FTP HTTPS/Globus links, and MetaboLights browser/API
   links. Use `mgnify_study_lookup` for exact MGnify study accessions such as
   `MGYS00006862`, `mgnify_study_search` for microbiome/metagenomics study
   discovery, `mgnify_sample_lookup` for MGnify samples such as `SRS10016989`,
   and `mgnify_biome_lookup` for biome lineages such as
   `root:Host-associated:Human:Digestive system:Large intestine`. MGnify
   records expose `project`, `sample`, and `taxonomy` display records with
   BioProject/BioSample links, sample metadata tables, biome lineages, related
   samples/studies/analyses/downloads links, and MGnify browser/API links. Use
   `encode_experiment_lookup` for exact ENCODE experiment accessions such as
   `ENCSR844TIU`, `encode_experiment_search` for functional-genomics dataset
   discovery such as `K562 RNA-seq` or `ATAC-seq`, `encode_file_lookup` for
   ENCODE file accessions such as `ENCFF789PHQ`, and `encode_file_manifest`
   for metadata-only experiment file manifests. Use `encode_biosample_lookup`
   for exact ENCODE biosample accessions such as `ENCBS000AAA`, and
   `encode_biosample_search` for biosample discovery such as `K562`, `MCF-7`,
   liver, or T cell. ENCODE records expose `project`, `sample`, and
   `download_plan` display records with assay and biosample summaries, sample
   organism/life-stage/sex/ontology metadata, status, assemblies, GEO
   cross-references, HTTPS/cloud file links, checksums, replicate fields, and
   ENCODE browser/API links. Use
   `cbioportal_study_search` for cancer genomics cohort discovery,
   `cbioportal_study_lookup` for exact cBioPortal study IDs such as
   `brca_tcga`, `cbioportal_molecular_profiles` and
   `cbioportal_sample_lists` to inspect profile/sample-list IDs before
   downstream queries, `cbioportal_mutations_fetch` to retrieve bounded
   mutation rows for genes such as `TP53` in a profile/sample-list pair,
   `cbioportal_molecular_data_fetch` to retrieve bounded numeric expression or
   molecular matrices, and `cbioportal_discrete_cna_fetch` to retrieve bounded
   GISTIC-style discrete copy-number matrices with alteration labels,
   `cbioportal_clinical_attributes` to inspect available sample/patient
   clinical fields, and `cbioportal_clinical_data_fetch` to retrieve bounded
   sample or patient clinical tables for cohort filters and chart-ready
   matrices. Use `cbioportal_survival_data_fetch` for bounded OS/DFS-style
   survival rows by patient IDs, sample IDs, or sample-list ID when Kaplan-Meier
   style front-end previews are needed.
   cBioPortal records expose `project` and `dataset` display records with
   cancer cohort summaries, molecular profile tables, sample-list tables,
   gene mutation tables, clinical attribute tables, sample/patient clinical
   matrices, survival-curve preview rows, expression/CNA heatmap matrix
   previews, PubMed links when present, and cBioPortal browser/API links.
3. Query narrowly, handle pagination, and preserve stable accession identifiers,
   release information, and source URLs.
   For public cancer expression or multi-omics contrasts where tumor/normal,
   paired, disease state, treatment arm, time point, or other sample-level
   grouping defines the requested comparison, choose a source that exposes
   sample identifiers plus those grouping fields. Use cohort portals such as
   cBioPortal for discovery, molecular-profile inspection, and bounded cohort
   queries, but do not rely on them as the sole source when the required
   comparison groups are absent, aggregated, or not represented in the selected
   profile/sample list. Prefer repository exports or APIs that preserve
   sample-level annotations before downstream analysis.
4. Validate identifier mappings and distinguish exact matches, aliases,
   deprecated records, orthologs, and inferred associations.
5. Save raw responses only when useful or requested, then provide a compact
   normalized result with retrieval date and unresolved ambiguities.

## Front-end Contract

When using MCP tools that return UI-renderable records, prefer
`structuredContent.records[]` over raw text or database-specific payload fields.
Records should follow `schemas/record.schema.json`, with TypeScript consumers
using `types/record.ts` and rendering behavior following
`docs/frontend-record-rendering.md`.

For user-visible identifiers, prefer `stable_id`. For clicks, prefer
`display.primary_url`, then `url`, then `display.actions[].url`, then
`links[].url`. For hover previews, use `display.hover`. For richer shared UI
widgets, use `display.previews` before reaching into database-specific `data`.
Do not reconstruct database URLs in the agent when the MCP already returned
links.

## Boundaries

- Do not guess identifiers or silently merge records from different organisms,
  assemblies, releases, or namespaces.
- Do not expose credentials or place API keys in project files.
- Estimate size before downloading large datasets and do not start a material
  bulk transfer without the user's request.
- SRA, BioSample, and BioProject MCP tools return metadata and links only; do
  not turn Run Browser or Run Selector links into automatic FASTQ/BAM downloads.
- GEO/SRA download-plan MCP tools return manifests, URLs, and command strings
  only; do not execute downloads unless the user explicitly asks for that stage.
- Database records are not a substitute for peer-reviewed evidence; route
  literature questions to `omics-literature`.

## Delivery

Return the resolved identifiers or dataset records, source database, query or
endpoint, release/build context, retrieval date, and any mapping uncertainty.
