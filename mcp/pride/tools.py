"""MCP tool registry for the PRIDE Archive server."""

from __future__ import annotations

from .client import PrideClient
from .constants import DEFAULT_FILES, DEFAULT_RESULTS, MAX_FILES, MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import PrideError
from .records import pride_files_download_plan_record, pride_project_record
from .utils import optional_bool, optional_int, optional_string, require_accession, require_non_empty_string, source_info


def pride_status(args: JsonObject, client: PrideClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "pride",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "website_base_url": client.config.website_base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["pride_archive", "proteomexchange"],
        "tool_groups": {
            "projects": ["pride_project_lookup", "pride_project_search"],
            "files": ["pride_project_files"],
            "status": ["pride_status"],
        },
        "frontend_components": ["project", "download_plan"],
        "preview_kinds": ["table", "citation_list", "xref_groups", "download_manifest"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload, headers = client.request_json_with_headers("projects/PXD001357", {})
        status["network_check"] = {
            "ok": True,
            "example_accession": payload.get("accession") if isinstance(payload, dict) else None,
            "example_title": payload.get("title") if isinstance(payload, dict) else None,
            "content_type": headers.get("content-type"),
        }
    return status


def pride_project_lookup(args: JsonObject, client: PrideClient) -> JsonObject:
    accession = require_accession(args)
    include_files = optional_bool(args, "include_files", default=False)
    max_files = optional_int(args, "max_files", default=DEFAULT_FILES, minimum=1, maximum=MAX_FILES)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"projects/{accession}"
    payload, headers = client.request_json_with_headers(endpoint, {})
    project = ensure_project(payload, accession)
    file_rows: list[JsonObject] = []
    file_payload = None
    if include_files:
        file_payload, _file_headers = client.request_json_with_headers(f"projects/{accession}/files", {"pageSize": max_files})
        file_rows = result_list(file_payload)[:max_files]
    record = pride_project_record(
        project,
        files=file_rows,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "pride",
        "query": accession,
        "returned": 1,
        "project": project_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = {"project": payload, "files": file_payload}
    return response


def pride_project_search(args: JsonObject, client: PrideClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    max_results = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    params: JsonObject = {"keyword": query, "pageSize": max_results}
    endpoint = "projects"
    payload, headers = client.request_json_with_headers(endpoint, params)
    rows = result_list(payload)[:max_results]
    records = [
        pride_project_record(row, website_base_url=client.config.website_base_url, api_base_url=client.config.base_url)
        for row in rows
    ]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "pride",
        "query": query,
        "returned": len(records),
        "projects": [project_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def pride_project_files(args: JsonObject, client: PrideClient) -> JsonObject:
    accession = require_accession(args)
    max_files = optional_int(args, "max_files", default=DEFAULT_FILES, minimum=1, maximum=MAX_FILES)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"projects/{accession}/files"
    params: JsonObject = {"pageSize": max_files}
    payload, headers = client.request_json_with_headers(endpoint, params)
    rows = result_list(payload)[:max_files]
    record = pride_files_download_plan_record(
        accession,
        rows,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "pride",
        "query": accession,
        "returned": len(rows),
        "files": record["data"]["files"],
        "records": [record],
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def ensure_project(payload: object, accession: str) -> JsonObject:
    if isinstance(payload, dict) and payload.get("accession"):
        return payload
    raise PrideError(f"PRIDE project not found for {accession}")


def result_list(payload: object) -> list[JsonObject]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("content", "projects", "files", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def project_summary(record: JsonObject) -> JsonObject:
    data = record["data"]
    return {
        "accession": data["accession"],
        "title": data["title"],
        "doi": data["doi"],
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
            "name": "pride_project_lookup",
            "title": "Look up a PRIDE Archive project",
            "description": "Fetch one PRIDE Archive project by PXD accession and return a front-end-compatible project record with project metadata, references, protocol summaries, and links.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "accession": {"type": "string", "description": "PRIDE/ProteomeXchange accession, for example PXD001357."},
                    "include_files": {"type": "boolean", "default": False},
                    "max_files": {"type": "integer", "minimum": 1, "maximum": MAX_FILES, "default": DEFAULT_FILES},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["accession"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "pride_project_search",
            "title": "Search PRIDE Archive projects",
            "description": "Search PRIDE Archive projects with a keyword and return bounded front-end-compatible project records.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword, title, organism, tag, or proteomics query text."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "pride_project_files",
            "title": "Build a PRIDE project file manifest",
            "description": "Fetch bounded PRIDE project file metadata and return a metadata-only download-plan record. No file transfer is started.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "accession": {"type": "string", "description": "PRIDE/ProteomeXchange accession, for example PXD001357."},
                    "max_files": {"type": "integer", "minimum": 1, "maximum": MAX_FILES, "default": DEFAULT_FILES},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["accession"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "pride_status",
            "title": "Inspect PRIDE MCP status",
            "description": "Return configured PRIDE MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
    ]


TOOL_HANDLERS = {
    "pride_project_lookup": pride_project_lookup,
    "pride_project_search": pride_project_search,
    "pride_project_files": pride_project_files,
    "pride_status": pride_status,
}

