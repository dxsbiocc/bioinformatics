"""MCP tool registry for the RNAcentral server."""

from __future__ import annotations

from .client import RnaCentralClient
from .constants import MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import RnaCentralError
from .records import rna_entry_record, xrefs_record
from .utils import max_results, optional_bool, optional_taxid, page, require_query, require_rnacentral_id, source_info


def rnacentral_status(args: JsonObject, client: RnaCentralClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "rnacentral",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "tool_groups": {
            "entries": ["rnacentral_entry_lookup", "rnacentral_search"],
            "cross_references": ["rnacentral_xrefs"],
            "status": ["rnacentral_status"],
        },
        "frontend_components": ["genomic_feature", "identifier_conversion"],
        "preview_kinds": ["sequence", "table", "xref_groups", "text"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        endpoint = "rna/URS000075C808/9606/"
        payload, headers = client.request_json_with_headers(endpoint, {})
        status["network_check"] = {
            "ok": True,
            "example_id": payload.get("rnacentral_id") if isinstance(payload, dict) else None,
            "example_description": payload.get("description") if isinstance(payload, dict) else None,
            "content_type": headers.get("content-type"),
        }
    return status


def rnacentral_entry_lookup(args: JsonObject, client: RnaCentralClient) -> JsonObject:
    rnacentral_id = require_rnacentral_id(args)
    taxid = optional_taxid(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"rna/{rnacentral_id}/{taxid}/" if taxid else f"rna/{rnacentral_id}/"
    payload, headers = client.request_json_with_headers(endpoint, {})
    if not isinstance(payload, dict) or not payload.get("rnacentral_id"):
        raise RnaCentralError(f"No RNAcentral entry found for {rnacentral_id}")
    record = rna_entry_record(payload)
    response = records_response(
        query=f"{rnacentral_id}_{taxid}" if taxid else rnacentral_id,
        records=[record],
        endpoint=endpoint,
        params={},
        headers=headers,
    )
    response["entries"] = [entry_summary(record)]
    if include_raw:
        response["raw"] = payload
    return response


def rnacentral_search(args: JsonObject, client: RnaCentralClient) -> JsonObject:
    query = require_query(args)
    limit = max_results(args)
    selected_page = page(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = "rna/"
    params: JsonObject = {"q": query, "page_size": limit, "page": selected_page}
    payload, headers = client.request_json_with_headers(endpoint, params)
    rows = paginated_results(payload)[:limit]
    records = [rna_entry_record(row) for row in rows]
    response = records_response(
        query=query,
        records=records,
        endpoint=endpoint,
        params=params,
        headers=headers,
    )
    response["entries"] = [entry_summary(record) for record in records]
    response["page"] = selected_page
    response["pagination"] = pagination(payload)
    if include_raw:
        response["raw"] = payload
    return response


def rnacentral_xrefs(args: JsonObject, client: RnaCentralClient) -> JsonObject:
    rnacentral_id = require_rnacentral_id(args)
    limit = max_results(args)
    selected_page = page(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"rna/{rnacentral_id}/xrefs/"
    params: JsonObject = {"page_size": limit, "page": selected_page}
    payload, headers = client.request_json_with_headers(endpoint, params)
    rows = paginated_results(payload)[:limit]
    total = paginated_count(payload, rows)
    record = xrefs_record(rnacentral_id, rows, total=total)
    response = records_response(
        query=rnacentral_id,
        records=[record],
        endpoint=endpoint,
        params=params,
        headers=headers,
    )
    response["xrefs"] = record["data"]["xrefs"]
    response["page"] = selected_page
    response["pagination"] = pagination(payload)
    if include_raw:
        response["raw"] = payload
    return response


def paginated_results(payload: object) -> list[JsonObject]:
    if isinstance(payload, dict):
        rows = payload.get("results")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def paginated_count(payload: object, rows: list[JsonObject]) -> int:
    if isinstance(payload, dict) and isinstance(payload.get("count"), int):
        return int(payload["count"])
    return len(rows)


def pagination(payload: object) -> JsonObject:
    if not isinstance(payload, dict):
        return {}
    return {
        "count": payload.get("count"),
        "next": payload.get("next"),
        "previous": payload.get("previous"),
    }


def records_response(
    *,
    query: str,
    records: list[JsonObject],
    endpoint: str,
    params: JsonObject,
    headers: dict[str, str],
) -> JsonObject:
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "rnacentral",
        "query": query,
        "returned": len(records),
        "records": records,
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    return response


def entry_summary(record: JsonObject) -> JsonObject:
    data = record["data"]
    return {
        "rnacentral_id": data["rnacentral_id"],
        "title": record["title"],
        "species": data["species"],
        "taxid": data["taxid"],
        "rna_type": data["rna_type"],
        "length": data["length"],
        "url": record["url"],
    }


def source_with_headers(endpoint: str, params: JsonObject, headers: dict[str, str]) -> JsonObject:
    source = source_info(endpoint, params)
    if headers.get("content-type"):
        source["content_type"] = headers["content-type"]
    return source


def tool_definitions() -> list[JsonObject]:
    return [
        {
            "name": "rnacentral_entry_lookup",
            "title": "Look up an RNAcentral RNA entry",
            "description": "Fetch one RNAcentral URS entry, optionally scoped to a species TaxID, and return a front-end-compatible genomic feature record with sequence, RNA type, organism, and links.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "rnacentral_id": {"type": "string", "description": "RNAcentral URS identifier, for example URS000075C808 or URS000075C808_9606."},
                    "taxid": {"type": "integer", "minimum": 1, "description": "Optional NCBI TaxID, for example 9606."},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["rnacentral_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "rnacentral_search",
            "title": "Search RNAcentral RNA entries",
            "description": "Run a bounded RNAcentral text search and return front-end-compatible RNA sequence records.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query, for example HOTAIR, miR-21, or an RNA type."},
                    "page": {"type": "integer", "minimum": 1, "default": 1},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": 10},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "rnacentral_xrefs",
            "title": "List RNAcentral cross-references",
            "description": "Fetch bounded RNAcentral cross-references for one URS identifier and return grouped xref/table previews.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "rnacentral_id": {"type": "string", "description": "RNAcentral URS identifier, for example URS000075C808."},
                    "page": {"type": "integer", "minimum": 1, "default": 1},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": 10},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["rnacentral_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "rnacentral_status",
            "title": "Inspect RNAcentral MCP status",
            "description": "Return configured RNAcentral MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
    ]


TOOL_HANDLERS = {
    "rnacentral_entry_lookup": rnacentral_entry_lookup,
    "rnacentral_search": rnacentral_search,
    "rnacentral_xrefs": rnacentral_xrefs,
    "rnacentral_status": rnacentral_status,
}

