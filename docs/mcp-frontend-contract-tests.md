# MCP Front-end Contract Tests

Bioinformatics MCP tools should return database-specific details, but front-end
renderers need a stable shared surface. The contract tests in
`tests/frontend_contract_assertions.py` assert that representative MCP results
include the fields app renderers rely on:

- `structuredContent.records[]`
- `record.url`
- `record.identifiers`
- `record.links`
- `display.component`
- `display.metadata`
- `display.badges`
- `display.primary_url`
- `display.actions[]`
- `display.hover`
- `display.sections[]`
- `display.previews[]`

The shared assertions keep the schema extensible while checking the preview
shapes front-end widgets need today: tables, grouped cross-references,
download manifests, citation lists, networks, sequences, feature tracks, 3D
structures, chemical structures, survival rows, heatmap matrices, and text
summaries.

The tests intentionally use deterministic fake client payloads rather than live
network requests. This keeps CI fast while still protecting the normalized
record contract for NCBI, bioRxiv/medRxiv, RNAcentral, EFO, UniProt, AlphaFold, STRING,
RCSB PDB, Reactome, Ensembl, ClinVar, gnomAD, GWAS Catalog, Open Targets,
ChEMBL, PubChem, ChEBI, QuickGO, PRIDE, BioStudies/ArrayExpress, CELLxGENE,
Human Protein Atlas, MetaboLights, HMDB, MGnify, ENCODE, and cBioPortal.

When adding a new MCP, add at least one representative tool test that calls
`assert_result_frontend_contract` with the expected component and preview kinds.
Do not loosen the shared assertions to accommodate incomplete records; fix the
MCP record builder instead.
