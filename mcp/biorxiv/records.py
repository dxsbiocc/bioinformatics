"""Front-end compatible record envelopes for bioRxiv/medRxiv results."""

from __future__ import annotations

import urllib.parse

from .constants import BIORXIV_WEBSITE_BASE_URL, MEDRXIV_WEBSITE_BASE_URL, RECORD_SCHEMA_VERSION, JsonObject
from .utils import normalize_space, split_authors


def preprint_record(row: JsonObject, *, server: str) -> JsonObject:
    normalized = normalize_preprint(row, server=server)
    links = preprint_links(normalized)
    title = normalized["title"] or normalized["doi"]
    description = normalized["abstract"]
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "literature.preprint",
        "record_type": f"{normalized['server']}_preprint",
        "database": normalized["server"],
        "id": normalized["doi"],
        "stable_id": f"{server_label(normalized['server'])}:{normalized['doi']}",
        "label": normalized["doi"],
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": normalized["server"],
        "identifiers": preprint_identifiers(normalized),
        "links": links,
        "display": {
            "component": "citation",
            "chip_label": server_label(normalized["server"]),
            "icon": normalized["server"],
            "title": title,
            "subtitle": citation_subtitle(normalized),
            "description": description,
            "metadata": preprint_metadata(normalized),
            "badges": compact_badges(
                (server_label(normalized["server"]), "source"),
                (normalized["doi"], "identifier"),
                (normalized["category"], "category"),
                (f"v{normalized['version']}" if normalized["version"] else "", "version"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": citation_subtitle(normalized),
                "icon": normalized["server"],
                "fields": compact_fields(
                    ("DOI", normalized["doi"]),
                    ("Server", server_label(normalized["server"])),
                    ("Date", normalized["date"]),
                    ("Version", normalized["version"]),
                    ("Category", normalized["category"]),
                    ("Authors", author_text(normalized["authors"], 6)),
                    ("Published DOI", normalized["published_doi"]),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": preprint_sections(normalized),
            "previews": preprint_previews(normalized, links),
        },
        "citation": citation_payload(normalized),
        "related": {
            "published_doi": normalized["published_doi"],
            "published_url": normalized["published_url"],
            "jats_xml_url": normalized["jats_xml_url"],
        },
        "data": normalized,
    }


def publication_link_record(row: JsonObject, *, server: str) -> JsonObject:
    normalized = normalize_publication_link(row, server=server)
    links = publication_links(normalized)
    title = normalized["preprint_title"] or normalized["preprint_doi"] or normalized["published_doi"]
    description = " | ".join(
        part
        for part in [
            normalized["published_journal"],
            normalized["published_date"],
            f"published DOI {normalized['published_doi']}" if normalized["published_doi"] else "",
        ]
        if part
    )
    url = normalized["published_url"] or normalized["preprint_url"]
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "literature.publication_link",
        "record_type": f"{normalized['server']}_publication_link",
        "database": normalized["server"],
        "id": normalized["preprint_doi"] or normalized["published_doi"],
        "stable_id": f"{server_label(normalized['server'])}:published:{normalized['preprint_doi'] or normalized['published_doi']}",
        "label": normalized["preprint_doi"] or normalized["published_doi"],
        "title": title,
        "description": description,
        "url": url,
        "icon": normalized["server"],
        "identifiers": publication_identifiers(normalized),
        "links": links,
        "display": {
            "component": "citation",
            "chip_label": f"{server_label(normalized['server'])} publication",
            "icon": normalized["server"],
            "title": title,
            "subtitle": description,
            "description": normalized["preprint_abstract"],
            "metadata": publication_metadata(normalized),
            "badges": compact_badges(
                (server_label(normalized["server"]), "source"),
                ("published", "record_type"),
                (normalized["published_journal"], "journal"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": description,
                "icon": normalized["server"],
                "fields": compact_fields(
                    ("Preprint DOI", normalized["preprint_doi"]),
                    ("Published DOI", normalized["published_doi"]),
                    ("Journal", normalized["published_journal"]),
                    ("Preprint date", normalized["preprint_date"]),
                    ("Published date", normalized["published_date"]),
                    ("Authors", author_text(normalized["preprint_authors"], 6)),
                    ("URL", url),
                ),
            },
            "primary_url": url,
            "sections": publication_sections(normalized),
            "previews": publication_previews(normalized, links),
        },
        "citation": publication_citation_payload(normalized),
        "related": {
            "preprint_doi": normalized["preprint_doi"],
            "published_doi": normalized["published_doi"],
            "published_journal": normalized["published_journal"],
        },
        "data": normalized,
    }


def normalize_preprint(row: JsonObject, *, server: str) -> JsonObject:
    doi = normalize_space(row.get("doi") or row.get("preprint_doi") or row.get("biorxiv_doi"))
    version = normalize_space(row.get("version"))
    actual_server = normalize_space(row.get("server")).lower() or server
    published_doi = normalize_space(row.get("published") or row.get("published_doi"))
    return {
        "server": actual_server,
        "doi": doi,
        "title": normalize_space(row.get("title")),
        "authors": split_authors(row.get("authors")),
        "author_text": normalize_space(row.get("authors")),
        "author_corresponding": normalize_space(row.get("author_corresponding")),
        "author_corresponding_institution": normalize_space(row.get("author_corresponding_institution")),
        "date": normalize_space(row.get("date")),
        "version": version,
        "category": normalize_space(row.get("category")),
        "type": normalize_space(row.get("type")),
        "license": normalize_space(row.get("license")),
        "abstract": normalize_space(row.get("abstract")),
        "funding": normalize_space(row.get("funding")),
        "jats_xml_url": normalize_space(row.get("jatsxml") or row.get("jats_xml") or row.get("jats xml path")),
        "published_doi": published_doi,
        "published_url": doi_url(published_doi),
        "doi_url": doi_url(doi),
        "url": preprint_url(actual_server, doi, version),
    }


def normalize_publication_link(row: JsonObject, *, server: str) -> JsonObject:
    preprint_doi = normalize_space(row.get("biorxiv_doi") or row.get("preprint_doi") or row.get("doi"))
    published_doi = normalize_space(row.get("published_doi") or row.get("published"))
    actual_server = normalize_space(row.get("preprint_platform")).lower() or server
    return {
        "server": actual_server if actual_server in {"biorxiv", "medrxiv"} else server,
        "preprint_doi": preprint_doi,
        "published_doi": published_doi,
        "published_journal": normalize_space(row.get("published_journal")),
        "published_date": normalize_space(row.get("published_date")),
        "preprint_title": normalize_space(row.get("preprint_title") or row.get("title")),
        "preprint_authors": split_authors(row.get("preprint_authors") or row.get("authors")),
        "preprint_author_text": normalize_space(row.get("preprint_authors") or row.get("authors")),
        "preprint_category": normalize_space(row.get("preprint_category") or row.get("category")),
        "preprint_date": normalize_space(row.get("preprint_date") or row.get("date")),
        "preprint_abstract": normalize_space(row.get("preprint_abstract") or row.get("abstract")),
        "preprint_url": preprint_url(server, preprint_doi, normalize_space(row.get("version"))),
        "preprint_doi_url": doi_url(preprint_doi),
        "published_url": doi_url(published_doi),
    }


def preprint_links(normalized: JsonObject) -> list[JsonObject]:
    return compact_links(
        link(f"Open {server_label(normalized['server'])}", normalized["url"], primary=True),
        link("Open DOI", normalized["doi_url"], kind="external"),
        link("Open published DOI", normalized["published_url"], kind="related"),
        link("Open JATS XML", normalized["jats_xml_url"], kind="download"),
    )


def publication_links(normalized: JsonObject) -> list[JsonObject]:
    return compact_links(
        link("Open published DOI", normalized["published_url"], primary=bool(normalized["published_url"])),
        link(f"Open {server_label(normalized['server'])}", normalized["preprint_url"], kind="related", primary=not bool(normalized["published_url"])),
        link("Open preprint DOI", normalized["preprint_doi_url"], kind="related"),
    )


def preprint_identifiers(normalized: JsonObject) -> JsonObject:
    identifiers: JsonObject = {
        "doi": {"namespace": "doi", "id": normalized["doi"], "label": normalized["doi"], "url": normalized["doi_url"]},
        "preprint": {"namespace": normalized["server"], "id": normalized["doi"], "label": f"{server_label(normalized['server'])}:{normalized['doi']}", "url": normalized["url"]},
    }
    if normalized["published_doi"]:
        identifiers["published_doi"] = {
            "namespace": "doi",
            "id": normalized["published_doi"],
            "label": normalized["published_doi"],
            "url": normalized["published_url"],
        }
    return identifiers


def publication_identifiers(normalized: JsonObject) -> JsonObject:
    identifiers: JsonObject = {}
    if normalized["preprint_doi"]:
        identifiers["preprint_doi"] = {
            "namespace": "doi",
            "id": normalized["preprint_doi"],
            "label": normalized["preprint_doi"],
            "url": normalized["preprint_doi_url"],
        }
    if normalized["published_doi"]:
        identifiers["published_doi"] = {
            "namespace": "doi",
            "id": normalized["published_doi"],
            "label": normalized["published_doi"],
            "url": normalized["published_url"],
        }
    return identifiers


def preprint_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Server", server_label(normalized["server"])),
        ("DOI", normalized["doi"]),
        ("Date", normalized["date"]),
        ("Version", normalized["version"]),
        ("Category", normalized["category"]),
        ("Type", normalized["type"]),
        ("License", normalized["license"]),
        ("Authors", author_text(normalized["authors"], 6)),
        ("Published DOI", normalized["published_doi"]),
    )


def publication_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Server", server_label(normalized["server"])),
        ("Preprint DOI", normalized["preprint_doi"]),
        ("Published DOI", normalized["published_doi"]),
        ("Journal", normalized["published_journal"]),
        ("Preprint date", normalized["preprint_date"]),
        ("Published date", normalized["published_date"]),
        ("Category", normalized["preprint_category"]),
        ("Authors", author_text(normalized["preprint_authors"], 6)),
    )


def preprint_sections(normalized: JsonObject) -> list[JsonObject]:
    sections: list[JsonObject] = [
        {"key": "overview", "title": "Overview", "kind": "fields", "fields": preprint_metadata(normalized)},
        {
            "key": "authors",
            "title": "Authors",
            "kind": "table",
            "rows": [{"author": author} for author in normalized["authors"]],
        },
    ]
    if normalized["abstract"]:
        sections.append({"key": "abstract", "title": "Abstract", "kind": "text", "text": normalized["abstract"]})
    if normalized["funding"]:
        sections.append({"key": "funding", "title": "Funding", "kind": "text", "text": normalized["funding"]})
    return sections


def publication_sections(normalized: JsonObject) -> list[JsonObject]:
    sections: list[JsonObject] = [
        {"key": "overview", "title": "Overview", "kind": "fields", "fields": publication_metadata(normalized)},
        {
            "key": "publication_link",
            "title": "Publication link",
            "kind": "table",
            "rows": compact_fields(
                ("Preprint DOI", normalized["preprint_doi"]),
                ("Published DOI", normalized["published_doi"]),
                ("Journal", normalized["published_journal"]),
                ("Published date", normalized["published_date"]),
            ),
        },
    ]
    if normalized["preprint_abstract"]:
        sections.append({"key": "abstract", "title": "Preprint abstract", "kind": "text", "text": normalized["preprint_abstract"]})
    return sections


def preprint_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews: list[JsonObject] = [
        citation_preview(normalized, links),
        {
            "kind": "table",
            "title": "Preprint metadata",
            "provider": server_label(normalized["server"]),
            "id": normalized["doi"],
            "url": normalized["url"],
            "section_key": "overview",
            "data": {"columns": ["label", "value"], "rows": preprint_metadata(normalized)},
        },
        xref_preview(normalized["doi"], normalized["url"], preprint_xref_groups(normalized), links, server=normalized["server"]),
    ]
    if normalized["abstract"]:
        previews.append(
            {
                "kind": "text",
                "title": "Abstract",
                "provider": server_label(normalized["server"]),
                "id": normalized["doi"],
                "url": normalized["url"],
                "section_key": "abstract",
                "data": {"text": normalized["abstract"]},
            }
        )
    return previews


def publication_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    return [
        publication_citation_preview(normalized, links),
        {
            "kind": "table",
            "title": "Publication metadata",
            "provider": server_label(normalized["server"]),
            "id": normalized["preprint_doi"] or normalized["published_doi"],
            "url": normalized["published_url"] or normalized["preprint_url"],
            "section_key": "overview",
            "data": {"columns": ["label", "value"], "rows": publication_metadata(normalized)},
        },
        xref_preview(
            normalized["preprint_doi"] or normalized["published_doi"],
            normalized["published_url"] or normalized["preprint_url"],
            publication_xref_groups(normalized),
            links,
            server=normalized["server"],
        ),
    ]


def citation_preview(normalized: JsonObject, links: list[JsonObject]) -> JsonObject:
    return {
        "kind": "citation_list",
        "title": "Preprint citation",
        "provider": server_label(normalized["server"]),
        "id": normalized["doi"],
        "url": normalized["url"],
        "actions": display_actions(links),
        "data": {"items": [citation_payload(normalized)]},
    }


def publication_citation_preview(normalized: JsonObject, links: list[JsonObject]) -> JsonObject:
    return {
        "kind": "citation_list",
        "title": "Published article link",
        "provider": server_label(normalized["server"]),
        "id": normalized["preprint_doi"] or normalized["published_doi"],
        "url": normalized["published_url"] or normalized["preprint_url"],
        "actions": display_actions(links),
        "data": {"items": [publication_citation_payload(normalized)]},
    }


def xref_preview(identifier: str, url: str, groups: list[JsonObject], links: list[JsonObject], *, server: str) -> JsonObject:
    return {
        "kind": "xref_groups",
        "title": "Citation links",
        "provider": server_label(server),
        "id": identifier,
        "url": url,
        "actions": display_actions(links),
        "data": {"groups": groups},
    }


def preprint_xref_groups(normalized: JsonObject) -> list[JsonObject]:
    groups = [
        {
            "database": server_label(normalized["server"]),
            "items": [{"id": normalized["doi"], "label": normalized["doi"], "url": normalized["url"]}],
        },
        {"database": "DOI", "items": [{"id": normalized["doi"], "label": normalized["doi"], "url": normalized["doi_url"]}]},
    ]
    if normalized["published_doi"]:
        groups.append(
            {
                "database": "Published DOI",
                "items": [{"id": normalized["published_doi"], "label": normalized["published_doi"], "url": normalized["published_url"]}],
            }
        )
    if normalized["jats_xml_url"]:
        groups.append({"database": "JATS XML", "items": [{"id": "jatsxml", "label": "JATS XML", "url": normalized["jats_xml_url"]}]})
    return groups


def publication_xref_groups(normalized: JsonObject) -> list[JsonObject]:
    groups = []
    if normalized["preprint_doi"]:
        groups.append(
            {
                "database": server_label(normalized["server"]),
                "items": [{"id": normalized["preprint_doi"], "label": normalized["preprint_doi"], "url": normalized["preprint_url"]}],
            }
        )
    if normalized["published_doi"]:
        groups.append(
            {
                "database": "Published DOI",
                "items": [{"id": normalized["published_doi"], "label": normalized["published_doi"], "url": normalized["published_url"]}],
            }
        )
    return groups


def citation_payload(normalized: JsonObject) -> JsonObject:
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "citation",
        "citation_type": "preprint",
        "database": normalized["server"],
        "id": normalized["doi"],
        "stable_id": f"{server_label(normalized['server'])}:{normalized['doi']}",
        "label": normalized["doi"],
        "title": normalized["title"],
        "authors": normalized["authors"],
        "first_author": normalized["authors"][0] if normalized["authors"] else None,
        "journal": server_label(normalized["server"]),
        "publication_date": normalized["date"],
        "doi": normalized["doi"],
        "url": normalized["url"],
        "icon": normalized["server"],
        "summary": normalized["abstract"],
        "hover": {
            "title": normalized["title"],
            "subtitle": citation_subtitle(normalized),
            "icon": normalized["server"],
            "fields": preprint_metadata(normalized),
        },
        "links": display_actions(preprint_links(normalized)),
    }


def publication_citation_payload(normalized: JsonObject) -> JsonObject:
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "citation",
        "citation_type": "article",
        "database": normalized["server"],
        "id": normalized["published_doi"] or normalized["preprint_doi"],
        "stable_id": f"{server_label(normalized['server'])}:published:{normalized['published_doi'] or normalized['preprint_doi']}",
        "label": normalized["published_doi"] or normalized["preprint_doi"],
        "title": normalized["preprint_title"],
        "authors": normalized["preprint_authors"],
        "first_author": normalized["preprint_authors"][0] if normalized["preprint_authors"] else None,
        "journal": normalized["published_journal"],
        "publication_date": normalized["published_date"],
        "doi": normalized["published_doi"] or normalized["preprint_doi"],
        "url": normalized["published_url"] or normalized["preprint_url"],
        "icon": normalized["server"],
        "summary": normalized["preprint_abstract"],
        "hover": {
            "title": normalized["preprint_title"],
            "subtitle": " | ".join(part for part in [normalized["published_journal"], normalized["published_date"]] if part),
            "icon": normalized["server"],
            "fields": publication_metadata(normalized),
        },
        "links": display_actions(publication_links(normalized)),
    }


def preprint_url(server: str, doi: str, version: str = "") -> str:
    if not doi:
        return ""
    base = MEDRXIV_WEBSITE_BASE_URL if server == "medrxiv" else BIORXIV_WEBSITE_BASE_URL
    suffix = f"v{version}" if version else ""
    return f"{base.rstrip()}/content/{urllib.parse.quote(doi, safe='/')}{suffix}"


def doi_url(doi: str) -> str:
    doi = normalize_space(doi)
    if not doi:
        return ""
    return f"https://doi.org/{urllib.parse.quote(doi, safe='/')}"


def server_label(server: str) -> str:
    return "medRxiv" if server == "medrxiv" else "bioRxiv"


def citation_subtitle(normalized: JsonObject) -> str:
    return " | ".join(part for part in [author_text(normalized["authors"], 3), normalized["date"], normalized["category"]] if part)


def author_text(authors: list[str], limit: int) -> str:
    if not authors:
        return ""
    shown = authors[:limit]
    suffix = f" +{len(authors) - limit}" if len(authors) > limit else ""
    return "; ".join(shown) + suffix


def compact_fields(*pairs: tuple[str, object]) -> list[JsonObject]:
    rows = []
    for label_text, value in pairs:
        text = normalize_space(value)
        if text:
            rows.append({"label": label_text, "value": text})
    return rows


def compact_badges(*pairs: tuple[object, str]) -> list[JsonObject]:
    rows = []
    for label_value, badge_kind in pairs:
        text = normalize_space(label_value)
        if text:
            rows.append({"label": text, "kind": badge_kind})
    return rows


def link(label: str, url: object, *, kind: str = "external", primary: bool = False) -> JsonObject:
    url_text = normalize_space(url)
    if not url_text or not url_text.startswith(("http://", "https://")):
        return {}
    return {"label": label, "url": url_text, "kind": kind, "primary": primary}


def compact_links(*links: JsonObject) -> list[JsonObject]:
    return [item for item in links if item.get("label") and item.get("url")]


def display_actions(links: list[JsonObject]) -> list[JsonObject]:
    return [
        {
            "label": normalize_space(item.get("label")),
            "url": normalize_space(item.get("url")),
            "kind": normalize_space(item.get("kind")) or "external",
            "primary": bool(item.get("primary")),
        }
        for item in links
        if normalize_space(item.get("label")) and normalize_space(item.get("url"))
    ]

