"""MCP tool registry for the Reactome server."""

from __future__ import annotations

from typing import Callable

from .client import ReactomeClient
from .constants import (
    MAX_PARTICIPANTS,
    MAX_REFERENCES,
    MAX_SEARCH_RESULTS,
    REACTOME_CONTENT_API_BASE_URL,
    REACTOME_WEBSITE_BASE_URL,
    RESULT_SCHEMA_VERSION,
    JsonObject,
)
from .errors import ReactomeError
from .records import reactome_pathway_record
from .utils import (
    clean_html,
    normalize_space,
    optional_bool,
    optional_int,
    optional_string,
    require_non_empty_string,
    require_stable_id,
    source_info,
)


def reactome_status(args: JsonObject, client: ReactomeClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "reactome",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "website_url": client.config.website_base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["reactome"],
        "tool_groups": {
            "pathway": [
                "reactome_lookup",
                "reactome_search",
                "reactome_pathways_for_identifier",
            ],
            "status": ["reactome_status"],
        },
        "frontend_components": ["pathway"],
        "preview_kinds": ["network", "table", "citation_list", "xref_groups"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        event, _headers = client.request_json_with_headers("data/query/R-HSA-5633007", {})
        if not isinstance(event, dict):
            raise ReactomeError("Reactome network check returned non-object JSON")
        status["network_check"] = {
            "ok": True,
            "stable_id": event.get("stId"),
            "display_name": clean_html(event.get("displayName")),
        }
    return status


def reactome_lookup(args: JsonObject, client: ReactomeClient) -> JsonObject:
    stable_id = require_stable_id(args)
    include_participants = optional_bool(args, "include_participants", default=True)
    include_raw = optional_bool(args, "include_raw", default=False)
    max_participants = optional_int(
        args,
        "max_participants",
        default=MAX_PARTICIPANTS,
        minimum=0,
        maximum=MAX_PARTICIPANTS,
    )
    endpoint = f"data/query/{stable_id}"
    event, event_headers = client.request_json_with_headers(endpoint, {})
    if not isinstance(event, dict):
        raise ReactomeError(f"Reactome {endpoint} returned non-object JSON")
    participants: list[JsonObject] = []
    participant_warning = ""
    if include_participants and max_participants > 0:
        try:
            payload, _participant_headers = client.request_json_with_headers(
                f"data/participants/{stable_id}",
                {},
            )
            if isinstance(payload, list):
                participants = [item for item in payload[:max_participants] if isinstance(item, dict)]
            else:
                participant_warning = "Reactome participants endpoint returned non-list JSON"
        except ReactomeError as exc:
            participant_warning = str(exc)
    record = reactome_pathway_record(event, participants=participants)
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "reactome",
        "query": stable_id,
        "returned": 1,
        "event": pathway_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, {}, event_headers),
    }
    response["provenance"] = response["source"]
    if participant_warning:
        response["warnings"] = [participant_warning]
    if include_raw:
        response["raw"] = {
            "event": event,
            "participants": participants,
        }
    return response


def reactome_search(args: JsonObject, client: ReactomeClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    species = optional_string(args, "species", default="Homo sapiens")
    types = optional_string(args, "types", default="Pathway")
    max_results = optional_int(
        args,
        "max_results",
        default=10,
        minimum=1,
        maximum=MAX_SEARCH_RESULTS,
    )
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = "search/query"
    params: JsonObject = {
        "query": query,
        "species": species,
        "types": types,
    }
    payload, headers = client.request_json_with_headers(endpoint, params)
    if not isinstance(payload, dict):
        raise ReactomeError("Reactome search returned non-object JSON")
    entries = flatten_search_entries(payload, max_results=max_results)
    records = [
        reactome_pathway_record(entry, search_score=entry.get("score", ""))
        for entry in entries
    ]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "reactome",
        "query": query,
        "returned": len(records),
        "total": search_total(payload),
        "entries": [pathway_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def reactome_pathways_for_identifier(args: JsonObject, client: ReactomeClient) -> JsonObject:
    identifier = require_non_empty_string(args, "identifier")
    resource = optional_string(args, "resource", default="UniProt")
    species = optional_string(args, "species", default="9606")
    max_results = optional_int(
        args,
        "max_results",
        default=10,
        minimum=1,
        maximum=MAX_SEARCH_RESULTS,
    )
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"data/mapping/{resource}/{identifier}/pathways"
    params: JsonObject = {"species": species}
    payload, headers = client.request_json_with_headers(endpoint, params)
    if not isinstance(payload, list):
        raise ReactomeError(f"Reactome {endpoint} returned non-list JSON")
    pathways = [item for item in payload[:max_results] if isinstance(item, dict)]
    records = [
        reactome_pathway_record(
            pathway,
            mapping_resource=resource,
            query_identifier=identifier,
        )
        for pathway in pathways
    ]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "reactome",
        "query": identifier,
        "resource": resource,
        "species": species,
        "returned": len(records),
        "total": len(payload),
        "pathways": [pathway_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def flatten_search_entries(payload: JsonObject, *, max_results: int) -> list[JsonObject]:
    entries: list[JsonObject] = []
    groups = payload.get("results")
    if not isinstance(groups, list):
        return entries
    for group in groups:
        if not isinstance(group, dict):
            continue
        group_entries = group.get("entries")
        if not isinstance(group_entries, list):
            continue
        for entry in group_entries:
            if not isinstance(entry, dict):
                continue
            normalized = dict(entry)
            normalized["displayName"] = clean_html(entry.get("name") or entry.get("displayName"))
            normalized["schemaClass"] = clean_html(entry.get("exactType") or entry.get("type") or entry.get("schemaClass"))
            normalized["speciesName"] = species_text(entry.get("species"))
            normalized["summation"] = [{"text": clean_html(entry.get("summation"))}]
            entries.append(normalized)
            if len(entries) >= max_results:
                return entries
    return entries


def search_total(payload: JsonObject) -> int | str:
    total = payload.get("total")
    if isinstance(total, int):
        return total
    groups = payload.get("results")
    if not isinstance(groups, list):
        return ""
    count = 0
    for group in groups:
        if isinstance(group, dict) and isinstance(group.get("entries"), list):
            count += len(group["entries"])
    return count


def species_text(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(clean_html(item) for item in value if clean_html(item))
    return clean_html(value)


def pathway_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "stable_id": normalize_space(data.get("stable_id")),
        "db_id": data.get("db_id", ""),
        "display_name": normalize_space(data.get("display_name")),
        "schema_class": normalize_space(data.get("schema_class")),
        "species_name": normalize_space(data.get("species_name")),
        "participant_count": data.get("participant_count", 0),
        "reference_count": data.get("reference_count", 0),
        "url": normalize_space(data.get("url")),
    }


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
            "name": "reactome_lookup",
            "title": "Look up a Reactome pathway or event",
            "description": (
                "Fetch one Reactome pathway/event by stable ID and return a "
                "front-end-compatible pathway record with browser URLs, "
                "participants, network/table previews, and literature references."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "stable_id": {
                        "type": "string",
                        "description": "Reactome stable ID, for example R-HSA-5633007.",
                    },
                    "include_participants": {
                        "type": "boolean",
                        "default": True,
                    },
                    "max_participants": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": MAX_PARTICIPANTS,
                        "default": MAX_PARTICIPANTS,
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["stable_id"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "reactome_search",
            "title": "Search Reactome pathways",
            "description": (
                "Search Reactome by text and return app-renderable pathway records "
                "with stable Reactome URLs and preview hints."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text query, for example TP53 or apoptosis.",
                    },
                    "species": {
                        "type": "string",
                        "default": "Homo sapiens",
                    },
                    "types": {
                        "type": "string",
                        "default": "Pathway",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_SEARCH_RESULTS,
                        "default": 10,
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
            "name": "reactome_pathways_for_identifier",
            "title": "Map a biological identifier to Reactome pathways",
            "description": (
                "Use the Reactome mapping API to resolve identifiers such as "
                "UniProt accessions to the pathways they participate in."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "External identifier, for example P04637.",
                    },
                    "resource": {
                        "type": "string",
                        "default": "UniProt",
                        "description": "Reactome mapping resource, for example UniProt, Ensembl, or ChEBI.",
                    },
                    "species": {
                        "type": "string",
                        "default": "9606",
                        "description": "Species filter accepted by Reactome, commonly 9606 for human.",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_SEARCH_RESULTS,
                        "default": 10,
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["identifier"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "reactome_status",
            "title": "Inspect Reactome MCP status",
            "description": "Return configured Reactome MCP capabilities and optional network health.",
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


TOOL_HANDLERS: dict[str, Callable[[JsonObject, ReactomeClient], JsonObject]] = {
    "reactome_lookup": reactome_lookup,
    "reactome_search": reactome_search,
    "reactome_pathways_for_identifier": reactome_pathways_for_identifier,
    "reactome_status": reactome_status,
}

