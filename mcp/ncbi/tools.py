"""MCP tool registry for the NCBI server."""

from __future__ import annotations

from typing import Callable

from .bioproject import bioproject_lookup
from .biosample import biosample_lookup
from .client import NcbiClient
from .constants import MAX_PUBMED_IDS, JsonObject
from .entrez import ncbi_db_info, ncbi_link, ncbi_related_records
from .gene import gene_lookup
from .geo import geo_search, geo_series
from .manifests import (
    geo_download_plan,
    omics_sample_sheet,
    sra_download_plan,
    tool_runtime_status,
)
from .pmc import pmc_id_convert
from .pubmed import (
    pubmed_articles,
    pubmed_fetch,
    pubmed_search,
    pubmed_summaries,
)
from .sra import sra_lookup, sra_search
from .taxonomy import taxonomy_lookup
from .utils import optional_bool, parse_count


def ncbi_status(args: JsonObject, client: NcbiClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "ncbi",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "tool": client.config.tool,
        "email_configured": bool(client.config.email),
        "api_key_configured": bool(client.config.api_key),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": [
            "pubmed",
            "pmc",
            "gene",
            "taxonomy",
            "geo",
            "bioproject",
            "biosample",
            "sra",
        ],
        "available_common_tools": [
            "ncbi_db_info",
            "ncbi_link",
            "ncbi_related_records",
            "omics_sample_sheet",
            "tool_runtime_status",
        ],
        "available_workflows": [
            "geo_download_plan",
            "sra_download_plan",
            "omics_sample_sheet",
            "tool_runtime_status",
        ],
        "tool_groups": {
            "literature": [
                "pubmed_search",
                "pubmed_summaries",
                "pubmed_articles",
                "pubmed_fetch",
                "pmc_id_convert",
            ],
            "omics_datasets": [
                "geo_series",
                "geo_search",
                "geo_download_plan",
                "bioproject_lookup",
                "biosample_lookup",
                "sra_lookup",
                "sra_search",
                "sra_download_plan",
                "omics_sample_sheet",
            ],
            "entities": [
                "gene_lookup",
                "taxonomy_lookup",
            ],
            "entrez": [
                "ncbi_db_info",
                "ncbi_link",
                "ncbi_related_records",
            ],
            "runtime": [
                "tool_runtime_status",
            ],
            "status": [
                "ncbi_status",
            ],
        },
        "frontend_components": [
            "citation",
            "dataset",
            "gene",
            "taxonomy",
            "identifier_conversion",
            "database",
            "linkset",
            "project",
            "sample",
            "run",
            "download_plan",
            "sample_sheet",
            "runtime_status",
        ],
        "preview_kinds": [
            "citation_list",
            "download_manifest",
            "table",
            "xref_groups",
            "text",
        ],
        "planned_databases": [
            "protein",
            "nuccore",
            "assembly",
        ],
    }
    if check_network:
        payload = client.request_json(
            "esearch.fcgi",
            {
                "db": "pubmed",
                "term": "pubmed[journal]",
                "retmode": "json",
                "retmax": 0,
            },
        )
        status["network_check"] = {
            "ok": True,
            "count": parse_count(payload.get("esearchresult", {}).get("count")),
        }
    return status


def tool_definitions() -> list[JsonObject]:
    read_only_annotations = {
        "readOnlyHint": True,
        "openWorldHint": True,
    }
    return [
        {
            "name": "pubmed_search",
            "title": "Search PubMed",
            "description": (
                "Search PubMed through NCBI ESearch and optionally attach "
                "ESummary metadata for returned PMIDs."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "PubMed query string, including field tags if needed.",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 10,
                    },
                    "sort": {
                        "type": "string",
                        "enum": [
                            "relevance",
                            "pub_date",
                            "journal",
                            "title",
                            "author",
                            "first_author",
                        ],
                        "default": "relevance",
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Optional lower date bound: YYYY, YYYY/MM, or YYYY/MM/DD.",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Optional upper date bound: YYYY, YYYY/MM, or YYYY/MM/DD.",
                    },
                    "date_type": {
                        "type": "string",
                        "default": "pdat",
                        "description": "NCBI ESearch date type, usually pdat for publication date.",
                    },
                    "include_summaries": {
                        "type": "boolean",
                        "default": True,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "pubmed_summaries",
            "title": "Get PubMed summaries",
            "description": "Retrieve normalized PubMed ESummary metadata for PMIDs.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ids": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                                "maxItems": MAX_PUBMED_IDS,
                            },
                        ],
                        "description": "PMID string, comma-separated PMIDs, or PMID array.",
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["ids"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "pubmed_articles",
            "title": "Get PubMed article details",
            "description": (
                "Fetch PubMed XML through NCBI EFetch and return parsed title, "
                "abstract, authors, journal, identifiers, MeSH terms, and keywords."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ids": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                                "maxItems": MAX_PUBMED_IDS,
                            },
                        ],
                    },
                    "include_xml": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["ids"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "pubmed_fetch",
            "title": "Fetch PubMed records",
            "description": "Fetch raw PubMed records as abstract text, MEDLINE, or XML.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ids": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                                "maxItems": MAX_PUBMED_IDS,
                            },
                        ],
                    },
                    "format": {
                        "type": "string",
                        "enum": ["abstract", "medline", "xml"],
                        "default": "abstract",
                    },
                },
                "required": ["ids"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "geo_series",
            "title": "Get GEO Series metadata",
            "description": (
                "Resolve a GEO Series accession such as GSE100 through NCBI "
                "GEO DataSets and return normalized metadata plus stable GEO, "
                "SOFT, series matrix, and supplementary-file links."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "accession": {
                        "type": "string",
                        "description": "GEO Series accession, for example GSE100.",
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["accession"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "geo_search",
            "title": "Search GEO DataSets",
            "description": (
                "Search NCBI GEO DataSets and return normalized GEO records. "
                "Use geo_series when you already have an exact GSE accession."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "GEO DataSets query string, including field tags if needed.",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 10,
                    },
                    "entry_type": {
                        "type": "string",
                        "enum": ["all", "gse", "gds", "gsm", "gpl"],
                        "default": "all",
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "geo_download_plan",
            "title": "Plan GEO Series downloads",
            "description": (
                "Resolve a GEO Series accession and return a metadata-only "
                "download manifest with GEO browser, SOFT, series matrix, and "
                "supplementary-file URLs for front-end display."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "accession": {
                        "type": "string",
                        "description": "GEO Series accession, for example GSE100.",
                    },
                    "include_samples": {
                        "type": "boolean",
                        "default": True,
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["accession"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "bioproject_lookup",
            "title": "Look up NCBI BioProject records",
            "description": (
                "Resolve a BioProject accession such as PRJNA450921 or a "
                "BioProject UID and return project, organism, submitter, and "
                "SRA Run Selector metadata."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "BioProject accession, UID, or search query.",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 5,
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "biosample_lookup",
            "title": "Look up NCBI BioSample records",
            "description": (
                "Resolve a BioSample accession such as SAMN08954945 or a "
                "BioSample UID and return sample attributes, organism metadata, "
                "and linked SRA/GEO/BioProject identifiers."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "BioSample accession, UID, or search query.",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 5,
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "sra_lookup",
            "title": "Look up NCBI SRA records",
            "description": (
                "Resolve SRR/SRX/SRS/SRP accessions or SRA UIDs and return "
                "run, experiment, study, library, organism, BioProject, and "
                "BioSample metadata without downloading raw data."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SRA run, experiment, sample, study accession, UID, or search query.",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 5,
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "sra_search",
            "title": "Search NCBI SRA",
            "description": (
                "Search SRA by free-text query with optional organism, library "
                "strategy, and library source filters, returning normalized "
                "metadata and external URLs only."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SRA query string, including field tags if needed.",
                    },
                    "organism": {
                        "type": "string",
                        "description": "Optional organism filter, for example Homo sapiens.",
                    },
                    "strategy": {
                        "type": "string",
                        "description": "Optional library strategy filter, for example RNA-Seq.",
                    },
                    "source": {
                        "type": "string",
                        "description": "Optional library source filter, for example TRANSCRIPTOMIC.",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 10,
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "sra_download_plan",
            "title": "Plan SRA Toolkit downloads",
            "description": (
                "Resolve SRA accessions, BioProject/BioSample accessions, or "
                "SRA searches into a metadata-only run manifest and suggested "
                "prefetch/fasterq-dump commands. The tool never downloads data."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "SRR/SRX/SRS/SRP accession, SRA UID, PRJNA/SAMN "
                            "accession, or SRA query."
                        ),
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 20,
                    },
                    "threads": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 128,
                        "default": 8,
                    },
                    "prefetch_outdir": {
                        "type": "string",
                        "default": "data/sra",
                    },
                    "fastq_outdir": {
                        "type": "string",
                        "default": "data/fastq",
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "omics_sample_sheet",
            "title": "Build an omics sample sheet",
            "description": (
                "Create a front-end-ready metadata table from GEO Series or "
                "SRA metadata without downloading raw data."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "GSE accession, SRA accession, BioProject accession, or SRA query.",
                    },
                    "source": {
                        "type": "string",
                        "enum": ["auto", "geo", "sra"],
                        "default": "auto",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 50,
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "gene_lookup",
            "title": "Look up NCBI Gene records",
            "description": (
                "Resolve a GeneID or gene symbol through NCBI Gene and return "
                "normalized gene, organism, genomic location, alias, OMIM, and URL metadata."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "GeneID or gene symbol, for example 7157 or TP53.",
                    },
                    "organism": {
                        "type": "string",
                        "description": "Optional organism filter, for example Homo sapiens.",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 5,
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "taxonomy_lookup",
            "title": "Look up NCBI Taxonomy records",
            "description": (
                "Resolve a TaxID or scientific name through NCBI Taxonomy and return "
                "normalized organism metadata and stable Taxonomy URLs."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "TaxID or scientific name, for example 9606 or Homo sapiens.",
                    },
                    "exact": {
                        "type": "boolean",
                        "default": True,
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 5,
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "pmc_id_convert",
            "title": "Convert PubMed, PMC, DOI, and manuscript identifiers",
            "description": (
                "Use the PMC ID Converter API to map PMIDs, PMCIDs, DOIs, and "
                "manuscript IDs while preserving clickable PubMed, PMC, and DOI links."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ids": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                                "maxItems": 200,
                            },
                        ],
                        "description": "One ID, comma-separated IDs, or an ID array.",
                    },
                    "id_type": {
                        "type": "string",
                        "description": "Optional source ID type such as pmid, pmcid, doi, or mid.",
                    },
                    "versions": {
                        "type": "boolean",
                        "default": False,
                    },
                    "show_aiid": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["ids"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "ncbi_db_info",
            "title": "Inspect Entrez database metadata",
            "description": (
                "List Entrez databases or retrieve searchable fields and link types "
                "for a specific database via NCBI EInfo."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "database": {
                        "type": "string",
                        "description": "Optional Entrez database name, for example gene or pubmed.",
                    },
                    "include_fields": {
                        "type": "boolean",
                        "default": False,
                    },
                    "include_links": {
                        "type": "boolean",
                        "default": True,
                    },
                    "include_hidden": {
                        "type": "boolean",
                        "default": False,
                    },
                    "max_fields": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 500,
                        "default": 50,
                    },
                    "max_links": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 500,
                        "default": 100,
                    },
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "ncbi_link",
            "title": "Find Entrez linked records",
            "description": (
                "Use NCBI ELink to find records linked across Entrez databases, "
                "such as Gene to PubMed, PubMed to PMC, or BioSample to SRA."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "db_from": {
                        "type": "string",
                        "description": "Source Entrez database, for example gene.",
                    },
                    "db_to": {
                        "type": "string",
                        "description": "Optional target Entrez database, for example pubmed.",
                    },
                    "ids": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                            },
                        ],
                    },
                    "link_name": {
                        "type": "string",
                        "description": "Optional specific ELink linkname.",
                    },
                    "max_links": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 500,
                        "default": 50,
                    },
                },
                "required": ["db_from", "ids"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "ncbi_related_records",
            "title": "Find related NCBI records",
            "description": (
                "Convenience wrapper around NCBI ELink for discovering related "
                "records from one Entrez database to all or selected target "
                "databases, such as BioProject to SRA or BioSample to SRA."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "database": {
                        "type": "string",
                        "description": "Source Entrez database, for example bioproject.",
                    },
                    "ids": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                            },
                        ],
                    },
                    "target_databases": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                            },
                        ],
                        "description": "Optional target databases, for example sra,biosample,pubmed.",
                    },
                    "max_links": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 500,
                        "default": 50,
                    },
                },
                "required": ["database", "ids"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "ncbi_status",
            "title": "Inspect NCBI MCP status",
            "description": (
                "Report configured NCBI metadata and currently available/planned "
                "database surfaces. Optionally perform a tiny PubMed network check."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "check_network": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "tool_runtime_status",
            "title": "Inspect local omics tool runtimes",
            "description": (
                "Check whether common omics command-line tools are available "
                "on PATH and optionally collect version strings for known tools."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tools": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                                "maxItems": 100,
                            },
                        ],
                        "description": "Optional command names. Defaults to common NGS tools.",
                    },
                    "check_versions": {
                        "type": "boolean",
                        "default": False,
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 30,
                        "default": 3,
                    },
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
    ]


TOOL_HANDLERS: dict[str, Callable[[JsonObject, NcbiClient], JsonObject]] = {
    "pubmed_search": pubmed_search,
    "pubmed_summaries": pubmed_summaries,
    "pubmed_articles": pubmed_articles,
    "pubmed_fetch": pubmed_fetch,
    "geo_series": geo_series,
    "geo_search": geo_search,
    "geo_download_plan": geo_download_plan,
    "bioproject_lookup": bioproject_lookup,
    "biosample_lookup": biosample_lookup,
    "sra_lookup": sra_lookup,
    "sra_search": sra_search,
    "sra_download_plan": sra_download_plan,
    "omics_sample_sheet": omics_sample_sheet,
    "gene_lookup": gene_lookup,
    "taxonomy_lookup": taxonomy_lookup,
    "pmc_id_convert": pmc_id_convert,
    "ncbi_db_info": ncbi_db_info,
    "ncbi_link": ncbi_link,
    "ncbi_related_records": ncbi_related_records,
    "ncbi_status": ncbi_status,
    "tool_runtime_status": tool_runtime_status,
}
