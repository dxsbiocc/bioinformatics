"""NCBI SRA lookup and search tools."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .client import NcbiClient
from .constants import JsonObject
from .errors import NcbiError
from .omics_records import with_sra_compat
from .records import bioproject_url, biosample_url, sra_url, taxonomy_url
from .utils import (
    element_text,
    normalize_space,
    optional_bool,
    optional_int,
    parse_count,
    require_non_empty_string,
    source_info,
    text_from_child,
)

SRA_ACCESSION_RE = re.compile(
    r"^(SRR|ERR|DRR|SRX|ERX|DRX|SRS|ERS|DRS|SRP|ERP|DRP|SRA|ERA|DRA)\d+$",
    re.IGNORECASE,
)


def sra_lookup(args: JsonObject, client: NcbiClient) -> JsonObject:
    query = normalize_space(args.get("query") or args.get("accession") or args.get("uid"))
    if not query:
        query = require_non_empty_string(args, "query")
    max_results = optional_int(args, "max_results", default=5, minimum=1, maximum=50)
    include_raw = optional_bool(args, "include_raw", default=False)

    if re.fullmatch(r"\d+", query):
        summary = sra_summaries_for_ids([query], client, include_raw=include_raw)
        summary["query"] = query
        return summary

    term = f"{query.upper()}[ACCN]" if SRA_ACCESSION_RE.fullmatch(query) else query
    return search_sra_term(
        term,
        client,
        query=query,
        max_results=max_results,
        include_raw=include_raw,
    )


def sra_search(args: JsonObject, client: NcbiClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    organism = normalize_space(args.get("organism"))
    strategy = normalize_space(args.get("strategy"))
    source = normalize_space(args.get("source"))
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=100)
    include_raw = optional_bool(args, "include_raw", default=False)

    term_parts = [query]
    if organism:
        term_parts.append(f"{organism}[Organism]")
    if strategy:
        term_parts.append(f"{strategy}[Strategy]")
    if source:
        term_parts.append(f"{source}[Source]")
    return search_sra_term(
        " AND ".join(term_parts),
        client,
        query=query,
        max_results=max_results,
        include_raw=include_raw,
        extra_response={
            "organism": organism or None,
            "strategy": strategy or None,
            "source_filter": source or None,
        },
    )


def search_sra_term(
    term: str,
    client: NcbiClient,
    *,
    query: str,
    max_results: int,
    include_raw: bool,
    extra_response: JsonObject | None = None,
) -> JsonObject:
    search_params: JsonObject = {
        "db": "sra",
        "term": term,
        "retmode": "json",
        "retmax": max_results,
    }
    search_payload = client.request_json("esearch.fcgi", search_params)
    search_result = search_payload.get("esearchresult")
    if not isinstance(search_result, dict):
        raise NcbiError("SRA search response is missing esearchresult")

    ids = [str(sra_id) for sra_id in search_result.get("idlist", [])]
    response: JsonObject = {
        "database": "sra",
        "query": query,
        "translated_query": search_result.get("querytranslation"),
        "count": parse_count(search_result.get("count")),
        "returned": len(ids),
        "sra_ids": ids,
        "experiments": [],
        "source": source_info("esearch.fcgi", search_params),
    }
    if extra_response:
        response.update(extra_response)
    if ids:
        summary = sra_summaries_for_ids(ids, client, include_raw=include_raw)
        response["experiments"] = summary.get("experiments", [])
        response["returned"] = len(response["experiments"])
        response["summary_source"] = summary.get("source")
    return with_sra_compat(response)


def sra_summaries_for_ids(
    ids: list[str],
    client: NcbiClient,
    *,
    include_raw: bool = False,
) -> JsonObject:
    params: JsonObject = {
        "db": "sra",
        "id": ",".join(ids),
        "retmode": "json",
    }
    payload = client.request_json("esummary.fcgi", params)
    result = payload.get("result")
    if not isinstance(result, dict):
        raise NcbiError("SRA summary response is missing result")

    experiments = []
    for uid in result.get("uids", ids):
        record = result.get(str(uid))
        if not isinstance(record, dict):
            continue
        normalized = normalize_sra_summary(record)
        if include_raw:
            normalized["raw"] = record
        experiments.append(normalized)

    return with_sra_compat(
        {
            "database": "sra",
            "sra_ids": ids,
            "returned": len(experiments),
            "experiments": experiments,
            "source": source_info("esummary.fcgi", params),
        }
    )


def normalize_sra_summary(record: JsonObject) -> JsonObject:
    uid = normalize_space(record.get("uid"))
    expxml = parse_sra_expxml(record.get("expxml"))
    runs = parse_sra_runs(record.get("runs"))
    experiment = expxml.get("experiment") if isinstance(expxml.get("experiment"), dict) else {}
    study = expxml.get("study") if isinstance(expxml.get("study"), dict) else {}
    sample = expxml.get("sample") if isinstance(expxml.get("sample"), dict) else {}
    accession = (
        first_run_accession(runs)
        or normalize_space(experiment.get("accession"))
        or normalize_space(study.get("accession"))
        or uid
    )
    return {
        "uid": uid,
        "accession": accession,
        "title": normalize_space(expxml.get("title")),
        "platform": expxml.get("platform", {}),
        "statistics": expxml.get("statistics", {}),
        "submitter": expxml.get("submitter", {}),
        "experiment": experiment,
        "study": study,
        "organism": expxml.get("organism", {}),
        "sample": sample,
        "instrument": expxml.get("instrument", {}),
        "library": expxml.get("library", {}),
        "bioproject": normalize_space(expxml.get("bioproject")),
        "biosample": normalize_space(expxml.get("biosample")),
        "runs": runs,
        "extlinks": normalize_space(record.get("extlinks")),
        "create_date": normalize_space(record.get("createdate")),
        "update_date": normalize_space(record.get("updatedate")),
        "parse_errors": expxml.get("parse_errors", []),
        "url": sra_url(accession),
    }


def parse_sra_expxml(value: object) -> JsonObject:
    root, error = parse_xml_fragment(value)
    if root is None:
        return {"parse_errors": [error] if error else []}

    summary = root.find("Summary")
    platform_node = summary.find("Platform") if summary is not None else None
    statistics_node = summary.find("Statistics") if summary is not None else None
    organism_node = root.find("Organism")
    library_node = root.find("Library_descriptor")
    return {
        "title": text_from_child(summary, "Title"),
        "platform": {
            "name": element_text(platform_node),
            "instrument_model": normalize_space(
                platform_node.get("instrument_model") if platform_node is not None else ""
            ),
        },
        "statistics": normalized_attrs(statistics_node),
        "submitter": sra_accession_attrs(root.find("Submitter")),
        "experiment": sra_accession_attrs(root.find("Experiment")),
        "study": sra_accession_attrs(root.find("Study")),
        "organism": {
            "taxid": normalize_space(organism_node.get("taxid") if organism_node is not None else ""),
            "scientific_name": normalize_space(
                organism_node.get("ScientificName") if organism_node is not None else ""
            ),
            "url": taxonomy_url(
                normalize_space(organism_node.get("taxid") if organism_node is not None else "")
            ),
        },
        "sample": sra_accession_attrs(root.find("Sample")),
        "instrument": normalized_attrs(root.find("Instrument")),
        "library": parse_sra_library(library_node),
        "bioproject": text_from_child(root, "Bioproject"),
        "biosample": text_from_child(root, "Biosample"),
        "parse_errors": [error] if error else [],
    }


def parse_sra_library(node: ET.Element | None) -> JsonObject:
    if node is None:
        return {}
    layout_node = node.find("LIBRARY_LAYOUT")
    layout = ""
    if layout_node is not None and list(layout_node):
        layout = normalize_space(list(layout_node)[0].tag)
    return {
        "strategy": text_from_child(node, "LIBRARY_STRATEGY"),
        "source": text_from_child(node, "LIBRARY_SOURCE"),
        "selection": text_from_child(node, "LIBRARY_SELECTION"),
        "layout": layout,
        "construction_protocol": text_from_child(node, "LIBRARY_CONSTRUCTION_PROTOCOL"),
    }


def parse_sra_runs(value: object) -> list[JsonObject]:
    root, _ = parse_xml_fragment(value)
    if root is None:
        return []
    runs = []
    for node in root.findall("Run"):
        attrs = sra_accession_attrs(node)
        if attrs:
            runs.append(attrs)
    return runs


def parse_xml_fragment(value: object) -> tuple[ET.Element | None, str]:
    text = str(value or "").strip()
    if not text:
        return None, ""
    try:
        return ET.fromstring(f"<Root>{text}</Root>"), ""
    except ET.ParseError as exc:
        return None, str(exc)


def sra_accession_attrs(node: ET.Element | None) -> JsonObject:
    attrs = normalized_attrs(node)
    accession = normalize_space(attrs.pop("acc", ""))
    if accession:
        attrs["accession"] = accession
        attrs.setdefault("url", sra_url(accession))
    return attrs


def normalized_attrs(node: ET.Element | None) -> JsonObject:
    if node is None:
        return {}
    return {
        normalize_attr_name(key): normalize_numeric(value)
        for key, value in node.attrib.items()
        if normalize_space(value)
    }


def normalize_attr_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def normalize_numeric(value: object) -> object:
    text = normalize_space(value)
    if re.fullmatch(r"\d+", text):
        return parse_count(text)
    if text.lower() in {"true", "false"}:
        return text.lower() == "true"
    return text


def first_run_accession(runs: list[JsonObject]) -> str:
    for run in runs:
        accession = normalize_space(run.get("accession"))
        if accession:
            return accession
    return ""


def sra_related_urls(experiment: JsonObject) -> JsonObject:
    return {
        "sra": sra_url(normalize_space(experiment.get("accession"))),
        "bioproject": bioproject_url(normalize_space(experiment.get("bioproject"))),
        "biosample": biosample_url(normalize_space(experiment.get("biosample"))),
    }
