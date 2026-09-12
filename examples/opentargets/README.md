# Open Targets MCP Examples

Use these examples from Codex through the installed `opentargets` MCP server.

## Target Lookup

```json
{
  "ensembl_id": "ENSG00000141510",
  "max_results": 10
}
```

Call `opentargets_target_lookup` to retrieve TP53, associated diseases, overall
association scores, datasource scores, datatype scores, and Open Targets links.

## Disease Lookup

```json
{
  "efo_id": "MONDO_0004979",
  "max_results": 10
}
```

Call `opentargets_disease_lookup` to retrieve asthma, associated targets,
ontology cross-references, and evidence score tables.

## Search

```json
{
  "query": "TP53",
  "entity_names": ["target", "disease"],
  "max_results": 10
}
```

Call `opentargets_search` to resolve text to clickable target and disease hits.
