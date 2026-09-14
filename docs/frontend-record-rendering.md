# Front-end Record Rendering Contract

This document describes how Codex app surfaces and other front-end consumers
should render bioinformatics MCP results. MCP tools own retrieval, normalization,
stable identifiers, provenance, and URL generation. The application owns visual
rendering, hover behavior, routing, and opening external links.

The machine-readable record schema is `schemas/record.schema.json`. Dynamic
parameter-context responses use `schemas/dynamic-context.schema.json`.
TypeScript consumers can use `types/record.ts`. Deterministic fixture records
remain under `fixtures/frontend/ncbi/core-records.json` for app-side renderer
tests.

## Payload Selection

1. Prefer `structuredContent` from the MCP `tools/call` response.
2. Read `structuredContent.records` as the primary renderable collection.
3. Read `structuredContent.citations` only for inline citation lists or
   bibliography-specific views.
4. Preserve tool-specific fields such as `articles`, `datasets`, `genes`,
   `taxa`, `conversions`, and `linksets` for drill-down views.
5. For dynamic parameter resolution tools where `operation` is
   `resolve_context`, read `structuredContent.contexts` as candidate rows and
   `structuredContent.entities` as compact first-pass cards.
6. Treat `data` and `related` as expandable details, not as the primary display
   contract.

MCP hosts should pass `tools/call.result.structuredContent` to renderers rather
than parsing the fallback JSON string in `content[].text`.

## Dynamic Context Display

`*_resolve_context` tools return `context_schema_version:
bioinformatics.dynamic_context.v1`. These responses are for selecting or
confirming tool arguments before running a database fetch. They are not full
record collections, but they use the same front-end ideas: stable labels, real
URLs, hover payloads, actions, diagnostics, and provenance.

Render a dynamic context result from:

- `contexts[]`: all candidate argument rows. Each row usually includes
  `parameter_name`, `value`, `label`, `description`, `url`, `metadata`, and a
  lightweight `display` object.
- `entities[]`: compact summaries for database-backed candidates. Prefer this
  for the first visible card/list when present.
- Legacy summary aliases such as `accessions`, `pathways`, `variants`,
  `features`, `studies`, `profiles`, `sample_lists`, `clinical_attributes`,
  `databases`, and `organisms`: compatibility fields for older consumers.
- `recommended_calls[]`: suggested next MCP tool calls. Treat these as
  user-confirmable call seeds, not commands to run automatically.
- `diagnostics[]`: recoverable no-match, mismatch, or compatibility messages.
  Render `severity`, `message`, and `suggested_action` when present.
- `source`, `sources`, and `provenance`: API/documentation URLs used to resolve
  the candidates.

Render each `contexts[]` row like a compact record chip/card:

- Use `context.display.hover` for hover cards when present.
- Use `context.display.primary_url`, then `context.url`, then the first
  `context.display.actions[].url` as the click target.
- Open only `http://` and `https://` URLs.
- Show `parameter_name` as the chip label and `value` as the copyable argument.
- Preserve `metadata` for detail panes and filtering.

Recommended calls should show the local tool name first. When `server` is
present, label it as a cross-server suggestion. Front ends should let the user
inspect and edit `arguments` before invoking the call.

## Record Display

Each `records[]` item should be rendered from `record.display` first:

- `display.component`: select the renderer.
- `display.chip_label`: compact label for chips, pills, and table cells.
- `display.icon`: icon token.
- `display.title`: primary visible title.
- `display.subtitle`: secondary visible context.
- `display.description`: optional summary body.
- `display.metadata`: label/value rows for compact detail surfaces.
- `display.badges`: source, identifier, record-type, and context badges.
- `display.actions`: click targets.
- `display.hover`: hover card payload.
- `display.primary_url`: preferred click target.
- `display.sections`: optional detail sections for tabs, accordions, sequence
  tracks, cross-reference groups, lists, or tables.
- `display.previews`: optional high-level preview hints for shared widgets such
  as sequence viewers, structure viewers, network panels, citation lists, and
  cross-reference groups.

Known `display.component` values:

- `citation`: PubMed, ChEMBL source document, bioRxiv/medRxiv preprint,
  publication-linkage, or other literature article chip/card.
- `dataset`: GEO, GWAS trait search, Open Targets disease evidence, HMDB disease search, PubChem BioAssay/Substance, or other omics dataset/evidence-set card/row.
- `compound`: ChEMBL, PubChem, ChEBI, HMDB metabolite, or other small-molecule/compound card/row.
- `protein`: UniProtKB, HMDB protein, or other protein entry/sequence card/row.
- `protein_structure`: AlphaFold DB, RCSB PDB, or other protein structure card/row.
- `protein_network`: STRING or other protein interaction network card/row.
- `pathway`: Reactome, HMDB pathway, or other pathway/event card/row.
- `ontology_term`: QuickGO, GO, ECO, EFO/OLS4, ChEBI ontology relations, or other ontology term card/row.
- `gene`: NCBI Gene, Ensembl gene, gnomAD constraint, GWAS mapped-gene evidence, Open Targets target evidence, Human Protein Atlas expression/evidence, or other gene card/row.
- `genomic_feature`: Ensembl transcript, exon, regulatory, region feature, RNAcentral RNA entry, or other genomic feature card/row.
- `variant`: Ensembl, ClinVar, gnomAD, GWAS Catalog, or other genomic variant card/row.
- `taxonomy`: organism or TaxID card/row.
- `identifier_conversion`: PMID, PMCID, DOI, manuscript ID mapping, RNAcentral external cross-reference grouping, or Open Targets search hit mapping.
- `database`: Entrez database catalog item.
- `linkset`: cross-database Entrez link result.
- `project`: BioProject or other omics project metadata.
- `sample`: BioSample or other omics sample metadata.
- `run`: SRA run, experiment, study, or sequencing-run metadata.
- `download_plan`: metadata-only SRA/GEO download manifest item.
- `sample_sheet`: front-end-ready omics sample metadata table.
- `runtime_status`: local command-line tool availability/version status.

Unknown components should fall back to a generic record card using `title`,
`subtitle`, `description`, `metadata`, `badges`, and `actions`.

## Preview Contract

`display.previews` is the compatibility layer for richer front-end interaction.
It should describe what can be previewed without forcing app code to understand
every database-specific field in `record.data`.

Common preview kinds:

- `sequence`: protein, nucleotide, or other biological sequence preview. Use
  `format`, `mime_type`, `length`, `url`, and `data.alphabet` when present.
- `feature_track`: bounded sequence-feature rows and tracks. Use `data.summary`,
  `data.tracks`, and `data.rows`; show truncation when the summary says so.
- `structure_3d`: structural preview entry. Use `provider`, `id`, `url`, and
  provider-specific `data` such as an AlphaFold API URL or PDB IDs.
- `chemical_structure`: 2D compound structure preview. Use `provider`, `id`,
  `url`, and provider-specific `data` such as SMILES, InChIKey, molfile, and
  image URLs.
- `network`: graph preview seed for interaction or pathway renderers. Use
  `data.nodes`, `data.edges`, and `url` when a full external graph exists.
- `survival_curve`: survival analysis preview rows for Kaplan-Meier style
  renderers. Use `data.time_unit`, `data.endpoints`, and `data.rows`, where
  rows should include patient IDs, endpoint labels, time values, status labels,
  and event-observed booleans when available.
- `heatmap_matrix`: bounded numeric or discrete matrix preview for expression,
  copy-number, proteomics, or similar sample-by-feature views. Use
  `data.row_id`, `data.column_ids`, `data.value_key`, `data.columns`, and
  `data.rows`; show `data.value_labels` for discrete encodings such as
  cBioPortal CNA calls and surface `data.truncated` when only a bounded subset
  was returned.
- `citation_list`: literature references and PubMed IDs suitable for citation
  chips or bibliography side panels.
- `xref_groups`: grouped external database references for expandable accordions
  or tabular detail views.
- `download_manifest`: reviewable download-plan preview. Do not download
  automatically.
- `table`: compact table preview, typically with `data.columns` and `data.rows`.
- `text`: text preview when no richer renderer applies.

Each preview may include `actions`; the same URL safety rules as
`display.actions` apply. A preview `url` is a user-openable external target, not
an instruction to fetch automatically. A preview can point back to a matching
detail section through `section_key`, allowing cards, tabs, and hover panels to
stay synchronized.

## Hover

Render hover cards from `display.hover`:

- Use `hover.title` as the hover title.
- Use `hover.subtitle` as the smaller context line.
- Use `hover.icon` when present; otherwise use `display.icon`.
- Render `hover.fields` as label/value rows.

For citations, the hover should show at least PMID, title, journal, authors,
publication date, DOI, PMCID, and URL when available. The MCP should provide
those fields; the front end should not scrape or refetch just to populate the
hover card.

## Clicks And URL Routing

Use the first available URL in this order:

1. `record.display.primary_url`
2. `record.url`
3. first `record.display.actions[].url`
4. first `record.links[].url`

Open only `http://` and `https://` URLs by default. Do not open `file://`,
`javascript:`, shell commands, or opaque custom schemes from MCP output.

For `kind: "external"`, open the user's default browser. For
`kind: "download"`, show an explicit download/open action and avoid automatic
bulk transfer. Dataset tools may expose FTP-derived HTTPS links; they are still
user-initiated actions.

Command suggestions, such as SRA Toolkit `prefetch` and `fasterq-dump`
commands, live under `record.data.commands` or tool-specific manifest fields.
Never treat command strings as clickable URLs, and never execute them from the
renderer without an explicit user action and the application's normal execution
guardrails.

## Component Guidance

`citation` records should support both inline chips and full cards. The compact
label should be `stable_id`, for example `PMID:36973787`. Hover should expose
journal, title, authors, DOI, PMCID, and URL.
ChEMBL document citation records should expose the ChEMBL document ID, title,
authors, journal, year, PMID, DOI, ChEMBL source link, PubMed/DOI links when
available, abstract text previews, and grouped ChEMBL/PubMed/DOI xrefs.

`dataset` records should expose the accession, organism, study type, sample
count, platform, source links, and related entities such as GEO samples,
platforms, PubMed articles, and BioProject records. GWAS trait-search dataset
records should expose association and study counts, EFO traits, PubMed evidence,
and GWAS Catalog links through table and citation-list previews. Open Targets
disease evidence records should expose the disease identifier, associated target
count, ontology cross-references, target association tables, datasource score
tables, and Open Targets browser links. ChEMBL assay dataset records should
expose the assay ID, assay type, BAO format, organism, target ID, document ID,
confidence score/description, parameter tables, classification tables, and
ChEMBL browser/API links. ChEMBL activity and mechanism dataset
records should expose the molecule or target query, returned row count, total
upstream row count, bounded activity/mechanism tables, ChEMBL molecule and
target links, assay links, document or reference links when present, and the
ChEMBL API query URL. ChEMBL drug-indication dataset records should expose the molecule ID,
returned row count, total upstream row count, bounded indication tables,
EFO/HPO and MeSH disease identifiers, maximum indication phase, source evidence
references such as ClinicalTrials, ATC, or DailyMed, and the ChEMBL API query
URL. PubChem BioAssay and Substance dataset records should expose AID/SID,
source or depositor metadata, assay/source summaries, linked PubChem compounds,
grouped cross-references, PubChem browser URLs, and PUG REST URLs. cBioPortal
dataset records should expose molecular profile IDs, sample-list IDs, mutation
query context, HUGO/Entrez gene identifiers, returned row counts, bounded
mutation tables, sample/patient IDs, protein changes, mutation type, variant
type, genomic coordinates when present, clinical attribute definitions,
sample/patient clinical matrices, long-form clinical value tables, OS/DFS-style
survival rows for curve renderers, expression or other numeric molecular
matrices, discrete CNA matrices with alteration labels, heatmap previews, and
cBioPortal browser/API links.

`compound` records should expose the compound accession, preferred name,
molecule type, approval phase, first approval year, molecular formula, molecular
weight, canonical SMILES, InChIKey, synonyms, source links, and grouped
cross-references. Interactive views should read `display.previews` for
`chemical_structure`, molecule-property `table`, synonym table, and
`xref_groups` hints. PubChem compound records may omit approval-phase fields but
should expose CID, title, formula, molecular weight, SMILES, InChI/InChIKey,
IUPAC name, XLogP/TPSA style properties, descriptions, synonyms, structure
image URLs, PubChem browser URLs, and PUG REST URLs. HMDB metabolite records
should expose HMDB accessions, names, formula/mass, SMILES/InChI/InChIKey when
present, synonyms, taxonomy/classification fields, grouped cross-references,
HMDB browser links, and chemical structure preview hints.
ChEBI compound records should expose the CHEBI accession, preferred name,
definition, formula/mass/charge, SMILES/InChI/InChIKey when present, synonyms,
secondary IDs, grouped external accessions, citation references, biological
origins, ChEBI structure image URLs, browser URLs, API URLs, and optional
ontology relation detail.

`protein` records should expose the UniProtKB accession, entry name, protein
name, gene symbol(s), organism, TaxID, reviewed status, sequence length, FASTA
link, and stable UniProt browser URL. Rich detail views should read
`display.sections` for overview fields, function text, bounded sequence
features, keywords, comments, cross-reference groups, and literature links.
Interactive views should read `display.previews` for sequence, feature-track,
3D-structure, STRING-network, citation-list, and cross-reference preview hints.

`protein_structure` records should expose the structure accession, source
provider, UniProt accession when known, organism, TaxID, residue region,
confidence or quality score, experimental method, resolution, model version,
browser URL, and user-openable structure files. Interactive views should read
`display.previews` for `structure_3d`, `download_manifest`, optional
`sequence`, and optional entity `table` hints.

`protein_network` records should expose the source provider, seed identifiers,
species TaxID, node count, interaction count, browser URL, and user-openable
network links. Interactive graph views should read `display.previews` for a
`network` preview with `data.nodes`, `data.edges`, and score metadata; table
views can use the companion `table` preview or the `interactions` section.

`pathway` records should expose the pathway/event stable ID, source provider,
species, class, participant count, reference count, browser URL, and API URL.
Interactive views should read `display.previews` for a `network` preview of
participants, a participant `table`, optional `citation_list`, and
`xref_groups` for stable Reactome identifiers.

`ontology_term` records should expose the ontology term ID, preferred name,
aspect or ontology namespace, definition, obsolete status, synonyms, parent or
child relation metadata, browser URL, and API URL. QuickGO term records expose
GO definitions, synonym tables, child/ancestor relation tables, ontology
relation `network` previews, and grouped cross-reference previews for PubMed,
Reactome, Wikipedia, UniProt keyword, or other source links.
ChEBI relation records should expose the related CHEBI term, relation type,
query term, browser URL, and a two-node `network` preview so parent/child
relationships can be rendered without ChEBI-specific field handling.

`gene` records should expose `GeneID` or Ensembl stable IDs, symbol, organism,
TaxID or species, chromosome/region, aliases, OMIM or external links, and
genomic locations when present. gnomAD gene records should additionally expose
constraint metrics through `table` previews, while keeping the browser URL in
`display.primary_url`. GWAS Catalog mapped-gene records should expose
association evidence through `table` previews and PubMed IDs through
`citation_list` previews. Open Targets target records should expose the Ensembl
target ID, HGNC symbol, biotype, genomic location, associated disease count,
target-disease association tables, datasource/datatype score tables, and Open
Targets browser/API links. Human Protein Atlas gene records should expose the
Ensembl ID, symbol, UniProt accessions, evidence label, RNA/protein expression
specificity, subcellular localization, antibody reliability, cancer prognostic
tables when available, grouped cross-references, and HPA browser/API links.

`genomic_feature` records should expose the stable feature ID, feature type,
biotype, species, assembly, coordinates, strand, browser URL, and API URL. Use
`display.previews` for transcript/feature tables and grouped cross-reference
widgets when available.

`variant` records should expose the variant ID, class or variant type,
consequence or clinical significance, primary mapping/location, alleles when
present, review status or evidence labels, browser URL, and dbSNP or other
external links when present. Use `table` previews for mappings, ClinVar
locations, gnomAD population frequencies, transcript consequences, or
GWAS association evidence, or supporting submissions, and `xref_groups`
previews for variant identifiers, synonyms, gene links, EFO traits, PubMed IDs,
and external references.

`taxonomy` records should expose `TaxID`, scientific name, common name, rank,
division, status, and the stable NCBI Taxonomy browser URL. MGnify biome
taxonomy records should expose biome name, lineage, sample count, related
studies/samples/genomes/children links, and MGnify API URLs.

`identifier_conversion` records should expose each mapped identifier and keep
PubMed, PMC, DOI, and manuscript links distinct. Open Targets search records
should expose resolved target and disease hits with their own clickable Open
Targets URLs instead of requiring the renderer to construct target or disease
links.

`database` records should expose Entrez database metadata and provide a stable
NCBI database URL.

`linkset` records should expose the source record and linked target groups.
Show truncation clearly when `target_groups[].truncated` is true.

`project` records should expose project accession, project title, organism,
data type, submitter, registration date, BioProject URL, and SRA Run Selector
link when applicable. PRIDE project records should expose the PXD accession,
title, description, submission/publication dates, DOI, organisms, instruments,
experiment types, PTMs, submitter or lab PI summaries, publication references,
PRIDE browser/API links, and optional metadata-only file manifest previews.
BioStudies and ArrayExpress project records should expose the accession, title,
description, release date, organisms, study types, sample/assay counts,
authors, protocols, publication references, external repository links such as
ENA or Expression Atlas, BioStudies browser/API links, and optional
metadata-only file manifest previews. CELLxGENE project records should expose
collection UUIDs, title, description, DOI, publication metadata, authors,
dataset counts, cell counts, organism/tissue/disease/cell type/assay ontology
labels, dataset explorer URLs, CELLxGENE browser/API links, and optional H5AD
asset manifest previews. MetaboLights project records should expose MTBLS
accessions, title, description, study status, study category, public release
date, study design labels, organisms when available, assays, protocols,
publication references, file counts, MetaboLights browser/API links, FTP HTTPS
folder links, Globus links, and optional metadata-only file manifest previews.
HMDB disease and pathway records should expose HMDB identifiers when available,
names, descriptions, associated pathways/diseases, grouped cross-references,
and HMDB browser links while using existing `dataset` and `pathway` renderers.
MGnify project records should expose MGYS accessions, study title, BioProject
and secondary accessions, sample counts, centre name, public release or update
dates, biome lineages, relationship links for samples/analyses/downloads/
publications, and MGnify browser/API links. ENCODE project records should
expose ENCSR accessions, assay title, biosample ontology term, organism, status,
release date, assemblies, lab, GEO cross-references when present, ENCODE
browser/API links, and optional metadata-only file manifest previews. cBioPortal
project records should expose study IDs, study title, cancer type, sample
counts, sequencing/CNA/expression sample counts when available, group/public
status, PubMed links when present, molecular profile previews, sample-list
previews, and cBioPortal browser/API links.

`sample` records should expose BioSample accession, organism, TaxID, package,
owner organization, key attributes such as tissue or disease, and related
SRA/GEO/BioProject identifiers. MGnify sample records should expose sample
accessions, BioSample accessions, sample names or aliases, species, host TaxID,
collection date, geolocation, biome lineage, related studies/runs links, and
bounded sample metadata table previews. ENCODE biosample records should expose
ENCBS accessions, biosample summary, ontology term/path, organism, life stage,
age, sex, donor/source/lab/award links, status, external references, and
grouped ENCODE/API links.

`run` records should expose SRA accession, study, experiment, run accessions,
BioProject, BioSample, organism, library strategy/source/selection/layout,
platform, instrument, and Run Browser/Run Selector links. Do not start raw-data
downloads from these records without an explicit user action.

`download_plan` records should expose the accession, source database, intended
files or runs, browser links, download links, and suggested commands where
relevant. They are planning artifacts only; the renderer should show them as
reviewable actions and not perform network or shell work automatically. PRIDE
file manifests should preserve original FTP/Aspera locations in `data` while
using only safe `http(s)` URLs for clickable actions when an HTTPS mirror is
available. BioStudies file manifests should preserve file path, section, type,
description, format, size, HTTP download URL, and optional Globus/browser links
without starting a download. CELLxGENE asset manifests should preserve dataset
IDs, dataset titles, asset file types, file sizes, H5AD URLs, and dataset
explorer URLs without starting a download. MetaboLights file manifests should
preserve file names, file types, status, timestamps, directory flags, FTP HTTPS
download URLs when available, and optional Globus/browser links without
starting a download. ENCODE file manifests should preserve ENCFF accessions,
file format/type, output type/category, assembly, replicate fields, file size,
MD5 checksum, ENCODE portal/API links, HTTPS download URLs, and optional cloud
URLs without starting a download.

`sample_sheet` records should expose row and column counts, the source query,
the primary key, and a compact table preview from `record.data.rows` and
`record.data.columns`. The front end may offer export actions, but should keep
the original structured rows for downstream pipeline configuration.

`runtime_status` records should expose command availability, discovered path,
and version information when the MCP has safely checked it. Missing tools should
be rendered as actionable environment gaps, not as fatal UI errors.

## Front-end Robustness Rules

- Do not parse raw `content[].text` JSON when `structuredContent` is present.
- For `resolve_context` responses, render `contexts[]` and `entities[]`; do not
  require `records[]`.
- Do not rely on database-specific `data` for the first-pass UI.
- Do not assume every record has every optional field.
- Preserve unknown fields for future detail panes.
- Prefer `stable_id` over `id` for user-visible identifiers.
- Prefer `display.metadata` over ad hoc field selection.
- Prefer `display.actions` over constructing URLs in the front end.
- Prefer `display.sections` for expandable detail panes when it is present.
- Prefer `display.previews` for rich widgets when it is present; fall back to
  `display.sections` or generic cards when a preview kind is unknown.
- Keep renderer behavior deterministic and side-effect free until the user
  clicks an action.
- Before rendering browser links, allow only `http://` and `https://` URLs.

## Agent Guidance

Skills should tell agents when to call MCP tools and which fields matter. They
should not implement UI rendering. MCP tools should keep returning stable,
front-end-compatible envelopes. Application code should render those envelopes
with shared components and the TypeScript helpers in `types/record.ts`.
