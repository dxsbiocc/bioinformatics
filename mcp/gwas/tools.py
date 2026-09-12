"""MCP tool registry for the GWAS Catalog server."""

from __future__ import annotations

from typing import Callable

from .client import GwasClient
from .constants import MAX_RESULTS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import GwasError
from .records import gwas_gene_record, gwas_trait_record, gwas_variant_record
from .utils import optional_bool, optional_int, require_non_empty_string, source_info


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


def tool_definitions() -> list[JsonObject]:
    read_only_annotations = {
        "readOnlyHint": True,
        "openWorldHint": True,
    }
    return [
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
    "gwas_variant_lookup": gwas_variant_lookup,
    "gwas_gene_lookup": gwas_gene_lookup,
    "gwas_trait_search": gwas_trait_search,
    "gwas_status": gwas_status,
}

