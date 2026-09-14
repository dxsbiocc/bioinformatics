"""MCP tool registry for the Open Targets server."""

from __future__ import annotations

from mcp.dynamic_context import build_dynamic_context_response
from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition
from typing import Callable

from .client import OpenTargetsClient
from .constants import MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import McpError, OpenTargetsError
from .records import (
    opentargets_disease_record,
    opentargets_search_record,
    opentargets_target_record,
)
from .utils import (
    normalize_space,
    optional_bool,
    optional_entity_names,
    optional_int,
    require_non_empty_string,
    source_info,
)


OPENTARGETS_CONTEXT_TYPES = ["all", "search", "targets", "diseases", "entity_names"]
OPENTARGETS_CONTEXT_SCHEMA_VERSION = "bioinformatics.dynamic_context.v1"


TARGET_QUERY = """
query TargetAssociatedDiseases($ensemblId: String!, $size: Int!) {
  target(ensemblId: $ensemblId) {
    id
    approvedSymbol
    approvedName
    biotype
    genomicLocation {
      chromosome
      start
      end
      strand
    }
    associatedDiseases(page: { index: 0, size: $size }) {
      count
      rows {
        score
        disease {
          id
          name
        }
        datasourceScores {
          id
          score
        }
        datatypeScores {
          id
          score
        }
      }
    }
  }
}
"""


DISEASE_QUERY = """
query DiseaseAssociatedTargets($efoId: String!, $size: Int!) {
  disease(efoId: $efoId) {
    id
    name
    description
    dbXRefs
    associatedTargets(page: { index: 0, size: $size }) {
      count
      rows {
        score
        target {
          id
          approvedSymbol
          approvedName
        }
        datasourceScores {
          id
          score
        }
        datatypeScores {
          id
          score
        }
      }
    }
  }
}
"""


SEARCH_QUERY = """
query Search($queryString: String!, $entityNames: [String!], $size: Int!) {
  search(queryString: $queryString, entityNames: $entityNames, page: { index: 0, size: $size }) {
    total
    hits {
      id
      entity
      score
      object {
        ... on Target {
          id
          approvedSymbol
          approvedName
          biotype
        }
        ... on Disease {
          id
          name
          description
          dbXRefs
        }
      }
    }
  }
}
"""


META_QUERY = """
query OpenTargetsMeta {
  meta {
    name
    product
    dataPrefix
    apiVersion {
      x
      y
      z
      suffix
    }
    dataVersion {
      year
      month
      iteration
    }
  }
}
"""


def opentargets_status(args: JsonObject, client: OpenTargetsClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "opentargets",
        "version": "0.1.0",
        "graphql_url": client.config.graphql_url,
        "website_base_url": client.config.website_base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["opentargets"],
        "tool_groups": {
            "context": ["opentargets_parameter_domains", "opentargets_resolve_context"],
            "target": ["opentargets_target_lookup"],
            "disease": ["opentargets_disease_lookup"],
            "search": ["opentargets_search"],
            "status": ["opentargets_status"],
        },
        "frontend_components": ["gene", "dataset", "identifier_conversion"],
        "preview_kinds": ["table", "xref_groups"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload, _headers = client.request_graphql_with_headers(META_QUERY, {})
        ensure_no_graphql_errors(payload)
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        meta = data.get("meta") if isinstance(data, dict) and isinstance(data.get("meta"), dict) else {}
        status["network_check"] = {
            "ok": True,
            "name": meta.get("name"),
            "product": meta.get("product"),
            "data_prefix": meta.get("dataPrefix"),
            "api_version": version_label(meta.get("apiVersion")),
            "data_version": version_label(meta.get("dataVersion")),
        }
    return status


def opentargets_resolve_context(args: JsonObject, client: OpenTargetsClient) -> JsonObject:
    context_type = optional_context_type(args, "context_type", allowed=OPENTARGETS_CONTEXT_TYPES, default="all")
    query = optional_text(args, "query")
    ensembl_id = optional_text(args, "ensembl_id")
    efo_id = optional_text(args, "efo_id")
    entity_names = optional_entity_names(args) if "entity_names" in args else ["target", "disease"]
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    contexts = static_opentargets_contexts()
    recommended_calls: list[JsonObject] = []
    sources: list[JsonObject] = []
    raw: JsonObject = {}

    if query:
        result = opentargets_search(
            {"query": query, "entity_names": entity_names, "max_results": max_results, "include_raw": include_raw},
            client,
        )
        for record in [record for record in result.get("records", []) if isinstance(record, dict)]:
            hits = record.get("data", {}).get("hits") if isinstance(record.get("data"), dict) else []
            for hit in hits if isinstance(hits, list) else []:
                if isinstance(hit, dict):
                    contexts.append(opentargets_hit_context(hit))
                    recommended_calls.extend(opentargets_hit_recommended_calls(hit))
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["search"] = result["raw"]

    if ensembl_id:
        result = opentargets_target_lookup({"ensembl_id": ensembl_id, "max_results": max_results, "include_raw": include_raw}, client)
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(opentargets_record_context(record) for record in records)
        for record in records:
            recommended_calls.extend(opentargets_record_recommended_calls(record))
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["target"] = result["raw"]

    if efo_id:
        result = opentargets_disease_lookup({"efo_id": efo_id, "max_results": max_results, "include_raw": include_raw}, client)
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(opentargets_record_context(record) for record in records)
        for record in records:
            recommended_calls.extend(opentargets_record_recommended_calls(record))
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["disease"] = result["raw"]

    filtered_contexts = [
        context
        for context in contexts
        if opentargets_context_matches(context, context_type=context_type, query=query or ensembl_id or efo_id)
    ]
    return build_dynamic_context_response(
        schema_version=RESULT_SCHEMA_VERSION,
        context_schema_version=OPENTARGETS_CONTEXT_SCHEMA_VERSION,
        database="opentargets",
        query={
            "context_type": context_type,
            "query": query,
            "ensembl_id": ensembl_id,
            "efo_id": efo_id,
            "entity_names": entity_names,
        },
        contexts=filtered_contexts,
        recommended_calls=recommended_calls,
        max_results=max_results,
        fallback_source=source_info("resolve_context", {"context_type": context_type, "query": query, "ensembl_id": ensembl_id, "efo_id": efo_id}),
        sources=sources,
        entity_groups={"targets", "diseases"},
        raw=raw,
        include_raw=include_raw,
        prioritize_entities=True,
        prioritize_same_server_calls=True,
    )


def opentargets_target_lookup(args: JsonObject, client: OpenTargetsClient) -> JsonObject:
    ensembl_id = require_non_empty_string(args, "ensembl_id")
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    variables: JsonObject = {"ensemblId": ensembl_id, "size": max_results}
    payload, headers = client.request_graphql_with_headers(TARGET_QUERY, variables)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    target = data.get("target") if isinstance(data, dict) else None
    if not isinstance(target, dict):
        ensure_no_graphql_errors(payload)
        raise OpenTargetsError(f"Open Targets target not found for {ensembl_id}")
    record = opentargets_target_record(
        target,
        max_results=max_results,
        website_base_url=client.config.website_base_url,
        graphql_url=client.config.graphql_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "opentargets",
        "query": ensembl_id,
        "returned": 1,
        "target": target_summary(record),
        "records": [record],
        "source": source_with_headers("target", variables, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def opentargets_disease_lookup(args: JsonObject, client: OpenTargetsClient) -> JsonObject:
    efo_id = require_non_empty_string(args, "efo_id")
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    variables: JsonObject = {"efoId": efo_id, "size": max_results}
    payload, headers = client.request_graphql_with_headers(DISEASE_QUERY, variables)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    disease = data.get("disease") if isinstance(data, dict) else None
    if not isinstance(disease, dict):
        ensure_no_graphql_errors(payload)
        raise OpenTargetsError(f"Open Targets disease not found for {efo_id}")
    record = opentargets_disease_record(
        disease,
        max_results=max_results,
        website_base_url=client.config.website_base_url,
        graphql_url=client.config.graphql_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "opentargets",
        "query": efo_id,
        "returned": 1,
        "disease": disease_summary(record),
        "records": [record],
        "source": source_with_headers("disease", variables, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def opentargets_search(args: JsonObject, client: OpenTargetsClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    entity_names = optional_entity_names(args)
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    variables: JsonObject = {
        "queryString": query,
        "entityNames": entity_names,
        "size": max_results,
    }
    payload, headers = client.request_graphql_with_headers(SEARCH_QUERY, variables)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    search = data.get("search") if isinstance(data, dict) else None
    if not isinstance(search, dict):
        ensure_no_graphql_errors(payload)
        raise OpenTargetsError(f"Open Targets search failed for {query}")
    record = opentargets_search_record(
        query=query,
        search=search,
        entity_names=entity_names,
        max_results=max_results,
        website_base_url=client.config.website_base_url,
        graphql_url=client.config.graphql_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "opentargets",
        "query": query,
        "entity_names": entity_names,
        "returned": len(record["data"]["hits"]) if isinstance(record.get("data"), dict) else 0,
        "total": record["data"].get("total_hits") if isinstance(record.get("data"), dict) else None,
        "search": search_summary(record),
        "records": [record],
        "source": source_with_headers("search", variables, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def ensure_no_graphql_errors(payload: JsonObject) -> None:
    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        messages = []
        for item in errors:
            if isinstance(item, dict) and item.get("message"):
                messages.append(str(item["message"]))
            else:
                messages.append(str(item))
        raise OpenTargetsError("; ".join(messages))


def target_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "target_id": data.get("target_id"),
        "symbol": data.get("symbol"),
        "name": data.get("name"),
        "associated_diseases": data.get("total_associated_diseases"),
        "url": data.get("url"),
    }


def disease_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "disease_id": data.get("disease_id"),
        "name": data.get("name"),
        "associated_targets": data.get("total_associated_targets"),
        "url": data.get("url"),
    }


def search_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "query": data.get("query"),
        "total_hits": data.get("total_hits"),
        "returned": len(data.get("hits", [])) if isinstance(data.get("hits"), list) else 0,
        "url": data.get("url"),
    }


def version_label(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    if "year" in value or "month" in value:
        parts = [value.get("year"), value.get("month")]
    else:
        parts = [value.get("x"), value.get("y"), value.get("z")]
    numeric = ".".join(str(part) for part in parts if part is not None)
    suffix = value.get("suffix") or value.get("iteration")
    return f"{numeric}-{suffix}" if numeric and suffix else numeric or None


def source_with_headers(operation: str, variables: JsonObject, headers: dict[str, str]) -> JsonObject:
    source = source_info(operation, variables)
    content_type = headers.get("content-type")
    if content_type:
        source["content_type"] = content_type
    return source


def optional_text(args: JsonObject, name: str) -> str:
    value = args.get(name)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise McpError(-32602, f"{name} must be a string")
    return value.strip()


def optional_context_type(args: JsonObject, name: str, *, allowed: list[str], default: str) -> str:
    value = optional_text(args, name) or default
    if value not in allowed:
        raise McpError(-32602, f"{name} must be one of: {', '.join(allowed)}")
    return value


def static_opentargets_contexts() -> list[JsonObject]:
    contexts: list[JsonObject] = [
        opentargets_parameter_context(
            "context_type",
            value,
            label=value,
            description="Dynamic Open Targets context family to resolve before target, disease, or search calls.",
            kind="enum",
            group="context_types",
            url="",
            metadata={"context_type": value},
        )
        for value in OPENTARGETS_CONTEXT_TYPES
    ]
    contexts.extend(
        opentargets_parameter_context(
            "entity_names",
            value,
            label=value,
            description="Open Targets search entity filter.",
            kind="entity_name",
            group="entity_names",
            url="",
            metadata={"entity_name": value, "tool_hint": "opentargets_search"},
        )
        for value in ["target", "disease"]
    )
    return contexts


def opentargets_record_context(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    record_type = normalize_space(record.get("record_type"))
    if record_type == "opentargets_disease":
        parameter_name, group, value = "efo_id", "diseases", normalize_space(data.get("disease_id") or record.get("id"))
    else:
        parameter_name, group, value = "ensembl_id", "targets", normalize_space(data.get("target_id") or record.get("id"))
    return opentargets_parameter_context(
        parameter_name,
        value,
        label=normalize_space(record.get("title") or record.get("label") or value),
        description=normalize_space(record.get("description") or data.get("description") or data.get("name")),
        kind=record_type or group.rstrip("s"),
        group=group,
        url=normalize_space(record.get("url") or data.get("url")),
        metadata={
            "id": value,
            "symbol": data.get("symbol", ""),
            "name": data.get("name", ""),
            "biotype": data.get("biotype", ""),
            "associated_diseases": data.get("total_associated_diseases", ""),
            "associated_targets": data.get("total_associated_targets", ""),
        },
    )


def opentargets_hit_context(hit: JsonObject) -> JsonObject:
    entity = normalize_space(hit.get("entity"))
    identifier = normalize_space(hit.get("id"))
    group = "diseases" if entity == "disease" else "targets"
    parameter_name = "efo_id" if entity == "disease" else "ensembl_id"
    return opentargets_parameter_context(
        parameter_name,
        identifier,
        label=normalize_space(hit.get("label") or identifier),
        description=normalize_space(hit.get("description") or entity),
        kind=f"search_{entity or 'hit'}",
        group=group,
        url=normalize_space(hit.get("url")),
        metadata={"id": identifier, "entity": entity, "score": hit.get("score", ""), "label": hit.get("label", "")},
    )


def opentargets_parameter_context(
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
    display_fields = [{"label": key.replace("_", " ").title(), "value": item} for key, item in metadata.items() if item not in ("", None, [], {})]
    if url:
        display_fields.append({"label": "URL", "value": url})
    component = "dataset" if group == "diseases" else "gene" if group == "targets" else "identifier_conversion"
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
            "icon": "opentargets",
            "title": label,
            "subtitle": f"{parameter_name}: {value}",
            "description": description,
            "metadata": display_fields,
            "badges": [{"label": "Open Targets", "kind": "source"}, {"label": parameter_name, "kind": "parameter"}],
            "actions": [{"label": "Open source", "url": url, "kind": "external", "primary": True}] if url else [],
            "hover": {"title": label, "subtitle": f"{parameter_name}: {value}", "icon": "opentargets", "fields": display_fields},
            "primary_url": url,
        },
    }


def opentargets_record_recommended_calls(record: JsonObject) -> list[JsonObject]:
    return opentargets_hit_recommended_calls({"id": record.get("id"), "entity": "disease" if record.get("record_type") == "opentargets_disease" else "target"})


def opentargets_hit_recommended_calls(hit: JsonObject) -> list[JsonObject]:
    entity = normalize_space(hit.get("entity"))
    identifier = normalize_space(hit.get("id"))
    if entity == "disease":
        return [
            {"tool_name": "opentargets_disease_lookup", "arguments": {"efo_id": identifier}, "reason": "Fetch associated targets and evidence scores for this Open Targets disease."},
            {"server": "efo", "tool_name": "efo_term_lookup", "arguments": {"term_id": identifier}, "reason": "Open ontology context for this disease or phenotype identifier."},
        ]
    return [
        {"tool_name": "opentargets_target_lookup", "arguments": {"ensembl_id": identifier}, "reason": "Fetch associated diseases and evidence scores for this Open Targets target."},
        {"server": "ensembl", "tool_name": "ensembl_lookup", "arguments": {"ensembl_id": identifier}, "reason": "Open Ensembl gene metadata for this target."},
    ]


def opentargets_context_matches(context: JsonObject, *, context_type: str, query: str) -> bool:
    if context_type != "all" and context.get("group") != context_type:
        return False
    if not query:
        return True
    metadata = context.get("metadata")
    haystack_values = [context.get("parameter_name"), context.get("value"), context.get("label"), context.get("description"), context.get("kind")]
    if isinstance(metadata, dict):
        haystack_values.extend(metadata.values())
    haystack = " ".join(str(item).lower() for item in haystack_values if item not in ("", None))
    return query.lower() in haystack or context.get("group") in {"targets", "diseases"}


def tool_definitions() -> list[JsonObject]:
    read_only_annotations = {
        "readOnlyHint": True,
        "openWorldHint": True,
    }
    return [
        parameter_domains_tool_definition("opentargets_parameter_domains"),
        {
            "name": "opentargets_resolve_context",
            "title": "Resolve Open Targets dynamic parameter context",
            "description": (
                "Resolve Open Targets target and disease IDs from search or explicit identifiers before lookup calls. "
                "Returns front-end-friendly context rows, Open Targets URLs, and recommended follow-up calls."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "context_type": {"type": "string", "enum": OPENTARGETS_CONTEXT_TYPES, "default": "all"},
                    "query": {"type": "string", "description": "Optional Open Targets search text such as TP53 or asthma."},
                    "ensembl_id": {"type": "string", "description": "Optional Ensembl target ID such as ENSG00000141510."},
                    "efo_id": {"type": "string", "description": "Optional disease ID such as MONDO_0004979."},
                    "entity_names": {"type": "array", "items": {"type": "string", "enum": ["target", "disease"]}, "default": ["target", "disease"]},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": 10},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "opentargets_target_lookup",
            "title": "Look up Open Targets target-disease associations",
            "description": (
                "Fetch one Open Targets target by Ensembl gene ID and return a front-end-compatible "
                "gene record with associated diseases, datasource scores, datatype scores, and links."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ensembl_id": {
                        "type": "string",
                        "description": "Ensembl gene ID, for example ENSG00000141510.",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_RESULTS,
                        "default": 10,
                    },
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["ensembl_id"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "opentargets_disease_lookup",
            "title": "Look up Open Targets disease-target associations",
            "description": (
                "Fetch one Open Targets disease or phenotype by EFO/MONDO ID and return a dataset-style "
                "record with associated targets, datasource scores, datatype scores, and ontology xrefs."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "efo_id": {
                        "type": "string",
                        "description": "Open Targets disease ID, for example MONDO_0004979.",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_RESULTS,
                        "default": 10,
                    },
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["efo_id"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "opentargets_search",
            "title": "Search Open Targets targets and diseases",
            "description": (
                "Search Open Targets target and disease entities and return an identifier-conversion "
                "record with clickable target or disease hits."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search text, for example TP53 or asthma."},
                    "entity_names": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["target", "disease"]},
                        "default": ["target", "disease"],
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_RESULTS,
                        "default": 10,
                    },
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "opentargets_status",
            "title": "Inspect Open Targets MCP status",
            "description": "Return configured Open Targets MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
    ]


TOOL_HANDLERS: dict[str, Callable[[JsonObject, OpenTargetsClient], JsonObject]] = {
    "opentargets_parameter_domains": make_parameter_domains_handler("opentargets", "opentargets_parameter_domains", tool_definitions),
    "opentargets_resolve_context": opentargets_resolve_context,
    "opentargets_target_lookup": opentargets_target_lookup,
    "opentargets_disease_lookup": opentargets_disease_lookup,
    "opentargets_search": opentargets_search,
    "opentargets_status": opentargets_status,
}
