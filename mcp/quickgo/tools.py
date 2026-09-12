"""MCP tool registry for the QuickGO server."""

from __future__ import annotations

from .client import QuickGoClient
from .constants import DEFAULT_RESULTS, MAX_RELATIONS, MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import McpError, QuickGoError
from .records import quickgo_annotation_dataset_record, quickgo_term_record
from .utils import (
    optional_bool,
    optional_go_id,
    optional_int,
    optional_string,
    require_go_id,
    require_non_empty_string,
    source_info,
)


def quickgo_status(args: JsonObject, client: QuickGoClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "quickgo",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "website_base_url": client.config.website_base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["gene_ontology", "gene_ontology_annotation"],
        "tool_groups": {
            "ontology": ["quickgo_term_lookup", "quickgo_term_search", "quickgo_term_children"],
            "annotations": ["quickgo_annotation_search"],
            "status": ["quickgo_status"],
        },
        "frontend_components": ["ontology_term", "dataset"],
        "preview_kinds": ["table", "network", "xref_groups"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload, headers = client.request_json_with_headers("ontology/go/terms/GO:0008150", {})
        rows = results(payload)
        status["network_check"] = {
            "ok": True,
            "returned": len(rows),
            "example_go_id": rows[0].get("id") if rows else None,
            "example_name": rows[0].get("name") if rows else None,
            "content_type": headers.get("content-type"),
        }
    return status


def quickgo_term_lookup(args: JsonObject, client: QuickGoClient) -> JsonObject:
    go_id = require_go_id(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"ontology/go/terms/{go_id}"
    payload, headers = client.request_json_with_headers(endpoint, {})
    term = first_result(payload)
    record = quickgo_term_record(
        term,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "quickgo",
        "query": go_id,
        "returned": 1,
        "term": term_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def quickgo_term_search(args: JsonObject, client: QuickGoClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    max_results = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    params: JsonObject = {"query": query, "limit": max_results, "page": 1}
    endpoint = "ontology/go/search"
    payload, headers = client.request_json_with_headers(endpoint, params)
    rows = results(payload)[:max_results]
    records = [
        quickgo_term_record(row, website_base_url=client.config.website_base_url, api_base_url=client.config.base_url)
        for row in rows
    ]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "quickgo",
        "query": query,
        "returned": len(records),
        "total": total_hits(payload),
        "terms": [term_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def quickgo_term_children(args: JsonObject, client: QuickGoClient) -> JsonObject:
    go_id = require_go_id(args)
    max_children = optional_int(args, "max_children", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RELATIONS)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"ontology/go/terms/{go_id}/children"
    payload, headers = client.request_json_with_headers(endpoint, {})
    parent = first_result(payload)
    child_rows = parent.get("children") if isinstance(parent.get("children"), list) else []
    records = [
        quickgo_term_record(
            row,
            relation=str(row.get("relation") or ""),
            parent_id=go_id,
            website_base_url=client.config.website_base_url,
            api_base_url=client.config.base_url,
        )
        for row in child_rows[:max_children]
        if isinstance(row, dict)
    ]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "quickgo",
        "query": go_id,
        "returned": len(records),
        "total": len(child_rows),
        "parent": {"id": parent.get("id"), "name": parent.get("name")},
        "terms": [term_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def quickgo_annotation_search(args: JsonObject, client: QuickGoClient) -> JsonObject:
    gene_product_id = optional_string(args, "gene_product_id")
    go_id = optional_go_id(args, "go_id")
    taxon_id = optional_string(args, "taxon_id")
    evidence_code = optional_string(args, "evidence_code")
    max_results = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    if not any([gene_product_id, go_id, taxon_id, evidence_code]):
        raise McpError(-32602, "Provide at least one of gene_product_id, go_id, taxon_id, or evidence_code")
    params: JsonObject = {"limit": max_results, "page": 1}
    if gene_product_id:
        params["geneProductId"] = gene_product_id
    if go_id:
        params["goId"] = go_id
    if taxon_id:
        params["taxonId"] = taxon_id
    if evidence_code:
        params["evidenceCode"] = evidence_code
    endpoint = "annotation/search"
    payload, headers = client.request_json_with_headers(endpoint, params)
    rows = results(payload)[:max_results]
    record = quickgo_annotation_dataset_record(
        rows,
        query=params,
        total=total_hits(payload),
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "quickgo",
        "query": record["label"],
        "returned": len(rows),
        "total": total_hits(payload),
        "annotations": record["data"]["annotations"],
        "records": [record],
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def results(payload: object) -> list[JsonObject]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get("results")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def first_result(payload: object) -> JsonObject:
    rows = results(payload)
    if not rows:
        raise QuickGoError("QuickGO response did not contain a result")
    return rows[0]


def total_hits(payload: object) -> int:
    if not isinstance(payload, dict):
        return 0
    value = payload.get("numberOfHits")
    try:
        return int(value)
    except (TypeError, ValueError):
        return len(results(payload))


def term_summary(record: JsonObject) -> JsonObject:
    data = record["data"]
    return {
        "id": data["id"],
        "name": data["name"],
        "aspect": data["aspect_label"],
        "url": data["url"],
    }


def source_with_headers(endpoint: str, params: JsonObject, headers: dict[str, str]) -> JsonObject:
    source = source_info(endpoint, params)
    if headers.get("content-type"):
        source["content_type"] = headers["content-type"]
    return source


def tool_definitions() -> list[JsonObject]:
    return [
        {
            "name": "quickgo_term_lookup",
            "title": "Look up a Gene Ontology term in QuickGO",
            "description": "Fetch one GO term by GO ID and return an ontology-term record with definition, synonyms, relations, xrefs, previews, and links.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "go_id": {"type": "string", "description": "GO ID, for example GO:0006915."},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["go_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "quickgo_term_search",
            "title": "Search Gene Ontology terms in QuickGO",
            "description": "Search GO terms by text and return front-end-compatible ontology-term records.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Term search text, for example apoptosis."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "quickgo_annotation_search",
            "title": "Search QuickGO annotation evidence",
            "description": "Search GO annotation rows by gene product, GO ID, taxon, or evidence code and return a dataset record with a bounded evidence table.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "gene_product_id": {"type": "string", "description": "Gene product ID, for example UniProtKB:P04637."},
                    "go_id": {"type": "string", "description": "Optional GO ID filter, for example GO:0008285."},
                    "taxon_id": {"type": ["integer", "string"], "description": "Optional NCBI TaxID filter, for example 9606."},
                    "evidence_code": {"type": "string", "description": "Optional ECO code filter, for example ECO:0000315."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "quickgo_term_children",
            "title": "List child GO terms in QuickGO",
            "description": "Fetch child terms for one GO ID and return bounded ontology-term records with relation metadata and links.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "go_id": {"type": "string", "description": "Parent GO ID, for example GO:0006915."},
                    "max_children": {"type": "integer", "minimum": 1, "maximum": MAX_RELATIONS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["go_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "quickgo_status",
            "title": "Inspect QuickGO MCP status",
            "description": "Return configured QuickGO MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
    ]


TOOL_HANDLERS = {
    "quickgo_term_lookup": quickgo_term_lookup,
    "quickgo_term_search": quickgo_term_search,
    "quickgo_annotation_search": quickgo_annotation_search,
    "quickgo_term_children": quickgo_term_children,
    "quickgo_status": quickgo_status,
}

