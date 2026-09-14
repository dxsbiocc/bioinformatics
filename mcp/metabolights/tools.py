"""MCP tool registry for the MetaboLights server."""

from __future__ import annotations

from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition

from .client import MetaboLightsClient
from .constants import DEFAULT_FILES, DEFAULT_RESULTS, MAX_FILES, MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import MetaboLightsError
from .records import metabolights_file_manifest_record, metabolights_project_record, metabolights_search_record
from .utils import optional_bool, optional_int, require_accession, require_non_empty_string, source_info


def metabolights_status(args: JsonObject, client: MetaboLightsClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "metabolights",
        "version": "0.1.0",
        "ws_base_url": client.config.ws_base_url,
        "search_base_url": client.config.search_base_url,
        "website_base_url": client.config.website_base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["metabolights", "ebi_search"],
        "tool_groups": {
            "studies": ["metabolights_study_lookup", "metabolights_search"],
            "files": ["metabolights_file_manifest"],
            "status": ["metabolights_status"],
        },
        "frontend_components": ["project", "download_plan"],
        "preview_kinds": ["table", "citation_list", "download_manifest", "xref_groups"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload, headers = client.request_ws_json_with_headers("studies/MTBLS1", {})
        status["network_check"] = {
            "ok": True,
            "example_accession": example_accession(payload),
            "content_type": headers.get("content-type"),
        }
    return status


def metabolights_study_lookup(args: JsonObject, client: MetaboLightsClient) -> JsonObject:
    accession = require_accession(args)
    include_files = optional_bool(args, "include_files", default=True)
    max_files = optional_int(args, "max_files", default=DEFAULT_FILES, minimum=1, maximum=MAX_FILES)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"studies/{accession}"
    payload, headers = client.request_ws_json_with_headers(endpoint, {})
    study = ensure_study(payload, accession)
    files_payload: JsonObject = {}
    file_source: JsonObject | None = None
    if include_files:
        files_endpoint = f"studies/{accession}/files"
        files_payload_obj, file_headers = client.request_ws_json_with_headers(files_endpoint, {"include_raw_data": "false"})
        files_payload = files_payload_obj if isinstance(files_payload_obj, dict) else {}
        file_source = source_with_headers(files_endpoint, {"include_raw_data": "false"}, file_headers, client.build_ws_url(files_endpoint, {"include_raw_data": "false"}))
    record = metabolights_project_record(study, files_payload=files_payload, website_base_url=client.config.website_base_url, ws_base_url=client.config.ws_base_url)
    if include_files and record["data"]["files"]:
        record["data"]["files"] = record["data"]["files"][:max_files]
        record["related"]["files"] = record["data"]["files"]
        trim_file_sections(record, max_files)
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "metabolights",
        "query": accession,
        "returned": 1,
        "study": study_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, {}, headers, client.build_ws_url(endpoint, {})),
    }
    if file_source is not None:
        response["file_source"] = file_source
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
        if files_payload:
            response["raw_files"] = files_payload
    return response


def metabolights_search(args: JsonObject, client: MetaboLightsClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    max_results = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = "metabolights"
    params: JsonObject = {
        "query": query,
        "format": "json",
        "size": max_results,
        "fields": "name,description,organism,study_design",
    }
    payload, headers = client.request_search_json_with_headers(endpoint, params)
    entries = search_entries(payload)[:max_results]
    records = [metabolights_search_record(entry, website_base_url=client.config.website_base_url, search_base_url=client.config.search_base_url) for entry in entries]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "metabolights",
        "query": query,
        "returned": len(records),
        "total": payload.get("hitCount") if isinstance(payload, dict) else None,
        "studies": [study_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, params, headers, client.build_search_url(endpoint, params)),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def metabolights_file_manifest(args: JsonObject, client: MetaboLightsClient) -> JsonObject:
    accession = require_accession(args)
    max_files = optional_int(args, "max_files", default=DEFAULT_FILES, minimum=1, maximum=MAX_FILES)
    include_raw = optional_bool(args, "include_raw", default=False)
    include_study = optional_bool(args, "include_study", default=True)
    files_endpoint = f"studies/{accession}/files"
    files_params: JsonObject = {"include_raw_data": "false"}
    files_payload_obj, headers = client.request_ws_json_with_headers(files_endpoint, files_params)
    files_payload = files_payload_obj if isinstance(files_payload_obj, dict) else {}
    study_payload: JsonObject | None = None
    study_source: JsonObject | None = None
    if include_study:
        study_endpoint = f"studies/{accession}"
        study_payload_obj, study_headers = client.request_ws_json_with_headers(study_endpoint, {})
        study_payload = study_payload_obj if isinstance(study_payload_obj, dict) else None
        study_source = source_with_headers(study_endpoint, {}, study_headers, client.build_ws_url(study_endpoint, {}))
    record = metabolights_file_manifest_record(
        accession,
        files_payload,
        study_payload=study_payload,
        max_files=max_files,
        website_base_url=client.config.website_base_url,
        ws_base_url=client.config.ws_base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "metabolights",
        "query": accession,
        "returned": len(record["data"]["files"]),
        "records": [record],
        "source": source_with_headers(files_endpoint, files_params, headers, client.build_ws_url(files_endpoint, files_params)),
    }
    if study_source is not None:
        response["study_source"] = study_source
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = files_payload
        if study_payload is not None:
            response["raw_study"] = study_payload
    return response


def ensure_study(payload: object, accession: str) -> JsonObject:
    if isinstance(payload, dict) and isinstance(payload.get("isaInvestigation"), dict):
        return payload
    raise MetaboLightsError(f"MetaboLights study not found for {accession}")


def search_entries(payload: object) -> list[JsonObject]:
    if not isinstance(payload, dict):
        return []
    return [item for item in payload.get("entries", []) if isinstance(item, dict)]


def example_accession(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    investigation = payload.get("isaInvestigation") if isinstance(payload.get("isaInvestigation"), dict) else {}
    return str(investigation.get("identifier") or "")


def study_summary(record: JsonObject) -> JsonObject:
    data = record["data"]
    return {
        "accession": data["accession"],
        "title": data["title"],
        "status": data["status"],
        "url": data["url"],
    }


def source_with_headers(endpoint: str, params: JsonObject, headers: dict[str, str], url: str) -> JsonObject:
    source = source_info(endpoint, params)
    source["url"] = url
    if headers.get("content-type"):
        source["content_type"] = headers["content-type"]
    return source


def trim_file_sections(record: JsonObject, max_files: int) -> None:
    files = record["data"]["files"][:max_files]
    for section in record["display"].get("sections", []):
        if section.get("key") == "files":
            section["rows"] = files
    for preview in record["display"].get("previews", []):
        if preview.get("section_key") == "files" and isinstance(preview.get("data"), dict):
            preview["data"]["rows"] = files


def tool_definitions() -> list[JsonObject]:
    return [
        parameter_domains_tool_definition("metabolights_parameter_domains"),
        {
            "name": "metabolights_study_lookup",
            "title": "Look up a MetaboLights study",
            "description": "Fetch one MetaboLights study by MTBLS accession and return a front-end-compatible project record with study design, assay, protocol, publication, and optional file-manifest previews.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "accession": {"type": "string", "description": "MetaboLights accession, for example MTBLS1."},
                    "include_files": {"type": "boolean", "default": True},
                    "max_files": {"type": "integer", "minimum": 1, "maximum": MAX_FILES, "default": DEFAULT_FILES},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["accession"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "metabolights_search",
            "title": "Search MetaboLights studies",
            "description": "Search MetaboLights through EBI Search and return bounded front-end-compatible project records.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text query such as disease, organism, assay, or metabolomics topic."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "metabolights_file_manifest",
            "title": "Fetch a MetaboLights file manifest",
            "description": "Fetch a bounded metadata-only MetaboLights file manifest. It returns safe links and does not download data.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "accession": {"type": "string", "description": "MetaboLights accession, for example MTBLS1."},
                    "max_files": {"type": "integer", "minimum": 1, "maximum": MAX_FILES, "default": DEFAULT_FILES},
                    "include_study": {"type": "boolean", "default": True},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["accession"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "metabolights_status",
            "title": "Inspect MetaboLights MCP status",
            "description": "Return configured MetaboLights MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
    ]


TOOL_HANDLERS = {
    "metabolights_parameter_domains": make_parameter_domains_handler("metabolights", "metabolights_parameter_domains", tool_definitions),
    "metabolights_study_lookup": metabolights_study_lookup,
    "metabolights_search": metabolights_search,
    "metabolights_file_manifest": metabolights_file_manifest,
    "metabolights_status": metabolights_status,
}

