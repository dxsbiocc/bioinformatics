"""MCP tool registry for the ClinVar server."""

from __future__ import annotations

from collections.abc import Callable

from mcp.dynamic_context import build_dynamic_context_response
from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition

from .client import ClinvarClient
from .constants import MAX_IDS_PER_SUMMARY, MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import ClinvarError, McpError
from .records import clinvar_variant_record
from .utils import (
    clinvar_uid,
    normalize_space,
    optional_bool,
    optional_int,
    require_non_empty_string,
    source_info,
)

CLINVAR_CONTEXT_TYPES = ["all", "variants", "clinical_significance", "genes", "identifiers"]
CLINVAR_CONTEXT_SCHEMA_VERSION = "bioinformatics.dynamic_context.v1"
CLINVAR_SIGNIFICANCE_HINTS = [
    "Pathogenic",
    "Likely pathogenic",
    "Uncertain significance",
    "Likely benign",
    "Benign",
    "Conflicting classifications of pathogenicity",
]


def clinvar_status(args: JsonObject, client: ClinvarClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "clinvar",
        "version": "0.1.0",
        "clinical_tables_url": client.config.clinical_tables_url,
        "eutils_base_url": client.config.eutils_base_url,
        "tool": client.config.tool,
        "email_configured": bool(client.config.email),
        "api_key_configured": bool(client.config.api_key),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["clinvar"],
        "tool_groups": {
            "context": ["clinvar_parameter_domains", "clinvar_resolve_context"],
            "variation": ["clinvar_lookup", "clinvar_search"],
            "status": ["clinvar_status"],
        },
        "frontend_components": ["variant"],
        "preview_kinds": ["table", "xref_groups"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload, _headers = client.request_eutils_json_with_headers(
            "esummary.fcgi",
            {"db": "clinvar", "id": "37390"},
        )
        item = first_esummary_item(payload)
        status["network_check"] = {
            "ok": True,
            "uid": item.get("uid"),
            "accession": item.get("accession"),
        }
    return status


def clinvar_resolve_context(args: JsonObject, client: ClinvarClient) -> JsonObject:
    context_type = optional_context_type(args, "context_type", allowed=CLINVAR_CONTEXT_TYPES, default="all")
    query = optional_string(args, "query")
    identifier = optional_string(args, "identifier")
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_RESULTS)
    hydrate = optional_bool(args, "hydrate", default=True)
    include_raw = optional_bool(args, "include_raw", default=False)
    contexts = static_clinvar_contexts()
    recommended_calls: list[JsonObject] = []
    sources: list[JsonObject] = []
    raw: JsonObject = {}

    if identifier:
        result = clinvar_lookup({"identifier": identifier, "include_raw": include_raw}, client)
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(clinvar_record_context(record) for record in records)
        for record in records:
            recommended_calls.extend(clinvar_recommended_calls(record))
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["lookup"] = result["raw"]

    if query:
        result = clinvar_search(
            {
                "terms": query,
                "max_results": max_results,
                "hydrate": hydrate,
                "include_raw": include_raw,
            },
            client,
        )
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(clinvar_record_context(record) for record in records)
        for record in records[:3]:
            recommended_calls.extend(clinvar_recommended_calls(record))
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["search"] = result["raw"]

    filtered_contexts = [
        context
        for context in contexts
        if clinvar_context_matches(context, context_type=context_type, query=query or identifier)
    ]
    return build_dynamic_context_response(
        schema_version=RESULT_SCHEMA_VERSION,
        context_schema_version=CLINVAR_CONTEXT_SCHEMA_VERSION,
        database="clinvar",
        query={
            "context_type": context_type,
            "query": query,
            "identifier": identifier,
            "hydrate": hydrate,
        },
        contexts=filtered_contexts,
        recommended_calls=recommended_calls,
        max_results=max_results,
        fallback_source=source_info("resolve_context", {"context_type": context_type, "query": query, "identifier": identifier}),
        sources=sources,
        entity_groups={"variants"},
        raw=raw,
        summary_fields={"variants": lambda context: context.get("group") == "variants"},
        include_raw=include_raw,
    )


def clinvar_lookup(args: JsonObject, client: ClinvarClient) -> JsonObject:
    identifier = require_non_empty_string(args, "identifier")
    uid = clinvar_uid(identifier)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = "esummary.fcgi"
    params: JsonObject = {"db": "clinvar", "id": uid}
    payload, headers = client.request_eutils_json_with_headers(endpoint, params)
    item = first_esummary_item(payload)
    if not item:
        raise ClinvarError(f"ClinVar record not found for {identifier}")
    record = clinvar_variant_record(item)
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "clinvar",
        "query": identifier,
        "returned": 1,
        "variant": variant_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def clinvar_search(args: JsonObject, client: ClinvarClient) -> JsonObject:
    terms = require_non_empty_string(args, "terms")
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_RESULTS)
    hydrate = optional_bool(args, "hydrate", default=True)
    include_raw = optional_bool(args, "include_raw", default=False)
    params: JsonObject = {"terms": terms, "maxList": max_results}
    search_payload, search_headers = client.request_clinical_tables_with_headers(params)
    if not isinstance(search_payload, list) or len(search_payload) < 4:
        raise ClinvarError("Clinical Tables response did not match expected list shape")
    total = search_payload[0] if isinstance(search_payload[0], int) else 0
    identifiers = search_payload[1] if isinstance(search_payload[1], list) else []
    display_rows = search_payload[3] if isinstance(search_payload[3], list) else []
    labels = display_row_labels(display_rows)
    records: list[JsonObject] = []
    summaries: list[JsonObject] = []
    if hydrate and identifiers:
        ids = [clinvar_uid(item) for item in identifiers[: min(max_results, MAX_IDS_PER_SUMMARY)]]
        summary_payload, _summary_headers = client.request_eutils_json_with_headers(
            "esummary.fcgi",
            {"db": "clinvar", "id": ",".join(ids)},
        )
        summaries = esummary_items(summary_payload)
        label_by_uid = {
            clinvar_uid(uid): labels[index]
            for index, uid in enumerate(identifiers)
            if index < len(labels)
        }
        records = [
            clinvar_variant_record(item, search_label=label_by_uid.get(clinvar_uid(item.get("uid")), ""))
            for item in summaries
        ]
    else:
        records = [clinical_tables_record(uid, labels[index] if index < len(labels) else "") for index, uid in enumerate(identifiers[:max_results])]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "clinvar",
        "query": terms,
        "returned": len(records),
        "total": total,
        "truncated": total > len(records),
        "identifiers": identifiers[:max_results],
        "records": records,
        "source": source_with_headers("clinicaltables/search", params, search_headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = search_payload
    return response


def first_esummary_item(payload: JsonObject) -> JsonObject:
    items = esummary_items(payload)
    return items[0] if items else {}


def esummary_items(payload: JsonObject) -> list[JsonObject]:
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    uids = result.get("uids") if isinstance(result.get("uids"), list) else []
    items = []
    for uid in uids:
        item = result.get(str(uid))
        if isinstance(item, dict):
            items.append(item)
    return items


def display_row_labels(rows: object) -> list[str]:
    labels = []
    if not isinstance(rows, list):
        return labels
    for row in rows:
        if isinstance(row, list) and len(row) > 1:
            labels.append(normalize_space(row[1]))
        else:
            labels.append(normalize_space(row))
    return labels


def clinical_tables_record(uid: object, label: str) -> JsonObject:
    uid_text = clinvar_uid(uid)
    item: JsonObject = {
        "uid": uid_text,
        "title": label or uid_text,
        "accession": f"VCV{int(uid_text):09d}" if uid_text.isdigit() else "",
        "variation_set": [{"variation_name": label}],
    }
    return clinvar_variant_record(item, search_label=label)


def variant_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "uid": normalize_space(data.get("uid")),
        "accession": normalize_space(data.get("accession")),
        "title": normalize_space(data.get("title")),
        "classification": normalize_space(data.get("classification")),
        "gene": normalize_space(data.get("primary_gene")),
        "location": normalize_space(data.get("primary_location")),
        "url": normalize_space(data.get("url")),
    }


def source_with_headers(endpoint: str, params: JsonObject, headers: dict[str, str]) -> JsonObject:
    source = source_info(endpoint, params)
    content_type = headers.get("content-type")
    if content_type:
        source["content_type"] = content_type
    return source


def optional_string(args: JsonObject, name: str, *, default: str = "") -> str:
    value = args.get(name, default)
    if value is None:
        return default
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if not isinstance(value, str):
        raise McpError(-32602, f"{name} must be a string")
    return value.strip()


def optional_context_type(args: JsonObject, name: str, *, allowed: list[str], default: str) -> str:
    value = optional_string(args, name, default=default)
    if value not in allowed:
        raise McpError(-32602, f"{name} must be one of: {', '.join(allowed)}")
    return value


def static_clinvar_contexts() -> list[JsonObject]:
    contexts: list[JsonObject] = [
        clinvar_parameter_context(
            "context_type",
            value,
            label=value,
            description="Dynamic ClinVar context family to resolve before variation lookup or search.",
            kind="enum",
            group="context_types",
            url="",
            metadata={"context_type": value},
        )
        for value in CLINVAR_CONTEXT_TYPES
    ]
    contexts.extend(
        clinvar_parameter_context(
            "classification",
            value,
            label=value,
            description="Common ClinVar clinical significance phrase to use in search or UI filters.",
            kind="clinical_significance",
            group="clinical_significance",
            url="https://www.ncbi.nlm.nih.gov/clinvar/",
            metadata={"classification": value},
        )
        for value in CLINVAR_SIGNIFICANCE_HINTS
    )
    contexts.extend(
        [
            clinvar_parameter_context(
                "identifier",
                "VCV000037390",
                label="VCV accession",
                description="ClinVar variation accession format accepted by clinvar_lookup.",
                kind="identifier_format",
                group="identifiers",
                url="https://www.ncbi.nlm.nih.gov/clinvar/variation/37390/",
                metadata={"example": "VCV000037390", "normalized_uid": "37390"},
            ),
            clinvar_parameter_context(
                "identifier",
                "37390",
                label="ClinVar numeric UID",
                description="Numeric ClinVar variation UID accepted by clinvar_lookup.",
                kind="identifier_format",
                group="identifiers",
                url="https://www.ncbi.nlm.nih.gov/clinvar/variation/37390/",
                metadata={"example": "37390"},
            ),
        ]
    )
    return contexts


def clinvar_record_context(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    uid = normalize_space(data.get("uid") or record.get("id"))
    accession = normalize_space(data.get("accession") or record.get("stable_id"))
    label = normalize_space(record.get("title") or accession or uid)
    return clinvar_parameter_context(
        "identifier",
        accession or uid,
        label=label,
        description=normalize_space(record.get("description") or data.get("classification") or "ClinVar variation record."),
        kind="variant",
        group="variants",
        url=normalize_space(record.get("url") or data.get("url")),
        metadata={
            "uid": uid,
            "accession": accession,
            "classification": data.get("classification", ""),
            "review_status": data.get("review_status", ""),
            "primary_gene": data.get("primary_gene", ""),
            "primary_location": data.get("primary_location", ""),
            "variant_type": data.get("variant_type", ""),
        },
    )


def clinvar_parameter_context(
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
            "component": "variant",
            "chip_label": parameter_name,
            "icon": "clinvar",
            "title": label,
            "subtitle": f"{parameter_name}: {value}",
            "description": description,
            "metadata": display_fields,
            "badges": [
                {"label": "ClinVar", "kind": "source"},
                {"label": parameter_name, "kind": "parameter"},
            ],
            "actions": [{"label": "Open source", "url": url, "kind": "external", "primary": True}] if url else [],
            "hover": {"title": label, "subtitle": f"{parameter_name}: {value}", "icon": "clinvar", "fields": display_fields},
            "primary_url": url,
        },
    }


def clinvar_recommended_calls(record: JsonObject) -> list[JsonObject]:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    identifier = normalize_space(data.get("accession") or data.get("uid") or record.get("id"))
    calls: list[JsonObject] = [
        {"tool_name": "clinvar_lookup", "arguments": {"identifier": identifier}, "reason": "Fetch detailed ClinVar variation metadata, clinical significance, submissions, and cross-references."}
    ]
    primary_gene = normalize_space(data.get("primary_gene"))
    if primary_gene:
        calls.append({"server": "ncbi", "tool_name": "gene_search", "arguments": {"term": primary_gene}, "reason": "Open NCBI Gene context for the primary gene."})
    xrefs = data.get("xrefs")
    if isinstance(xrefs, list):
        for xref in xrefs:
            if isinstance(xref, dict) and normalize_space(xref.get("database")).lower() == "dbsnp" and xref.get("label"):
                calls.append({"server": "ensembl", "tool_name": "ensembl_variation", "arguments": {"species": "homo_sapiens", "variant_id": normalize_space(xref["label"])}, "reason": "Open Ensembl variant context for the linked dbSNP identifier."})
    return calls


def clinvar_context_matches(context: JsonObject, *, context_type: str, query: str) -> bool:
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
    return query.lower() in haystack or context.get("group") == "variants"


def tool_definitions() -> list[JsonObject]:
    read_only_annotations = {
        "readOnlyHint": True,
        "openWorldHint": True,
    }
    return [
        parameter_domains_tool_definition("clinvar_parameter_domains"),
        {
            "name": "clinvar_resolve_context",
            "title": "Resolve ClinVar dynamic parameter context",
            "description": (
                "Resolve ClinVar query terms, VCV/numeric identifiers, clinical-significance hints, and variant candidates "
                "before calling lookup/search tools. Returns front-end-friendly context rows and recommended calls."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "context_type": {"type": "string", "enum": CLINVAR_CONTEXT_TYPES, "default": "all"},
                    "query": {"type": "string", "description": "Optional ClinVar search terms such as BRCA1."},
                    "identifier": {"type": "string", "description": "Optional ClinVar UID or VCV accession such as VCV000037390."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": 10},
                    "hydrate": {"type": "boolean", "default": True},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "clinvar_lookup",
            "title": "Look up a ClinVar VCV/variation record",
            "description": (
                "Fetch one ClinVar variation by numeric UID or VCV accession "
                "and return a front-end-compatible variant record."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "ClinVar UID or VCV accession, for example 37390 or VCV000037390.",
                    },
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["identifier"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "clinvar_search",
            "title": "Search ClinVar variants",
            "description": (
                "Search ClinVar via NLM Clinical Tables, optionally hydrate "
                "top hits through NCBI ClinVar ESummary, and return variant records."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "terms": {"type": "string", "description": "Search terms such as BRCA1 or VCV000037390."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": 10},
                    "hydrate": {"type": "boolean", "default": True},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["terms"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "clinvar_status",
            "title": "Inspect ClinVar MCP status",
            "description": "Return configured ClinVar MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
    ]


TOOL_HANDLERS: dict[str, Callable[[JsonObject, ClinvarClient], JsonObject]] = {
    "clinvar_parameter_domains": make_parameter_domains_handler("clinvar", "clinvar_parameter_domains", tool_definitions),
    "clinvar_resolve_context": clinvar_resolve_context,
    "clinvar_lookup": clinvar_lookup,
    "clinvar_search": clinvar_search,
    "clinvar_status": clinvar_status,
}
