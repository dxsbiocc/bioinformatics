"""MCP tool registry for the ChEBI server."""

from __future__ import annotations

from mcp.dynamic_context import build_dynamic_context_response
from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition
from .client import ChebiClient
from .constants import DEFAULT_RESULTS, MAX_RELATIONS, MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import ChebiError, McpError
from .records import chebi_compound_record, chebi_relation_record
from .utils import max_results, normalize_chebi_id, normalize_space, optional_bool, optional_int, require_chebi_id, require_query, safe_dict, safe_list, source_info


SEARCH_ENDPOINT = "chebi/backend/api/public/es_search/"
COMPOUND_ENDPOINT_PREFIX = "chebi/backend/api/public/compound"
CHILDREN_ENDPOINT_PREFIX = "chebi/backend/api/public/ontology/children"
PARENTS_ENDPOINT_PREFIX = "chebi/backend/api/public/ontology/parents"
CHEBI_CONTEXT_TYPES = ["all", "compounds", "ontology", "identifiers"]
CHEBI_CONTEXT_SCHEMA_VERSION = "bioinformatics.dynamic_context.v1"


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
            "context": ["chebi_parameter_domains", "chebi_resolve_context"],
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


def chebi_resolve_context(args: JsonObject, client: ChebiClient) -> JsonObject:
    context_type = optional_context_type(args, "context_type", allowed=CHEBI_CONTEXT_TYPES, default="all")
    query = optional_text(args, "query")
    chebi_id = optional_text(args, "chebi_id")
    include_relations = optional_bool(args, "include_relations", default=False)
    limit = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    contexts = static_chebi_contexts()
    recommended_calls: list[JsonObject] = []
    sources: list[JsonObject] = []
    raw: JsonObject = {}

    if query:
        result = chebi_compound_search({"query": query, "max_results": limit, "include_raw": include_raw}, client)
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(chebi_record_context(record) for record in records)
        for record in records[:3]:
            recommended_calls.extend(chebi_recommended_calls(record))
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["search"] = result["raw"]

    if chebi_id:
        normalized_id = normalize_chebi_id(chebi_id)
        result = chebi_compound_lookup({"chebi_id": normalized_id, "include_raw": include_raw}, client)
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(chebi_record_context(record) for record in records)
        for record in records:
            recommended_calls.extend(chebi_recommended_calls(record))
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["lookup"] = result["raw"]
        if include_relations:
            for tool, key in [(chebi_ontology_children, "children"), (chebi_ontology_parents, "parents")]:
                relation_result = tool({"chebi_id": normalized_id, "max_results": min(limit, MAX_RELATIONS), "include_raw": include_raw}, client)
                relation_records = [record for record in relation_result.get("records", []) if isinstance(record, dict)]
                contexts.extend(chebi_record_context(record, group="ontology") for record in relation_records)
                relation_source = relation_result.get("source")
                if isinstance(relation_source, dict):
                    sources.append(relation_source)
                if include_raw and "raw" in relation_result:
                    raw[key] = relation_result["raw"]

    query_text = query or chebi_id
    filtered_contexts = [
        context
        for context in contexts
        if chebi_context_matches(context, context_type=context_type, query=query_text)
    ]
    return build_dynamic_context_response(
        schema_version=RESULT_SCHEMA_VERSION,
        context_schema_version=CHEBI_CONTEXT_SCHEMA_VERSION,
        database="chebi",
        query={"context_type": context_type, "query": query, "chebi_id": chebi_id, "include_relations": include_relations},
        contexts=filtered_contexts,
        recommended_calls=recommended_calls,
        max_results=limit,
        fallback_source=source_info("resolve_context", {"context_type": context_type, "query": query, "chebi_id": chebi_id}),
        sources=sources,
        entity_groups={"compounds", "ontology"},
        raw=raw,
        include_raw=include_raw,
        prioritize_entities=True,
        prioritize_same_server_calls=True,
    )


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


def optional_text(args: JsonObject, name: str) -> str:
    value = args.get(name)
    if value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    if not isinstance(value, str):
        raise McpError(-32602, f"{name} must be a string")
    return value.strip()


def optional_context_type(args: JsonObject, name: str, *, allowed: list[str], default: str) -> str:
    value = optional_text(args, name) or default
    if value not in allowed:
        raise McpError(-32602, f"{name} must be one of: {', '.join(allowed)}")
    return value


def static_chebi_contexts() -> list[JsonObject]:
    contexts: list[JsonObject] = [
        chebi_parameter_context(
            "context_type",
            value,
            label=value,
            description="Dynamic ChEBI context family to resolve before compound lookup, search, or ontology traversal.",
            kind="enum",
            group="context_types",
            url="",
            metadata={"context_type": value},
        )
        for value in CHEBI_CONTEXT_TYPES
    ]
    contexts.extend(
        [
            chebi_parameter_context(
                "chebi_id",
                "CHEBI:27732",
                label="CHEBI:27732",
                description="Canonical ChEBI identifier format accepted by lookup and ontology tools.",
                kind="identifier_format",
                group="identifiers",
                url="https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:27732",
                metadata={"example": "CHEBI:27732"},
            ),
            chebi_parameter_context(
                "include_relations",
                True,
                label="Include ontology relations",
                description="Fetch ChEBI parent and child relation contexts when chebi_id is provided.",
                kind="boolean_filter",
                group="ontology",
                url="",
                metadata={"tool_hint": "chebi_resolve_context"},
            ),
        ]
    )
    return contexts


def chebi_record_context(record: JsonObject, *, group: str = "") -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    value = normalize_space(data.get("id") or record.get("id"))
    if not group:
        group = "ontology" if normalize_space(record.get("record_type")) == "chebi_relation" else "compounds"
    return chebi_parameter_context(
        "chebi_id",
        value,
        label=normalize_space(record.get("title") or record.get("label") or data.get("name") or value),
        description=normalize_space(record.get("description") or data.get("definition") or f"ChEBI {group.rstrip('s')} context."),
        kind=normalize_space(record.get("record_type")) or group.rstrip("s"),
        group=group,
        url=normalize_space(record.get("url") or data.get("url")),
        metadata={
            "id": value,
            "name": data.get("name", ""),
            "formula": data.get("formula", ""),
            "mass": data.get("mass", ""),
            "inchikey": data.get("inchikey", ""),
            "smiles": data.get("smiles", ""),
            "relation": data.get("relation", ""),
        },
    )


def chebi_parameter_context(
    parameter_name: str,
    value: object,
    *,
    label: str,
    description: str,
    kind: str,
    group: str,
    url: str,
    metadata: JsonObject,
) -> JsonObject:
    display_fields = [{"label": key.replace("_", " ").title(), "value": item} for key, item in metadata.items() if item not in ("", None, [], {})]
    if url:
        display_fields.append({"label": "URL", "value": url})
    component = "ontology_term" if group == "ontology" else "compound"
    return {
        "kind": kind,
        "group": group,
        "parameter_name": parameter_name,
        "value": value,
        "label": label,
        "title": label,
        "description": description,
        "url": url,
        "metadata": metadata,
        "display": {
            "component": component,
            "chip_label": parameter_name,
            "icon": "chebi",
            "title": label,
            "subtitle": f"{parameter_name}: {value}",
            "description": description,
            "metadata": display_fields,
            "badges": [{"label": "ChEBI", "kind": "source"}, {"label": parameter_name, "kind": "parameter"}],
            "actions": [{"label": "Open source", "url": url, "kind": "external", "primary": True}] if url else [],
            "hover": {"title": label, "subtitle": f"{parameter_name}: {value}", "icon": "chebi", "fields": display_fields},
            "primary_url": url,
        },
    }


def chebi_recommended_calls(record: JsonObject) -> list[JsonObject]:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    chebi_id = normalize_space(data.get("id") or record.get("id"))
    calls: list[JsonObject] = [
        {"tool_name": "chebi_compound_lookup", "arguments": {"chebi_id": chebi_id}, "reason": "Fetch ChEBI compound metadata, synonyms, structures, xrefs, and citations."},
        {"tool_name": "chebi_ontology_children", "arguments": {"chebi_id": chebi_id}, "reason": "Fetch child/descendant relation context for this ChEBI term."},
        {"tool_name": "chebi_ontology_parents", "arguments": {"chebi_id": chebi_id}, "reason": "Fetch parent/role relation context for this ChEBI term."},
    ]
    if data.get("inchikey"):
        calls.append({"server": "pubchem", "tool_name": "pubchem_compound_search", "arguments": {"query": data["inchikey"]}, "reason": "Search PubChem for the same InChIKey or related compound context."})
    return calls


def chebi_context_matches(context: JsonObject, *, context_type: str, query: str) -> bool:
    if context_type != "all" and context.get("group") != context_type:
        return False
    if not query:
        return True
    metadata = context.get("metadata")
    haystack_values = [context.get("parameter_name"), context.get("value"), context.get("label"), context.get("description"), context.get("kind")]
    if isinstance(metadata, dict):
        haystack_values.extend(metadata.values())
    haystack = " ".join(str(item).lower() for item in haystack_values if item not in ("", None))
    return query.lower() in haystack or context.get("group") in {"compounds", "ontology"}


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
        parameter_domains_tool_definition("chebi_parameter_domains"),
        {
            "name": "chebi_resolve_context",
            "title": "Resolve ChEBI dynamic parameter context",
            "description": (
                "Resolve ChEBI search terms, CHEBI IDs, and optional ontology relation context before lookup or traversal. "
                "Returns front-end-friendly context rows, ChEBI URLs, and recommended follow-up calls."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "context_type": {"type": "string", "enum": CHEBI_CONTEXT_TYPES, "default": "all"},
                    "query": {"type": "string", "description": "Optional ChEBI text query such as caffeine."},
                    "chebi_id": {"type": "string", "description": "Optional ChEBI identifier such as CHEBI:27732."},
                    "include_relations": {"type": "boolean", "default": False},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
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
    "chebi_parameter_domains": make_parameter_domains_handler("chebi", "chebi_parameter_domains", tool_definitions),
    "chebi_resolve_context": chebi_resolve_context,
    "chebi_compound_search": chebi_compound_search,
    "chebi_compound_lookup": chebi_compound_lookup,
    "chebi_ontology_children": chebi_ontology_children,
    "chebi_ontology_parents": chebi_ontology_parents,
    "chebi_status": chebi_status,
}
