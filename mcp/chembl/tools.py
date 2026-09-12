"""MCP tool registry for the ChEMBL server."""

from __future__ import annotations

import urllib.parse
from typing import Callable

from .client import ChemblClient
from .constants import MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import ChemblError, McpError
from .records import (
    chembl_activity_record,
    chembl_assay_record,
    chembl_document_record,
    chembl_drug_indication_record,
    chembl_mechanism_record,
    chembl_molecule_record,
    chembl_target_record,
)
from .utils import (
    normalize_space,
    optional_bool,
    optional_int,
    optional_string,
    require_non_empty_string,
    source_info,
)


def chembl_status(args: JsonObject, client: ChemblClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "chembl",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "website_base_url": client.config.website_base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["chembl"],
        "tool_groups": {
            "compound": ["chembl_molecule_lookup", "chembl_molecule_search"],
            "target": ["chembl_target_lookup"],
            "assay": ["chembl_assay_lookup"],
            "document": ["chembl_document_lookup"],
            "activity": ["chembl_activity_search"],
            "mechanism": ["chembl_mechanism_search"],
            "indication": ["chembl_drug_indications"],
            "status": ["chembl_status"],
        },
        "frontend_components": ["compound", "protein", "dataset"],
        "preview_kinds": ["chemical_structure", "table", "xref_groups"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload, headers = client.request_json_with_headers("status.json", {})
        if not isinstance(payload, dict):
            raise ChemblError("ChEMBL status returned an unexpected payload")
        status["network_check"] = {
            "ok": True,
            "status": payload.get("status"),
            "chembl_db_version": payload.get("chembl_db_version") or payload.get("database_version"),
            "release_date": payload.get("release_date"),
            "api_version": payload.get("api_version"),
            "content_type": headers.get("content-type"),
        }
    return status


def chembl_molecule_lookup(args: JsonObject, client: ChemblClient) -> JsonObject:
    molecule_chembl_id = require_non_empty_string(args, "molecule_chembl_id")
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"molecule/{urllib.parse.quote(molecule_chembl_id, safe='')}.json"
    payload, headers = client.request_json_with_headers(endpoint, {})
    if not isinstance(payload, dict) or not payload.get("molecule_chembl_id"):
        raise ChemblError(f"ChEMBL molecule not found for {molecule_chembl_id}")
    record = chembl_molecule_record(
        payload,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "chembl",
        "query": molecule_chembl_id,
        "returned": 1,
        "molecule": molecule_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def chembl_molecule_search(args: JsonObject, client: ChemblClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    params: JsonObject = {"q": query, "limit": max_results}
    payload, headers = client.request_json_with_headers("molecule/search.json", params)
    molecules = collection(payload, "molecules")
    records = [
        chembl_molecule_record(
            molecule,
            website_base_url=client.config.website_base_url,
            api_base_url=client.config.base_url,
        )
        for molecule in molecules
    ]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "chembl",
        "query": query,
        "returned": len(records),
        "total": page_total(payload, fallback=len(records)),
        "molecules": [molecule_summary(record) for record in records],
        "records": records,
        "source": source_with_headers("molecule/search.json", params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def chembl_target_lookup(args: JsonObject, client: ChemblClient) -> JsonObject:
    target_chembl_id = require_non_empty_string(args, "target_chembl_id")
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"target/{urllib.parse.quote(target_chembl_id, safe='')}.json"
    payload, headers = client.request_json_with_headers(endpoint, {})
    if not isinstance(payload, dict) or not payload.get("target_chembl_id"):
        raise ChemblError(f"ChEMBL target not found for {target_chembl_id}")
    record = chembl_target_record(
        payload,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "chembl",
        "query": target_chembl_id,
        "returned": 1,
        "target": target_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def chembl_assay_lookup(args: JsonObject, client: ChemblClient) -> JsonObject:
    assay_chembl_id = require_non_empty_string(args, "assay_chembl_id")
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"assay/{urllib.parse.quote(assay_chembl_id, safe='')}.json"
    payload, headers = client.request_json_with_headers(endpoint, {})
    if not isinstance(payload, dict) or not payload.get("assay_chembl_id"):
        raise ChemblError(f"ChEMBL assay not found for {assay_chembl_id}")
    record = chembl_assay_record(
        payload,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "chembl",
        "query": assay_chembl_id,
        "returned": 1,
        "assay": assay_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def chembl_document_lookup(args: JsonObject, client: ChemblClient) -> JsonObject:
    document_chembl_id = require_non_empty_string(args, "document_chembl_id")
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"document/{urllib.parse.quote(document_chembl_id, safe='')}.json"
    payload, headers = client.request_json_with_headers(endpoint, {})
    if not isinstance(payload, dict) or not payload.get("document_chembl_id"):
        raise ChemblError(f"ChEMBL document not found for {document_chembl_id}")
    record = chembl_document_record(
        payload,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "chembl",
        "query": document_chembl_id,
        "returned": 1,
        "document": document_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def chembl_activity_search(args: JsonObject, client: ChemblClient) -> JsonObject:
    molecule_chembl_id = optional_string(args, "molecule_chembl_id")
    target_chembl_id = optional_string(args, "target_chembl_id")
    standard_type = optional_string(args, "standard_type")
    if not molecule_chembl_id and not target_chembl_id:
        raise McpError(-32602, "molecule_chembl_id or target_chembl_id is required")
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    params = activity_params(
        molecule_chembl_id=molecule_chembl_id,
        target_chembl_id=target_chembl_id,
        standard_type=standard_type,
        limit=max_results,
    )
    payload, headers = client.request_json_with_headers("activity.json", params)
    activities = collection(payload, "activities")
    query_label = relation_query_label(molecule_chembl_id=molecule_chembl_id, target_chembl_id=target_chembl_id)
    total = page_total(payload, fallback=len(activities))
    record = chembl_activity_record(
        query_label=query_label,
        activities=activities,
        total=total,
        params=params,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "chembl",
        "query": query_label,
        "returned": len(activities),
        "total": total,
        "activity": activity_summary(record),
        "records": [record],
        "source": source_with_headers("activity.json", params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def chembl_mechanism_search(args: JsonObject, client: ChemblClient) -> JsonObject:
    molecule_chembl_id = optional_string(args, "molecule_chembl_id")
    target_chembl_id = optional_string(args, "target_chembl_id")
    if not molecule_chembl_id and not target_chembl_id:
        raise McpError(-32602, "molecule_chembl_id or target_chembl_id is required")
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    params = activity_params(
        molecule_chembl_id=molecule_chembl_id,
        target_chembl_id=target_chembl_id,
        standard_type=None,
        limit=max_results,
    )
    payload, headers = client.request_json_with_headers("mechanism.json", params)
    mechanisms = collection(payload, "mechanisms")
    query_label = relation_query_label(molecule_chembl_id=molecule_chembl_id, target_chembl_id=target_chembl_id)
    total = page_total(payload, fallback=len(mechanisms))
    record = chembl_mechanism_record(
        query_label=query_label,
        mechanisms=mechanisms,
        total=total,
        params=params,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "chembl",
        "query": query_label,
        "returned": len(mechanisms),
        "total": total,
        "mechanism": mechanism_summary(record),
        "records": [record],
        "source": source_with_headers("mechanism.json", params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def chembl_drug_indications(args: JsonObject, client: ChemblClient) -> JsonObject:
    molecule_chembl_id = require_non_empty_string(args, "molecule_chembl_id")
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    params: JsonObject = {"molecule_chembl_id": molecule_chembl_id, "limit": max_results}
    payload, headers = client.request_json_with_headers("drug_indication.json", params)
    indications = collection(payload, "drug_indications")
    total = page_total(payload, fallback=len(indications))
    record = chembl_drug_indication_record(
        molecule_chembl_id=molecule_chembl_id,
        indications=indications,
        total=total,
        params=params,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "chembl",
        "query": molecule_chembl_id,
        "returned": len(indications),
        "total": total,
        "indications": indication_summary(record),
        "records": [record],
        "source": source_with_headers("drug_indication.json", params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def collection(payload: object, key: str) -> list[JsonObject]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def page_total(payload: object, *, fallback: int) -> int:
    if not isinstance(payload, dict):
        return fallback
    page_meta = payload.get("page_meta")
    if isinstance(page_meta, dict):
        value = page_meta.get("total_count")
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    value = payload.get("total_count")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return fallback


def activity_params(
    *,
    molecule_chembl_id: str | None,
    target_chembl_id: str | None,
    standard_type: str | None,
    limit: int,
) -> JsonObject:
    params: JsonObject = {"limit": limit}
    if molecule_chembl_id:
        params["molecule_chembl_id"] = molecule_chembl_id
    if target_chembl_id:
        params["target_chembl_id"] = target_chembl_id
    if standard_type:
        params["standard_type"] = standard_type
    return params


def relation_query_label(*, molecule_chembl_id: str | None, target_chembl_id: str | None) -> str:
    parts = [part for part in [molecule_chembl_id, target_chembl_id] if part]
    return " / ".join(parts) if parts else "ChEMBL query"


def molecule_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "molecule_chembl_id": data.get("molecule_chembl_id"),
        "pref_name": data.get("pref_name"),
        "molecule_type": data.get("molecule_type"),
        "max_phase": data.get("max_phase"),
        "canonical_smiles": data.get("canonical_smiles"),
        "url": data.get("url"),
    }


def target_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "target_chembl_id": data.get("target_chembl_id"),
        "pref_name": data.get("pref_name"),
        "target_type": data.get("target_type"),
        "organism": data.get("organism"),
        "components": len(data.get("components", [])) if isinstance(data.get("components"), list) else 0,
        "url": data.get("url"),
    }


def assay_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "assay_chembl_id": data.get("assay_chembl_id"),
        "assay_type": data.get("assay_type"),
        "assay_type_description": data.get("assay_type_description"),
        "organism": data.get("organism"),
        "target_chembl_id": data.get("target_chembl_id"),
        "document_chembl_id": data.get("document_chembl_id"),
        "confidence_score": data.get("confidence_score"),
        "url": data.get("url"),
    }


def document_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "document_chembl_id": data.get("document_chembl_id"),
        "title": data.get("title"),
        "journal": data.get("journal"),
        "year": data.get("year"),
        "pubmed_id": data.get("pubmed_id"),
        "doi": data.get("doi"),
        "url": data.get("primary_url") or data.get("url"),
    }


def activity_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "query": data.get("query"),
        "returned": len(data.get("activities", [])) if isinstance(data.get("activities"), list) else 0,
        "total_activities": data.get("total_activities"),
        "url": data.get("url"),
    }


def mechanism_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "query": data.get("query"),
        "returned": len(data.get("mechanisms", [])) if isinstance(data.get("mechanisms"), list) else 0,
        "total_mechanisms": data.get("total_mechanisms"),
        "url": data.get("url"),
    }


def indication_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "molecule_chembl_id": data.get("molecule_chembl_id"),
        "returned": len(data.get("indications", [])) if isinstance(data.get("indications"), list) else 0,
        "total_indications": data.get("total_indications"),
        "url": data.get("url"),
    }


def source_with_headers(endpoint: str, params: JsonObject, headers: dict[str, str]) -> JsonObject:
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
            "name": "chembl_molecule_lookup",
            "title": "Look up a ChEMBL compound",
            "description": (
                "Fetch one ChEMBL molecule by CHEMBL ID and return a front-end-compatible "
                "compound record with structure, properties, synonyms, cross-references, and links."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "molecule_chembl_id": {
                        "type": "string",
                        "description": "ChEMBL molecule ID, for example CHEMBL25.",
                    },
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["molecule_chembl_id"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "chembl_molecule_search",
            "title": "Search ChEMBL compounds",
            "description": (
                "Search ChEMBL molecules by text and return compound records with browser/API links "
                "and chemical structure preview hints."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search text, for example imatinib."},
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_RESULTS,
                        "default": 10,
                    },
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "chembl_target_lookup",
            "title": "Look up a ChEMBL target",
            "description": (
                "Fetch one ChEMBL target by target CHEMBL ID and return a protein-style record with "
                "target components, UniProt links, and cross-reference previews."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "target_chembl_id": {
                        "type": "string",
                        "description": "ChEMBL target ID, for example CHEMBL1824.",
                    },
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["target_chembl_id"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "chembl_activity_search",
            "title": "Search ChEMBL bioactivity rows",
            "description": (
                "Fetch ChEMBL activity measurements for a molecule, target, or molecule-target pair "
                "and return a dataset record with bounded activity tables and clickable entities."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "molecule_chembl_id": {"type": "string", "description": "Optional molecule ID, for example CHEMBL25."},
                    "target_chembl_id": {"type": "string", "description": "Optional target ID, for example CHEMBL1824."},
                    "standard_type": {"type": "string", "description": "Optional activity type filter, for example IC50."},
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_RESULTS,
                        "default": 10,
                    },
                    "include_raw": {"type": "boolean", "default": False},
                },
                "anyOf": [
                    {"required": ["molecule_chembl_id"]},
                    {"required": ["target_chembl_id"]},
                ],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "chembl_assay_lookup",
            "title": "Look up a ChEMBL assay",
            "description": (
                "Fetch one ChEMBL assay by assay CHEMBL ID and return a dataset record with "
                "assay type, BAO format, organism, target, document, confidence, and clickable links."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "assay_chembl_id": {
                        "type": "string",
                        "description": "ChEMBL assay ID, for example CHEMBL1217643.",
                    },
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["assay_chembl_id"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "chembl_document_lookup",
            "title": "Look up a ChEMBL document",
            "description": (
                "Fetch one ChEMBL source document by document CHEMBL ID and return a citation record "
                "with title, authors, journal, year, PMID, DOI, abstract, and clickable PubMed/DOI/ChEMBL links."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "document_chembl_id": {
                        "type": "string",
                        "description": "ChEMBL document ID, for example CHEMBL1212834.",
                    },
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["document_chembl_id"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "chembl_mechanism_search",
            "title": "Search ChEMBL drug mechanisms",
            "description": (
                "Fetch ChEMBL mechanism-of-action rows for a molecule, target, or pair and return "
                "a dataset record with mechanism tables, references, and clickable entities."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "molecule_chembl_id": {"type": "string", "description": "Optional molecule ID, for example CHEMBL25."},
                    "target_chembl_id": {"type": "string", "description": "Optional target ID, for example CHEMBL1824."},
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_RESULTS,
                        "default": 10,
                    },
                    "include_raw": {"type": "boolean", "default": False},
                },
                "anyOf": [
                    {"required": ["molecule_chembl_id"]},
                    {"required": ["target_chembl_id"]},
                ],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "chembl_drug_indications",
            "title": "Fetch ChEMBL drug indications",
            "description": (
                "Fetch ChEMBL drug indication rows for a molecule and return a dataset record with "
                "indication terms, EFO/HPO and MeSH identifiers, evidence references, and clickable links."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "molecule_chembl_id": {
                        "type": "string",
                        "description": "ChEMBL molecule ID, for example CHEMBL25.",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_RESULTS,
                        "default": 10,
                    },
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["molecule_chembl_id"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "chembl_status",
            "title": "Inspect ChEMBL MCP status",
            "description": "Return configured ChEMBL MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
    ]


TOOL_HANDLERS: dict[str, Callable[[JsonObject, ChemblClient], JsonObject]] = {
    "chembl_molecule_lookup": chembl_molecule_lookup,
    "chembl_molecule_search": chembl_molecule_search,
    "chembl_target_lookup": chembl_target_lookup,
    "chembl_assay_lookup": chembl_assay_lookup,
    "chembl_document_lookup": chembl_document_lookup,
    "chembl_activity_search": chembl_activity_search,
    "chembl_mechanism_search": chembl_mechanism_search,
    "chembl_drug_indications": chembl_drug_indications,
    "chembl_status": chembl_status,
}
