"""MCP tool registry for the Reactome server."""

from __future__ import annotations

from mcp.dynamic_context import build_dynamic_context_response
from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition
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
from .errors import McpError, ReactomeError
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


REACTOME_CONTEXT_TYPES = ["all", "search", "pathway", "identifier", "species", "resources"]
REACTOME_CONTEXT_SCHEMA_VERSION = "bioinformatics.dynamic_context.v1"
REACTOME_MAPPING_RESOURCES = ["UniProt", "Ensembl", "ChEBI", "miRBase"]
REACTOME_SPECIES_HINTS = [
    ("9606", "Homo sapiens"),
    ("10090", "Mus musculus"),
    ("10116", "Rattus norvegicus"),
    ("7227", "Drosophila melanogaster"),
]


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
            "context": ["reactome_parameter_domains", "reactome_resolve_context"],
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


def reactome_resolve_context(args: JsonObject, client: ReactomeClient) -> JsonObject:
    context_type = optional_context_type(args, "context_type", allowed=REACTOME_CONTEXT_TYPES, default="all")
    query = optional_string(args, "query", default="")
    stable_id = optional_string(args, "stable_id", default="")
    identifier = optional_string(args, "identifier", default="")
    resource = optional_string(args, "resource", default="UniProt")
    species = optional_string(args, "species", default="9606")
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_SEARCH_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    contexts = static_reactome_contexts()
    recommended_calls: list[JsonObject] = []
    sources: list[JsonObject] = []
    raw: JsonObject = {}

    if stable_id:
        result = reactome_lookup(
            {
                "stable_id": stable_id,
                "include_participants": False,
                "max_participants": 0,
                "include_raw": include_raw,
            },
            client,
        )
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(reactome_record_context(record) for record in records)
        recommended_calls.extend(reactome_recommended_calls(record) for record in records)
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["lookup"] = result["raw"]

    if query:
        result = reactome_search(
            {
                "query": query,
                "species": species if not species.isdigit() else "Homo sapiens",
                "types": "Pathway",
                "max_results": max_results,
                "include_raw": include_raw,
            },
            client,
        )
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(reactome_record_context(record) for record in records)
        recommended_calls.extend(reactome_recommended_calls(record) for record in records[:3])
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["search"] = result["raw"]

    if identifier:
        result = reactome_pathways_for_identifier(
            {
                "identifier": identifier,
                "resource": resource,
                "species": species,
                "max_results": max_results,
                "include_raw": include_raw,
            },
            client,
        )
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(reactome_record_context(record, parameter_name="stable_id", kind="mapped_pathway") for record in records)
        recommended_calls.extend(reactome_recommended_calls(record) for record in records[:3])
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["mapping"] = result["raw"]

    filtered_contexts = [
        context
        for context in contexts
        if reactome_context_matches(context, context_type=context_type, query=query or stable_id or identifier)
    ]
    return build_dynamic_context_response(
        schema_version=RESULT_SCHEMA_VERSION,
        context_schema_version=REACTOME_CONTEXT_SCHEMA_VERSION,
        database="reactome",
        query={
            "context_type": context_type,
            "query": query,
            "stable_id": stable_id,
            "identifier": identifier,
            "resource": resource,
            "species": species,
        },
        contexts=filtered_contexts,
        recommended_calls=recommended_calls,
        max_results=max_results,
        fallback_source=source_info("resolve_context", {"context_type": context_type, "query": query, "stable_id": stable_id, "identifier": identifier}),
        sources=sources,
        entity_groups={"pathway"},
        raw=raw,
        summary_fields={"pathways": lambda context: context.get("group") == "pathway"},
        include_raw=include_raw,
    )


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


def optional_context_type(args: JsonObject, name: str, *, allowed: list[str], default: str) -> str:
    value = optional_string(args, name, default=default)
    if value not in allowed:
        raise McpError(-32602, f"{name} must be one of: {', '.join(allowed)}")
    return value


def static_reactome_contexts() -> list[JsonObject]:
    contexts: list[JsonObject] = [
        reactome_parameter_context(
            "context_type",
            value,
            label=value,
            description="Dynamic Reactome context family to resolve before pathway lookup, search, or identifier mapping.",
            kind="enum",
            group="search",
            url="",
            metadata={"context_type": value},
        )
        for value in REACTOME_CONTEXT_TYPES
    ]
    contexts.extend(
        reactome_parameter_context(
            "resource",
            resource,
            label=resource,
            description="Reactome identifier-mapping resource accepted by reactome_pathways_for_identifier.",
            kind="mapping_resource",
            group="resources",
            url="https://reactome.org/ContentService/",
            metadata={"tool_hint": "reactome_pathways_for_identifier"},
        )
        for resource in REACTOME_MAPPING_RESOURCES
    )
    contexts.extend(
        reactome_parameter_context(
            "species",
            taxid,
            label=name,
            description="Common Reactome species filter for identifier-to-pathway mapping.",
            kind="species",
            group="species",
            url=f"https://reactome.org/content/query?q={taxid}",
            metadata={"taxon_id": taxid, "scientific_name": name},
        )
        for taxid, name in REACTOME_SPECIES_HINTS
    )
    return contexts


def reactome_record_context(record: JsonObject, *, parameter_name: str = "stable_id", kind: str = "pathway") -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    stable_id = normalize_space(data.get("stable_id") or record.get("id"))
    title = normalize_space(record.get("title") or data.get("display_name") or stable_id)
    return reactome_parameter_context(
        parameter_name,
        stable_id,
        label=title,
        description=normalize_space(record.get("description") or data.get("summary") or "Reactome pathway/event."),
        kind=kind,
        group="pathway",
        url=normalize_space(record.get("url") or data.get("url")),
        metadata={
            "stable_id": stable_id,
            "db_id": data.get("db_id", ""),
            "schema_class": data.get("schema_class", ""),
            "species_name": data.get("species_name", ""),
            "participant_count": data.get("participant_count", 0),
            "reference_count": data.get("reference_count", 0),
        },
    )


def reactome_parameter_context(
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
    display_fields = [
        {"label": key.replace("_", " ").title(), "value": item}
        for key, item in metadata.items()
        if item not in ("", None, [], {})
    ]
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
            "component": "pathway",
            "chip_label": parameter_name,
            "icon": "reactome",
            "title": label,
            "subtitle": f"{parameter_name}: {value}",
            "description": description,
            "metadata": display_fields,
            "badges": [
                {"label": "Reactome", "kind": "source"},
                {"label": parameter_name, "kind": "parameter"},
            ],
            "actions": [{"label": "Open source", "url": url, "kind": "external", "primary": True}] if url else [],
            "hover": {"title": label, "subtitle": f"{parameter_name}: {value}", "icon": "reactome", "fields": display_fields},
            "primary_url": url,
        },
    }


def reactome_recommended_calls(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    stable_id = normalize_space(data.get("stable_id") or record.get("id"))
    return {
        "tool_name": "reactome_lookup",
        "arguments": {"stable_id": stable_id},
        "reason": "Fetch detailed Reactome pathway metadata, participant previews, and literature references.",
    }


def reactome_context_matches(context: JsonObject, *, context_type: str, query: str) -> bool:
    if context_type != "all" and context.get("group") != context_type:
        return False
    if not query:
        return True
    metadata = context.get("metadata")
    haystack_values = [
        context.get("parameter_name"),
        context.get("value"),
        context.get("label"),
        context.get("description"),
        context.get("kind"),
    ]
    if isinstance(metadata, dict):
        haystack_values.extend(metadata.values())
    haystack = " ".join(str(item).lower() for item in haystack_values if item not in ("", None))
    return query.lower() in haystack or context.get("group") == "pathway"


def tool_definitions() -> list[JsonObject]:
    read_only_annotations = {
        "readOnlyHint": True,
        "openWorldHint": True,
    }
    return [
        parameter_domains_tool_definition("reactome_parameter_domains"),
        {
            "name": "reactome_resolve_context",
            "title": "Resolve Reactome dynamic parameter context",
            "description": (
                "Resolve Reactome pathway IDs, search hits, species/resource hints, and identifier-to-pathway mappings "
                "before calling lookup or pathway mapping tools. Returns front-end-friendly context rows and recommended calls."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "context_type": {"type": "string", "enum": REACTOME_CONTEXT_TYPES, "default": "all"},
                    "query": {"type": "string", "description": "Optional pathway text search such as TP53 or apoptosis."},
                    "stable_id": {"type": "string", "description": "Optional Reactome stable ID such as R-HSA-5633007."},
                    "identifier": {"type": "string", "description": "Optional external identifier such as UniProt accession P04637."},
                    "resource": {"type": "string", "description": "Reactome mapping resource such as UniProt, Ensembl, or ChEBI.", "default": "UniProt"},
                    "species": {"type": "string", "description": "Species filter such as 9606.", "default": "9606"},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_SEARCH_RESULTS, "default": 10},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
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
    "reactome_parameter_domains": make_parameter_domains_handler("reactome", "reactome_parameter_domains", tool_definitions),
    "reactome_resolve_context": reactome_resolve_context,
    "reactome_lookup": reactome_lookup,
    "reactome_search": reactome_search,
    "reactome_pathways_for_identifier": reactome_pathways_for_identifier,
    "reactome_status": reactome_status,
}
