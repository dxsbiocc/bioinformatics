# KEGG MCP Operations

The KEGG MCP server wraps the official KEGG REST API as read-only tools that
return the shared `bioinformatics.record.v1` front-end contract.

## Tool Set

- `kegg_status`: local configuration, available tools, preview kinds, and an
  optional `info/kegg` health check.
- `kegg_parameter_domains`: searchable parameter domains derived from the KEGG
  tool JSON Schemas.
- `kegg_resolve_context`: dynamic parameter context discovery for KEGG
  databases, organism codes, pathway map IDs, and pathway-coloring inputs.
- `kegg_info`: database metadata from `info/<database>`.
- `kegg_list`: entry lists from `list/<database>[/<option>]`.
- `kegg_find`: text or chemical search from
  `find/<database>/<query>[/<option>]`.
- `kegg_get`: entry retrieval from `get/<dbentries>[/<option>]`.
- `kegg_conv`: identifier conversion from
  `conv/<target_db>/<source_db_or_entries>`.
- `kegg_link`: relationship mapping from
  `link/<target_db>/<source_db_or_entries>[/<option>]`.
- `kegg_ddi`: drug-drug interaction rows from `ddi/<drug_ids>[/<target>]`.
- `kegg_color_pathway_url`: generate an official KEGG
  `show_pathway?map=<mapid>&multi_query=<dataset>` URL from KEGG identifiers
  and color specifications.
- `kegg_color_pathway_from_table`: generate the same colored pathway record
  from analysis rows that already contain KEGG IDs and numeric values such as
  `log2fc` and `padj`.

## Front-End Contract

Each data-fetching tool returns `structuredContent.records` where possible.
Records include:

- stable IDs such as `KEGG:hsa:10458` or `KEGG:C00002`
- `url`, `display.primary_url`, and clickable `display.actions`
- `display.hover.fields` for quick inspection
- previews using existing renderer kinds: `table`, `xref_groups`, `text`,
  `sequence`, `chemical_structure`, `download_manifest`, and `network`

The MCP does not require the front end to know every KEGG field. It maps common
KEGG entries onto existing components such as `pathway`, `gene`, `compound`,
`protein`, `database`, `identifier_conversion`, `linkset`, and `dataset`.

Dynamic context responses use `contexts` rows with `parameter_name`, `value`,
`label`, `description`, `url`, `metadata`, and `display` fields. This lets a
front end render candidate organism/pathway/coloring values as generic
selectable rows while still preserving real KEGG entry, REST, or documentation
links.

Colored pathway tools return `record_type: "kegg_colored_pathway"` with:

- `display.actions[0]` pointing to the official KEGG colored pathway page
- `data.multi_query` preserving the exact KEGG Mapper Color textarea payload
- a `table` preview containing `kegg_id`, color fields, labels, and source
  values for front-end inspection
- a `text` preview containing the raw `multi_query` payload for reproducibility

## Usage Notes

KEGG REST is intended for academic use and should be called at no more than
three requests per second. The client defaults to 3 requests/second and exposes
the configured rate in `kegg_status`.

For pathway coloring, pass KEGG identifiers such as `hsa:7157`, `K00844`,
`3.1.3.9`, `C00031`, `G00001`, or `D00564`. The MCP intentionally does not
resolve arbitrary gene symbols to KEGG gene IDs before coloring.

Use `kegg_resolve_context` before pathway work when the map ID or organism code
is uncertain. For example, `context_type: "pathways"`, `organism: "hsa"`, and
`query: "cell cycle"` returns `hsa04110` candidates plus recommended
`kegg_get` and `kegg_color_pathway_url` calls. Use `context_type: "coloring"`
to retrieve the accepted KEGG ID and color-column hints without making a
network request.
