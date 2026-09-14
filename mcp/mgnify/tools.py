"""MCP tool registry for the MGnify server."""

from __future__ import annotations

import urllib.parse

from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition

from .client import MgnifyClient
from .constants import DEFAULT_RESULTS, MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import MgnifyError
from .records import mgnify_biome_record, mgnify_sample_record, mgnify_study_record
from .utils import (
    optional_bool,
    optional_int,
    require_biome_id,
    require_non_empty_string,
    require_sample_accession,
    require_study_accession,
    source_info,
)


def mgnify_status(args: JsonObject, client: MgnifyClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "mgnify",
        "version": "0.1.0",
        "api_base_url": client.config.api_base_url,
        "website_base_url": client.config.website_base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["mgnify"],
        "tool_groups": {
            "studies": ["mgnify_study_lookup", "mgnify_study_search"],
            "samples": ["mgnify_sample_lookup"],
            "biomes": ["mgnify_biome_lookup"],
            "status": ["mgnify_status"],
        },
        "frontend_components": ["project", "sample", "taxonomy"],
        "preview_kinds": ["table", "xref_groups"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload, headers = client.request_json_with_headers("studies", {"page_size": 1})
        record = first_record(payload)
        status["network_check"] = {
            "ok": True,
            "example_accession": record.get("id") if isinstance(record, dict) else None,
            "content_type": headers.get("content-type"),
        }
    return status


def mgnify_study_lookup(args: JsonObject, client: MgnifyClient) -> JsonObject:
    accession = require_study_accession(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"studies/{accession}"
    payload, headers = client.request_json_with_headers(endpoint, {})
    item = ensure_record(payload, accession)
    record = mgnify_study_record(item, website_base_url=client.config.website_base_url, api_base_url=client.config.api_base_url)
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "mgnify",
        "query": accession,
        "returned": 1,
        "study": summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, {}, headers, client.build_url(endpoint, {})),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def mgnify_study_search(args: JsonObject, client: MgnifyClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    max_results = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = "studies"
    params: JsonObject = {"search": query, "page_size": max_results}
    payload, headers = client.request_json_with_headers(endpoint, params)
    rows = collection_records(payload)[:max_results]
    records = [mgnify_study_record(item, website_base_url=client.config.website_base_url, api_base_url=client.config.api_base_url) for item in rows]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "mgnify",
        "query": query,
        "returned": len(records),
        "total": total_count(payload),
        "studies": [summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, params, headers, client.build_url(endpoint, params)),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def mgnify_sample_lookup(args: JsonObject, client: MgnifyClient) -> JsonObject:
    accession = require_sample_accession(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"samples/{accession}"
    payload, headers = client.request_json_with_headers(endpoint, {})
    item = ensure_record(payload, accession)
    record = mgnify_sample_record(item, website_base_url=client.config.website_base_url, api_base_url=client.config.api_base_url)
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "mgnify",
        "query": accession,
        "returned": 1,
        "sample": summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, {}, headers, client.build_url(endpoint, {})),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def mgnify_biome_lookup(args: JsonObject, client: MgnifyClient) -> JsonObject:
    biome_id = require_biome_id(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"biomes/{urllib.parse.quote(biome_id, safe=':')}"
    payload, headers = client.request_json_with_headers(endpoint, {})
    item = ensure_record(payload, biome_id)
    record = mgnify_biome_record(item, website_base_url=client.config.website_base_url, api_base_url=client.config.api_base_url)
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "mgnify",
        "query": biome_id,
        "returned": 1,
        "biome": summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, {}, headers, client.build_url(endpoint, {})),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def ensure_record(payload: object, identifier: str) -> JsonObject:
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"]
    raise MgnifyError(f"MGnify record not found for {identifier}")


def first_record(payload: object) -> JsonObject:
    rows = collection_records(payload)
    return rows[0] if rows else {}


def collection_records(payload: object) -> list[JsonObject]:
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return [item for item in payload["data"] if isinstance(item, dict)]
    return []


def total_count(payload: object) -> int | None:
    if not isinstance(payload, dict):
        return None
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    pagination = meta.get("pagination") if isinstance(meta.get("pagination"), dict) else {}
    count = pagination.get("count")
    return int(count) if isinstance(count, int) else None


def summary(record: JsonObject) -> JsonObject:
    data = record["data"]
    return {
        "id": data.get("accession") or data.get("lineage"),
        "title": data.get("name") or data.get("sample_name") or data.get("lineage"),
        "url": data["url"],
    }


def source_with_headers(endpoint: str, params: JsonObject, headers: dict[str, str], url: str) -> JsonObject:
    source = source_info(endpoint, params)
    source["url"] = url
    if headers.get("content-type"):
        source["content_type"] = headers["content-type"]
    return source


def tool_definitions() -> list[JsonObject]:
    return [
        parameter_domains_tool_definition("mgnify_parameter_domains"),
        {
            "name": "mgnify_study_lookup",
            "title": "Look up an MGnify study",
            "description": "Fetch one MGnify study by MGYS accession and return a front-end-compatible project record with biome, sample-count, BioProject, and relationship-link previews.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "accession": {"type": "string", "description": "MGnify study accession, for example MGYS00006862."},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["accession"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "mgnify_study_search",
            "title": "Search MGnify studies",
            "description": "Search MGnify studies and return bounded front-end-compatible project records.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text query such as human gut, marine, soil, or BioProject text."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "mgnify_sample_lookup",
            "title": "Look up an MGnify sample",
            "description": "Fetch one MGnify sample and return a front-end-compatible sample record with BioSample, biome, species, study links, and metadata-table previews.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "accession": {"type": "string", "description": "MGnify sample accession, for example SRS10016989."},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["accession"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "mgnify_biome_lookup",
            "title": "Look up an MGnify biome",
            "description": "Fetch one MGnify biome lineage and return a front-end-compatible taxonomy record with study/sample/genome relationship links.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "biome_id": {"type": "string", "description": "MGnify biome lineage, for example root:Host-associated:Human:Digestive system:Large intestine."},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["biome_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "mgnify_status",
            "title": "Inspect MGnify MCP status",
            "description": "Return configured MGnify MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
    ]


TOOL_HANDLERS = {
    "mgnify_parameter_domains": make_parameter_domains_handler("mgnify", "mgnify_parameter_domains", tool_definitions),
    "mgnify_study_lookup": mgnify_study_lookup,
    "mgnify_study_search": mgnify_study_search,
    "mgnify_sample_lookup": mgnify_sample_lookup,
    "mgnify_biome_lookup": mgnify_biome_lookup,
    "mgnify_status": mgnify_status,
}
