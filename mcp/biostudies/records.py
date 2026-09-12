"""Front-end compatible record envelopes for BioStudies and ArrayExpress."""

from __future__ import annotations

import urllib.parse
from typing import Any

from .constants import BIOSTUDIES_API_BASE_URL, BIOSTUDIES_WEBSITE_BASE_URL, RECORD_SCHEMA_VERSION, JsonObject
from .utils import normalize_space, safe_list


def biostudies_study_record(
    study: JsonObject,
    *,
    info: JsonObject | None = None,
    files: list[JsonObject] | None = None,
    repository: str = "biostudies",
    website_base_url: str = BIOSTUDIES_WEBSITE_BASE_URL,
    api_base_url: str = BIOSTUDIES_API_BASE_URL,
) -> JsonObject:
    normalized = normalize_study(
        study,
        info=info or {},
        files=files or [],
        repository=repository,
        website_base_url=website_base_url,
        api_base_url=api_base_url,
    )
    accession = normalized["accession"]
    title = normalized["title"] or accession
    links = study_links(normalized)
    description = normalized["description"] or "BioStudies public study"
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.project",
        "record_type": "biostudies_study",
        "database": "biostudies",
        "id": accession,
        "stable_id": accession,
        "label": accession,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": normalized["icon"],
        "identifiers": study_identifiers(normalized),
        "links": links,
        "display": {
            "component": "project",
            "chip_label": accession,
            "icon": normalized["icon"],
            "title": title,
            "subtitle": study_subtitle(normalized),
            "description": description,
            "metadata": study_metadata(normalized),
            "badges": compact_badges(
                (normalized["repository_label"], "source"),
                (accession, "identifier"),
                (first_value(normalized["study_types"]), "record_type"),
                (first_value(normalized["organisms"]), "context"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": study_subtitle(normalized),
                "icon": normalized["icon"],
                "fields": compact_fields(
                    ("Accession", accession),
                    ("Repository", normalized["repository_label"]),
                    ("Organism", ", ".join(normalized["organisms"][:3])),
                    ("Study type", ", ".join(normalized["study_types"][:3])),
                    ("Release date", normalized["release_date"]),
                    ("Files", str(normalized["file_count"]) if normalized["file_count"] else ""),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": study_sections(normalized),
            "previews": study_previews(normalized, links),
        },
        "related": {
            "authors": normalized["authors"],
            "publications": normalized["publications"],
            "protocols": normalized["protocols"],
            "external_links": normalized["external_links"],
            "files": normalized["files"],
        },
        "data": normalized,
    }


def biostudies_file_manifest_record(
    accession: str,
    info: JsonObject,
    files: list[JsonObject],
    *,
    repository: str = "biostudies",
    website_base_url: str = BIOSTUDIES_WEBSITE_BASE_URL,
    api_base_url: str = BIOSTUDIES_API_BASE_URL,
) -> JsonObject:
    accession = normalize_space(accession).upper()
    normalized_info = normalize_info(info)
    http_base = normalized_info.get("http_link", "")
    normalized_files = [normalize_file(item, accession=accession, http_base=http_base) for item in files]
    normalized_files = [item for item in normalized_files if item["path"] or item["name"]]
    url = study_url(accession, website_base_url)
    api_url = api_url_for(f"studies/{accession}/files", api_base_url, {})
    links = [
        {"label": "Open BioStudies study", "url": url, "kind": "external", "primary": True},
        {"label": "Open BioStudies files API", "url": api_url, "kind": "external"},
    ]
    if normalized_info.get("globus_link"):
        links.append({"label": "Open Globus location", "url": normalized_info["globus_link"], "kind": "external"})
    first_file_url = first_download_url(normalized_files)
    if first_file_url:
        links.append({"label": "Open first file", "url": first_file_url, "kind": "download"})
    repository_label = repository_label_for(repository, accession)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.download_plan",
        "record_type": "biostudies_file_manifest",
        "database": "biostudies",
        "id": f"{accession}:files",
        "stable_id": f"{accession}:files",
        "label": f"{accession} files",
        "title": f"{accession} BioStudies file manifest",
        "description": f"{len(normalized_files)} metadata-only file rows. No download has been started.",
        "url": url,
        "icon": "download",
        "identifiers": {
            "biostudies": {"namespace": "biostudies.study", "id": accession, "label": accession, "url": url}
        },
        "links": links,
        "display": {
            "component": "download_plan",
            "chip_label": f"{accession} files",
            "icon": "download",
            "title": f"{accession} BioStudies file manifest",
            "subtitle": f"{repository_label} | {len(normalized_files)} file rows",
            "description": "Metadata-only BioStudies file manifest. Review links before downloading data.",
            "metadata": compact_fields(
                ("Accession", accession),
                ("Repository", repository_label),
                ("Returned files", str(len(normalized_files))),
                ("Total files", str(normalized_info.get("files") or "")),
                ("HTTP root", normalized_info.get("http_link", "")),
                ("API", api_url),
            ),
            "badges": compact_badges((repository_label, "source"), (accession, "identifier"), ("download plan", "record_type")),
            "actions": display_actions(links),
            "hover": {
                "title": f"{accession} BioStudies file manifest",
                "subtitle": f"{len(normalized_files)} file rows",
                "icon": "download",
                "fields": compact_fields(
                    ("Accession", accession),
                    ("Returned files", str(len(normalized_files))),
                    ("URL", url),
                ),
            },
            "primary_url": url,
            "sections": [{"key": "files", "title": "Files", "kind": "table", "rows": normalized_files}],
            "previews": [
                {
                    "kind": "download_manifest",
                    "title": "BioStudies file manifest",
                    "section_key": "files",
                    "actions": display_actions(links),
                    "data": {"rows": normalized_files},
                },
                {
                    "kind": "table",
                    "title": "Files",
                    "section_key": "files",
                    "data": {
                        "columns": ["name", "section", "type", "size", "download_url"],
                        "rows": normalized_files,
                    },
                },
            ],
        },
        "related": {"files": normalized_files},
        "data": {
            "accession": accession,
            "repository": repository,
            "files": normalized_files,
            "file_info": normalized_info,
            "url": url,
            "api_url": api_url,
        },
    }


def normalize_study(
    study: JsonObject,
    *,
    info: JsonObject,
    files: list[JsonObject],
    repository: str,
    website_base_url: str,
    api_base_url: str,
) -> JsonObject:
    accession = normalize_space(study.get("accno") or study.get("accession")).upper()
    section = study.get("section") if isinstance(study.get("section"), dict) else {}
    top_attributes = attribute_values(safe_list(study.get("attributes")))
    section_attributes = attribute_values(safe_list(section.get("attributes"))) if isinstance(section, dict) else {}
    all_sections = collect_sections(section)
    normalized_info = normalize_info(info)
    http_base = normalized_info.get("http_link", "")
    normalized_files = [normalize_file(item, accession=accession, http_base=http_base) for item in files]
    if not normalized_files:
        normalized_files = [normalize_file(item, accession=accession, http_base=http_base) for item in collect_files(section)]
    normalized_files = [item for item in normalized_files if item["path"] or item["name"]]
    publications = normalize_publications([item for item in all_sections if text_equal(item.get("type"), "Publication")])
    return {
        "accession": accession,
        "repository": repository,
        "repository_label": repository_label_for(repository, accession),
        "icon": "arrayexpress" if repository == "arrayexpress" or accession.startswith("E-") else "biostudies",
        "title": first_text(top_attributes.get("Title"), section_attributes.get("Title"), study.get("title")),
        "description": first_text(section_attributes.get("Description"), top_attributes.get("Description"), study.get("content")),
        "release_date": first_text(top_attributes.get("ReleaseDate"), section_attributes.get("ReleaseDate"), study.get("release_date")),
        "authors": normalize_authors(all_sections, study.get("author")),
        "study_types": unique_texts(section_attributes.get("Study type", [])),
        "organisms": unique_texts(section_attributes.get("Organism", [])),
        "sample_count": first_text(section_attributes.get("Sample count"), values_from_sections(all_sections, "Samples", "Sample count")),
        "assay_count": first_text(values_from_sections(all_sections, "Assays and Data", "Assay count")),
        "technology": first_text(values_from_sections(all_sections, "Assays and Data", "Technology")),
        "protocols": normalize_protocols([item for item in all_sections if text_equal(item.get("type"), "Protocols")]),
        "publications": publications,
        "external_links": normalize_links(collect_links(section), accession=accession, website_base_url=website_base_url),
        "file_count": int_or_zero(normalized_info.get("files") or study.get("files") or len(normalized_files)),
        "files": normalized_files,
        "file_info": normalized_info,
        "url": study_url(accession, website_base_url),
        "api_url": api_url_for(f"studies/{accession}", api_base_url, {}),
        "info_api_url": api_url_for(f"studies/{accession}/info", api_base_url, {}),
        "files_api_url": api_url_for(f"studies/{accession}/files", api_base_url, {}),
    }


def normalize_info(info: JsonObject) -> JsonObject:
    return {
        "files": int_or_zero(info.get("files")),
        "http_link": safe_http_url(info.get("httpLink")),
        "ftp_link": normalize_space(info.get("ftpLink")),
        "globus_link": safe_http_url(info.get("globusLink")),
        "is_public": bool(info.get("isPublic")) if isinstance(info.get("isPublic"), bool) else None,
        "rel_path": normalize_space(info.get("relPath")),
        "sections": unique_texts(safe_list(info.get("sections"))),
        "section_file_counts": info.get("sectionFileCounts") if isinstance(info.get("sectionFileCounts"), dict) else {},
    }


def normalize_file(item: JsonObject, *, accession: str, http_base: str) -> JsonObject:
    attrs = attribute_values(safe_list(item.get("attributes")))
    path = normalize_space(item.get("path") or item.get("Name"))
    name = normalize_space(item.get("Name") or path.rsplit("/", 1)[-1])
    section = normalize_space(item.get("Section") or item.get("section") or first_text(attrs.get("Section")))
    file_type = normalize_space(item.get("Type") or item.get("type") or item.get("file_type") or first_text(attrs.get("Type")))
    description = normalize_space(item.get("Description") or first_text(attrs.get("Description")))
    file_format = normalize_space(item.get("Format") or first_text(attrs.get("Format")))
    size = int_or_zero(item.get("Size") or item.get("size"))
    return {
        "accession": accession,
        "name": name,
        "path": path,
        "section": section,
        "type": file_type,
        "description": description,
        "format": file_format,
        "size": size,
        "size_label": human_size(size),
        "download_url": file_download_url(http_base, path),
        "raw": item,
    }


def normalize_authors(sections: list[JsonObject], search_author: object) -> list[JsonObject]:
    authors = []
    for item in sections:
        if not text_equal(item.get("type"), "Author"):
            continue
        attrs = attribute_values(safe_list(item.get("attributes")))
        name = first_text(attrs.get("Name"))
        if name:
            authors.append(
                {
                    "name": name,
                    "role": first_text(attrs.get("Role")),
                    "affiliation": first_text(attrs.get("affiliation"), attrs.get("Affiliation")),
                    "email": first_text(attrs.get("Email")),
                }
            )
    if not authors and search_author:
        for name in normalize_space(search_author).split(","):
            if name.strip():
                authors.append({"name": name.strip(), "role": "", "affiliation": "", "email": ""})
    return authors[:25]


def normalize_protocols(sections: list[JsonObject]) -> list[JsonObject]:
    protocols = []
    for item in sections:
        attrs = attribute_values(safe_list(item.get("attributes")))
        protocols.append(
            {
                "accession": normalize_space(item.get("accno")),
                "name": first_text(attrs.get("Name"), item.get("accno")),
                "type": first_text(attrs.get("Type")),
                "description": first_text(attrs.get("Description")),
                "hardware": first_text(attrs.get("Hardware")),
            }
        )
    return [item for item in protocols if item["name"] or item["type"] or item["description"]][:25]


def normalize_publications(sections: list[JsonObject]) -> list[JsonObject]:
    publications = []
    for item in sections:
        attrs = attribute_values(safe_list(item.get("attributes")))
        pmid = normalize_space(item.get("accno"))
        doi = first_text(attrs.get("DOI"))
        publications.append(
            {
                "pmid": pmid if pmid.isdigit() else "",
                "pmid_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid.isdigit() else "",
                "title": first_text(attrs.get("Title")),
                "authors": first_text(attrs.get("Authors")),
                "doi": doi,
                "doi_url": f"https://doi.org/{urllib.parse.quote(doi, safe='/')}" if doi else "",
                "status": first_text(attrs.get("Status")),
            }
        )
    return [item for item in publications if item["title"] or item["pmid"] or item["doi"]][:25]


def normalize_links(groups: list[JsonObject], *, accession: str, website_base_url: str) -> list[JsonObject]:
    links = []
    for item in groups:
        url_value = normalize_space(item.get("url"))
        if not url_value:
            continue
        attrs = attribute_values(safe_list(item.get("attributes")))
        link_type = first_text(attrs.get("Type"), attrs.get("type"))
        url = external_link_url(url_value, link_type, website_base_url)
        if not url:
            continue
        links.append({"label": link_type or url_value, "id": url_value, "type": link_type, "url": url})
    seen = set()
    unique = []
    for item in links:
        key = (item["label"], item["url"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique[:50]


def collect_sections(value: object) -> list[JsonObject]:
    found: list[JsonObject] = []
    if isinstance(value, dict):
        found.append(value)
        for child in safe_list(value.get("subsections")):
            found.extend(collect_sections(child))
    elif isinstance(value, list):
        for item in value:
            found.extend(collect_sections(item))
    return found


def collect_files(value: object) -> list[JsonObject]:
    found: list[JsonObject] = []
    if isinstance(value, dict):
        for item in safe_list(value.get("files")):
            found.extend(flatten_dicts(item))
        for child in safe_list(value.get("subsections")):
            found.extend(collect_files(child))
    elif isinstance(value, list):
        for item in value:
            found.extend(collect_files(item))
    return found


def collect_links(value: object) -> list[JsonObject]:
    found: list[JsonObject] = []
    if isinstance(value, dict):
        for item in safe_list(value.get("links")):
            found.extend(flatten_dicts(item))
        for child in safe_list(value.get("subsections")):
            found.extend(collect_links(child))
    elif isinstance(value, list):
        for item in value:
            found.extend(collect_links(item))
    return found


def flatten_dicts(value: object) -> list[JsonObject]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        flattened: list[JsonObject] = []
        for item in value:
            flattened.extend(flatten_dicts(item))
        return flattened
    return []


def attribute_values(attributes: list[Any]) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for item in attributes:
        if not isinstance(item, dict):
            continue
        name = normalize_space(item.get("name"))
        value = normalize_space(item.get("value"))
        if not name or not value:
            continue
        values.setdefault(name, []).append(value)
    return values


def values_from_sections(sections: list[JsonObject], section_type: str, attr_name: str) -> list[str]:
    values = []
    for section in sections:
        if not text_equal(section.get("type"), section_type):
            continue
        values.extend(attribute_values(safe_list(section.get("attributes"))).get(attr_name, []))
    return values


def study_sections(study: JsonObject) -> list[JsonObject]:
    sections = [
        {
            "key": "overview",
            "title": "Overview",
            "kind": "table",
            "rows": study_metadata(study),
        }
    ]
    if study["protocols"]:
        sections.append({"key": "protocols", "title": "Protocols", "kind": "table", "rows": study["protocols"]})
    if study["publications"]:
        sections.append({"key": "references", "title": "References", "kind": "list", "items": study["publications"]})
    if study["external_links"]:
        sections.append({"key": "links", "title": "External links", "kind": "list", "items": study["external_links"]})
    if study["files"]:
        sections.append({"key": "files", "title": "Files", "kind": "table", "rows": study["files"]})
    return sections


def study_previews(study: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews: list[JsonObject] = [
        {
            "kind": "table",
            "title": "Study overview",
            "section_key": "overview",
            "data": {"columns": ["label", "value"], "rows": study_metadata(study)},
        }
    ]
    if study["protocols"]:
        previews.append(
            {
                "kind": "table",
                "title": "Protocols",
                "section_key": "protocols",
                "data": {"columns": ["name", "type", "description", "hardware"], "rows": study["protocols"]},
            }
        )
    if study["publications"]:
        previews.append(
            {
                "kind": "citation_list",
                "title": "Publication references",
                "section_key": "references",
                "data": {"items": study["publications"]},
            }
        )
    if study["external_links"]:
        previews.append(
            {
                "kind": "xref_groups",
                "title": "External links",
                "section_key": "links",
                "data": {"groups": [{"source": "BioStudies links", "items": study["external_links"]}]},
            }
        )
    if study["files"]:
        previews.append(
            {
                "kind": "download_manifest",
                "title": "BioStudies file manifest",
                "section_key": "files",
                "actions": display_actions(links),
                "data": {"rows": study["files"]},
            }
        )
    return previews


def study_links(study: JsonObject) -> list[JsonObject]:
    links = [
        {"label": "Open BioStudies study", "url": study["url"], "kind": "external", "primary": True},
        {"label": "Open BioStudies API", "url": study["api_url"], "kind": "external"},
    ]
    if study.get("files_api_url"):
        links.append({"label": "Open files API", "url": study["files_api_url"], "kind": "external"})
    if study.get("file_info", {}).get("globus_link"):
        links.append({"label": "Open Globus location", "url": study["file_info"]["globus_link"], "kind": "external"})
    first_file_url = first_download_url(study["files"])
    if first_file_url:
        links.append({"label": "Open first file", "url": first_file_url, "kind": "download"})
    return links


def study_identifiers(study: JsonObject) -> JsonObject:
    identifiers: JsonObject = {
        "biostudies": {"namespace": "biostudies.study", "id": study["accession"], "label": study["accession"], "url": study["url"]}
    }
    if study["accession"].startswith("E-"):
        identifiers["arrayexpress"] = {
            "namespace": "arrayexpress.experiment",
            "id": study["accession"],
            "label": study["accession"],
            "url": study["url"],
        }
    pmids = [item for item in study["publications"] if item.get("pmid")]
    if pmids:
        identifiers["pmid"] = {"namespace": "pubmed", "id": pmids[0]["pmid"], "label": f"PMID:{pmids[0]['pmid']}", "url": pmids[0]["pmid_url"]}
    return identifiers


def study_metadata(study: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Accession", study["accession"]),
        ("Repository", study["repository_label"]),
        ("Release date", study["release_date"]),
        ("Organism", ", ".join(study["organisms"][:5])),
        ("Study type", ", ".join(study["study_types"][:5])),
        ("Sample count", study["sample_count"]),
        ("Assay count", study["assay_count"]),
        ("Technology", study["technology"]),
        ("Files", str(study["file_count"]) if study["file_count"] else ""),
        ("Authors", ", ".join(item["name"] for item in study["authors"][:3])),
        ("API", study["api_url"]),
    )


def study_subtitle(study: JsonObject) -> str:
    parts = [study["repository_label"]]
    if study["release_date"]:
        parts.append(study["release_date"])
    if study["organisms"]:
        parts.append(", ".join(study["organisms"][:2]))
    return " | ".join(parts)


def repository_label_for(repository: str, accession: str) -> str:
    if repository == "arrayexpress" or accession.startswith("E-"):
        return "ArrayExpress"
    return "BioStudies"


def first_download_url(files: list[JsonObject]) -> str:
    for item in files:
        url = safe_http_url(item.get("download_url"))
        if url:
            return url
    return ""


def file_download_url(http_base: str, path: str) -> str:
    if not http_base or not path:
        return ""
    return f"{http_base.rstrip('/')}/{urllib.parse.quote(path.lstrip('/'), safe='/')}"


def study_url(accession: str, website_base_url: str = BIOSTUDIES_WEBSITE_BASE_URL) -> str:
    return f"{website_base_url.rstrip('/')}/studies/{urllib.parse.quote(accession, safe='')}"


def api_url_for(endpoint: str, api_base_url: str, params: JsonObject) -> str:
    url = f"{api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    if not params:
        return url
    return f"{url}?{urllib.parse.urlencode(params, doseq=True)}"


def external_link_url(value: str, link_type: str, website_base_url: str) -> str:
    if value.startswith(("http://", "https://")):
        return safe_http_url(value)
    lowered = link_type.lower()
    if lowered == "doi" or value.startswith("10."):
        return f"https://doi.org/{urllib.parse.quote(value, safe='/')}"
    if lowered == "ena" or value.startswith(("ER", "SR", "DR")):
        return f"https://www.ebi.ac.uk/ena/browser/view/{urllib.parse.quote(value, safe=',-')}"
    if lowered in {"biostudies", "arrayexpress"} or value.startswith(("E-", "S-")):
        return study_url(value, website_base_url)
    if lowered == "gxa-sc":
        return f"https://www.ebi.ac.uk/gxa/sc/experiments/{urllib.parse.quote(value, safe='')}"
    return ""


def safe_http_url(value: object) -> str:
    text = normalize_space(value)
    if text.startswith(("http://", "https://")):
        return text
    return ""


def compact_fields(*pairs: tuple[str, object]) -> list[JsonObject]:
    fields = []
    for label, value in pairs:
        text = normalize_space(value)
        if text:
            fields.append({"label": label, "value": text})
    return fields


def compact_badges(*pairs: tuple[str, str]) -> list[JsonObject]:
    badges = []
    for label, kind in pairs:
        text = normalize_space(label)
        if text:
            badges.append({"label": text, "kind": kind})
    return badges


def display_actions(links: list[JsonObject]) -> list[JsonObject]:
    actions = []
    for link in links:
        url = safe_http_url(link.get("url"))
        label = normalize_space(link.get("label"))
        if url and label:
            actions.append({"label": label, "url": url, "kind": normalize_space(link.get("kind") or "external")})
    return actions


def unique_texts(values: list[Any]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        text = normalize_space(value)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def first_text(*values: object) -> str:
    for value in values:
        if isinstance(value, list):
            for item in value:
                text = normalize_space(item)
                if text:
                    return text
            continue
        text = normalize_space(value)
        if text:
            return text
    return ""


def first_value(values: list[str]) -> str:
    return values[0] if values else ""


def int_or_zero(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def human_size(size: int) -> str:
    if size <= 0:
        return ""
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return ""


def text_equal(value: object, expected: str) -> bool:
    return normalize_space(value).lower() == expected.lower()

