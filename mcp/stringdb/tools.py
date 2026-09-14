"""MCP tool registry for the STRING server."""

from __future__ import annotations

from mcp.dynamic_context import build_dynamic_context_response
from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition
from typing import Callable

from .client import StringDbClient
from .constants import (
    MAX_INTERACTIONS,
    RESULT_SCHEMA_VERSION,
    STRING_WEBSITE_BASE_URL,
    JsonObject,
)
from .records import (
    build_network_nodes,
    normalize_interaction,
    normalize_mapping,
    string_mapping_record,
    string_network_record,
)
from .errors import McpError
from .utils import normalize_space, optional_bool, optional_int, require_identifiers, source_info


STRING_CONTEXT_TYPES = ["all", "identifiers", "species", "network", "scores"]
STRING_CONTEXT_SCHEMA_VERSION = "bioinformatics.dynamic_context.v1"
STRING_SCORE_HINTS = ["score", "nscore", "fscore", "pscore", "ascore", "escore", "dscore", "tscore"]


def string_status(args: JsonObject, client: StringDbClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "string",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "website_url": STRING_WEBSITE_BASE_URL,
        "tool": client.config.tool,
        "caller_identity": client.config.caller_identity,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["string"],
        "tool_groups": {
            "context": ["string_parameter_domains", "string_resolve_context"],
            "protein_network": [
                "string_map",
                "string_interactions",
            ],
            "status": ["string_status"],
        },
        "frontend_components": ["identifier_conversion", "protein_network"],
        "preview_kinds": ["network", "table", "xref_groups"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        mappings, _headers = client.request_json_array_with_headers(
            "json/get_string_ids",
            {
                "identifiers": "TP53",
                "species": 9606,
                "limit": 1,
                "echo_query": 1,
            },
        )
        status["network_check"] = {
            "ok": True,
            "returned": len(mappings),
        }
    return status


def string_resolve_context(args: JsonObject, client: StringDbClient) -> JsonObject:
    context_type = optional_context_type(args, "context_type", allowed=STRING_CONTEXT_TYPES, default="all")
    identifiers = optional_identifiers(args)
    species = optional_int(args, "species", default=9606, minimum=1, maximum=999999999)
    limit = optional_int(args, "limit", default=1, minimum=1, maximum=20)
    include_raw = optional_bool(args, "include_raw", default=False)
    contexts = static_string_contexts()
    recommended_calls: list[JsonObject] = []
    sources: list[JsonObject] = []
    raw: JsonObject = {}

    if identifiers:
        endpoint = "json/get_string_ids"
        params: JsonObject = {
            "identifiers": "\r".join(identifiers),
            "species": species,
            "limit": limit,
            "echo_query": 1,
        }
        raw_mappings, headers = client.request_json_array_with_headers(endpoint, params)
        mappings = [normalize_mapping(mapping) for mapping in raw_mappings]
        raw["mappings"] = raw_mappings
        sources.append(source_with_headers(endpoint, params, headers))
        contexts.extend(string_mapping_context(mapping) for mapping in mappings)
        recommended_calls.extend(
            [
                {"tool_name": "string_map", "arguments": {"identifiers": identifiers, "species": species, "limit": limit}, "reason": "Resolve identifiers to STRING IDs."},
                {"tool_name": "string_interactions", "arguments": {"identifiers": identifiers, "species": species}, "reason": "Fetch interaction partners after identifier resolution."},
            ]
        )

    query_text = " ".join(identifiers)
    filtered_contexts = [context for context in contexts if string_context_matches(context, context_type=context_type, query=query_text)]
    return build_dynamic_context_response(
        schema_version=RESULT_SCHEMA_VERSION,
        context_schema_version=STRING_CONTEXT_SCHEMA_VERSION,
        database="string",
        query={
            "context_type": context_type,
            "identifiers": identifiers,
            "species": species,
            "limit": limit,
        },
        contexts=filtered_contexts,
        recommended_calls=recommended_calls,
        max_results=max(limit, 10),
        fallback_source=source_info("resolve_context", {"context_type": context_type, "species": species}),
        sources=sources,
        entity_groups={"identifiers"},
        raw=raw,
        summary_fields={"mappings": lambda context: context.get("parameter_name") == "identifiers"},
        include_raw=include_raw,
        dedupe_calls=False,
    )


def string_map(args: JsonObject, client: StringDbClient) -> JsonObject:
    identifiers = require_identifiers(args)
    species = optional_int(args, "species", default=9606, minimum=1, maximum=999999999)
    limit = optional_int(args, "limit", default=1, minimum=1, maximum=20)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = "json/get_string_ids"
    params: JsonObject = {
        "identifiers": "\r".join(identifiers),
        "species": species,
        "limit": limit,
        "echo_query": 1,
    }
    raw_mappings, headers = client.request_json_array_with_headers(endpoint, params)
    mappings = [normalize_mapping(mapping) for mapping in raw_mappings]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "string",
        "query": ", ".join(identifiers),
        "identifiers": identifiers,
        "species": species,
        "returned": len(mappings),
        "mappings": mappings,
        "records": [string_mapping_record(mapping) for mapping in raw_mappings],
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = raw_mappings
    return response


def string_interactions(args: JsonObject, client: StringDbClient) -> JsonObject:
    identifiers = require_identifiers(args)
    species = optional_int(args, "species", default=9606, minimum=1, maximum=999999999)
    limit = optional_int(
        args,
        "limit",
        default=10,
        minimum=1,
        maximum=MAX_INTERACTIONS,
    )
    include_raw = optional_bool(args, "include_raw", default=False)
    mapping_endpoint = "json/get_string_ids"
    mapping_params: JsonObject = {
        "identifiers": "\r".join(identifiers),
        "species": species,
        "limit": 1,
        "echo_query": 1,
    }
    raw_mappings, mapping_headers = client.request_json_array_with_headers(
        mapping_endpoint,
        mapping_params,
    )
    mappings = [normalize_mapping(mapping) for mapping in raw_mappings]
    interaction_endpoint = "json/interaction_partners"
    interaction_params: JsonObject = {
        "identifiers": "\r".join(identifiers),
        "species": species,
        "limit": limit,
    }
    raw_interactions, interaction_headers = client.request_json_array_with_headers(
        interaction_endpoint,
        interaction_params,
    )
    interactions = [normalize_interaction(item) for item in raw_interactions]
    nodes = build_network_nodes(mappings, interactions)
    records = [
        string_network_record(
            query=identifiers,
            mappings=mappings,
            interactions=interactions,
            nodes=nodes,
            edges=interactions,
            species=species,
            limit=limit,
        )
    ]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "string",
        "query": ", ".join(identifiers),
        "identifiers": identifiers,
        "species": species,
        "returned": len(interactions),
        "mapping_count": len(mappings),
        "node_count": len(nodes),
        "edge_count": len(interactions),
        "mappings": mappings,
        "nodes": nodes,
        "edges": interactions,
        "records": records,
        "source": {
            "database": "string",
            "retrieved_at": source_info(interaction_endpoint, interaction_params)["retrieved_at"],
            "requests": [
                source_with_headers(mapping_endpoint, mapping_params, mapping_headers),
                source_with_headers(
                    interaction_endpoint,
                    interaction_params,
                    interaction_headers,
                ),
            ],
        },
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = {
            "mappings": raw_mappings,
            "interactions": raw_interactions,
        }
    return response


def source_with_headers(
    endpoint: str,
    params: JsonObject,
    headers: dict[str, str],
) -> JsonObject:
    source = source_info(endpoint, params)
    content_type = headers.get("content-type")
    if content_type:
        source["content_type"] = content_type
    return source


def optional_context_type(args: JsonObject, name: str, *, allowed: list[str], default: str) -> str:
    value = normalize_space(args.get(name)) or default
    if value not in allowed:
        raise McpError(-32602, f"{name} must be one of: {', '.join(allowed)}")
    return value


def optional_identifiers(args: JsonObject) -> list[str]:
    if args.get("identifiers") in (None, "", []):
        return []
    return require_identifiers(args)


def static_string_contexts() -> list[JsonObject]:
    contexts = [
        string_parameter_context(
            "species",
            9606,
            label="Homo sapiens",
            description="Default human NCBI TaxID used by STRING mapping and interaction calls.",
            kind="species",
            group="species",
            url="https://string-db.org/cgi/network?species=9606",
            metadata={"taxon_id": 9606, "scientific_name": "Homo sapiens"},
        ),
        string_parameter_context(
            "species",
            10090,
            label="Mus musculus",
            description="Mouse NCBI TaxID accepted by STRING mapping and interaction calls.",
            kind="species",
            group="species",
            url="https://string-db.org/cgi/network?species=10090",
            metadata={"taxon_id": 10090, "scientific_name": "Mus musculus"},
        ),
        string_parameter_context(
            "limit",
            10,
            label="Default interaction partner limit",
            description="Bound returned interaction partners for front-end network rendering.",
            kind="integer_hint",
            group="network",
            url="",
            metadata={"minimum": 1, "maximum": MAX_INTERACTIONS, "tool_hint": "string_interactions"},
        ),
    ]
    contexts.extend(
        string_parameter_context(
            "score_field",
            score,
            label=score,
            description="STRING evidence or combined score field returned in interaction edges.",
            kind="score_field",
            group="scores",
            url="https://string-db.org/help/faq/#what-do-the-scores-mean",
            metadata={"tool_hint": "string_interactions"},
        )
        for score in STRING_SCORE_HINTS
    )
    return contexts


def string_mapping_context(mapping: JsonObject) -> JsonObject:
    string_id = str(mapping.get("string_id") or "")
    preferred_name = str(mapping.get("preferred_name") or string_id)
    taxon_id = mapping.get("taxid") or ""
    url = f"{STRING_WEBSITE_BASE_URL.rstrip('/')}/network/{string_id}" if string_id else STRING_WEBSITE_BASE_URL
    return string_parameter_context(
        "identifiers",
        string_id or preferred_name,
        label=preferred_name,
        description=str(mapping.get("annotation") or "STRING identifier mapping candidate."),
        kind="string_identifier",
        group="identifiers",
        url=url,
        metadata={
            "string_id": string_id,
            "preferred_name": preferred_name,
            "query": mapping.get("query_item") or "",
            "taxon_id": taxon_id,
            "tool_hint": "string_interactions",
        },
    )


def string_parameter_context(
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
            "component": "protein_network" if group in {"network", "scores", "identifiers"} else "dataset",
            "chip_label": parameter_name,
            "icon": "string",
            "title": label,
            "subtitle": f"{parameter_name}: {value}",
            "description": description,
            "metadata": display_fields,
            "badges": [
                {"label": "STRING", "kind": "source"},
                {"label": parameter_name, "kind": "parameter"},
            ],
            "actions": [{"label": "Open source", "url": url, "kind": "external", "primary": True}] if url else [],
            "hover": {"title": label, "subtitle": f"{parameter_name}: {value}", "icon": "string", "fields": display_fields},
            "primary_url": url,
        },
    }


def string_context_matches(context: JsonObject, *, context_type: str, query: str) -> bool:
    if context_type != "all" and context.get("group") != context_type:
        return False
    if not query:
        return True
    metadata = context.get("metadata")
    fields = [context.get("parameter_name"), context.get("value"), context.get("label"), context.get("description"), context.get("kind")]
    if isinstance(metadata, dict):
        fields.extend(metadata.values())
    haystack = " ".join(str(field).lower() for field in fields if field not in ("", None))
    return any(part.lower() in haystack for part in query.split()) or context.get("group") == "identifiers"


def tool_definitions() -> list[JsonObject]:
    read_only_annotations = {
        "readOnlyHint": True,
        "openWorldHint": True,
    }
    return [
        parameter_domains_tool_definition("string_parameter_domains"),
        {
            "name": "string_resolve_context",
            "title": "Resolve STRING dynamic parameter context",
            "description": (
                "Resolve STRING identifier/species/network context before mapping or interaction calls. "
                "Returns front-end-friendly mapping candidates, score-field hints, STRING URLs, and recommended calls."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "context_type": {"type": "string", "enum": STRING_CONTEXT_TYPES, "default": "all"},
                    "identifiers": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}},
                        ],
                        "description": "Optional identifiers to map, for example TP53 or P04637.",
                    },
                    "species": {"type": "integer", "default": 9606, "description": "NCBI TaxID for mapping and interactions."},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 1},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "string_map",
            "title": "Map protein identifiers to STRING IDs",
            "description": (
                "Resolve gene symbols, UniProt accessions, or other protein identifiers "
                "to STRING identifiers and return front-end-compatible mapping records."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "identifiers": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        ],
                        "description": "One or more identifiers, for example TP53 or P04637.",
                    },
                    "species": {
                        "type": "integer",
                        "default": 9606,
                        "description": "NCBI TaxID for identifier resolution. Default is human 9606.",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 1,
                        "description": "Maximum STRING matches per input identifier.",
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["identifiers"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "string_interactions",
            "title": "Fetch STRING protein interaction partners",
            "description": (
                "Resolve seed identifiers and fetch STRING interaction partners, returning "
                "a protein_network record with app-renderable nodes, edges, scores, and URLs."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "identifiers": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        ],
                        "description": "One or more protein identifiers, for example TP53, MDM2, or P04637.",
                    },
                    "species": {
                        "type": "integer",
                        "default": 9606,
                        "description": "NCBI TaxID for interaction lookup. Default is human 9606.",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_INTERACTIONS,
                        "default": 10,
                        "description": "Maximum interaction partners returned by STRING.",
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["identifiers"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "string_status",
            "title": "Inspect STRING MCP status",
            "description": "Return configured STRING MCP capabilities and optional network health.",
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


TOOL_HANDLERS: dict[str, Callable[[JsonObject, StringDbClient], JsonObject]] = {
    "string_parameter_domains": make_parameter_domains_handler("string", "string_parameter_domains", tool_definitions),
    "string_resolve_context": string_resolve_context,
    "string_map": string_map,
    "string_interactions": string_interactions,
    "string_status": string_status,
}
