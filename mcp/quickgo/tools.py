"""MCP tool registry for the QuickGO server."""

from __future__ import annotations

from mcp.dynamic_context import build_dynamic_context_response
from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition
from .client import QuickGoClient
from .constants import DEFAULT_RESULTS, MAX_RELATIONS, MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import McpError, QuickGoError
from .records import quickgo_annotation_dataset_record, quickgo_term_record
from .utils import (
    normalize_space,
    optional_bool,
    optional_go_id,
    optional_int,
    optional_string,
    require_go_id,
    require_non_empty_string,
    source_info,
)


QUICKGO_CONTEXT_TYPES = ["all", "terms", "annotations", "evidence", "taxon", "aspects"]
QUICKGO_CONTEXT_SCHEMA_VERSION = "bioinformatics.dynamic_context.v1"
QUICKGO_EVIDENCE_HINTS = [
    ("ECO:0000269", "manual assertion"),
    ("ECO:0000314", "direct assay evidence"),
    ("ECO:0000315", "mutant phenotype evidence"),
    ("ECO:0000501", "IEA automatic assertion"),
]
QUICKGO_TAXON_HINTS = [
    ("9606", "Homo sapiens"),
    ("10090", "Mus musculus"),
    ("10116", "Rattus norvegicus"),
]
QUICKGO_ASPECT_HINTS = [
    ("biological_process", "Biological process"),
    ("molecular_function", "Molecular function"),
    ("cellular_component", "Cellular component"),
]


def quickgo_status(args: JsonObject, client: QuickGoClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "quickgo",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "website_base_url": client.config.website_base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["gene_ontology", "gene_ontology_annotation"],
        "tool_groups": {
            "context": ["quickgo_parameter_domains", "quickgo_resolve_context"],
            "ontology": ["quickgo_term_lookup", "quickgo_term_search", "quickgo_term_children"],
            "annotations": ["quickgo_annotation_search"],
            "status": ["quickgo_status"],
        },
        "frontend_components": ["ontology_term", "dataset"],
        "preview_kinds": ["table", "network", "xref_groups"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload, headers = client.request_json_with_headers("ontology/go/terms/GO:0008150", {})
        rows = results(payload)
        status["network_check"] = {
            "ok": True,
            "returned": len(rows),
            "example_go_id": rows[0].get("id") if rows else None,
            "example_name": rows[0].get("name") if rows else None,
            "content_type": headers.get("content-type"),
        }
    return status


def quickgo_resolve_context(args: JsonObject, client: QuickGoClient) -> JsonObject:
    context_type = optional_context_type(args, "context_type", allowed=QUICKGO_CONTEXT_TYPES, default="all")
    query = optional_string(args, "query")
    go_id = optional_go_id(args, "go_id")
    gene_product_id = optional_string(args, "gene_product_id")
    taxon_id = optional_string(args, "taxon_id")
    evidence_code = optional_string(args, "evidence_code")
    max_results = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    contexts = static_quickgo_contexts()
    recommended_calls: list[JsonObject] = []
    sources: list[JsonObject] = []
    raw: JsonObject = {}

    if go_id:
        result = quickgo_term_lookup({"go_id": go_id, "include_raw": include_raw}, client)
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(quickgo_term_context(record) for record in records)
        recommended_calls.extend(quickgo_recommended_calls(record) for record in records)
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["lookup"] = result["raw"]

    if query:
        result = quickgo_term_search(
            {"query": query, "max_results": max_results, "include_raw": include_raw},
            client,
        )
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(quickgo_term_context(record) for record in records)
        recommended_calls.extend(quickgo_recommended_calls(record) for record in records[:3])
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["search"] = result["raw"]

    annotation_filters = {
        "gene_product_id": gene_product_id,
        "go_id": go_id,
        "taxon_id": taxon_id,
        "evidence_code": evidence_code,
        "max_results": max_results,
        "include_raw": include_raw,
    }
    if any([gene_product_id, go_id, taxon_id, evidence_code]) and context_type in {"all", "annotations"}:
        result = quickgo_annotation_search(annotation_filters, client)
        annotations = result.get("annotations") if isinstance(result.get("annotations"), list) else []
        contexts.extend(quickgo_annotation_context(row) for row in annotations if isinstance(row, dict))
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["annotations"] = result["raw"]

    filtered_contexts = [
        context
        for context in contexts
        if quickgo_context_matches(context, context_type=context_type, query=query or go_id or gene_product_id or evidence_code or taxon_id)
    ]
    return build_dynamic_context_response(
        schema_version=RESULT_SCHEMA_VERSION,
        context_schema_version=QUICKGO_CONTEXT_SCHEMA_VERSION,
        database="quickgo",
        query={
            "context_type": context_type,
            "query": query,
            "go_id": go_id,
            "gene_product_id": gene_product_id,
            "taxon_id": taxon_id,
            "evidence_code": evidence_code,
        },
        contexts=filtered_contexts,
        recommended_calls=recommended_calls,
        max_results=max_results,
        fallback_source=source_info("resolve_context", {"context_type": context_type, "query": query, "go_id": go_id}),
        sources=sources,
        entity_groups={"terms", "annotations"},
        raw=raw,
        summary_fields={"terms": lambda context: context.get("group") == "terms"},
        include_raw=include_raw,
    )


def quickgo_term_lookup(args: JsonObject, client: QuickGoClient) -> JsonObject:
    go_id = require_go_id(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"ontology/go/terms/{go_id}"
    payload, headers = client.request_json_with_headers(endpoint, {})
    term = first_result(payload)
    record = quickgo_term_record(
        term,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "quickgo",
        "query": go_id,
        "returned": 1,
        "term": term_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def quickgo_term_search(args: JsonObject, client: QuickGoClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    max_results = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    params: JsonObject = {"query": query, "limit": max_results, "page": 1}
    endpoint = "ontology/go/search"
    payload, headers = client.request_json_with_headers(endpoint, params)
    rows = results(payload)[:max_results]
    records = [
        quickgo_term_record(row, website_base_url=client.config.website_base_url, api_base_url=client.config.base_url)
        for row in rows
    ]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "quickgo",
        "query": query,
        "returned": len(records),
        "total": total_hits(payload),
        "terms": [term_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def quickgo_term_children(args: JsonObject, client: QuickGoClient) -> JsonObject:
    go_id = require_go_id(args)
    max_children = optional_int(args, "max_children", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RELATIONS)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"ontology/go/terms/{go_id}/children"
    payload, headers = client.request_json_with_headers(endpoint, {})
    parent = first_result(payload)
    child_rows = parent.get("children") if isinstance(parent.get("children"), list) else []
    records = [
        quickgo_term_record(
            row,
            relation=str(row.get("relation") or ""),
            parent_id=go_id,
            website_base_url=client.config.website_base_url,
            api_base_url=client.config.base_url,
        )
        for row in child_rows[:max_children]
        if isinstance(row, dict)
    ]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "quickgo",
        "query": go_id,
        "returned": len(records),
        "total": len(child_rows),
        "parent": {"id": parent.get("id"), "name": parent.get("name")},
        "terms": [term_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def quickgo_annotation_search(args: JsonObject, client: QuickGoClient) -> JsonObject:
    gene_product_id = optional_string(args, "gene_product_id")
    go_id = optional_go_id(args, "go_id")
    taxon_id = optional_string(args, "taxon_id")
    evidence_code = optional_string(args, "evidence_code")
    max_results = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    if not any([gene_product_id, go_id, taxon_id, evidence_code]):
        raise McpError(-32602, "Provide at least one of gene_product_id, go_id, taxon_id, or evidence_code")
    params: JsonObject = {"limit": max_results, "page": 1}
    if gene_product_id:
        params["geneProductId"] = gene_product_id
    if go_id:
        params["goId"] = go_id
    if taxon_id:
        params["taxonId"] = taxon_id
    if evidence_code:
        params["evidenceCode"] = evidence_code
    endpoint = "annotation/search"
    payload, headers = client.request_json_with_headers(endpoint, params)
    rows = results(payload)[:max_results]
    record = quickgo_annotation_dataset_record(
        rows,
        query=params,
        total=total_hits(payload),
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "quickgo",
        "query": record["label"],
        "returned": len(rows),
        "total": total_hits(payload),
        "annotations": record["data"]["annotations"],
        "records": [record],
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def results(payload: object) -> list[JsonObject]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get("results")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def first_result(payload: object) -> JsonObject:
    rows = results(payload)
    if not rows:
        raise QuickGoError("QuickGO response did not contain a result")
    return rows[0]


def total_hits(payload: object) -> int:
    if not isinstance(payload, dict):
        return 0
    value = payload.get("numberOfHits")
    try:
        return int(value)
    except (TypeError, ValueError):
        return len(results(payload))


def term_summary(record: JsonObject) -> JsonObject:
    data = record["data"]
    return {
        "id": data["id"],
        "name": data["name"],
        "aspect": data["aspect_label"],
        "url": data["url"],
    }


def source_with_headers(endpoint: str, params: JsonObject, headers: dict[str, str]) -> JsonObject:
    source = source_info(endpoint, params)
    if headers.get("content-type"):
        source["content_type"] = headers["content-type"]
    return source


def optional_context_type(args: JsonObject, name: str, *, allowed: list[str], default: str) -> str:
    value = optional_string(args, name, default=default)
    if value not in allowed:
        raise McpError(-32602, f"{name} must be one of: {', '.join(allowed)}")
    return value


def static_quickgo_contexts() -> list[JsonObject]:
    contexts: list[JsonObject] = [
        quickgo_parameter_context(
            "context_type",
            value,
            label=value,
            description="Dynamic QuickGO context family to resolve before GO term lookup or annotation search.",
            kind="enum",
            group="context_types",
            url="",
            metadata={"context_type": value},
        )
        for value in QUICKGO_CONTEXT_TYPES
    ]
    contexts.extend(
        quickgo_parameter_context(
            "evidence_code",
            code,
            label=label,
            description="Common ECO evidence-code filter for quickgo_annotation_search.",
            kind="evidence_code",
            group="evidence",
            url=f"https://www.ebi.ac.uk/QuickGO/term/{code}",
            metadata={"evidence_code": code, "label": label},
        )
        for code, label in QUICKGO_EVIDENCE_HINTS
    )
    contexts.extend(
        quickgo_parameter_context(
            "taxon_id",
            taxid,
            label=name,
            description="Common NCBI TaxID filter for QuickGO annotations.",
            kind="taxon",
            group="taxon",
            url=f"https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id={taxid}",
            metadata={"taxon_id": taxid, "scientific_name": name},
        )
        for taxid, name in QUICKGO_TAXON_HINTS
    )
    contexts.extend(
        quickgo_parameter_context(
            "aspect",
            aspect,
            label=label,
            description="Gene Ontology aspect used for display and filtering decisions.",
            kind="aspect",
            group="aspects",
            url="",
            metadata={"aspect": aspect, "label": label},
        )
        for aspect, label in QUICKGO_ASPECT_HINTS
    )
    return contexts


def quickgo_term_context(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    go_id = normalize_space(data.get("id") or record.get("id"))
    title = normalize_space(record.get("title") or data.get("name") or go_id)
    return quickgo_parameter_context(
        "go_id",
        go_id,
        label=title,
        description=normalize_space(record.get("description") or data.get("definition_text") or "Gene Ontology term."),
        kind="go_term",
        group="terms",
        url=normalize_space(record.get("url") or data.get("url")),
        metadata={
            "go_id": go_id,
            "name": title,
            "aspect": data.get("aspect_label", ""),
            "is_obsolete": data.get("is_obsolete", False),
            "synonym_count": len(data.get("synonyms", [])) if isinstance(data.get("synonyms"), list) else 0,
        },
    )


def quickgo_annotation_context(row: JsonObject) -> JsonObject:
    gene_product_id = normalize_space(row.get("gene_product_id"))
    go_id = normalize_space(row.get("go_id"))
    label = normalize_space(row.get("symbol") or gene_product_id or go_id)
    return quickgo_parameter_context(
        "gene_product_id",
        gene_product_id,
        label=label,
        description="QuickGO annotation evidence row that can seed a narrower annotation search.",
        kind="annotation",
        group="annotations",
        url=normalize_space(row.get("go_url") or row.get("reference_url")),
        metadata={
            "gene_product_id": gene_product_id,
            "go_id": go_id,
            "symbol": row.get("symbol", ""),
            "evidence_code": row.get("evidence_code", ""),
            "taxon_id": row.get("taxon_id", ""),
            "reference": row.get("reference", ""),
        },
    )


def quickgo_parameter_context(
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
            "component": "ontology_term" if group != "annotations" else "dataset",
            "chip_label": parameter_name,
            "icon": "quickgo",
            "title": label,
            "subtitle": f"{parameter_name}: {value}",
            "description": description,
            "metadata": display_fields,
            "badges": [
                {"label": "QuickGO", "kind": "source"},
                {"label": parameter_name, "kind": "parameter"},
            ],
            "actions": [{"label": "Open source", "url": url, "kind": "external", "primary": True}] if url else [],
            "hover": {"title": label, "subtitle": f"{parameter_name}: {value}", "icon": "quickgo", "fields": display_fields},
            "primary_url": url,
        },
    }


def quickgo_recommended_calls(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    go_id = normalize_space(data.get("id") or record.get("id"))
    return {
        "tool_name": "quickgo_term_lookup",
        "arguments": {"go_id": go_id},
        "reason": "Fetch detailed GO term metadata, relation previews, synonyms, and cross-references.",
    }


def quickgo_context_matches(context: JsonObject, *, context_type: str, query: str) -> bool:
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
    return query.lower() in haystack or context.get("group") in {"terms", "annotations"}


def tool_definitions() -> list[JsonObject]:
    return [
        parameter_domains_tool_definition("quickgo_parameter_domains"),
        {
            "name": "quickgo_resolve_context",
            "title": "Resolve QuickGO dynamic parameter context",
            "description": (
                "Resolve GO IDs, text-search term candidates, annotation filter hints, evidence codes, and TaxID values "
                "before calling QuickGO lookup or annotation tools."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "context_type": {"type": "string", "enum": QUICKGO_CONTEXT_TYPES, "default": "all"},
                    "query": {"type": "string", "description": "Optional GO term text query such as apoptosis."},
                    "go_id": {"type": "string", "description": "Optional GO ID such as GO:0006915."},
                    "gene_product_id": {"type": "string", "description": "Optional gene product ID such as UniProtKB:P04637."},
                    "taxon_id": {"type": ["integer", "string"], "description": "Optional NCBI TaxID filter such as 9606."},
                    "evidence_code": {"type": "string", "description": "Optional ECO evidence code such as ECO:0000315."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "quickgo_term_lookup",
            "title": "Look up a Gene Ontology term in QuickGO",
            "description": "Fetch one GO term by GO ID and return an ontology-term record with definition, synonyms, relations, xrefs, previews, and links.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "go_id": {"type": "string", "description": "GO ID, for example GO:0006915."},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["go_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "quickgo_term_search",
            "title": "Search Gene Ontology terms in QuickGO",
            "description": "Search GO terms by text and return front-end-compatible ontology-term records.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Term search text, for example apoptosis."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "quickgo_annotation_search",
            "title": "Search QuickGO annotation evidence",
            "description": "Search GO annotation rows by gene product, GO ID, taxon, or evidence code and return a dataset record with a bounded evidence table.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "gene_product_id": {"type": "string", "description": "Gene product ID, for example UniProtKB:P04637."},
                    "go_id": {"type": "string", "description": "Optional GO ID filter, for example GO:0008285."},
                    "taxon_id": {"type": ["integer", "string"], "description": "Optional NCBI TaxID filter, for example 9606."},
                    "evidence_code": {"type": "string", "description": "Optional ECO code filter, for example ECO:0000315."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "quickgo_term_children",
            "title": "List child GO terms in QuickGO",
            "description": "Fetch child terms for one GO ID and return bounded ontology-term records with relation metadata and links.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "go_id": {"type": "string", "description": "Parent GO ID, for example GO:0006915."},
                    "max_children": {"type": "integer", "minimum": 1, "maximum": MAX_RELATIONS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["go_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "quickgo_status",
            "title": "Inspect QuickGO MCP status",
            "description": "Return configured QuickGO MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
    ]


TOOL_HANDLERS = {
    "quickgo_parameter_domains": make_parameter_domains_handler("quickgo", "quickgo_parameter_domains", tool_definitions),
    "quickgo_resolve_context": quickgo_resolve_context,
    "quickgo_term_lookup": quickgo_term_lookup,
    "quickgo_term_search": quickgo_term_search,
    "quickgo_annotation_search": quickgo_annotation_search,
    "quickgo_term_children": quickgo_term_children,
    "quickgo_status": quickgo_status,
}
