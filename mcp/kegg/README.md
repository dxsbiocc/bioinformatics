# KEGG MCP

This MCP server wraps the public KEGG REST API in metadata-first tools that
return the shared `bioinformatics.record.v1` envelope used by the plugin.

## Tools

- `kegg_status`: report configured base URLs, tools, preview kinds, and optional
  network health.
- `kegg_parameter_domains`: search parameter domains from the JSON Schemas for
  all KEGG tools.
- `kegg_info`: call `info/<database>`.
- `kegg_list`: call `list/<database>[/<option>]`.
- `kegg_find`: call `find/<database>/<query>[/<option>]`.
- `kegg_get`: call `get/<dbentries>[/<option>]` and return flat-file, FASTA, or
  downloadable resource records.
- `kegg_conv`: call `conv/<target_db>/<source_db_or_entries>`.
- `kegg_link`: call `link/<target_db>/<source_db_or_entries>[/<option>]`.
- `kegg_ddi`: call `ddi/<drug_ids>[/<target>]`.
- `kegg_color_pathway_url`: generate an official KEGG colored pathway URL from
  KEGG identifiers and color specifications.
- `kegg_color_pathway_from_table`: generate a colored pathway URL from analysis
  rows that already contain KEGG IDs and numeric values.

The server keeps REST results compatible with the front-end contract by
including stable identifiers, KEGG entry URLs, REST URLs, hover metadata,
clickable actions, and preview hints such as tables, xref groups, sequences,
chemical structures, download manifests, and relationship networks.

Pathway coloring records also preserve the exact `multi_query` text that KEGG
Mapper Color accepts and expose the generated `show_pathway` URL as the primary
front-end action.

## Environment

- `KEGG_REST_BASE_URL`: defaults to `https://rest.kegg.jp`.
- `KEGG_WEBSITE_BASE_URL`: defaults to `https://www.kegg.jp`.
- `KEGG_CONTACT`: optional contact string included in the User-Agent.
- `KEGG_TOOL`: optional tool name included in the User-Agent.
- `KEGG_REQUESTS_PER_SECOND`: defaults to `3` and is capped at `3`.

KEGG REST is intended for academic use and should be called at no more than
three requests per second. Check KEGG's current license terms before using the
service in non-academic or redistributed workflows.
