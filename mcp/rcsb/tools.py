"""MCP tool registry for the RCSB PDB server."""

from __future__ import annotations

from collections.abc import Callable

from mcp.dynamic_context import build_dynamic_context_response
from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition

from .client import RcsbClient
from .constants import (
    MAX_ENTITY_SUMMARIES,
    MAX_SEARCH_RESULTS,
    RESULT_SCHEMA_VERSION,
    JsonObject,
)
from .errors import McpError
from .records import rcsb_fasta_record, rcsb_structure_record
from .utils import (
    normalize_space,
    optional_bool,
    optional_int,
    require_non_empty_string,
    require_pdb_id,
    source_info,
)

RCSB_CONTEXT_TYPES = ["all", "search", "entry", "downloads"]
RCSB_CONTEXT_SCHEMA_VERSION = "bioinformatics.dynamic_context.v1"
RCSB_DOWNLOAD_OPTIONS = ["pdb", "cif", "bcif", "pdbx", "fasta"]


def rcsb_status(args: JsonObject, client: RcsbClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "rcsb",
        "version": "0.1.0",
        "data_base_url": client.config.data_base_url,
        "search_base_url": client.config.search_base_url,
        "website_url": client.config.website_base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["rcsb_pdb"],
        "tool_groups": {
            "context": ["rcsb_parameter_domains", "rcsb_resolve_context"],
            "protein_structure": [
                "rcsb_lookup",
                "rcsb_search",
                "rcsb_fasta",
            ],
            "status": ["rcsb_status"],
        },
        "frontend_components": ["protein_structure", "protein"],
        "preview_kinds": [
            "structure_3d",
            "download_manifest",
            "table",
            "citation_list",
            "sequence",
        ],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        entry, _headers = client.request_data_json_with_headers("core/entry/4HHB", {})
        status["network_check"] = {
            "ok": True,
            "entry_id": entry.get("rcsb_id"),
        }
    return status


def rcsb_resolve_context(args: JsonObject, client: RcsbClient) -> JsonObject:
    context_type = optional_context_type(args, "context_type", allowed=RCSB_CONTEXT_TYPES, default="all")
    query = optional_string(args, "query")
    pdb_id = optional_string(args, "pdb_id")
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_SEARCH_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    contexts = static_rcsb_contexts(client)
    recommended_calls: list[JsonObject] = []
    sources: list[JsonObject] = []
    raw: JsonObject = {}

    if pdb_id:
        pdb_id = require_pdb_id({"pdb_id": pdb_id})
        endpoint = f"core/entry/{pdb_id}"
        entry, headers = client.request_data_json_with_headers(endpoint, {})
        raw["entry"] = entry
        sources.append(source_with_headers(endpoint, {}, headers))
        contexts.append(rcsb_entry_context(entry, client))
        recommended_calls.extend(rcsb_recommended_calls(pdb_id))

    if query:
        payload: JsonObject = {
            "query": {
                "type": "terminal",
                "service": "full_text",
                "parameters": {"value": query},
            },
            "return_type": "entry",
            "request_options": {"paginate": {"start": 0, "rows": max_results}},
        }
        search_payload, headers = client.request_search_json_with_headers("query", payload)
        raw["search"] = search_payload
        sources.append(source_with_headers("query", {"json_body": payload}, headers))
        hits = [item for item in search_payload.get("result_set", []) if isinstance(item, dict) and normalize_space(item.get("identifier"))]
        for hit in hits[:max_results]:
            hit_id = normalize_space(hit.get("identifier")).upper()
            contexts.append(rcsb_hit_context(hit_id, client, score=hit.get("score", "")))
            recommended_calls.extend(rcsb_recommended_calls(hit_id))

    query_text = query or pdb_id
    filtered_contexts = [context for context in contexts if rcsb_context_matches(context, context_type=context_type, query=query_text)]
    return build_dynamic_context_response(
        schema_version=RESULT_SCHEMA_VERSION,
        context_schema_version=RCSB_CONTEXT_SCHEMA_VERSION,
        database="rcsb_pdb",
        query={
            "context_type": context_type,
            "query": query,
            "pdb_id": pdb_id,
        },
        contexts=filtered_contexts,
        recommended_calls=recommended_calls,
        max_results=max_results,
        fallback_source=source_info("resolve_context", {"context_type": context_type, "query": query, "pdb_id": pdb_id}),
        sources=sources,
        entity_groups={"entry"},
        raw=raw,
        summary_fields={"entries": lambda context: context.get("parameter_name") == "pdb_id"},
        include_raw=include_raw,
        call_dedupe_include_server=False,
    )


def rcsb_lookup(args: JsonObject, client: RcsbClient) -> JsonObject:
    pdb_id = require_pdb_id(args)
    include_entities = optional_bool(args, "include_entities", default=True)
    include_ligands = optional_bool(args, "include_ligands", default=True)
    include_raw = optional_bool(args, "include_raw", default=False)
    max_entities = optional_int(
        args,
        "max_entities",
        default=MAX_ENTITY_SUMMARIES,
        minimum=0,
        maximum=MAX_ENTITY_SUMMARIES,
    )
    entry_endpoint = f"core/entry/{pdb_id}"
    entry, entry_headers = client.request_data_json_with_headers(entry_endpoint, {})
    polymer_entities: list[JsonObject] = []
    nonpolymer_entities: list[JsonObject] = []
    if include_entities:
        polymer_entities = fetch_polymer_entities(
            entry,
            client,
            pdb_id=pdb_id,
            max_entities=max_entities,
        )
    if include_ligands:
        nonpolymer_entities = fetch_nonpolymer_entities(
            entry,
            client,
            pdb_id=pdb_id,
            max_entities=max_entities,
        )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "rcsb_pdb",
        "query": pdb_id,
        "returned": 1,
        "entry": entry_summary(entry, polymer_entities, nonpolymer_entities),
        "records": [
            rcsb_structure_record(
                entry,
                polymer_entities=polymer_entities,
                nonpolymer_entities=nonpolymer_entities,
            )
        ],
        "source": source_with_headers(entry_endpoint, {}, entry_headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = {
            "entry": entry,
            "polymer_entities": polymer_entities,
            "nonpolymer_entities": nonpolymer_entities,
        }
    return response


def rcsb_search(args: JsonObject, client: RcsbClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    max_results = optional_int(
        args,
        "max_results",
        default=10,
        minimum=1,
        maximum=MAX_SEARCH_RESULTS,
    )
    fetch_records = optional_bool(args, "fetch_records", default=True)
    include_raw = optional_bool(args, "include_raw", default=False)
    payload: JsonObject = {
        "query": {
            "type": "terminal",
            "service": "full_text",
            "parameters": {
                "value": query,
            },
        },
        "return_type": "entry",
        "request_options": {
            "paginate": {
                "start": 0,
                "rows": max_results,
            }
        },
    }
    search_payload, headers = client.request_search_json_with_headers("query", payload)
    hits = [
        item
        for item in search_payload.get("result_set", [])
        if isinstance(item, dict) and normalize_space(item.get("identifier"))
    ]
    entries: list[JsonObject] = []
    records: list[JsonObject] = []
    if fetch_records:
        for hit in hits[:max_results]:
            pdb_id = normalize_space(hit.get("identifier")).upper()
            entry, _entry_headers = client.request_data_json_with_headers(f"core/entry/{pdb_id}", {})
            entries.append(entry_summary(entry, [], []))
            records.append(
                rcsb_structure_record(
                    entry,
                    polymer_entities=[],
                    nonpolymer_entities=[],
                    search_score=hit.get("score", ""),
                )
            )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "rcsb_pdb",
        "query": query,
        "returned": len(hits[:max_results]),
        "total": search_payload.get("total_count", ""),
        "result_set": hits[:max_results],
        "entries": entries,
        "records": records,
        "source": source_with_headers("query", {"json_body": payload}, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = search_payload
    return response


def rcsb_fasta(args: JsonObject, client: RcsbClient) -> JsonObject:
    pdb_id = require_pdb_id(args)
    url = f"{client.config.website_base_url.rstrip('/')}/fasta/entry/{pdb_id}/download"
    fasta_text, headers = client.request_text_with_headers(
        url,
        label=f"fasta/entry/{pdb_id}/download",
        accept="text/x-fasta,text/plain",
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "rcsb_pdb",
        "query": pdb_id,
        "returned": 1 if fasta_text.strip() else 0,
        "fasta": fasta_text,
        "records": [rcsb_fasta_record(pdb_id, fasta_text)] if fasta_text.strip() else [],
        "source": source_with_headers(f"fasta/entry/{pdb_id}/download", {}, headers),
    }
    response["provenance"] = response["source"]
    return response


def fetch_polymer_entities(
    entry: JsonObject,
    client: RcsbClient,
    *,
    pdb_id: str,
    max_entities: int,
) -> list[JsonObject]:
    identifiers = entry.get("rcsb_entry_container_identifiers")
    if not isinstance(identifiers, dict):
        return []
    entity_ids = identifiers.get("polymer_entity_ids")
    if not isinstance(entity_ids, list):
        return []
    entities = []
    for entity_id in entity_ids[:max_entities]:
        endpoint = f"core/polymer_entity/{pdb_id}/{entity_id}"
        entity, _headers = client.request_data_json_with_headers(endpoint, {})
        entities.append(entity)
    return entities


def fetch_nonpolymer_entities(
    entry: JsonObject,
    client: RcsbClient,
    *,
    pdb_id: str,
    max_entities: int,
) -> list[JsonObject]:
    identifiers = entry.get("rcsb_entry_container_identifiers")
    if not isinstance(identifiers, dict):
        return []
    entity_ids = identifiers.get("non_polymer_entity_ids")
    if not isinstance(entity_ids, list):
        return []
    entities = []
    for entity_id in entity_ids[:max_entities]:
        endpoint = f"core/nonpolymer_entity/{pdb_id}/{entity_id}"
        entity, _headers = client.request_data_json_with_headers(endpoint, {})
        entities.append(entity)
    return entities


def entry_summary(
    entry: JsonObject,
    polymer_entities: list[JsonObject],
    nonpolymer_entities: list[JsonObject],
) -> JsonObject:
    record = rcsb_structure_record(
        entry,
        polymer_entities=polymer_entities,
        nonpolymer_entities=nonpolymer_entities,
    )
    data = record["data"]
    return {
        "pdb_id": data["pdb_id"],
        "title": data["title"],
        "methods": data["methods"],
        "resolution": data["resolution"],
        "polymer_entity_ids": data["polymer_entity_ids"],
        "nonpolymer_entity_ids": data["nonpolymer_entity_ids"],
        "uniprot_ids": data["uniprot_ids"],
        "ligand_ids": data["ligand_ids"],
        "url": data["url"],
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


def optional_string(args: JsonObject, name: str, *, default: str = "") -> str:
    value = args.get(name, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise McpError(-32602, f"{name} must be a string")
    return value.strip() or default


def optional_context_type(args: JsonObject, name: str, *, allowed: list[str], default: str) -> str:
    value = optional_string(args, name, default=default)
    if value not in allowed:
        raise McpError(-32602, f"{name} must be one of: {', '.join(allowed)}")
    return value


def static_rcsb_contexts(client: RcsbClient) -> list[JsonObject]:
    contexts = [
        rcsb_parameter_context(
            "context_type",
            value,
            label=value,
            description="Dynamic RCSB context family to resolve before choosing search, lookup, FASTA, or download views.",
            kind="enum",
            group="search",
            url="",
            metadata={"context_type": value},
        )
        for value in RCSB_CONTEXT_TYPES
    ]
    contexts.extend(
        rcsb_parameter_context(
            "download_option",
            value,
            label=value,
            description="Common RCSB downloadable representation or sequence endpoint.",
            kind="download_option",
            group="downloads",
            url=f"{client.config.website_base_url.rstrip('/')}/docs/programmatic-access/file-download-services",
            metadata={"tool_hint": "rcsb_lookup" if value != "fasta" else "rcsb_fasta"},
        )
        for value in RCSB_DOWNLOAD_OPTIONS
    )
    return contexts


def rcsb_entry_context(entry: JsonObject, client: RcsbClient) -> JsonObject:
    pdb_id = normalize_space(entry.get("rcsb_id")).upper()
    title = normalize_space(entry.get("struct", {}).get("title") if isinstance(entry.get("struct"), dict) else "") or pdb_id
    info = entry.get("rcsb_entry_info") if isinstance(entry.get("rcsb_entry_info"), dict) else {}
    return rcsb_parameter_context(
        "pdb_id",
        pdb_id,
        label=title,
        description="RCSB PDB entry ID resolved through the Data API.",
        kind="pdb_entry",
        group="entry",
        url=rcsb_entry_url(client, pdb_id),
        metadata={
            "pdb_id": pdb_id,
            "method": info.get("experimental_method") or "",
            "resolution": first_resolution(info),
            "tool_hint": "rcsb_lookup",
        },
    )


def rcsb_hit_context(pdb_id: str, client: RcsbClient, *, score: object) -> JsonObject:
    return rcsb_parameter_context(
        "pdb_id",
        pdb_id,
        label=f"PDB {pdb_id}",
        description="RCSB PDB search hit. Use rcsb_lookup to hydrate full structure metadata.",
        kind="pdb_search_hit",
        group="entry",
        url=rcsb_entry_url(client, pdb_id),
        metadata={"pdb_id": pdb_id, "search_score": score, "tool_hint": "rcsb_lookup"},
    )


def rcsb_parameter_context(
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
            "component": "protein_structure" if group in {"entry", "downloads"} else "dataset",
            "chip_label": parameter_name,
            "icon": "rcsb",
            "title": label,
            "subtitle": f"{parameter_name}: {value}",
            "description": description,
            "metadata": display_fields,
            "badges": [
                {"label": "RCSB PDB", "kind": "source"},
                {"label": parameter_name, "kind": "parameter"},
            ],
            "actions": [{"label": "Open source", "url": url, "kind": "external", "primary": True}] if url else [],
            "hover": {"title": label, "subtitle": f"{parameter_name}: {value}", "icon": "rcsb", "fields": display_fields},
            "primary_url": url,
        },
    }


def rcsb_recommended_calls(pdb_id: str) -> list[JsonObject]:
    return [
        {"tool_name": "rcsb_lookup", "arguments": {"pdb_id": pdb_id}, "reason": "Hydrate structure metadata, citations, ligands, UniProt IDs, and 3D/download previews."},
        {"tool_name": "rcsb_fasta", "arguments": {"pdb_id": pdb_id}, "reason": "Fetch FASTA sequences for polymer entities in this PDB entry."},
    ]


def rcsb_context_matches(context: JsonObject, *, context_type: str, query: str) -> bool:
    if context_type != "all" and context.get("group") != context_type:
        return False
    if not query:
        return True
    metadata = context.get("metadata")
    fields = [context.get("parameter_name"), context.get("value"), context.get("label"), context.get("description"), context.get("kind")]
    if isinstance(metadata, dict):
        fields.extend(metadata.values())
    haystack = " ".join(str(field).lower() for field in fields if field not in ("", None))
    return query.lower() in haystack or context.get("group") == "entry"


def first_resolution(info: JsonObject) -> object:
    values = info.get("resolution_combined")
    if isinstance(values, list) and values:
        return values[0]
    return ""


def rcsb_entry_url(client: RcsbClient, pdb_id: str) -> str:
    return f"{client.config.website_base_url.rstrip('/')}/structure/{pdb_id}"


def tool_definitions() -> list[JsonObject]:
    read_only_annotations = {
        "readOnlyHint": True,
        "openWorldHint": True,
    }
    return [
        parameter_domains_tool_definition("rcsb_parameter_domains"),
        {
            "name": "rcsb_resolve_context",
            "title": "Resolve RCSB PDB dynamic parameter context",
            "description": (
                "Resolve RCSB PDB search hits, entry IDs, and download/FASTA context before structure calls. "
                "Returns front-end-friendly context rows, structure URLs, and recommended lookup/FASTA calls."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "context_type": {"type": "string", "enum": RCSB_CONTEXT_TYPES, "default": "all"},
                    "query": {"type": "string", "description": "Optional full-text RCSB search query, for example hemoglobin."},
                    "pdb_id": {"type": "string", "description": "Optional 4-character PDB entry ID, for example 4HHB."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_SEARCH_RESULTS, "default": 10},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "rcsb_lookup",
            "title": "Look up an RCSB PDB structure entry",
            "description": (
                "Fetch RCSB PDB entry metadata and return front-end-compatible "
                "protein_structure records with 3D preview, file URLs, polymer "
                "entity summaries, ligand summaries, citations, and UniProt links."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "pdb_id": {
                        "type": "string",
                        "description": "4-character PDB entry ID, for example 4HHB.",
                    },
                    "include_entities": {
                        "type": "boolean",
                        "default": True,
                    },
                    "include_ligands": {
                        "type": "boolean",
                        "default": True,
                    },
                    "max_entities": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": MAX_ENTITY_SUMMARIES,
                        "default": MAX_ENTITY_SUMMARIES,
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["pdb_id"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "rcsb_search",
            "title": "Search RCSB PDB entries",
            "description": (
                "Search the RCSB Search API and optionally hydrate top hits into "
                "front-end-compatible protein_structure records."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Full-text RCSB search query, for example hemoglobin.",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_SEARCH_RESULTS,
                        "default": 10,
                    },
                    "fetch_records": {
                        "type": "boolean",
                        "default": True,
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
            "name": "rcsb_fasta",
            "title": "Fetch RCSB PDB entry FASTA",
            "description": "Fetch FASTA sequences for one PDB entry and return a sequence preview record.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "pdb_id": {
                        "type": "string",
                        "description": "4-character PDB entry ID, for example 4HHB.",
                    }
                },
                "required": ["pdb_id"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "rcsb_status",
            "title": "Inspect RCSB PDB MCP status",
            "description": "Return configured RCSB MCP capabilities and optional network health.",
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


TOOL_HANDLERS: dict[str, Callable[[JsonObject, RcsbClient], JsonObject]] = {
    "rcsb_parameter_domains": make_parameter_domains_handler("rcsb", "rcsb_parameter_domains", tool_definitions),
    "rcsb_resolve_context": rcsb_resolve_context,
    "rcsb_lookup": rcsb_lookup,
    "rcsb_search": rcsb_search,
    "rcsb_fasta": rcsb_fasta,
    "rcsb_status": rcsb_status,
}
