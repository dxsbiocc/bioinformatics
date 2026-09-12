# ChEMBL MCP Examples

Example tool calls for the `chembl` MCP server:

```json
{"name":"chembl_molecule_lookup","arguments":{"molecule_chembl_id":"CHEMBL25"}}
```

```json
{"name":"chembl_molecule_search","arguments":{"query":"imatinib","max_results":3}}
```

```json
{"name":"chembl_target_lookup","arguments":{"target_chembl_id":"CHEMBL1824"}}
```

```json
{"name":"chembl_assay_lookup","arguments":{"assay_chembl_id":"CHEMBL1217643"}}
```

```json
{"name":"chembl_document_lookup","arguments":{"document_chembl_id":"CHEMBL1212834"}}
```

```json
{"name":"chembl_activity_search","arguments":{"molecule_chembl_id":"CHEMBL25","max_results":5}}
```

```json
{"name":"chembl_mechanism_search","arguments":{"molecule_chembl_id":"CHEMBL25","max_results":5}}
```

```json
{"name":"chembl_drug_indications","arguments":{"molecule_chembl_id":"CHEMBL25","max_results":5}}
```

Each result returns `structuredContent.records[]` for app rendering. Molecule
records include `compound` display hints and `chemical_structure` previews;
assay, activity, mechanism, and drug-indication results include dataset tables
with browser/API links and grouped cross-reference previews; document results
include citation cards with PubMed/DOI links and abstract previews.
