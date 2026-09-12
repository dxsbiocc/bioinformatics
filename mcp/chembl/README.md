# ChEMBL MCP Server

This server exposes a metadata-first subset of the official ChEMBL REST API for
compound, target, assay, source-document, bioactivity, mechanism-of-action, and drug-indication retrieval. It returns the
shared bioinformatics record envelope so Codex app surfaces can render cards,
hover panels, clickable ChEMBL links, structure previews, and bounded tables
without understanding raw ChEMBL fields.

## Tools

- `chembl_molecule_lookup`: exact molecule lookup by ChEMBL molecule ID, such as
  `CHEMBL25`.
- `chembl_molecule_search`: text search across ChEMBL molecules, such as
  `imatinib`.
- `chembl_target_lookup`: exact target lookup by ChEMBL target ID, such as
  `CHEMBL1824`.
- `chembl_assay_lookup`: exact assay lookup by ChEMBL assay ID, such as
  `CHEMBL1217643`, with BAO format, organism, target, document, confidence,
  parameters, and classifications when ChEMBL returns them.
- `chembl_document_lookup`: exact source-document lookup by ChEMBL document ID,
  such as `CHEMBL1212834`, with title, authors, journal, year, PMID, DOI,
  abstract, and PubMed/DOI/ChEMBL links when ChEMBL returns them.
- `chembl_activity_search`: bounded ChEMBL activity rows for a molecule, target,
  or molecule-target pair, optionally filtered by `standard_type`.
- `chembl_mechanism_search`: bounded mechanism-of-action rows for a molecule,
  target, or pair.
- `chembl_drug_indications`: bounded drug-indication rows for a molecule,
  including EFO/HPO terms, MeSH terms, maximum indication phase, and evidence
  references such as ClinicalTrials, ATC, or DailyMed links when ChEMBL returns
  them.
- `chembl_status`: local capability inventory and optional API status check.

## Front-end Contract

All retrieval tools return `structuredContent.records[]` with stable fields from
`schemas/record.schema.json`.

- Molecules use `display.component = "compound"` and include
  `chemical_structure`, `table`, and `xref_groups` previews.
- Targets use `display.component = "protein"` and include component table and
  grouped cross-reference previews.
- Assays, activities, mechanisms, and drug indications use
  `display.component = "dataset"` with bounded table previews and clickable
  molecule, target, assay, disease term, document, ontology, or reference links.
- Documents use `display.component = "citation"` with citation metadata,
  abstract text previews, and grouped ChEMBL/PubMed/DOI links.

The MCP owns API URLs and browser URLs. Front ends should prefer
`display.primary_url`, then `record.url`, then `display.actions[]`.

## Environment

- `CHEMBL_REST_BASE_URL`: override the REST API base URL.
- `CHEMBL_WEBSITE_BASE_URL`: override the ChEMBL website base URL.
- `CHEMBL_CONTACT`: optional contact string for the User-Agent.
- `CHEMBL_TOOL`: optional tool name for the User-Agent.

The default REST source is `https://www.ebi.ac.uk/chembl/api/data`.
