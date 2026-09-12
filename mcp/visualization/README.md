# Omics Visualization MCP

This local MCP server wraps the Bioinformatics omics visualization fast-route
scripts. It profiles an existing CSV/TSV result table, scores template
contracts from `skills/omics-visualization/references/template_contracts.json`,
and returns app-renderable recommendation records.

## Tools

- `omics_visualization_route` profiles a result table and returns scored
  template recommendations, role mappings, risks, and next steps.
- `omics_visualization_contract_coverage` validates fast-route contracts
  against the full visualization catalog and reports family-level coverage.
- `omics_visualization_status` reports script availability, frontend record
  hints, and optional contract coverage.

The server is metadata-only. It does not render plots, install R packages, or
download remote data.
