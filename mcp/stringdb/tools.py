"""MCP tool registry for the STRING server."""

from __future__ import annotations

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
from .utils import optional_bool, optional_int, require_identifiers, source_info


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


def tool_definitions() -> list[JsonObject]:
    read_only_annotations = {
        "readOnlyHint": True,
        "openWorldHint": True,
    }
    return [
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
    "string_map": string_map,
    "string_interactions": string_interactions,
    "string_status": string_status,
}

