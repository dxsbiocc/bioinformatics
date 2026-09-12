"""NCBI BioSample lookup tools."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .client import NcbiClient
from .constants import JsonObject
from .errors import NcbiError
from .omics_records import with_biosample_compat
from .records import bioproject_url, biosample_url, sra_url, taxonomy_url
from .schemas import geo_accession_url
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


BIOSAMPLE_ACCESSION_RE = re.compile(r"^SAM[A-Z]+\d+$", re.IGNORECASE)


def biosample_lookup(args: JsonObject, client: NcbiClient) -> JsonObject:
    query = normalize_space(args.get("query") or args.get("accession") or args.get("uid"))
    if not query:
        query = require_non_empty_string(args, "query")
    max_results = optional_int(args, "max_results", default=5, minimum=1, maximum=50)
    include_raw = optional_bool(args, "include_raw", default=False)

    if re.fullmatch(r"\d+", query):
        summary = biosample_summaries_for_ids(
            [query],
            client,
            include_raw=include_raw,
        )
        summary["query"] = query
        return summary

    term = f"{query.upper()}[ACCN]" if BIOSAMPLE_ACCESSION_RE.fullmatch(query) else query
    search_params: JsonObject = {
        "db": "biosample",
        "term": term,
        "retmode": "json",
        "retmax": max_results,
    }
    search_payload = client.request_json("esearch.fcgi", search_params)
    search_result = search_payload.get("esearchresult")
    if not isinstance(search_result, dict):
        raise NcbiError("BioSample search response is missing esearchresult")

    ids = [str(sample_id) for sample_id in search_result.get("idlist", [])]
    response: JsonObject = {
        "database": "biosample",
        "query": query,
        "translated_query": search_result.get("querytranslation"),
        "count": parse_count(search_result.get("count")),
        "returned": len(ids),
        "biosample_ids": ids,
        "samples": [],
        "source": source_info("esearch.fcgi", search_params),
    }
    if ids:
        summary = biosample_summaries_for_ids(
            ids,
            client,
            include_raw=include_raw,
        )
        response["samples"] = summary.get("samples", [])
        response["returned"] = len(response["samples"])
        response["summary_source"] = summary.get("source")
    return with_biosample_compat(response)


def biosample_summaries_for_ids(
    ids: list[str],
    client: NcbiClient,
    *,
    include_raw: bool = False,
) -> JsonObject:
    params: JsonObject = {
        "db": "biosample",
        "id": ",".join(ids),
        "retmode": "json",
    }
    payload = client.request_json("esummary.fcgi", params)
    result = payload.get("result")
    if not isinstance(result, dict):
        raise NcbiError("BioSample summary response is missing result")

    samples = []
    for uid in result.get("uids", ids):
        record = result.get(str(uid))
        if not isinstance(record, dict):
            continue
        normalized = normalize_biosample_summary(record)
        if include_raw:
            normalized["raw"] = record
        samples.append(normalized)

    return with_biosample_compat(
        {
            "database": "biosample",
            "biosample_ids": ids,
            "returned": len(samples),
            "samples": samples,
            "source": source_info("esummary.fcgi", params),
        }
    )


def normalize_biosample_summary(record: JsonObject) -> JsonObject:
    uid = normalize_space(record.get("uid"))
    accession = normalize_space(record.get("accession"))
    parsed = parse_biosample_sampledata(record.get("sampledata"))
    organism = parsed.get("organism") if isinstance(parsed.get("organism"), dict) else {}
    taxid = normalize_space(organism.get("taxid") or record.get("taxonomy"))
    scientific_name = normalize_space(organism.get("scientific_name") or record.get("organism"))
    source_identifiers = merge_source_identifiers(
        parse_biosample_identifier_text(record.get("identifiers")),
        parsed.get("source_identifiers") if isinstance(parsed.get("source_identifiers"), list) else [],
    )
    return {
        "uid": uid,
        "accession": accession,
        "title": normalize_space(parsed.get("title") or record.get("title")),
        "publication_date": normalize_space(record.get("publicationdate") or record.get("date")),
        "submission_date": normalize_space(parsed.get("submission_date")),
        "modification_date": normalize_space(record.get("modificationdate") or parsed.get("last_update")),
        "organization": normalize_space(parsed.get("owner") or record.get("organization")),
        "organism": {
            "scientific_name": scientific_name,
            "taxid": taxid,
            "url": taxonomy_url(taxid) if taxid else "",
        },
        "source_sample": normalize_space(record.get("sourcesample")),
        "source_identifiers": source_identifiers,
        "package": normalize_space(parsed.get("package_display") or record.get("package")),
        "package_name": normalize_space(parsed.get("package")),
        "models": parsed.get("models", []),
        "attributes": parsed.get("attributes", []),
        "links": parsed.get("links", []),
        "status": parsed.get("status", {}),
        "infraspecies": normalize_space(record.get("infraspecies")),
        "url": biosample_url(accession or uid),
    }


def parse_biosample_sampledata(value: object) -> JsonObject:
    text = str(value or "").strip()
    if not text:
        return {}
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        return {"parse_error": str(exc)}
    if root.tag != "BioSample":
        sample = root.find(".//BioSample")
        if sample is None:
            return {}
        root = sample

    organism_node = root.find("./Description/Organism")
    package_node = root.find("./Package")
    status_node = root.find("./Status")
    return {
        "accession": normalize_space(root.get("accession")),
        "uid": normalize_space(root.get("id")),
        "publication_date": normalize_space(root.get("publication_date")),
        "submission_date": normalize_space(root.get("submission_date")),
        "last_update": normalize_space(root.get("last_update")),
        "title": text_from_child(root.find("./Description"), "Title"),
        "organism": {
            "scientific_name": normalize_space(
                organism_node.get("taxonomy_name") if organism_node is not None else ""
            )
            or text_from_child(organism_node, "OrganismName"),
            "taxid": normalize_space(
                organism_node.get("taxonomy_id") if organism_node is not None else ""
            ),
        },
        "owner": text_from_child(root.find("./Owner"), "Name"),
        "models": [
            element_text(model)
            for model in root.findall("./Models/Model")
            if element_text(model)
        ],
        "package": element_text(package_node),
        "package_display": normalize_space(
            package_node.get("display_name") if package_node is not None else ""
        ),
        "source_identifiers": parse_biosample_xml_ids(root),
        "attributes": parse_biosample_xml_attributes(root),
        "links": parse_biosample_xml_links(root),
        "status": {
            "status": normalize_space(status_node.get("status") if status_node is not None else ""),
            "when": normalize_space(status_node.get("when") if status_node is not None else ""),
        },
    }


def parse_biosample_xml_ids(root: ET.Element) -> list[JsonObject]:
    identifiers = []
    for node in root.findall("./Ids/Id"):
        namespace = normalize_space(node.get("db"))
        value = element_text(node)
        if not namespace or not value:
            continue
        identifiers.append(
            {
                "namespace": namespace,
                "id": value,
                "label": f"{namespace}:{value}",
                "url": biosample_identifier_url(namespace, value),
                "primary": normalize_space(node.get("is_primary")) == "1",
            }
        )
    return identifiers


def parse_biosample_xml_attributes(root: ET.Element) -> list[JsonObject]:
    attributes = []
    for node in root.findall("./Attributes/Attribute"):
        value = element_text(node)
        name = normalize_space(node.get("attribute_name"))
        if not name and not value:
            continue
        attributes.append(
            {
                "name": name,
                "harmonized_name": normalize_space(node.get("harmonized_name")),
                "display_name": normalize_space(node.get("display_name")),
                "value": value,
            }
        )
    return attributes


def parse_biosample_xml_links(root: ET.Element) -> list[JsonObject]:
    links = []
    for node in root.findall("./Links/Link"):
        link_type = normalize_space(node.get("type"))
        target = normalize_space(node.get("target"))
        label = normalize_space(node.get("label"))
        value = element_text(node)
        url = biosample_link_url(link_type, target, label, value)
        links.append(
            {
                "type": link_type,
                "target": target,
                "label": label or value,
                "value": value,
                "url": url,
            }
        )
    return links


def parse_biosample_identifier_text(value: object) -> list[JsonObject]:
    identifiers = []
    for part in normalize_space(value).split(";"):
        if ":" not in part:
            continue
        namespace, identifier = part.split(":", 1)
        namespace = normalize_space(namespace)
        identifier = normalize_space(identifier)
        if not namespace or not identifier:
            continue
        identifiers.append(
            {
                "namespace": namespace,
                "id": identifier,
                "label": f"{namespace}:{identifier}",
                "url": biosample_identifier_url(namespace, identifier),
            }
        )
    return identifiers


def merge_source_identifiers(*groups: object) -> list[JsonObject]:
    merged = []
    seen = set()
    for group in groups:
        if not isinstance(group, list):
            continue
        for item in group:
            if not isinstance(item, dict):
                continue
            namespace = normalize_space(item.get("namespace"))
            identifier = normalize_space(item.get("id"))
            if not namespace or not identifier:
                continue
            key = (namespace.lower(), identifier)
            if key in seen:
                continue
            seen.add(key)
            merged.append(
                {
                    "namespace": namespace,
                    "id": identifier,
                    "label": normalize_space(item.get("label")) or f"{namespace}:{identifier}",
                    "url": normalize_space(item.get("url")) or biosample_identifier_url(namespace, identifier),
                }
            )
    return merged


def biosample_identifier_url(namespace: str, identifier: str) -> str:
    lowered = normalize_space(namespace).lower()
    value = normalize_space(identifier)
    if lowered == "biosample":
        return biosample_url(value)
    if lowered == "sra":
        return sra_url(value)
    if lowered == "geo":
        return geo_accession_url(value)
    if lowered == "bioproject":
        return bioproject_url(value)
    return ""


def biosample_link_url(link_type: str, target: str, label: str, value: str) -> str:
    if normalize_space(link_type).lower() == "url" and value.startswith(("http://", "https://")):
        return value
    target = normalize_space(target).lower()
    label = normalize_space(label)
    value = normalize_space(value)
    if target == "bioproject":
        return bioproject_url(label or value)
    if target == "sra":
        return sra_url(label or value)
    if target == "geo":
        return geo_accession_url(label or value)
    if target == "taxonomy":
        return taxonomy_url(value)
    return ""
