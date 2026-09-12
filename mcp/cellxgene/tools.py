"""MCP tool registry for the CELLxGENE Discover server."""

from __future__ import annotations

from .client import CellxGeneClient
from .constants import DEFAULT_DATASETS, DEFAULT_RESULTS, MAX_DATASETS, MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import CellxGeneError
from .records import cellxgene_assets_download_plan_record, cellxgene_collection_record
from .utils import normalize_space, optional_bool, optional_int, require_non_empty_string, require_uuid, source_info


def cellxgene_status(args: JsonObject, client: CellxGeneClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "cellxgene",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "website_base_url": client.config.website_base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["cellxgene_discover"],
        "tool_groups": {
            "collections": ["cellxgene_collection_lookup", "cellxgene_collections_search"],
            "assets": ["cellxgene_collection_assets"],
            "status": ["cellxgene_status"],
        },
        "frontend_components": ["project", "download_plan"],
        "preview_kinds": ["table", "citation_list", "xref_groups", "download_manifest"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload, headers = client.request_json_with_headers("collections/db468083-041c-41ca-8f6f-bf991a070adf", {})
        status["network_check"] = {
            "ok": True,
            "example_collection_id": payload.get("collection_id") if isinstance(payload, dict) else None,
            "example_name": payload.get("name") if isinstance(payload, dict) else None,
            "content_type": headers.get("content-type"),
        }
    return status


def cellxgene_collection_lookup(args: JsonObject, client: CellxGeneClient) -> JsonObject:
    collection_id = require_uuid(args, "collection_id")
    max_datasets = optional_int(args, "max_datasets", default=DEFAULT_DATASETS, minimum=1, maximum=MAX_DATASETS)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"collections/{collection_id}"
    payload, headers = client.request_json_with_headers(endpoint, {})
    collection = ensure_collection(payload, collection_id)
    record = cellxgene_collection_record(
        collection,
        max_datasets=max_datasets,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "cellxgene",
        "query": collection_id,
        "returned": 1,
        "collection": collection_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def cellxgene_collections_search(args: JsonObject, client: CellxGeneClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    max_results = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)
    max_datasets = optional_int(args, "max_datasets", default=DEFAULT_DATASETS, minimum=1, maximum=MAX_DATASETS)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = "collections"
    payload, headers = client.request_json_with_headers(endpoint, {})
    rows = collection_list(payload)
    matches = filter_collections(rows, query)[:max_results]
    records = [
        cellxgene_collection_record(row, max_datasets=max_datasets, website_base_url=client.config.website_base_url, api_base_url=client.config.base_url)
        for row in matches
    ]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "cellxgene",
        "query": query,
        "returned": len(records),
        "searched_collections": len(rows),
        "search_note": "CELLxGENE Discover does not expose a compact full-text search endpoint here; results are filtered locally from the public collections metadata list.",
        "collections": [collection_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = matches
    return response


def cellxgene_collection_assets(args: JsonObject, client: CellxGeneClient) -> JsonObject:
    collection_id = require_uuid(args, "collection_id")
    max_datasets = optional_int(args, "max_datasets", default=DEFAULT_DATASETS, minimum=1, maximum=MAX_DATASETS)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"collections/{collection_id}"
    payload, headers = client.request_json_with_headers(endpoint, {})
    collection = ensure_collection(payload, collection_id)
    record = cellxgene_assets_download_plan_record(
        collection,
        max_datasets=max_datasets,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "cellxgene",
        "query": collection_id,
        "returned": len(record["data"]["assets"]),
        "assets": record["data"]["assets"],
        "records": [record],
        "source": source_with_headers(endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def ensure_collection(payload: object, collection_id: str) -> JsonObject:
    if isinstance(payload, dict) and payload.get("collection_id"):
        return payload
    raise CellxGeneError(f"CELLxGENE collection not found for {collection_id}")


def collection_list(payload: object) -> list[JsonObject]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("collections"), list):
        return [item for item in payload["collections"] if isinstance(item, dict)]
    return []


def filter_collections(rows: list[JsonObject], query: str) -> list[JsonObject]:
    terms = [term for term in normalize_space(query).lower().split() if term]
    if not terms:
        return []
    scored = []
    for row in rows:
        haystack = collection_haystack(row)
        if all(term in haystack for term in terms):
            scored.append((score_collection(row, terms), row))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [row for _score, row in scored]


def collection_haystack(row: JsonObject) -> str:
    parts = [
        row.get("collection_id"),
        row.get("name"),
        row.get("description"),
        row.get("doi"),
        row.get("contact_name"),
        " ".join(str(item) for item in row.get("consortia", []) if item),
    ]
    publisher = row.get("publisher_metadata") if isinstance(row.get("publisher_metadata"), dict) else {}
    parts.append(publisher.get("journal"))
    for author in publisher.get("authors", []) if isinstance(publisher.get("authors"), list) else []:
        if isinstance(author, dict):
            parts.extend([author.get("name"), author.get("given"), author.get("family")])
    for dataset in row.get("datasets", []) if isinstance(row.get("datasets"), list) else []:
        if not isinstance(dataset, dict):
            continue
        parts.append(dataset.get("title"))
        for key in ("assay", "cell_type", "disease", "organism", "tissue"):
            for term in dataset.get(key, []) if isinstance(dataset.get(key), list) else []:
                if isinstance(term, dict):
                    parts.extend([term.get("label"), term.get("ontology_term_id")])
        parts.extend(dataset.get("suspension_type", []) if isinstance(dataset.get("suspension_type"), list) else [])
    return " ".join(normalize_space(part).lower() for part in parts if part)


def score_collection(row: JsonObject, terms: list[str]) -> int:
    title = normalize_space(row.get("name")).lower()
    description = normalize_space(row.get("description")).lower()
    score = 0
    for term in terms:
        if term in title:
            score += 10
        if term in description:
            score += 2
    score += len(row.get("datasets", [])) if isinstance(row.get("datasets"), list) else 0
    return score


def collection_summary(record: JsonObject) -> JsonObject:
    data = record["data"]
    return {
        "collection_id": data["collection_id"],
        "name": data["name"],
        "dataset_count": data["dataset_count"],
        "cell_count": data["cell_count"],
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
            "name": "cellxgene_collection_lookup",
            "title": "Look up a CELLxGENE Discover collection",
            "description": "Fetch one public CELLxGENE Discover collection by UUID and return a front-end-compatible project record with dataset, ontology, publication, explorer, and asset metadata.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "collection_id": {"type": "string", "description": "CELLxGENE collection UUID."},
                    "max_datasets": {"type": "integer", "minimum": 1, "maximum": MAX_DATASETS, "default": DEFAULT_DATASETS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["collection_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "cellxgene_collections_search",
            "title": "Search CELLxGENE Discover collections",
            "description": "Filter public CELLxGENE Discover collection metadata by keywords and return bounded front-end-compatible project records.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword query across collection names, descriptions, authors, organisms, tissues, diseases, assays, and ontology IDs."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "max_datasets": {"type": "integer", "minimum": 1, "maximum": MAX_DATASETS, "default": DEFAULT_DATASETS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "cellxgene_collection_assets",
            "title": "Build a CELLxGENE collection asset manifest",
            "description": "Fetch one CELLxGENE collection and return a metadata-only H5AD asset download-plan record. No file transfer is started.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "collection_id": {"type": "string", "description": "CELLxGENE collection UUID."},
                    "max_datasets": {"type": "integer", "minimum": 1, "maximum": MAX_DATASETS, "default": DEFAULT_DATASETS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["collection_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "cellxgene_status",
            "title": "Inspect CELLxGENE MCP status",
            "description": "Return configured CELLxGENE MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
    ]


TOOL_HANDLERS = {
    "cellxgene_collection_lookup": cellxgene_collection_lookup,
    "cellxgene_collections_search": cellxgene_collections_search,
    "cellxgene_collection_assets": cellxgene_collection_assets,
    "cellxgene_status": cellxgene_status,
}

