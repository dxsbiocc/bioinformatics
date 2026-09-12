"""MCP tool registry for the UniProt server."""

from __future__ import annotations

import urllib.parse
from typing import Callable

from .client import UniProtClient
from .constants import (
    MAX_RESULTS,
    RESULT_SCHEMA_VERSION,
    UNIPROT_REST_BASE_URL,
    UNIPROT_WEBSITE_BASE_URL,
    JsonObject,
)
from .records import fasta_record, normalize_uniprot_entry, uniprotkb_record
from .utils import (
    normalize_space,
    optional_bool,
    optional_int,
    optional_string_list,
    require_accession,
    require_non_empty_string,
    source_info,
)


def uniprot_status(args: JsonObject, client: UniProtClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "uniprot",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "website_url": UNIPROT_WEBSITE_BASE_URL,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["uniprotkb"],
        "tool_groups": {
            "protein": [
                "uniprot_search",
                "uniprot_lookup",
                "uniprot_fasta",
            ],
            "status": ["uniprot_status"],
        },
        "frontend_components": ["protein"],
        "preview_kinds": [
            "sequence",
            "feature_track",
            "structure_3d",
            "network",
            "citation_list",
            "xref_groups",
        ],
        "detail_sections": [
            "overview",
            "function",
            "features",
            "keywords",
            "comments",
            "cross_references",
            "literature",
        ],
        "pagination": {
            "search_total_header": "x-total-results",
            "next_link_rel": "next",
        },
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload = client.request_json(
            "uniprotkb/search",
            {
                "query": "accession:P04637",
                "format": "json",
                "size": 1,
            },
        )
        results = payload.get("results") if isinstance(payload.get("results"), list) else []
        status["network_check"] = {
            "ok": True,
            "returned": len(results),
        }
    return status


def uniprot_search(args: JsonObject, client: UniProtClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    max_results = optional_int(
        args,
        "max_results",
        default=10,
        minimum=1,
        maximum=MAX_RESULTS,
    )
    include_raw = optional_bool(args, "include_raw", default=False)
    include_features = optional_bool(args, "include_features", default=False)
    max_features = optional_int(
        args,
        "max_features",
        default=20 if include_features else 0,
        minimum=0,
        maximum=200,
    )
    max_comments = optional_int(
        args,
        "max_comments",
        default=3,
        minimum=0,
        maximum=50,
    )
    feature_types = optional_string_list(args, "feature_types")
    search_query = build_search_query(args, query)
    params: JsonObject = {
        "query": search_query,
        "format": "json",
        "size": max_results,
    }
    cursor = normalize_space(args.get("cursor"))
    if cursor:
        params["cursor"] = cursor
    payload, headers = client.request_json_with_headers("uniprotkb/search", params)
    raw_entries = [
        entry
        for entry in payload.get("results", [])
        if isinstance(entry, dict)
    ]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "uniprotkb",
        "query": query,
        "normalized_query": search_query,
        "returned": len(raw_entries),
        "pagination": pagination_info(headers, size=max_results, returned=len(raw_entries)),
        "entries": [
            normalize_uniprot_entry(
                entry,
                include_raw=False,
                include_features=include_features,
                max_features=max_features,
                feature_types=feature_types,
                max_comments=max_comments,
            )
            for entry in raw_entries
        ],
        "records": [
            uniprotkb_record(
                entry,
                include_raw=include_raw,
                include_features=include_features,
                max_features=max_features,
                feature_types=feature_types,
                max_comments=max_comments,
            )
            for entry in raw_entries
        ],
        "source": source_with_release("uniprotkb/search", params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def uniprot_lookup(args: JsonObject, client: UniProtClient) -> JsonObject:
    accession = require_accession(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    include_features = optional_bool(args, "include_features", default=True)
    max_features = optional_int(
        args,
        "max_features",
        default=40,
        minimum=0,
        maximum=500,
    )
    max_comments = optional_int(
        args,
        "max_comments",
        default=8,
        minimum=0,
        maximum=100,
    )
    feature_types = optional_string_list(args, "feature_types")
    endpoint = f"uniprotkb/{urllib.parse.quote(accession, safe='')}"
    params: JsonObject = {"format": "json"}
    entry, headers = client.request_json_with_headers(endpoint, params)
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "uniprotkb",
        "query": accession,
        "returned": 1,
        "entries": [
            normalize_uniprot_entry(
                entry,
                include_raw=False,
                include_features=include_features,
                max_features=max_features,
                feature_types=feature_types,
                max_comments=max_comments,
            )
        ],
        "records": [
            uniprotkb_record(
                entry,
                include_raw=include_raw,
                include_features=include_features,
                max_features=max_features,
                feature_types=feature_types,
                max_comments=max_comments,
            )
        ],
        "source": source_with_release(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = entry
    return response


def uniprot_fasta(args: JsonObject, client: UniProtClient) -> JsonObject:
    accession = require_accession(args)
    endpoint = f"uniprotkb/{urllib.parse.quote(accession, safe='')}.fasta"
    fasta_text, headers = client.request_text_with_headers(
        endpoint,
        {},
        accept="text/x-fasta,text/plain",
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "uniprotkb",
        "query": accession,
        "returned": 1 if fasta_text.strip() else 0,
        "fasta": fasta_text,
        "records": [fasta_record(accession, fasta_text)] if fasta_text.strip() else [],
        "source": source_with_release(endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    return response


def build_search_query(args: JsonObject, query: str) -> str:
    clauses = [f"({query})"]
    organism = normalize_space(args.get("organism"))
    if organism:
        if organism.isdigit():
            clauses.append(f"(organism_id:{organism})")
        else:
            escaped = organism.replace('"', '\\"')
            clauses.append(f'(organism_name:"{escaped}")')
    if "reviewed" in args:
        reviewed = optional_bool(args, "reviewed", default=False)
        clauses.append(f"(reviewed:{str(reviewed).lower()})")
    return " AND ".join(clauses)


def pagination_info(
    headers: dict[str, str],
    *,
    size: int,
    returned: int,
) -> JsonObject:
    total = parse_optional_int(headers.get("x-total-results"))
    next_url = link_header_url(headers.get("link", ""), rel="next")
    info: JsonObject = {
        "size": size,
        "returned": returned,
        "total": total,
        "next_url": next_url,
        "next_cursor": cursor_from_url(next_url),
    }
    return {key: value for key, value in info.items() if value not in {"", None}}


def parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def link_header_url(header: str, *, rel: str) -> str:
    for part in header.split(","):
        url_part, separator, meta = part.partition(";")
        if not separator:
            continue
        if f'rel="{rel}"' not in meta:
            continue
        url = url_part.strip()
        if url.startswith("<") and url.endswith(">"):
            return url[1:-1]
    return ""


def cursor_from_url(url: str) -> str:
    if not url:
        return ""
    parsed = urllib.parse.urlparse(url)
    values = urllib.parse.parse_qs(parsed.query).get("cursor", [])
    return values[0] if values else ""


def source_with_release(
    endpoint: str,
    params: JsonObject,
    headers: dict[str, str],
) -> JsonObject:
    source = source_info(endpoint, params)
    release = normalize_space(headers.get("x-uniprot-release"))
    release_date = normalize_space(headers.get("x-uniprot-release-date"))
    api_deployment_date = normalize_space(headers.get("x-api-deployment-date"))
    if release:
        source["release"] = release
    if release_date:
        source["release_date"] = release_date
    if api_deployment_date:
        source["api_deployment_date"] = api_deployment_date
    return source


def tool_definitions() -> list[JsonObject]:
    read_only_annotations = {
        "readOnlyHint": True,
        "openWorldHint": True,
    }
    return [
        {
            "name": "uniprot_search",
            "title": "Search UniProtKB",
            "description": (
                "Search UniProtKB through the UniProt REST API and return "
                "front-end-compatible protein records with display previews."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "UniProt query string, for example gene:TP53.",
                    },
                    "organism": {
                        "type": "string",
                        "description": "Optional organism name or TaxID, for example 9606.",
                    },
                    "reviewed": {
                        "type": "boolean",
                        "description": "Optional Swiss-Prot reviewed filter.",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_RESULTS,
                        "default": 10,
                    },
                    "cursor": {
                        "type": "string",
                        "description": "Optional UniProt pagination cursor from pagination.next_cursor.",
                    },
                    "include_features": {
                        "type": "boolean",
                        "default": False,
                        "description": "Return bounded sequence feature rows for richer detail rendering.",
                    },
                    "feature_types": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        ],
                        "description": "Optional feature type filter, for example Domain, Region, or Modified residue.",
                    },
                    "max_features": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 200,
                        "default": 0,
                    },
                    "max_comments": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 50,
                        "default": 3,
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
            "name": "uniprot_lookup",
            "title": "Look up a UniProtKB entry",
            "description": (
                "Fetch one UniProtKB accession and return normalized protein, "
                "gene, organism, sequence length, cross-reference, preview, and URL metadata."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "accession": {
                        "type": "string",
                        "description": "UniProtKB accession, for example P04637.",
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                    "include_features": {
                        "type": "boolean",
                        "default": True,
                        "description": "Return bounded sequence feature rows for detail rendering.",
                    },
                    "feature_types": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        ],
                        "description": "Optional feature type filter, for example Domain, Region, or Modified residue.",
                    },
                    "max_features": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 500,
                        "default": 40,
                    },
                    "max_comments": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                        "default": 8,
                    },
                },
                "required": ["accession"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "uniprot_fasta",
            "title": "Fetch UniProtKB FASTA",
            "description": (
                "Fetch the FASTA sequence for one UniProtKB accession and return "
                "a protein sequence record plus the raw FASTA text."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "accession": {
                        "type": "string",
                        "description": "UniProtKB accession, for example P04637.",
                    }
                },
                "required": ["accession"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "uniprot_status",
            "title": "Inspect UniProt MCP status",
            "description": "Return configured UniProt MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "check_network": {
                        "type": "boolean",
                        "default": False,
                    }
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
    ]


TOOL_HANDLERS: dict[str, Callable[[JsonObject, UniProtClient], JsonObject]] = {
    "uniprot_search": uniprot_search,
    "uniprot_lookup": uniprot_lookup,
    "uniprot_fasta": uniprot_fasta,
    "uniprot_status": uniprot_status,
}
