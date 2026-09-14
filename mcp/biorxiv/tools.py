"""MCP tool registry for the bioRxiv/medRxiv server."""

from __future__ import annotations

from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition
from .client import BioRxivClient
from .constants import MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import BioRxivError
from .records import preprint_record, publication_link_record
from .utils import (
    date_interval_or_recent_days,
    max_results,
    optional_bool,
    optional_int,
    optional_string,
    require_doi,
    require_server,
    source_info,
)


def biorxiv_status(args: JsonObject, client: BioRxivClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "biorxiv",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["biorxiv", "medrxiv"],
        "tool_groups": {
            "preprints": ["biorxiv_preprint_lookup", "biorxiv_preprint_interval"],
            "publication_links": ["biorxiv_publication_lookup", "biorxiv_publication_interval"],
            "status": ["biorxiv_status"],
        },
        "frontend_components": ["citation"],
        "preview_kinds": ["citation_list", "table", "xref_groups", "text"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        endpoint = "details/biorxiv/10.1101/2020.09.09.20191205/na/json"
        payload, headers = client.request_json_with_headers(endpoint, {})
        rows = collection(payload)
        status["network_check"] = {
            "ok": True,
            "example_doi": rows[0].get("doi") if rows else None,
            "example_title": rows[0].get("title") if rows else None,
            "content_type": headers.get("content-type"),
        }
    return status


def biorxiv_preprint_lookup(args: JsonObject, client: BioRxivClient) -> JsonObject:
    server = require_server(args)
    doi = require_doi(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"details/{server}/{doi}/na/json"
    payload, headers = client.request_json_with_headers(endpoint, {})
    rows = collection(payload)
    if not rows:
        raise BioRxivError(f"No {server} preprint found for DOI {doi}")
    records = [preprint_record(rows[0], server=server)]
    response = preprint_response(
        query=doi,
        records=records,
        endpoint=endpoint,
        params={},
        headers=headers,
    )
    if include_raw:
        response["raw"] = payload
    return response


def biorxiv_preprint_interval(args: JsonObject, client: BioRxivClient) -> JsonObject:
    server = require_server(args)
    limit = max_results(args)
    cursor = optional_int(args, "cursor", default=0, minimum=0, maximum=100000)
    category = optional_string(args, "category")
    include_raw = optional_bool(args, "include_raw", default=False)
    interval, interval_params = date_interval_or_recent_days(args)
    endpoint = f"details/{server}/{interval}/{cursor}/json"
    params: JsonObject = {"category": category} if category else {}
    payload, headers = client.request_json_with_headers(endpoint, params)
    rows = collection(payload)[:limit]
    records = [preprint_record(row, server=server) for row in rows]
    response = preprint_response(
        query=category or interval,
        records=records,
        endpoint=endpoint,
        params={**interval_params, **params, "cursor": cursor, "max_results": limit},
        headers=headers,
    )
    response["server"] = server
    response["cursor"] = cursor
    response["interval"] = interval_params
    if include_raw:
        response["raw"] = payload
    return response


def biorxiv_publication_lookup(args: JsonObject, client: BioRxivClient) -> JsonObject:
    server = require_server(args)
    doi = require_doi(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"pubs/{server}/{doi}/na/json"
    payload, headers = client.request_json_with_headers(endpoint, {})
    rows = collection(payload)
    if not rows:
        raise BioRxivError(f"No {server} publication link found for DOI {doi}")
    records = [publication_link_record(rows[0], server=server)]
    response = publication_response(
        query=doi,
        records=records,
        endpoint=endpoint,
        params={},
        headers=headers,
    )
    if include_raw:
        response["raw"] = payload
    return response


def biorxiv_publication_interval(args: JsonObject, client: BioRxivClient) -> JsonObject:
    server = require_server(args)
    limit = max_results(args)
    cursor = optional_int(args, "cursor", default=0, minimum=0, maximum=100000)
    include_raw = optional_bool(args, "include_raw", default=False)
    interval, interval_params = date_interval_or_recent_days(args)
    endpoint = f"pubs/{server}/{interval}/{cursor}"
    payload, headers = client.request_json_with_headers(endpoint, {})
    rows = collection(payload)[:limit]
    records = [publication_link_record(row, server=server) for row in rows]
    response = publication_response(
        query=interval,
        records=records,
        endpoint=endpoint,
        params={**interval_params, "cursor": cursor, "max_results": limit},
        headers=headers,
    )
    response["server"] = server
    response["cursor"] = cursor
    response["interval"] = interval_params
    if include_raw:
        response["raw"] = payload
    return response


def collection(payload: object) -> list[JsonObject]:
    if isinstance(payload, dict):
        rows = payload.get("collection")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def preprint_response(
    *,
    query: str,
    records: list[JsonObject],
    endpoint: str,
    params: JsonObject,
    headers: dict[str, str],
) -> JsonObject:
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "biorxiv",
        "query": query,
        "returned": len(records),
        "preprints": [preprint_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    return response


def publication_response(
    *,
    query: str,
    records: list[JsonObject],
    endpoint: str,
    params: JsonObject,
    headers: dict[str, str],
) -> JsonObject:
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "biorxiv",
        "query": query,
        "returned": len(records),
        "publication_links": [publication_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    return response


def preprint_summary(record: JsonObject) -> JsonObject:
    data = record["data"]
    return {
        "doi": data["doi"],
        "title": data["title"],
        "date": data["date"],
        "category": data["category"],
        "url": data["url"],
    }


def publication_summary(record: JsonObject) -> JsonObject:
    data = record["data"]
    return {
        "preprint_doi": data["preprint_doi"],
        "published_doi": data["published_doi"],
        "published_journal": data["published_journal"],
        "published_date": data["published_date"],
        "url": data["published_url"] or data["preprint_url"],
    }


def source_with_headers(endpoint: str, params: JsonObject, headers: dict[str, str]) -> JsonObject:
    source = source_info(endpoint, params)
    if headers.get("content-type"):
        source["content_type"] = headers["content-type"]
    return source


def tool_definitions() -> list[JsonObject]:
    return [
        parameter_domains_tool_definition("biorxiv_parameter_domains"),
        {
            "name": "biorxiv_preprint_lookup",
            "title": "Look up a bioRxiv or medRxiv preprint",
            "description": "Fetch one bioRxiv or medRxiv preprint by DOI and return a front-end-compatible citation record with DOI, authors, abstract, version, category, and links.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "server": {"type": "string", "enum": ["biorxiv", "medrxiv"], "default": "biorxiv"},
                    "doi": {"type": "string", "description": "Preprint DOI, for example 10.1101/2020.09.09.20191205."},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["doi"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "biorxiv_preprint_interval",
            "title": "List recent bioRxiv or medRxiv preprints",
            "description": "Fetch bounded preprint metadata by date range or recent-day interval. Results are front-end-compatible citation records.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "server": {"type": "string", "enum": ["biorxiv", "medrxiv"], "default": "biorxiv"},
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD. Must be paired with end_date."},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD. Must be paired with start_date."},
                    "recent_days": {"type": "integer", "minimum": 1, "maximum": 365, "default": 7},
                    "cursor": {"type": "integer", "minimum": 0, "default": 0},
                    "category": {"type": "string", "description": "Optional bioRxiv/medRxiv category filter when supported by the API."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": 10},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "biorxiv_publication_lookup",
            "title": "Look up a preprint publication link",
            "description": "Fetch formal-publication linkage for a bioRxiv or medRxiv DOI, including published DOI and journal when available.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "server": {"type": "string", "enum": ["biorxiv", "medrxiv"], "default": "biorxiv"},
                    "doi": {"type": "string", "description": "Preprint DOI, for example 10.1101/2020.09.09.20191205."},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["doi"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "biorxiv_publication_interval",
            "title": "List preprints with publication links",
            "description": "Fetch bounded formal-publication linkage rows by date range or recent-day interval.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "server": {"type": "string", "enum": ["biorxiv", "medrxiv"], "default": "biorxiv"},
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD. Must be paired with end_date."},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD. Must be paired with start_date."},
                    "recent_days": {"type": "integer", "minimum": 1, "maximum": 365, "default": 7},
                    "cursor": {"type": "integer", "minimum": 0, "default": 0},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": 10},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "biorxiv_status",
            "title": "Inspect bioRxiv/medRxiv MCP status",
            "description": "Return configured bioRxiv/medRxiv MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
    ]


TOOL_HANDLERS = {
    "biorxiv_parameter_domains": make_parameter_domains_handler("biorxiv", "biorxiv_parameter_domains", tool_definitions),
    "biorxiv_preprint_lookup": biorxiv_preprint_lookup,
    "biorxiv_preprint_interval": biorxiv_preprint_interval,
    "biorxiv_publication_lookup": biorxiv_publication_lookup,
    "biorxiv_publication_interval": biorxiv_publication_interval,
    "biorxiv_status": biorxiv_status,
}

