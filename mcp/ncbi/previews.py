"""Front-end preview hints for NCBI records."""

from __future__ import annotations

from .constants import JsonObject
from .utils import normalize_space


def with_ncbi_previews(record: JsonObject) -> JsonObject:
    """Attach shared display previews without changing the record contract."""
    display = record.get("display")
    if not isinstance(display, dict):
        return record
    previews = ncbi_record_previews(record)
    if previews:
        display["previews"] = previews
    return record


def ncbi_record_previews(record: JsonObject) -> list[JsonObject]:
    component = normalize_space(record.get("display", {}).get("component"))
    record_type = normalize_space(record.get("record_type"))
    previews: list[JsonObject] = []

    if component == "citation" or record_type == "pubmed_article":
        previews.append(citation_preview(record))
    elif component == "download_plan":
        previews.append(download_manifest_preview(record))
    elif component == "sample_sheet":
        previews.append(table_preview(record))
    elif component == "linkset":
        previews.append(linkset_preview(record))
    elif component == "runtime_status":
        previews.append(text_preview(record, title="Runtime status", provider="Local runtime"))
    elif component == "dataset":
        previews.extend(dataset_previews(record))
    elif component in {"gene", "taxonomy", "identifier_conversion", "database", "project", "sample", "run"}:
        previews.extend(entity_previews(record))

    return [preview for preview in previews if preview]


def citation_preview(record: JsonObject) -> JsonObject:
    citation = record.get("citation") if isinstance(record.get("citation"), dict) else {}
    pmid = normalize_space(citation.get("id") or record.get("id"))
    return {
        "kind": "citation_list",
        "title": "Citation",
        "provider": "NCBI PubMed",
        "id": pmid,
        "url": normalize_space(record.get("url")),
        "section_key": "citation",
        "actions": preview_actions(record),
        "data": {
            "pubmed_ids": [pmid] if pmid else [],
            "citations": [citation] if citation else [],
            "doi": normalize_space(citation.get("doi")),
            "pmcid": normalize_space(citation.get("pmcid")),
            "journal": normalize_space(citation.get("journal")),
            "authors": citation.get("authors", []) if isinstance(citation.get("authors"), list) else [],
        },
    }


def download_manifest_preview(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    related = record.get("related") if isinstance(record.get("related"), dict) else {}
    commands = data.get("commands") if isinstance(data.get("commands"), dict) else {}
    return {
        "kind": "download_manifest",
        "title": "Download manifest",
        "provider": provider_for_record(record),
        "id": normalize_space(record.get("id")),
        "url": normalize_space(record.get("url")),
        "section_key": "manifest",
        "actions": preview_actions(record),
        "data": {
            "source": normalize_space(record.get("database")),
            "accession": normalize_space(record.get("id")),
            "links": safe_links(record),
            "commands": commands,
            "sample_count": data.get("sample_count", ""),
            "samples": first_items(related.get("samples"), 20),
            "pubmed_ids": first_items(related.get("pubmed_ids"), 20),
            "bioproject": related.get("bioproject", ""),
            "biosample": related.get("biosample", {}),
        },
    }


def table_preview(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    rows = data.get("rows") if isinstance(data.get("rows"), list) else []
    columns = data.get("columns") if isinstance(data.get("columns"), list) else []
    return {
        "kind": "table",
        "title": "Sample table",
        "provider": provider_for_record(record),
        "id": normalize_space(record.get("id")),
        "url": normalize_space(record.get("url")),
        "section_key": "table",
        "actions": preview_actions(record),
        "data": {
            "columns": columns,
            "rows": rows[:25],
            "row_count": len(rows),
            "column_count": len(columns),
            "primary_key": normalize_space(data.get("primary_key")),
            "truncated": len(rows) > 25,
        },
    }


def linkset_preview(record: JsonObject) -> JsonObject:
    related = record.get("related") if isinstance(record.get("related"), dict) else {}
    target_groups = related.get("target_groups")
    if not isinstance(target_groups, list):
        target_groups = []
    return {
        "kind": "xref_groups",
        "title": "Linked NCBI records",
        "provider": "NCBI Entrez",
        "id": normalize_space(record.get("id")),
        "url": normalize_space(record.get("url")),
        "section_key": "links",
        "actions": preview_actions(record),
        "data": {
            "source": {
                "database": normalize_space(record.get("database")),
                "id": normalize_space(record.get("id")),
                "stable_id": normalize_space(record.get("stable_id")),
            },
            "groups": target_groups,
            "group_count": len(target_groups),
        },
    }


def dataset_previews(record: JsonObject) -> list[JsonObject]:
    previews = [xref_groups_preview(record, title="Related records", section_key="related")]
    related = record.get("related") if isinstance(record.get("related"), dict) else {}
    samples = related.get("samples")
    if isinstance(samples, list) and samples:
        previews.append(
            {
                "kind": "table",
                "title": "GEO samples",
                "provider": "NCBI GEO",
                "id": normalize_space(record.get("id")),
                "url": normalize_space(record.get("url")),
                "section_key": "samples",
                "actions": preview_actions(record),
                "data": {
                    "columns": [
                        {"key": "id", "label": "Accession"},
                        {"key": "title", "label": "Title"},
                        {"key": "url", "label": "URL"},
                    ],
                    "rows": samples[:25],
                    "row_count": len(samples),
                    "truncated": len(samples) > 25,
                },
            }
        )
    literature = related.get("literature")
    if isinstance(literature, list) and literature:
        previews.append(
            {
                "kind": "citation_list",
                "title": "Related literature",
                "provider": "NCBI PubMed",
                "id": normalize_space(literature[0].get("id")) if isinstance(literature[0], dict) else "",
                "url": normalize_space(literature[0].get("url")) if isinstance(literature[0], dict) else "",
                "section_key": "literature",
                "data": {
                    "pubmed_ids": [
                        normalize_space(item.get("id"))
                        for item in literature
                        if isinstance(item, dict) and normalize_space(item.get("id"))
                    ],
                    "references": literature,
                    "count": len(literature),
                },
            }
        )
    return previews


def entity_previews(record: JsonObject) -> list[JsonObject]:
    previews: list[JsonObject] = []
    xrefs = xref_groups_preview(record, title="Identifiers and related records", section_key="related")
    if xrefs:
        previews.append(xrefs)
    data_table = entity_table_preview(record)
    if data_table:
        previews.append(data_table)
    summary = text_preview(record, title="Summary", provider=provider_for_record(record))
    if summary:
        previews.append(summary)
    return previews


def xref_groups_preview(
    record: JsonObject,
    *,
    title: str,
    section_key: str,
) -> JsonObject:
    identifiers = record.get("identifiers") if isinstance(record.get("identifiers"), dict) else {}
    related = record.get("related") if isinstance(record.get("related"), dict) else {}
    groups = identifier_groups(identifiers) + related_groups(related)
    if not groups:
        return {}
    return {
        "kind": "xref_groups",
        "title": title,
        "provider": provider_for_record(record),
        "id": normalize_space(record.get("id")),
        "url": normalize_space(record.get("url")),
        "section_key": section_key,
        "actions": preview_actions(record),
        "data": {
            "groups": groups,
            "group_count": len(groups),
        },
    }


def entity_table_preview(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    component = normalize_space(record.get("display", {}).get("component"))
    if component == "sample":
        attributes = data.get("attributes") if isinstance(data.get("attributes"), list) else []
        if not attributes:
            return {}
        return rows_preview(
            record,
            title="Sample attributes",
            rows=attributes,
            columns=[
                {"key": "name", "label": "Name"},
                {"key": "value", "label": "Value"},
                {"key": "display_name", "label": "Display name"},
            ],
        )
    if component == "run":
        runs = data.get("runs") if isinstance(data.get("runs"), list) else []
        if not runs:
            return {}
        return rows_preview(
            record,
            title="SRA runs",
            rows=runs,
            columns=[
                {"key": "accession", "label": "Run"},
                {"key": "total_spots", "label": "Spots"},
                {"key": "total_bases", "label": "Bases"},
            ],
        )
    if component == "database":
        fields = data.get("fields") if isinstance(data.get("fields"), list) else []
        if not fields:
            return {}
        return rows_preview(
            record,
            title="Search fields",
            rows=fields,
            columns=[
                {"key": "name", "label": "Name"},
                {"key": "full_name", "label": "Full name"},
                {"key": "description", "label": "Description"},
            ],
        )
    return {}


def rows_preview(
    record: JsonObject,
    *,
    title: str,
    rows: list[object],
    columns: list[JsonObject],
) -> JsonObject:
    return {
        "kind": "table",
        "title": title,
        "provider": provider_for_record(record),
        "id": normalize_space(record.get("id")),
        "url": normalize_space(record.get("url")),
        "section_key": "table",
        "actions": preview_actions(record),
        "data": {
            "columns": columns,
            "rows": rows[:25],
            "row_count": len(rows),
            "column_count": len(columns),
            "truncated": len(rows) > 25,
        },
    }


def text_preview(record: JsonObject, *, title: str, provider: str) -> JsonObject:
    description = normalize_space(record.get("description"))
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    fallback = normalize_space(data.get("summary") or data.get("description") or data.get("version_error"))
    text = description or fallback
    if not text:
        return {}
    return {
        "kind": "text",
        "title": title,
        "provider": provider,
        "id": normalize_space(record.get("id")),
        "url": normalize_space(record.get("url")),
        "section_key": "overview",
        "actions": preview_actions(record),
        "data": {
            "text": text,
        },
    }


def identifier_groups(identifiers: JsonObject) -> list[JsonObject]:
    groups: list[JsonObject] = []
    for namespace, value in identifiers.items():
        items = value if isinstance(value, list) else [value]
        normalized_items = []
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = normalize_space(item.get("id"))
            label = normalize_space(item.get("label")) or item_id
            if not item_id and not label:
                continue
            normalized: JsonObject = {
                "id": item_id,
                "label": label,
            }
            url = normalize_space(item.get("url"))
            if url:
                normalized["url"] = url
            normalized_items.append(normalized)
        if normalized_items:
            groups.append(
                {
                    "database": normalize_space(namespace),
                    "count": len(normalized_items),
                    "ids": normalized_items,
                }
            )
    return groups


def related_groups(related: JsonObject) -> list[JsonObject]:
    groups: list[JsonObject] = []
    for key, value in related.items():
        items = value if isinstance(value, list) else [value]
        normalized_items = []
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = normalize_space(item.get("id"))
            label = normalize_space(item.get("label")) or item_id
            if not item_id and not label:
                continue
            normalized: JsonObject = {
                "id": item_id,
                "label": label,
            }
            url = normalize_space(item.get("url") or item.get("run_browser_url"))
            if url:
                normalized["url"] = url
            title = normalize_space(item.get("title"))
            if title:
                normalized["title"] = title
            normalized_items.append(normalized)
        if normalized_items:
            groups.append(
                {
                    "database": normalize_space(key),
                    "count": len(normalized_items),
                    "ids": normalized_items,
                }
            )
    return groups


def preview_actions(record: JsonObject) -> list[JsonObject]:
    return [
        {
            "label": normalize_space(action.get("label")),
            "url": normalize_space(action.get("url")),
            "kind": normalize_space(action.get("kind")) or "external",
            "primary": bool(action.get("primary")),
        }
        for action in safe_links(record, prefer_display=True)
        if normalize_space(action.get("label")) and normalize_space(action.get("url"))
    ]


def safe_links(record: JsonObject, *, prefer_display: bool = False) -> list[JsonObject]:
    if prefer_display:
        display = record.get("display") if isinstance(record.get("display"), dict) else {}
        actions = display.get("actions") if isinstance(display.get("actions"), list) else []
        if actions:
            return [action for action in actions if isinstance(action, dict)]
    links = record.get("links") if isinstance(record.get("links"), list) else []
    return [link for link in links if isinstance(link, dict)]


def first_items(value: object, limit: int) -> list[object]:
    if not isinstance(value, list):
        return []
    return value[:limit]


def provider_for_record(record: JsonObject) -> str:
    database = normalize_space(record.get("database")).lower()
    if database == "pubmed":
        return "NCBI PubMed"
    if database == "pmc":
        return "NCBI PMC"
    if database == "geo":
        return "NCBI GEO"
    if database == "sra":
        return "NCBI SRA"
    if database == "gene":
        return "NCBI Gene"
    if database == "taxonomy":
        return "NCBI Taxonomy"
    if database == "bioproject":
        return "NCBI BioProject"
    if database == "biosample":
        return "NCBI BioSample"
    if database == "local_runtime":
        return "Local runtime"
    if database:
        return f"NCBI {database}"
    return "NCBI"
