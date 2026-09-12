"""Front-end compatible record envelopes for MGnify JSON:API records."""

from __future__ import annotations

import urllib.parse
from typing import Any

from .constants import MGNIFY_API_BASE_URL, MGNIFY_WEBSITE_BASE_URL, RECORD_SCHEMA_VERSION, JsonObject
from .utils import normalize_space, safe_list


def mgnify_study_record(item: JsonObject, *, website_base_url: str = MGNIFY_WEBSITE_BASE_URL, api_base_url: str = MGNIFY_API_BASE_URL) -> JsonObject:
    study = normalize_study(item, website_base_url=website_base_url, api_base_url=api_base_url)
    links = study_links(study)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.project",
        "record_type": "mgnify_study",
        "database": "mgnify",
        "id": study["accession"],
        "stable_id": study["accession"],
        "label": study["accession"],
        "title": study["name"] or study["accession"],
        "description": study["abstract"] or "MGnify microbiome or metagenomics study",
        "url": study["url"],
        "icon": "mgnify",
        "identifiers": study_identifiers(study),
        "links": links,
        "display": {
            "component": "project",
            "chip_label": study["accession"],
            "icon": "mgnify",
            "title": study["name"] or study["accession"],
            "subtitle": study_subtitle(study),
            "description": study["abstract"] or "MGnify study record",
            "metadata": study_metadata(study),
            "badges": compact_badges(
                ("MGnify", "source"),
                (study["accession"], "identifier"),
                (study["data_origination"], "status"),
                (first_value(study["biomes"]), "context"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": study["name"] or study["accession"],
                "subtitle": study_subtitle(study),
                "icon": "mgnify",
                "fields": compact_fields(
                    ("Accession", study["accession"]),
                    ("BioProject", study["bioproject"]),
                    ("Secondary accession", study["secondary_accession"]),
                    ("Samples", str(study["samples_count"]) if study["samples_count"] else ""),
                    ("Biome", ", ".join(study["biomes"][:3])),
                    ("URL", study["url"]),
                ),
            },
            "primary_url": study["url"],
            "sections": study_sections(study),
            "previews": study_previews(study, links),
        },
        "related": {
            "biomes": study["biomes"],
            "relationship_links": study["relationship_links"],
        },
        "data": study,
    }


def mgnify_sample_record(item: JsonObject, *, website_base_url: str = MGNIFY_WEBSITE_BASE_URL, api_base_url: str = MGNIFY_API_BASE_URL) -> JsonObject:
    sample = normalize_sample(item, website_base_url=website_base_url, api_base_url=api_base_url)
    links = sample_links(sample)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.sample",
        "record_type": "mgnify_sample",
        "database": "mgnify",
        "id": sample["accession"],
        "stable_id": sample["accession"],
        "label": sample["accession"],
        "title": sample["sample_name"] or sample["accession"],
        "description": sample["description"] or "MGnify sample",
        "url": sample["url"],
        "icon": "sample",
        "identifiers": sample_identifiers(sample),
        "links": links,
        "display": {
            "component": "sample",
            "chip_label": sample["accession"],
            "icon": "sample",
            "title": sample["sample_name"] or sample["accession"],
            "subtitle": sample_subtitle(sample),
            "description": sample["description"] or "MGnify sample record",
            "metadata": sample_metadata(sample),
            "badges": compact_badges(
                ("MGnify", "source"),
                (sample["accession"], "identifier"),
                (sample["species"], "context"),
                (sample["biome"], "record_type"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": sample["sample_name"] or sample["accession"],
                "subtitle": sample_subtitle(sample),
                "icon": "sample",
                "fields": compact_fields(
                    ("Accession", sample["accession"]),
                    ("BioSample", sample["biosample"]),
                    ("Species", sample["species"]),
                    ("Host TaxID", str(sample["host_tax_id"]) if sample["host_tax_id"] else ""),
                    ("Biome", sample["biome"]),
                    ("URL", sample["url"]),
                ),
            },
            "primary_url": sample["url"],
            "sections": sample_sections(sample),
            "previews": sample_previews(sample, links),
        },
        "related": {
            "studies": sample["studies"],
            "metadata": sample["sample_metadata"],
            "relationship_links": sample["relationship_links"],
        },
        "data": sample,
    }


def mgnify_biome_record(item: JsonObject, *, website_base_url: str = MGNIFY_WEBSITE_BASE_URL, api_base_url: str = MGNIFY_API_BASE_URL) -> JsonObject:
    biome = normalize_biome(item, website_base_url=website_base_url, api_base_url=api_base_url)
    links = biome_links(biome)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.taxonomy",
        "record_type": "mgnify_biome",
        "database": "mgnify",
        "id": biome["lineage"],
        "stable_id": biome["lineage"],
        "label": biome["name"] or biome["lineage"],
        "title": biome["name"] or biome["lineage"],
        "description": f"MGnify biome lineage {biome['lineage']}",
        "url": biome["url"],
        "icon": "mgnify",
        "identifiers": {"mgnify_biome": {"namespace": "mgnify.biome", "id": biome["lineage"], "label": biome["name"], "url": biome["url"]}},
        "links": links,
        "display": {
            "component": "taxonomy",
            "chip_label": biome["name"] or biome["lineage"],
            "icon": "mgnify",
            "title": biome["name"] or biome["lineage"],
            "subtitle": f"MGnify biome | {biome['samples_count']} samples" if biome["samples_count"] else "MGnify biome",
            "description": f"MGnify biome lineage {biome['lineage']}",
            "metadata": biome_metadata(biome),
            "badges": compact_badges(("MGnify", "source"), (biome["name"], "identifier"), ("biome", "record_type")),
            "actions": display_actions(links),
            "hover": {
                "title": biome["name"] or biome["lineage"],
                "subtitle": "MGnify biome",
                "icon": "mgnify",
                "fields": compact_fields(
                    ("Name", biome["name"]),
                    ("Lineage", biome["lineage"]),
                    ("Samples", str(biome["samples_count"]) if biome["samples_count"] else ""),
                    ("URL", biome["url"]),
                ),
            },
            "primary_url": biome["url"],
            "sections": [{"key": "overview", "title": "Overview", "kind": "table", "rows": biome_metadata(biome)}],
            "previews": [
                {"kind": "table", "title": "Biome summary", "section_key": "overview", "data": {"columns": ["label", "value"], "rows": biome_metadata(biome)}},
                {"kind": "xref_groups", "title": "MGnify links", "actions": display_actions(links), "data": {"groups": biome_xref_groups(biome)}},
            ],
        },
        "related": {"relationship_links": biome["relationship_links"]},
        "data": biome,
    }


def normalize_study(item: JsonObject, *, website_base_url: str, api_base_url: str) -> JsonObject:
    attrs = attributes(item)
    accession = first_text(attrs.get("accession"), item.get("id")).upper()
    relationships = relationships_links(item)
    biomes = relationship_ids(item, "biomes")
    return {
        "accession": accession,
        "name": first_text(attrs.get("study-name")),
        "abstract": first_text(attrs.get("study-abstract")),
        "bioproject": first_text(attrs.get("bioproject")),
        "secondary_accession": first_text(attrs.get("secondary-accession")),
        "centre_name": first_text(attrs.get("centre-name")),
        "samples_count": int_or_zero(attrs.get("samples-count")),
        "is_private": bool(attrs.get("is-private")) if attrs.get("is-private") is not None else False,
        "last_update": first_text(attrs.get("last-update")),
        "public_release_date": first_text(attrs.get("public-release-date")),
        "data_origination": first_text(attrs.get("data-origination")),
        "biomes": biomes,
        "url": study_url(accession, website_base_url),
        "api_url": api_url_for(f"studies/{accession}", api_base_url),
        "relationship_links": relationships,
        "source_url": link_self(item),
    }


def normalize_sample(item: JsonObject, *, website_base_url: str, api_base_url: str) -> JsonObject:
    attrs = attributes(item)
    accession = first_text(attrs.get("accession"), item.get("id"))
    metadata = normalize_metadata(safe_list(attrs.get("sample-metadata")))
    studies = relationship_ids(item, "studies")
    biome = first_text(relationship_id(item, "biome"), attrs.get("environment-biome"))
    return {
        "accession": accession,
        "biosample": first_text(attrs.get("biosample")),
        "sample_name": first_text(attrs.get("sample-name")),
        "sample_alias": first_text(attrs.get("sample-alias")),
        "description": first_text(attrs.get("sample-desc")),
        "species": first_text(attrs.get("species")),
        "host_tax_id": int_or_zero(attrs.get("host-tax-id")),
        "collection_date": first_text(attrs.get("collection-date")),
        "geo_location": first_text(attrs.get("geo-loc-name")),
        "latitude": attrs.get("latitude"),
        "longitude": attrs.get("longitude"),
        "environment_biome": first_text(attrs.get("environment-biome")),
        "environment_feature": first_text(attrs.get("environment-feature")),
        "environment_material": first_text(attrs.get("environment-material")),
        "analysis_completed": first_text(attrs.get("analysis-completed")),
        "last_update": first_text(attrs.get("last-update")),
        "sample_metadata": metadata,
        "studies": studies,
        "biome": biome,
        "url": sample_url(accession, website_base_url),
        "api_url": api_url_for(f"samples/{urllib.parse.quote(accession, safe='')}", api_base_url),
        "relationship_links": relationships_links(item),
        "source_url": link_self(item),
    }


def normalize_biome(item: JsonObject, *, website_base_url: str, api_base_url: str) -> JsonObject:
    attrs = attributes(item)
    lineage = first_text(attrs.get("lineage"), item.get("id"))
    return {
        "lineage": lineage,
        "name": first_text(attrs.get("biome-name")),
        "samples_count": int_or_zero(attrs.get("samples-count")),
        "url": biome_url(lineage, website_base_url),
        "api_url": api_url_for(f"biomes/{urllib.parse.quote(lineage, safe='')}", api_base_url),
        "relationship_links": relationships_links(item),
        "source_url": link_self(item),
    }


def study_sections(study: JsonObject) -> list[JsonObject]:
    return [
        {"key": "overview", "title": "Overview", "kind": "table", "rows": study_metadata(study)},
        {"key": "relationships", "title": "Relationship links", "kind": "table", "rows": link_rows(study["relationship_links"])},
    ]


def study_previews(study: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    return [
        {"kind": "table", "title": "Study summary", "section_key": "overview", "data": {"columns": ["label", "value"], "rows": study_metadata(study)}},
        {"kind": "xref_groups", "title": "Identifiers and MGnify links", "actions": display_actions(links), "data": {"groups": study_xref_groups(study)}},
    ]


def sample_sections(sample: JsonObject) -> list[JsonObject]:
    sections = [{"key": "overview", "title": "Overview", "kind": "table", "rows": sample_metadata(sample)}]
    if sample["sample_metadata"]:
        sections.append({"key": "sample_metadata", "title": "Sample metadata", "kind": "table", "rows": sample["sample_metadata"]})
    sections.append({"key": "relationships", "title": "Relationship links", "kind": "table", "rows": link_rows(sample["relationship_links"])})
    return sections


def sample_previews(sample: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews: list[JsonObject] = [
        {"kind": "table", "title": "Sample summary", "section_key": "overview", "data": {"columns": ["label", "value"], "rows": sample_metadata(sample)}}
    ]
    if sample["sample_metadata"]:
        previews.append({"kind": "table", "title": "Sample metadata", "section_key": "sample_metadata", "data": {"columns": ["key", "value", "unit"], "rows": sample["sample_metadata"]}})
    previews.append({"kind": "xref_groups", "title": "Identifiers and MGnify links", "actions": display_actions(links), "data": {"groups": sample_xref_groups(sample)}})
    return previews


def study_links(study: JsonObject) -> list[JsonObject]:
    links = [{"label": "Open MGnify study", "url": study["url"], "kind": "external", "primary": True}]
    if study["api_url"]:
        links.append({"label": "Open MGnify study API", "url": study["api_url"], "kind": "external"})
    if study["bioproject"]:
        links.append({"label": f"Open BioProject {study['bioproject']}", "url": f"https://www.ncbi.nlm.nih.gov/bioproject/{urllib.parse.quote(study['bioproject'], safe='')}", "kind": "external"})
    links.extend(relationship_actions(study["relationship_links"]))
    return links


def sample_links(sample: JsonObject) -> list[JsonObject]:
    links = [{"label": "Open MGnify sample", "url": sample["url"], "kind": "external", "primary": True}]
    if sample["api_url"]:
        links.append({"label": "Open MGnify sample API", "url": sample["api_url"], "kind": "external"})
    if sample["biosample"]:
        links.append({"label": f"Open BioSample {sample['biosample']}", "url": f"https://www.ncbi.nlm.nih.gov/biosample/{urllib.parse.quote(sample['biosample'], safe='')}", "kind": "external"})
    links.extend(relationship_actions(sample["relationship_links"]))
    return links


def biome_links(biome: JsonObject) -> list[JsonObject]:
    links = [{"label": "Open MGnify biome", "url": biome["url"], "kind": "external", "primary": True}]
    if biome["api_url"]:
        links.append({"label": "Open MGnify biome API", "url": biome["api_url"], "kind": "external"})
    links.extend(relationship_actions(biome["relationship_links"]))
    return links


def study_identifiers(study: JsonObject) -> JsonObject:
    identifiers: JsonObject = {"mgnify": {"namespace": "mgnify.study", "id": study["accession"], "label": study["accession"], "url": study["url"]}}
    if study["bioproject"]:
        identifiers["bioproject"] = {"namespace": "ncbi.bioproject", "id": study["bioproject"], "label": study["bioproject"], "url": f"https://www.ncbi.nlm.nih.gov/bioproject/{study['bioproject']}"}
    if study["secondary_accession"]:
        identifiers["secondary"] = {"namespace": "ena.study", "id": study["secondary_accession"], "label": study["secondary_accession"], "url": study["url"]}
    return identifiers


def sample_identifiers(sample: JsonObject) -> JsonObject:
    identifiers: JsonObject = {"mgnify": {"namespace": "mgnify.sample", "id": sample["accession"], "label": sample["accession"], "url": sample["url"]}}
    if sample["biosample"]:
        identifiers["biosample"] = {"namespace": "ncbi.biosample", "id": sample["biosample"], "label": sample["biosample"], "url": f"https://www.ncbi.nlm.nih.gov/biosample/{sample['biosample']}"}
    return identifiers


def study_metadata(study: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Accession", study["accession"]),
        ("BioProject", study["bioproject"]),
        ("Secondary accession", study["secondary_accession"]),
        ("Samples", str(study["samples_count"]) if study["samples_count"] else ""),
        ("Centre", study["centre_name"]),
        ("Data origination", study["data_origination"]),
        ("Public release", study["public_release_date"]),
        ("Last update", study["last_update"]),
        ("Biome", ", ".join(study["biomes"][:5])),
        ("API", study["api_url"]),
    )


def sample_metadata(sample: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Accession", sample["accession"]),
        ("BioSample", sample["biosample"]),
        ("Sample name", sample["sample_name"]),
        ("Alias", sample["sample_alias"]),
        ("Species", sample["species"]),
        ("Host TaxID", str(sample["host_tax_id"]) if sample["host_tax_id"] else ""),
        ("Biome", sample["biome"]),
        ("Collection date", sample["collection_date"]),
        ("Geo location", sample["geo_location"]),
        ("Studies", ", ".join(sample["studies"][:5])),
        ("Last update", sample["last_update"]),
        ("API", sample["api_url"]),
    )


def biome_metadata(biome: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Name", biome["name"]),
        ("Lineage", biome["lineage"]),
        ("Samples", str(biome["samples_count"]) if biome["samples_count"] else ""),
        ("API", biome["api_url"]),
    )


def study_xref_groups(study: JsonObject) -> list[JsonObject]:
    groups = [{"source": "MGnify", "items": [{"label": study["accession"], "id": study["accession"], "url": study["url"]}]}]
    if study["bioproject"]:
        groups.append({"source": "BioProject", "items": [{"label": study["bioproject"], "id": study["bioproject"], "url": f"https://www.ncbi.nlm.nih.gov/bioproject/{study['bioproject']}"}]})
    if study["biomes"]:
        groups.append({"source": "Biomes", "items": [{"label": item, "id": item, "url": biome_url(item, MGNIFY_WEBSITE_BASE_URL)} for item in study["biomes"]]})
    if study["relationship_links"]:
        groups.append({"source": "MGnify relationships", "items": [{"label": key, "id": key, "url": url} for key, url in study["relationship_links"].items()]})
    return groups


def sample_xref_groups(sample: JsonObject) -> list[JsonObject]:
    groups = [{"source": "MGnify", "items": [{"label": sample["accession"], "id": sample["accession"], "url": sample["url"]}]}]
    if sample["biosample"]:
        groups.append({"source": "BioSample", "items": [{"label": sample["biosample"], "id": sample["biosample"], "url": f"https://www.ncbi.nlm.nih.gov/biosample/{sample['biosample']}"}]})
    if sample["studies"]:
        groups.append({"source": "Studies", "items": [{"label": item, "id": item, "url": study_url(item, MGNIFY_WEBSITE_BASE_URL)} for item in sample["studies"]]})
    if sample["biome"]:
        groups.append({"source": "Biome", "items": [{"label": sample["biome"], "id": sample["biome"], "url": biome_url(sample["biome"], MGNIFY_WEBSITE_BASE_URL)}]})
    return groups


def biome_xref_groups(biome: JsonObject) -> list[JsonObject]:
    groups = [{"source": "MGnify biome", "items": [{"label": biome["lineage"], "id": biome["lineage"], "url": biome["url"]}]}]
    if biome["relationship_links"]:
        groups.append({"source": "MGnify relationships", "items": [{"label": key, "id": key, "url": url} for key, url in biome["relationship_links"].items()]})
    return groups


def study_subtitle(study: JsonObject) -> str:
    parts = ["MGnify"]
    for value in [study["data_origination"], first_value(study["biomes"]), str(study["samples_count"]) + " samples" if study["samples_count"] else ""]:
        if value:
            parts.append(value)
    return " | ".join(parts)


def sample_subtitle(sample: JsonObject) -> str:
    parts = ["MGnify sample"]
    for value in [sample["species"], sample["biome"], first_value(sample["studies"])]:
        if value:
            parts.append(value)
    return " | ".join(parts)


def normalize_metadata(items: list[Any]) -> list[JsonObject]:
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        key = normalize_space(item.get("key"))
        value = normalize_space(item.get("value"))
        unit = normalize_space(item.get("unit"))
        if key or value:
            rows.append({"key": key, "value": value, "unit": unit})
    return rows


def relationships_links(item: JsonObject) -> dict[str, str]:
    rels = item.get("relationships") if isinstance(item.get("relationships"), dict) else {}
    out: dict[str, str] = {}
    for key, value in rels.items():
        if not isinstance(value, dict):
            continue
        links = value.get("links") if isinstance(value.get("links"), dict) else {}
        related = normalize_space(links.get("related"))
        if related.startswith(("http://", "https://")):
            out[key] = related
    return out


def relationship_actions(links: dict[str, str]) -> list[JsonObject]:
    return [{"label": f"Open {label}", "url": url, "kind": "external"} for label, url in links.items() if url.startswith(("http://", "https://"))]


def relationship_id(item: JsonObject, name: str) -> str:
    rels = item.get("relationships") if isinstance(item.get("relationships"), dict) else {}
    rel = rels.get(name) if isinstance(rels.get(name), dict) else {}
    data = rel.get("data")
    if isinstance(data, dict):
        return normalize_space(data.get("id"))
    return ""


def relationship_ids(item: JsonObject, name: str) -> list[str]:
    rels = item.get("relationships") if isinstance(item.get("relationships"), dict) else {}
    rel = rels.get(name) if isinstance(rels.get(name), dict) else {}
    data = rel.get("data")
    if isinstance(data, list):
        return unique_texts([entry.get("id") for entry in data if isinstance(entry, dict)])
    if isinstance(data, dict):
        return unique_texts([data.get("id")])
    return []


def link_self(item: JsonObject) -> str:
    links = item.get("links") if isinstance(item.get("links"), dict) else {}
    return normalize_space(links.get("self"))


def attributes(item: JsonObject) -> JsonObject:
    return item.get("attributes") if isinstance(item.get("attributes"), dict) else {}


def link_rows(links: dict[str, str]) -> list[JsonObject]:
    return [{"label": key, "value": url} for key, url in links.items()]


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


def study_url(accession: str, website_base_url: str) -> str:
    return f"{website_base_url.rstrip('/')}/studies/{urllib.parse.quote(accession, safe='')}"


def sample_url(accession: str, website_base_url: str) -> str:
    return f"{website_base_url.rstrip('/')}/samples/{urllib.parse.quote(accession, safe='')}"


def biome_url(lineage: str, website_base_url: str) -> str:
    return f"{website_base_url.rstrip('/')}/api/v1/biomes/{urllib.parse.quote(lineage, safe='')}"


def api_url_for(endpoint: str, api_base_url: str) -> str:
    return f"{api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"


def int_or_zero(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


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
