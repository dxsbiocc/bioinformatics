# ChEBI MCP Server

This server exposes a compact, metadata-first subset of the EBI ChEBI public
backend API. It returns the shared bioinformatics record envelope so Codex app
surfaces can render compound cards, chemical structure previews, synonym/xref
tables, citation lists, ontology relation networks, hover panels, and
user-openable ChEBI links without parsing raw ChEBI payloads.

## Tools

- `chebi_compound_search`: search ChEBI compounds by text, such as `caffeine`.
- `chebi_compound_lookup`: exact compound lookup by ChEBI ID, such as
  `CHEBI:27732`.
- `chebi_ontology_children`: list incoming child relations for a ChEBI term.
- `chebi_ontology_parents`: list outgoing parent/role relations for a ChEBI
  term.
- `chebi_status`: local capability inventory and optional API check.

## Front-end Contract

All retrieval tools return `structuredContent.records[]` with stable fields from
`schemas/record.schema.json`.

- Compound records use `display.component = "compound"` and include
  `chemical_structure`, detail `table`, `xref_groups`, optional
  `citation_list`, and `text` previews.
- Ontology relation records use `display.component = "ontology_term"` and
  include `table` and `network` previews.

The MCP owns URL construction. Front ends should prefer `display.primary_url`,
then `record.url`, then `display.actions[]`.

## Environment

- `CHEBI_API_BASE_URL`: override the EBI API base URL.
- `CHEBI_WEBSITE_BASE_URL`: override the ChEBI website base URL.
- `CHEBI_CONTACT`: optional contact string for the User-Agent.
- `CHEBI_TOOL`: optional tool name for the User-Agent.

The default API source is `https://www.ebi.ac.uk` with public routes under
`/chebi/backend/api/public/`.
