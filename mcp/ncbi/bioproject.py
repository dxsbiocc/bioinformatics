"""NCBI BioProject lookup tools."""

from __future__ import annotations

import re

from .client import NcbiClient
from .constants import JsonObject
from .errors import NcbiError
from .omics_records import with_bioproject_compat
from .records import bioproject_url, taxonomy_url
from .utils import (
    normalize_space,
    optional_bool,
    optional_int,
    parse_count,
    require_non_empty_string,
    source_info,
)

BIOPROJECT_ACCESSION_RE = re.compile(r"^PRJ[A-Z]{1,4}\d+$", re.IGNORECASE)


def bioproject_lookup(args: JsonObject, client: NcbiClient) -> JsonObject:
    query = normalize_space(
        args.get("query") or args.get("accession") or args.get("project_id")
    )
    if not query:
        query = require_non_empty_string(args, "query")
    max_results = optional_int(args, "max_results", default=5, minimum=1, maximum=50)
    include_raw = optional_bool(args, "include_raw", default=False)

    if re.fullmatch(r"\d+", query):
        summary = bioproject_summaries_for_ids(
            [query],
            client,
            include_raw=include_raw,
        )
        summary["query"] = query
        return summary

    term = bioproject_search_term(query)
    search_params: JsonObject = {
        "db": "bioproject",
        "term": term,
        "retmode": "json",
        "retmax": max_results,
    }
    search_payload = client.request_json("esearch.fcgi", search_params)
    search_result = search_payload.get("esearchresult")
    if not isinstance(search_result, dict):
        raise NcbiError("BioProject search response is missing esearchresult")

    ids = [str(project_id) for project_id in search_result.get("idlist", [])]
    response: JsonObject = {
        "database": "bioproject",
        "query": query,
        "translated_query": search_result.get("querytranslation"),
        "count": parse_count(search_result.get("count")),
        "returned": len(ids),
        "bioproject_ids": ids,
        "projects": [],
        "source": source_info("esearch.fcgi", search_params),
    }
    if ids:
        summary = bioproject_summaries_for_ids(
            ids,
            client,
            include_raw=include_raw,
        )
        response["projects"] = summary.get("projects", [])
        response["returned"] = len(response["projects"])
        response["summary_source"] = summary.get("source")
    return with_bioproject_compat(response)


def bioproject_summaries_for_ids(
    ids: list[str],
    client: NcbiClient,
    *,
    include_raw: bool = False,
) -> JsonObject:
    params: JsonObject = {
        "db": "bioproject",
        "id": ",".join(ids),
        "retmode": "json",
    }
    payload = client.request_json("esummary.fcgi", params)
    result = payload.get("result")
    if not isinstance(result, dict):
        raise NcbiError("BioProject summary response is missing result")

    projects = []
    for uid in result.get("uids", ids):
        record = result.get(str(uid))
        if not isinstance(record, dict):
            continue
        normalized = normalize_bioproject_summary(record)
        if include_raw:
            normalized["raw"] = record
        projects.append(normalized)

    return with_bioproject_compat(
        {
            "database": "bioproject",
            "bioproject_ids": ids,
            "returned": len(projects),
            "projects": projects,
            "source": source_info("esummary.fcgi", params),
        }
    )


def normalize_bioproject_summary(record: JsonObject) -> JsonObject:
    uid = normalize_space(record.get("uid"))
    project_id = normalize_space(record.get("project_id") or uid)
    accession = normalize_space(record.get("project_acc"))
    taxid = normalize_space(record.get("taxid"))
    return {
        "uid": uid,
        "project_id": project_id,
        "accession": accession,
        "project_type": normalize_space(record.get("project_type")),
        "data_type": normalize_space(record.get("project_data_type")),
        "subtype": normalize_space(record.get("project_subtype")),
        "target_scope": normalize_space(record.get("project_target_scope")),
        "target_material": normalize_space(record.get("project_target_material")),
        "target_capture": normalize_space(record.get("project_target_capture")),
        "method_type": normalize_space(record.get("project_methodtype")),
        "method": normalize_space(record.get("project_method")),
        "objectives": normalize_bioproject_objectives(record.get("project_objectives_list")),
        "registration_date": normalize_space(record.get("registration_date")),
        "name": normalize_space(record.get("project_name")),
        "title": normalize_space(record.get("project_title")),
        "description": normalize_space(record.get("project_description")),
        "keyword": normalize_space(record.get("keyword")),
        "relevance": normalize_bioproject_relevance(record),
        "organism": {
            "scientific_name": normalize_space(record.get("organism_name")),
            "strain": normalize_space(record.get("organism_strain")),
            "label": normalize_space(record.get("organism_label")),
            "taxid": taxid,
            "supergroup": normalize_space(record.get("supergroup")),
            "url": taxonomy_url(taxid) if taxid else "",
        },
        "sequencing_status": normalize_space(record.get("sequencing_status")),
        "submitter_organization": normalize_space(record.get("submitter_organization")),
        "submitter_organizations": [
            normalize_space(item)
            for item in record.get("submitter_organization_list", [])
            if normalize_space(item)
        ],
        "url": bioproject_url(accession or project_id),
    }


def bioproject_search_term(query: str) -> str:
    if BIOPROJECT_ACCESSION_RE.fullmatch(query):
        return f"{query.upper()}[PRJA]"
    return query


def normalize_bioproject_objectives(value: object) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    objectives = []
    for item in value:
        if not isinstance(item, dict):
            continue
        objective_type = normalize_space(item.get("project_objectivestype"))
        objective = normalize_space(item.get("project_objectives"))
        if objective_type or objective:
            objectives.append({"type": objective_type, "description": objective})
    return objectives


def normalize_bioproject_relevance(record: JsonObject) -> JsonObject:
    keys = {
        "agricultural": "relevance_agricultural",
        "medical": "relevance_medical",
        "industrial": "relevance_industrial",
        "environmental": "relevance_environmental",
        "evolution": "relevance_evolution",
        "model": "relevance_model",
        "other": "relevance_other",
    }
    return {
        label: normalize_space(record.get(source))
        for label, source in keys.items()
        if normalize_space(record.get(source))
    }
