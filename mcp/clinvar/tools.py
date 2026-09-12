"""MCP tool registry for the ClinVar server."""

from __future__ import annotations

from typing import Callable

from .client import ClinvarClient
from .constants import MAX_IDS_PER_SUMMARY, MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import ClinvarError
from .records import clinvar_variant_record
from .utils import (
    clinvar_uid,
    normalize_space,
    optional_bool,
    optional_int,
    require_non_empty_string,
    source_info,
)


def clinvar_status(args: JsonObject, client: ClinvarClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "clinvar",
        "version": "0.1.0",
        "clinical_tables_url": client.config.clinical_tables_url,
        "eutils_base_url": client.config.eutils_base_url,
        "tool": client.config.tool,
        "email_configured": bool(client.config.email),
        "api_key_configured": bool(client.config.api_key),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["clinvar"],
        "tool_groups": {
            "variation": ["clinvar_lookup", "clinvar_search"],
            "status": ["clinvar_status"],
        },
        "frontend_components": ["variant"],
        "preview_kinds": ["table", "xref_groups"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload, _headers = client.request_eutils_json_with_headers(
            "esummary.fcgi",
            {"db": "clinvar", "id": "37390"},
        )
        item = first_esummary_item(payload)
        status["network_check"] = {
            "ok": True,
            "uid": item.get("uid"),
            "accession": item.get("accession"),
        }
    return status


def clinvar_lookup(args: JsonObject, client: ClinvarClient) -> JsonObject:
    identifier = require_non_empty_string(args, "identifier")
    uid = clinvar_uid(identifier)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = "esummary.fcgi"
    params: JsonObject = {"db": "clinvar", "id": uid}
    payload, headers = client.request_eutils_json_with_headers(endpoint, params)
    item = first_esummary_item(payload)
    if not item:
        raise ClinvarError(f"ClinVar record not found for {identifier}")
    record = clinvar_variant_record(item)
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "clinvar",
        "query": identifier,
        "returned": 1,
        "variant": variant_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def clinvar_search(args: JsonObject, client: ClinvarClient) -> JsonObject:
    terms = require_non_empty_string(args, "terms")
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_RESULTS)
    hydrate = optional_bool(args, "hydrate", default=True)
    include_raw = optional_bool(args, "include_raw", default=False)
    params: JsonObject = {"terms": terms, "maxList": max_results}
    search_payload, search_headers = client.request_clinical_tables_with_headers(params)
    if not isinstance(search_payload, list) or len(search_payload) < 4:
        raise ClinvarError("Clinical Tables response did not match expected list shape")
    total = search_payload[0] if isinstance(search_payload[0], int) else 0
    identifiers = search_payload[1] if isinstance(search_payload[1], list) else []
    display_rows = search_payload[3] if isinstance(search_payload[3], list) else []
    labels = display_row_labels(display_rows)
    records: list[JsonObject] = []
    summaries: list[JsonObject] = []
    if hydrate and identifiers:
        ids = [clinvar_uid(item) for item in identifiers[: min(max_results, MAX_IDS_PER_SUMMARY)]]
        summary_payload, _summary_headers = client.request_eutils_json_with_headers(
            "esummary.fcgi",
            {"db": "clinvar", "id": ",".join(ids)},
        )
        summaries = esummary_items(summary_payload)
        label_by_uid = {
            clinvar_uid(uid): labels[index]
            for index, uid in enumerate(identifiers)
            if index < len(labels)
        }
        records = [
            clinvar_variant_record(item, search_label=label_by_uid.get(clinvar_uid(item.get("uid")), ""))
            for item in summaries
        ]
    else:
        records = [clinical_tables_record(uid, labels[index] if index < len(labels) else "") for index, uid in enumerate(identifiers[:max_results])]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "clinvar",
        "query": terms,
        "returned": len(records),
        "total": total,
        "truncated": total > len(records),
        "identifiers": identifiers[:max_results],
        "records": records,
        "source": source_with_headers("clinicaltables/search", params, search_headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = search_payload
    return response


def first_esummary_item(payload: JsonObject) -> JsonObject:
    items = esummary_items(payload)
    return items[0] if items else {}


def esummary_items(payload: JsonObject) -> list[JsonObject]:
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    uids = result.get("uids") if isinstance(result.get("uids"), list) else []
    items = []
    for uid in uids:
        item = result.get(str(uid))
        if isinstance(item, dict):
            items.append(item)
    return items


def display_row_labels(rows: object) -> list[str]:
    labels = []
    if not isinstance(rows, list):
        return labels
    for row in rows:
        if isinstance(row, list) and len(row) > 1:
            labels.append(normalize_space(row[1]))
        else:
            labels.append(normalize_space(row))
    return labels


def clinical_tables_record(uid: object, label: str) -> JsonObject:
    uid_text = clinvar_uid(uid)
    item: JsonObject = {
        "uid": uid_text,
        "title": label or uid_text,
        "accession": f"VCV{int(uid_text):09d}" if uid_text.isdigit() else "",
        "variation_set": [{"variation_name": label}],
    }
    return clinvar_variant_record(item, search_label=label)


def variant_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "uid": normalize_space(data.get("uid")),
        "accession": normalize_space(data.get("accession")),
        "title": normalize_space(data.get("title")),
        "classification": normalize_space(data.get("classification")),
        "gene": normalize_space(data.get("primary_gene")),
        "location": normalize_space(data.get("primary_location")),
        "url": normalize_space(data.get("url")),
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
            "name": "clinvar_lookup",
            "title": "Look up a ClinVar VCV/variation record",
            "description": (
                "Fetch one ClinVar variation by numeric UID or VCV accession "
                "and return a front-end-compatible variant record."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "ClinVar UID or VCV accession, for example 37390 or VCV000037390.",
                    },
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["identifier"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "clinvar_search",
            "title": "Search ClinVar variants",
            "description": (
                "Search ClinVar via NLM Clinical Tables, optionally hydrate "
                "top hits through NCBI ClinVar ESummary, and return variant records."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "terms": {"type": "string", "description": "Search terms such as BRCA1 or VCV000037390."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": 10},
                    "hydrate": {"type": "boolean", "default": True},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["terms"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "clinvar_status",
            "title": "Inspect ClinVar MCP status",
            "description": "Return configured ClinVar MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
    ]


TOOL_HANDLERS: dict[str, Callable[[JsonObject, ClinvarClient], JsonObject]] = {
    "clinvar_lookup": clinvar_lookup,
    "clinvar_search": clinvar_search,
    "clinvar_status": clinvar_status,
}

