# Bioinformatics MCP Plugin

[![CI](https://github.com/dxsbiocc/bioinformatics/actions/workflows/ci.yml/badge.svg)](https://github.com/dxsbiocc/bioinformatics/actions/workflows/ci.yml)

A collection of [Model Context Protocol](https://modelcontextprotocol.io)
servers that give an LLM agent (Claude, Codex, or any MCP-compatible host) read
access to major public bioinformatics databases and literature sources, plus a
set of Skills for running omics analysis, search, and visualization workflows
on top of them.

Every server speaks MCP over stdio by hand — there is no MCP SDK dependency.
Outbound HTTP goes through [httpx](https://www.python-httpx.org/) (with
HTTP/2) using one reused `httpx.Client` per server process, instead of the
standard library's `urllib`. Responses follow a shared,
app-renderable record contract (see
[docs/frontend-record-rendering.md](docs/frontend-record-rendering.md)) so a
front end can render results consistently across all 29 servers without
per-database special-casing.

## Who this is for

Agent builders who want an LLM to look up genes, proteins, variants,
compounds, pathways, structures, public datasets, or literature during a
conversation — without hand-rolling a REST client for each database, and
without giving the agent unrestricted internet access.

## What's included

### MCP servers (`mcp/`)

| Server | Database | Covers |
| --- | --- | --- |
| `ncbi` | NCBI Entrez | PubMed, PMC, Gene, Taxonomy, GEO, BioProject, BioSample, SRA |
| `biorxiv` | bioRxiv / medRxiv | Preprint metadata, publication linkage |
| `uniprot` | UniProtKB | Protein search, accession lookup, FASTA |
| `alphafold` | AlphaFold DB | Predicted structure lookup by UniProt accession |
| `rcsb` | RCSB PDB | Structure search/lookup, FASTA, polymer/ligand summaries |
| `ensembl` | Ensembl | Stable ID lookup, xrefs, region overlap, variation |
| `clinvar` | ClinVar | Variant clinical significance, review status |
| `gnomad` | gnomAD | Variant frequency, gene constraint |
| `gwas` | GWAS Catalog | Variant/gene/trait associations |
| `opentargets` | Open Targets | Target-disease association evidence |
| `chembl` | ChEMBL | Compounds, targets, assays, mechanisms, indications |
| `pubchem` | PubChem | Compound/assay/substance lookup |
| `chebi` | ChEBI | Chemical ontology search and traversal |
| `quickgo` | QuickGO | GO term lookup, annotation evidence |
| `reactome` | Reactome | Pathway lookup and identifier mapping |
| `stringdb` | STRING | Protein-protein interaction networks |
| `rnacentral` | RNAcentral | ncRNA sequence and xref lookup |
| `efo` | EFO (OLS4) | Experimental factor ontology terms |
| `pride` | PRIDE Archive | Proteomics project metadata and file manifests |
| `biostudies` | BioStudies / ArrayExpress | Study metadata and file manifests |
| `cellxgene` | CELLxGENE Discover | Single-cell collection metadata |
| `hpa` | Human Protein Atlas | Expression, localization, prognostic data |
| `metabolights` | MetaboLights | Metabolomics study metadata |
| `hmdb` | HMDB | Metabolite/protein/disease/pathway records |
| `mgnify` | MGnify | Microbiome/metagenomics study and sample metadata |
| `encode` | ENCODE | Functional genomics experiments and biosamples |
| `cbioportal` | cBioPortal | Cancer genomics studies, mutations, clinical/survival data |
| `kegg` | KEGG | REST operations plus pathway-coloring image URLs |
| `visualization` | (local) | Routes result tables to plotting templates; no external API |

Most servers also expose a `<server>_parameter_domains` tool (discovers valid
enum/range/required-field values from the tool schema) and, where useful, a
`<server>_resolve_context` tool (resolves ambiguous identifiers to concrete
arguments before a fetch call). See [docs/mcp-parameter-domains.md](docs/mcp-parameter-domains.md).

### Skills (`skills/`)

- `omics-search` — routes a broad natural-language query to the right database/literature tool
- `omics-database` — database record and accession retrieval
- `omics-literature` — literature discovery and synthesis
- `omics-analysis` / `transcriptomics-analysis` — statistical analysis of prepared matrices
- `omics-pipeline` — raw-data processing pipeline planning (FASTQ/BAM/CRAM, etc.)
- `omics-visualization` — publication-style figures from result tables via bundled plotting templates

## Requirements

- Python 3.10+ (developed against 3.12). One third-party dependency,
  `httpx[http2]`, used by every MCP server for outbound HTTP; see
  [pyproject.toml](pyproject.toml). Install with `pip install -e .` or
  `pip install 'httpx[http2]'`.
- R 4.x, only if you use the `omics-visualization` or
  `transcriptomics-analysis` skills' plotting/analysis scripts. Install the
  required CRAN, Bioconductor, and GitHub packages with:

  ```bash
  Rscript requirements.R
  ```

- Some MCP servers accept an API key or contact email via environment
  variables for higher rate limits (e.g. `NCBI_API_KEY`, `CLINVAR_API_KEY`).
  All are optional; each server works anonymously with public rate limits
  otherwise.

## Installation

### Claude Code

Point Claude Code at this repo's [.mcp.json](.mcp.json), or add servers
individually:

```bash
claude mcp add ncbi python3 ./mcp/ncbi/server.py
```

Repeat for any other server you want enabled, or copy the relevant entries
from `.mcp.json` into your own MCP config.

### Codex

This repo is packaged as a Codex plugin — see
[.codex-plugin/plugin.json](.codex-plugin/plugin.json). Install it as a local
plugin pointing at this directory.

## Development

```bash
# Run the full test suite (stdlib unittest, no pytest dependency)
python3 -m unittest discover -s tests

# Run a single server's tests
python3 -m unittest tests.test_ncbi_mcp_server -v

# Optional: live smoke tests against real upstream APIs (off by default)
BIOINFORMATICS_LIVE_MCP_SMOKE=1 python3 -m unittest tests.test_live_mcp_smoke -v
```

Contract and schema references:

- [docs/frontend-record-rendering.md](docs/frontend-record-rendering.md) — how a front end should read `structuredContent` from any server
- [docs/mcp-parameter-domains.md](docs/mcp-parameter-domains.md) — the `*_parameter_domains` tool contract
- [docs/mcp-frontend-contract-tests.md](docs/mcp-frontend-contract-tests.md) — how contract tests are structured
- [docs/ncbi-mcp-operations.md](docs/ncbi-mcp-operations.md), [docs/kegg-mcp-operations.md](docs/kegg-mcp-operations.md) — per-server operation references
- [schemas/record.schema.json](schemas/record.schema.json), [schemas/dynamic-context.schema.json](schemas/dynamic-context.schema.json), [types/record.ts](types/record.ts) — machine-readable contract definitions

See [CHANGELOG.md](CHANGELOG.md) for release history.
