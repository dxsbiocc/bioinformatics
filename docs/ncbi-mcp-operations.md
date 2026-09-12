# NCBI MCP Operations

The NCBI MCP server is a metadata and planning layer. It should keep API
queries narrow, preserve provenance, and return front-end-compatible records
without performing bulk downloads or workflow execution.

## Stable Surfaces

- `tools/list` exposes the callable MCP tool schema.
- `ncbi_status` exposes the same tool inventory as structured data, grouped by
  literature, omics datasets, entities, Entrez links, runtime, and status.
- `structuredContent.records[]` is the primary UI payload for cards, rows,
  hover previews, and external actions.
- `structuredContent.citations[]` is reserved for PubMed/PMC citation chips and
  bibliography-specific views.
- `records[].display.previews[]` provides optional shared renderer hints for
  PubMed citation lists, GEO/SRA download manifests, sample-sheet tables,
  SRA run tables, grouped cross-references, and runtime text summaries.

## Common Error Cases

- Network failure: report that NCBI could not be reached and keep the original
  query visible in the response or error message.
- No result: return a valid result envelope with `returned: 0`, empty
  domain-specific arrays, and empty `records`.
- Identifier mismatch: keep the requested identifier separate from returned
  identifiers. Do not silently merge different accessions, organisms, assemblies,
  or namespaces.
- NCBI rate limiting: prefer `NCBI_API_KEY` and `NCBI_EMAIL` for sustained use.
  Without an API key the client throttles to the lower public request rate.
- Malformed upstream XML/JSON: keep parse errors in normalized payloads where
  possible, and avoid crashing the MCP boundary for partial SRA/GEO metadata.

## Download Planning

`geo_download_plan` and `sra_download_plan` return planning records only:

- URLs are safe candidates for browser/download buttons after the app checks
  the scheme.
- Download-plan records expose `display.previews[].kind: "download_manifest"`
  for review panes, but this preview is still metadata only.
- SRA Toolkit commands are strings under manifest/run data, not executable
  actions.
- Large transfers require an explicit user request and normal app execution
  guardrails.
- The front end should show `kind: "download"` links as user-initiated actions,
  not automatic transfers.

## Runtime Checks

`tool_runtime_status` inspects command names on `PATH`. By default it only checks
presence. When `check_versions` is true, it runs known version flags for a small
allowlist of common tools and uses a timeout.

The runtime status result is advisory. It should help an agent pick a prepared
environment or explain missing tools, not trigger ad hoc installation by itself.

## Fixture Usage

Use `fixtures/frontend/ncbi/core-records.json` for deterministic front-end
renderer work. It intentionally avoids live NCBI calls while covering citation,
download plan, sample sheet, and runtime status components.
