"""MCP tool registry for the EFO server."""

from __future__ import annotations

from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition

from .client import EfoClient
from .constants import DEFAULT_RESULTS, MAX_RELATIONS, MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import EfoError
from .records import efo_term_record
from .utils import (
    max_results,
    optional_bool,
    optional_int,
    require_query,
    require_term,
    source_info,
    term_endpoint,
)


def efo_status(args: JsonObject, client: EfoClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "efo",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "website_base_url": client.config.website_base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "tool_groups": {
            "ontology": ["efo_term_lookup", "efo_term_search", "efo_term_children", "efo_term_descendants"],
            "status": ["efo_status"],
        },
        "frontend_components": ["ontology_term"],
        "preview_kinds": ["table", "network", "xref_groups", "text"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        endpoint, _iri = term_endpoint("EFO:0000270")
        payload, headers = client.request_json_with_headers(endpoint, {})
        status["network_check"] = {
            "ok": True,
            "example_id": payload.get("obo_id") if isinstance(payload, dict) else None,
            "example_label": payload.get("label") if isinstance(payload, dict) else None,
            "content_type": headers.get("content-type"),
        }
    return status


def efo_term_lookup(args: JsonObject, client: EfoClient) -> JsonObject:
    term_id = require_term(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint, iri = term_endpoint(term_id)
    payload, headers = client.request_json_with_headers(endpoint, {})
    if not isinstance(payload, dict) or not payload.get("iri"):
        raise EfoError(f"No EFO term found for {term_id}")
    record = efo_term_record(payload, website_base_url=client.config.website_base_url, api_base_url=client.config.base_url)
    response = term_response(query=term_id, records=[record], endpoint=endpoint, params={}, headers=headers)
    response["iri"] = iri
    if include_raw:
        response["raw"] = payload
    return response


def efo_term_search(args: JsonObject, client: EfoClient) -> JsonObject:
    query = require_query(args)
    limit = max_results(args)
    include_obsolete = optional_bool(args, "include_obsolete", default=False)
    exact = optional_bool(args, "exact", default=False)
    include_raw = optional_bool(args, "include_raw", default=False)
    params: JsonObject = {"q": query, "ontology": "efo", "rows": limit}
    if exact:
        params["exact"] = "true"
    if not include_obsolete:
        params["is_obsolete"] = "false"
    payload, headers = client.request_json_with_headers("search", params)
    rows = search_docs(payload)[:limit]
    records = [efo_term_record(row, website_base_url=client.config.website_base_url, api_base_url=client.config.base_url) for row in rows]
    response = term_response(query=query, records=records, endpoint="search", params=params, headers=headers)
    response["total"] = search_total(payload)
    if include_raw:
        response["raw"] = payload
    return response


def efo_term_children(args: JsonObject, client: EfoClient) -> JsonObject:
    return relation_terms(args, client, relation_name="children")


def efo_term_descendants(args: JsonObject, client: EfoClient) -> JsonObject:
    return relation_terms(args, client, relation_name="descendants")


def relation_terms(args: JsonObject, client: EfoClient, *, relation_name: str) -> JsonObject:
    term_id = require_term(args)
    limit = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RELATIONS)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint, iri = term_endpoint(term_id)
    relation_endpoint = f"{endpoint}/{relation_name}"
    params: JsonObject = {"size": limit}
    payload, headers = client.request_json_with_headers(relation_endpoint, params)
    rows = embedded_terms(payload)[:limit]
    records = [
        efo_term_record(
            row,
            relation=relation_name[:-1] if relation_name.endswith("s") else relation_name,
            parent_id=term_id,
            website_base_url=client.config.website_base_url,
            api_base_url=client.config.base_url,
        )
        for row in rows
    ]
    response = term_response(query=term_id, records=records, endpoint=relation_endpoint, params=params, headers=headers)
    response["iri"] = iri
    response["total"] = relation_total(payload, records)
    if include_raw:
        response["raw"] = payload
    return response


def search_docs(payload: object) -> list[JsonObject]:
    if not isinstance(payload, dict):
        return []
    response = payload.get("response")
    if not isinstance(response, dict):
        return []
    docs = response.get("docs")
    if not isinstance(docs, list):
        return []
    return [row for row in docs if isinstance(row, dict)]


def search_total(payload: object) -> int:
    if isinstance(payload, dict) and isinstance(payload.get("response"), dict):
        value = payload["response"].get("numFound")
        try:
            return int(value)
        except (TypeError, ValueError):
            pass
    return len(search_docs(payload))


def embedded_terms(payload: object) -> list[JsonObject]:
    if not isinstance(payload, dict):
        return []
    embedded = payload.get("_embedded")
    if not isinstance(embedded, dict):
        return []
    terms = embedded.get("terms")
    if not isinstance(terms, list):
        return []
    return [row for row in terms if isinstance(row, dict)]


def relation_total(payload: object, records: list[JsonObject]) -> int:
    if isinstance(payload, dict) and isinstance(payload.get("page"), dict):
        value = payload["page"].get("totalElements")
        try:
            return int(value)
        except (TypeError, ValueError):
            pass
    return len(records)


def term_response(*, query: str, records: list[JsonObject], endpoint: str, params: JsonObject, headers: dict[str, str]) -> JsonObject:
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "efo",
        "query": query,
        "returned": len(records),
        "terms": [term_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    return response


def term_summary(record: JsonObject) -> JsonObject:
    data = record["data"]
    return {
        "id": data["id"],
        "label": data["label"],
        "iri": data["iri"],
        "obsolete": data["is_obsolete"],
        "url": record["url"],
    }


def source_with_headers(endpoint: str, params: JsonObject, headers: dict[str, str]) -> JsonObject:
    source = source_info(endpoint, params)
    if headers.get("content-type"):
        source["content_type"] = headers["content-type"]
    return source


def tool_definitions() -> list[JsonObject]:
    return [
        parameter_domains_tool_definition("efo_parameter_domains"),
        {
            "name": "efo_term_lookup",
            "title": "Look up an EFO ontology term",
            "description": "Fetch one EFO/OLS4 term by CURIE, underscore ID, or full IRI and return an ontology-term record with definition, synonyms, xrefs, replacement links, and browser/API URLs.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "term_id": {"type": "string", "description": "EFO:0000270, EFO_0000270, MONDO:0004979, or a full term IRI."},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["term_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "efo_term_search",
            "title": "Search EFO ontology terms",
            "description": "Search EFO through EBI OLS4 and return bounded front-end-compatible ontology-term records.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search text, for example asthma or liver carcinoma."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "exact": {"type": "boolean", "default": False},
                    "include_obsolete": {"type": "boolean", "default": False},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "efo_term_children",
            "title": "List child EFO terms",
            "description": "Fetch bounded child terms for one EFO/OLS4 term.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "term_id": {"type": "string", "description": "Parent term CURIE, underscore ID, or full IRI."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RELATIONS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["term_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "efo_term_descendants",
            "title": "List descendant EFO terms",
            "description": "Fetch bounded descendant terms for one EFO/OLS4 term.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "term_id": {"type": "string", "description": "Ancestor term CURIE, underscore ID, or full IRI."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RELATIONS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["term_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "efo_status",
            "title": "Inspect EFO MCP status",
            "description": "Return configured EFO MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
    ]


TOOL_HANDLERS = {
    "efo_parameter_domains": make_parameter_domains_handler("efo", "efo_parameter_domains", tool_definitions),
    "efo_term_lookup": efo_term_lookup,
    "efo_term_search": efo_term_search,
    "efo_term_children": efo_term_children,
    "efo_term_descendants": efo_term_descendants,
    "efo_status": efo_status,
}

