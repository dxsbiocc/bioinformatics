"""MCP tool registry for the AlphaFold server."""

from __future__ import annotations

from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition
import urllib.parse
from typing import Callable

from .client import AlphaFoldClient
from .constants import (
    ALPHAFOLD_API_BASE_URL,
    ALPHAFOLD_WEBSITE_BASE_URL,
    MAX_MODELS,
    RESULT_SCHEMA_VERSION,
    JsonObject,
)
from .records import alphafold_record, normalize_prediction
from .utils import optional_bool, optional_int, require_accession, source_info


def alphafold_status(args: JsonObject, client: AlphaFoldClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "alphafold",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "website_url": ALPHAFOLD_WEBSITE_BASE_URL,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["alphafold"],
        "tool_groups": {
            "protein_structure": ["alphafold_lookup"],
            "status": ["alphafold_status"],
        },
        "frontend_components": ["protein_structure"],
        "preview_kinds": ["structure_3d", "download_manifest", "sequence"],
        "file_formats": ["pdb", "mmcif", "bcif", "pae_json", "pae_image"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        predictions, _headers = client.request_json_array_with_headers(
            "prediction/P04637",
            {},
        )
        status["network_check"] = {
            "ok": True,
            "returned": len(predictions),
        }
    return status


def alphafold_lookup(args: JsonObject, client: AlphaFoldClient) -> JsonObject:
    accession = require_accession(args)
    max_models = optional_int(
        args,
        "max_models",
        default=20,
        minimum=1,
        maximum=MAX_MODELS,
    )
    canonical_only = optional_bool(args, "canonical_only", default=False)
    include_sequence = optional_bool(args, "include_sequence", default=False)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"prediction/{urllib.parse.quote(accession, safe='')}"
    params: JsonObject = {
        "accession": accession,
        "canonical_only": canonical_only,
        "include_sequence": include_sequence,
        "max_models": max_models,
    }
    predictions, headers = client.request_json_array_with_headers(endpoint, {})
    filtered = filter_predictions(
        predictions,
        accession=accession,
        canonical_only=canonical_only,
    )
    returned_predictions = filtered[:max_models]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "alphafold",
        "query": accession,
        "returned": len(returned_predictions),
        "total": len(predictions),
        "matching": len(filtered),
        "truncated": len(filtered) > len(returned_predictions),
        "canonical_only": canonical_only,
        "predictions": [
            normalize_prediction(prediction, include_sequence=include_sequence)
            for prediction in returned_predictions
        ],
        "records": [
            alphafold_record(prediction, include_sequence=include_sequence)
            for prediction in returned_predictions
        ],
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = predictions
    return response


def filter_predictions(
    predictions: list[JsonObject],
    *,
    accession: str,
    canonical_only: bool,
) -> list[JsonObject]:
    if not canonical_only:
        return predictions
    accession_lower = accession.lower()
    return [
        prediction
        for prediction in predictions
        if str(prediction.get("uniprotAccession") or "").lower() == accession_lower
    ]


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
        parameter_domains_tool_definition("alphafold_parameter_domains"),
        {
            "name": "alphafold_lookup",
            "title": "Look up AlphaFold predicted structures",
            "description": (
                "Fetch AlphaFold DB predictions for a UniProt accession and return "
                "front-end-compatible 3D structure records with PDB, mmCIF, "
                "BinaryCIF, PAE, and confidence metadata."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "accession": {
                        "type": "string",
                        "description": "UniProtKB accession, for example P04637.",
                    },
                    "canonical_only": {
                        "type": "boolean",
                        "default": False,
                        "description": "Return only the exact accession, excluding isoform accessions.",
                    },
                    "max_models": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_MODELS,
                        "default": 20,
                    },
                    "include_sequence": {
                        "type": "boolean",
                        "default": False,
                        "description": "Include model sequence text in records and sequence previews.",
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["accession"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "alphafold_status",
            "title": "Inspect AlphaFold MCP status",
            "description": "Return configured AlphaFold MCP capabilities and optional network health.",
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


TOOL_HANDLERS: dict[str, Callable[[JsonObject, AlphaFoldClient], JsonObject]] = {
    "alphafold_parameter_domains": make_parameter_domains_handler("alphafold", "alphafold_parameter_domains", tool_definitions),
    "alphafold_lookup": alphafold_lookup,
    "alphafold_status": alphafold_status,
}
