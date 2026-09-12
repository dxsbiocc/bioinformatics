# HMDB MCP Examples

List tools:

```bash
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n' \
  | python3 mcp/hmdb/server.py
```

Search metabolites:

```bash
printf '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"hmdb_metabolite_search","arguments":{"query":"serotonin","max_results":3}}}\n' \
  | python3 mcp/hmdb/server.py
```

Search pathways:

```bash
printf '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"hmdb_pathway_search","arguments":{"query":"glycolysis","max_results":3}}}\n' \
  | python3 mcp/hmdb/server.py
```

If HMDB returns a browser challenge in the current runtime, the tool reports that
as an explicit HMDB access error. The record contract and URL rendering are still
covered by offline tests.

