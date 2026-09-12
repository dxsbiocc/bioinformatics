# cBioPortal MCP

Metadata-first MCP tools for cBioPortal cancer genomics records.

## Tools

- `cbioportal_study_search`: search public cBioPortal studies.
- `cbioportal_study_lookup`: fetch one study with optional molecular profile
  and sample-list previews.
- `cbioportal_molecular_profiles`: list study molecular profiles.
- `cbioportal_sample_lists`: list study sample lists.
- `cbioportal_mutations_fetch`: fetch bounded mutation rows for Entrez Gene IDs
  or HUGO symbols.
- `cbioportal_molecular_data_fetch`: fetch bounded numeric molecular data rows,
  such as expression z-scores, with table and heatmap-matrix previews.
- `cbioportal_discrete_cna_fetch`: fetch bounded GISTIC-style discrete
  copy-number calls with alteration labels and heatmap-matrix previews.
- `cbioportal_clinical_attributes`: list clinical attribute definitions for a
  study.
- `cbioportal_clinical_data_fetch`: fetch bounded sample or patient clinical
  values as both long-form rows and a front-end-ready matrix.
- `cbioportal_survival_data_fetch`: fetch bounded OS/DFS-style survival
  clinical values as chart-ready rows plus fallback tables.
- `cbioportal_status`: inspect server configuration and optional network health.

Mutation, molecular-data, discrete-CNA, clinical, survival, and study responses
are metadata-only and expose cBioPortal browser/API links through the shared
`bioinformatics.record.v1` display envelope.

Gene-symbol fetch tools resolve HUGO symbols through `genes/fetch` with
`geneIdType=HUGO_GENE_SYMBOL`. Symbols that cBioPortal does not resolve are
reported in `structuredContent.warnings` and omitted from downstream requests.
If cBioPortal returns HTTP 404 or an empty payload for a mutation,
molecular-data, or CNA fetch, the MCP returns an empty dataset record plus a
warning instead of aborting the whole batch or leaving the empty state
ambiguous. The warning includes `diagnosis` details from lightweight
single-resource checks against `molecular-profiles/{id}` and, when relevant,
`sample-lists/{id}`. Front ends can use the warning `code` and
`diagnosis.status` to render a precise empty state:

- `cbioportal_profile_not_found` / `profile_not_found`
- `cbioportal_sample_list_not_found` / `sample_list_not_found`
- `cbioportal_profile_sample_list_study_mismatch` / `study_mismatch`
- `cbioportal_fetch_context_not_found` / `fetch_context_not_found`
- `cbioportal_fetch_context_empty` / `fetch_context_not_found`
- `cbioportal_fetch_diagnosis_incomplete` / `diagnosis_incomplete`

The same diagnostics are copied into each returned record under
`record.data.diagnostics` and summarized in display metadata for hover/detail
cards.
