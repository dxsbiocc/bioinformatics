# cBioPortal MCP Examples

Example calls:

- `cbioportal_study_search` with `{"query":"breast","max_results":5}`.
- `cbioportal_study_lookup` with `{"study_id":"brca_tcga","max_related":10}`.
- `cbioportal_molecular_profiles` with `{"study_id":"brca_tcga"}`.
- `cbioportal_sample_lists` with `{"study_id":"brca_tcga"}`.
- `cbioportal_mutations_fetch` with
  `{"molecular_profile_id":"brca_tcga_mutations","sample_list_id":"brca_tcga_all","hugo_gene_symbols":["TP53"],"max_records":25}`.
- `cbioportal_molecular_data_fetch` with
  `{"molecular_profile_id":"brca_tcga_rna_seq_v2_mrna_median_Zscores","sample_list_id":"brca_tcga_all","hugo_gene_symbols":["TP53","BRCA1"],"max_records":100}`.
- `cbioportal_discrete_cna_fetch` with
  `{"molecular_profile_id":"brca_tcga_gistic","sample_list_id":"brca_tcga_all","hugo_gene_symbols":["TP53","BRCA1"],"discrete_copy_number_event_type":"ALL","max_records":100}`.
- `cbioportal_clinical_attributes` with
  `{"study_id":"brca_tcga","max_results":50}`.
- `cbioportal_clinical_data_fetch` with
  `{"study_id":"brca_tcga","sample_list_id":"brca_tcga_all","clinical_attribute_ids":["CANCER_TYPE","SAMPLE_TYPE"],"max_ids":25}`.
- `cbioportal_survival_data_fetch` with
  `{"study_id":"brca_tcga","sample_list_id":"brca_tcga_all","survival_prefixes":["OS","DFS"],"max_ids":25}`.

Mutation, molecular-data, discrete-CNA, clinical, and survival fetches return
bounded metadata tables or matrices with cBioPortal browser/API links. They do
not download bulk study data.
