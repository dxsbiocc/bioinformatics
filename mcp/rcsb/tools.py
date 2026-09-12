"""MCP tool registry for the RCSB PDB server."""

from __future__ import annotations

from typing import Callable

from .client import RcsbClient
from .constants import (
    MAX_ENTITY_SUMMARIES,
    MAX_SEARCH_RESULTS,
    RCSB_DATA_API_BASE_URL,
    RCSB_SEARCH_API_BASE_URL,
    RCSB_WEBSITE_BASE_URL,
    RESULT_SCHEMA_VERSION,
    JsonObject,
)
from .records import rcsb_fasta_record, rcsb_structure_record
from .utils import (
    normalize_space,
    optional_bool,
    optional_int,
    require_non_empty_string,
    require_pdb_id,
    source_info,
)


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


def tool_definitions() -> list[JsonObject]:
    read_only_annotations = {
        "readOnlyHint": True,
        "openWorldHint": True,
    }
    return [
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
    "rcsb_lookup": rcsb_lookup,
    "rcsb_search": rcsb_search,
    "rcsb_fasta": rcsb_fasta,
    "rcsb_status": rcsb_status,
}

