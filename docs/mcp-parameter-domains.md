# MCP Parameter Domain Discovery

Every MCP server in this plugin exposes a read-only parameter-domain search
tool named `<server>_parameter_domains`, for example:

- `ncbi_parameter_domains`
- `uniprot_parameter_domains`
- `cbioportal_parameter_domains`
- `string_parameter_domains`
- `omics_visualization_parameter_domains`

These tools make each server's callable parameter space discoverable through
the same JSON-RPC/MCP `tools/list` and `tools/call` flow used for normal tools.
They derive their results from the server's existing `inputSchema`, so they
stay aligned with the real callable interface.

## Inputs

All parameter-domain tools share the same input schema:

- `query`: optional text search over tool names, titles, descriptions,
  parameter names, parameter descriptions, and enum values.
- `tool_name`: optional exact or partial tool-name filter.
- `parameter_name`: optional exact or partial parameter-name filter.
- `domain_type`: optional domain filter. Supported values are `enum`,
  `boolean`, `integer_range`, `number_range`, `string`, `array`, `object`,
  `one_of`, and `all`.
- `include_status_tools`: include status and parameter-domain tools. Defaults
  to `false`.
- `include_schema`: include the original JSON Schema fragment for each matched
  parameter. Defaults to `false`.
- `max_results`: bounded result count, default `100`, maximum `500`.

## Output

The response uses `schema_version:
bioinformatics.parameter_domains.v1` and includes:

- `domains`: flat matched parameter-domain rows.
- `tools`: tool-level summaries with matched parameters.
- `searched_tools`: tools considered after filtering.
- `usage_hints`: generic guidance for enums, numeric bounds, open string IDs,
  and diagnostics.

Each domain row includes:

- `tool_name`
- `parameter_name`
- `required`
- `domain_type`
- `domain_source`
- `description`
- `default` when present
- `enum` for closed values
- `minimum`/`maximum` for numeric ranges
- `items` for arrays
- `dynamic_value_hint` for identifier-like, query-like, date-like, or path-like
  open values

## Agent Usage

Agents should call a server's parameter-domain tool before constructing calls
when they are uncertain about a parameter name, enum value, numeric bound, or
whether a value is a closed domain or an open identifier.

The discovery tool does not replace database-specific search or lookup tools.
For open string identifiers such as accessions, profile IDs, sample-list IDs,
study IDs, assay IDs, or local paths, agents should use the same MCP server's
search/list/lookup/status tools first when the exact value is unknown.

## Dynamic Context Tools

Some databases also expose `<server>_resolve_context` tools. These complement
parameter-domain discovery when a parameter value is not a closed enum and must
be resolved from live database context.

Current dynamic context tools:

- `ncbi_resolve_context`: resolves common Entrez databases, PubMed IDs,
  GEO/SRA/BioProject/BioSample/Gene/Taxonomy identifier candidates, real NCBI
  browser links, and recommended follow-up calls.
- `uniprot_resolve_context`: resolves UniProt accession candidates, organism
  and reviewed filters, feature-type hints, cross-reference hints, and
  downstream AlphaFold/RCSB/STRING/literature calls.
- `string_resolve_context`: resolves STRING identifier mappings, species
  defaults, score-field hints, network URLs, and mapping/interaction calls.
- `rcsb_resolve_context`: resolves RCSB PDB search hits or entry IDs,
  structure/download/FASTA hints, RCSB structure URLs, and lookup/FASTA calls.
- `reactome_resolve_context`: resolves Reactome pathway search hits, stable
  IDs, species/resource hints, identifier-to-pathway mapping results, browser
  URLs, and pathway lookup calls.
- `quickgo_resolve_context`: resolves GO term search hits, GO IDs, annotation
  evidence rows, ECO evidence-code hints, TaxID filters, and term lookup calls.
- `chembl_resolve_context`: resolves ChEMBL molecule, target, assay, document,
  and activity-filter context with real ChEMBL URLs and follow-up calls for
  activity, mechanism, indication, UniProt, and literature workflows.
- `ensembl_resolve_context`: resolves Ensembl stable IDs, xrefs, region
  overlap candidates, variant IDs, species hints, feature-type hints, and
  lookup/xref/variation calls.
- `clinvar_resolve_context`: resolves ClinVar VCV/numeric identifiers, variant
  search candidates, clinical-significance hints, gene context, source URLs,
  and variant lookup calls.
- `gnomad_resolve_context`: resolves gnomAD variant IDs, Ensembl gene IDs,
  dataset IDs, reference-genome hints, browser URLs, frequency/constraint
  records, and gnomAD/Ensembl/ClinVar follow-up calls.
- `gwas_resolve_context`: resolves GWAS Catalog rsIDs, mapped-gene evidence,
  trait evidence, PubMed/EFO-linked evidence records, GWAS URLs, and
  GWAS/Ensembl/ClinVar/Open Targets follow-up calls.
- `opentargets_resolve_context`: resolves Open Targets target and disease
  search hits, Ensembl/EFO/MONDO identifiers, browser URLs, association
  evidence entry points, and Open Targets/Ensembl/EFO follow-up calls.
- `pubchem_resolve_context`: resolves PubChem compound names/CIDs, BioAssay
  AIDs, Substance SIDs, browser URLs, chemical preview metadata, and
  PubChem/ChEMBL/ChEBI/NCBI follow-up calls.
- `chebi_resolve_context`: resolves ChEBI text hits, CHEBI IDs, optional
  ontology parent/child context, browser/API URLs, chemical preview metadata,
  and ChEBI/PubChem follow-up calls.
- `cbioportal_resolve_context`: resolves study IDs, molecular profile IDs,
  sample-list IDs, clinical attributes, profile/sample-list compatibility, and
  recommended cBioPortal fetch calls.
- `kegg_resolve_context`: resolves KEGG database names, organism codes,
  pathway map IDs, KEGG Color URL input hints, and recommended KEGG REST or
  pathway-coloring calls.

These tools return `context_schema_version:
bioinformatics.dynamic_context.v1`. The front-end contract is described by
`schemas/dynamic-context.schema.json`, documented in
`docs/frontend-record-rendering.md`, and typed in `types/record.ts`.

The response includes:

- `contexts`: generic rows containing `parameter_name`, `value`, `label`,
  `description`, `url`, `metadata`, and a lightweight `display` object for app
  hover/actions.
- `entities`: compact summaries for database-backed candidates. Some tools also
  retain compatibility aliases such as `accessions`, `pathways`, `variants`,
  `studies`, `profiles`, `sample_lists`, `clinical_attributes`, `databases`,
  and `organisms`.
- `recommended_calls`: MCP tool names plus argument seeds and any remaining
  required inputs.
- `diagnostics`: recoverable compatibility or no-match messages when the
  requested context is invalid or incomplete.
- `source`/`sources`: real API or documentation URLs used to resolve the
  candidates.

Agents should call parameter-domain tools when they are unsure about parameter
names, enum values, or numeric bounds. They should call dynamic context tools
when they need database-backed identifiers or compatibility checks before
calling a fetch tool.

## Live Smoke Tests

Most MCP tests use fake clients and never call public APIs. To check that the
dynamic context tools still match live upstream APIs, run the optional smoke
suite explicitly:

```bash
BIOINFORMATICS_LIVE_MCP_SMOKE=1 python3 -B -m unittest tests.test_live_mcp_smoke -v
```

Limit the run to one or more servers with a comma-separated filter:

```bash
BIOINFORMATICS_LIVE_MCP_SMOKE=1 \
BIOINFORMATICS_LIVE_MCP_SERVERS=pubchem,chebi \
python3 -B -m unittest tests.test_live_mcp_smoke -v
```

The smoke suite currently covers dynamic context resolution for NCBI, UniProt,
STRING, RCSB PDB, Reactome, QuickGO, ChEMBL, Ensembl, ClinVar, Open Targets,
GWAS Catalog, gnomAD, PubChem, ChEBI, cBioPortal, and KEGG. It verifies the
shared `bioinformatics.dynamic_context.v1` contract, entity summaries, real
URLs, and recommended follow-up calls. Keep it outside default CI because
upstream availability, network policy, and rate limits are external state.
