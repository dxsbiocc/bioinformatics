"""MCP tool registry for the Ensembl server."""

from __future__ import annotations

from mcp.dynamic_context import build_dynamic_context_response
from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition
from typing import Callable

from .client import EnsemblClient
from .constants import MAX_RESULTS, MAX_XREFS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import EnsemblError, McpError
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
ENSEMBL_CONTEXT_TYPES = ["all", "stable_ids", "xrefs", "regions", "variations", "species", "features"]
ENSEMBL_CONTEXT_SCHEMA_VERSION = "bioinformatics.dynamic_context.v1"
ENSEMBL_SPECIES_HINTS = [
    ("homo_sapiens", "Homo sapiens"),
    ("mus_musculus", "Mus musculus"),
    ("rattus_norvegicus", "Rattus norvegicus"),
    ("danio_rerio", "Danio rerio"),
]


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
            "context": ["ensembl_parameter_domains", "ensembl_resolve_context"],
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


def ensembl_resolve_context(args: JsonObject, client: EnsemblClient) -> JsonObject:
    context_type = optional_context_type(args, "context_type", allowed=ENSEMBL_CONTEXT_TYPES, default="all")
    ensembl_id = optional_string(args, "ensembl_id", default="")
    region = optional_string(args, "region", default="")
    variant_id = optional_string(args, "variant_id", default="")
    species = optional_string(args, "species", default="homo_sapiens")
    features = optional_string_list(args, "features", default=["gene"], allowed=OVERLAP_FEATURES)
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    contexts = static_ensembl_contexts()
    recommended_calls: list[JsonObject] = []
    sources: list[JsonObject] = []
    raw: JsonObject = {}

    if ensembl_id:
        result = ensembl_lookup(
            {
                "ensembl_id": ensembl_id,
                "expand": False,
                "include_xrefs": False,
                "max_xrefs": min(max_results, MAX_XREFS),
                "include_raw": include_raw,
            },
            client,
        )
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(ensembl_record_context(record) for record in records)
        for record in records:
            recommended_calls.extend(ensembl_recommended_calls(record))
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["lookup"] = result["raw"]

    if ensembl_id and context_type in {"all", "xrefs"}:
        result = ensembl_xrefs(
            {
                "ensembl_id": ensembl_id,
                "all_levels": True,
                "max_results": min(max_results, MAX_XREFS),
                "include_raw": include_raw,
            },
            client,
        )
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(ensembl_record_context(record) for record in records)
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["xrefs"] = result["raw"]

    if region:
        result = ensembl_overlap_region(
            {
                "species": species,
                "region": region,
                "features": features,
                "max_results": max_results,
                "include_raw": include_raw,
            },
            client,
        )
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(ensembl_record_context(record, group="regions") for record in records)
        for record in records[:3]:
            recommended_calls.extend(ensembl_recommended_calls(record))
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["overlap"] = result["raw"]

    if variant_id:
        result = ensembl_variation(
            {"species": species, "variant_id": variant_id, "include_raw": include_raw},
            client,
        )
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(ensembl_record_context(record) for record in records)
        for record in records:
            recommended_calls.extend(ensembl_recommended_calls(record))
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["variation"] = result["raw"]

    query_text = ensembl_id or region or variant_id or species
    filtered_contexts = [
        context
        for context in contexts
        if ensembl_context_matches(context, context_type=context_type, query=query_text)
    ]
    return build_dynamic_context_response(
        schema_version=RESULT_SCHEMA_VERSION,
        context_schema_version=ENSEMBL_CONTEXT_SCHEMA_VERSION,
        database="ensembl",
        query={
            "context_type": context_type,
            "ensembl_id": ensembl_id,
            "region": region,
            "variant_id": variant_id,
            "species": species,
            "features": features,
        },
        contexts=filtered_contexts,
        recommended_calls=recommended_calls,
        max_results=max_results,
        fallback_source=source_info("resolve_context", {"context_type": context_type, "ensembl_id": ensembl_id, "region": region, "variant_id": variant_id}),
        sources=sources,
        entity_groups={"stable_ids", "regions", "variations", "xrefs"},
        raw=raw,
        summary_fields={
            "features": lambda context: context.get("group") in {"stable_ids", "regions", "variations"},
        },
        include_raw=include_raw,
    )


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


def optional_context_type(args: JsonObject, name: str, *, allowed: list[str], default: str) -> str:
    value = optional_string(args, name, default=default)
    if value not in allowed:
        raise McpError(-32602, f"{name} must be one of: {', '.join(allowed)}")
    return value


def static_ensembl_contexts() -> list[JsonObject]:
    contexts: list[JsonObject] = [
        ensembl_parameter_context(
            "context_type",
            value,
            label=value,
            description="Dynamic Ensembl context family to resolve before stable-ID, region, xref, or variant calls.",
            kind="enum",
            group="context_types",
            url="",
            metadata={"context_type": value},
        )
        for value in ENSEMBL_CONTEXT_TYPES
    ]
    contexts.extend(
        ensembl_parameter_context(
            "species",
            value,
            label=label,
            description="Common Ensembl species path segment accepted by REST endpoints.",
            kind="species",
            group="species",
            url=f"https://www.ensembl.org/{label.replace(' ', '_')}/Info/Index",
            metadata={"species": value, "label": label},
        )
        for value, label in ENSEMBL_SPECIES_HINTS
    )
    contexts.extend(
        ensembl_parameter_context(
            "features",
            feature,
            label=feature,
            description="Feature type accepted by ensembl_overlap_region.",
            kind="feature_type",
            group="features",
            url="",
            metadata={"feature": feature, "tool_hint": "ensembl_overlap_region"},
        )
        for feature in sorted(OVERLAP_FEATURES)
    )
    return contexts


def ensembl_record_context(record: JsonObject, *, group: str = "") -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    record_type = normalize_space(record.get("record_type"))
    parameter_name = "variant_id" if record_type == "ensembl_variant" else "ensembl_id"
    if not group:
        if record_type == "ensembl_xrefs":
            group = "xrefs"
        elif record_type == "ensembl_variant":
            group = "variations"
        else:
            group = "stable_ids"
    value = normalize_space(data.get("id") or data.get("ensembl_id") or record.get("id"))
    label = normalize_space(record.get("title") or record.get("label") or value)
    return ensembl_parameter_context(
        parameter_name,
        value,
        label=label,
        description=normalize_space(record.get("description") or label),
        kind=record_type or group.rstrip("s"),
        group=group,
        url=normalize_space(record.get("url") or data.get("url")),
        metadata={
            "id": value,
            "display_name": data.get("display_name", ""),
            "object_type": data.get("object_type", ""),
            "species": data.get("species", ""),
            "location": data.get("location") or data.get("primary_location", ""),
            "biotype": data.get("biotype", ""),
            "var_class": data.get("var_class", ""),
            "most_severe_consequence": data.get("most_severe_consequence", ""),
        },
    )


def ensembl_parameter_context(
    parameter_name: str,
    value: object,
    *,
    label: str,
    description: str,
    kind: str,
    group: str,
    url: str,
    metadata: JsonObject,
) -> JsonObject:
    display_fields = [
        {"label": key.replace("_", " ").title(), "value": item}
        for key, item in metadata.items()
        if item not in ("", None, [], {})
    ]
    if url:
        display_fields.append({"label": "URL", "value": url})
    component = "variant" if group == "variations" else "identifier_conversion" if group == "xrefs" else "gene"
    return {
        "kind": kind,
        "group": group,
        "parameter_name": parameter_name,
        "value": value,
        "label": label,
        "title": label,
        "description": description,
        "url": url,
        "metadata": metadata,
        "display": {
            "component": component,
            "chip_label": parameter_name,
            "icon": "ensembl",
            "title": label,
            "subtitle": f"{parameter_name}: {value}",
            "description": description,
            "metadata": display_fields,
            "badges": [
                {"label": "Ensembl", "kind": "source"},
                {"label": parameter_name, "kind": "parameter"},
            ],
            "actions": [{"label": "Open source", "url": url, "kind": "external", "primary": True}] if url else [],
            "hover": {"title": label, "subtitle": f"{parameter_name}: {value}", "icon": "ensembl", "fields": display_fields},
            "primary_url": url,
        },
    }


def ensembl_recommended_calls(record: JsonObject) -> list[JsonObject]:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    record_type = normalize_space(record.get("record_type"))
    if record_type == "ensembl_variant":
        variant_id = normalize_space(data.get("id") or record.get("id"))
        return [
            {"tool_name": "ensembl_variation", "arguments": {"species": data.get("species") or "homo_sapiens", "variant_id": variant_id}, "reason": "Fetch Ensembl variant metadata and genomic mappings."},
            {"server": "clinvar", "tool_name": "clinvar_search", "arguments": {"terms": variant_id}, "reason": "Check clinical significance for this variant in ClinVar."},
        ]
    ensembl_id = normalize_space(data.get("id") or data.get("ensembl_id") or record.get("id"))
    return [
        {"tool_name": "ensembl_lookup", "arguments": {"ensembl_id": ensembl_id, "include_xrefs": True}, "reason": "Fetch detailed Ensembl feature metadata and cross-references."},
        {"tool_name": "ensembl_xrefs", "arguments": {"ensembl_id": ensembl_id, "all_levels": True}, "reason": "Fetch external database references for this stable ID."},
    ]


def ensembl_context_matches(context: JsonObject, *, context_type: str, query: str) -> bool:
    if context_type != "all" and context.get("group") != context_type:
        return False
    if not query:
        return True
    metadata = context.get("metadata")
    haystack_values = [
        context.get("parameter_name"),
        context.get("value"),
        context.get("label"),
        context.get("description"),
        context.get("kind"),
    ]
    if isinstance(metadata, dict):
        haystack_values.extend(metadata.values())
    haystack = " ".join(str(item).lower() for item in haystack_values if item not in ("", None))
    return query.lower() in haystack or context.get("group") in {"stable_ids", "regions", "variations", "xrefs"}


def tool_definitions() -> list[JsonObject]:
    read_only_annotations = {
        "readOnlyHint": True,
        "openWorldHint": True,
    }
    return [
        parameter_domains_tool_definition("ensembl_parameter_domains"),
        {
            "name": "ensembl_resolve_context",
            "title": "Resolve Ensembl dynamic parameter context",
            "description": (
                "Resolve Ensembl stable IDs, region-overlap features, variants, species hints, and feature-type values "
                "before calling Ensembl lookup, xref, overlap, or variation tools."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "context_type": {"type": "string", "enum": ENSEMBL_CONTEXT_TYPES, "default": "all"},
                    "ensembl_id": {"type": "string", "description": "Optional Ensembl stable ID such as ENSG00000141510."},
                    "region": {"type": "string", "description": "Optional genomic region such as 17:7661779-7687546."},
                    "variant_id": {"type": "string", "description": "Optional variant identifier such as rs699."},
                    "species": {"type": "string", "default": "homo_sapiens"},
                    "features": {"oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}], "default": ["gene"]},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": 10},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
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
    "ensembl_parameter_domains": make_parameter_domains_handler("ensembl", "ensembl_parameter_domains", tool_definitions),
    "ensembl_resolve_context": ensembl_resolve_context,
    "ensembl_lookup": ensembl_lookup,
    "ensembl_xrefs": ensembl_xrefs,
    "ensembl_overlap_region": ensembl_overlap_region,
    "ensembl_variation": ensembl_variation,
    "ensembl_status": ensembl_status,
}
