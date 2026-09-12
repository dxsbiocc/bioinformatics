# NCBI MCP

Local MCP server for NCBI access in the Bioinformatics plugin.

Implemented surfaces through NCBI E-utilities:

- `ncbi_db_info`
- `ncbi_link`
- `pubmed_search`
- `pubmed_summaries`
- `pubmed_articles`
- `pubmed_fetch`
- `pmc_id_convert`
- `gene_lookup`
- `taxonomy_lookup`
- `bioproject_lookup`
- `biosample_lookup`
- `sra_lookup`
- `sra_search`
- `sra_download_plan`
- `geo_series`
- `geo_search`
- `geo_download_plan`
- `omics_sample_sheet`
- `tool_runtime_status`
- `ncbi_status`

The server is written with Python's standard library only. Optional environment
variables:

- `NCBI_API_KEY` or `ENTREZ_API_KEY`
- `NCBI_EMAIL` or `ENTREZ_EMAIL`
- `NCBI_TOOL`

The plugin loads this server through `../../.mcp.json`.

Baseline notes:

- Release history: `../../CHANGELOG.md`
- Operational guidance: `../../docs/ncbi-mcp-operations.md`
- Tool call examples: `../../examples/ncbi/README.md`
- Front-end fixtures: `../../fixtures/frontend/ncbi/core-records.json`

## Implementation layout

- `server.py`: stdio JSON-RPC/MCP entrypoint and backward-compatible exports.
- `client.py`: NCBI E-utilities HTTP client, request metadata, and rate limit.
- `entrez.py`: common EInfo and ELink tools for database metadata and cross-database links.
- `pubmed.py`: PubMed tools, ESummary normalization, and EFetch XML parsing.
- `pmc.py`: PMC ID Converter API integration for PMID, PMCID, DOI, and manuscript IDs.
- `gene.py`: NCBI Gene symbol/GeneID lookup and metadata normalization.
- `taxonomy.py`: NCBI Taxonomy TaxID/scientific-name lookup.
- `bioproject.py`: BioProject accession/UID lookup and project metadata normalization.
- `biosample.py`: BioSample accession/UID lookup and sample attribute normalization.
- `sra.py`: SRA accession/UID lookup, SRA search, and ESummary XML-fragment parsing.
- `geo.py`: GEO DataSets search, GSE resolution, and GEO download-link builders.
- `manifests.py`: metadata-only GEO/SRA download plans, sample sheets, and runtime checks.
- `manifest_records.py`: front-end envelopes for download plans, sample sheets, and runtime status.
- `schemas.py`: PubMed/GEO record envelopes plus shared display helpers.
- `records.py`: Gene, Taxonomy, PMC, common Entrez, and URL helpers.
- `omics_records.py`: BioProject, BioSample, and SRA front-end envelopes.
- `previews.py`: shared front-end preview hints for citations, manifests,
  tables, grouped cross-references, and text summaries.
- `tools.py`: MCP tool schemas and handler registry.
- `utils.py`: validation, provenance, and XML text helpers.

## Front-end compatibility contract

The shared renderer contract is documented in
`../../docs/frontend-record-rendering.md`, typed in `../../types/record.ts`, and
described as JSON Schema in `../../schemas/record.schema.json`.

Tool responses keep their database-specific legacy fields, such as `pmids`,
`articles`, `text`, and `source`. They also include a stable compatibility
layer for agent UI rendering:

- `schema_version`: result envelope version.
- `provenance`: retrieval endpoint, query parameters, and retrieval time.
- `records`: generic NCBI result records for cards, rows, hover previews, and
  external-link handling.
- `citations`: literature citation objects for inline citation chips.

Every item in `records` should keep this front-end contract stable:

- `id`, `stable_id`, `label`, `title`, `description`, `url`, and `icon` for
  common list/card rendering.
- `identifiers` for stable database identifiers and their target URLs.
- `links` for all click targets. The MCP returns URLs only; the agent
  application decides whether to open a browser, preview, or download.
- `display.component`, `display.chip_label`, `display.title`,
  `display.subtitle`, `display.description`, `display.metadata`,
  `display.badges`, `display.actions`, `display.hover`, and
  `display.primary_url` for UI rendering without database-specific parsing.
- `display.previews` for richer shared widgets such as PubMed citation lists,
  GEO/SRA download manifests, sample-sheet tables, SRA run tables, grouped
  Entrez cross-references, and runtime text summaries.
- `data` for the normalized domain payload. Database modules may add
  `related` for linked entities such as GEO samples, platforms, PubMed
  articles, or BioProject records.

PubMed records include stable identifiers and links:

```json
{
  "schema_version": "bioinformatics.record.v1",
  "type": "literature.article",
  "database": "pubmed",
  "id": "36973787",
  "stable_id": "PMID:36973787",
  "label": "PMID:36973787",
  "url": "https://pubmed.ncbi.nlm.nih.gov/36973787/",
  "icon": "pubmed",
  "display": {
    "component": "citation",
    "chip_label": "PMID:36973787",
    "hover": {
      "title": "Article title",
      "subtitle": "Journal | Publication date",
      "icon": "pubmed",
      "fields": []
    },
    "primary_url": "https://pubmed.ncbi.nlm.nih.gov/36973787/"
  }
}
```

Future NCBI database additions should return the same `records` envelope and
preserve their source-specific fields. For example, Gene records should expose
`stable_id` values such as `GeneID:7157`, and all records should provide a
primary URL when NCBI has a stable browser page.

For GEO Series accessions, use `geo_series`:

```json
{
  "accession": "GSE100"
}
```

The response includes GEO browser URLs plus HTTPS FTP links for the family SOFT
file, series matrix file, and supplementary-file directory. The MCP returns
links only; it does not start bulk downloads.

For metadata-first data acquisition planning, use:

- `geo_download_plan` for a GSE accession. It returns a download manifest with
  the GEO browser URL, FTP-derived HTTPS links, sample accessions, platform,
  BioProject, PubMed IDs, and a `download_plan` record for UI rendering.
- `sra_download_plan` for SRR/SRX/SRS/SRP, BioProject, BioSample, or broader
  SRA queries. It returns one planned run item per SRA run, Run Browser and Run
  Selector links, and suggested SRA Toolkit command strings in `commands`.
- `omics_sample_sheet` for a front-end-ready GEO or SRA sample metadata table
  with stable columns and row-level links.
- `tool_runtime_status` to check whether common local command-line tools such
  as SRA Toolkit, FastQC, MultiQC, Salmon, STAR, HISAT2, Samtools, SeqKit, and
  Nextflow are discoverable on `PATH`.

These planning tools return metadata and suggestions only. They do not run SRA
Toolkit, download GEO/SRA files, install tools, or modify project files.

For common identifiers, use the narrowest matching tool:

- `gene_lookup` for GeneID or symbol plus an optional organism filter, for
  example `{"query": "TP53", "organism": "Homo sapiens"}`.
- `taxonomy_lookup` for TaxID or scientific name, for example
  `{"query": "Homo sapiens"}`.
- `pmc_id_convert` for PMID, PMCID, DOI, or manuscript ID conversion.
- `ncbi_db_info` to inspect supported Entrez databases, searchable fields, and
  link types before constructing a query.
- `ncbi_link` to discover cross-database links such as Gene to PubMed or
  PubMed to PMC.
- `bioproject_lookup` for PRJNA/PRJEB/PRJDB accessions or BioProject UIDs.
- `biosample_lookup` for SAMN/SAMEA/SAMD accessions or BioSample UIDs.
- `sra_lookup` for SRR/SRX/SRS/SRP-style accessions or SRA UIDs.
- `sra_search` for broader SRA discovery with optional organism, strategy, and
  source filters.
- `sra_download_plan` when the user needs a run manifest or exact SRA Toolkit
  command suggestions before starting a download.
- `geo_download_plan` when the user has a GSE accession and needs the GEO file
  URLs prepared for review.
- `omics_sample_sheet` when pipeline setup needs a table of GEO samples or SRA
  runs before execution.
- `tool_runtime_status` before pipeline execution when local tool availability
  must be checked without solving environments ad hoc.
- `ncbi_related_records` for ELink-based related records when the source
  database is known and target databases are optional.
- `ncbi_status` to inspect configured NCBI settings, the full tool inventory,
  grouped capabilities, renderer components, and optional network health.

Future NCBI database additions should be added behind the same server interface,
not as separate ad hoc scripts:

- NCBI Protein records
- Nucleotide records
- PMC full-text metadata beyond ID conversion
- Assembly metadata
