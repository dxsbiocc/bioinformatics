"""MCP tool registry for the Ensembl server."""

from __future__ import annotations

from typing import Callable

from .client import EnsemblClient
from .constants import MAX_RESULTS, MAX_XREFS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import EnsemblError
from .records import ensembl_feature_record, ensembl_variant_record, ensembl_xrefs_record
from .utils import (
    normalize_space,
    optional_bool,
    optional_int,
    optional_string,
    optional_string_list,
    require_ensembl_id,
    require_non_empty_string,
    require_region,
    source_info,
)


OVERLAP_FEATURES = {"gene", "transcript", "variation", "regulatory"}


def ensembl_status(args: JsonObject, client: EnsemblClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "ensembl",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "website_url": client.config.website_base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["ensembl"],
        "tool_groups": {
            "annotation": [
                "ensembl_lookup",
                "ensembl_xrefs",
                "ensembl_overlap_region",
            ],
            "variation": ["ensembl_variation"],
            "status": ["ensembl_status"],
        },
        "frontend_components": ["gene", "genomic_feature", "variant", "identifier_conversion"],
        "preview_kinds": ["table", "xref_groups"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload, _headers = client.request_json_with_headers("lookup/id/ENSG00000141510", {})
        if not isinstance(payload, dict):
            raise EnsemblError("Ensembl network check returned non-object JSON")
        status["network_check"] = {
            "ok": True,
            "id": payload.get("id"),
            "display_name": payload.get("display_name"),
        }
    return status


def ensembl_lookup(args: JsonObject, client: EnsemblClient) -> JsonObject:
    ensembl_id = require_ensembl_id(args)
    expand = optional_bool(args, "expand", default=False)
    include_xrefs = optional_bool(args, "include_xrefs", default=False)
    max_xrefs = optional_int(args, "max_xrefs", default=25, minimum=0, maximum=MAX_XREFS)
    include_raw = optional_bool(args, "include_raw", default=False)
    params: JsonObject = {}
    if expand:
        params["expand"] = 1
    endpoint = f"lookup/id/{ensembl_id}"
    payload, headers = client.request_json_with_headers(endpoint, params)
    if not isinstance(payload, dict):
        raise EnsemblError(f"Ensembl {endpoint} returned non-object JSON")
    xrefs: list[JsonObject] = []
    xref_total = 0
    if include_xrefs and max_xrefs > 0:
        xref_payload, _xref_headers = client.request_json_with_headers(
            f"xrefs/id/{ensembl_id}",
            {"all_levels": 1},
        )
        if isinstance(xref_payload, list):
            xref_total = len(xref_payload)
            xrefs = [item for item in xref_payload[:max_xrefs] if isinstance(item, dict)]
    record = ensembl_feature_record(payload, xrefs=xrefs)
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "ensembl",
        "query": ensembl_id,
        "returned": 1,
        "record": feature_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    if include_xrefs:
        response["xref_total"] = xref_total
    if include_raw:
        response["raw"] = payload
    return response


def ensembl_xrefs(args: JsonObject, client: EnsemblClient) -> JsonObject:
    ensembl_id = require_ensembl_id(args)
    all_levels = optional_bool(args, "all_levels", default=False)
    max_results = optional_int(args, "max_results", default=25, minimum=1, maximum=MAX_XREFS)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"xrefs/id/{ensembl_id}"
    params: JsonObject = {"all_levels": 1} if all_levels else {}
    payload, headers = client.request_json_with_headers(endpoint, params)
    if not isinstance(payload, list):
        raise EnsemblError(f"Ensembl {endpoint} returned non-list JSON")
    xrefs = [item for item in payload[:max_results] if isinstance(item, dict)]
    record = ensembl_xrefs_record(ensembl_id, xrefs, total=len(payload))
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "ensembl",
        "query": ensembl_id,
        "returned": len(xrefs),
        "total": len(payload),
        "records": [record],
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def ensembl_overlap_region(args: JsonObject, client: EnsemblClient) -> JsonObject:
    species = optional_string(args, "species", default="homo_sapiens")
    region = require_region(args)
    features = optional_string_list(
        args,
        "features",
        default=["gene"],
        allowed=OVERLAP_FEATURES,
    )
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"overlap/region/{species}/{region}"
    params: JsonObject = {"feature": features}
    payload, headers = client.request_json_with_headers(endpoint, params)
    if not isinstance(payload, list):
        raise EnsemblError(f"Ensembl {endpoint} returned non-list JSON")
    items = [item for item in payload[:max_results] if isinstance(item, dict)]
    records = [
        ensembl_variant_record(item, species=species, source_region=region)
        if normalize_space(item.get("feature_type")).lower() == "variation"
        else ensembl_feature_record(item, source_region=region)
        for item in items
    ]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "ensembl",
        "query": region,
        "species": species,
        "features": features,
        "returned": len(records),
        "total": len(payload),
        "truncated": len(payload) > len(records),
        "records": records,
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def ensembl_variation(args: JsonObject, client: EnsemblClient) -> JsonObject:
    species = optional_string(args, "species", default="homo_sapiens")
    variant_id = require_non_empty_string(args, "variant_id")
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"variation/{species}/{variant_id}"
    payload, headers = client.request_json_with_headers(endpoint, {})
    if not isinstance(payload, dict):
        raise EnsemblError(f"Ensembl {endpoint} returned non-object JSON")
    record = ensembl_variant_record(payload, species=species)
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "ensembl",
        "query": variant_id,
        "species": species,
        "returned": 1,
        "variant": variant_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def feature_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "id": normalize_space(data.get("id")),
        "display_name": normalize_space(data.get("display_name")),
        "object_type": normalize_space(data.get("object_type")),
        "species": normalize_space(data.get("species")),
        "location": normalize_space(data.get("location")),
        "url": normalize_space(data.get("url")),
    }


def variant_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "id": normalize_space(data.get("id")),
        "var_class": normalize_space(data.get("var_class")),
        "most_severe_consequence": normalize_space(data.get("most_severe_consequence")),
        "primary_location": normalize_space(data.get("primary_location")),
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
            "name": "ensembl_lookup",
            "title": "Look up an Ensembl stable ID",
            "description": (
                "Fetch one Ensembl gene, transcript, exon, protein, or other stable ID "
                "and return an app-renderable gene/genomic_feature record."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ensembl_id": {"type": "string", "description": "Ensembl stable ID, for example ENSG00000141510."},
                    "expand": {"type": "boolean", "default": False},
                    "include_xrefs": {"type": "boolean", "default": False},
                    "max_xrefs": {"type": "integer", "minimum": 0, "maximum": MAX_XREFS, "default": 25},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["ensembl_id"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "ensembl_xrefs",
            "title": "Fetch Ensembl cross-references",
            "description": "Fetch external database references for one Ensembl stable ID.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ensembl_id": {"type": "string"},
                    "all_levels": {"type": "boolean", "default": False},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_XREFS, "default": 25},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["ensembl_id"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "ensembl_overlap_region",
            "title": "Fetch Ensembl region overlap features",
            "description": (
                "Fetch genes, transcripts, variants, or regulatory features overlapping "
                "a genomic region and return app-renderable records."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "species": {"type": "string", "default": "homo_sapiens"},
                    "region": {"type": "string", "description": "Region such as 17:7661779-7687546."},
                    "features": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}},
                        ],
                        "default": ["gene"],
                    },
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": 10},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["region"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "ensembl_variation",
            "title": "Look up an Ensembl variant",
            "description": "Fetch Ensembl variation metadata for a variant such as rs699.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "species": {"type": "string", "default": "homo_sapiens"},
                    "variant_id": {"type": "string", "description": "Variant identifier, for example rs699."},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["variant_id"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "ensembl_status",
            "title": "Inspect Ensembl MCP status",
            "description": "Return configured Ensembl MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
    ]


TOOL_HANDLERS: dict[str, Callable[[JsonObject, EnsemblClient], JsonObject]] = {
    "ensembl_lookup": ensembl_lookup,
    "ensembl_xrefs": ensembl_xrefs,
    "ensembl_overlap_region": ensembl_overlap_region,
    "ensembl_variation": ensembl_variation,
    "ensembl_status": ensembl_status,
}

