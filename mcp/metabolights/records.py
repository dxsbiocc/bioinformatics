"""Front-end compatible record envelopes for MetaboLights studies."""

from __future__ import annotations

import urllib.parse
from typing import Any

from .constants import (
    EBI_SEARCH_BASE_URL,
    METABOLIGHTS_WEBSITE_BASE_URL,
    METABOLIGHTS_WS_BASE_URL,
    RECORD_SCHEMA_VERSION,
    JsonObject,
)
from .utils import normalize_space, safe_list, strip_html


def metabolights_project_record(
    payload: JsonObject,
    *,
    files_payload: JsonObject | None = None,
    website_base_url: str = METABOLIGHTS_WEBSITE_BASE_URL,
    ws_base_url: str = METABOLIGHTS_WS_BASE_URL,
) -> JsonObject:
    normalized = normalize_study(payload, files_payload=files_payload or {}, website_base_url=website_base_url, ws_base_url=ws_base_url)
    return project_record_from_normalized(normalized)


def metabolights_search_record(
    entry: JsonObject,
    *,
    website_base_url: str = METABOLIGHTS_WEBSITE_BASE_URL,
    search_base_url: str = EBI_SEARCH_BASE_URL,
) -> JsonObject:
    normalized = normalize_search_entry(entry, website_base_url=website_base_url, search_base_url=search_base_url)
    return project_record_from_normalized(normalized)


def metabolights_file_manifest_record(
    accession: str,
    files_payload: JsonObject,
    *,
    study_payload: JsonObject | None = None,
    max_files: int | None = None,
    website_base_url: str = METABOLIGHTS_WEBSITE_BASE_URL,
    ws_base_url: str = METABOLIGHTS_WS_BASE_URL,
) -> JsonObject:
    accession = normalize_space(accession).upper()
    normalized_study = normalize_study(study_payload or {"mtblsStudy": {}, "isaInvestigation": {"identifier": accession}}, files_payload=files_payload, website_base_url=website_base_url, ws_base_url=ws_base_url)
    files = normalized_study["files"]
    if max_files is not None:
        files = files[:max_files]
    file_count = normalized_study["file_count"] or len(files)
    title = f"{accession} MetaboLights file manifest"
    url = normalized_study["url"]
    links = [
        {"label": "Open MetaboLights study", "url": url, "kind": "external", "primary": True},
        {"label": "Open MetaboLights files API", "url": normalized_study["files_api_url"], "kind": "external"},
    ]
    if normalized_study["ftp_http_url"]:
        links.append({"label": "Open FTP HTTPS folder", "url": normalized_study["ftp_http_url"], "kind": "external"})
    if normalized_study["globus_url"]:
        links.append({"label": "Open Globus location", "url": normalized_study["globus_url"], "kind": "external"})
    first_url = first_download_url(files)
    if first_url:
        links.append({"label": "Open first file", "url": first_url, "kind": "download"})
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.download_plan",
        "record_type": "metabolights_file_manifest",
        "database": "metabolights",
        "id": f"{accession}:files",
        "stable_id": f"{accession}:files",
        "label": f"{accession} files",
        "title": title,
        "description": f"{len(files)} metadata-only file rows. No download has been started.",
        "url": url,
        "icon": "download",
        "identifiers": {"metabolights": {"namespace": "metabolights.study", "id": accession, "label": accession, "url": url}},
        "links": links,
        "display": {
            "component": "download_plan",
            "chip_label": f"{accession} files",
            "icon": "download",
            "title": title,
            "subtitle": f"MetaboLights | {len(files)} returned file rows",
            "description": "Metadata-only MetaboLights file manifest. Review links before downloading data.",
            "metadata": compact_fields(
                ("Accession", accession),
                ("Returned files", str(len(files))),
                ("Total files", str(file_count) if file_count else ""),
                ("FTP HTTPS root", normalized_study["ftp_http_url"]),
                ("API", normalized_study["files_api_url"]),
            ),
            "badges": compact_badges(("MetaboLights", "source"), (accession, "identifier"), ("download plan", "record_type")),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": f"{len(files)} file rows",
                "icon": "download",
                "fields": compact_fields(
                    ("Accession", accession),
                    ("Returned files", str(len(files))),
                    ("URL", url),
                ),
            },
            "primary_url": url,
            "sections": [{"key": "files", "title": "Files", "kind": "table", "rows": files}],
            "previews": [
                {
                    "kind": "download_manifest",
                    "title": "MetaboLights file manifest",
                    "section_key": "files",
                    "actions": display_actions(links),
                    "data": {"rows": files},
                },
                {
                    "kind": "table",
                    "title": "Files",
                    "section_key": "files",
                    "data": {"columns": ["file", "type", "status", "directory", "download_url"], "rows": files},
                },
            ],
        },
        "related": {"files": files},
        "data": {
            "accession": accession,
            "files": files,
            "file_count": file_count,
            "url": url,
            "files_api_url": normalized_study["files_api_url"],
            "ftp_http_url": normalized_study["ftp_http_url"],
            "globus_url": normalized_study["globus_url"],
        },
    }


def project_record_from_normalized(study: JsonObject) -> JsonObject:
    accession = study["accession"]
    title = study["title"] or accession
    links = study_links(study)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.project",
        "record_type": "metabolights_study",
        "database": "metabolights",
        "id": accession,
        "stable_id": accession,
        "label": accession,
        "title": title,
        "description": study["description"] or "MetaboLights public metabolomics study",
        "url": study["url"],
        "icon": "metabolights",
        "identifiers": study_identifiers(study),
        "links": links,
        "display": {
            "component": "project",
            "chip_label": accession,
            "icon": "metabolights",
            "title": title,
            "subtitle": study_subtitle(study),
            "description": study["description"] or "MetaboLights study record",
            "metadata": study_metadata(study),
            "badges": compact_badges(
                ("MetaboLights", "source"),
                (accession, "identifier"),
                (study["status"], "status"),
                (study["category"], "record_type"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": study_subtitle(study),
                "icon": "metabolights",
                "fields": compact_fields(
                    ("Accession", accession),
                    ("Status", study["status"]),
                    ("Category", study["category"]),
                    ("Organism", ", ".join(study["organisms"][:3])),
                    ("Study design", ", ".join(study["study_designs"][:3])),
                    ("Public release", study["public_release_date"]),
                    ("URL", study["url"]),
                ),
            },
            "primary_url": study["url"],
            "sections": study_sections(study),
            "previews": study_previews(study, links),
        },
        "related": {
            "publications": study["publications"],
            "protocols": study["protocols"],
            "assays": study["assays"],
            "files": study["files"],
        },
        "data": study,
    }


def normalize_study(
    payload: JsonObject,
    *,
    files_payload: JsonObject,
    website_base_url: str,
    ws_base_url: str,
) -> JsonObject:
    mtbls = payload.get("mtblsStudy") if isinstance(payload.get("mtblsStudy"), dict) else {}
    investigation = payload.get("isaInvestigation") if isinstance(payload.get("isaInvestigation"), dict) else {}
    studies = [item for item in safe_list(investigation.get("studies")) if isinstance(item, dict)]
    study = studies[0] if studies else {}
    accession = first_text(investigation.get("identifier"), study.get("identifier"), mtbls.get("studyPermission", {}).get("studyId") if isinstance(mtbls.get("studyPermission"), dict) else "")
    accession = normalize_space(accession).upper()
    ftp_http_url = https_url(first_text(mtbls.get("studyHttpUrl")))
    files = normalize_files(files_payload, accession=accession, ftp_http_url=ftp_http_url)
    return {
        "accession": accession,
        "title": first_text(study.get("title"), investigation.get("title")),
        "description": first_text(study.get("description"), investigation.get("description")),
        "status": first_text(mtbls.get("studyStatus"), mtbls.get("studyPermission", {}).get("studyStatus") if isinstance(mtbls.get("studyPermission"), dict) else ""),
        "category": first_text(mtbls.get("studyCategory"), comment_value(study, "Study Category")),
        "submission_date": first_text(study.get("submissionDate"), investigation.get("submissionDate")),
        "public_release_date": first_text(study.get("publicReleaseDate"), investigation.get("publicReleaseDate"), mtbls.get("firstPublicDate")),
        "modified_time": first_text(mtbls.get("modifiedTime")),
        "revision_date": first_text(mtbls.get("revisionDatetime"), comment_value(study, "Revision Date")),
        "license": first_text(mtbls.get("datasetLicense"), comment_value(study, "License")),
        "license_url": first_text(mtbls.get("datasetLicenseUrl")),
        "organisms": unique_texts(annotation_values(study.get("characteristicCategories"))),
        "study_designs": unique_texts(annotation_values(study.get("studyDesignDescriptors"))),
        "factors": normalize_factors(safe_list(study.get("factors"))),
        "assays": normalize_assays(safe_list(study.get("assays"))),
        "protocols": normalize_protocols(safe_list(study.get("protocols"))),
        "publications": normalize_publications(safe_list(study.get("publications"))),
        "people": normalize_people(safe_list(study.get("people"))),
        "files": files,
        "file_count": len(files),
        "url": study_url(accession, website_base_url),
        "api_url": api_url_for(f"studies/{accession}", ws_base_url, {}),
        "files_api_url": api_url_for(f"studies/{accession}/files", ws_base_url, {}),
        "ftp_http_url": ftp_http_url,
        "ftp_url": first_text(mtbls.get("studyFtpUrl")),
        "globus_url": first_text(mtbls.get("studyGlobusUrl")),
        "aspera_path": first_text(mtbls.get("studyAsperaPath")),
        "source": "metabolights_ws",
    }


def normalize_search_entry(entry: JsonObject, *, website_base_url: str, search_base_url: str) -> JsonObject:
    accession = normalize_space(entry.get("id")).upper()
    fields = entry.get("fields") if isinstance(entry.get("fields"), dict) else {}
    title = first_from_field(fields, "name")
    description = strip_html(first_from_field(fields, "description"))
    organisms = field_values(fields, "organism")
    study_designs = field_values(fields, "study_design")
    return {
        "accession": accession,
        "title": title,
        "description": description,
        "status": "",
        "category": "",
        "submission_date": "",
        "public_release_date": "",
        "modified_time": "",
        "revision_date": "",
        "license": "",
        "license_url": "",
        "organisms": organisms,
        "study_designs": study_designs,
        "factors": [],
        "assays": [],
        "protocols": [],
        "publications": [],
        "people": [],
        "files": [],
        "file_count": 0,
        "url": study_url(accession, website_base_url),
        "api_url": "",
        "files_api_url": "",
        "search_api_url": api_url_for("metabolights", search_base_url, {"query": accession, "format": "json"}),
        "ftp_http_url": "",
        "ftp_url": "",
        "globus_url": "",
        "aspera_path": "",
        "source": "ebi_search",
    }


def normalize_files(payload: JsonObject, *, accession: str, ftp_http_url: str) -> list[JsonObject]:
    rows: list[JsonObject] = []
    for group in ["study", "latest", "private"]:
        for item in safe_list(payload.get(group)):
            if not isinstance(item, dict):
                continue
            file_name = first_text(item.get("file"), item.get("name"))
            if not file_name:
                continue
            is_directory = bool(item.get("directory"))
            download_url = ""
            if ftp_http_url and not is_directory:
                download_url = f"{ftp_http_url.rstrip('/')}/{urllib.parse.quote(file_name, safe='/')}"
            rows.append(
                {
                    "file": file_name,
                    "type": first_text(item.get("type")),
                    "status": first_text(item.get("status")),
                    "created_at": first_text(item.get("createdAt")),
                    "timestamp": first_text(item.get("timestamp")),
                    "directory": is_directory,
                    "group": group,
                    "download_url": download_url,
                    "accession": accession,
                }
            )
    return rows


def normalize_assays(items: list[Any]) -> list[JsonObject]:
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "measurement_type": annotation_value(item.get("measurementType")),
                "technology_type": annotation_value(item.get("technologyType")),
                "technology_platform": normalize_space(item.get("technologyPlatform")),
                "filename": normalize_space(item.get("filename")),
            }
        )
    return [row for row in rows if any(row.values())]


def normalize_protocols(items: list[Any]) -> list[JsonObject]:
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "name": normalize_space(item.get("name")),
                "type": annotation_value(item.get("protocolType")),
                "description": normalize_space(item.get("description")),
                "uri": normalize_space(item.get("uri")),
                "version": normalize_space(item.get("version")),
            }
        )
    return [row for row in rows if row["name"] or row["type"] or row["description"]]


def normalize_publications(items: list[Any]) -> list[JsonObject]:
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        pmid = normalize_space(item.get("pubMedID"))
        doi = normalize_space(item.get("doi"))
        rows.append(
            {
                "title": normalize_space(item.get("title")),
                "authors": normalize_space(item.get("authorList")),
                "pmid": pmid,
                "doi": doi,
                "status": annotation_value(item.get("status")),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else (f"https://doi.org/{doi}" if doi else ""),
            }
        )
    return [row for row in rows if row["title"] or row["pmid"] or row["doi"]]


def normalize_people(items: list[Any]) -> list[JsonObject]:
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = " ".join(part for part in [normalize_space(item.get("firstName")), normalize_space(item.get("lastName"))] if part)
        rows.append(
            {
                "name": name,
                "email": normalize_space(item.get("email")),
                "affiliation": normalize_space(item.get("affiliation")),
                "roles": annotation_values(item.get("roles")),
            }
        )
    return [row for row in rows if row["name"] or row["affiliation"]]


def normalize_factors(items: list[Any]) -> list[JsonObject]:
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        rows.append({"name": normalize_space(item.get("factorName")), "type": annotation_value(item.get("factorType"))})
    return [row for row in rows if row["name"] or row["type"]]


def study_sections(study: JsonObject) -> list[JsonObject]:
    sections = [{"key": "overview", "title": "Overview", "kind": "table", "rows": study_metadata(study)}]
    if study["assays"]:
        sections.append({"key": "assays", "title": "Assays", "kind": "table", "rows": study["assays"]})
    if study["protocols"]:
        sections.append({"key": "protocols", "title": "Protocols", "kind": "table", "rows": study["protocols"][:10]})
    if study["publications"]:
        sections.append({"key": "publications", "title": "Publications", "kind": "list", "items": study["publications"]})
    if study["files"]:
        sections.append({"key": "files", "title": "Files", "kind": "table", "rows": study["files"]})
    return sections


def study_previews(study: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews: list[JsonObject] = [
        {
            "kind": "table",
            "title": "Study summary",
            "section_key": "overview",
            "data": {"columns": ["label", "value"], "rows": study_metadata(study)},
        }
    ]
    if study["assays"]:
        previews.append({"kind": "table", "title": "Assays", "section_key": "assays", "data": {"columns": ["measurement_type", "technology_type", "technology_platform", "filename"], "rows": study["assays"]}})
    if study["publications"]:
        previews.append({"kind": "citation_list", "title": "Publications", "section_key": "publications", "data": {"citations": study["publications"]}})
    if study["files"]:
        previews.append({"kind": "download_manifest", "title": "MetaboLights files", "section_key": "files", "actions": display_actions(links), "data": {"rows": study["files"]}})
    previews.append({"kind": "xref_groups", "title": "Identifiers and links", "actions": display_actions(links), "data": {"groups": xref_groups(study)}})
    return previews


def study_links(study: JsonObject) -> list[JsonObject]:
    links = [{"label": "Open MetaboLights study", "url": study["url"], "kind": "external", "primary": True}]
    if study.get("api_url"):
        links.append({"label": "Open MetaboLights API", "url": study["api_url"], "kind": "external"})
    if study.get("files_api_url"):
        links.append({"label": "Open MetaboLights files API", "url": study["files_api_url"], "kind": "external"})
    if study.get("ftp_http_url"):
        links.append({"label": "Open FTP HTTPS folder", "url": study["ftp_http_url"], "kind": "external"})
    if study.get("globus_url"):
        links.append({"label": "Open Globus location", "url": study["globus_url"], "kind": "external"})
    if study.get("license_url"):
        links.append({"label": "Open license", "url": study["license_url"], "kind": "external"})
    return links


def study_identifiers(study: JsonObject) -> JsonObject:
    return {"metabolights": {"namespace": "metabolights.study", "id": study["accession"], "label": study["accession"], "url": study["url"]}}


def study_metadata(study: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Accession", study["accession"]),
        ("Status", study["status"]),
        ("Category", study["category"]),
        ("Public release", study["public_release_date"]),
        ("Submission date", study["submission_date"]),
        ("Revision date", study["revision_date"]),
        ("Study design", ", ".join(study["study_designs"][:5])),
        ("Organism", ", ".join(study["organisms"][:5])),
        ("Assays", str(len(study["assays"])) if study["assays"] else ""),
        ("Protocols", str(len(study["protocols"])) if study["protocols"] else ""),
        ("Files", str(study["file_count"]) if study["file_count"] else ""),
        ("License", study["license"]),
        ("API", study.get("api_url", "")),
    )


def xref_groups(study: JsonObject) -> list[JsonObject]:
    groups = [{"source": "MetaboLights", "items": [{"label": study["accession"], "id": study["accession"], "url": study["url"]}]}]
    publications = []
    for publication in study["publications"]:
        if publication.get("pmid"):
            publications.append({"label": f"PMID:{publication['pmid']}", "id": publication["pmid"], "url": publication["url"]})
        elif publication.get("doi"):
            publications.append({"label": f"DOI:{publication['doi']}", "id": publication["doi"], "url": publication["url"]})
    if publications:
        groups.append({"source": "Publications", "items": publications})
    if study["study_designs"]:
        groups.append({"source": "Study design", "items": [{"label": item, "id": item, "url": ""} for item in study["study_designs"]]})
    return groups


def study_subtitle(study: JsonObject) -> str:
    parts = ["MetaboLights"]
    for value in [study["status"], study["category"], first_value(study["study_designs"]), first_value(study["organisms"])]:
        if value:
            parts.append(value)
    return " | ".join(parts)


def study_url(accession: str, website_base_url: str) -> str:
    return f"{website_base_url.rstrip('/')}/{urllib.parse.quote(accession, safe='')}"


def api_url_for(endpoint: str, base_url: str, params: JsonObject) -> str:
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    if not params:
        return url
    return f"{url}?{urllib.parse.urlencode(params, doseq=True)}"


def https_url(url: str) -> str:
    if url.startswith("http://"):
        return "https://" + url[len("http://") :]
    return url


def display_actions(links: list[JsonObject]) -> list[JsonObject]:
    actions = []
    for link in links:
        url = normalize_space(link.get("url"))
        label = normalize_space(link.get("label"))
        if url.startswith(("http://", "https://")) and label:
            actions.append({"label": label, "url": url, "kind": normalize_space(link.get("kind") or "external")})
    return actions


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


def first_download_url(files: list[JsonObject]) -> str:
    for item in files:
        url = normalize_space(item.get("download_url"))
        if url.startswith(("http://", "https://")):
            return url
    return ""


def field_values(fields: JsonObject, name: str) -> list[str]:
    return unique_texts([strip_html(item) for item in safe_list(fields.get(name))])


def first_from_field(fields: JsonObject, name: str) -> str:
    values = field_values(fields, name)
    return values[0] if values else ""


def annotation_value(value: object) -> str:
    if isinstance(value, dict):
        return normalize_space(value.get("annotationValue"))
    return normalize_space(value)


def annotation_values(value: object) -> list[str]:
    return unique_texts([annotation_value(item) for item in safe_list(value)])


def comment_value(item: JsonObject, name: str) -> str:
    for comment in safe_list(item.get("comments")):
        if isinstance(comment, dict) and normalize_space(comment.get("name")).lower() == name.lower():
            return normalize_space(comment.get("value"))
    return ""


def first_text(*values: object) -> str:
    for value in values:
        text = normalize_space(value)
        if text:
            return text
    return ""


def first_value(values: list[str]) -> str:
    return values[0] if values else ""


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
