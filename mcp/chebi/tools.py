"""MCP tool registry for the ChEBI server."""

from __future__ import annotations

from .client import ChebiClient
from .constants import DEFAULT_RESULTS, MAX_RELATIONS, MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import ChebiError
from .records import chebi_compound_record, chebi_relation_record
from .utils import max_results, optional_bool, optional_int, require_chebi_id, require_query, safe_dict, safe_list, source_info


SEARCH_ENDPOINT = "chebi/backend/api/public/es_search/"
COMPOUND_ENDPOINT_PREFIX = "chebi/backend/api/public/compound"
CHILDREN_ENDPOINT_PREFIX = "chebi/backend/api/public/ontology/children"
PARENTS_ENDPOINT_PREFIX = "chebi/backend/api/public/ontology/parents"


def chebi_status(args: JsonObject, client: ChebiClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "chebi",
        "version": "0.1.0",
        "api_base_url": client.config.api_base_url,
        "website_base_url": client.config.website_base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "tool_groups": {
            "compound": ["chebi_compound_search", "chebi_compound_lookup"],
            "ontology": ["chebi_ontology_children", "chebi_ontology_parents"],
            "status": ["chebi_status"],
        },
        "frontend_components": ["compound", "ontology_term"],
        "preview_kinds": ["table", "chemical_structure", "xref_groups", "citation_list", "text", "network"],
        "record_schema_version": "bioinformatics.record.v1",
        "backend_api_family": "EBI ChEBI public backend API",
    }
    if check_network:
        payload, headers, url = client.request_json_with_headers(SEARCH_ENDPOINT, {"query": "caffeine", "size": 1})
        rows = search_rows(payload)[:1]
        status["network_check"] = {
            "ok": True,
            "returned": len(rows),
            "example_id": rows[0].get("chebi_accession") if rows else None,
            "content_type": headers.get("content-type"),
            "url": url,
        }
    return status


def chebi_compound_search(args: JsonObject, client: ChebiClient) -> JsonObject:
    query = require_query(args)
    limit = max_results(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    params: JsonObject = {"query": query, "size": limit}
    payload, headers, url = client.request_json_with_headers(SEARCH_ENDPOINT, params)
    rows = search_rows(payload)[:limit]
    records = [
        chebi_compound_record(row, website_base_url=client.config.website_base_url, api_base_url=client.config.api_base_url)
        for row in rows
    ]
    response = compound_response(query=query, records=records, endpoint=SEARCH_ENDPOINT, params=params, headers=headers, url=url)
    response["total"] = search_total(payload, rows)
    response["items"] = [record_summary(record) for record in records]
    if include_raw:
        response["raw"] = payload
    return response


def chebi_compound_lookup(args: JsonObject, client: ChebiClient) -> JsonObject:
    chebi_id = require_chebi_id(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"{COMPOUND_ENDPOINT_PREFIX}/{chebi_id}/"
    payload, headers, url = client.request_json_with_headers(endpoint, {})
    if not isinstance(payload, dict) or not payload.get("chebi_accession"):
        raise ChebiError(f"No ChEBI compound found for {chebi_id}")
    record = chebi_compound_record(payload, website_base_url=client.config.website_base_url, api_base_url=client.config.api_base_url)
    response = compound_response(query=chebi_id, records=[record], endpoint=endpoint, params={}, headers=headers, url=url)
    response["items"] = [record_summary(record)]
    if include_raw:
        response["raw"] = payload
    return response


def chebi_ontology_children(args: JsonObject, client: ChebiClient) -> JsonObject:
    return relation_search(args, client, direction="children", endpoint_prefix=CHILDREN_ENDPOINT_PREFIX)


def chebi_ontology_parents(args: JsonObject, client: ChebiClient) -> JsonObject:
    return relation_search(args, client, direction="parents", endpoint_prefix=PARENTS_ENDPOINT_PREFIX)


def relation_search(args: JsonObject, client: ChebiClient, *, direction: str, endpoint_prefix: str) -> JsonObject:
    chebi_id = require_chebi_id(args)
    limit = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RELATIONS)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"{endpoint_prefix}/{chebi_id}/"
    payload, headers, url = client.request_json_with_headers(endpoint, {})
    query_name = ""
    if isinstance(payload, dict):
        query_name = str(payload.get("name") or "")
    rows = relation_rows(payload, direction)[:limit]
    records = [
        chebi_relation_record(row, direction=direction, query_id=chebi_id, query_name=query_name, website_base_url=client.config.website_base_url)
        for row in rows
    ]
    response = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "chebi",
        "query": chebi_id,
        "direction": direction,
        "returned": len(records),
        "total": relation_total(payload, rows),
        "records": records,
        "terms": [record_summary(record) for record in records],
        "source": source_with_headers(endpoint, {}, headers, url),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def search_rows(payload: object) -> list[JsonObject]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get("results")
    if not isinstance(rows, list):
        return []
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        source = safe_dict(row.get("_source")) if isinstance(row.get("_source"), dict) else row
        if source:
            normalized.append(source)
    return normalized


def search_total(payload: object, rows: list[JsonObject]) -> int:
    if isinstance(payload, dict):
        try:
            return int(payload["total"])
        except (KeyError, TypeError, ValueError):
            pass
    return len(rows)


def relation_rows(payload: object, direction: str) -> list[JsonObject]:
    if not isinstance(payload, dict):
        return []
    relations = safe_dict(payload.get("ontology_relations"))
    key = "incoming_relations" if direction == "children" else "outgoing_relations"
    return [row for row in safe_list(relations.get(key)) if isinstance(row, dict)]


def relation_total(payload: object, rows: list[JsonObject]) -> int:
    if isinstance(payload, dict):
        relations = safe_dict(payload.get("ontology_relations"))
        for key in ["incoming_relations", "outgoing_relations"]:
            value = relations.get(key)
            if isinstance(value, list):
                return len(value)
    return len(rows)


def compound_response(*, query: str, records: list[JsonObject], endpoint: str, params: JsonObject, headers: dict[str, str], url: str) -> JsonObject:
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "chebi",
        "query": query,
        "returned": len(records),
        "records": records,
        "source": source_with_headers(endpoint, params, headers, url),
    }
    response["provenance"] = response["source"]
    return response


def record_summary(record: JsonObject) -> JsonObject:
    return {
        "id": record["id"],
        "title": record["title"],
        "type": record["type"],
        "url": record["url"],
    }


def source_with_headers(endpoint: str, params: JsonObject, headers: dict[str, str], url: str) -> JsonObject:
    source = source_info(endpoint, params, url=url)
    if headers.get("content-type"):
        source["content_type"] = headers["content-type"]
    return source


def tool_definitions() -> list[JsonObject]:
    common_search_properties = {
        "query": {"type": "string", "description": "Search text, for example caffeine, glucose, or CHEBI names."},
        "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
        "include_raw": {"type": "boolean", "default": False},
    }
    relation_properties = {
        "chebi_id": {"type": "string", "description": "ChEBI identifier such as CHEBI:27732 or 27732."},
        "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RELATIONS, "default": DEFAULT_RESULTS},
        "include_raw": {"type": "boolean", "default": False},
    }
    return [
        {
            "name": "chebi_compound_search",
            "title": "Search ChEBI compounds",
            "description": "Search ChEBI compounds through EBI public search and return compound records with chemical previews and ChEBI links.",
            "inputSchema": {
                "type": "object",
                "properties": common_search_properties,
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "chebi_compound_lookup",
            "title": "Look up a ChEBI compound",
            "description": "Fetch one ChEBI compound by CHEBI ID and return names, formula, structure identifiers, xrefs, citations, origins, ontology relations, and URLs.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "chebi_id": {"type": "string", "description": "ChEBI identifier such as CHEBI:27732 or 27732."},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["chebi_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "chebi_ontology_children",
            "title": "List child compounds for a ChEBI term",
            "description": "Return incoming ChEBI ontology relations as front-end-compatible ontology-term records with a small relation network preview.",
            "inputSchema": {
                "type": "object",
                "properties": relation_properties,
                "required": ["chebi_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "chebi_ontology_parents",
            "title": "List parent/role terms for a ChEBI term",
            "description": "Return outgoing ChEBI ontology relations as front-end-compatible ontology-term records with a small relation network preview.",
            "inputSchema": {
                "type": "object",
                "properties": relation_properties,
                "required": ["chebi_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "chebi_status",
            "title": "Inspect ChEBI MCP status",
            "description": "Return configured ChEBI MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
    ]


TOOL_HANDLERS = {
    "chebi_compound_search": chebi_compound_search,
    "chebi_compound_lookup": chebi_compound_lookup,
    "chebi_ontology_children": chebi_ontology_children,
    "chebi_ontology_parents": chebi_ontology_parents,
    "chebi_status": chebi_status,
}
