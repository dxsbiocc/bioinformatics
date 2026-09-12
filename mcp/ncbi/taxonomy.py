"""NCBI Taxonomy lookup tools."""

from __future__ import annotations

import re

from .client import NcbiClient
from .constants import JsonObject
from .errors import NcbiError
from .records import taxonomy_url, with_taxonomy_compat
from .utils import (
    normalize_space,
    optional_bool,
    optional_int,
    parse_count,
    require_non_empty_string,
    source_info,
)


def taxonomy_lookup(args: JsonObject, client: NcbiClient) -> JsonObject:
    query = normalize_space(args.get("query") or args.get("taxid") or args.get("name"))
    if not query:
        query = require_non_empty_string(args, "query")
    exact = optional_bool(args, "exact", default=True)
    max_results = optional_int(args, "max_results", default=5, minimum=1, maximum=50)
    include_raw = optional_bool(args, "include_raw", default=False)

    if re.fullmatch(r"\d+", query):
        summary = taxonomy_summaries_for_ids([query], client, include_raw=include_raw)
        summary["query"] = query
        return summary

    term = f"{query}[Scientific Name]" if exact else query
    search_params: JsonObject = {
        "db": "taxonomy",
        "term": term,
        "retmode": "json",
        "retmax": max_results,
    }
    search_payload = client.request_json("esearch.fcgi", search_params)
    search_result = search_payload.get("esearchresult")
    if not isinstance(search_result, dict):
        raise NcbiError("Taxonomy search response is missing esearchresult")

    ids = [str(taxid) for taxid in search_result.get("idlist", [])]
    response: JsonObject = {
        "database": "taxonomy",
        "query": query,
        "exact": exact,
        "translated_query": search_result.get("querytranslation"),
        "count": parse_count(search_result.get("count")),
        "returned": len(ids),
        "taxids": ids,
        "taxa": [],
        "source": source_info("esearch.fcgi", search_params),
    }
    if ids:
        summary = taxonomy_summaries_for_ids(ids, client, include_raw=include_raw)
        response["taxa"] = summary.get("taxa", [])
        response["returned"] = len(response["taxa"])
        response["summary_source"] = summary.get("source")
    return with_taxonomy_compat(response)


def taxonomy_summaries_for_ids(
    ids: list[str],
    client: NcbiClient,
    *,
    include_raw: bool = False,
) -> JsonObject:
    params: JsonObject = {
        "db": "taxonomy",
        "id": ",".join(ids),
        "retmode": "json",
    }
    payload = client.request_json("esummary.fcgi", params)
    result = payload.get("result")
    if not isinstance(result, dict):
        raise NcbiError("Taxonomy summary response is missing result")

    taxa = []
    for uid in result.get("uids", ids):
        record = result.get(str(uid))
        if not isinstance(record, dict):
            continue
        normalized = normalize_taxonomy_summary(record)
        if include_raw:
            normalized["raw"] = record
        taxa.append(normalized)

    return with_taxonomy_compat(
        {
            "database": "taxonomy",
            "taxids": ids,
            "returned": len(taxa),
            "taxa": taxa,
            "source": source_info("esummary.fcgi", params),
        }
    )


def normalize_taxonomy_summary(record: JsonObject) -> JsonObject:
    taxid = normalize_space(record.get("taxid") or record.get("uid"))
    return {
        "taxid": taxid,
        "scientific_name": normalize_space(record.get("scientificname")),
        "common_name": normalize_space(record.get("commonname")),
        "status": normalize_space(record.get("status")),
        "rank": normalize_space(record.get("rank")),
        "division": normalize_space(record.get("division")),
        "genbank_division": normalize_space(record.get("genbankdivision")),
        "modification_date": normalize_space(record.get("modificationdate")),
        "aka_taxid": normalize_space(record.get("akataxid")),
        "genus": normalize_space(record.get("genus")),
        "species": normalize_space(record.get("species")),
        "subspecies": normalize_space(record.get("subsp")),
        "url": taxonomy_url(taxid),
    }
