"""MCP tool registry for the PubChem server."""

from __future__ import annotations

from mcp.dynamic_context import build_dynamic_context_response
from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition
import urllib.parse
from typing import Callable

from .client import PubChemClient
from .constants import COMPOUND_PROPERTY_FIELDS, MAX_RESULTS, MAX_SYNONYMS, RESULT_SCHEMA_VERSION, JsonObject
from .errors import McpError, PubChemError
from .records import (
    pubchem_assay_record,
    pubchem_compound_record,
    pubchem_substance_record,
)
from .utils import (
    normalize_space,
    optional_bool,
    optional_int,
    optional_positive_identifier,
    optional_string,
    require_non_empty_string,
    source_info,
)


PUBCHEM_CONTEXT_TYPES = ["all", "compounds", "assays", "substances", "namespaces"]
PUBCHEM_CONTEXT_SCHEMA_VERSION = "bioinformatics.dynamic_context.v1"


def pubchem_status(args: JsonObject, client: PubChemClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "pubchem",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "website_base_url": client.config.website_base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["pubchem_compound", "pubchem_substance", "pubchem_bioassay"],
        "tool_groups": {
            "context": ["pubchem_parameter_domains", "pubchem_resolve_context"],
            "compound": ["pubchem_compound_lookup", "pubchem_compound_search"],
            "assay": ["pubchem_assay_summary"],
            "substance": ["pubchem_substance_lookup"],
            "status": ["pubchem_status"],
        },
        "frontend_components": ["compound", "dataset"],
        "preview_kinds": ["chemical_structure", "table", "xref_groups"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload, headers = client.request_json_with_headers(
            "compound/cid/2244/property/Title/JSON",
            {},
        )
        properties = property_rows(payload)
        status["network_check"] = {
            "ok": True,
            "returned": len(properties),
            "example_cid": properties[0].get("CID") if properties else None,
            "example_title": properties[0].get("Title") if properties else None,
            "content_type": headers.get("content-type"),
        }
    return status


def pubchem_resolve_context(args: JsonObject, client: PubChemClient) -> JsonObject:
    context_type = optional_context_type(args, "context_type", allowed=PUBCHEM_CONTEXT_TYPES, default="all")
    query = optional_text(args, "query")
    cid = optional_positive_identifier(args, "cid")
    aid = optional_positive_identifier(args, "aid")
    sid = optional_positive_identifier(args, "sid")
    max_results = optional_int(args, "max_results", default=5, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    contexts = static_pubchem_contexts()
    recommended_calls: list[JsonObject] = []
    sources: list[JsonObject] = []
    raw: JsonObject = {}

    if query:
        result = pubchem_compound_search(
            {"query": query, "max_results": max_results, "include_descriptions": True, "include_synonyms": False, "include_raw": include_raw},
            client,
        )
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(pubchem_record_context(record) for record in records)
        for record in records[:3]:
            recommended_calls.extend(pubchem_recommended_calls(record))
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["compound_search"] = result["raw"]

    if cid:
        result = pubchem_compound_lookup({"cid": cid, "include_descriptions": True, "include_synonyms": True, "include_raw": include_raw}, client)
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(pubchem_record_context(record) for record in records)
        for record in records:
            recommended_calls.extend(pubchem_recommended_calls(record))
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["compound_lookup"] = result["raw"]

    if aid:
        result = pubchem_assay_summary({"aid": aid, "include_raw": include_raw}, client)
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(pubchem_record_context(record) for record in records)
        for record in records:
            recommended_calls.extend(pubchem_recommended_calls(record))
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["assay"] = result["raw"]

    if sid:
        result = pubchem_substance_lookup({"sid": sid, "include_raw": include_raw}, client)
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(pubchem_record_context(record) for record in records)
        for record in records:
            recommended_calls.extend(pubchem_recommended_calls(record))
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["substance"] = result["raw"]

    query_text = query or cid or aid or sid
    filtered_contexts = [
        context
        for context in contexts
        if pubchem_context_matches(context, context_type=context_type, query=query_text or "")
    ]
    return build_dynamic_context_response(
        schema_version=RESULT_SCHEMA_VERSION,
        context_schema_version=PUBCHEM_CONTEXT_SCHEMA_VERSION,
        database="pubchem",
        query={"context_type": context_type, "query": query, "cid": cid, "aid": aid, "sid": sid},
        contexts=filtered_contexts,
        recommended_calls=recommended_calls,
        max_results=max_results,
        fallback_source=source_info("resolve_context", {"context_type": context_type, "query": query, "cid": cid, "aid": aid, "sid": sid}),
        sources=sources,
        entity_groups={"compounds", "assays", "substances"},
        raw=raw,
        include_raw=include_raw,
        prioritize_entities=True,
        prioritize_same_server_calls=True,
    )


def pubchem_compound_lookup(args: JsonObject, client: PubChemClient) -> JsonObject:
    cid = optional_positive_identifier(args, "cid")
    name = optional_string(args, "name")
    if not cid and not name:
        raise McpError(-32602, "cid or name is required")
    include_synonyms = optional_bool(args, "include_synonyms", default=True)
    include_descriptions = optional_bool(args, "include_descriptions", default=True)
    max_synonyms = optional_int(args, "max_synonyms", default=MAX_SYNONYMS, minimum=0, maximum=100)
    include_raw = optional_bool(args, "include_raw", default=False)

    namespace = "cid" if cid else "name"
    identifier = cid or name or ""
    endpoint = compound_property_endpoint(namespace, identifier)
    payload, headers = client.request_json_with_headers(endpoint, {})
    properties = first_property(payload)
    resolved_cid = str(properties.get("CID") or cid or "")
    if not resolved_cid:
        raise PubChemError(f"PubChem compound not found for {identifier}")

    warnings: list[str] = []
    descriptions, description_payload = fetch_descriptions(client, resolved_cid, include_descriptions, warnings)
    synonyms, synonyms_truncated, synonym_payload = fetch_synonyms(client, resolved_cid, include_synonyms, max_synonyms, warnings)
    record = pubchem_compound_record(
        properties,
        descriptions=descriptions,
        synonyms=synonyms,
        synonyms_truncated=synonyms_truncated,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "pubchem",
        "query": identifier,
        "returned": 1,
        "compound": compound_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    if warnings:
        response["warnings"] = warnings
    if include_raw:
        response["raw"] = {"properties": payload, "descriptions": description_payload, "synonyms": synonym_payload}
    return response


def pubchem_compound_search(args: JsonObject, client: PubChemClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    max_results = optional_int(args, "max_results", default=5, minimum=1, maximum=MAX_RESULTS)
    include_descriptions = optional_bool(args, "include_descriptions", default=True)
    include_synonyms = optional_bool(args, "include_synonyms", default=False)
    include_raw = optional_bool(args, "include_raw", default=False)
    cids_endpoint = f"compound/name/{quote_path(query)}/cids/JSON"
    cids_payload, headers = client.request_json_with_headers(cids_endpoint, {})
    cids = extract_identifier_list(cids_payload, "CID")[:max_results]
    records = []
    raw_records = []
    warnings: list[str] = []
    for cid in cids:
        property_payload, _property_headers = client.request_json_with_headers(compound_property_endpoint("cid", cid), {})
        properties = first_property(property_payload)
        descriptions, description_payload = fetch_descriptions(client, cid, include_descriptions, warnings)
        synonyms, synonyms_truncated, synonym_payload = fetch_synonyms(client, cid, include_synonyms, MAX_SYNONYMS, warnings)
        records.append(
            pubchem_compound_record(
                properties,
                descriptions=descriptions,
                synonyms=synonyms,
                synonyms_truncated=synonyms_truncated,
                website_base_url=client.config.website_base_url,
                api_base_url=client.config.base_url,
            )
        )
        raw_records.append({"properties": property_payload, "descriptions": description_payload, "synonyms": synonym_payload})
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "pubchem",
        "query": query,
        "returned": len(records),
        "total": len(extract_identifier_list(cids_payload, "CID")),
        "compounds": [compound_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(cids_endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    if warnings:
        response["warnings"] = warnings
    if include_raw:
        response["raw"] = {"cids": cids_payload, "records": raw_records}
    return response


def pubchem_assay_summary(args: JsonObject, client: PubChemClient) -> JsonObject:
    aid = optional_positive_identifier(args, "aid")
    if not aid:
        raise McpError(-32602, "aid is required")
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"assay/aid/{quote_path(aid)}/summary/JSON"
    payload, headers = client.request_json_with_headers(endpoint, {})
    assay = first_assay(payload)
    if not assay:
        raise PubChemError(f"PubChem assay not found for AID {aid}")
    record = pubchem_assay_record(
        assay,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "pubchem",
        "query": aid,
        "returned": 1,
        "assay": assay_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def pubchem_substance_lookup(args: JsonObject, client: PubChemClient) -> JsonObject:
    sid = optional_positive_identifier(args, "sid")
    if not sid:
        raise McpError(-32602, "sid is required")
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"substance/sid/{quote_path(sid)}/JSON"
    payload, headers = client.request_json_with_headers(endpoint, {})
    substance = first_substance(payload)
    if not substance:
        raise PubChemError(f"PubChem substance not found for SID {sid}")
    record = pubchem_substance_record(
        substance,
        website_base_url=client.config.website_base_url,
        api_base_url=client.config.base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "pubchem",
        "query": sid,
        "returned": 1,
        "substance": substance_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def fetch_descriptions(
    client: PubChemClient,
    cid: str,
    enabled: bool,
    warnings: list[str],
) -> tuple[list[JsonObject], JsonObject | None]:
    if not enabled:
        return [], None
    endpoint = f"compound/cid/{quote_path(cid)}/description/JSON"
    try:
        payload, _headers = client.request_json_with_headers(endpoint, {})
    except PubChemError as exc:
        warnings.append(f"Could not fetch descriptions for CID {cid}: {exc}")
        return [], None
    return information_rows(payload), payload


def fetch_synonyms(
    client: PubChemClient,
    cid: str,
    enabled: bool,
    max_synonyms: int,
    warnings: list[str],
) -> tuple[list[str], bool, JsonObject | None]:
    if not enabled or max_synonyms <= 0:
        return [], False, None
    endpoint = f"compound/cid/{quote_path(cid)}/synonyms/JSON"
    try:
        payload, _headers = client.request_json_with_headers(endpoint, {})
    except PubChemError as exc:
        warnings.append(f"Could not fetch synonyms for CID {cid}: {exc}")
        return [], False, None
    rows = information_rows(payload)
    synonyms = []
    for row in rows:
        values = row.get("Synonym")
        if isinstance(values, list):
            synonyms.extend(str(value) for value in values)
    return synonyms[:max_synonyms], len(synonyms) > max_synonyms, payload


def first_property(payload: object) -> JsonObject:
    rows = property_rows(payload)
    if not rows:
        raise PubChemError("PubChem compound property response did not contain a compound")
    return rows[0]


def property_rows(payload: object) -> list[JsonObject]:
    if not isinstance(payload, dict):
        return []
    table = payload.get("PropertyTable")
    if not isinstance(table, dict):
        return []
    rows = table.get("Properties")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def information_rows(payload: object) -> list[JsonObject]:
    if not isinstance(payload, dict):
        return []
    info = payload.get("InformationList")
    if not isinstance(info, dict):
        return []
    rows = info.get("Information")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def extract_identifier_list(payload: object, key: str) -> list[str]:
    if not isinstance(payload, dict):
        return []
    identifiers = payload.get("IdentifierList")
    if not isinstance(identifiers, dict):
        return []
    values = identifiers.get(key)
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if str(value).strip()]


def first_assay(payload: object) -> JsonObject:
    if not isinstance(payload, dict):
        return {}
    summaries = payload.get("AssaySummaries")
    if isinstance(summaries, dict):
        rows = summaries.get("AssaySummary")
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    return row
    if isinstance(summaries, list):
        for row in summaries:
            if isinstance(row, dict):
                return row
    return {}


def first_substance(payload: object) -> JsonObject:
    if not isinstance(payload, dict):
        return {}
    rows = payload.get("PC_Substances")
    if not isinstance(rows, list):
        return {}
    for row in rows:
        if isinstance(row, dict):
            return row
    return {}


def compound_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "cid": data.get("cid"),
        "title": data.get("title"),
        "molecular_formula": data.get("molecular_formula"),
        "molecular_weight": data.get("molecular_weight"),
        "canonical_smiles": data.get("canonical_smiles"),
        "url": data.get("url"),
    }


def assay_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "aid": data.get("aid"),
        "name": data.get("name"),
        "source_name": data.get("source_name"),
        "target_name": data.get("target_name"),
        "url": data.get("url"),
    }


def substance_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "sid": data.get("sid"),
        "title": data.get("title"),
        "source_name": data.get("source_name"),
        "source_id": data.get("source_id"),
        "compound_cids": data.get("compound_cids"),
        "url": data.get("url"),
    }


def compound_property_endpoint(namespace: str, identifier: str) -> str:
    return f"compound/{namespace}/{quote_path(identifier)}/property/{','.join(COMPOUND_PROPERTY_FIELDS)}/JSON"


def quote_path(value: object) -> str:
    return urllib.parse.quote(str(value), safe="")


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


def static_pubchem_contexts() -> list[JsonObject]:
    contexts: list[JsonObject] = [
        pubchem_parameter_context(
            "context_type",
            value,
            label=value,
            description="Dynamic PubChem context family to resolve before compound, assay, or substance calls.",
            kind="enum",
            group="context_types",
            url="",
            metadata={"context_type": value},
        )
        for value in PUBCHEM_CONTEXT_TYPES
    ]
    contexts.extend(
        pubchem_parameter_context(
            "namespace",
            value,
            label=label,
            description="PubChem identifier namespace used by lookup tools.",
            kind="namespace",
            group="namespaces",
            url="https://pubchem.ncbi.nlm.nih.gov/",
            metadata={"namespace": value},
        )
        for value, label in [("cid", "Compound ID"), ("name", "Compound name"), ("aid", "BioAssay ID"), ("sid", "Substance ID")]
    )
    return contexts


def pubchem_record_context(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    record_type = normalize_space(record.get("record_type"))
    if record_type == "pubchem_assay":
        parameter_name, group, value = "aid", "assays", normalize_space(data.get("aid") or record.get("id"))
    elif record_type == "pubchem_substance":
        parameter_name, group, value = "sid", "substances", normalize_space(data.get("sid") or record.get("id"))
    else:
        parameter_name, group, value = "cid", "compounds", normalize_space(data.get("cid") or record.get("id"))
    return pubchem_parameter_context(
        parameter_name,
        value,
        label=normalize_space(record.get("title") or record.get("label") or value),
        description=normalize_space(record.get("description") or f"PubChem {group.rstrip('s')} context."),
        kind=record_type or group.rstrip("s"),
        group=group,
        url=normalize_space(record.get("url") or data.get("url")),
        metadata={
            "id": value,
            "title": data.get("title", ""),
            "name": data.get("name", ""),
            "molecular_formula": data.get("molecular_formula", ""),
            "molecular_weight": data.get("molecular_weight", ""),
            "inchi_key": data.get("inchi_key", ""),
            "target_gene_id": data.get("target_gene_id", ""),
            "source_name": data.get("source_name", ""),
            "compound_cids": data.get("compound_cids", ""),
        },
    )


def pubchem_parameter_context(
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
    component = "compound" if group == "compounds" else "dataset"
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
            "icon": "pubchem",
            "title": label,
            "subtitle": f"{parameter_name}: {value}",
            "description": description,
            "metadata": display_fields,
            "badges": [{"label": "PubChem", "kind": "source"}, {"label": parameter_name, "kind": "parameter"}],
            "actions": [{"label": "Open source", "url": url, "kind": "external", "primary": True}] if url else [],
            "hover": {"title": label, "subtitle": f"{parameter_name}: {value}", "icon": "pubchem", "fields": display_fields},
            "primary_url": url,
        },
    }


def pubchem_recommended_calls(record: JsonObject) -> list[JsonObject]:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    record_type = normalize_space(record.get("record_type"))
    if record_type == "pubchem_assay":
        aid = normalize_space(data.get("aid") or record.get("id"))
        calls = [{"tool_name": "pubchem_assay_summary", "arguments": {"aid": aid}, "reason": "Fetch PubChem BioAssay summary and target metadata."}]
        if data.get("target_gene_id"):
            calls.append({"server": "ncbi", "tool_name": "gene_lookup", "arguments": {"gene_id": str(data["target_gene_id"])}, "reason": "Open NCBI Gene context for this assay target."})
        return calls
    if record_type == "pubchem_substance":
        sid = normalize_space(data.get("sid") or record.get("id"))
        calls = [{"tool_name": "pubchem_substance_lookup", "arguments": {"sid": sid}, "reason": "Fetch PubChem Substance depositor metadata and linked compounds."}]
        for cid in data.get("compound_cids", []) if isinstance(data.get("compound_cids"), list) else []:
            calls.append({"tool_name": "pubchem_compound_lookup", "arguments": {"cid": cid}, "reason": "Open linked PubChem compound context."})
        return calls
    cid = normalize_space(data.get("cid") or record.get("id"))
    return [
        {"tool_name": "pubchem_compound_lookup", "arguments": {"cid": cid}, "reason": "Fetch PubChem compound properties, descriptions, synonyms, and structure previews."},
        {"server": "chembl", "tool_name": "chembl_resolve_context", "arguments": {"query": data.get("title") or cid}, "reason": "Resolve related ChEMBL molecule context for this compound."},
        {"server": "chebi", "tool_name": "chebi_compound_search", "arguments": {"query": data.get("title") or cid}, "reason": "Search ChEBI for ontology context for this compound."},
    ]


def pubchem_context_matches(context: JsonObject, *, context_type: str, query: str) -> bool:
    if context_type != "all" and context.get("group") != context_type:
        return False
    if not query:
        return True
    metadata = context.get("metadata")
    haystack_values = [context.get("parameter_name"), context.get("value"), context.get("label"), context.get("description"), context.get("kind")]
    if isinstance(metadata, dict):
        haystack_values.extend(metadata.values())
    haystack = " ".join(str(item).lower() for item in haystack_values if item not in ("", None))
    return query.lower() in haystack or context.get("group") in {"compounds", "assays", "substances"}


def tool_definitions() -> list[JsonObject]:
    read_only_annotations = {
        "readOnlyHint": True,
        "openWorldHint": True,
    }
    return [
        parameter_domains_tool_definition("pubchem_parameter_domains"),
        {
            "name": "pubchem_resolve_context",
            "title": "Resolve PubChem dynamic parameter context",
            "description": (
                "Resolve PubChem compound names/CIDs, BioAssay AIDs, and Substance SIDs before lookup calls. "
                "Returns front-end-friendly context rows, PubChem URLs, and recommended follow-up calls."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "context_type": {"type": "string", "enum": PUBCHEM_CONTEXT_TYPES, "default": "all"},
                    "query": {"type": "string", "description": "Optional compound name such as aspirin."},
                    "cid": {"type": ["integer", "string"], "description": "Optional PubChem CID such as 2244."},
                    "aid": {"type": ["integer", "string"], "description": "Optional PubChem AID such as 1706."},
                    "sid": {"type": ["integer", "string"], "description": "Optional PubChem SID such as 4594."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": 5},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "pubchem_compound_lookup",
            "title": "Look up a PubChem compound",
            "description": (
                "Fetch one PubChem compound by CID or exact name and return a front-end-compatible "
                "compound record with properties, descriptions, synonyms, structure preview, and links."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "cid": {"type": ["integer", "string"], "description": "PubChem Compound ID, for example 2244."},
                    "name": {"type": "string", "description": "Compound name, for example aspirin."},
                    "include_descriptions": {"type": "boolean", "default": True},
                    "include_synonyms": {"type": "boolean", "default": True},
                    "max_synonyms": {"type": "integer", "minimum": 0, "maximum": 100, "default": MAX_SYNONYMS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "anyOf": [{"required": ["cid"]}, {"required": ["name"]}],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "pubchem_compound_search",
            "title": "Resolve PubChem compound names to CIDs",
            "description": (
                "Resolve a compound name through PubChem PUG REST and hydrate matching CIDs into "
                "front-end-compatible compound records."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Compound name or synonym, for example aspirin."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": 5},
                    "include_descriptions": {"type": "boolean", "default": True},
                    "include_synonyms": {"type": "boolean", "default": False},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "pubchem_assay_summary",
            "title": "Look up a PubChem BioAssay summary",
            "description": "Fetch one PubChem BioAssay by AID and return a dataset record with summary table and links.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "aid": {"type": ["integer", "string"], "description": "PubChem BioAssay ID, for example 1706."},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["aid"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "pubchem_substance_lookup",
            "title": "Look up a PubChem substance",
            "description": "Fetch one PubChem Substance by SID and return a dataset record with depositor metadata, synonyms, xrefs, and linked compounds.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sid": {"type": ["integer", "string"], "description": "PubChem Substance ID, for example 4594."},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["sid"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "pubchem_status",
            "title": "Inspect PubChem MCP status",
            "description": "Return configured PubChem MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
    ]


TOOL_HANDLERS: dict[str, Callable[[JsonObject, PubChemClient], JsonObject]] = {
    "pubchem_parameter_domains": make_parameter_domains_handler("pubchem", "pubchem_parameter_domains", tool_definitions),
    "pubchem_resolve_context": pubchem_resolve_context,
    "pubchem_compound_lookup": pubchem_compound_lookup,
    "pubchem_compound_search": pubchem_compound_search,
    "pubchem_assay_summary": pubchem_assay_summary,
    "pubchem_substance_lookup": pubchem_substance_lookup,
    "pubchem_status": pubchem_status,
}
