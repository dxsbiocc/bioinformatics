# PubChem MCP Server

This server exposes a compact, metadata-first subset of the official PubChem PUG
REST API. It returns the shared bioinformatics record envelope so Codex app
surfaces can render compound cards, structure previews, assay summaries,
substance metadata, hover panels, and user-openable PubChem links without
parsing raw PubChem payloads.

## Tools

- `pubchem_compound_lookup`: exact compound lookup by CID or name, such as
  `2244` or `aspirin`.
- `pubchem_compound_search`: resolve a compound name or synonym to CIDs and
  hydrate matching compounds.
- `pubchem_assay_summary`: BioAssay summary lookup by AID, such as `1706`.
- `pubchem_substance_lookup`: Substance lookup by SID, such as `4594`.
- `pubchem_status`: local capability inventory and optional API check.

## Front-end Contract

All retrieval tools return `structuredContent.records[]` with stable fields from
`schemas/record.schema.json`.

- Compound records use `display.component = "compound"` and include
  `chemical_structure`, property `table`, description/synonym tables, and
  `xref_groups` previews.
- Assay and substance records use `display.component = "dataset"` with bounded
  `table` previews, grouped cross-reference previews, and PubChem browser/API
  links.

The MCP owns URL construction. Front ends should prefer `display.primary_url`,
then `record.url`, then `display.actions[]`.

## Environment

- `PUBCHEM_PUG_BASE_URL`: override the PUG REST base URL.
- `PUBCHEM_WEBSITE_BASE_URL`: override the PubChem website base URL.
- `PUBCHEM_CONTACT`: optional contact string for the User-Agent.
- `PUBCHEM_TOOL`: optional tool name for the User-Agent.

The default PUG REST source is
`https://pubchem.ncbi.nlm.nih.gov/rest/pug`.
