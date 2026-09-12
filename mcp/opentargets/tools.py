"""MCP tool registry for the Open Targets server."""

from __future__ import annotations

from typing import Callable

from .client import OpenTargetsClient
from .constants import MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import OpenTargetsError
from .records import (
    opentargets_disease_record,
    opentargets_search_record,
    opentargets_target_record,
)
from .utils import (
    optional_bool,
    optional_entity_names,
    optional_int,
    require_non_empty_string,
    source_info,
)


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


def tool_definitions() -> list[JsonObject]:
    read_only_annotations = {
        "readOnlyHint": True,
        "openWorldHint": True,
    }
    return [
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
    "opentargets_target_lookup": opentargets_target_lookup,
    "opentargets_disease_lookup": opentargets_disease_lookup,
    "opentargets_search": opentargets_search,
    "opentargets_status": opentargets_status,
}
