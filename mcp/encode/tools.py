"""MCP tool registry for the ENCODE server."""

from __future__ import annotations

from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition
from .client import EncodeClient
from .constants import DEFAULT_FILES, DEFAULT_RESULTS, MAX_FILES, MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import EncodeError
from .records import encode_biosample_record, encode_experiment_record, encode_file_manifest_record, encode_file_record
from .utils import (
    optional_bool,
    optional_int,
    optional_string,
    require_biosample_accession,
    require_experiment_accession,
    require_file_accession,
    require_non_empty_string,
    source_info,
)


def encode_status(args: JsonObject, client: EncodeClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "encode",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["encode"],
        "tool_groups": {
            "experiments": ["encode_experiment_lookup", "encode_experiment_search"],
            "biosamples": ["encode_biosample_lookup", "encode_biosample_search"],
            "files": ["encode_file_lookup", "encode_file_manifest"],
            "status": ["encode_status"],
        },
        "frontend_components": ["project", "sample", "download_plan"],
        "preview_kinds": ["table", "xref_groups", "download_manifest"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload, headers = client.request_json_with_headers("search/", {"type": "Experiment", "searchTerm": "ATAC-seq", "limit": 1})
        rows = search_hits(payload)
        status["network_check"] = {
            "ok": True,
            "example_accession": rows[0].get("accession") if rows else None,
            "content_type": headers.get("content-type"),
        }
    return status


def encode_experiment_lookup(args: JsonObject, client: EncodeClient) -> JsonObject:
    accession = require_experiment_accession(args)
    max_files = optional_int(args, "max_files", default=DEFAULT_FILES, minimum=1, maximum=MAX_FILES)
    include_files = optional_bool(args, "include_files", default=True)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"experiments/{accession}/"
    params: JsonObject = {"frame": "embedded"}
    payload, headers = client.request_json_with_headers(endpoint, params)
    experiment = ensure_object(payload, accession)
    files = file_rows(experiment)[:max_files] if include_files else []
    record = encode_experiment_record(experiment, files=files, base_url=client.config.base_url)
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "encode",
        "query": accession,
        "returned": 1,
        "experiment": experiment_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, params, headers, client.build_url(endpoint, params)),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def encode_experiment_search(args: JsonObject, client: EncodeClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    max_results = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = "search/"
    params: JsonObject = {"type": "Experiment", "searchTerm": query, "limit": max_results}
    for arg_name, param_name in [
        ("assay_title", "assay_title"),
        ("biosample_term_name", "biosample_ontology.term_name"),
        ("status", "status"),
    ]:
        value = optional_string(args, arg_name)
        if value:
            params[param_name] = value
    payload, headers = client.request_json_with_headers(endpoint, params)
    rows = search_hits(payload)[:max_results]
    records = [encode_experiment_record(row, files=[], base_url=client.config.base_url) for row in rows]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "encode",
        "query": query,
        "returned": len(records),
        "total": total_count(payload),
        "experiments": [experiment_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, params, headers, client.build_url(endpoint, params)),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def encode_biosample_lookup(args: JsonObject, client: EncodeClient) -> JsonObject:
    accession = require_biosample_accession(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"biosamples/{accession}/"
    params: JsonObject = {"frame": "object"}
    payload, headers = client.request_json_with_headers(endpoint, params)
    biosample = ensure_object(payload, accession)
    record = encode_biosample_record(biosample, base_url=client.config.base_url)
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "encode",
        "query": accession,
        "returned": 1,
        "biosample": biosample_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, params, headers, client.build_url(endpoint, params)),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def encode_biosample_search(args: JsonObject, client: EncodeClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    max_results = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = "search/"
    params: JsonObject = {"type": "Biosample", "searchTerm": query, "limit": max_results, "frame": "object"}
    for arg_name, param_name in [
        ("biosample_term_name", "biosample_ontology.term_name"),
        ("organism", "organism.scientific_name"),
        ("status", "status"),
        ("life_stage", "life_stage"),
    ]:
        value = optional_string(args, arg_name)
        if value:
            params[param_name] = value
    payload, headers = client.request_json_with_headers(endpoint, params)
    rows = search_hits(payload)[:max_results]
    records = [encode_biosample_record(row, base_url=client.config.base_url) for row in rows]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "encode",
        "query": query,
        "returned": len(records),
        "total": total_count(payload),
        "biosamples": [biosample_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, params, headers, client.build_url(endpoint, params)),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def encode_file_lookup(args: JsonObject, client: EncodeClient) -> JsonObject:
    accession = require_file_accession(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"files/{accession}/"
    params: JsonObject = {"frame": "object"}
    payload, headers = client.request_json_with_headers(endpoint, params)
    file_item = ensure_object(payload, accession)
    record = encode_file_record(file_item, base_url=client.config.base_url)
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "encode",
        "query": accession,
        "returned": 1,
        "file": file_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, params, headers, client.build_url(endpoint, params)),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def encode_file_manifest(args: JsonObject, client: EncodeClient) -> JsonObject:
    accession = require_experiment_accession(args, "experiment_accession")
    max_files = optional_int(args, "max_files", default=DEFAULT_FILES, minimum=1, maximum=MAX_FILES)
    file_format = optional_string(args, "file_format").lower()
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"experiments/{accession}/"
    params: JsonObject = {"frame": "embedded"}
    payload, headers = client.request_json_with_headers(endpoint, params)
    experiment = ensure_object(payload, accession)
    rows = file_rows(experiment)
    if file_format:
        rows = [row for row in rows if str(row.get("file_format") or row.get("file_type") or "").lower() == file_format]
    rows = rows[:max_files]
    record = encode_file_manifest_record(accession, rows, base_url=client.config.base_url)
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "encode",
        "query": accession,
        "returned": len(rows),
        "files": record["data"]["files"],
        "records": [record],
        "source": source_with_headers(endpoint, params, headers, client.build_url(endpoint, params)),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def ensure_object(payload: object, identifier: str) -> JsonObject:
    if isinstance(payload, dict) and payload.get("accession"):
        return payload
    raise EncodeError(f"ENCODE record not found for {identifier}")


def search_hits(payload: object) -> list[JsonObject]:
    if isinstance(payload, dict) and isinstance(payload.get("@graph"), list):
        return [item for item in payload["@graph"] if isinstance(item, dict)]
    return []


def file_rows(experiment: JsonObject) -> list[JsonObject]:
    return [item for item in experiment.get("files", []) if isinstance(item, dict)]


def total_count(payload: object) -> int | None:
    if not isinstance(payload, dict):
        return None
    total = payload.get("total")
    try:
        return int(total) if total is not None else None
    except (TypeError, ValueError):
        return None


def experiment_summary(record: JsonObject) -> JsonObject:
    data = record["data"]
    return {"accession": data["accession"], "title": record["title"], "assay": data["assay_title"], "url": data["url"]}


def biosample_summary(record: JsonObject) -> JsonObject:
    data = record["data"]
    return {
        "accession": data["accession"],
        "title": record["title"],
        "biosample": data["biosample_term_name"],
        "organism": data["organism"],
        "url": data["url"],
    }


def file_summary(record: JsonObject) -> JsonObject:
    files = record["data"]["files"]
    first = files[0] if files else {}
    return {"accession": first.get("accession"), "file_format": first.get("file_format"), "download_url": first.get("download_url"), "url": first.get("url")}


def source_with_headers(endpoint: str, params: JsonObject, headers: dict[str, str], url: str) -> JsonObject:
    source = source_info(endpoint, params)
    source["url"] = url
    if headers.get("content-type"):
        source["content_type"] = headers["content-type"]
    return source


def tool_definitions() -> list[JsonObject]:
    return [
        parameter_domains_tool_definition("encode_parameter_domains"),
        {
            "name": "encode_experiment_lookup",
            "title": "Look up an ENCODE experiment",
            "description": "Fetch one ENCODE experiment by ENCSR accession and return a front-end-compatible project record with assay, biosample, external IDs, and optional file previews.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "accession": {"type": "string", "description": "ENCODE experiment accession, for example ENCSR844TIU."},
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
            "name": "encode_experiment_search",
            "title": "Search ENCODE experiments",
            "description": "Search ENCODE experiments with a text query and optional assay, biosample term, or status filters.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text query such as K562 RNA-seq, ATAC-seq, CTCF, liver, or GRCh38."},
                    "assay_title": {"type": "string", "description": "Optional exact ENCODE assay title, for example ATAC-seq or total RNA-seq."},
                    "biosample_term_name": {"type": "string", "description": "Optional biosample term name, for example K562 or A549."},
                    "status": {"type": "string", "description": "Optional ENCODE status, usually released."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "encode_biosample_lookup",
            "title": "Look up an ENCODE biosample",
            "description": "Fetch one ENCODE biosample by ENCBS accession and return a front-end-compatible sample record.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "accession": {"type": "string", "description": "ENCODE biosample accession, for example ENCBS000AAA."},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["accession"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "encode_biosample_search",
            "title": "Search ENCODE biosamples",
            "description": "Search ENCODE biosamples with text and optional biosample term, organism, life-stage, or status filters.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text query such as K562, liver, MCF-7, T cell, or mouse."},
                    "biosample_term_name": {"type": "string", "description": "Optional exact biosample ontology term name, for example K562."},
                    "organism": {"type": "string", "description": "Optional organism scientific name, for example Homo sapiens or Mus musculus."},
                    "life_stage": {"type": "string", "description": "Optional ENCODE life stage, for example adult or embryonic."},
                    "status": {"type": "string", "description": "Optional ENCODE status, usually released."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "encode_file_lookup",
            "title": "Look up an ENCODE file",
            "description": "Fetch one ENCODE file by ENCFF accession and return a metadata-only download-plan record with portal, API, HTTPS, cloud, checksum, replicate, and assembly fields.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "accession": {"type": "string", "description": "ENCODE file accession, for example ENCFF789PHQ."},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["accession"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "encode_file_manifest",
            "title": "Build an ENCODE experiment file manifest",
            "description": "Return a metadata-only file manifest for an ENCODE experiment. No data download is started.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "experiment_accession": {"type": "string", "description": "ENCODE experiment accession, for example ENCSR844TIU."},
                    "max_files": {"type": "integer", "minimum": 1, "maximum": MAX_FILES, "default": DEFAULT_FILES},
                    "file_format": {"type": "string", "description": "Optional exact file format filter, for example fastq, bam, bigWig, or bed."},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["experiment_accession"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "encode_status",
            "title": "Inspect ENCODE MCP status",
            "description": "Return configured ENCODE MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
    ]


TOOL_HANDLERS = {
    "encode_parameter_domains": make_parameter_domains_handler("encode", "encode_parameter_domains", tool_definitions),
    "encode_experiment_lookup": encode_experiment_lookup,
    "encode_experiment_search": encode_experiment_search,
    "encode_biosample_lookup": encode_biosample_lookup,
    "encode_biosample_search": encode_biosample_search,
    "encode_file_lookup": encode_file_lookup,
    "encode_file_manifest": encode_file_manifest,
    "encode_status": encode_status,
}
