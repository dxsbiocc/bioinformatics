"""Front-end compatible record envelopes for CELLxGENE Discover."""

from __future__ import annotations

import urllib.parse
from typing import Any

from .constants import CELLXGENE_API_BASE_URL, CELLXGENE_WEBSITE_BASE_URL, RECORD_SCHEMA_VERSION, JsonObject
from .utils import normalize_space, safe_list


def cellxgene_collection_record(
    collection: JsonObject,
    *,
    max_datasets: int,
    website_base_url: str = CELLXGENE_WEBSITE_BASE_URL,
    api_base_url: str = CELLXGENE_API_BASE_URL,
) -> JsonObject:
    normalized = normalize_collection(
        collection,
        max_datasets=max_datasets,
        website_base_url=website_base_url,
        api_base_url=api_base_url,
    )
    collection_id = normalized["collection_id"]
    title = normalized["name"] or collection_id
    links = collection_links(normalized)
    description = normalized["description"] or "CELLxGENE Discover public single-cell collection"
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.project",
        "record_type": "cellxgene_collection",
        "database": "cellxgene",
        "id": collection_id,
        "stable_id": collection_id,
        "label": title,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "cellxgene",
        "identifiers": collection_identifiers(normalized),
        "links": links,
        "display": {
            "component": "project",
            "chip_label": "CELLxGENE",
            "icon": "cellxgene",
            "title": title,
            "subtitle": collection_subtitle(normalized),
            "description": description,
            "metadata": collection_metadata(normalized),
            "badges": compact_badges(
                ("CELLxGENE", "source"),
                (str(normalized["dataset_count"]) + " datasets", "record_type"),
                (first_value(normalized["organisms"]), "context"),
                (normalized["visibility"], "status"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": collection_subtitle(normalized),
                "icon": "cellxgene",
                "fields": compact_fields(
                    ("Collection ID", collection_id),
                    ("DOI", normalized["doi"]),
                    ("Organisms", ", ".join(normalized["organisms"][:3])),
                    ("Tissues", ", ".join(normalized["tissues"][:3])),
                    ("Diseases", ", ".join(normalized["diseases"][:3])),
                    ("Cell count", str(normalized["cell_count"]) if normalized["cell_count"] else ""),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": collection_sections(normalized),
            "previews": collection_previews(normalized, links),
        },
        "related": {
            "datasets": normalized["datasets"],
            "authors": normalized["authors"],
            "links": normalized["external_links"],
            "assets": normalized["assets"],
        },
        "data": normalized,
    }


def cellxgene_assets_download_plan_record(
    collection: JsonObject,
    *,
    max_datasets: int,
    website_base_url: str = CELLXGENE_WEBSITE_BASE_URL,
    api_base_url: str = CELLXGENE_API_BASE_URL,
) -> JsonObject:
    normalized = normalize_collection(
        collection,
        max_datasets=max_datasets,
        website_base_url=website_base_url,
        api_base_url=api_base_url,
    )
    collection_id = normalized["collection_id"]
    links = [
        {"label": "Open CELLxGENE collection", "url": normalized["url"], "kind": "external", "primary": True},
        {"label": "Open CELLxGENE API", "url": normalized["api_url"], "kind": "external"},
    ]
    first_url = first_asset_url(normalized["assets"])
    if first_url:
        links.append({"label": "Open first asset", "url": first_url, "kind": "download"})
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.download_plan",
        "record_type": "cellxgene_asset_manifest",
        "database": "cellxgene",
        "id": f"{collection_id}:assets",
        "stable_id": f"{collection_id}:assets",
        "label": f"{collection_id} assets",
        "title": f"{normalized['name'] or collection_id} CELLxGENE asset manifest",
        "description": f"{len(normalized['assets'])} metadata-only asset rows. No download has been started.",
        "url": normalized["url"],
        "icon": "download",
        "identifiers": {
            "cellxgene_collection": {"namespace": "cellxgene.collection", "id": collection_id, "label": collection_id, "url": normalized["url"]}
        },
        "links": links,
        "display": {
            "component": "download_plan",
            "chip_label": "CELLxGENE assets",
            "icon": "download",
            "title": f"{normalized['name'] or collection_id} assets",
            "subtitle": f"CELLxGENE | {len(normalized['assets'])} asset rows",
            "description": "Metadata-only CELLxGENE asset manifest. Review links before downloading H5AD data.",
            "metadata": compact_fields(
                ("Collection ID", collection_id),
                ("Datasets", str(normalized["dataset_count"])),
                ("Assets", str(len(normalized["assets"]))),
                ("Cell count", str(normalized["cell_count"]) if normalized["cell_count"] else ""),
                ("API", normalized["api_url"]),
            ),
            "badges": compact_badges(("CELLxGENE", "source"), ("download plan", "record_type"), (collection_id, "identifier")),
            "actions": display_actions(links),
            "hover": {
                "title": f"{normalized['name'] or collection_id} assets",
                "subtitle": f"{len(normalized['assets'])} asset rows",
                "icon": "download",
                "fields": compact_fields(
                    ("Collection ID", collection_id),
                    ("Assets", str(len(normalized["assets"]))),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": [{"key": "assets", "title": "Assets", "kind": "table", "rows": normalized["assets"]}],
            "previews": [
                {
                    "kind": "download_manifest",
                    "title": "CELLxGENE asset manifest",
                    "section_key": "assets",
                    "actions": display_actions(links),
                    "data": {"rows": normalized["assets"]},
                },
                {
                    "kind": "table",
                    "title": "Assets",
                    "section_key": "assets",
                    "data": {
                        "columns": ["dataset_id", "dataset_title", "filetype", "filesize_label", "url"],
                        "rows": normalized["assets"],
                    },
                },
            ],
        },
        "related": {"datasets": normalized["datasets"], "assets": normalized["assets"]},
        "data": {
            "collection_id": collection_id,
            "collection_name": normalized["name"],
            "assets": normalized["assets"],
            "datasets": normalized["datasets"],
            "url": normalized["url"],
            "api_url": normalized["api_url"],
        },
    }


def normalize_collection(
    collection: JsonObject,
    *,
    max_datasets: int,
    website_base_url: str,
    api_base_url: str,
) -> JsonObject:
    collection_id = normalize_space(collection.get("collection_id")).lower()
    datasets = [normalize_dataset(item) for item in safe_list(collection.get("datasets")) if isinstance(item, dict)]
    datasets = datasets[:max_datasets]
    assets = collection_assets(datasets)
    publisher = collection.get("publisher_metadata") if isinstance(collection.get("publisher_metadata"), dict) else {}
    doi = normalize_space(collection.get("doi"))
    return {
        "collection_id": collection_id,
        "collection_version_id": normalize_space(collection.get("collection_version_id")),
        "name": normalize_space(collection.get("name")),
        "description": normalize_space(collection.get("description")),
        "doi": doi,
        "doi_url": f"https://doi.org/{urllib.parse.quote(doi, safe='/')}" if doi else "",
        "visibility": normalize_space(collection.get("visibility")),
        "consortia": unique_texts(safe_list(collection.get("consortia"))),
        "contact_name": normalize_space(collection.get("contact_name")),
        "contact_email": normalize_space(collection.get("contact_email")),
        "curator_name": normalize_space(collection.get("curator_name")),
        "created_at": normalize_space(collection.get("created_at")),
        "published_at": normalize_space(collection.get("published_at")),
        "revised_at": normalize_space(collection.get("revised_at")),
        "publisher": {
            "journal": normalize_space(publisher.get("journal")),
            "published_year": normalize_space(publisher.get("published_year")),
            "is_preprint": bool(publisher.get("is_preprint")) if isinstance(publisher.get("is_preprint"), bool) else None,
        },
        "authors": normalize_authors(safe_list(publisher.get("authors"))),
        "external_links": normalize_external_links(safe_list(collection.get("links"))),
        "datasets": datasets,
        "dataset_count": len(safe_list(collection.get("datasets"))),
        "returned_dataset_count": len(datasets),
        "assets": assets,
        "cell_count": sum(item["cell_count"] for item in datasets),
        "organisms": unique_values_from_datasets(datasets, "organism"),
        "tissues": unique_values_from_datasets(datasets, "tissue"),
        "diseases": unique_values_from_datasets(datasets, "disease"),
        "assays": unique_values_from_datasets(datasets, "assay"),
        "cell_types": unique_values_from_datasets(datasets, "cell_type"),
        "url": collection_url(collection, collection_id, website_base_url),
        "api_url": api_url_for(f"collections/{collection_id}", api_base_url, {}),
    }


def normalize_dataset(dataset: JsonObject) -> JsonObject:
    assets = normalize_assets(safe_list(dataset.get("assets")))
    dataset_id = normalize_space(dataset.get("dataset_id")).lower()
    return {
        "dataset_id": dataset_id,
        "dataset_version_id": normalize_space(dataset.get("dataset_version_id")),
        "title": normalize_space(dataset.get("title")),
        "cell_count": int_or_zero(dataset.get("cell_count")),
        "primary_cell_count": int_or_zero(dataset.get("primary_cell_count")),
        "feature_count": int_or_zero(dataset.get("feature_count")),
        "schema_version": normalize_space(dataset.get("schema_version")),
        "explorer_url": safe_http_url(dataset.get("explorer_url")),
        "assay": normalize_terms(safe_list(dataset.get("assay"))),
        "cell_type": normalize_terms(safe_list(dataset.get("cell_type"))),
        "development_stage": normalize_terms(safe_list(dataset.get("development_stage"))),
        "disease": normalize_terms(safe_list(dataset.get("disease"))),
        "organism": normalize_terms(safe_list(dataset.get("organism"))),
        "sex": normalize_terms(safe_list(dataset.get("sex"))),
        "tissue": normalize_terms(safe_list(dataset.get("tissue"))),
        "suspension_type": unique_texts(safe_list(dataset.get("suspension_type"))),
        "embeddings": unique_texts(safe_list(dataset.get("embeddings"))),
        "default_embedding": normalize_space(dataset.get("default_embedding")),
        "is_primary_data": safe_list(dataset.get("is_primary_data")),
        "assets": assets,
        "citation": normalize_space(dataset.get("citation")),
    }


def normalize_assets(assets: list[Any]) -> list[JsonObject]:
    normalized = []
    for item in assets:
        if not isinstance(item, dict):
            continue
        size = int_or_zero(item.get("filesize"))
        url = safe_http_url(item.get("url"))
        if not url:
            continue
        normalized.append(
            {
                "filetype": normalize_space(item.get("filetype")),
                "filesize": size,
                "filesize_label": human_size(size),
                "url": url,
            }
        )
    return normalized


def collection_assets(datasets: list[JsonObject]) -> list[JsonObject]:
    rows = []
    for dataset in datasets:
        for asset in dataset["assets"]:
            rows.append(
                {
                    "dataset_id": dataset["dataset_id"],
                    "dataset_title": dataset["title"],
                    "filetype": asset["filetype"],
                    "filesize": asset["filesize"],
                    "filesize_label": asset["filesize_label"],
                    "url": asset["url"],
                    "explorer_url": dataset["explorer_url"],
                }
            )
    return rows


def normalize_terms(values: list[Any]) -> list[JsonObject]:
    terms = []
    for item in values:
        if not isinstance(item, dict):
            continue
        label = normalize_space(item.get("label"))
        term_id = normalize_space(item.get("ontology_term_id"))
        if label or term_id:
            terms.append({"label": label, "ontology_term_id": term_id, "tissue_type": normalize_space(item.get("tissue_type"))})
    return terms


def normalize_authors(authors: list[Any]) -> list[JsonObject]:
    normalized = []
    for item in authors:
        if not isinstance(item, dict):
            continue
        name = normalize_space(item.get("name"))
        if not name:
            given = normalize_space(item.get("given"))
            family = normalize_space(item.get("family"))
            name = " ".join(part for part in [given, family] if part)
        if name:
            normalized.append({"name": name})
    return normalized[:50]


def normalize_external_links(links: list[Any]) -> list[JsonObject]:
    normalized = []
    for item in links:
        if not isinstance(item, dict):
            continue
        url = safe_http_url(item.get("link_url"))
        if not url:
            continue
        label = normalize_space(item.get("link_name")) or normalize_space(item.get("link_type")) or url
        normalized.append(
            {
                "label": label,
                "type": normalize_space(item.get("link_type")),
                "url": url,
            }
        )
    return normalized[:50]


def collection_links(collection: JsonObject) -> list[JsonObject]:
    links = [
        {"label": "Open CELLxGENE collection", "url": collection["url"], "kind": "external", "primary": True},
        {"label": "Open CELLxGENE API", "url": collection["api_url"], "kind": "external"},
    ]
    if collection["doi_url"]:
        links.append({"label": "Open DOI", "url": collection["doi_url"], "kind": "external"})
    for dataset in collection["datasets"][:5]:
        if dataset["explorer_url"]:
            links.append({"label": f"Explore dataset {dataset['dataset_id'][:8]}", "url": dataset["explorer_url"], "kind": "external"})
    for link in collection["external_links"][:5]:
        links.append({"label": link["label"], "url": link["url"], "kind": "external"})
    first_url = first_asset_url(collection["assets"])
    if first_url:
        links.append({"label": "Open first H5AD asset", "url": first_url, "kind": "download"})
    return links


def collection_identifiers(collection: JsonObject) -> JsonObject:
    identifiers: JsonObject = {
        "cellxgene_collection": {
            "namespace": "cellxgene.collection",
            "id": collection["collection_id"],
            "label": collection["collection_id"],
            "url": collection["url"],
        }
    }
    if collection["doi"]:
        identifiers["doi"] = {"namespace": "doi", "id": collection["doi"], "label": collection["doi"], "url": collection["doi_url"]}
    return identifiers


def collection_sections(collection: JsonObject) -> list[JsonObject]:
    sections = [
        {"key": "overview", "title": "Overview", "kind": "table", "rows": collection_metadata(collection)}
    ]
    if collection["datasets"]:
        sections.append({"key": "datasets", "title": "Datasets", "kind": "table", "rows": collection["datasets"]})
    if collection["assets"]:
        sections.append({"key": "assets", "title": "Assets", "kind": "table", "rows": collection["assets"]})
    if collection["authors"]:
        sections.append({"key": "authors", "title": "Authors", "kind": "list", "items": collection["authors"]})
    if collection["external_links"]:
        sections.append({"key": "links", "title": "External links", "kind": "list", "items": collection["external_links"]})
    return sections


def collection_previews(collection: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews: list[JsonObject] = [
        {
            "kind": "table",
            "title": "Collection overview",
            "section_key": "overview",
            "data": {"columns": ["label", "value"], "rows": collection_metadata(collection)},
        }
    ]
    if collection["datasets"]:
        previews.append(
            {
                "kind": "table",
                "title": "Datasets",
                "section_key": "datasets",
                "data": {
                    "columns": ["dataset_id", "title", "cell_count", "organism", "tissue", "disease", "assay", "explorer_url"],
                    "rows": collection["datasets"],
                },
            }
        )
    if collection["assets"]:
        previews.append(
            {
                "kind": "download_manifest",
                "title": "H5AD assets",
                "section_key": "assets",
                "actions": display_actions(links),
                "data": {"rows": collection["assets"]},
            }
        )
    if collection["doi"] or collection["authors"]:
        previews.append(
            {
                "kind": "citation_list",
                "title": "Publication",
                "data": {
                    "items": [
                        {
                            "doi": collection["doi"],
                            "doi_url": collection["doi_url"],
                            "journal": collection["publisher"]["journal"],
                            "year": collection["publisher"]["published_year"],
                            "authors": ", ".join(item["name"] for item in collection["authors"][:10]),
                        }
                    ]
                },
            }
        )
    xrefs = xref_groups(collection)
    if xrefs:
        previews.append({"kind": "xref_groups", "title": "Ontology and external links", "data": {"groups": xrefs}})
    return previews


def xref_groups(collection: JsonObject) -> list[JsonObject]:
    groups = []
    for label, key in [("Organisms", "organism"), ("Tissues", "tissue"), ("Diseases", "disease"), ("Assays", "assay"), ("Cell types", "cell_type")]:
        items = []
        for dataset in collection["datasets"]:
            for term in dataset.get(key, []):
                if term.get("label") or term.get("ontology_term_id"):
                    items.append({"label": term.get("label", ""), "id": term.get("ontology_term_id", ""), "url": ontology_url(term.get("ontology_term_id", ""))})
        unique = unique_dicts(items, ("label", "id"))
        if unique:
            groups.append({"source": label, "items": unique[:50]})
    if collection["external_links"]:
        groups.append({"source": "External links", "items": collection["external_links"]})
    return groups


def collection_metadata(collection: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Collection ID", collection["collection_id"]),
        ("Version ID", collection["collection_version_id"]),
        ("DOI", collection["doi"]),
        ("Journal", collection["publisher"]["journal"]),
        ("Published", collection["published_at"]),
        ("Revised", collection["revised_at"]),
        ("Datasets", str(collection["dataset_count"])),
        ("Returned datasets", str(collection["returned_dataset_count"])),
        ("Cell count", str(collection["cell_count"]) if collection["cell_count"] else ""),
        ("Organisms", ", ".join(collection["organisms"][:5])),
        ("Tissues", ", ".join(collection["tissues"][:5])),
        ("Diseases", ", ".join(collection["diseases"][:5])),
        ("Assays", ", ".join(collection["assays"][:5])),
        ("Contact", collection["contact_name"]),
        ("Consortia", ", ".join(collection["consortia"][:5])),
        ("API", collection["api_url"]),
    )


def collection_subtitle(collection: JsonObject) -> str:
    parts = ["CELLxGENE"]
    if collection["dataset_count"]:
        parts.append(f"{collection['dataset_count']} datasets")
    if collection["cell_count"]:
        parts.append(f"{collection['cell_count']} cells")
    if collection["organisms"]:
        parts.append(", ".join(collection["organisms"][:2]))
    return " | ".join(parts)


def unique_values_from_datasets(datasets: list[JsonObject], key: str) -> list[str]:
    values = []
    for dataset in datasets:
        for term in dataset.get(key, []):
            if isinstance(term, dict):
                values.append(term.get("label"))
    return unique_texts(values)


def collection_url(collection: JsonObject, collection_id: str, website_base_url: str) -> str:
    direct = safe_http_url(collection.get("collection_url"))
    if direct:
        return direct
    return f"{website_base_url.rstrip('/')}/collections/{urllib.parse.quote(collection_id, safe='')}"


def api_url_for(endpoint: str, api_base_url: str, params: JsonObject) -> str:
    url = f"{api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    if not params:
        return url
    return f"{url}?{urllib.parse.urlencode(params, doseq=True)}"


def ontology_url(term_id: str) -> str:
    term_id = normalize_space(term_id)
    if not term_id or term_id == "unknown":
        return ""
    if ":" in term_id:
        prefix, local_id = term_id.split(":", 1)
        return f"https://www.ebi.ac.uk/ols4/ontologies/{urllib.parse.quote(prefix.lower(), safe='')}/terms?iri={urllib.parse.quote(term_id, safe='')}"
    return ""


def first_asset_url(assets: list[JsonObject]) -> str:
    for item in assets:
        url = safe_http_url(item.get("url"))
        if url:
            return url
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


def unique_dicts(values: list[JsonObject], keys: tuple[str, ...]) -> list[JsonObject]:
    seen = set()
    out = []
    for value in values:
        key = tuple(normalize_space(value.get(item)) for item in keys)
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


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
