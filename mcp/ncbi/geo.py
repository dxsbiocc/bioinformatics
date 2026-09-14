"""GEO DataSets tools and normalizers."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from .client import NcbiClient
from .constants import MAX_GEO_IDS, JsonObject
from .errors import McpError, NcbiError
from .schemas import with_geo_compat
from .utils import (
    normalize_space,
    optional_bool,
    optional_int,
    parse_count,
    require_non_empty_string,
    source_info,
)

GEO_ENTRY_TYPES = {
    "all": None,
    "gse": "gse",
    "gds": "gds",
    "gsm": "gsm",
    "gpl": "gpl",
}


def geo_series(args: JsonObject, client: NcbiClient) -> JsonObject:
    accession = coerce_gse_accession(args.get("accession") or args.get("gse"))
    include_raw = optional_bool(args, "include_raw", default=False)

    search_params: JsonObject = {
        "db": "gds",
        "term": f"{accession}[ACCN] AND gse[ETYP]",
        "retmode": "json",
        "retmax": 10,
    }
    search_payload = client.request_json("esearch.fcgi", search_params)
    search_result = search_payload.get("esearchresult")
    if not isinstance(search_result, dict):
        raise NcbiError("GEO series search response is missing esearchresult")

    uids = [str(uid) for uid in search_result.get("idlist", [])]
    response: JsonObject = {
        "database": "geo",
        "entrez_database": "gds",
        "accession": accession,
        "query": accession,
        "translated_query": search_result.get("querytranslation"),
        "count": parse_count(search_result.get("count")),
        "found": False,
        "uids": uids,
        "source": source_info("esearch.fcgi", search_params),
    }
    if not uids:
        return with_geo_compat(response)

    summary = geo_summaries_for_uids(uids, client, include_raw=include_raw)
    datasets = [
        dataset
        for dataset in summary.get("datasets", [])
        if isinstance(dataset, dict)
    ]
    exact = next(
        (
            dataset
            for dataset in datasets
            if normalize_space(dataset.get("accession")).upper() == accession
            and normalize_space(dataset.get("entry_type")).upper() == "GSE"
        ),
        None,
    )
    if exact is None and datasets:
        exact = datasets[0]

    response["returned"] = len(datasets)
    response["datasets"] = [exact] if exact else []
    response["related_datasets"] = [
        dataset for dataset in datasets if dataset is not exact
    ]
    response["summary_source"] = summary.get("source")
    if exact:
        response["found"] = True
        response["uid"] = exact.get("uid")
        response["series"] = exact
    return with_geo_compat(response)


def geo_search(args: JsonObject, client: NcbiClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=100)
    entry_type = normalize_geo_entry_type(args.get("entry_type", "all"))
    include_raw = optional_bool(args, "include_raw", default=False)

    entrez_term = query
    if entry_type:
        entrez_term = f"({query}) AND {entry_type}[ETYP]"
    search_params: JsonObject = {
        "db": "gds",
        "term": entrez_term,
        "retmode": "json",
        "retmax": max_results,
    }
    search_payload = client.request_json("esearch.fcgi", search_params)
    search_result = search_payload.get("esearchresult")
    if not isinstance(search_result, dict):
        raise NcbiError("GEO search response is missing esearchresult")

    uids = [str(uid) for uid in search_result.get("idlist", [])]
    response: JsonObject = {
        "database": "geo",
        "entrez_database": "gds",
        "query": query,
        "entry_type": entry_type or "all",
        "translated_query": search_result.get("querytranslation"),
        "count": parse_count(search_result.get("count")),
        "returned": len(uids),
        "uids": uids,
        "datasets": [],
        "source": source_info("esearch.fcgi", search_params),
    }
    if uids:
        summary = geo_summaries_for_uids(uids, client, include_raw=include_raw)
        datasets = summary.get("datasets", [])
        response["datasets"] = datasets
        response["returned"] = len(datasets) if isinstance(datasets, list) else 0
        response["summary_source"] = summary.get("source")
    return with_geo_compat(response)


def geo_summaries_for_uids(
    uids: list[str],
    client: NcbiClient,
    *,
    include_raw: bool = False,
) -> JsonObject:
    ids = coerce_geo_uids(uids)
    params: JsonObject = {
        "db": "gds",
        "id": ",".join(ids),
        "retmode": "json",
    }
    payload = client.request_json("esummary.fcgi", params)
    result = payload.get("result")
    if not isinstance(result, dict):
        raise NcbiError("GEO summary response is missing result")

    result_uids = result.get("uids", ids)
    datasets = []
    for uid in result_uids:
        record = result.get(str(uid))
        if not isinstance(record, dict):
            continue
        normalized = normalize_geo_summary(record)
        if include_raw:
            normalized["raw"] = record
        datasets.append(normalized)

    return with_geo_compat({
        "database": "geo",
        "entrez_database": "gds",
        "uids": ids,
        "returned": len(datasets),
        "datasets": datasets,
        "source": source_info("esummary.fcgi", params),
    })


def normalize_geo_summary(record: JsonObject) -> JsonObject:
    accession = normalize_space(record.get("accession")).upper()
    entry_type = normalize_space(record.get("entrytype")).upper()
    gse_number = normalize_space(record.get("gse"))
    if not accession and entry_type == "GSE" and gse_number:
        accession = f"GSE{gse_number}"

    platform_accession = normalize_geo_platform(record.get("gpl"))
    samples = normalize_geo_samples(record.get("samples"))
    pubmed_ids = [
        str(pmid)
        for pmid in record.get("pubmedids", [])
        if re.fullmatch(r"\d+", str(pmid))
    ]

    return {
        "uid": normalize_space(record.get("uid")),
        "accession": accession,
        "entry_type": entry_type,
        "title": normalize_space(record.get("title") or record.get("seriestitle")),
        "summary": normalize_space(record.get("summary")),
        "organism": normalize_space(record.get("taxon") or record.get("samplestaxa")),
        "taxon": normalize_space(record.get("taxon")),
        "study_type": normalize_space(record.get("gdstype")),
        "platform_technology": normalize_space(record.get("ptechtype")),
        "value_type": normalize_space(record.get("valtype")),
        "publication_date": normalize_space(record.get("pdat")),
        "sample_count": parse_count(record.get("n_samples")),
        "samples": samples,
        "sample_accessions": [sample["accession"] for sample in samples],
        "platform": {
            "accession": platform_accession,
            "title": normalize_space(record.get("platformtitle")),
            "organism": normalize_space(record.get("platformtaxa")),
        },
        "pubmed_ids": pubmed_ids,
        "bioproject": normalize_space(record.get("bioproject")),
        "geo2r": normalize_space(record.get("geo2r")),
        "supplementary_files": normalize_space(record.get("suppfile")),
        "ftp": geo_https_url(normalize_space(record.get("ftplink")))
        or geo_series_ftp_base(accession),
        "url": geo_accession_url(accession),
        "download_links": geo_download_links(accession, normalize_space(record.get("ftplink"))),
        "raw_relations": record.get("relations", []),
        "raw_external_relations": record.get("extrelations", []),
        "projects": record.get("projects", []),
    }


def normalize_geo_samples(value: Any) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    samples = []
    for item in value:
        if not isinstance(item, dict):
            continue
        accession = normalize_space(item.get("accession")).upper()
        if not accession:
            continue
        samples.append(
            {
                "accession": accession,
                "title": normalize_space(item.get("title")),
                "url": geo_accession_url(accession),
            }
        )
    return samples


def normalize_geo_platform(value: Any) -> str:
    platform = normalize_space(value).upper()
    if not platform:
        return ""
    if platform.startswith("GPL"):
        return platform
    if platform.isdigit():
        return f"GPL{platform}"
    return platform


def normalize_geo_entry_type(value: Any) -> str | None:
    normalized = str(value).strip().lower()
    if normalized not in GEO_ENTRY_TYPES:
        raise McpError(-32602, "entry_type must be one of: all, gse, gds, gsm, gpl")
    return GEO_ENTRY_TYPES[normalized]


def coerce_gse_accession(value: Any) -> str:
    accession = normalize_space(value).upper()
    if not re.fullmatch(r"GSE\d+", accession):
        raise McpError(-32602, "accession must be a GEO Series accession like GSE100")
    return accession


def coerce_geo_uids(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_ids: Iterable[Any] = re.split(r"[\s,;]+", value.strip())
    elif isinstance(value, list):
        raw_ids = value
    else:
        raise McpError(-32602, "uids must be a UID string or an array of UIDs")

    ids = []
    seen = set()
    for item in raw_ids:
        uid = str(item).strip()
        if not uid:
            continue
        if not re.fullmatch(r"\d+", uid):
            raise McpError(-32602, f"Invalid GEO UID: {uid}")
        if uid not in seen:
            seen.add(uid)
            ids.append(uid)
    if not ids:
        raise McpError(-32602, "At least one GEO UID is required")
    if len(ids) > MAX_GEO_IDS:
        raise McpError(-32602, f"At most {MAX_GEO_IDS} GEO UIDs may be requested")
    return ids


def geo_accession_url(accession: str) -> str:
    accession = normalize_space(accession).upper()
    if not accession:
        return ""
    return f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={accession}"


def geo_series_ftp_base(accession: str) -> str:
    accession = normalize_space(accession).upper()
    match = re.fullmatch(r"GSE(\d+)", accession)
    if not match:
        return ""
    digits = match.group(1)
    bucket = f"GSE{digits[:-3]}nnn"
    return f"https://ftp.ncbi.nlm.nih.gov/geo/series/{bucket}/{accession}/"


def geo_https_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("ftp://ftp.ncbi.nlm.nih.gov/"):
        return "https://ftp.ncbi.nlm.nih.gov/" + url.removeprefix(
            "ftp://ftp.ncbi.nlm.nih.gov/"
        )
    return url


def geo_download_links(accession: str, ftplink: str = "") -> list[JsonObject]:
    accession = normalize_space(accession).upper()
    base = geo_https_url(ftplink) or geo_series_ftp_base(accession)
    if not accession or not base:
        return []
    base = base.rstrip("/") + "/"
    return [
        {
            "label": "GEO FTP directory",
            "url": base,
            "kind": "external",
            "primary": False,
        },
        {
            "label": "SOFT family file",
            "url": f"{base}soft/{accession}_family.soft.gz",
            "kind": "download",
            "primary": False,
        },
        {
            "label": "Series matrix",
            "url": f"{base}matrix/{accession}_series_matrix.txt.gz",
            "kind": "download",
            "primary": False,
        },
        {
            "label": "Supplementary files",
            "url": f"{base}suppl/",
            "kind": "external",
            "primary": False,
        },
    ]
