"""MCP tool registry for the Human Protein Atlas server."""

from __future__ import annotations

import urllib.parse

from .client import HpaClient
from .constants import DEFAULT_RESULTS, MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import HpaError
from .records import hpa_gene_record
from .utils import optional_bool, optional_int, require_ensembl_id, require_non_empty_string, source_info


def hpa_status(args: JsonObject, client: HpaClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "hpa",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["human_protein_atlas"],
        "tool_groups": {
            "genes": ["hpa_gene_lookup", "hpa_search"],
            "status": ["hpa_status"],
        },
        "frontend_components": ["gene"],
        "preview_kinds": ["table", "xref_groups"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload, headers = client.request_json_with_headers("ENSG00000141510.json", {})
        status["network_check"] = {
            "ok": True,
            "example_gene": payload.get("Gene") if isinstance(payload, dict) else None,
            "example_ensembl": payload.get("Ensembl") if isinstance(payload, dict) else None,
            "content_type": headers.get("content-type"),
        }
    return status


def hpa_gene_lookup(args: JsonObject, client: HpaClient) -> JsonObject:
    ensembl_id = require_ensembl_id(args, "ensembl_id")
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"{ensembl_id}.json"
    payload, headers = client.request_json_with_headers(endpoint, {})
    gene = ensure_gene(payload, ensembl_id)
    record = hpa_gene_record(gene, base_url=client.config.base_url)
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "hpa",
        "query": ensembl_id,
        "returned": 1,
        "gene": gene_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, {}, headers, client.config.base_url),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def hpa_search(args: JsonObject, client: HpaClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    max_results = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = "api/search_download.php"
    params: JsonObject = {
        "search": query,
        "format": "json",
        "columns": "g,gs,eg,gd,up,pe",
        "compress": "no",
    }
    payload, headers = client.request_json_with_headers(endpoint, params)
    rows = result_rows(payload)[:max_results]
    records = [hpa_gene_record(row, base_url=client.config.base_url) for row in rows]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "hpa",
        "query": query,
        "returned": len(records),
        "genes": [gene_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, params, headers, client.config.base_url),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def ensure_gene(payload: object, ensembl_id: str) -> JsonObject:
    if isinstance(payload, dict) and (payload.get("Ensembl") or payload.get("Gene")):
        return payload
    raise HpaError(f"Human Protein Atlas gene not found for {ensembl_id}")


def result_rows(payload: object) -> list[JsonObject]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def gene_summary(record: JsonObject) -> JsonObject:
    data = record["data"]
    return {
        "gene": data["gene"],
        "ensembl": data["ensembl"],
        "description": data["description"],
        "url": data["url"],
    }


def source_with_headers(endpoint: str, params: JsonObject, headers: dict[str, str], base_url: str) -> JsonObject:
    source = source_info(endpoint, params)
    source["url"] = source_url(endpoint, params, base_url)
    if headers.get("content-type"):
        source["content_type"] = headers["content-type"]
    return source


def source_url(endpoint: str, params: JsonObject, base_url: str) -> str:
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    if not params:
        return url
    return f"{url}?{urllib.parse.urlencode(params, doseq=True)}"


def tool_definitions() -> list[JsonObject]:
    return [
        {
            "name": "hpa_gene_lookup",
            "title": "Look up a Human Protein Atlas gene",
            "description": "Fetch one Human Protein Atlas gene JSON record by Ensembl gene ID and return a front-end-compatible gene record with expression, subcellular, antibody, and cancer prognostic summaries.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ensembl_id": {"type": "string", "description": "Ensembl gene ID, for example ENSG00000141510."},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["ensembl_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "hpa_search",
            "title": "Search Human Protein Atlas genes",
            "description": "Search Human Protein Atlas gene metadata and return bounded front-end-compatible gene records.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Gene symbol, synonym, Ensembl ID, or free-text query."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "hpa_status",
            "title": "Inspect Human Protein Atlas MCP status",
            "description": "Return configured Human Protein Atlas MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
    ]


TOOL_HANDLERS = {
    "hpa_gene_lookup": hpa_gene_lookup,
    "hpa_search": hpa_search,
    "hpa_status": hpa_status,
}
