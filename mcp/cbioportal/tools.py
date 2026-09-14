"""MCP tool registry for the cBioPortal server."""

from __future__ import annotations

from mcp.dynamic_context import build_dynamic_context_response
from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition

from .client import CbioPortalClient
from .constants import (
    DEFAULT_CLINICAL_IDS,
    DEFAULT_MOLECULAR_ROWS,
    DEFAULT_MUTATIONS,
    DEFAULT_RESULTS,
    DEFAULT_SURVIVAL_PREFIXES,
    MAX_CLINICAL_ATTRIBUTES,
    MAX_CLINICAL_IDS,
    MAX_MOLECULAR_ROWS,
    MAX_MUTATIONS,
    MAX_RESULTS,
    MAX_SURVIVAL_PREFIXES,
    RESULT_SCHEMA_VERSION,
    JsonObject,
)
from .errors import CbioPortalError, McpError
from .records import (
    cbioportal_clinical_attributes_record,
    cbioportal_clinical_data_record,
    cbioportal_discrete_cna_record,
    cbioportal_molecular_data_record,
    cbioportal_mutations_record,
    cbioportal_profile_record,
    cbioportal_sample_list_record,
    cbioportal_study_record,
    cbioportal_survival_data_record,
)
from .utils import (
    optional_bool,
    optional_clinical_data_type,
    optional_identifier_list,
    optional_int,
    optional_int_list,
    optional_string,
    optional_symbol_list,
    require_non_empty_string,
    require_profile_id,
    require_sample_list_id,
    require_study_id,
    source_info,
)

CNA_EVENT_TYPES = {"HOMDEL_AND_AMP", "HOMDEL", "AMP", "GAIN", "HETLOSS", "DIPLOID", "ALL"}
CBIOPORTAL_CONTEXT_TYPES = ["all", "studies", "study", "profiles", "sample_lists", "clinical_attributes", "fetch_context"]
CBIOPORTAL_CONTEXT_SCHEMA_VERSION = "bioinformatics.dynamic_context.v1"


def cbioportal_status(args: JsonObject, client: CbioPortalClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "cbioportal",
        "version": "0.1.0",
        "api_base_url": client.config.api_base_url,
        "website_base_url": client.config.website_base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["cbioportal"],
        "tool_groups": {
            "context": ["cbioportal_parameter_domains", "cbioportal_resolve_context"],
            "studies": ["cbioportal_study_search", "cbioportal_study_lookup"],
            "profiles": ["cbioportal_molecular_profiles"],
            "samples": ["cbioportal_sample_lists"],
            "mutations": ["cbioportal_mutations_fetch"],
            "molecular_data": ["cbioportal_molecular_data_fetch", "cbioportal_discrete_cna_fetch"],
            "clinical": ["cbioportal_clinical_attributes", "cbioportal_clinical_data_fetch"],
            "survival": ["cbioportal_survival_data_fetch"],
            "status": ["cbioportal_status"],
        },
        "frontend_components": ["project", "dataset"],
        "preview_kinds": ["table", "xref_groups", "survival_curve", "heatmap_matrix"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload, headers = client.request_json_with_headers("studies", {"keyword": "breast", "projection": "SUMMARY", "pageSize": 1})
        rows = list_payload(payload)
        status["network_check"] = {
            "ok": True,
            "example_study_id": rows[0].get("studyId") if rows else None,
            "content_type": headers.get("content-type"),
        }
    return status


def cbioportal_resolve_context(args: JsonObject, client: CbioPortalClient) -> JsonObject:
    context_type = optional_context_type(args, "context_type", allowed=CBIOPORTAL_CONTEXT_TYPES, default="all")
    query = optional_string(args, "query")
    study_id = optional_string(args, "study_id")
    molecular_profile_id = optional_string(args, "molecular_profile_id")
    sample_list_id = optional_string(args, "sample_list_id")
    max_results = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    if study_id:
        study_id = require_study_id({"study_id": study_id})
    if molecular_profile_id:
        molecular_profile_id = require_profile_id({"molecular_profile_id": molecular_profile_id})
    if sample_list_id:
        sample_list_id = require_sample_list_id({"sample_list_id": sample_list_id})

    contexts: list[JsonObject] = []
    sources: list[JsonObject] = []
    diagnostics: list[JsonObject] = []
    raw: JsonObject = {}
    study: JsonObject = {}
    profiles: list[JsonObject] = []
    sample_lists: list[JsonObject] = []
    clinical_attributes: list[JsonObject] = []
    profile: JsonObject = {}
    sample_list: JsonObject = {}

    if context_type == "all" or not any([query, study_id, molecular_profile_id, sample_list_id]):
        contexts.extend(static_cbioportal_contexts(client))

    if query and not study_id and context_type in {"all", "studies", "study"}:
        endpoint = "studies"
        params: JsonObject = {"keyword": query, "projection": "SUMMARY", "pageSize": max_results}
        payload, headers = client.request_json_with_headers(endpoint, params)
        rows = list_payload(payload)[:max_results]
        raw["study_search"] = payload
        sources.append(source_with_headers(endpoint, params, headers, client.build_url(endpoint, params)))
        for row in rows:
            contexts.append(cbioportal_study_context(row, client))

    if study_id:
        if context_type in {"all", "study", "fetch_context"}:
            endpoint = f"studies/{study_id}"
            params = {"projection": "DETAILED"}
            payload, headers = client.request_json_with_headers(endpoint, params)
            study = ensure_object(payload, study_id)
            raw["study"] = payload
            sources.append(source_with_headers(endpoint, params, headers, client.build_url(endpoint, params)))
            contexts.append(cbioportal_study_context(study, client))
        if context_type in {"all", "profiles", "fetch_context"}:
            endpoint = f"studies/{study_id}/molecular-profiles"
            params = {"projection": "SUMMARY"}
            payload, headers = client.request_json_with_headers(endpoint, params)
            profiles = list_payload(payload)
            raw["profiles"] = payload
            sources.append(source_with_headers(endpoint, params, headers, client.build_url(endpoint, params)))
            contexts.extend(cbioportal_profile_context(row, client) for row in profiles[:max_results])
        if context_type in {"all", "sample_lists", "fetch_context"}:
            endpoint = f"studies/{study_id}/sample-lists"
            params = {"projection": "SUMMARY"}
            payload, headers = client.request_json_with_headers(endpoint, params)
            sample_lists = list_payload(payload)
            raw["sample_lists"] = payload
            sources.append(source_with_headers(endpoint, params, headers, client.build_url(endpoint, params)))
            contexts.extend(cbioportal_sample_list_context(row, client) for row in sample_lists[:max_results])
        if context_type in {"all", "clinical_attributes", "fetch_context"}:
            endpoint = f"studies/{study_id}/clinical-attributes"
            params = {"projection": "SUMMARY", "pageSize": max_results}
            payload, headers = client.request_json_with_headers(endpoint, params)
            clinical_attributes = list_payload(payload)
            raw["clinical_attributes"] = payload
            sources.append(source_with_headers(endpoint, params, headers, client.build_url(endpoint, params)))
            contexts.extend(cbioportal_clinical_attribute_context(study_id, row, client) for row in clinical_attributes[:max_results])

    if molecular_profile_id:
        profile = first_matching_profile(profiles, molecular_profile_id)
        if not profile:
            detail = read_optional_cbioportal_record(client, f"molecular-profiles/{molecular_profile_id}", molecular_profile_id, "molecular_profile")
            sources.extend(detail["sources"])
            diagnostics.extend(detail["diagnostics"])
            profile = detail["record"]
            if profile:
                raw["molecular_profile"] = profile
        if profile and not any(context.get("parameter_name") == "molecular_profile_id" and context.get("value") == molecular_profile_id for context in contexts):
            contexts.append(cbioportal_profile_context(profile, client))

    if sample_list_id:
        sample_list = first_matching_sample_list(sample_lists, sample_list_id)
        if not sample_list:
            detail = read_optional_cbioportal_record(client, f"sample-lists/{sample_list_id}", sample_list_id, "sample_list")
            sources.extend(detail["sources"])
            diagnostics.extend(detail["diagnostics"])
            sample_list = detail["record"]
            if sample_list:
                raw["sample_list"] = sample_list
        if sample_list and not any(context.get("parameter_name") == "sample_list_id" and context.get("value") == sample_list_id for context in contexts):
            contexts.append(cbioportal_sample_list_context(sample_list, client))

    resolved = resolved_cbioportal_context(
        study_id=study_id,
        molecular_profile_id=molecular_profile_id,
        sample_list_id=sample_list_id,
        profile=profile,
        sample_list=sample_list,
    )
    diagnostics.extend(cbioportal_context_diagnostics(resolved))
    recommended_calls = recommended_cbioportal_calls(
        study_id=study_id,
        profile=profile,
        sample_list=sample_list,
        clinical_attributes=clinical_attributes,
        compatible=resolved.get("compatible"),
    )
    filtered_contexts = [context for context in contexts if context_matches(context, query)]
    context_parameter_names = {
        "study_id",
        "molecular_profile_id",
        "sample_list_id",
        "clinical_attribute_ids",
    }
    return build_dynamic_context_response(
        schema_version=RESULT_SCHEMA_VERSION,
        context_schema_version=CBIOPORTAL_CONTEXT_SCHEMA_VERSION,
        database="cbioportal",
        query={
            "context_type": context_type,
            "query": query,
            "study_id": study_id,
            "molecular_profile_id": molecular_profile_id,
            "sample_list_id": sample_list_id,
        },
        contexts=filtered_contexts,
        recommended_calls=recommended_calls,
        max_results=max_results,
        fallback_source=source_info("resolve_context", {"context_type": context_type, "query": query}),
        sources=sources,
        entity_groups={"studies", "profiles", "sample_lists", "clinical_attributes"},
        raw=raw,
        summary_fields={
            "entities": lambda context: context.get("parameter_name") in context_parameter_names,
            "studies": lambda context: context.get("parameter_name") == "study_id",
            "profiles": lambda context: context.get("parameter_name") == "molecular_profile_id",
            "sample_lists": lambda context: context.get("parameter_name") == "sample_list_id",
            "clinical_attributes": lambda context: context.get("parameter_name") == "clinical_attribute_ids",
        },
        extra_fields={"resolved": resolved, **({"diagnostics": diagnostics} if diagnostics else {})},
        include_raw=include_raw,
        prioritize_entities=True,
        dedupe_calls=False,
    )


def cbioportal_study_search(args: JsonObject, client: CbioPortalClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    max_results = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = "studies"
    params: JsonObject = {"keyword": query, "projection": "SUMMARY", "pageSize": max_results}
    payload, headers = client.request_json_with_headers(endpoint, params)
    rows = list_payload(payload)[:max_results]
    records = [cbioportal_study_record(row, api_base_url=client.config.api_base_url, website_base_url=client.config.website_base_url) for row in rows]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "cbioportal",
        "query": query,
        "returned": len(records),
        "studies": [study_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, params, headers, client.build_url(endpoint, params)),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def cbioportal_study_lookup(args: JsonObject, client: CbioPortalClient) -> JsonObject:
    study_id = require_study_id(args)
    include_profiles = optional_bool(args, "include_profiles", default=True)
    include_sample_lists = optional_bool(args, "include_sample_lists", default=True)
    max_related = optional_int(args, "max_related", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"studies/{study_id}"
    params: JsonObject = {"projection": "DETAILED"}
    payload, headers = client.request_json_with_headers(endpoint, params)
    study = ensure_object(payload, study_id)
    profiles_payload: object | None = None
    sample_lists_payload: object | None = None
    profiles: list[JsonObject] = []
    sample_lists: list[JsonObject] = []
    if include_profiles:
        profiles_payload, _profile_headers = client.request_json_with_headers(f"studies/{study_id}/molecular-profiles", {"projection": "SUMMARY"})
        profiles = list_payload(profiles_payload)[:max_related]
    if include_sample_lists:
        sample_lists_payload, _sample_headers = client.request_json_with_headers(f"studies/{study_id}/sample-lists", {"projection": "SUMMARY"})
        sample_lists = list_payload(sample_lists_payload)[:max_related]
    record = cbioportal_study_record(
        study,
        profiles=profiles,
        sample_lists=sample_lists,
        api_base_url=client.config.api_base_url,
        website_base_url=client.config.website_base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "cbioportal",
        "query": study_id,
        "returned": 1,
        "study": study_summary(record),
        "records": [record],
        "source": source_with_headers(endpoint, params, headers, client.build_url(endpoint, params)),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = {"study": payload, "profiles": profiles_payload, "sample_lists": sample_lists_payload}
    return response


def cbioportal_molecular_profiles(args: JsonObject, client: CbioPortalClient) -> JsonObject:
    study_id = require_study_id(args)
    max_results = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"studies/{study_id}/molecular-profiles"
    params: JsonObject = {"projection": "SUMMARY"}
    payload, headers = client.request_json_with_headers(endpoint, params)
    rows = list_payload(payload)[:max_results]
    records = [cbioportal_profile_record(row, api_base_url=client.config.api_base_url, website_base_url=client.config.website_base_url) for row in rows]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "cbioportal",
        "query": study_id,
        "returned": len(records),
        "profiles": [profile_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, params, headers, client.build_url(endpoint, params)),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def cbioportal_sample_lists(args: JsonObject, client: CbioPortalClient) -> JsonObject:
    study_id = require_study_id(args)
    max_results = optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"studies/{study_id}/sample-lists"
    params: JsonObject = {"projection": "SUMMARY"}
    payload, headers = client.request_json_with_headers(endpoint, params)
    rows = list_payload(payload)[:max_results]
    records = [cbioportal_sample_list_record(row, api_base_url=client.config.api_base_url, website_base_url=client.config.website_base_url) for row in rows]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "cbioportal",
        "query": study_id,
        "returned": len(records),
        "sample_lists": [sample_list_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, params, headers, client.build_url(endpoint, params)),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def cbioportal_clinical_attributes(args: JsonObject, client: CbioPortalClient) -> JsonObject:
    study_id = require_study_id(args)
    max_results = optional_int(args, "max_results", default=MAX_CLINICAL_ATTRIBUTES, minimum=1, maximum=MAX_CLINICAL_ATTRIBUTES)
    include_raw = optional_bool(args, "include_raw", default=False)
    endpoint = f"studies/{study_id}/clinical-attributes"
    params: JsonObject = {"projection": "SUMMARY", "pageSize": max_results}
    payload, headers = client.request_json_with_headers(endpoint, params)
    rows = list_payload(payload)[:max_results]
    api_url = client.build_url(endpoint, params)
    record = cbioportal_clinical_attributes_record(
        study_id=study_id,
        attributes=rows,
        api_url=api_url,
        website_base_url=client.config.website_base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "cbioportal",
        "query": study_id,
        "returned": len(rows),
        "clinical_attributes": record["data"]["attributes"],
        "records": [record],
        "source": source_with_headers(endpoint, params, headers, api_url),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def cbioportal_clinical_data_fetch(args: JsonObject, client: CbioPortalClient) -> JsonObject:
    study_id = require_study_id(args)
    clinical_data_type = optional_clinical_data_type(args)
    clinical_attribute_ids = optional_identifier_list(args, "clinical_attribute_ids")
    if not clinical_attribute_ids:
        raise McpError(-32602, "clinical_attribute_ids must contain at least one attribute ID")
    if len(clinical_attribute_ids) > MAX_CLINICAL_ATTRIBUTES:
        raise McpError(-32602, f"clinical_attribute_ids can contain at most {MAX_CLINICAL_ATTRIBUTES} IDs")
    ids = optional_identifier_list(args, "ids")
    sample_list_id = optional_string(args, "sample_list_id")
    if sample_list_id:
        sample_list_id = require_sample_list_id({"sample_list_id": sample_list_id})
    max_ids = optional_int(args, "max_ids", default=DEFAULT_CLINICAL_IDS, minimum=1, maximum=MAX_CLINICAL_IDS)
    include_raw = optional_bool(args, "include_raw", default=False)
    if sample_list_id and clinical_data_type != "SAMPLE":
        raise McpError(-32602, "sample_list_id can only be used with SAMPLE clinical_data_type; provide patient ids for PATIENT data")
    if not ids and not sample_list_id:
        raise McpError(-32602, "Provide ids or sample_list_id")

    sample_ids_payload: object | None = None
    sample_ids_headers: dict[str, str] = {}
    sample_ids_api_url = ""
    if sample_list_id:
        sample_ids_endpoint = f"sample-lists/{sample_list_id}/sample-ids"
        sample_ids_payload, sample_ids_headers = client.request_json_with_headers(sample_ids_endpoint)
        sample_ids_api_url = client.build_url(sample_ids_endpoint)
        ids = list_string_payload(sample_ids_payload)
    ids = ids[:max_ids]

    endpoint = f"studies/{study_id}/clinical-data/fetch"
    params: JsonObject = {"clinicalDataType": clinical_data_type, "projection": "SUMMARY"}
    body: JsonObject = {"ids": ids, "attributeIds": clinical_attribute_ids}
    payload, headers = client.request_json_with_headers(endpoint, params, method="POST", json_body=body)
    rows = list_payload(payload)
    api_url = client.build_url(endpoint, params)
    record = cbioportal_clinical_data_record(
        study_id=study_id,
        clinical_data_type=clinical_data_type,
        ids=ids,
        sample_list_id=sample_list_id,
        attribute_ids=clinical_attribute_ids,
        values=rows,
        api_url=api_url,
        sample_ids_api_url=sample_ids_api_url,
        website_base_url=client.config.website_base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "cbioportal",
        "query": {
            "study_id": study_id,
            "clinical_data_type": clinical_data_type,
            "sample_list_id": sample_list_id,
            "ids": ids,
            "clinical_attribute_ids": clinical_attribute_ids,
        },
        "returned": len(rows),
        "clinical_values": record["data"]["values"],
        "clinical_matrix": record["data"]["matrix"],
        "records": [record],
        "source": source_with_headers(endpoint, params, headers, api_url, method="POST", body=body),
    }
    if sample_list_id:
        response["sample_ids_source"] = source_with_headers(f"sample-lists/{sample_list_id}/sample-ids", {}, sample_ids_headers, sample_ids_api_url)
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = {"sample_ids": sample_ids_payload, "clinical_data": payload}
    return response


def cbioportal_survival_data_fetch(args: JsonObject, client: CbioPortalClient) -> JsonObject:
    study_id = require_study_id(args)
    patient_ids = optional_identifier_list(args, "patient_ids")
    sample_ids = optional_identifier_list(args, "sample_ids")
    sample_list_id = optional_string(args, "sample_list_id")
    if sample_list_id:
        sample_list_id = require_sample_list_id({"sample_list_id": sample_list_id})
    survival_prefixes = optional_identifier_list(args, "survival_prefixes") or list(DEFAULT_SURVIVAL_PREFIXES)
    survival_prefixes = [prefix.upper() for prefix in survival_prefixes]
    if len(survival_prefixes) > MAX_SURVIVAL_PREFIXES:
        raise McpError(-32602, f"survival_prefixes can contain at most {MAX_SURVIVAL_PREFIXES} IDs")
    max_ids = optional_int(args, "max_ids", default=DEFAULT_CLINICAL_IDS, minimum=1, maximum=MAX_CLINICAL_IDS)
    include_raw = optional_bool(args, "include_raw", default=False)
    input_modes = sum(bool(value) for value in (patient_ids, sample_ids, sample_list_id))
    if input_modes != 1:
        raise McpError(-32602, "Provide exactly one of patient_ids, sample_ids, or sample_list_id")

    sample_ids_payload: object | None = None
    sample_ids_headers: dict[str, str] = {}
    sample_ids_api_url = ""
    if sample_list_id:
        sample_ids_endpoint = f"sample-lists/{sample_list_id}/sample-ids"
        sample_ids_payload, sample_ids_headers = client.request_json_with_headers(sample_ids_endpoint)
        sample_ids_api_url = client.build_url(sample_ids_endpoint)
        sample_ids = list_string_payload(sample_ids_payload)
    sample_ids = sample_ids[:max_ids]

    samples_payload: object | None = None
    samples_headers: dict[str, str] = {}
    samples_fetch_api_url = ""
    samples: list[JsonObject] = []
    if not patient_ids:
        if not sample_ids:
            raise McpError(-32602, "No sample IDs resolved for survival data fetch")
        samples_endpoint = "samples/fetch"
        samples_params: JsonObject = {"projection": "SUMMARY"}
        samples_body: JsonObject = {"sampleIdentifiers": [{"studyId": study_id, "sampleId": sample_id} for sample_id in sample_ids]}
        samples_payload, samples_headers = client.request_json_with_headers(samples_endpoint, samples_params, method="POST", json_body=samples_body)
        samples_fetch_api_url = client.build_url(samples_endpoint, samples_params)
        samples = list_payload(samples_payload)
        patient_ids = sorted({str(row.get("patientId")) for row in samples if row.get("patientId")})[:max_ids]
    else:
        patient_ids = patient_ids[:max_ids]
    if not patient_ids:
        raise McpError(-32602, "No patient IDs resolved for survival data fetch")

    endpoint = f"studies/{study_id}/clinical-data/fetch"
    params: JsonObject = {"clinicalDataType": "PATIENT", "projection": "SUMMARY"}
    attribute_ids = []
    for prefix in survival_prefixes:
        attribute_ids.extend([f"{prefix}_STATUS", f"{prefix}_MONTHS"])
    body: JsonObject = {"ids": patient_ids, "attributeIds": attribute_ids}
    payload, headers = client.request_json_with_headers(endpoint, params, method="POST", json_body=body)
    rows = list_payload(payload)
    api_url = client.build_url(endpoint, params)
    record = cbioportal_survival_data_record(
        study_id=study_id,
        sample_list_id=sample_list_id,
        sample_ids=sample_ids,
        patient_ids=patient_ids,
        survival_prefixes=survival_prefixes,
        samples=samples,
        values=rows,
        api_url=api_url,
        sample_ids_api_url=sample_ids_api_url,
        samples_fetch_api_url=samples_fetch_api_url,
        website_base_url=client.config.website_base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "cbioportal",
        "query": {
            "study_id": study_id,
            "sample_list_id": sample_list_id,
            "sample_ids": sample_ids,
            "patient_ids": patient_ids,
            "survival_prefixes": survival_prefixes,
        },
        "returned": len(record["data"]["survival_rows"]),
        "clinical_value_count": len(rows),
        "survival_rows": record["data"]["survival_rows"],
        "clinical_matrix": record["data"]["clinical_matrix"],
        "records": [record],
        "source": source_with_headers(endpoint, params, headers, api_url, method="POST", body=body),
    }
    if sample_ids_api_url:
        response["sample_ids_source"] = source_with_headers(f"sample-lists/{sample_list_id}/sample-ids", {}, sample_ids_headers, sample_ids_api_url)
    if samples_fetch_api_url:
        response["samples_source"] = source_with_headers("samples/fetch", {"projection": "SUMMARY"}, samples_headers, samples_fetch_api_url, method="POST", body={"sampleIdentifiers": [{"studyId": study_id, "sampleId": sample_id} for sample_id in sample_ids]})
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = {"sample_ids": sample_ids_payload, "samples": samples_payload, "clinical_data": payload}
    return response


def cbioportal_molecular_data_fetch(args: JsonObject, client: CbioPortalClient) -> JsonObject:
    molecular_profile_id = require_profile_id(args)
    sample_list_id = optional_string(args, "sample_list_id")
    sample_ids = optional_identifier_list(args, "sample_ids")
    if sample_list_id:
        sample_list_id = require_sample_list_id({"sample_list_id": sample_list_id})
    if bool(sample_list_id) == bool(sample_ids):
        raise McpError(-32602, "Provide exactly one of sample_list_id or sample_ids")
    if len(sample_ids) > MAX_CLINICAL_IDS:
        raise McpError(-32602, f"sample_ids can contain at most {MAX_CLINICAL_IDS} IDs")
    max_records = optional_int(args, "max_records", default=DEFAULT_MOLECULAR_ROWS, minimum=1, maximum=MAX_MOLECULAR_ROWS)
    entrez_gene_ids = optional_int_list(args, "entrez_gene_ids")
    hugo_gene_symbols = optional_symbol_list(args, "hugo_gene_symbols")
    include_raw = optional_bool(args, "include_raw", default=False)
    entrez_gene_ids, gene_map, gene_rows, requested_genes, warnings = resolve_gene_ids(client, entrez_gene_ids, hugo_gene_symbols)

    endpoint = f"molecular-profiles/{molecular_profile_id}/molecular-data/fetch"
    params: JsonObject = {"projection": "SUMMARY"}
    body: JsonObject = {"entrezGeneIds": entrez_gene_ids}
    if sample_list_id:
        body["sampleListId"] = sample_list_id
    else:
        body["sampleIds"] = sample_ids
    payload: object = []
    headers: dict[str, str] = {}
    if entrez_gene_ids:
        payload, headers, fetch_warning = request_fetch_json_or_empty(
            client,
            endpoint,
            params,
            body,
            molecular_profile_id=molecular_profile_id,
            sample_list_id=sample_list_id,
            sample_ids=sample_ids,
        )
        if fetch_warning:
            warnings.append(fetch_warning)
    else:
        warnings.append(empty_gene_request_warning(requested_genes))
    upstream_rows = list_payload(payload)
    append_empty_fetch_warning(
        client,
        warnings,
        endpoint=endpoint,
        body=body,
        molecular_profile_id=molecular_profile_id,
        sample_list_id=sample_list_id,
        sample_ids=sample_ids,
        entrez_gene_ids=entrez_gene_ids,
        upstream_rows=upstream_rows,
    )
    rows = upstream_rows[:max_records]
    api_url = client.build_url(endpoint, params)
    record = cbioportal_molecular_data_record(
        molecular_profile_id=molecular_profile_id,
        sample_list_id=sample_list_id,
        sample_ids=sample_ids,
        values=rows,
        gene_map=gene_map,
        requested_genes=requested_genes,
        api_url=api_url,
        upstream_returned=len(upstream_rows),
        api_base_url=client.config.api_base_url,
        website_base_url=client.config.website_base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "cbioportal",
        "query": {
            "molecular_profile_id": molecular_profile_id,
            "sample_list_id": sample_list_id,
            "sample_ids": sample_ids,
            "genes": requested_genes,
        },
        "returned": len(rows),
        "upstream_returned": len(upstream_rows),
        "total_truncated_to": max_records,
        "truncated": len(upstream_rows) > len(rows),
        "molecular_values": record["data"]["values"],
        "molecular_matrix": record["data"]["matrix"],
        "records": [record],
        "source": source_with_headers(endpoint, params, headers, api_url, method="POST", body=body),
    }
    attach_warnings(response, [record], warnings)
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = {"genes": gene_rows, "molecular_data": payload, "warnings": warnings}
    return response


def cbioportal_discrete_cna_fetch(args: JsonObject, client: CbioPortalClient) -> JsonObject:
    molecular_profile_id = require_profile_id(args)
    sample_list_id = optional_string(args, "sample_list_id")
    sample_ids = optional_identifier_list(args, "sample_ids")
    if sample_list_id:
        sample_list_id = require_sample_list_id({"sample_list_id": sample_list_id})
    if bool(sample_list_id) == bool(sample_ids):
        raise McpError(-32602, "Provide exactly one of sample_list_id or sample_ids")
    if len(sample_ids) > MAX_CLINICAL_IDS:
        raise McpError(-32602, f"sample_ids can contain at most {MAX_CLINICAL_IDS} IDs")
    max_records = optional_int(args, "max_records", default=DEFAULT_MOLECULAR_ROWS, minimum=1, maximum=MAX_MOLECULAR_ROWS)
    entrez_gene_ids = optional_int_list(args, "entrez_gene_ids")
    hugo_gene_symbols = optional_symbol_list(args, "hugo_gene_symbols")
    event_type = optional_string(args, "discrete_copy_number_event_type").upper() or "ALL"
    if event_type not in CNA_EVENT_TYPES:
        raise McpError(-32602, f"discrete_copy_number_event_type must be one of {', '.join(sorted(CNA_EVENT_TYPES))}")
    include_raw = optional_bool(args, "include_raw", default=False)
    entrez_gene_ids, gene_map, gene_rows, requested_genes, warnings = resolve_gene_ids(client, entrez_gene_ids, hugo_gene_symbols)

    endpoint = f"molecular-profiles/{molecular_profile_id}/discrete-copy-number/fetch"
    params: JsonObject = {"projection": "SUMMARY", "discreteCopyNumberEventType": event_type}
    body: JsonObject = {"entrezGeneIds": entrez_gene_ids}
    if sample_list_id:
        body["sampleListId"] = sample_list_id
    else:
        body["sampleIds"] = sample_ids
    payload: object = []
    headers: dict[str, str] = {}
    if entrez_gene_ids:
        payload, headers, fetch_warning = request_fetch_json_or_empty(
            client,
            endpoint,
            params,
            body,
            molecular_profile_id=molecular_profile_id,
            sample_list_id=sample_list_id,
            sample_ids=sample_ids,
        )
        if fetch_warning:
            warnings.append(fetch_warning)
    else:
        warnings.append(empty_gene_request_warning(requested_genes))
    upstream_rows = list_payload(payload)
    append_empty_fetch_warning(
        client,
        warnings,
        endpoint=endpoint,
        body=body,
        molecular_profile_id=molecular_profile_id,
        sample_list_id=sample_list_id,
        sample_ids=sample_ids,
        entrez_gene_ids=entrez_gene_ids,
        upstream_rows=upstream_rows,
    )
    rows = upstream_rows[:max_records]
    api_url = client.build_url(endpoint, params)
    record = cbioportal_discrete_cna_record(
        molecular_profile_id=molecular_profile_id,
        sample_list_id=sample_list_id,
        sample_ids=sample_ids,
        event_type=event_type,
        values=rows,
        gene_map=gene_map,
        requested_genes=requested_genes,
        api_url=api_url,
        upstream_returned=len(upstream_rows),
        api_base_url=client.config.api_base_url,
        website_base_url=client.config.website_base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "cbioportal",
        "query": {
            "molecular_profile_id": molecular_profile_id,
            "sample_list_id": sample_list_id,
            "sample_ids": sample_ids,
            "genes": requested_genes,
            "discrete_copy_number_event_type": event_type,
        },
        "returned": len(rows),
        "upstream_returned": len(upstream_rows),
        "total_truncated_to": max_records,
        "truncated": len(upstream_rows) > len(rows),
        "cna_values": record["data"]["values"],
        "cna_matrix": record["data"]["matrix"],
        "records": [record],
        "source": source_with_headers(endpoint, params, headers, api_url, method="POST", body=body),
    }
    attach_warnings(response, [record], warnings)
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = {"genes": gene_rows, "discrete_copy_number": payload, "warnings": warnings}
    return response


def cbioportal_mutations_fetch(args: JsonObject, client: CbioPortalClient) -> JsonObject:
    molecular_profile_id = require_profile_id(args)
    sample_list_id = require_sample_list_id(args)
    max_records = optional_int(args, "max_records", default=DEFAULT_MUTATIONS, minimum=1, maximum=MAX_MUTATIONS)
    entrez_gene_ids = optional_int_list(args, "entrez_gene_ids")
    hugo_gene_symbols = optional_symbol_list(args, "hugo_gene_symbols")
    include_raw = optional_bool(args, "include_raw", default=False)
    entrez_gene_ids, gene_map, gene_rows, requested_genes, warnings = resolve_gene_ids(client, entrez_gene_ids, hugo_gene_symbols)

    endpoint = f"molecular-profiles/{molecular_profile_id}/mutations/fetch"
    params: JsonObject = {"projection": "SUMMARY"}
    body: JsonObject = {"sampleListId": sample_list_id, "entrezGeneIds": entrez_gene_ids}
    payload: object = []
    headers: dict[str, str] = {}
    if entrez_gene_ids:
        payload, headers, fetch_warning = request_fetch_json_or_empty(
            client,
            endpoint,
            params,
            body,
            molecular_profile_id=molecular_profile_id,
            sample_list_id=sample_list_id,
            sample_ids=[],
        )
        if fetch_warning:
            warnings.append(fetch_warning)
    else:
        warnings.append(empty_gene_request_warning(requested_genes))
    upstream_rows = list_payload(payload)
    append_empty_fetch_warning(
        client,
        warnings,
        endpoint=endpoint,
        body=body,
        molecular_profile_id=molecular_profile_id,
        sample_list_id=sample_list_id,
        sample_ids=[],
        entrez_gene_ids=entrez_gene_ids,
        upstream_rows=upstream_rows,
    )
    rows = upstream_rows[:max_records]
    api_url = client.build_url(endpoint, params)
    record = cbioportal_mutations_record(
        molecular_profile_id=molecular_profile_id,
        sample_list_id=sample_list_id,
        mutations=rows,
        gene_map=gene_map,
        requested_genes=requested_genes,
        api_url=api_url,
        api_base_url=client.config.api_base_url,
        website_base_url=client.config.website_base_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "cbioportal",
        "query": {"molecular_profile_id": molecular_profile_id, "sample_list_id": sample_list_id, "genes": requested_genes},
        "returned": len(rows),
        "total_truncated_to": max_records,
        "mutations": record["data"]["mutations"],
        "records": [record],
        "source": source_with_headers(endpoint, params, headers, api_url, method="POST", body=body),
    }
    attach_warnings(response, [record], warnings)
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = {"genes": gene_rows, "mutations": payload, "warnings": warnings}
    return response


def resolve_gene_ids(client: CbioPortalClient, entrez_gene_ids: list[int], hugo_gene_symbols: list[str]) -> tuple[list[int], dict[int, str], list[JsonObject], list[str], list[JsonObject]]:
    if not entrez_gene_ids and not hugo_gene_symbols:
        raise McpError(-32602, "Provide at least one of entrez_gene_ids or hugo_gene_symbols")

    gene_rows: list[JsonObject] = []
    warnings: list[JsonObject] = []
    if hugo_gene_symbols:
        genes_payload, _gene_headers = client.request_json_with_headers(
            "genes/fetch",
            {"geneIdType": "HUGO_GENE_SYMBOL"},
            method="POST",
            json_body=hugo_gene_symbols,
        )
        gene_rows = list_payload(genes_payload)
        entrez_gene_ids.extend(int(row["entrezGeneId"]) for row in gene_rows if row.get("entrezGeneId") is not None)
        resolved_symbols = {str(row.get("hugoGeneSymbol", "")).upper() for row in gene_rows}
        unresolved_symbols = [symbol for symbol in hugo_gene_symbols if symbol.upper() not in resolved_symbols]
        if unresolved_symbols:
            warnings.append(
                {
                    "code": "unresolved_gene_symbols",
                    "message": "Some HUGO symbols were not resolved by cBioPortal genes/fetch and were omitted from the downstream request.",
                    "symbols": unresolved_symbols,
                    "source_endpoint": "genes/fetch",
                }
            )
    gene_map = {int(row["entrezGeneId"]): str(row.get("hugoGeneSymbol")) for row in gene_rows if row.get("entrezGeneId") is not None}
    unique_entrez_ids = sorted(set(entrez_gene_ids))
    requested_genes = hugo_gene_symbols or [str(gene_id) for gene_id in unique_entrez_ids]
    return unique_entrez_ids, gene_map, gene_rows, requested_genes, warnings


def request_fetch_json_or_empty(
    client: CbioPortalClient,
    endpoint: str,
    params: JsonObject,
    body: JsonObject,
    *,
    molecular_profile_id: str,
    sample_list_id: str | None,
    sample_ids: list[str],
) -> tuple[object, dict[str, str], JsonObject | None]:
    try:
        payload, headers = client.request_json_with_headers(endpoint, params, method="POST", json_body=body)
        return payload, headers, None
    except CbioPortalError as exc:
        if exc.status_code != 404:
            raise
        diagnosis = diagnose_fetch_not_found(client, molecular_profile_id, sample_list_id, sample_ids)
        return [], {}, fetch_not_found_warning(exc, endpoint, body, diagnosis)


def diagnose_fetch_not_found(
    client: CbioPortalClient,
    molecular_profile_id: str,
    sample_list_id: str | None,
    sample_ids: list[str],
) -> JsonObject:
    diagnosis: JsonObject = {
        "kind": "cbioportal_fetch_context",
        "status": "unknown",
        "molecular_profile": {
            "id": molecular_profile_id,
            "exists": None,
            "study_id": "",
            "api_url": client.build_url(f"molecular-profiles/{molecular_profile_id}", {"projection": "SUMMARY"}),
        },
        "sample_list": {
            "id": sample_list_id or "",
            "exists": None,
            "study_id": "",
            "api_url": client.build_url(f"sample-lists/{sample_list_id}", {"projection": "SUMMARY"}) if sample_list_id else "",
        },
        "sample_ids": {"count": len(sample_ids), "preview": sample_ids[:10]},
        "study_match": None,
        "checks": [],
    }

    profile = probe_single_record(client, f"molecular-profiles/{molecular_profile_id}", molecular_profile_id, "molecular_profile")
    diagnosis["checks"].append(profile["check"])
    diagnosis["molecular_profile"].update(profile["summary"])
    if profile["status"] == "not_found":
        diagnosis["status"] = "profile_not_found"
        diagnosis["summary"] = f"Molecular profile not found: {molecular_profile_id}"
        return diagnosis
    if profile["status"] == "error":
        diagnosis["status"] = "diagnosis_incomplete"
        diagnosis["summary"] = f"Could not verify molecular profile: {molecular_profile_id}"
        return diagnosis

    if sample_list_id:
        sample_list = probe_single_record(client, f"sample-lists/{sample_list_id}", sample_list_id, "sample_list")
        diagnosis["checks"].append(sample_list["check"])
        diagnosis["sample_list"].update(sample_list["summary"])
        if sample_list["status"] == "not_found":
            diagnosis["status"] = "sample_list_not_found"
            diagnosis["summary"] = f"Sample list not found: {sample_list_id}"
            return diagnosis
        if sample_list["status"] == "error":
            diagnosis["status"] = "diagnosis_incomplete"
            diagnosis["summary"] = f"Could not verify sample list: {sample_list_id}"
            return diagnosis

        profile_study = str(diagnosis["molecular_profile"].get("study_id") or "")
        sample_list_study = str(diagnosis["sample_list"].get("study_id") or "")
        if profile_study and sample_list_study:
            diagnosis["study_match"] = profile_study == sample_list_study
            if profile_study != sample_list_study:
                diagnosis["status"] = "study_mismatch"
                diagnosis["summary"] = f"Molecular profile study ({profile_study}) does not match sample list study ({sample_list_study})."
                return diagnosis

    diagnosis["status"] = "fetch_context_not_found"
    diagnosis["summary"] = "Molecular profile and sample context were found, but cBioPortal still returned 404 for the fetch endpoint."
    return diagnosis


def probe_single_record(client: CbioPortalClient, endpoint: str, identifier: str, target: str) -> JsonObject:
    check: JsonObject = {"target": target, "id": identifier, "endpoint": endpoint, "ok": False}
    summary: JsonObject = {"exists": None, "study_id": ""}
    try:
        payload, _headers = client.request_json_with_headers(endpoint, {"projection": "SUMMARY"})
    except CbioPortalError as exc:
        check["status_code"] = exc.status_code
        check["detail"] = exc.response_body[:300]
        if exc.status_code == 404:
            summary["exists"] = False
            return {"status": "not_found", "check": check, "summary": summary}
        return {"status": "error", "check": check, "summary": summary}

    if isinstance(payload, dict) and payload:
        check["ok"] = True
        summary["exists"] = True
        summary["study_id"] = str(payload.get("studyId") or "")
        if target == "molecular_profile":
            summary["name"] = str(payload.get("name") or "")
            summary["molecular_alteration_type"] = str(payload.get("molecularAlterationType") or "")
            summary["datatype"] = str(payload.get("datatype") or "")
        if target == "sample_list":
            summary["name"] = str(payload.get("name") or "")
            summary["category"] = str(payload.get("category") or "")
            summary["sample_count"] = payload.get("sampleCount") or 0
        return {"status": "ok", "check": check, "summary": summary}

    check["detail"] = "Empty or non-object payload"
    summary["exists"] = False
    return {"status": "not_found", "check": check, "summary": summary}


def fetch_not_found_warning(exc: CbioPortalError, endpoint: str, body: JsonObject, diagnosis: JsonObject) -> JsonObject:
    status = str(diagnosis.get("status") or "unknown")
    code_by_status = {
        "profile_not_found": "cbioportal_profile_not_found",
        "sample_list_not_found": "cbioportal_sample_list_not_found",
        "study_mismatch": "cbioportal_profile_sample_list_study_mismatch",
        "fetch_context_not_found": "cbioportal_fetch_context_not_found",
        "diagnosis_incomplete": "cbioportal_fetch_diagnosis_incomplete",
    }
    action_by_status = {
        "profile_not_found": "List molecular profiles for the intended study and retry with one of those IDs.",
        "sample_list_not_found": "List sample lists for the intended study and retry with one of those IDs.",
        "study_mismatch": "Use a molecular profile and sample list from the same cBioPortal study.",
        "fetch_context_not_found": "Treat this as unavailable data for the selected profile/sample/gene context, or try a different profile or cohort.",
        "diagnosis_incomplete": "Inspect the endpoint and retry; cBioPortal did not provide enough information for full classification.",
    }
    return {
        "code": code_by_status.get(status, "cbioportal_fetch_not_found"),
        "message": str(diagnosis.get("summary") or "cBioPortal returned HTTP 404 for this fetch. The MCP returned an empty result instead of aborting the whole batch."),
        "severity": "warning",
        "recoverable": True,
        "suggested_action": action_by_status.get(status, "Check the molecular profile, sample list, and requested data context."),
        "endpoint": endpoint,
        "status_code": exc.status_code,
        "detail": exc.response_body[:500],
        "body": body,
        "diagnosis": diagnosis,
    }


def append_empty_fetch_warning(
    client: CbioPortalClient,
    warnings: list[JsonObject],
    *,
    endpoint: str,
    body: JsonObject,
    molecular_profile_id: str,
    sample_list_id: str | None,
    sample_ids: list[str],
    entrez_gene_ids: list[int],
    upstream_rows: list[JsonObject],
) -> None:
    if upstream_rows or not entrez_gene_ids or any(isinstance(warning.get("diagnosis"), dict) for warning in warnings):
        return
    diagnosis = diagnose_fetch_not_found(client, molecular_profile_id, sample_list_id, sample_ids)
    warnings.append(fetch_empty_warning(endpoint, body, diagnosis))


def fetch_empty_warning(endpoint: str, body: JsonObject, diagnosis: JsonObject) -> JsonObject:
    status = str(diagnosis.get("status") or "unknown")
    code_by_status = {
        "profile_not_found": "cbioportal_profile_not_found",
        "sample_list_not_found": "cbioportal_sample_list_not_found",
        "study_mismatch": "cbioportal_profile_sample_list_study_mismatch",
        "fetch_context_not_found": "cbioportal_fetch_context_empty",
        "diagnosis_incomplete": "cbioportal_fetch_diagnosis_incomplete",
    }
    action_by_status = {
        "profile_not_found": "List molecular profiles for the intended study and retry with one of those IDs.",
        "sample_list_not_found": "List sample lists for the intended study and retry with one of those IDs.",
        "study_mismatch": "Use a molecular profile and sample list from the same cBioPortal study.",
        "fetch_context_not_found": "Treat this as no available rows for the selected profile/sample/gene context, or try a different profile or cohort.",
        "diagnosis_incomplete": "Inspect the endpoint and retry; cBioPortal did not provide enough information for full classification.",
    }
    message = str(diagnosis.get("summary") or "cBioPortal returned an empty payload for this fetch context.")
    if status == "fetch_context_not_found":
        message = "cBioPortal returned no rows, and the molecular profile/sample context appears valid."
    return {
        "code": code_by_status.get(status, "cbioportal_fetch_empty"),
        "message": message,
        "severity": "info" if status == "fetch_context_not_found" else "warning",
        "recoverable": True,
        "suggested_action": action_by_status.get(status, "Check the molecular profile, sample list, and requested data context."),
        "endpoint": endpoint,
        "status_code": 200,
        "body": body,
        "diagnosis": diagnosis,
    }


def empty_gene_request_warning(requested_genes: list[str]) -> JsonObject:
    return {
        "code": "no_resolved_entrez_gene_ids",
        "message": "No Entrez Gene IDs were resolved, so cBioPortal fetch was skipped and an empty result was returned.",
        "requested_genes": requested_genes,
    }


def attach_warnings(response: JsonObject, records: list[JsonObject], warnings: list[JsonObject]) -> None:
    if not warnings:
        return
    response["warnings"] = warnings
    diagnostics = [warning["diagnosis"] for warning in warnings if isinstance(warning.get("diagnosis"), dict)]
    if diagnostics:
        response["diagnostics"] = diagnostics
    for record in records:
        record.setdefault("data", {})["warnings"] = warnings
        if diagnostics:
            record["data"]["diagnostics"] = diagnostics
        display = record.get("display")
        if not isinstance(display, dict):
            continue
        metadata = display.get("metadata")
        if isinstance(metadata, list):
            codes = ", ".join(str(warning.get("code")) for warning in warnings if warning.get("code"))
            if codes:
                metadata.append({"label": "Warnings", "value": codes})
            summaries = [str(diagnosis.get("summary")) for diagnosis in diagnostics if diagnosis.get("summary")]
            if summaries:
                metadata.append({"label": "Diagnosis", "value": " | ".join(summaries)})
            hover = display.get("hover")
            if isinstance(hover, dict):
                hover["fields"] = metadata[:8]


def optional_context_type(args: JsonObject, name: str, *, allowed: list[str], default: str) -> str:
    value = optional_string(args, name) or default
    if value not in allowed:
        raise McpError(-32602, f"{name} must be one of: {', '.join(allowed)}")
    return value


def static_cbioportal_contexts(client: CbioPortalClient) -> list[JsonObject]:
    contexts: list[JsonObject] = [
        cbioportal_parameter_context(
            "context_type",
            value,
            label=value,
            description="Dynamic cBioPortal context family to resolve before making a data-fetch call.",
            kind="enum",
            url="",
            source_endpoint="resolve_context",
            metadata={"category": "context"},
        )
        for value in CBIOPORTAL_CONTEXT_TYPES
    ]
    contexts.extend(
        [
            cbioportal_parameter_context(
                "clinical_data_type",
                value,
                label=value,
                description="Clinical data entity type accepted by cbioportal_clinical_data_fetch.",
                kind="enum",
                url="",
                source_endpoint="schema",
                metadata={"tool_name": "cbioportal_clinical_data_fetch"},
            )
            for value in ["SAMPLE", "PATIENT"]
        ]
    )
    contexts.extend(
        cbioportal_parameter_context(
            "discrete_copy_number_event_type",
            value,
            label=value,
            description="Discrete copy-number event filter accepted by cbioportal_discrete_cna_fetch.",
            kind="enum",
            url="",
            source_endpoint="schema",
            metadata={"tool_name": "cbioportal_discrete_cna_fetch"},
        )
        for value in sorted(CNA_EVENT_TYPES)
    )
    contexts.append(
        cbioportal_parameter_context(
            "hugo_gene_symbols",
            "TP53",
            label="HUGO gene symbols",
            description="Open gene-symbol array resolved through cBioPortal genes/fetch before molecular-data calls.",
            kind="dynamic_array",
            url=client.build_url("genes/fetch", {"geneIdType": "HUGO_GENE_SYMBOL"}),
            source_endpoint="genes/fetch",
            metadata={"examples": ["TP53", "BRCA1", "MYC"], "alternative": "entrez_gene_ids"},
        )
    )
    return contexts


def cbioportal_parameter_context(
    parameter_name: str,
    value: object,
    *,
    label: str,
    description: str,
    kind: str,
    url: str,
    source_endpoint: str,
    metadata: JsonObject | None = None,
) -> JsonObject:
    metadata = metadata or {}
    group = cbioportal_context_group(parameter_name)
    display_fields = [{"label": key.replace("_", " ").title(), "value": item} for key, item in metadata.items() if item not in ("", None, [], {})]
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
        "source": source_endpoint,
        "metadata": metadata,
        "display": {
            "component": "dataset",
            "chip_label": parameter_name,
            "icon": "cbioportal",
            "title": label,
            "subtitle": f"{parameter_name}: {value}",
            "description": description,
            "metadata": display_fields,
            "badges": [
                {"label": "cBioPortal", "kind": "source"},
                {"label": parameter_name, "kind": "parameter"},
            ],
            "actions": [{"label": "Open source", "url": url, "kind": "external", "primary": True}] if url else [],
            "hover": {"title": label, "subtitle": f"{parameter_name}: {value}", "icon": "cbioportal", "fields": display_fields},
            "primary_url": url,
        },
    }


def cbioportal_context_group(parameter_name: str) -> str:
    return {
        "study_id": "studies",
        "molecular_profile_id": "profiles",
        "sample_list_id": "sample_lists",
        "clinical_attribute_ids": "clinical_attributes",
    }.get(parameter_name, "parameters")


def cbioportal_study_context(study: JsonObject, client: CbioPortalClient) -> JsonObject:
    record = cbioportal_study_record(
        study,
        api_base_url=client.config.api_base_url,
        website_base_url=client.config.website_base_url,
    )
    data = record["data"]
    return cbioportal_parameter_context(
        "study_id",
        data["study_id"],
        label=record["title"],
        description=record["description"],
        kind="study",
        url=data["url"],
        source_endpoint="studies",
        metadata={
            "study_id": data["study_id"],
            "cancer_type_id": data["cancer_type_id"],
            "all_sample_count": data["all_sample_count"],
            "sequenced_sample_count": data["sequenced_sample_count"],
        },
    )


def cbioportal_profile_context(profile: JsonObject, client: CbioPortalClient) -> JsonObject:
    record = cbioportal_profile_record(
        profile,
        api_base_url=client.config.api_base_url,
        website_base_url=client.config.website_base_url,
    )
    data = record["data"]
    return cbioportal_parameter_context(
        "molecular_profile_id",
        data["molecular_profile_id"],
        label=record["title"],
        description=record["description"],
        kind="molecular_profile",
        url=data["url"],
        source_endpoint="molecular-profiles",
        metadata={
            "study_id": data["study_id"],
            "molecular_alteration_type": data["molecular_alteration_type"],
            "datatype": data["datatype"],
            "tool_hint": profile_fetch_tool(profile),
        },
    )


def cbioportal_sample_list_context(sample_list: JsonObject, client: CbioPortalClient) -> JsonObject:
    record = cbioportal_sample_list_record(
        sample_list,
        api_base_url=client.config.api_base_url,
        website_base_url=client.config.website_base_url,
    )
    data = record["data"]
    return cbioportal_parameter_context(
        "sample_list_id",
        data["sample_list_id"],
        label=record["title"],
        description=record["description"],
        kind="sample_list",
        url=data["url"],
        source_endpoint="sample-lists",
        metadata={
            "study_id": data["study_id"],
            "category": data["category"],
            "sample_count": data["sample_count"],
        },
    )


def cbioportal_clinical_attribute_context(study_id: str, attribute: JsonObject, client: CbioPortalClient) -> JsonObject:
    attribute_id = str(attribute.get("clinicalAttributeId") or "")
    display_name = str(attribute.get("displayName") or attribute_id)
    description = str(attribute.get("description") or "cBioPortal clinical attribute")
    url = f"{client.config.website_base_url.rstrip('/')}/study/summary?id={study_id}"
    return cbioportal_parameter_context(
        "clinical_attribute_ids",
        attribute_id,
        label=display_name,
        description=description,
        kind="clinical_attribute",
        url=url,
        source_endpoint=f"studies/{study_id}/clinical-attributes",
        metadata={
            "study_id": study_id,
            "clinical_attribute_id": attribute_id,
            "datatype": attribute.get("datatype") or "",
            "patient_attribute": bool(attribute.get("patientAttribute")),
        },
    )


def first_matching_profile(profiles: list[JsonObject], molecular_profile_id: str) -> JsonObject:
    for profile in profiles:
        if profile.get("molecularProfileId") == molecular_profile_id:
            return profile
    return {}


def first_matching_sample_list(sample_lists: list[JsonObject], sample_list_id: str) -> JsonObject:
    for sample_list in sample_lists:
        if sample_list.get("sampleListId") == sample_list_id:
            return sample_list
    return {}


def read_optional_cbioportal_record(client: CbioPortalClient, endpoint: str, identifier: str, target: str) -> JsonObject:
    params: JsonObject = {"projection": "SUMMARY"}
    try:
        payload, headers = client.request_json_with_headers(endpoint, params)
        record = ensure_object(payload, identifier)
        return {
            "record": record,
            "sources": [source_with_headers(endpoint, params, headers, client.build_url(endpoint, params))],
            "diagnostics": [],
        }
    except CbioPortalError as exc:
        return {
            "record": {},
            "sources": [source_info(endpoint, params)],
            "diagnostics": [
                {
                    "code": f"cbioportal_{target}_not_found" if exc.status_code == 404 else f"cbioportal_{target}_lookup_failed",
                    "severity": "warning" if exc.status_code == 404 else "error",
                    "message": f"Could not resolve {target} {identifier}: {exc.response_body[:300] or str(exc)}",
                    "identifier": identifier,
                    "endpoint": endpoint,
                    "status_code": exc.status_code,
                    "url": client.build_url(endpoint, params),
                }
            ],
        }


def resolved_cbioportal_context(
    *,
    study_id: str,
    molecular_profile_id: str,
    sample_list_id: str,
    profile: JsonObject,
    sample_list: JsonObject,
) -> JsonObject:
    profile_study_id = str(profile.get("studyId") or "")
    sample_list_study_id = str(sample_list.get("studyId") or "")
    compatible: bool | None = None
    if profile_study_id and sample_list_study_id:
        compatible = profile_study_id == sample_list_study_id
    elif study_id and profile_study_id:
        compatible = profile_study_id == study_id
    elif study_id and sample_list_study_id:
        compatible = sample_list_study_id == study_id
    return {
        "study_id": study_id,
        "molecular_profile_id": molecular_profile_id,
        "sample_list_id": sample_list_id,
        "profile_study_id": profile_study_id,
        "sample_list_study_id": sample_list_study_id,
        "profile_type": str(profile.get("molecularAlterationType") or ""),
        "profile_datatype": str(profile.get("datatype") or ""),
        "compatible": compatible,
    }


def cbioportal_context_diagnostics(resolved: JsonObject) -> list[JsonObject]:
    diagnostics: list[JsonObject] = []
    study_id = str(resolved.get("study_id") or "")
    profile_study_id = str(resolved.get("profile_study_id") or "")
    sample_list_study_id = str(resolved.get("sample_list_study_id") or "")
    if study_id and profile_study_id and study_id != profile_study_id:
        diagnostics.append(
            {
                "code": "cbioportal_profile_study_mismatch",
                "severity": "error",
                "message": f"Molecular profile belongs to {profile_study_id}, not requested study {study_id}.",
                "recoverable": True,
                "suggested_action": "Use cbioportal_resolve_context with the profile study or choose a profile from the requested study.",
            }
        )
    if study_id and sample_list_study_id and study_id != sample_list_study_id:
        diagnostics.append(
            {
                "code": "cbioportal_sample_list_study_mismatch",
                "severity": "error",
                "message": f"Sample list belongs to {sample_list_study_id}, not requested study {study_id}.",
                "recoverable": True,
                "suggested_action": "Use a sample list from the same study as the molecular profile.",
            }
        )
    if profile_study_id and sample_list_study_id and profile_study_id != sample_list_study_id:
        diagnostics.append(
            {
                "code": "cbioportal_profile_sample_list_study_mismatch",
                "severity": "error",
                "message": f"Molecular profile study ({profile_study_id}) does not match sample list study ({sample_list_study_id}).",
                "recoverable": True,
                "suggested_action": "Resolve profiles and sample lists from one study before calling fetch tools.",
            }
        )
    return diagnostics


def recommended_cbioportal_calls(
    *,
    study_id: str,
    profile: JsonObject,
    sample_list: JsonObject,
    clinical_attributes: list[JsonObject],
    compatible: object,
) -> list[JsonObject]:
    calls: list[JsonObject] = []
    if study_id and not profile:
        calls.extend(
            [
                {
                    "tool_name": "cbioportal_molecular_profiles",
                    "arguments": {"study_id": study_id},
                    "reason": "List compatible molecular_profile_id values for this study.",
                },
                {
                    "tool_name": "cbioportal_sample_lists",
                    "arguments": {"study_id": study_id},
                    "reason": "List compatible sample_list_id values for this study.",
                },
                {
                    "tool_name": "cbioportal_clinical_attributes",
                    "arguments": {"study_id": study_id},
                    "reason": "List clinical_attribute_ids available for this study.",
                },
            ]
        )
    if profile and sample_list and compatible is not False:
        tool_name = profile_fetch_tool(profile)
        arguments: JsonObject = {
            "molecular_profile_id": str(profile.get("molecularProfileId") or ""),
            "sample_list_id": str(sample_list.get("sampleListId") or ""),
        }
        if tool_name == "cbioportal_discrete_cna_fetch":
            arguments["discrete_copy_number_event_type"] = "ALL"
        calls.append(
            {
                "tool_name": tool_name,
                "arguments": arguments,
                "requires": ["hugo_gene_symbols or entrez_gene_ids"],
                "reason": "Profile and sample list resolve to the same cBioPortal study.",
            }
        )
    if study_id and sample_list and clinical_attributes and compatible is not False:
        attribute_ids = [str(row.get("clinicalAttributeId")) for row in clinical_attributes if row.get("clinicalAttributeId")][:5]
        if attribute_ids:
            calls.append(
                {
                    "tool_name": "cbioportal_clinical_data_fetch",
                    "arguments": {
                        "study_id": study_id,
                        "sample_list_id": str(sample_list.get("sampleListId") or ""),
                        "clinical_attribute_ids": attribute_ids,
                    },
                    "reason": "Clinical attributes and sample list are available for this study.",
                }
            )
        calls.append(
            {
                "tool_name": "cbioportal_survival_data_fetch",
                "arguments": {
                    "study_id": study_id,
                    "sample_list_id": str(sample_list.get("sampleListId") or ""),
                    "survival_prefixes": list(DEFAULT_SURVIVAL_PREFIXES),
                },
                "reason": "Sample list can seed patient-level survival data fetches.",
            }
        )
    return calls


def profile_fetch_tool(profile: JsonObject) -> str:
    alteration_type = str(profile.get("molecularAlterationType") or "").upper()
    datatype = str(profile.get("datatype") or "").upper()
    if alteration_type == "MUTATION_EXTENDED":
        return "cbioportal_mutations_fetch"
    if alteration_type == "COPY_NUMBER_ALTERATION" and datatype == "DISCRETE":
        return "cbioportal_discrete_cna_fetch"
    return "cbioportal_molecular_data_fetch"


def context_matches(context: JsonObject, query: str) -> bool:
    if not query:
        return True
    needle = query.lower()
    fields = [
        context.get("parameter_name"),
        context.get("value"),
        context.get("label"),
        context.get("title"),
        context.get("description"),
        context.get("kind"),
    ]
    metadata = context.get("metadata")
    if isinstance(metadata, dict):
        fields.extend(metadata.values())
    return any(needle in str(field).lower() for field in fields if field not in (None, ""))


def ensure_object(payload: object, identifier: str) -> JsonObject:
    if isinstance(payload, dict) and payload:
        return payload
    raise CbioPortalError(f"cBioPortal record not found for {identifier}")


def list_payload(payload: object) -> list[JsonObject]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def list_string_payload(payload: object) -> list[str]:
    if isinstance(payload, list):
        return [str(item) for item in payload if isinstance(item, str) and item.strip()]
    return []


def study_summary(record: JsonObject) -> JsonObject:
    data = record["data"]
    return {"study_id": data["study_id"], "title": record["title"], "samples": data["all_sample_count"], "url": data["url"]}


def profile_summary(record: JsonObject) -> JsonObject:
    data = record["data"]
    return {"molecular_profile_id": data["molecular_profile_id"], "name": data["name"], "datatype": data["datatype"], "url": data["url"]}


def sample_list_summary(record: JsonObject) -> JsonObject:
    data = record["data"]
    return {"sample_list_id": data["sample_list_id"], "name": data["name"], "category": data["category"], "url": data["url"]}


def source_with_headers(
    endpoint: str,
    params: JsonObject,
    headers: dict[str, str],
    url: str,
    *,
    method: str = "GET",
    body: JsonObject | list[object] | None = None,
) -> JsonObject:
    source = source_info(endpoint, params, method=method, body=body)
    source["url"] = url
    if headers.get("content-type"):
        source["content_type"] = headers["content-type"]
    return source


def tool_definitions() -> list[JsonObject]:
    return [
        parameter_domains_tool_definition("cbioportal_parameter_domains"),
        {
            "name": "cbioportal_resolve_context",
            "title": "Resolve cBioPortal dynamic parameter context",
            "description": (
                "Resolve compatible cBioPortal study, molecular_profile_id, sample_list_id, and clinical_attribute_ids candidates "
                "before fetch calls. Returns front-end-friendly context rows, compatibility diagnostics, source URLs, and recommended calls."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "context_type": {
                        "type": "string",
                        "enum": CBIOPORTAL_CONTEXT_TYPES,
                        "default": "all",
                        "description": "Context family to resolve. Use fetch_context to validate profile/sample-list compatibility before data fetches.",
                    },
                    "query": {"type": "string", "description": "Optional text query for study search or client-side filtering of returned contexts."},
                    "study_id": {"type": "string", "description": "Optional cBioPortal study ID such as brca_tcga."},
                    "molecular_profile_id": {"type": "string", "description": "Optional molecular profile ID to validate and classify."},
                    "sample_list_id": {"type": "string", "description": "Optional sample list ID to validate against the profile or study."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "cbioportal_study_search",
            "title": "Search cBioPortal studies",
            "description": "Search public cBioPortal studies and return front-end-compatible cancer genomics project records.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword such as breast, lung, melanoma, TCGA, or CPTAC."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "cbioportal_study_lookup",
            "title": "Look up a cBioPortal study",
            "description": "Fetch one cBioPortal study by study ID with optional molecular profile and sample-list previews.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "study_id": {"type": "string", "description": "cBioPortal study ID, for example brca_tcga."},
                    "include_profiles": {"type": "boolean", "default": True},
                    "include_sample_lists": {"type": "boolean", "default": True},
                    "max_related": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["study_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "cbioportal_molecular_profiles",
            "title": "List cBioPortal molecular profiles",
            "description": "List molecular profiles for a cBioPortal study as front-end-compatible dataset records.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "study_id": {"type": "string", "description": "cBioPortal study ID, for example brca_tcga."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["study_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "cbioportal_sample_lists",
            "title": "List cBioPortal sample lists",
            "description": "List sample lists for a cBioPortal study as front-end-compatible dataset records.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "study_id": {"type": "string", "description": "cBioPortal study ID, for example brca_tcga."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["study_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "cbioportal_mutations_fetch",
            "title": "Fetch cBioPortal mutations for genes",
            "description": "Fetch bounded mutation rows from a cBioPortal molecular profile and sample list by Entrez Gene IDs or HUGO symbols.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "molecular_profile_id": {"type": "string", "description": "Mutation molecular profile ID, for example brca_tcga_mutations."},
                    "sample_list_id": {"type": "string", "description": "Sample list ID, for example brca_tcga_all."},
                    "entrez_gene_ids": {"type": "array", "items": {"type": "integer"}, "description": "Entrez Gene IDs such as 7157 for TP53."},
                    "hugo_gene_symbols": {"type": "array", "items": {"type": "string"}, "description": "HUGO symbols such as TP53 or BRCA1."},
                    "max_records": {"type": "integer", "minimum": 1, "maximum": MAX_MUTATIONS, "default": DEFAULT_MUTATIONS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["molecular_profile_id", "sample_list_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "cbioportal_molecular_data_fetch",
            "title": "Fetch cBioPortal molecular data matrix",
            "description": "Fetch bounded numeric molecular data rows, such as expression z-scores, and return table plus heatmap-matrix previews.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "molecular_profile_id": {"type": "string", "description": "Numeric molecular profile ID, for example brca_tcga_rna_seq_v2_mrna_median_Zscores."},
                    "sample_list_id": {"type": "string", "description": "Sample list ID, for example brca_tcga_all. Provide this or sample_ids, not both."},
                    "sample_ids": {"type": "array", "items": {"type": "string"}, "description": "Specific sample IDs. Provide this or sample_list_id, not both."},
                    "entrez_gene_ids": {"type": "array", "items": {"type": "integer"}, "description": "Entrez Gene IDs such as 7157 for TP53."},
                    "hugo_gene_symbols": {"type": "array", "items": {"type": "string"}, "description": "HUGO symbols such as TP53 or BRCA1."},
                    "max_records": {"type": "integer", "minimum": 1, "maximum": MAX_MOLECULAR_ROWS, "default": DEFAULT_MOLECULAR_ROWS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["molecular_profile_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "cbioportal_discrete_cna_fetch",
            "title": "Fetch cBioPortal discrete copy-number matrix",
            "description": "Fetch bounded GISTIC-style discrete copy-number calls and return table plus heatmap-matrix previews.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "molecular_profile_id": {"type": "string", "description": "Discrete CNA profile ID, for example brca_tcga_gistic."},
                    "sample_list_id": {"type": "string", "description": "Sample list ID, for example brca_tcga_all. Provide this or sample_ids, not both."},
                    "sample_ids": {"type": "array", "items": {"type": "string"}, "description": "Specific sample IDs. Provide this or sample_list_id, not both."},
                    "entrez_gene_ids": {"type": "array", "items": {"type": "integer"}, "description": "Entrez Gene IDs such as 7157 for TP53."},
                    "hugo_gene_symbols": {"type": "array", "items": {"type": "string"}, "description": "HUGO symbols such as TP53 or BRCA1."},
                    "discrete_copy_number_event_type": {
                        "type": "string",
                        "enum": sorted(CNA_EVENT_TYPES),
                        "default": "ALL",
                        "description": "cBioPortal event filter. ALL returns the full -2/-1/0/1/2 matrix.",
                    },
                    "max_records": {"type": "integer", "minimum": 1, "maximum": MAX_MOLECULAR_ROWS, "default": DEFAULT_MOLECULAR_ROWS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["molecular_profile_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "cbioportal_clinical_attributes",
            "title": "List cBioPortal clinical attributes",
            "description": "List clinical attribute definitions for a cBioPortal study as a front-end-compatible table record.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "study_id": {"type": "string", "description": "cBioPortal study ID, for example brca_tcga."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_CLINICAL_ATTRIBUTES, "default": MAX_CLINICAL_ATTRIBUTES},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["study_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "cbioportal_clinical_data_fetch",
            "title": "Fetch cBioPortal clinical data",
            "description": "Fetch bounded sample or patient clinical values for front-end cohort tables and filters.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "study_id": {"type": "string", "description": "cBioPortal study ID, for example brca_tcga."},
                    "clinical_data_type": {"type": "string", "enum": ["SAMPLE", "PATIENT"], "default": "SAMPLE"},
                    "ids": {"type": "array", "items": {"type": "string"}, "description": "Sample IDs for SAMPLE data or patient IDs for PATIENT data."},
                    "sample_list_id": {"type": "string", "description": "Sample list ID for SAMPLE data, for example brca_tcga_all."},
                    "clinical_attribute_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Clinical attribute IDs such as CANCER_TYPE, SAMPLE_TYPE, AGE, OS_STATUS, or OS_MONTHS.",
                    },
                    "max_ids": {"type": "integer", "minimum": 1, "maximum": MAX_CLINICAL_IDS, "default": DEFAULT_CLINICAL_IDS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["study_id", "clinical_attribute_ids"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "cbioportal_survival_data_fetch",
            "title": "Fetch cBioPortal survival data",
            "description": "Fetch bounded OS/DFS-style patient survival clinical fields and return chart-ready survival rows.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "study_id": {"type": "string", "description": "cBioPortal study ID, for example brca_tcga."},
                    "patient_ids": {"type": "array", "items": {"type": "string"}, "description": "Patient IDs such as TCGA-A1-A0SB."},
                    "sample_ids": {"type": "array", "items": {"type": "string"}, "description": "Sample IDs that will be mapped to patient IDs through samples/fetch."},
                    "sample_list_id": {"type": "string", "description": "Sample list ID to resolve bounded sample and patient IDs, for example brca_tcga_all."},
                    "survival_prefixes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Clinical survival endpoint prefixes such as OS, DFS, DSS, or PFS. Each prefix reads *_STATUS and *_MONTHS.",
                        "default": DEFAULT_SURVIVAL_PREFIXES,
                    },
                    "max_ids": {"type": "integer", "minimum": 1, "maximum": MAX_CLINICAL_IDS, "default": DEFAULT_CLINICAL_IDS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["study_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "cbioportal_status",
            "title": "Inspect cBioPortal MCP status",
            "description": "Return configured cBioPortal MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
    ]


TOOL_HANDLERS = {
    "cbioportal_parameter_domains": make_parameter_domains_handler("cbioportal", "cbioportal_parameter_domains", tool_definitions),
    "cbioportal_resolve_context": cbioportal_resolve_context,
    "cbioportal_study_search": cbioportal_study_search,
    "cbioportal_study_lookup": cbioportal_study_lookup,
    "cbioportal_molecular_profiles": cbioportal_molecular_profiles,
    "cbioportal_sample_lists": cbioportal_sample_lists,
    "cbioportal_mutations_fetch": cbioportal_mutations_fetch,
    "cbioportal_molecular_data_fetch": cbioportal_molecular_data_fetch,
    "cbioportal_discrete_cna_fetch": cbioportal_discrete_cna_fetch,
    "cbioportal_clinical_attributes": cbioportal_clinical_attributes,
    "cbioportal_clinical_data_fetch": cbioportal_clinical_data_fetch,
    "cbioportal_survival_data_fetch": cbioportal_survival_data_fetch,
    "cbioportal_status": cbioportal_status,
}
