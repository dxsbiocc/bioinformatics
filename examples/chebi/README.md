# ChEBI MCP Examples

List tools:

```bash
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n' \
  | python3 mcp/chebi/server.py
```

Look up caffeine:

```bash
printf '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"chebi_compound_lookup","arguments":{"chebi_id":"CHEBI:27732"}}}\n' \
  | python3 mcp/chebi/server.py
```

Search compounds:

```bash
printf '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"chebi_compound_search","arguments":{"query":"caffeine","max_results":3}}}\n' \
  | python3 mcp/chebi/server.py
```

Inspect ontology parents:

```bash
printf '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"chebi_ontology_parents","arguments":{"chebi_id":"CHEBI:27732","max_results":5}}}\n' \
  | python3 mcp/chebi/server.py
```
