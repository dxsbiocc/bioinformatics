"""MCP tool registry for the BioStudies server."""

from __future__ import annotations

from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition

from .client import BioStudiesClient
from .constants import DEFAULT_FILES, DEFAULT_RESULTS, MAX_FILES, MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import BioStudiesError
from .records import biostudies_file_manifest_record, biostudies_study_record
from .utils import optional_bool, optional_int, require_accession, require_non_empty_string, source_info


def biostudies_status(args: JsonObject, client: BioStudiesClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "biostudies",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "website_base_url": client.config.website_base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["biostudies", "arrayexpress"],
        "tool_groups": {
            "studies": ["biostudies_study_lookup", "biostudies_search", "arrayexpress_search"],
            "files": ["biostudies_file_manifest"],
            "status": ["biostudies_status"],
        },
        "frontend_components": ["project", "download_plan"],
        "preview_kinds": ["table", "citation_list", "xref_groups", "download_manifest"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload, headers = client.request_json_with_headers("studies/E-MTAB-6701/info", {})
        status["network_check"] = {
            "ok": True,
            "example_accession": "E-MTAB-6701",
            "files": payload.get("files") if isinstance(payload, dict) else None,
            "content_type": headers.get("content-type"),
        }
    return status


def biostudies_study_lookup(args: JsonObject, client: BioStudiesClient) -> JsonObject:
    accession = require_accession(args)
    include_files = optional_bool(args, "include_files", default=False)
    max_files = optional_int(args, "max_files", default=DEFAULT_FILES, minimum=1, maximum=MAX_FILES)
    include_raw = optional_bool(args, "include_raw", default=False)
    repository = "arrayexpress" if accession.startswith("E-") else "biostudies"

    study_endpoint = f"studies/{accession}"
    study_payload, headers = client.request_json_with_headers(study_endpoint, {})
    study = ensure_study(study_payload, accession)
    info_payload, _info_headers = client.request_json_with_headers(f"studies/{accession}/info", {})
    files_payload = None
    file_rows: list[JsonObject] = []
    if include_files:
        files_payload, _file_headers = client.request_json_with_headers(f"studies/{accession}/files", {"limit": max_files})
        file_rows = file_list(files_payload)[:max_files]

    record = biostudies_study_record(
        study,
        info=info_payload if isinstance(info_payload, dict) else {},
        files=file_rows,
        repository=repository,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "biostudies",
        "query": accession,
        "returned": 1,
        "study": study_summary(record),
        "records": [record],
        "source": source_with_headers(study_endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = {"study": study_payload, "info": info_payload, "files": files_payload}
    return response


def biostudies_search(args: JsonObject, client: BioStudiesClient) -> JsonObject:
    return search(args, client, endpoint="search", repository="biostudies")


def arrayexpress_search(args: JsonObject, client: BioStudiesClient) -> JsonObject:
    return search(args, client, endpoint="ArrayExpress/search", repository="arrayexpress")


def search(args: JsonObject, client: BioStudiesClient, *, endpoint: str, repository: str) -> JsonObject:
    query = require_non_empty_string(args, "query")
    max_results = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    params: JsonObject = {"query": query, "page": 1, "pageSize": max_results}
    payload, headers = client.request_json_with_headers(endpoint, params)
    rows = result_hits(payload)[:max_results]
    records = [
        biostudies_study_record(row, repository=repository, website_base_url=client.config.website_base_url, api_base_url=client.config.base_url)
        for row in rows
    ]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "biostudies",
        "repository": repository,
        "query": query,
        "returned": len(records),
        "total_hits": payload.get("totalHits") if isinstance(payload, dict) else None,
        "studies": [study_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def biostudies_file_manifest(args: JsonObject, client: BioStudiesClient) -> JsonObject:
    accession = require_accession(args)
    max_files = optional_int(args, "max_files", default=DEFAULT_FILES, minimum=1, maximum=MAX_FILES)
    include_raw = optional_bool(args, "include_raw", default=False)
    repository = "arrayexpress" if accession.startswith("E-") else "biostudies"
    info_endpoint = f"studies/{accession}/info"
    info_payload, headers = client.request_json_with_headers(info_endpoint, {})
    files_endpoint = f"studies/{accession}/files"
    params: JsonObject = {"limit": max_files}
    files_payload, _file_headers = client.request_json_with_headers(files_endpoint, params)
    rows = file_list(files_payload)[:max_files]
    record = biostudies_file_manifest_record(
        accession,
        info_payload if isinstance(info_payload, dict) else {},
        rows,
        repository=repository,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "biostudies",
        "repository": repository,
        "query": accession,
        "returned": len(rows),
        "files": record["data"]["files"],
        "records": [record],
        "source": source_with_headers(info_endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = {"info": info_payload, "files": files_payload}
    return response


def ensure_study(payload: object, accession: str) -> JsonObject:
    if isinstance(payload, dict) and (payload.get("accno") or payload.get("accession")):
        return payload
    raise BioStudiesError(f"BioStudies study not found for {accession}")


def result_hits(payload: object) -> list[JsonObject]:
    if isinstance(payload, dict) and isinstance(payload.get("hits"), list):
        return [item for item in payload["hits"] if isinstance(item, dict)]
    return []


def file_list(payload: object) -> list[JsonObject]:
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [item for item in payload["items"] if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def study_summary(record: JsonObject) -> JsonObject:
    data = record["data"]
    return {
        "accession": data["accession"],
        "title": data["title"],
        "repository": data["repository"],
        "url": data["url"],
    }


def source_with_headers(endpoint: str, params: JsonObject, headers: dict[str, str]) -> JsonObject:
    source = source_info(endpoint, params)
    if headers.get("content-type"):
        source["content_type"] = headers["content-type"]
    return source


def tool_definitions() -> list[JsonObject]:
    return [
        parameter_domains_tool_definition("biostudies_parameter_domains"),
        {
            "name": "biostudies_study_lookup",
            "title": "Look up a BioStudies or ArrayExpress study",
            "description": "Fetch one BioStudies study by accession and return a front-end-compatible project record with study metadata, protocols, references, links, and optional file previews.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "accession": {"type": "string", "description": "BioStudies or ArrayExpress accession, for example E-MTAB-6701."},
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
            "name": "biostudies_search",
            "title": "Search BioStudies",
            "description": "Search BioStudies studies with a keyword and return bounded front-end-compatible project records.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword, title, organism, assay, or dataset query text."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "arrayexpress_search",
            "title": "Search ArrayExpress",
            "description": "Search the ArrayExpress view of BioStudies and return bounded front-end-compatible project records.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "ArrayExpress query text, for example single cell RNA-seq."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "biostudies_file_manifest",
            "title": "Build a BioStudies file manifest",
            "description": "Fetch bounded BioStudies file metadata and return a metadata-only download-plan record. No file transfer is started.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "accession": {"type": "string", "description": "BioStudies or ArrayExpress accession, for example E-MTAB-6701."},
                    "max_files": {"type": "integer", "minimum": 1, "maximum": MAX_FILES, "default": DEFAULT_FILES},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["accession"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "biostudies_status",
            "title": "Inspect BioStudies MCP status",
            "description": "Return configured BioStudies MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
    ]


TOOL_HANDLERS = {
    "biostudies_parameter_domains": make_parameter_domains_handler("biostudies", "biostudies_parameter_domains", tool_definitions),
    "biostudies_study_lookup": biostudies_study_lookup,
    "biostudies_search": biostudies_search,
    "arrayexpress_search": arrayexpress_search,
    "biostudies_file_manifest": biostudies_file_manifest,
    "biostudies_status": biostudies_status,
}

