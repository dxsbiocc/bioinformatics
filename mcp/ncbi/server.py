#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics NCBI MCP server.

Implementation lives in sibling modules so PubMed, future NCBI databases,
and front-end compatibility schemas can evolve independently. This file keeps
old imports working and remains the executable configured in .mcp.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.ncbi.bioproject import (
    BIOPROJECT_ACCESSION_RE,
    bioproject_lookup,
    bioproject_search_term,
    bioproject_summaries_for_ids,
    normalize_bioproject_summary,
)
from mcp.ncbi.biosample import (
    BIOSAMPLE_ACCESSION_RE,
    biosample_lookup,
    biosample_summaries_for_ids,
    normalize_biosample_summary,
    parse_biosample_sampledata,
)
from mcp.ncbi.client import NcbiClient, NcbiConfig
from mcp.ncbi.constants import (
    CITATION_SCHEMA_VERSION,
    DEFAULT_TOOL_NAME,
    JSONRPC_VERSION,
    LATEST_PROTOCOL_VERSION,
    MAX_GEO_IDS,
    MAX_PUBMED_IDS,
    NCBI_EUTILS_BASE_URL,
    RECORD_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    JsonObject,
)
from mcp.ncbi.errors import McpError, NcbiError
from mcp.ncbi.entrez import (
    coerce_database_list,
    coerce_entrez_ids,
    ncbi_db_info,
    ncbi_link,
    ncbi_related_records,
    normalize_database,
    normalize_db_info,
    normalize_linkset,
    require_database,
)
from mcp.ncbi.gene import (
    gene_lookup,
    gene_summaries_for_ids,
    normalize_gene_summary,
    normalize_genomic_location,
    split_comma_list,
    split_pipe_list,
)
from mcp.ncbi.geo import (
    coerce_geo_uids,
    coerce_gse_accession,
    geo_accession_url,
    geo_download_links,
    geo_https_url,
    geo_search,
    geo_series,
    geo_series_ftp_base,
    geo_summaries_for_uids,
    normalize_geo_entry_type,
    normalize_geo_platform,
    normalize_geo_samples,
    normalize_geo_summary,
)
from mcp.ncbi.manifest_records import (
    download_plan_item_record,
    geo_download_plan_record,
    runtime_status_record,
    sample_sheet_record,
    sra_download_plan_item_record,
)
from mcp.ncbi.manifests import (
    coerce_tools,
    geo_download_plan,
    geo_download_plan_payload,
    geo_sample_sheet,
    inspect_runtime_tool,
    omics_sample_sheet,
    resolve_sra_query,
    sra_contextual_query,
    sra_download_item,
    sra_download_items,
    sra_download_plan,
    sra_sample_sheet,
    tool_runtime_status,
)
from mcp.ncbi.omics_records import (
    bioproject_record,
    biosample_record,
    sra_record,
    with_bioproject_compat,
    with_biosample_compat,
    with_sra_compat,
)
from mcp.ncbi.pmc import (
    PMC_ID_CONVERTER_URL,
    coerce_pmc_ids,
    normalize_pmc_conversion,
    pmc_id_convert,
)
from mcp.ncbi.records import (
    bioproject_url,
    biosample_url,
    entrez_link_record,
    gene_display_metadata,
    gene_identifiers,
    gene_links,
    gene_record,
    gene_related,
    gene_url,
    ncbi_database_record,
    ncbi_database_url,
    ncbi_record_url,
    omim_url,
    pmc_article_url,
    pmc_conversion_identifiers,
    pmc_conversion_links,
    pmc_conversion_record,
    sra_run_browser_url,
    sra_run_selector_url,
    sra_url,
    taxonomy_display_metadata,
    taxonomy_links,
    taxonomy_record,
    taxonomy_url,
    with_database_compat,
    with_entrez_links_compat,
    with_gene_compat,
    with_pmc_id_compat,
    with_taxonomy_compat,
)
from mcp.ncbi.pubmed import (
    add_pubmed_date_params,
    coerce_pmids,
    normalize_pubmed_sort,
    normalize_pubmed_summary,
    parse_abstract,
    parse_article_ids,
    parse_authors,
    parse_journal,
    parse_keywords,
    parse_mesh_terms,
    parse_pub_date,
    parse_pubmed_xml,
    pubmed_articles,
    pubmed_fetch,
    pubmed_search,
    pubmed_summaries,
    pubmed_summaries_for_ids,
)
from mcp.ncbi.sra import (
    SRA_ACCESSION_RE,
    normalize_sra_summary,
    parse_sra_expxml,
    parse_sra_runs,
    sra_lookup,
    sra_search,
    sra_summaries_for_ids,
)
from mcp.ncbi.schemas import (
    article_id_value,
    author_names,
    citation_hover,
    citation_summary,
    compact_badges,
    compact_fields,
    display_actions,
    doi_url,
    format_authors,
    geo_dataset_record,
    geo_display_metadata,
    geo_hover,
    geo_identifiers,
    geo_links,
    geo_record_type,
    geo_related,
    journal_abbreviation_name,
    journal_name,
    journal_publication_date,
    pmc_url,
    pubmed_article_citation,
    pubmed_article_record,
    pubmed_identifiers,
    pubmed_links,
    pubmed_minimal_record,
    pubmed_url,
    with_geo_compat,
    with_pubmed_compat,
)
from mcp.ncbi.taxonomy import (
    normalize_taxonomy_summary,
    taxonomy_lookup,
    taxonomy_summaries_for_ids,
)
from mcp.ncbi.tools import TOOL_HANDLERS, ncbi_status, tool_definitions
from mcp.ncbi.utils import (
    element_text,
    normalize_space,
    optional_bool,
    optional_int,
    parse_count,
    require_date_like,
    require_non_empty_string,
    source_info,
    text_from_child,
)


class NcbiMcpServer:
    def __init__(self, client: NcbiClient | None = None) -> None:
        self.client = client or NcbiClient()

    def handle(self, request: JsonObject) -> JsonObject | None:
        if request.get("jsonrpc") != JSONRPC_VERSION:
            raise McpError(-32600, "Request jsonrpc must be '2.0'")
        method = request.get("method")
        request_id = request.get("id")
        params = request.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, dict):
            raise McpError(-32602, "params must be an object")

        if method == "initialize":
            return self._response(request_id, self._initialize(params))
        if method == "notifications/initialized":
            return None
        if method == "ping":
            return self._response(request_id, {})
        if method == "tools/list":
            return self._response(request_id, {"tools": tool_definitions()})
        if method == "tools/call":
            return self._response(request_id, self._call_tool(params))

        if request_id is None:
            return None
        raise McpError(-32601, f"Method not found: {method}")

    def _initialize(self, params: JsonObject) -> JsonObject:
        requested = str(params.get("protocolVersion") or LATEST_PROTOCOL_VERSION)
        protocol_version = (
            requested if requested in SUPPORTED_PROTOCOL_VERSIONS else LATEST_PROTOCOL_VERSION
        )
        return {
            "protocolVersion": protocol_version,
            "capabilities": {
                "tools": {
                    "listChanged": False,
                },
            },
            "serverInfo": {
                "name": "bioinformatics-ncbi",
                "version": "0.1.0",
            },
        }

    def _call_tool(self, params: JsonObject) -> JsonObject:
        name = params.get("name")
        if not isinstance(name, str) or not name:
            raise McpError(-32602, "tools/call params.name is required")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise McpError(-32602, "tools/call params.arguments must be an object")
        handler = TOOL_HANDLERS.get(name)
        if handler is None:
            raise McpError(-32602, f"Tool not found: {name}")

        result = handler(arguments, self.client)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, ensure_ascii=False, indent=2),
                }
            ],
            "structuredContent": result,
        }

    def _response(self, request_id: Any, result: JsonObject) -> JsonObject:
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "result": result,
        }


def error_response(request_id: Any, error: McpError) -> JsonObject:
    payload: JsonObject = {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "error": {
            "code": error.code,
            "message": error.message,
        },
    }
    if error.data is not None:
        payload["error"]["data"] = error.data
    return payload


def internal_error_response(request_id: Any, error: Exception) -> JsonObject:
    message = str(error) or error.__class__.__name__
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "error": {
            "code": -32603,
            "message": message,
        },
    }


def serve_stdio(server: NcbiMcpServer | None = None) -> None:
    server = server or NcbiMcpServer()
    for line in sys.stdin:
        if not line.strip():
            continue
        request_id: Any = None
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise McpError(-32600, "Request must be a JSON object")
            request_id = request.get("id")
            response = server.handle(request)
        except json.JSONDecodeError as exc:
            response = error_response(None, McpError(-32700, "Parse error", str(exc)))
        except McpError as exc:
            response = error_response(request_id, exc)
        except Exception as exc:  # noqa: BLE001 - MCP boundary must not crash.
            print(f"NCBI MCP internal error: {exc}", file=sys.stderr)
            response = internal_error_response(request_id, exc)

        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


__all__ = [
    "BIOPROJECT_ACCESSION_RE",
    "BIOSAMPLE_ACCESSION_RE",
    "CITATION_SCHEMA_VERSION",
    "DEFAULT_TOOL_NAME",
    "JSONRPC_VERSION",
    "LATEST_PROTOCOL_VERSION",
    "MAX_GEO_IDS",
    "MAX_PUBMED_IDS",
    "NCBI_EUTILS_BASE_URL",
    "RECORD_SCHEMA_VERSION",
    "RESULT_SCHEMA_VERSION",
    "SUPPORTED_PROTOCOL_VERSIONS",
    "JsonObject",
    "McpError",
    "NcbiClient",
    "NcbiConfig",
    "NcbiError",
    "NcbiMcpServer",
    "PMC_ID_CONVERTER_URL",
    "SRA_ACCESSION_RE",
    "TOOL_HANDLERS",
    "add_pubmed_date_params",
    "article_id_value",
    "author_names",
    "bioproject_lookup",
    "bioproject_record",
    "bioproject_search_term",
    "bioproject_summaries_for_ids",
    "bioproject_url",
    "biosample_lookup",
    "biosample_record",
    "biosample_summaries_for_ids",
    "biosample_url",
    "citation_hover",
    "citation_summary",
    "coerce_database_list",
    "coerce_entrez_ids",
    "coerce_geo_uids",
    "coerce_gse_accession",
    "coerce_pmc_ids",
    "coerce_pmids",
    "coerce_tools",
    "compact_badges",
    "compact_fields",
    "display_actions",
    "doi_url",
    "download_plan_item_record",
    "element_text",
    "entrez_link_record",
    "error_response",
    "format_authors",
    "gene_display_metadata",
    "gene_identifiers",
    "gene_links",
    "gene_lookup",
    "gene_record",
    "gene_related",
    "gene_summaries_for_ids",
    "gene_url",
    "geo_accession_url",
    "geo_dataset_record",
    "geo_display_metadata",
    "geo_download_plan",
    "geo_download_plan_payload",
    "geo_download_plan_record",
    "geo_download_links",
    "geo_hover",
    "geo_https_url",
    "geo_identifiers",
    "geo_links",
    "geo_record_type",
    "geo_related",
    "geo_sample_sheet",
    "geo_search",
    "geo_series",
    "geo_series_ftp_base",
    "geo_summaries_for_uids",
    "inspect_runtime_tool",
    "internal_error_response",
    "journal_abbreviation_name",
    "journal_name",
    "journal_publication_date",
    "ncbi_database_record",
    "ncbi_database_url",
    "ncbi_db_info",
    "ncbi_link",
    "ncbi_related_records",
    "ncbi_record_url",
    "ncbi_status",
    "normalize_bioproject_summary",
    "normalize_biosample_summary",
    "normalize_database",
    "normalize_db_info",
    "normalize_gene_summary",
    "normalize_genomic_location",
    "normalize_geo_entry_type",
    "normalize_geo_platform",
    "normalize_geo_samples",
    "normalize_geo_summary",
    "normalize_linkset",
    "normalize_pmc_conversion",
    "normalize_pubmed_sort",
    "normalize_pubmed_summary",
    "normalize_sra_summary",
    "normalize_space",
    "normalize_taxonomy_summary",
    "omics_sample_sheet",
    "omim_url",
    "optional_bool",
    "optional_int",
    "parse_abstract",
    "parse_article_ids",
    "parse_authors",
    "parse_count",
    "parse_journal",
    "parse_keywords",
    "parse_mesh_terms",
    "parse_pub_date",
    "parse_pubmed_xml",
    "parse_biosample_sampledata",
    "parse_sra_expxml",
    "parse_sra_runs",
    "pmc_article_url",
    "pmc_conversion_identifiers",
    "pmc_conversion_links",
    "pmc_conversion_record",
    "pmc_id_convert",
    "pmc_url",
    "pubmed_article_citation",
    "pubmed_article_record",
    "pubmed_articles",
    "pubmed_fetch",
    "pubmed_identifiers",
    "pubmed_links",
    "pubmed_minimal_record",
    "pubmed_search",
    "pubmed_summaries",
    "pubmed_summaries_for_ids",
    "pubmed_url",
    "require_date_like",
    "require_database",
    "require_non_empty_string",
    "resolve_sra_query",
    "runtime_status_record",
    "sample_sheet_record",
    "serve_stdio",
    "source_info",
    "split_comma_list",
    "split_pipe_list",
    "sra_contextual_query",
    "sra_download_item",
    "sra_download_items",
    "sra_download_plan",
    "sra_download_plan_item_record",
    "sra_lookup",
    "sra_record",
    "sra_run_browser_url",
    "sra_run_selector_url",
    "sra_search",
    "sra_summaries_for_ids",
    "sra_url",
    "taxonomy_display_metadata",
    "taxonomy_links",
    "taxonomy_lookup",
    "taxonomy_record",
    "taxonomy_summaries_for_ids",
    "taxonomy_url",
    "text_from_child",
    "tool_runtime_status",
    "tool_definitions",
    "with_bioproject_compat",
    "with_biosample_compat",
    "with_database_compat",
    "with_entrez_links_compat",
    "with_geo_compat",
    "with_gene_compat",
    "with_pmc_id_compat",
    "with_pubmed_compat",
    "with_sra_compat",
    "with_taxonomy_compat",
]


if __name__ == "__main__":
    serve_stdio()
