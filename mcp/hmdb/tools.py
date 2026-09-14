"""MCP tool registry for the HMDB server."""

from __future__ import annotations

from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition

from .client import HmdbClient
from .constants import DEFAULT_RESULTS, HMDB_CATEGORIES, MAX_RESULTS, RESULT_SCHEMA_VERSION, SEARCH_PATH, JsonObject
from .records import hmdb_record
from .utils import max_results, optional_bool, require_category, require_query, source_info


def hmdb_status(args: JsonObject, client: HmdbClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "hmdb",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["hmdb_metabolites", "hmdb_proteins", "hmdb_diseases", "hmdb_pathways"],
        "tool_groups": {
            "search": ["hmdb_search", "hmdb_metabolite_search", "hmdb_protein_search", "hmdb_disease_search", "hmdb_pathway_search"],
            "status": ["hmdb_status"],
        },
        "frontend_components": ["compound", "protein", "dataset", "pathway"],
        "preview_kinds": ["table", "text", "chemical_structure", "sequence", "xref_groups"],
        "record_schema_version": "bioinformatics.record.v1",
        "known_runtime_constraint": "HMDB may return a Cloudflare browser challenge for non-browser runtimes; errors expose that condition explicitly.",
    }
    if check_network:
        payload, headers, url = client.search_json_with_headers("serotonin", "metabolites", 1)
        rows = search_rows(payload, "metabolites")
        status["network_check"] = {
            "ok": True,
            "returned": len(rows),
            "example_id": rows[0].get("hmdb_id") or rows[0].get("accession") if rows else None,
            "content_type": headers.get("content-type"),
            "url": url,
        }
    return status


def hmdb_search(args: JsonObject, client: HmdbClient) -> JsonObject:
    query = require_query(args)
    category = require_category(args)
    return search_category(args, client, query=query, category=category)


def hmdb_metabolite_search(args: JsonObject, client: HmdbClient) -> JsonObject:
    return search_category(args, client, query=require_query(args), category="metabolites")


def hmdb_protein_search(args: JsonObject, client: HmdbClient) -> JsonObject:
    return search_category(args, client, query=require_query(args), category="proteins")


def hmdb_disease_search(args: JsonObject, client: HmdbClient) -> JsonObject:
    return search_category(args, client, query=require_query(args), category="diseases")


def hmdb_pathway_search(args: JsonObject, client: HmdbClient) -> JsonObject:
    return search_category(args, client, query=require_query(args), category="pathways")


def search_category(args: JsonObject, client: HmdbClient, *, query: str, category: str) -> JsonObject:
    limit = max_results(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    payload, headers, url = client.search_json_with_headers(query, category, limit)
    rows = search_rows(payload, category)[:limit]
    records = [hmdb_record(row, category=category, query=query, base_url=client.config.base_url) for row in rows]
    params: JsonObject = {"query": query, "category": category, "format": "json", "per_page": limit}
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "hmdb",
        "query": query,
        "category": category,
        "returned": len(records),
        "total": total_count(payload, rows, category),
        "records": records,
        "items": [record_summary(record) for record in records],
        "source": source_with_headers(SEARCH_PATH, params, headers, url),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def search_rows(payload: object, category: str) -> list[JsonObject]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    for key in [category, "results", "records", "items"]:
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    data = payload.get("data")
    if isinstance(data, dict):
        value = data.get(category) or data.get("results")
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    return []


def total_count(payload: object, rows: list[JsonObject], category: str) -> int:
    if isinstance(payload, dict):
        for key in ["total", "total_count", "count"]:
            try:
                return int(payload[key])
            except (KeyError, TypeError, ValueError):
                pass
        meta = payload.get("meta")
        if isinstance(meta, dict):
            for key in ["total", "total_count", "count"]:
                try:
                    return int(meta[key])
                except (KeyError, TypeError, ValueError):
                    pass
    return len(rows)


def record_summary(record: JsonObject) -> JsonObject:
    return {
        "id": record["id"],
        "title": record["title"],
        "category": record["data"]["category"],
        "url": record["url"],
    }


def source_with_headers(endpoint: str, params: JsonObject, headers: dict[str, str], url: str) -> JsonObject:
    source = source_info(endpoint, params, url=url)
    if headers.get("content-type"):
        source["content_type"] = headers["content-type"]
    return source


def tool_definitions() -> list[JsonObject]:
    category_schema = {"type": "string", "enum": sorted(HMDB_CATEGORIES), "default": "metabolites"}
    common_properties = {
        "query": {"type": "string", "description": "Search text, for example serotonin, albumin, diabetes, or glycolysis."},
        "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
        "include_raw": {"type": "boolean", "default": False},
    }
    return [
        parameter_domains_tool_definition("hmdb_parameter_domains"),
        {
            "name": "hmdb_search",
            "title": "Search HMDB by category",
            "description": "Search HMDB unearth/q for metabolites, proteins, diseases, or pathways and return app-renderable records with HMDB links.",
            "inputSchema": {
                "type": "object",
                "properties": {**common_properties, "category": category_schema},
                "required": ["query", "category"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "hmdb_metabolite_search",
            "title": "Search HMDB metabolites",
            "description": "Search HMDB metabolites and return compound records with formula, identifiers, chemical previews, and HMDB links when present.",
            "inputSchema": {"type": "object", "properties": common_properties, "required": ["query"], "additionalProperties": False},
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "hmdb_protein_search",
            "title": "Search HMDB proteins",
            "description": "Search HMDB proteins and return protein records with gene, UniProt, sequence, xref, and HMDB links when present.",
            "inputSchema": {"type": "object", "properties": common_properties, "required": ["query"], "additionalProperties": False},
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "hmdb_disease_search",
            "title": "Search HMDB diseases",
            "description": "Search HMDB diseases and return dataset records with descriptions, xrefs, and HMDB links.",
            "inputSchema": {"type": "object", "properties": common_properties, "required": ["query"], "additionalProperties": False},
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "hmdb_pathway_search",
            "title": "Search HMDB pathways",
            "description": "Search HMDB pathways and return pathway records with descriptions, xrefs, and HMDB links.",
            "inputSchema": {"type": "object", "properties": common_properties, "required": ["query"], "additionalProperties": False},
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "hmdb_status",
            "title": "Inspect HMDB MCP status",
            "description": "Return configured HMDB MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
    ]


TOOL_HANDLERS = {
    "hmdb_parameter_domains": make_parameter_domains_handler("hmdb", "hmdb_parameter_domains", tool_definitions),
    "hmdb_search": hmdb_search,
    "hmdb_metabolite_search": hmdb_metabolite_search,
    "hmdb_protein_search": hmdb_protein_search,
    "hmdb_disease_search": hmdb_disease_search,
    "hmdb_pathway_search": hmdb_pathway_search,
    "hmdb_status": hmdb_status,
}

