"""NCBI Gene lookup tools."""

from __future__ import annotations

import re
from typing import Any

from .client import NcbiClient
from .constants import JsonObject
from .errors import NcbiError
from .records import gene_url, taxonomy_url, with_gene_compat
from .utils import (
    normalize_space,
    optional_bool,
    optional_int,
    parse_count,
    require_non_empty_string,
    source_info,
)


def gene_lookup(args: JsonObject, client: NcbiClient) -> JsonObject:
    query = normalize_space(
        args.get("query") or args.get("symbol") or args.get("gene_id")
    )
    if not query:
        query = require_non_empty_string(args, "query")
    organism = normalize_space(args.get("organism"))
    max_results = optional_int(args, "max_results", default=5, minimum=1, maximum=50)
    include_raw = optional_bool(args, "include_raw", default=False)

    if re.fullmatch(r"\d+", query):
        summary = gene_summaries_for_ids([query], client, include_raw=include_raw)
        summary["query"] = query
        return summary

    term = f"{query}[Gene Name]"
    if organism:
        term = f"{term} AND {organism}[Organism]"
    search_params: JsonObject = {
        "db": "gene",
        "term": term,
        "retmode": "json",
        "retmax": max_results,
    }
    search_payload = client.request_json("esearch.fcgi", search_params)
    search_result = search_payload.get("esearchresult")
    if not isinstance(search_result, dict):
        raise NcbiError("Gene search response is missing esearchresult")

    ids = [str(gene_id) for gene_id in search_result.get("idlist", [])]
    response: JsonObject = {
        "database": "gene",
        "query": query,
        "organism": organism or None,
        "translated_query": search_result.get("querytranslation"),
        "count": parse_count(search_result.get("count")),
        "returned": len(ids),
        "gene_ids": ids,
        "genes": [],
        "source": source_info("esearch.fcgi", search_params),
    }
    if ids:
        summary = gene_summaries_for_ids(ids, client, include_raw=include_raw)
        response["genes"] = summary.get("genes", [])
        response["returned"] = len(response["genes"])
        response["summary_source"] = summary.get("source")
    return with_gene_compat(response)


def gene_summaries_for_ids(
    ids: list[str],
    client: NcbiClient,
    *,
    include_raw: bool = False,
) -> JsonObject:
    params: JsonObject = {
        "db": "gene",
        "id": ",".join(ids),
        "retmode": "json",
    }
    payload = client.request_json("esummary.fcgi", params)
    result = payload.get("result")
    if not isinstance(result, dict):
        raise NcbiError("Gene summary response is missing result")

    genes = []
    for uid in result.get("uids", ids):
        record = result.get(str(uid))
        if not isinstance(record, dict):
            continue
        normalized = normalize_gene_summary(record)
        if include_raw:
            normalized["raw"] = record
        genes.append(normalized)

    return with_gene_compat(
        {
            "database": "gene",
            "gene_ids": ids,
            "returned": len(genes),
            "genes": genes,
            "source": source_info("esummary.fcgi", params),
        }
    )


def normalize_gene_summary(record: JsonObject) -> JsonObject:
    gene_id = normalize_space(record.get("uid"))
    organism = record.get("organism") if isinstance(record.get("organism"), dict) else {}
    genomic_info = record.get("genomicinfo")
    genomic_info = genomic_info if isinstance(genomic_info, list) else []
    return {
        "gene_id": gene_id,
        "symbol": normalize_space(record.get("name")),
        "description": normalize_space(record.get("description")),
        "status": normalize_space(record.get("status")),
        "current_id": normalize_space(record.get("currentid")),
        "chromosome": normalize_space(record.get("chromosome")),
        "map_location": normalize_space(record.get("maplocation")),
        "genetic_source": normalize_space(record.get("geneticsource")),
        "aliases": split_comma_list(record.get("otheraliases")),
        "other_designations": split_pipe_list(record.get("otherdesignations")),
        "nomenclature_symbol": normalize_space(record.get("nomenclaturesymbol")),
        "nomenclature_name": normalize_space(record.get("nomenclaturename")),
        "nomenclature_status": normalize_space(record.get("nomenclaturestatus")),
        "mim_ids": [str(mim_id) for mim_id in record.get("mim", [])],
        "summary": normalize_space(record.get("summary")),
        "organism": {
            "scientific_name": normalize_space(organism.get("scientificname")),
            "common_name": normalize_space(organism.get("commonname")),
            "taxid": str(organism.get("taxid")) if organism.get("taxid") else "",
            "url": taxonomy_url(str(organism.get("taxid"))) if organism.get("taxid") else "",
        },
        "genomic_locations": [
            normalize_genomic_location(item)
            for item in genomic_info
            if isinstance(item, dict)
        ],
        "url": gene_url(gene_id),
    }


def normalize_genomic_location(item: JsonObject) -> JsonObject:
    return {
        "chromosome": normalize_space(item.get("chrloc")),
        "accession": normalize_space(item.get("chraccver")),
        "start": item.get("chrstart"),
        "stop": item.get("chrstop"),
        "exon_count": item.get("exoncount"),
    }


def split_comma_list(value: Any) -> list[str]:
    return [
        item.strip()
        for item in normalize_space(value).split(",")
        if item.strip()
    ]


def split_pipe_list(value: Any) -> list[str]:
    return [
        item.strip()
        for item in normalize_space(value).split("|")
        if item.strip()
    ]
