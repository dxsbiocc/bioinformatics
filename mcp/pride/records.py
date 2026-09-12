"""Front-end compatible record envelopes for PRIDE Archive projects and files."""

from __future__ import annotations

import urllib.parse
from typing import Any

from .constants import PRIDE_API_BASE_URL, PRIDE_WEBSITE_BASE_URL, RECORD_SCHEMA_VERSION, JsonObject
from .utils import normalize_space, safe_list


def pride_project_record(
    project: JsonObject,
    *,
    files: list[JsonObject] | None = None,
    website_base_url: str = PRIDE_WEBSITE_BASE_URL,
    api_base_url: str = PRIDE_API_BASE_URL,
) -> JsonObject:
    normalized = normalize_project(project, files=files or [], website_base_url=website_base_url, api_base_url=api_base_url)
    accession = normalized["accession"]
    title = normalized["title"] or accession
    links = project_links(normalized)
    description = normalized["project_description"] or "PRIDE Archive proteomics project"
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.project",
        "record_type": "pride_project",
        "database": "pride",
        "id": accession,
        "stable_id": accession,
        "label": accession,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "pride",
        "identifiers": project_identifiers(normalized),
        "links": links,
        "display": {
            "component": "project",
            "chip_label": accession,
            "icon": "pride",
            "title": title,
            "subtitle": project_subtitle(normalized),
            "description": description,
            "metadata": project_metadata(normalized),
            "badges": compact_badges(
                ("PRIDE", "source"),
                (accession, "identifier"),
                (normalized["submission_type"], "record_type"),
                (first_name(normalized["organisms"]), "context"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": project_subtitle(normalized),
                "icon": "pride",
                "fields": compact_fields(
                    ("PRIDE project", accession),
                    ("DOI", normalized["doi"]),
                    ("Organisms", ", ".join(item["name"] for item in normalized["organisms"][:3])),
                    ("Experiment types", ", ".join(item["name"] for item in normalized["experiment_types"][:3])),
                    ("Publication date", normalized["publication_date"]),
                    ("Files", str(normalized["file_count"]) if normalized["file_count"] else ""),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": project_sections(normalized),
            "previews": project_previews(normalized, links),
        },
        "related": {
            "references": normalized["references"],
            "organisms": normalized["organisms"],
            "instruments": normalized["instruments"],
            "files": normalized["files"],
            "other_omics_links": normalized["other_omics_links"],
        },
        "data": normalized,
    }


def pride_files_download_plan_record(
    accession: str,
    files: list[JsonObject],
    *,
    website_base_url: str = PRIDE_WEBSITE_BASE_URL,
    api_base_url: str = PRIDE_API_BASE_URL,
) -> JsonObject:
    normalized_files = [normalize_file(item) for item in files]
    normalized_files = [item for item in normalized_files if item["file_name"] or item["accession"]]
    accession = normalize_space(accession).upper()
    url = pride_project_url(accession, website_base_url)
    api_url = pride_api_url(f"projects/{accession}/files", api_base_url, {})
    links = [
        {"label": "Open PRIDE project", "url": url, "kind": "external", "primary": True},
        {"label": "Open PRIDE files API", "url": api_url, "kind": "external"},
    ]
    first_file_url = first_http_file_url(normalized_files)
    if first_file_url:
        links.append({"label": "Open first file", "url": first_file_url, "kind": "download"})
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.download_plan",
        "record_type": "pride_file_manifest",
        "database": "pride",
        "id": f"{accession}:files",
        "stable_id": f"{accession}:files",
        "label": f"{accession} files",
        "title": f"{accession} PRIDE file manifest",
        "description": f"{len(normalized_files)} metadata-only file rows. No download has been started.",
        "url": url,
        "icon": "download",
        "identifiers": {
            "pride_project": {"namespace": "pride.project", "id": accession, "label": accession, "url": url}
        },
        "links": links,
        "display": {
            "component": "download_plan",
            "chip_label": f"{accession} files",
            "icon": "download",
            "title": f"{accession} PRIDE file manifest",
            "subtitle": f"PRIDE | {len(normalized_files)} file rows",
            "description": "Metadata-only PRIDE file manifest. Review links before downloading data.",
            "metadata": compact_fields(
                ("PRIDE project", accession),
                ("Returned files", str(len(normalized_files))),
                ("First file", normalized_files[0]["file_name"] if normalized_files else ""),
                ("API", api_url),
            ),
            "badges": compact_badges(("PRIDE", "source"), (accession, "identifier"), ("download plan", "record_type")),
            "actions": display_actions(links),
            "hover": {
                "title": f"{accession} PRIDE file manifest",
                "subtitle": f"{len(normalized_files)} file rows",
                "icon": "download",
                "fields": compact_fields(
                    ("PRIDE project", accession),
                    ("Returned files", str(len(normalized_files))),
                    ("URL", url),
                ),
            },
            "primary_url": url,
            "sections": [
                {
                    "key": "files",
                    "title": "Files",
                    "kind": "table",
                    "rows": normalized_files,
                }
            ],
            "previews": [
                {
                    "kind": "download_manifest",
                    "title": "PRIDE file manifest",
                    "section_key": "files",
                    "actions": display_actions(links),
                    "data": {"rows": normalized_files},
                },
                {
                    "kind": "table",
                    "title": "Files",
                    "section_key": "files",
                    "data": {
                        "columns": ["file_name", "category", "download_url", "checksum"],
                        "rows": normalized_files,
                    },
                },
            ],
        },
        "related": {"files": normalized_files},
        "data": {
            "accession": accession,
            "files": normalized_files,
            "url": url,
            "api_url": api_url,
        },
    }


def normalize_project(
    project: JsonObject,
    *,
    files: list[JsonObject],
    website_base_url: str,
    api_base_url: str,
) -> JsonObject:
    accession = normalize_space(project.get("accession")).upper()
    references = normalize_references(safe_list(project.get("references")))
    return {
        "accession": accession,
        "title": normalize_space(project.get("title")),
        "project_description": normalize_space(project.get("projectDescription")),
        "sample_processing_protocol": normalize_space(project.get("sampleProcessingProtocol")),
        "data_processing_protocol": normalize_space(project.get("dataProcessingProtocol")),
        "project_tags": unique_texts(safe_list(project.get("projectTags"))),
        "keywords": unique_texts(safe_list(project.get("keywords"))),
        "doi": normalize_space(project.get("doi")),
        "submission_type": normalize_space(project.get("submissionType")),
        "license": normalize_space(project.get("license")),
        "submission_date": normalize_space(project.get("submissionDate")),
        "publication_date": normalize_space(project.get("publicationDate")),
        "submitters": normalize_people(safe_list(project.get("submitters"))),
        "lab_pis": normalize_people(safe_list(project.get("labPIs"))),
        "instruments": normalize_cvparams(safe_list(project.get("instruments"))),
        "softwares": normalize_cvparams(safe_list(project.get("softwares"))),
        "experiment_types": normalize_cvparams(safe_list(project.get("experimentTypes"))),
        "quantification_methods": normalize_cvparams(safe_list(project.get("quantificationMethods"))),
        "organisms": normalize_cvparams(safe_list(project.get("organisms"))),
        "organism_parts": normalize_cvparams(safe_list(project.get("organismParts"))),
        "diseases": normalize_cvparams(safe_list(project.get("diseases"))),
        "ptms": normalize_cvparams(safe_list(project.get("identifiedPTMStrings"))),
        "countries": unique_texts(safe_list(project.get("countries"))),
        "references": references,
        "file_count": int_or_zero(project.get("totalFileDownloads")),
        "other_omics_links": unique_texts(safe_list(project.get("otherOmicsLinks"))),
        "files": [normalize_file(item) for item in files],
        "url": pride_project_url(accession, website_base_url),
        "api_url": pride_api_url(f"projects/{accession}", api_base_url, {}),
        "files_api_url": pride_api_url(f"projects/{accession}/files", api_base_url, {}),
    }


def normalize_file(item: JsonObject) -> JsonObject:
    locations = normalize_locations(safe_list(item.get("publicFileLocations")))
    download_url = first_http_location(locations)
    file_name = file_name_from_locations(locations)
    category = normalize_cvparam(item.get("fileCategory") if isinstance(item.get("fileCategory"), dict) else {})
    return {
        "accession": normalize_space(item.get("accession")),
        "project_accessions": unique_texts(safe_list(item.get("projectAccessions"))),
        "file_name": file_name,
        "category": category.get("name", ""),
        "category_value": category.get("value", ""),
        "category_accession": category.get("accession", ""),
        "checksum": normalize_space(item.get("checksum")),
        "download_url": download_url,
        "locations": locations,
        "raw": item,
    }


def normalize_locations(items: list[Any]) -> list[JsonObject]:
    locations = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_url = normalize_space(item.get("value"))
        locations.append(
            {
                "protocol": normalize_space(item.get("name")),
                "accession": normalize_space(item.get("accession")),
                "raw_url": raw_url,
                "url": safe_download_url(raw_url),
            }
        )
    return locations


def normalize_references(items: list[Any]) -> list[JsonObject]:
    references = []
    for item in items:
        if not isinstance(item, dict):
            continue
        pmid = normalize_space(item.get("pubmedID"))
        doi = normalize_space(item.get("doi"))
        references.append(
            {
                "reference": normalize_space(item.get("referenceLine")),
                "pmid": pmid,
                "doi": doi,
                "pmid_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                "doi_url": f"https://doi.org/{doi}" if doi else "",
            }
        )
    return references


def normalize_people(items: list[Any]) -> list[JsonObject]:
    people = []
    for item in items:
        if not isinstance(item, dict):
            continue
        people.append(
            {
                "name": normalize_space(item.get("name")) or " ".join(
                    part for part in [normalize_space(item.get("firstName")), normalize_space(item.get("lastName"))] if part
                ),
                "affiliation": normalize_space(item.get("affiliation")),
                "country": normalize_space(item.get("country")),
                "orcid": normalize_space(item.get("orcid")),
            }
        )
    return [person for person in people if person["name"] or person["affiliation"]]


def normalize_cvparams(items: list[Any]) -> list[JsonObject]:
    return [normalize_cvparam(item) for item in items if isinstance(item, dict) and normalize_cvparam(item).get("name")]


def normalize_cvparam(item: JsonObject) -> JsonObject:
    return {
        "cv_label": normalize_space(item.get("cvLabel")),
        "accession": normalize_space(item.get("accession")),
        "name": normalize_space(item.get("name")),
        "value": normalize_space(item.get("value")),
    }


def project_sections(normalized: JsonObject) -> list[JsonObject]:
    sections = [
        {
            "key": "overview",
            "title": "Overview",
            "kind": "table",
            "rows": [
                {"field": "Accession", "value": normalized["accession"]},
                {"field": "Title", "value": normalized["title"]},
                {"field": "Description", "value": normalized["project_description"]},
                {"field": "Submission type", "value": normalized["submission_type"]},
                {"field": "Submission date", "value": normalized["submission_date"]},
                {"field": "Publication date", "value": normalized["publication_date"]},
                {"field": "DOI", "value": normalized["doi"]},
            ],
        }
    ]
    for key, title, rows in [
        ("organisms", "Organisms", normalized["organisms"]),
        ("instruments", "Instruments", normalized["instruments"]),
        ("experiment_types", "Experiment types", normalized["experiment_types"]),
        ("ptms", "PTMs", normalized["ptms"]),
        ("references", "References", normalized["references"]),
        ("files", "Files", normalized["files"]),
    ]:
        if rows:
            sections.append({"key": key, "title": title, "kind": "table", "rows": rows})
    return sections


def project_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews = [
        {
            "kind": "table",
            "title": "PRIDE project summary",
            "section_key": "overview",
            "actions": display_actions(links[:1]),
            "data": {"columns": ["field", "value"], "rows": project_sections(normalized)[0]["rows"]},
        }
    ]
    if normalized["files"]:
        previews.append(
            {
                "kind": "download_manifest",
                "title": "PRIDE files",
                "section_key": "files",
                "data": {"rows": normalized["files"]},
            }
        )
    if normalized["references"]:
        previews.append(
            {
                "kind": "citation_list",
                "title": "Project references",
                "section_key": "references",
                "data": {"citations": normalized["references"]},
            }
        )
    xrefs = project_xrefs(normalized)
    if xrefs:
        previews.append({"kind": "xref_groups", "title": "Project links", "data": {"groups": xref_groups(xrefs)}})
    return previews


def project_links(normalized: JsonObject) -> list[JsonObject]:
    links = [
        {"label": "Open PRIDE project", "url": normalized["url"], "kind": "external", "primary": True},
        {"label": "Open PRIDE API record", "url": normalized["api_url"], "kind": "external"},
        {"label": "Open PRIDE files API", "url": normalized["files_api_url"], "kind": "external"},
    ]
    if normalized["doi"]:
        links.append({"label": "Open DOI", "url": f"https://doi.org/{normalized['doi']}", "kind": "external"})
    return unique_links(links)


def project_identifiers(normalized: JsonObject) -> JsonObject:
    identifiers: JsonObject = {
        "pride_project": {
            "namespace": "pride.project",
            "id": normalized["accession"],
            "label": normalized["accession"],
            "url": normalized["url"],
        }
    }
    if normalized["doi"]:
        identifiers["doi"] = {
            "namespace": "doi",
            "id": normalized["doi"],
            "label": normalized["doi"],
            "url": f"https://doi.org/{normalized['doi']}",
        }
    pmids = [
        {
            "namespace": "pubmed",
            "id": item["pmid"],
            "label": f"PMID:{item['pmid']}",
            "url": item["pmid_url"],
        }
        for item in normalized["references"]
        if item.get("pmid")
    ]
    if pmids:
        identifiers["pubmed"] = pmids
    return identifiers


def project_xrefs(normalized: JsonObject) -> list[JsonObject]:
    xrefs = []
    if normalized["doi"]:
        xrefs.append({"database": "DOI", "id": normalized["doi"], "label": normalized["doi"], "url": f"https://doi.org/{normalized['doi']}"})
    for ref in normalized["references"]:
        if ref.get("pmid"):
            xrefs.append({"database": "PubMed", "id": ref["pmid"], "label": f"PMID:{ref['pmid']}", "url": ref["pmid_url"]})
    for link in normalized["other_omics_links"]:
        xrefs.append({"database": "ProteomeXchange", "id": link, "label": link, "url": ""})
    return xrefs


def project_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("PRIDE project", normalized["accession"]),
        ("DOI", normalized["doi"]),
        ("Submission type", normalized["submission_type"]),
        ("Submitted", normalized["submission_date"]),
        ("Published", normalized["publication_date"]),
        ("Organisms", ", ".join(item["name"] for item in normalized["organisms"][:3])),
        ("Experiment types", ", ".join(item["name"] for item in normalized["experiment_types"][:3])),
        ("Instruments", ", ".join(item["name"] for item in normalized["instruments"][:3])),
        ("Keywords", ", ".join(normalized["keywords"][:5])),
        ("File downloads", str(normalized["file_count"]) if normalized["file_count"] else ""),
    )


def project_subtitle(normalized: JsonObject) -> str:
    return " | ".join(
        part
        for part in [
            normalized["accession"],
            first_name(normalized["organisms"]),
            first_name(normalized["experiment_types"]),
            normalized["publication_date"],
        ]
        if part
    )


def xref_groups(xrefs: list[JsonObject]) -> list[JsonObject]:
    groups: dict[str, list[JsonObject]] = {}
    for item in xrefs:
        database = normalize_space(item.get("database")) or "xref"
        groups.setdefault(database, []).append(item)
    return [{"label": database, "items": items, "count": len(items)} for database, items in sorted(groups.items())]


def display_actions(links: list[JsonObject]) -> list[JsonObject]:
    actions = []
    for link in links:
        url = normalize_space(link.get("url"))
        if url.startswith(("http://", "https://")):
            actions.append(
                {
                    "label": normalize_space(link.get("label")),
                    "url": url,
                    "kind": normalize_space(link.get("kind") or "external"),
                    "primary": bool(link.get("primary")),
                }
            )
    return actions


def compact_fields(*pairs: tuple[str, object]) -> list[JsonObject]:
    fields = []
    for label, value in pairs:
        normalized = normalize_space(value)
        if normalized:
            fields.append({"label": label, "value": normalized})
    return fields


def compact_badges(*pairs: tuple[object, str]) -> list[JsonObject]:
    badges = []
    for label, kind in pairs:
        normalized = normalize_space(label)
        if normalized:
            badges.append({"label": normalized, "kind": kind})
    return badges


def unique_links(links: list[JsonObject]) -> list[JsonObject]:
    seen = set()
    out = []
    for link in links:
        key = normalize_space(link.get("url"))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(link)
    return out


def unique_texts(items: list[Any]) -> list[str]:
    out = []
    seen = set()
    for item in items:
        text = normalize_space(item)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def first_name(items: list[JsonObject]) -> str:
    return normalize_space(items[0].get("name")) if items else ""


def int_or_zero(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def pride_project_url(accession: str, website_base_url: str) -> str:
    return f"{website_base_url.rstrip('/')}/projects/{urllib.parse.quote(accession)}"


def pride_api_url(endpoint: str, api_base_url: str, params: JsonObject) -> str:
    base = f"{api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    if not params:
        return base
    return f"{base}?{urllib.parse.urlencode(params, doseq=True)}"


def safe_download_url(raw_url: str) -> str:
    if raw_url.startswith("ftp://ftp.pride.ebi.ac.uk/"):
        return "https://ftp.pride.ebi.ac.uk/" + raw_url.split("ftp://ftp.pride.ebi.ac.uk/", 1)[1]
    if raw_url.startswith(("http://", "https://")):
        return raw_url
    return ""


def first_http_location(locations: list[JsonObject]) -> str:
    for item in locations:
        url = normalize_space(item.get("url"))
        if url.startswith(("http://", "https://")):
            return url
    return ""


def first_http_file_url(files: list[JsonObject]) -> str:
    for item in files:
        url = normalize_space(item.get("download_url"))
        if url:
            return url
    return ""


def file_name_from_locations(locations: list[JsonObject]) -> str:
    for item in locations:
        raw_url = normalize_space(item.get("raw_url"))
        if raw_url:
            return raw_url.rsplit("/", 1)[-1]
    return ""

