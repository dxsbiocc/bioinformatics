# Changelog

## Unreleased - Continuous Integration - 2026-09-14

### Added

- GitHub Actions CI workflow (`.github/workflows/ci.yml`) running on every
  push/PR to `main`: installs `httpx[http2]`, byte-compiles `mcp/`, and runs
  the full `unittest` suite across Python 3.10, 3.11, and 3.12. The gated
  live-API smoke tests stay off by default, so CI never depends on upstream
  database availability.

## Unreleased - HTTP Client Migration - 2026-09-14

### Changed

- Every MCP server's outbound HTTP now goes through
  [httpx](https://www.python-httpx.org/) instead of the standard library's
  `urllib`, using one lazily created, reused `httpx.Client(http2=True)` per
  server process for connection reuse and HTTP/2 support. This is the plugin's
  first third-party Python dependency (`httpx[http2]`); see
  [pyproject.toml](../pyproject.toml).
- Each client's opener test-injection seam now passes an `httpx.Request`
  instead of a `urllib.request.Request`.
- Retry loops now catch only `httpx.RequestError` (genuine transport
  failures: timeout, connection reset) instead of `urllib.error.URLError`,
  which in urllib also silently retried on HTTP status errors since
  `HTTPError` subclasses `URLError`. httpx separates these into
  `HTTPStatusError`, so 4xx/5xx responses now propagate immediately instead
  of being retried.

## Unreleased - Visualization Routing Fast Path - 2026-09-12

### Added

- Omics visualization template contracts for common result-table shapes,
  using generic entity/feature/category roles instead of gene-only routing.
- Dependency-free `route_template.py` preview router that profiles CSV/TSV
  tables, returns scored template recommendations, and explains matched data
  shapes, roles, and risks.
- Dependency-free `qa_single_plot.py` artifact QA for single PNG/SVG outputs.
- Dependency-free `validate_template_contracts.py` check that keeps contract
  template ids, source paths, and preview paths aligned with the visualization
  catalog, reports contract coverage by family, and supports a coverage floor
  for future CI use.
- Regression tests for one-to-many routing, exact template-id override,
  volcano routing, flow/tree/time/composition routing, contract validation,
  and PNG/SVG artifact checks.
- Local omics visualization MCP server with template routing, contract
  coverage, and status tools that return app-renderable dataset/table records.
- Shared parameter-domain discovery for every MCP server through
  `<server>_parameter_domains` tools. These tools search existing input
  schemas for enum values, boolean flags, numeric ranges, array item domains,
  required fields, defaults, descriptions, and dynamic-value hints so agents can
  construct better calls before invoking database fetch tools.
- KEGG MCP server wrapping the official REST operations `info`, `list`, `find`,
  `get`, `conv`, `link`, and `ddi`, with front-end-compatible pathway, gene,
  compound, database, linkset, identifier-conversion, sequence, and downloadable
  resource records plus KEGG entry links, REST provenance URLs, preview hints,
  parameter-domain discovery, and 3 requests/second pacing metadata.
- KEGG pathway coloring MCP tools that generate official `show_pathway`
  colored-map URLs from explicit KEGG ID/color items or differential-style
  result-table rows, returning clickable pathway records with preserved
  `multi_query` text and table previews for front-end interaction.
- Dynamic parameter context tools for cBioPortal and KEGG. `cbioportal_resolve_context`
  resolves study/profile/sample-list/clinical-attribute candidates, validates
  profile and sample-list study compatibility, and returns recommended fetch
  calls. `kegg_resolve_context` resolves KEGG databases, organism codes,
  pathway map IDs, pathway-coloring hints, real source URLs, and recommended
  KEGG REST or colored-pathway calls.
- Second dynamic-context batch for NCBI, UniProt, STRING, and RCSB PDB.
  `ncbi_resolve_context`, `uniprot_resolve_context`,
  `string_resolve_context`, and `rcsb_resolve_context` expose database-backed
  identifier candidates, browser URLs, cross-database hints, and recommended
  follow-up calls using the same front-end-compatible `contexts` contract.
- Third dynamic-context batch for Reactome, QuickGO, ChEMBL, Ensembl, and
  ClinVar. `reactome_resolve_context`, `quickgo_resolve_context`,
  `chembl_resolve_context`, `ensembl_resolve_context`, and
  `clinvar_resolve_context` resolve pathway, ontology, compound/target,
  genomic-feature, and variant parameter context with real source URLs,
  display metadata, and recommended follow-up calls.
- Fourth dynamic-context batch for Open Targets, GWAS Catalog, gnomAD,
  PubChem, and ChEBI. `opentargets_resolve_context`, `gwas_resolve_context`,
  `gnomad_resolve_context`, `pubchem_resolve_context`, and
  `chebi_resolve_context` resolve target/disease, variant/gene/trait,
  frequency/constraint, compound/assay/substance, and ontology/compound
  parameter context with entity-first ordering, real browser URLs, hover-ready
  display metadata, and same-server recommended calls before cross-database
  follow-ups.
- Optional live MCP smoke tests for the latest dynamic-context batch, gated by
  `BIOINFORMATICS_LIVE_MCP_SMOKE=1` with server filtering through
  `BIOINFORMATICS_LIVE_MCP_SERVERS`, so real API compatibility can be checked
  without adding network dependence to default test runs.
- Expanded live MCP smoke coverage across NCBI, UniProt, STRING, RCSB PDB,
  Reactome, QuickGO, ChEMBL, Ensembl, ClinVar, Open Targets, GWAS Catalog,
  gnomAD, PubChem, ChEBI, cBioPortal, and KEGG, including URL-preservation
  assertions and transient-network skips for flaky upstream API timeouts.
- Shared dynamic-context helper module for entity-first context ordering,
  same-server recommended-call priority, duplicate recommended-call removal,
  and compact entity summaries across NCBI, UniProt, STRING, RCSB PDB,
  Reactome, QuickGO, ChEMBL, Ensembl, ClinVar, Open Targets, GWAS Catalog,
  gnomAD, PubChem, and ChEBI. RCSB keeps its historical tool/argument-only
  dedupe rule through an explicit helper option.
- Shared dynamic-context response builder for Open Targets, GWAS Catalog,
  gnomAD, PubChem, and ChEBI, keeping `contexts`, `entities`,
  `recommended_calls`, `source`, `sources`, `provenance`, and optional `raw`
  fields consistent for front-end consumption.
- Extended the shared dynamic-context response builder across NCBI, UniProt,
  STRING, RCSB PDB, Reactome, QuickGO, ChEMBL, Ensembl, ClinVar, cBioPortal,
  and KEGG while preserving legacy summary aliases such as `pathways`,
  `variants`, `features`, `studies`, and `databases`.
- Added a front-end dynamic-context contract with
  `schemas/dynamic-context.schema.json`, TypeScript interfaces and helpers in
  `types/record.ts`, and rendering guidance for `contexts`, `entities`,
  `recommended_calls`, diagnostics, hover payloads, and URL routing.
- First broad contract-coverage batch for common bar, boxplot, line, scatter,
  heatmap, Sankey, tree, sunburst, and radar templates, raising routed catalog
  coverage to 62 of 152 templates without gene- or project-specific rules.
- Second broad contract-coverage batch covering every bar, boxplot, line, pie,
  scatter, tree, and sunburst catalog entry, raising routed catalog coverage to
  123 of 152 templates through generic data-shape contracts.
- Final broad contract-coverage batch covering graph, specialized heatmap, and
  ideogram templates, raising routed catalog coverage to all 152 templates
  through reusable edge-list, matrix, mutation-event, and genomic-interval
  contracts.
- Sidecar-aware visualization routing for recognized companion files such as
  `nodes.tsv`, `links.tsv`, `rowInfo.tsv`, `colInfo.tsv`, `enrichment.tsv`,
  `cytoband.tsv`, `domains.tsv`, and `karyotype.tsv`.
- Sidecar alignment checks that compare reusable ID relationships such as
  matrix rows to `rowInfo.tsv`, matrix columns to `colInfo.tsv`, and node IDs
  to `links.tsv`/`edges.tsv` endpoints.
- Plugin source hygiene regression test that blocks local transient artifacts
  such as system cache files, R plotting scratch output, and top-level result
  folders from entering the plugin package.
- MCP inventory contract regression test that keeps `.mcp.json`, server
  entrypoints, `tools/list`, `TOOL_HANDLERS`, primary status `available_tools`,
  parameter-domain tools, and manifest capability coverage aligned before
  sealing plugin updates.

### Changed

- Omics visualization docs now route preview/common tasks through the fast
  contract layer before falling back to full catalog review for low-confidence,
  novel, or publication-critical figures.
- Visualization routing now recognizes generic second-category, component,
  uncertainty, paired-unit, ranking, enrichment-term-grid, hierarchy-area, and
  parallel-sets table shapes while keeping upstream statistical analysis out of
  the MCP layer.
- Visualization routing now recognizes average-abundance/effect MA tables,
  ternary non-negative components, supplied embedding coordinates, interval
  timelines, multi-root hierarchies, classification enrichment trees, SVG/icon
  marks, and per-node colors as reusable roles or shapes.
- Visualization routing now recognizes generic genomic intervals, cytobands,
  coverage tracks, synteny blocks, protein mutation lollipop tables, OncoPrint
  alteration events, mutation-energy matrices, and graph edge-list layouts
  without adding gene-, disease-, or project-specific fast routes.
- Tightened broad shape inference so significance/effect/correlation columns
  are not reused as ordinary y values, part-to-whole contracts do not capture
  x-y point clouds, and multi-axis categorical count tables stay routed to
  parallel sets instead of nested pies.
- Tightened group-split matrix inference so MA-style statistical summary
  tables remain routed to MA plots rather than circular heatmaps.
- Visualization MCP route responses now include discovered sidecar files,
  sidecar-derived shapes, and sidecar role mappings when companion files are
  present; this is still metadata-only routing and does not compute upstream
  statistics.
- Sidecar-dependent template recommendations are now confidence-capped and
  annotated with risks when companion identifiers do not align with the main
  table; the router reports the issue but does not silently filter, reorder, or
  repair user data.
- cBioPortal dynamic context now tags study, profile, sample-list, and clinical
  attribute contexts with entity groups and prioritizes them ahead of static
  enum hints, so small `max_results` windows still expose clickable front-end
  entities.

## 0.1.0 - NCBI MCP Baseline - 2026-09-08

This baseline freezes the first stable Bioinformatics plugin shape around the
NCBI MCP server, UniProt MCP server, and shared app-renderable record contract.

### Added

- NCBI MCP server with 21 metadata-first tools covering PubMed, PMC ID
  conversion, Gene, Taxonomy, GEO, BioProject, BioSample, SRA, common Entrez
  links, GEO/SRA download plans, omics sample sheets, local runtime status, and
  server status.
- NCBI records include shared `display.previews` hints for PubMed citation
  lists, GEO/SRA download manifests, sample-sheet tables, grouped Entrez
  cross-references, SRA run tables, and runtime text summaries.
- bioRxiv/medRxiv MCP server with preprint DOI lookup, bounded preprint
  interval retrieval, formal-publication linkage lookup, publication-link
  interval retrieval, DOI/JATS/published-article links, abstracts, version and
  category metadata, and shared `citation` record envelopes.
- RNAcentral MCP server with URS entry lookup, text search, cross-reference
  retrieval, RNA sequence previews, species/TaxID metadata, source database
  groups, xref tables, browser/API links, and shared
  `genomic_feature`/`identifier_conversion` record envelopes.
- EFO MCP server with OLS4-backed ontology term lookup, text search, child
  and descendant traversal, definitions, synonyms, obsolete/replacement
  metadata, grouped cross-references, relation-network previews, browser/API
  links, and shared `ontology_term` record envelopes.
- UniProt MCP server with protein search, accession lookup, FASTA retrieval,
  status, and shared `protein` record envelopes.
- AlphaFold MCP server with UniProt accession lookup, canonical/isoform model
  handling, confidence metadata, structure-file URLs, and shared
  `protein_structure` record envelopes.
- STRING MCP server with identifier mapping and protein interaction lookup,
  returning shared `identifier_conversion` and `protein_network` record
  envelopes.
- STRING interaction records include `network` and `table` previews with
  app-renderable nodes, edges, combined scores, evidence-channel scores, and
  stable STRING browser URLs.
- RCSB PDB MCP server with structure lookup, full-text search, FASTA retrieval,
  polymer/ligand summaries, structure-file URLs, and shared
  `protein_structure`/`protein` record envelopes.
- RCSB structure records include `structure_3d`, `download_manifest`, `table`,
  and citation-list previews when the upstream response contains those data.
- Reactome MCP server with pathway/event lookup, pathway search, UniProt or
  other external identifier-to-pathway mapping, participants, stable browser/API
  links, and shared `pathway` record envelopes.
- Reactome pathway records include `network`, `table`, `citation_list`, and
  `xref_groups` previews for app-side pathway cards, graph panels, hover cards,
  and detail panes.
- Ensembl MCP server with stable ID lookup, xref retrieval, region overlap, and
  variation lookup backed by Ensembl REST endpoints.
- Ensembl records include shared `gene`, `genomic_feature`, `variant`, and
  `identifier_conversion` envelopes with browser/API URLs, transcript or
  mapping tables, grouped cross-reference previews, and bounded result counts.
- ClinVar MCP server with NLM Clinical Tables search, NCBI E-utilities ClinVar
  lookup, clinical significance, review status, gene/dbSNP links, locations,
  supporting submissions, and shared `variant` record envelopes.
- gnomAD MCP server with GraphQL-backed variant frequency lookup, gene
  constraint lookup, gnomAD browser/API links, population-frequency tables,
  transcript-consequence tables, constraint tables, and shared `variant`/`gene`
  record envelopes.
- GWAS Catalog MCP server with REST API v2-backed variant, mapped-gene, and
  trait association evidence lookup, GWAS study tables, PubMed evidence links,
  EFO trait links, SNP links, and shared `variant`/`gene`/`dataset` record
  envelopes.
- Open Targets MCP server with GraphQL-backed target lookup, disease lookup,
  and target/disease search, returning target-disease association scores,
  datasource/datatype evidence score tables, ontology cross-references,
  browser/API links, and shared `gene`/`dataset`/`identifier_conversion`
  record envelopes.
- ChEMBL MCP server with REST-backed compound lookup/search, target lookup,
  assay lookup, source-document lookup, activity search, mechanism search,
  drug-indication lookup, molecule properties, chemical structure previews,
  target component tables, assay metadata tables, source-document citation
  records, mechanism references, EFO/HPO and MeSH indication terms, evidence
  links, browser/API links, and shared
  `compound`/`protein`/`citation`/`dataset` record envelopes.
- PubChem MCP server with PUG REST-backed compound lookup/search, BioAssay
  summary lookup, Substance lookup, compound properties, chemical structure
  previews, descriptions, synonyms, assay summary tables, depositor metadata,
  browser/API links, and shared `compound`/`dataset` record envelopes.
- ChEBI MCP server with EBI public backend API-backed compound search, exact
  compound lookup, ontology parent/child traversal, chemical structure previews,
  synonyms, grouped cross-references, citations, biological origins, relation
  network previews, ChEBI browser/API links, and shared
  `compound`/`ontology_term` record envelopes.
- QuickGO MCP server with Gene Ontology term lookup/search, child term
  traversal, annotation evidence search, GO definitions, synonyms, ontology
  relation network previews, evidence tables, PubMed/GO_REF links, and shared
  `ontology_term`/`dataset` record envelopes.
- PRIDE Archive MCP server with proteomics project lookup/search, metadata-only
  file manifest lookup, project descriptions, protocols, organisms,
  instruments, experiment types, PTMs, publication references, HTTPS-mirrored
  file links, and shared `project`/`download_plan` record envelopes.
- BioStudies and ArrayExpress MCP server with study lookup/search,
  metadata-only file manifests, study descriptions, release dates, organisms,
  study types, sample/assay counts, protocols, publication references, external
  repository links, HTTPS file links, and shared `project`/`download_plan`
  record envelopes.
- CELLxGENE Discover MCP server with collection lookup/search, metadata-only
  H5AD asset manifests, collection descriptions, DOI/publication metadata,
  authors, dataset/cell counts, organism/tissue/disease/cell type/assay
  ontology tables, explorer URLs, browser/API links, and shared
  `project`/`download_plan` record envelopes.
- Human Protein Atlas MCP server with Ensembl gene lookup, gene metadata
  search, expression summaries, subcellular localization, antibody evidence,
  cancer prognostic summaries when upstream data is present, UniProt/Ensembl
  cross-reference groups, browser/API links, and shared `gene` record
  envelopes.
- MetaboLights MCP server with exact MTBLS study lookup, EBI Search-backed
  study discovery, metadata-only file manifests, metabolomics study designs,
  assays, protocols, publication references, FTP HTTPS/Globus links, and shared
  `project`/`download_plan` record envelopes.
- HMDB MCP server with unearth/q-backed metabolite, protein, disease, and
  pathway category search, shared `compound`/`protein`/`dataset`/`pathway`
  record envelopes, chemical structure, sequence, table, text, and grouped
  cross-reference previews, HMDB browser links, and explicit Cloudflare
  challenge reporting for restricted non-browser runtimes.
- MGnify MCP server with microbiome/metagenomics study lookup and search,
  sample lookup, biome lookup, BioProject/BioSample links, sample metadata
  tables, biome relationship links, and shared `project`/`sample`/`taxonomy`
  record envelopes.
- ENCODE MCP server with functional genomics experiment lookup/search, file
  lookup, biosample lookup/search, metadata-only experiment file manifests,
  assay/biosample summaries, ENCBS sample cards, GEO cross-references,
  HTTPS/cloud file links, checksums, replicate metadata, and shared
  `project`/`sample`/`download_plan` record envelopes.
- cBioPortal MCP server with cancer genomics study lookup/search, molecular
  profile listing, sample-list listing, HUGO/Entrez-backed mutation table fetch,
  numeric molecular data matrix fetch, discrete copy-number matrix fetch,
  clinical attribute listing, bounded clinical data matrix fetch, OS/DFS-style
  survival row fetch, cohort sample counts, mutation rows, expression/CNA
  heatmap previews, clinical rows, survival-curve preview rows,
  PubMed/cBioPortal links, and shared `project`/`dataset` record envelopes.
- cBioPortal HUGO-symbol molecular fetches now report unresolved symbols and
  cBioPortal fetch HTTP 404 responses as structured warnings with empty
  front-end-compatible dataset records instead of aborting batch runs.
- cBioPortal fetch HTTP 404 and empty-payload warnings now include diagnostics
  that classify missing molecular profiles, missing sample lists,
  profile/sample-list study mismatches, and valid profile/sample contexts with
  unavailable fetch data. The diagnostics are exposed at top level and inside
  each returned record for app-side empty states and hover cards.
- Shared MCP front-end contract assertions cover representative NCBI, UniProt,
  AlphaFold, STRING, RCSB PDB, Reactome, Ensembl, ClinVar, gnomAD, and GWAS
  Catalog, Open Targets, ChEMBL, PubChem, ChEBI, QuickGO, PRIDE, BioStudies/
  ArrayExpress, CELLxGENE, Human Protein Atlas, MetaboLights, HMDB, MGnify,
  ENCODE, and cBioPortal records, including clickable URLs, identifiers, hover
  payloads, actions, metadata rows, badges, detail sections, survival-curve
  rows, heatmap matrices, networks, table previews, grouped cross-references,
  download manifests, citation lists, and text preview hints.
- UniProt detail records include bounded sequence features, feature tracks,
  keywords, comments, literature references, grouped cross-references, and
  search pagination metadata for richer app-side interactions.
- UniProt protein and FASTA records include shared `display.previews` hints for
  sequence, feature-track, AlphaFold/RCSB structure, STRING network,
  citation-list, and cross-reference widgets when backed by upstream
  identifiers.
- Front-end record contract in `schemas/record.schema.json`,
  `types/record.ts`, and `docs/frontend-record-rendering.md`.
- Metadata-only planning tools for GEO and SRA. They return URLs, manifests,
  sample tables, and suggested command strings, but do not download data or run
  shell commands.
- Fixed front-end fixture records under `fixtures/frontend/ncbi/` for renderer
  development without live NCBI requests.
- NCBI examples under `examples/ncbi/` and operational notes under
  `docs/ncbi-mcp-operations.md`.
- UniProt examples under `examples/uniprot/` and server notes under
  `mcp/uniprot/README.md`.
- AlphaFold examples under `examples/alphafold/` and server notes under
  `mcp/alphafold/README.md`.

### Guardrails

- MCP tools own retrieval, normalization, stable identifiers, provenance, and
  URL generation.
- Front-end/app code owns rendering, hover behavior, user-initiated link
  opening, downloads, and command execution.
- Large GEO/SRA transfers must remain explicit user actions.
