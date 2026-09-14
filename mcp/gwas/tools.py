"""MCP tool registry for the GWAS Catalog server."""

from __future__ import annotations

from collections.abc import Callable

from mcp.dynamic_context import build_dynamic_context_response
from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition

from .client import GwasClient
from .constants import MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import GwasError, McpError
from .records import gwas_gene_record, gwas_trait_record, gwas_variant_record
from .utils import normalize_space, optional_bool, optional_int, require_non_empty_string, source_info

GWAS_CONTEXT_TYPES = ["all", "variants", "genes", "traits", "evidence"]
GWAS_CONTEXT_SCHEMA_VERSION = "bioinformatics.dynamic_context.v1"


def gwas_status(args: JsonObject, client: GwasClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "gwas",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "website_base_url": client.config.website_base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["gwas_catalog"],
        "tool_groups": {
            "context": ["gwas_parameter_domains", "gwas_resolve_context"],
            "variant": ["gwas_variant_lookup"],
            "gene": ["gwas_gene_lookup"],
            "trait": ["gwas_trait_search"],
            "status": ["gwas_status"],
        },
        "frontend_components": ["variant", "gene", "dataset"],
        "preview_kinds": ["table", "citation_list", "xref_groups"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload, _headers = client.request_json_with_headers("metadata", {})
        if not isinstance(payload, dict):
            raise GwasError("GWAS Catalog metadata returned non-object JSON")
        status["network_check"] = {
            "ok": True,
            "title": payload.get("title"),
            "version": payload.get("version"),
            "data_release_date": payload.get("data_release_date"),
            "api_release_date": payload.get("api_release_date"),
            "dbsnp_build": payload.get("dbsnp_build"),
        }
    return status


def gwas_resolve_context(args: JsonObject, client: GwasClient) -> JsonObject:
    context_type = optional_context_type(args, "context_type", allowed=GWAS_CONTEXT_TYPES, default="all")
    query = optional_text(args, "query")
    rs_id = optional_text(args, "rs_id")
    gene = optional_text(args, "gene")
    trait = optional_text(args, "trait")
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    contexts = static_gwas_contexts()
    recommended_calls: list[JsonObject] = []
    sources: list[JsonObject] = []
    raw: JsonObject = {}

    effective_query = query
    if effective_query and effective_query.lower().startswith("rs") and not rs_id:
        rs_id = effective_query
    elif effective_query and not gene and context_type == "genes":
        gene = effective_query
    elif effective_query and not trait and context_type in {"all", "traits", "evidence"}:
        trait = effective_query

    if rs_id:
        result = gwas_variant_lookup({"rs_id": rs_id, "max_results": max_results, "include_raw": include_raw}, client)
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(gwas_record_context(record) for record in records)
        for record in records:
            recommended_calls.extend(gwas_recommended_calls(record))
        sources.extend(source for source in [result.get("snp_source"), result.get("source")] if isinstance(source, dict))
        if include_raw and "raw" in result:
            raw["variant"] = result["raw"]

    if gene:
        result = gwas_gene_lookup({"gene": gene, "max_results": max_results, "include_raw": include_raw}, client)
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(gwas_record_context(record) for record in records)
        for record in records:
            recommended_calls.extend(gwas_recommended_calls(record))
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["gene"] = result["raw"]

    if trait:
        result = gwas_trait_search({"trait": trait, "max_results": max_results, "include_raw": include_raw}, client)
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(gwas_record_context(record) for record in records)
        for record in records:
            recommended_calls.extend(gwas_recommended_calls(record))
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["trait"] = result["raw"]

    query_text = query or rs_id or gene or trait
    filtered_contexts = [
        context
        for context in contexts
        if gwas_context_matches(context, context_type=context_type, query=query_text)
    ]
    return build_dynamic_context_response(
        schema_version=RESULT_SCHEMA_VERSION,
        context_schema_version=GWAS_CONTEXT_SCHEMA_VERSION,
        database="gwas_catalog",
        query={
            "context_type": context_type,
            "query": query,
            "rs_id": rs_id,
            "gene": gene,
            "trait": trait,
        },
        contexts=filtered_contexts,
        recommended_calls=recommended_calls,
        max_results=max_results,
        fallback_source=source_info("resolve_context", {"context_type": context_type, "query": query}),
        sources=sources,
        entity_groups={"variants", "genes", "traits"},
        raw=raw,
        include_raw=include_raw,
        prioritize_entities=True,
        prioritize_same_server_calls=True,
    )


def gwas_variant_lookup(args: JsonObject, client: GwasClient) -> JsonObject:
    rs_id = normalize_rs_id(require_non_empty_string(args, "rs_id"))
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    snp_payload, snp_headers = client.request_json_with_headers(
        f"single-nucleotide-polymorphisms/{rs_id}",
        {},
    )
    if not isinstance(snp_payload, dict):
        raise GwasError(f"GWAS Catalog SNP record not found for {rs_id}")
    association_payload, association_headers = client.request_json_with_headers(
        "associations",
        {"rs_id": rs_id, "size": max_results},
    )
    associations = embedded_list(association_payload, "associations")
    total = page_total(association_payload, len(associations))
    record = gwas_variant_record(
        rs_id=rs_id,
        snp=snp_payload,
        associations=associations,
        total=total,
        max_results=max_results,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "gwas_catalog",
        "query": rs_id,
        "returned": len(associations),
        "total": total,
        "variant": variant_summary(record),
        "records": [record],
        "source": source_with_headers(
            "associations",
            {"rs_id": rs_id, "size": max_results},
            association_headers,
        ),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = {"snp": snp_payload, "associations": association_payload}
    response["snp_source"] = source_with_headers(f"single-nucleotide-polymorphisms/{rs_id}", {}, snp_headers)
    return response


def gwas_gene_lookup(args: JsonObject, client: GwasClient) -> JsonObject:
    gene = require_non_empty_string(args, "gene")
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    params: JsonObject = {"mapped_gene": gene, "size": max_results}
    payload, headers = client.request_json_with_headers("associations", params)
    associations = embedded_list(payload, "associations")
    total = page_total(payload, len(associations))
    record = gwas_gene_record(
        gene=gene,
        associations=associations,
        total=total,
        max_results=max_results,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "gwas_catalog",
        "query": gene,
        "returned": len(associations),
        "total": total,
        "gene": gene_summary(record),
        "records": [record],
        "source": source_with_headers("associations", params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def gwas_trait_search(args: JsonObject, client: GwasClient) -> JsonObject:
    trait = require_non_empty_string(args, "trait")
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    params: JsonObject = {"efo_trait": trait, "size": max_results}
    association_payload, association_headers = client.request_json_with_headers("associations", params)
    study_payload, _study_headers = client.request_json_with_headers("studies", params)
    associations = embedded_list(association_payload, "associations")
    studies = embedded_list(study_payload, "studies")
    association_total = page_total(association_payload, len(associations))
    study_total = page_total(study_payload, len(studies))
    record = gwas_trait_record(
        trait=trait,
        associations=associations,
        studies=studies,
        association_total=association_total,
        study_total=study_total,
        max_results=max_results,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "gwas_catalog",
        "query": trait,
        "returned": len(associations),
        "total": association_total,
        "study_total": study_total,
        "trait": trait_summary(record),
        "records": [record],
        "source": source_with_headers("associations", params, association_headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = {"associations": association_payload, "studies": study_payload}
    return response


def embedded_list(payload: object, key: str) -> list[JsonObject]:
    if not isinstance(payload, dict):
        return []
    embedded = payload.get("_embedded")
    if not isinstance(embedded, dict):
        return []
    value = embedded.get(key)
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def page_total(payload: object, fallback: int) -> int:
    if not isinstance(payload, dict):
        return fallback
    page = payload.get("page")
    if isinstance(page, dict):
        total = page.get("totalElements")
        if isinstance(total, int):
            return total
    return fallback


def normalize_rs_id(value: str) -> str:
    text = value.strip()
    return text if text.lower().startswith("rs") else f"rs{text}"


def variant_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    snp = data.get("snp") if isinstance(data.get("snp"), dict) else {}
    return {
        "rs_id": data.get("rs_id"),
        "location": snp.get("location"),
        "mapped_genes": snp.get("mapped_genes"),
        "associations": data.get("total_associations"),
        "url": data.get("url"),
    }


def gene_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "gene": data.get("gene"),
        "associations": data.get("total_associations"),
        "url": data.get("url"),
    }


def trait_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "trait": data.get("trait"),
        "associations": data.get("total_associations"),
        "studies": data.get("total_studies"),
        "url": data.get("url"),
    }


def source_with_headers(endpoint: str, params: JsonObject, headers: dict[str, str]) -> JsonObject:
    source = source_info(endpoint, params)
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


def static_gwas_contexts() -> list[JsonObject]:
    return [
        gwas_parameter_context(
            "context_type",
            value,
            label=value,
            description="Dynamic GWAS Catalog context family to resolve before variant, gene, or trait evidence calls.",
            kind="enum",
            group="context_types",
            url="",
            metadata={"context_type": value},
        )
        for value in GWAS_CONTEXT_TYPES
    ]


def gwas_record_context(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    record_type = normalize_space(record.get("record_type"))
    if record_type == "gwas_gene":
        parameter_name, group, value = "gene", "genes", normalize_space(data.get("gene") or record.get("id"))
    elif record_type == "gwas_trait":
        parameter_name, group, value = "trait", "traits", normalize_space(data.get("trait") or record.get("id"))
    else:
        parameter_name, group, value = "rs_id", "variants", normalize_space(data.get("rs_id") or record.get("id"))
    return gwas_parameter_context(
        parameter_name,
        value,
        label=normalize_space(record.get("title") or record.get("label") or value),
        description=normalize_space(record.get("description") or f"GWAS Catalog {group.rstrip('s')} context."),
        kind=record_type or group.rstrip("s"),
        group=group,
        url=normalize_space(record.get("url") or data.get("url")),
        metadata={
            "id": value,
            "total_associations": data.get("total_associations", ""),
            "total_studies": data.get("total_studies", ""),
            "mapped_genes": data.get("snp", {}).get("mapped_genes", "") if isinstance(data.get("snp"), dict) else "",
            "location": data.get("snp", {}).get("location", "") if isinstance(data.get("snp"), dict) else "",
        },
    )


def gwas_parameter_context(
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
    component = "variant" if group == "variants" else "gene" if group == "genes" else "dataset"
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
            "icon": "gwas",
            "title": label,
            "subtitle": f"{parameter_name}: {value}",
            "description": description,
            "metadata": display_fields,
            "badges": [{"label": "GWAS Catalog", "kind": "source"}, {"label": parameter_name, "kind": "parameter"}],
            "actions": [{"label": "Open source", "url": url, "kind": "external", "primary": True}] if url else [],
            "hover": {"title": label, "subtitle": f"{parameter_name}: {value}", "icon": "gwas", "fields": display_fields},
            "primary_url": url,
        },
    }


def gwas_recommended_calls(record: JsonObject) -> list[JsonObject]:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    record_type = normalize_space(record.get("record_type"))
    if record_type == "gwas_gene":
        gene = normalize_space(data.get("gene") or record.get("id"))
        return [
            {"tool_name": "gwas_gene_lookup", "arguments": {"gene": gene}, "reason": "Fetch GWAS association evidence for this mapped gene."},
            {"server": "ncbi", "tool_name": "gene_search", "arguments": {"term": gene}, "reason": "Open NCBI Gene context for this symbol."},
        ]
    if record_type == "gwas_trait":
        trait = normalize_space(data.get("trait") or record.get("id"))
        return [
            {"tool_name": "gwas_trait_search", "arguments": {"trait": trait}, "reason": "Fetch GWAS associations and studies for this trait."},
            {"server": "opentargets", "tool_name": "opentargets_search", "arguments": {"query": trait, "entity_names": ["disease"]}, "reason": "Search Open Targets disease context for this trait."},
        ]
    rs_id = normalize_space(data.get("rs_id") or record.get("id"))
    return [
        {"tool_name": "gwas_variant_lookup", "arguments": {"rs_id": rs_id}, "reason": "Fetch GWAS association evidence for this variant."},
        {"server": "ensembl", "tool_name": "ensembl_variation", "arguments": {"species": "homo_sapiens", "variant_id": rs_id}, "reason": "Open Ensembl variant metadata for this rsID."},
        {"server": "clinvar", "tool_name": "clinvar_search", "arguments": {"terms": rs_id}, "reason": "Check ClinVar clinical interpretation for this variant."},
    ]


def gwas_context_matches(context: JsonObject, *, context_type: str, query: str) -> bool:
    if context_type != "all" and context.get("group") != context_type:
        return False
    if not query:
        return True
    metadata = context.get("metadata")
    haystack_values = [context.get("parameter_name"), context.get("value"), context.get("label"), context.get("description"), context.get("kind")]
    if isinstance(metadata, dict):
        haystack_values.extend(metadata.values())
    haystack = " ".join(str(item).lower() for item in haystack_values if item not in ("", None))
    return query.lower() in haystack or context.get("group") in {"variants", "genes", "traits"}


def tool_definitions() -> list[JsonObject]:
    read_only_annotations = {
        "readOnlyHint": True,
        "openWorldHint": True,
    }
    return [
        parameter_domains_tool_definition("gwas_parameter_domains"),
        {
            "name": "gwas_resolve_context",
            "title": "Resolve GWAS Catalog dynamic parameter context",
            "description": (
                "Resolve GWAS rsID, mapped-gene, and trait context before evidence lookup. "
                "Returns app-renderable context rows, GWAS URLs, and recommended follow-up calls."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "context_type": {"type": "string", "enum": GWAS_CONTEXT_TYPES, "default": "all"},
                    "query": {"type": "string", "description": "Optional rsID, gene, or trait query."},
                    "rs_id": {"type": "string", "description": "Optional dbSNP rsID such as rs699."},
                    "gene": {"type": "string", "description": "Optional mapped gene such as BRCA1."},
                    "trait": {"type": "string", "description": "Optional trait such as asthma."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": 10},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "gwas_variant_lookup",
            "title": "Look up GWAS Catalog associations for a variant",
            "description": (
                "Fetch one GWAS Catalog SNP record and association evidence by rsID, "
                "returning a front-end-compatible variant record."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "rs_id": {"type": "string", "description": "dbSNP rsID, for example rs699."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": 10},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["rs_id"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "gwas_gene_lookup",
            "title": "Look up GWAS Catalog associations for a mapped gene",
            "description": (
                "Fetch association evidence filtered by GWAS Catalog mapped_gene, "
                "returning a front-end-compatible gene evidence record."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "gene": {"type": "string", "description": "Gene symbol such as BRCA1 or AGT."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": 10},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["gene"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "gwas_trait_search",
            "title": "Search GWAS Catalog associations and studies by trait",
            "description": (
                "Fetch association and study evidence for an EFO/reported trait query, "
                "returning a front-end-compatible dataset record."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "trait": {"type": "string", "description": "Trait query such as asthma."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": 10},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["trait"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "gwas_status",
            "title": "Inspect GWAS Catalog MCP status",
            "description": "Return configured GWAS Catalog MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
    ]


TOOL_HANDLERS: dict[str, Callable[[JsonObject, GwasClient], JsonObject]] = {
    "gwas_parameter_domains": make_parameter_domains_handler("gwas", "gwas_parameter_domains", tool_definitions),
    "gwas_resolve_context": gwas_resolve_context,
    "gwas_variant_lookup": gwas_variant_lookup,
    "gwas_gene_lookup": gwas_gene_lookup,
    "gwas_trait_search": gwas_trait_search,
    "gwas_status": gwas_status,
}
