"""Front-end compatible record envelopes for ENCODE records."""

from __future__ import annotations

from typing import Any

from .constants import ENCODE_BASE_URL, RECORD_SCHEMA_VERSION, JsonObject
from .utils import normalize_space, safe_list

ORGANISM_LABELS = {
    "human": "Homo sapiens",
    "mouse": "Mus musculus",
    "fly": "Drosophila melanogaster",
    "worm": "Caenorhabditis elegans",
    "rat": "Rattus norvegicus",
    "zebrafish": "Danio rerio",
}


def encode_experiment_record(
    experiment: JsonObject,
    *,
    files: list[JsonObject] | None = None,
    base_url: str = ENCODE_BASE_URL,
) -> JsonObject:
    normalized = normalize_experiment(experiment, files=files, base_url=base_url)
    accession = normalized["accession"]
    title = normalized["title"] or accession
    links = experiment_links(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.project",
        "record_type": "encode_experiment",
        "database": "encode",
        "id": accession,
        "stable_id": accession,
        "label": accession,
        "title": title,
        "description": normalized["description"] or "ENCODE experiment metadata",
        "url": normalized["url"],
        "icon": "encode",
        "identifiers": experiment_identifiers(normalized),
        "links": links,
        "display": {
            "component": "project",
            "chip_label": accession,
            "icon": "encode",
            "title": title,
            "subtitle": experiment_subtitle(normalized),
            "description": normalized["description"] or "ENCODE experiment record",
            "metadata": experiment_metadata(normalized),
            "badges": compact_badges(
                ("ENCODE", "source"),
                (accession, "identifier"),
                (normalized["assay_title"], "record_type"),
                (normalized["status"], "status"),
                (normalized["biosample_term_name"], "context"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": experiment_subtitle(normalized),
                "icon": "encode",
                "fields": compact_fields(
                    ("Accession", accession),
                    ("Assay", normalized["assay_title"]),
                    ("Biosample", normalized["biosample_term_name"]),
                    ("Organism", normalized["organism"]),
                    ("Status", normalized["status"]),
                    ("Files", str(len(normalized["files"])) if normalized["files"] else ""),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": experiment_sections(normalized),
            "previews": experiment_previews(normalized, links),
        },
        "related": {
            "dbxrefs": normalized["dbxrefs"],
            "files": normalized["files"],
            "assemblies": normalized["assemblies"],
        },
        "data": normalized,
    }


def encode_file_record(file_item: JsonObject, *, base_url: str = ENCODE_BASE_URL) -> JsonObject:
    normalized = normalize_file(file_item, base_url=base_url)
    return encode_file_manifest_record(
        normalized["dataset_accession"] or normalized["accession"],
        [normalized],
        title=f"{normalized['accession']} ENCODE file",
        base_url=base_url,
        record_id=normalized["accession"],
        record_type="encode_file",
    )


def encode_biosample_record(biosample: JsonObject, *, base_url: str = ENCODE_BASE_URL) -> JsonObject:
    normalized = normalize_biosample(biosample, base_url=base_url)
    accession = normalized["accession"]
    title = normalized["summary"] or normalized["description"] or accession
    links = biosample_links(normalized)
    metadata = biosample_metadata(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.sample",
        "record_type": "encode_biosample",
        "database": "encode",
        "id": accession,
        "stable_id": accession,
        "label": accession,
        "title": title,
        "description": normalized["description"] or normalized["summary"] or "ENCODE biosample metadata",
        "url": normalized["url"],
        "icon": "encode",
        "identifiers": biosample_identifiers(normalized),
        "links": links,
        "display": {
            "component": "sample",
            "chip_label": accession,
            "icon": "encode",
            "title": title,
            "subtitle": biosample_subtitle(normalized),
            "description": normalized["description"] or normalized["summary"] or "ENCODE biosample record",
            "metadata": metadata,
            "badges": compact_badges(
                ("ENCODE", "source"),
                (accession, "identifier"),
                (normalized["biosample_term_name"], "record_type"),
                (normalized["status"], "status"),
                (normalized["organism"], "context"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": biosample_subtitle(normalized),
                "icon": "encode",
                "fields": compact_fields(
                    ("Accession", accession),
                    ("Biosample", normalized["biosample_term_name"]),
                    ("Organism", normalized["organism"]),
                    ("Life stage", normalized["life_stage"]),
                    ("Sex", normalized["sex"]),
                    ("Status", normalized["status"]),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": biosample_sections(normalized),
            "previews": [
                {"kind": "table", "title": "Biosample summary", "section_key": "overview", "data": {"columns": ["label", "value"], "rows": metadata}},
                {"kind": "xref_groups", "title": "ENCODE and external links", "actions": display_actions(links), "data": {"groups": biosample_xref_groups(normalized)}},
            ],
        },
        "related": {
            "dbxrefs": normalized["dbxrefs"],
            "aliases": normalized["aliases"],
            "alternate_accessions": normalized["alternate_accessions"],
        },
        "data": normalized,
    }


def encode_file_manifest_record(
    experiment_accession: str,
    files: list[JsonObject],
    *,
    title: str | None = None,
    base_url: str = ENCODE_BASE_URL,
    record_id: str | None = None,
    record_type: str = "encode_file_manifest",
) -> JsonObject:
    accession = normalize_space(experiment_accession).upper()
    normalized_files = [item if item.get("download_url") else normalize_file(item, base_url=base_url) for item in files]
    normalized_files = [item for item in normalized_files if item.get("accession")]
    url = experiment_url(accession, base_url) if accession.startswith("ENCSR") else file_url(accession, base_url)
    api_url = encode_api_url(f"experiments/{accession}/", base_url, {}) if accession.startswith("ENCSR") else encode_api_url(f"files/{accession}/", base_url, {})
    label = title or f"{accession} ENCODE file manifest"
    links = [
        {"label": "Open ENCODE record", "url": url, "kind": "external", "primary": True},
        {"label": "Open ENCODE API", "url": api_url, "kind": "external"},
    ]
    first_download = first_download_url(normalized_files)
    if first_download:
        links.append({"label": "Open first file", "url": first_download, "kind": "download"})
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.download_plan",
        "record_type": record_type,
        "database": "encode",
        "id": record_id or f"{accession}:files",
        "stable_id": record_id or f"{accession}:files",
        "label": label,
        "title": label,
        "description": f"{len(normalized_files)} metadata-only ENCODE file rows. No download has been started.",
        "url": url,
        "icon": "download",
        "identifiers": {"encode": {"namespace": "encode", "id": accession, "label": accession, "url": url}},
        "links": links,
        "display": {
            "component": "download_plan",
            "chip_label": f"{accession} files",
            "icon": "download",
            "title": label,
            "subtitle": f"ENCODE | {len(normalized_files)} file rows",
            "description": "Metadata-only ENCODE file manifest. Review links before downloading data.",
            "metadata": compact_fields(
                ("ENCODE record", accession),
                ("Returned files", str(len(normalized_files))),
                ("First file", normalized_files[0]["accession"] if normalized_files else ""),
                ("API", api_url),
            ),
            "badges": compact_badges(("ENCODE", "source"), (accession, "identifier"), ("download plan", "record_type")),
            "actions": display_actions(links),
            "hover": {
                "title": label,
                "subtitle": f"{len(normalized_files)} file rows",
                "icon": "download",
                "fields": compact_fields(("ENCODE record", accession), ("Returned files", str(len(normalized_files))), ("URL", url)),
            },
            "primary_url": url,
            "sections": [{"key": "files", "title": "Files", "kind": "table", "rows": normalized_files}],
            "previews": [
                {"kind": "download_manifest", "title": "ENCODE file manifest", "section_key": "files", "actions": display_actions(links), "data": {"rows": normalized_files}},
                {
                    "kind": "table",
                    "title": "Files",
                    "section_key": "files",
                    "data": {"columns": ["accession", "file_format", "output_type", "assembly", "download_url", "file_size"], "rows": normalized_files},
                },
            ],
        },
        "related": {"files": normalized_files},
        "data": {"accession": accession, "files": normalized_files, "url": url, "api_url": api_url},
    }


def normalize_experiment(experiment: JsonObject, *, files: list[JsonObject] | None, base_url: str) -> JsonObject:
    accession = normalize_space(experiment.get("accession")).upper()
    embedded_files = [item for item in safe_list(files if files is not None else experiment.get("files")) if isinstance(item, dict)]
    biosample = experiment.get("biosample_ontology") if isinstance(experiment.get("biosample_ontology"), dict) else {}
    lab = experiment.get("lab") if isinstance(experiment.get("lab"), dict) else {}
    organism = experiment.get("organism") if isinstance(experiment.get("organism"), dict) else {}
    dbxrefs = unique_texts(safe_list(experiment.get("dbxrefs")))
    assay = first_text(experiment.get("assay_title"), experiment.get("assay_term_name"))
    biosample_term = first_text(biosample.get("term_name"), experiment.get("biosample_summary"), experiment.get("simple_biosample_summary"))
    return {
        "accession": accession,
        "title": f"{assay} in {biosample_term}".strip() if assay and biosample_term else assay or accession,
        "description": first_text(experiment.get("description"), experiment.get("biosample_summary"), experiment.get("simple_biosample_summary")),
        "assay_title": assay,
        "assay_term_name": first_text(experiment.get("assay_term_name")),
        "assay_term_id": first_text(experiment.get("assay_term_id")),
        "assay_slims": unique_texts(safe_list(experiment.get("assay_slims"))),
        "status": first_text(experiment.get("status")),
        "date_released": first_text(experiment.get("date_released")),
        "biosample_term_name": biosample_term,
        "biosample_term_id": first_text(biosample.get("term_id")),
        "biosample_classification": first_text(biosample.get("classification")),
        "organism": first_text(organism.get("scientific_name"), experiment.get("organism")),
        "lab": first_text(lab.get("title"), lab.get("name")),
        "award": object_id(experiment.get("award")),
        "assemblies": unique_texts(safe_list(experiment.get("assembly"))),
        "dbxrefs": dbxrefs,
        "files": [normalize_file(item, base_url=base_url) for item in embedded_files],
        "url": experiment_url(accession, base_url),
        "api_url": encode_api_url(f"experiments/{accession}/", base_url, {}),
        "source_url": first_text(experiment.get("@id")),
    }


def normalize_file(file_item: JsonObject, *, base_url: str) -> JsonObject:
    accession = normalize_space(file_item.get("accession")).upper()
    href = first_text(file_item.get("href"))
    cloud = file_item.get("cloud_metadata") if isinstance(file_item.get("cloud_metadata"), dict) else {}
    dataset = object_id(file_item.get("dataset"))
    return {
        "accession": accession,
        "file_format": first_text(file_item.get("file_format"), file_item.get("file_type")),
        "file_type": first_text(file_item.get("file_type")),
        "output_type": first_text(file_item.get("output_type")),
        "output_category": first_text(file_item.get("output_category")),
        "status": first_text(file_item.get("status")),
        "assembly": first_text(file_item.get("assembly")),
        "dataset": dataset,
        "dataset_accession": dataset.rstrip("/").split("/")[-1] if dataset.startswith("/experiments/") else "",
        "biological_replicates": safe_list(file_item.get("biological_replicates")),
        "technical_replicates": safe_list(file_item.get("technical_replicates")),
        "file_size": int_or_zero(file_item.get("file_size") or cloud.get("file_size")),
        "md5sum": first_text(file_item.get("md5sum")),
        "download_url": absolute_encode_url(href, base_url) if href else first_text(cloud.get("url")),
        "cloud_url": first_text(cloud.get("url")),
        "s3_uri": first_text(file_item.get("s3_uri")),
        "azure_uri": first_text(file_item.get("azure_uri")),
        "url": file_url(accession, base_url),
        "api_url": encode_api_url(f"files/{accession}/", base_url, {}),
    }


def normalize_biosample(biosample: JsonObject, *, base_url: str) -> JsonObject:
    accession = normalize_space(biosample.get("accession")).upper()
    ontology = biosample.get("biosample_ontology")
    organism = biosample.get("organism")
    donor = biosample.get("donor")
    source = biosample.get("source")
    lab = biosample.get("lab")
    award = biosample.get("award")
    return {
        "accession": accession,
        "summary": first_text(biosample.get("summary"), biosample.get("simple_summary")),
        "description": first_text(biosample.get("description"), biosample.get("notes")),
        "biosample_term_name": biosample_term_name(ontology, biosample),
        "biosample_term_id": biosample_term_id(ontology, biosample),
        "biosample_classification": biosample_classification(ontology),
        "biosample_ontology": object_id(ontology),
        "organism": organism_label(organism),
        "organism_id": object_id(organism),
        "life_stage": first_text(biosample.get("life_stage")),
        "age": age_label(biosample),
        "sex": first_text(biosample.get("sex")),
        "health_status": first_text(biosample.get("health_status")),
        "status": first_text(biosample.get("status")),
        "date_created": first_text(biosample.get("date_created")),
        "donor": object_id(donor),
        "source": object_id(source),
        "lab": object_id(lab),
        "award": object_id(award),
        "aliases": unique_texts(safe_list(biosample.get("aliases"))),
        "alternate_accessions": unique_texts(safe_list(biosample.get("alternate_accessions"))),
        "dbxrefs": unique_texts(safe_list(biosample.get("dbxrefs"))),
        "treatments": object_ids(safe_list(biosample.get("treatments"))),
        "genetic_modifications": object_ids(safe_list(biosample.get("genetic_modifications"))),
        "applied_modifications": object_ids(safe_list(biosample.get("applied_modifications"))),
        "url": biosample_url(accession, base_url),
        "api_url": encode_api_url(f"biosamples/{accession}/", base_url, {}),
        "source_url": first_text(biosample.get("@id")),
        "base_url": base_url,
    }


def experiment_sections(experiment: JsonObject) -> list[JsonObject]:
    sections = [{"key": "overview", "title": "Overview", "kind": "table", "rows": experiment_metadata(experiment)}]
    if experiment["files"]:
        sections.append({"key": "files", "title": "Files", "kind": "table", "rows": experiment["files"]})
    if experiment["dbxrefs"]:
        sections.append({"key": "external_ids", "title": "External identifiers", "kind": "table", "rows": [{"label": "dbxref", "value": value} for value in experiment["dbxrefs"]]})
    return sections


def biosample_sections(biosample: JsonObject) -> list[JsonObject]:
    sections = [{"key": "overview", "title": "Overview", "kind": "table", "rows": biosample_metadata(biosample)}]
    if biosample["dbxrefs"]:
        sections.append({"key": "external_ids", "title": "External identifiers", "kind": "table", "rows": [{"label": "dbxref", "value": value} for value in biosample["dbxrefs"]]})
    relationships = compact_fields(
        ("Donor", biosample["donor"]),
        ("Source", biosample["source"]),
        ("Lab", biosample["lab"]),
        ("Award", biosample["award"]),
        ("Treatments", ", ".join(biosample["treatments"])),
        ("Genetic modifications", ", ".join(biosample["genetic_modifications"])),
        ("Applied modifications", ", ".join(biosample["applied_modifications"])),
    )
    if relationships:
        sections.append({"key": "relationships", "title": "Relationships", "kind": "table", "rows": relationships})
    return sections


def experiment_previews(experiment: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews: list[JsonObject] = [
        {"kind": "table", "title": "Experiment summary", "section_key": "overview", "data": {"columns": ["label", "value"], "rows": experiment_metadata(experiment)}},
        {"kind": "xref_groups", "title": "ENCODE and external links", "actions": display_actions(links), "data": {"groups": experiment_xref_groups(experiment)}},
    ]
    if experiment["files"]:
        previews.insert(
            1,
            {
                "kind": "download_manifest",
                "title": "ENCODE files",
                "section_key": "files",
                "actions": display_actions(links),
                "data": {"rows": experiment["files"]},
            },
        )
    return previews


def experiment_metadata(experiment: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Accession", experiment["accession"]),
        ("Assay", experiment["assay_title"]),
        ("Biosample", experiment["biosample_term_name"]),
        ("Biosample ontology", experiment["biosample_term_id"]),
        ("Organism", experiment["organism"]),
        ("Status", experiment["status"]),
        ("Date released", experiment["date_released"]),
        ("Assemblies", ", ".join(experiment["assemblies"])),
        ("Lab", experiment["lab"]),
        ("Files", str(len(experiment["files"])) if experiment["files"] else ""),
        ("API", experiment["api_url"]),
    )


def biosample_metadata(biosample: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Accession", biosample["accession"]),
        ("Summary", biosample["summary"]),
        ("Biosample", biosample["biosample_term_name"]),
        ("Biosample ontology", biosample["biosample_term_id"]),
        ("Classification", biosample["biosample_classification"]),
        ("Organism", biosample["organism"]),
        ("Life stage", biosample["life_stage"]),
        ("Age", biosample["age"]),
        ("Sex", biosample["sex"]),
        ("Health status", biosample["health_status"]),
        ("Status", biosample["status"]),
        ("Date created", biosample["date_created"]),
        ("Donor", biosample["donor"]),
        ("Source", biosample["source"]),
        ("Lab", biosample["lab"]),
        ("API", biosample["api_url"]),
    )


def experiment_links(experiment: JsonObject) -> list[JsonObject]:
    links = [
        {"label": "Open ENCODE experiment", "url": experiment["url"], "kind": "external", "primary": True},
        {"label": "Open ENCODE API", "url": experiment["api_url"], "kind": "external"},
    ]
    for dbxref in experiment["dbxrefs"]:
        url = dbxref_url(dbxref)
        if url:
            links.append({"label": f"Open {dbxref}", "url": url, "kind": "external"})
    first_download = first_download_url(experiment["files"])
    if first_download:
        links.append({"label": "Open first file", "url": first_download, "kind": "download"})
    return links


def biosample_links(biosample: JsonObject) -> list[JsonObject]:
    base_url = biosample.get("base_url", ENCODE_BASE_URL)
    links = [
        {"label": "Open ENCODE biosample", "url": biosample["url"], "kind": "external", "primary": True},
        {"label": "Open ENCODE API", "url": biosample["api_url"], "kind": "external"},
    ]
    for field in ["biosample_ontology", "organism_id", "donor", "source", "lab", "award"]:
        url = encode_path_url(biosample.get(field, ""), base_url)
        if url:
            links.append({"label": f"Open {field.replace('_', ' ')}", "url": url, "kind": "external"})
    for dbxref in biosample["dbxrefs"]:
        url = dbxref_url(dbxref)
        if url:
            links.append({"label": f"Open {dbxref}", "url": url, "kind": "external"})
    return links


def experiment_identifiers(experiment: JsonObject) -> JsonObject:
    identifiers: JsonObject = {
        "encode": {"namespace": "encode.experiment", "id": experiment["accession"], "label": experiment["accession"], "url": experiment["url"]}
    }
    geo_ids = [xref.split(":", 1)[1] for xref in experiment["dbxrefs"] if xref.startswith("GEO:")]
    if geo_ids:
        identifiers["geo"] = {"namespace": "geo.series", "id": geo_ids[0], "label": geo_ids[0], "url": dbxref_url(f"GEO:{geo_ids[0]}")}
    return identifiers


def biosample_identifiers(biosample: JsonObject) -> JsonObject:
    identifiers: JsonObject = {
        "encode": {"namespace": "encode.biosample", "id": biosample["accession"], "label": biosample["accession"], "url": biosample["url"]}
    }
    geo_ids = [xref.split(":", 1)[1] for xref in biosample["dbxrefs"] if xref.startswith("GEO:")]
    if geo_ids:
        identifiers["geo"] = {"namespace": "geo.sample", "id": geo_ids[0], "label": geo_ids[0], "url": dbxref_url(f"GEO:{geo_ids[0]}")}
    return identifiers


def experiment_xref_groups(experiment: JsonObject) -> list[JsonObject]:
    groups = [{"source": "ENCODE", "items": [{"label": experiment["accession"], "id": experiment["accession"], "url": experiment["url"]}]}]
    if experiment["dbxrefs"]:
        groups.append(
            {
                "source": "External identifiers",
                "items": [{"label": value, "id": value, "url": dbxref_url(value)} for value in experiment["dbxrefs"] if dbxref_url(value)],
            }
        )
    if experiment["files"]:
        groups.append(
            {
                "source": "Files",
                "items": [{"label": item["accession"], "id": item["accession"], "url": item["url"]} for item in experiment["files"][:10]],
            }
        )
    return groups


def biosample_xref_groups(biosample: JsonObject) -> list[JsonObject]:
    base_url = biosample.get("base_url", ENCODE_BASE_URL)
    groups = [{"source": "ENCODE", "items": [{"label": biosample["accession"], "id": biosample["accession"], "url": biosample["url"]}]}]
    related_items = []
    for label, key in [
        ("Biosample ontology", "biosample_ontology"),
        ("Organism", "organism_id"),
        ("Donor", "donor"),
        ("Source", "source"),
        ("Lab", "lab"),
        ("Award", "award"),
    ]:
        value = biosample.get(key, "")
        url = encode_path_url(value, base_url)
        if value and url:
            related_items.append({"label": label, "id": value, "url": url})
    if related_items:
        groups.append({"source": "ENCODE related records", "items": related_items})
    if biosample["dbxrefs"]:
        groups.append(
            {
                "source": "External identifiers",
                "items": [{"label": value, "id": value, "url": dbxref_url(value)} for value in biosample["dbxrefs"] if dbxref_url(value)],
            }
        )
    return groups


def experiment_subtitle(experiment: JsonObject) -> str:
    parts = [experiment["assay_title"], experiment["biosample_term_name"], experiment["organism"], experiment["status"]]
    return "ENCODE | " + " | ".join(item for item in parts if item)


def biosample_subtitle(biosample: JsonObject) -> str:
    parts = [biosample["biosample_term_name"], biosample["organism"], biosample["status"]]
    return "ENCODE biosample | " + " | ".join(item for item in parts if item)


def first_download_url(files: list[JsonObject]) -> str:
    for item in files:
        url = first_text(item.get("download_url"), item.get("cloud_url"))
        if url.startswith(("http://", "https://")):
            return url
    return ""


def display_actions(links: list[JsonObject]) -> list[JsonObject]:
    return [{"label": link["label"], "url": link["url"], "kind": link.get("kind", "external")} for link in links if link.get("url", "").startswith(("http://", "https://"))]


def compact_fields(*pairs: tuple[str, Any]) -> list[JsonObject]:
    fields: list[JsonObject] = []
    for label, value in pairs:
        text = normalize_space(value)
        if text:
            fields.append({"label": label, "value": text})
    return fields


def compact_badges(*pairs: tuple[str, str]) -> list[JsonObject]:
    return [{"label": label, "kind": kind} for label, kind in pairs if normalize_space(label)]


def unique_texts(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = normalize_space(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def first_text(*values: Any) -> str:
    for value in values:
        text = normalize_space(value)
        if text:
            return text
    return ""


def object_id(value: Any) -> str:
    if isinstance(value, dict):
        return first_text(value.get("@id"), value.get("accession"), value.get("title"), value.get("name"))
    return first_text(value)


def object_ids(values: list[Any]) -> list[str]:
    return [text for text in (object_id(value) for value in values) if text]


def biosample_term_name(ontology: Any, biosample: JsonObject) -> str:
    if isinstance(ontology, dict):
        return first_text(ontology.get("term_name"), ontology.get("name"), ontology.get("title"), biosample.get("biosample_term_name"))
    return first_text(biosample.get("biosample_term_name"), biosample.get("biosample_ontology_term_name"), ontology_path_label(ontology))


def biosample_term_id(ontology: Any, biosample: JsonObject) -> str:
    if isinstance(ontology, dict):
        return first_text(ontology.get("term_id"), ontology.get("accession"), ontology.get("@id"))
    return first_text(biosample.get("biosample_term_id"), ontology)


def biosample_classification(ontology: Any) -> str:
    if isinstance(ontology, dict):
        return first_text(ontology.get("classification"), ontology.get("biosample_type"), ontology.get("category"))
    return ""


def organism_label(organism: Any) -> str:
    if isinstance(organism, dict):
        return first_text(organism.get("scientific_name"), organism.get("name"), organism.get("title"), organism.get("@id"))
    label = ontology_path_label(organism)
    return ORGANISM_LABELS.get(label, label)


def ontology_path_label(value: Any) -> str:
    text = first_text(value)
    if text.startswith("/") and text.endswith("/"):
        return text.strip("/").split("/")[-1].replace("_", " ")
    return text


def age_label(biosample: JsonObject) -> str:
    display = first_text(biosample.get("age_display"))
    if display:
        return display
    age = first_text(biosample.get("age"))
    units = first_text(biosample.get("age_units"))
    return f"{age} {units}".strip()


def int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def experiment_url(accession: str, base_url: str) -> str:
    return f"{base_url.rstrip('/')}/experiments/{accession}/"


def file_url(accession: str, base_url: str) -> str:
    return f"{base_url.rstrip('/')}/files/{accession}/"


def biosample_url(accession: str, base_url: str) -> str:
    return f"{base_url.rstrip('/')}/biosamples/{accession}/"


def encode_api_url(endpoint: str, base_url: str, params: JsonObject) -> str:
    endpoint = endpoint.lstrip("/")
    url = f"{base_url.rstrip('/')}/{endpoint}"
    if not params:
        return f"{url}?format=json"
    from urllib.parse import urlencode

    return f"{url}?{urlencode({'format': 'json', **params}, doseq=True)}"


def absolute_encode_url(path_or_url: str, base_url: str) -> str:
    if path_or_url.startswith(("http://", "https://")):
        return path_or_url
    return f"{base_url.rstrip('/')}/{path_or_url.lstrip('/')}"


def encode_path_url(path_or_url: str, base_url: str) -> str:
    text = first_text(path_or_url)
    if not text:
        return ""
    if text.startswith(("http://", "https://")):
        return text
    if text.startswith("/"):
        return f"{base_url.rstrip('/')}/{text.strip('/')}/"
    return ""


def dbxref_url(dbxref: str) -> str:
    if dbxref.startswith("GEO:"):
        accession = dbxref.split(":", 1)[1]
        return f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={accession}"
    return ""
