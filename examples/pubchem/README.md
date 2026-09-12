# PubChem MCP Examples

Example tool calls for the `pubchem` MCP server:

```json
{"name":"pubchem_compound_lookup","arguments":{"cid":2244}}
```

```json
{"name":"pubchem_compound_lookup","arguments":{"name":"aspirin","include_synonyms":true}}
```

```json
{"name":"pubchem_compound_search","arguments":{"query":"aspirin","max_results":3}}
```

```json
{"name":"pubchem_assay_summary","arguments":{"aid":1706}}
```

```json
{"name":"pubchem_substance_lookup","arguments":{"sid":4594}}
```

Compound results include `compound` display hints and `chemical_structure`
previews. Assay and substance results use dataset records with PubChem browser
and PUG REST links.
