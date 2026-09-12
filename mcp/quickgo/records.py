"""Front-end compatible record envelopes for QuickGO terms and annotations."""

from __future__ import annotations

import urllib.parse
from typing import Any

from .constants import QUICKGO_API_BASE_URL, QUICKGO_WEBSITE_BASE_URL, RECORD_SCHEMA_VERSION, JsonObject
from .utils import normalize_space, safe_list


def quickgo_term_record(
    term: JsonObject,
    *,
    relation: str = "",
    parent_id: str = "",
    website_base_url: str = QUICKGO_WEBSITE_BASE_URL,
    api_base_url: str = QUICKGO_API_BASE_URL,
) -> JsonObject:
    normalized = normalize_term(
        term,
        relation=relation,
        parent_id=parent_id,
        website_base_url=website_base_url,
        api_base_url=api_base_url,
    )
    go_id = normalized["id"]
    title = normalized["name"] or go_id
    description = normalized["definition_text"] or normalized["aspect_label"] or "Gene Ontology term"
    links = term_links(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "ontology.term",
        "record_type": "quickgo_term",
        "database": "quickgo",
        "id": go_id,
        "stable_id": go_id,
        "label": go_id,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "quickgo",
        "identifiers": term_identifiers(normalized),
        "links": links,
        "display": {
            "component": "ontology_term",
            "chip_label": go_id,
            "icon": "quickgo",
            "title": title,
            "subtitle": term_subtitle(normalized),
            "description": description,
            "metadata": term_metadata(normalized),
            "badges": compact_badges(
                ("QuickGO", "source"),
                (go_id, "identifier"),
                (normalized["aspect_label"], "context"),
                ("obsolete" if normalized["is_obsolete"] else "", "warning"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": term_subtitle(normalized),
                "icon": "quickgo",
                "fields": compact_fields(
                    ("GO ID", go_id),
                    ("Name", title),
                    ("Aspect", normalized["aspect_label"]),
                    ("Usage", normalized["usage"]),
                    ("Synonyms", str(len(normalized["synonyms"]))),
                    ("Children", str(len(normalized["children"]))),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": term_sections(normalized),
            "previews": term_previews(normalized, links),
        },
        "related": {
            "synonyms": normalized["synonyms"],
            "children": normalized["children"],
            "ancestors": normalized["ancestors"],
            "xrefs": normalized["xrefs"],
        },
        "data": normalized,
    }


def quickgo_annotation_dataset_record(
    rows: list[JsonObject],
    *,
    query: JsonObject,
    total: int,
    website_base_url: str = QUICKGO_WEBSITE_BASE_URL,
    api_base_url: str = QUICKGO_API_BASE_URL,
) -> JsonObject:
    annotations = [normalize_annotation(row) for row in rows]
    title = annotation_title(query)
    query_label = annotation_query_label(query)
    url = quickgo_annotations_url(query, website_base_url)
    api_url = quickgo_api_url("annotation/search", api_base_url, query)
    links = [
        {"label": "Open QuickGO annotations", "url": url, "kind": "external", "primary": True},
        {"label": "Open QuickGO API query", "url": api_url, "kind": "external"},
    ]
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "dataset",
        "record_type": "quickgo_annotation_search",
        "database": "quickgo",
        "id": query_label or "annotations",
        "stable_id": f"QuickGO annotations:{query_label or 'query'}",
        "label": query_label or "QuickGO annotations",
        "title": title,
        "description": f"{len(annotations)} returned of {total} QuickGO annotation rows",
        "url": url,
        "icon": "quickgo",
        "identifiers": annotation_identifiers(query),
        "links": links,
        "display": {
            "component": "dataset",
            "chip_label": query_label or "QuickGO annotations",
            "icon": "quickgo",
            "title": title,
            "subtitle": f"{len(annotations)} returned | {total} available",
            "description": f"QuickGO annotation evidence rows for {query_label or 'the supplied query'}.",
            "metadata": compact_fields(
                ("Returned rows", str(len(annotations))),
                ("Available rows", str(total)),
                ("Gene product", normalize_space(query.get("geneProductId"))),
                ("GO term", normalize_space(query.get("goId"))),
                ("Taxon", normalize_space(query.get("taxonId"))),
                ("Evidence", normalize_space(query.get("evidenceCode"))),
            ),
            "badges": compact_badges(("QuickGO", "source"), ("GOA", "record_type"), (query_label, "context")),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": f"{len(annotations)} returned | {total} available",
                "icon": "quickgo",
                "fields": compact_fields(
                    ("Gene product", normalize_space(query.get("geneProductId"))),
                    ("GO term", normalize_space(query.get("goId"))),
                    ("Taxon", normalize_space(query.get("taxonId"))),
                    ("Evidence", normalize_space(query.get("evidenceCode"))),
                    ("URL", url),
                ),
            },
            "primary_url": url,
            "sections": [
                {
                    "key": "annotations",
                    "title": "Annotation rows",
                    "kind": "table",
                    "rows": annotations,
                }
            ],
            "previews": annotation_previews(annotations, links),
        },
        "related": {"annotations": annotations, "query": dict(query)},
        "data": {
            "query": dict(query),
            "returned": len(annotations),
            "total": total,
            "annotations": annotations,
            "url": url,
            "api_url": api_url,
        },
    }


def normalize_term(
    term: JsonObject,
    *,
    relation: str,
    parent_id: str,
    website_base_url: str,
    api_base_url: str,
) -> JsonObject:
    go_id = normalize_space(term.get("id"))
    definition = term.get("definition") if isinstance(term.get("definition"), dict) else {}
    synonyms = [
        {
            "name": normalize_space(item.get("name")),
            "type": normalize_space(item.get("type")),
        }
        for item in safe_list(term.get("synonyms"))
        if isinstance(item, dict) and normalize_space(item.get("name"))
    ]
    children = [normalize_relation(item) for item in safe_list(term.get("children")) if isinstance(item, dict)]
    ancestors = [
        normalize_space(item)
        for item in safe_list(term.get("ancestors"))
        if normalize_space(item)
    ]
    xrefs = normalize_xrefs(safe_list(definition.get("xrefs"))) + normalize_xrefs(safe_list(term.get("xRefs")))
    return {
        "id": go_id,
        "name": normalize_space(term.get("name")),
        "aspect": normalize_space(term.get("aspect")),
        "aspect_label": aspect_label(term.get("aspect")),
        "usage": normalize_space(term.get("usage")),
        "is_obsolete": bool(term.get("isObsolete")),
        "definition_text": normalize_space(definition.get("text")),
        "definition_xrefs": normalize_xrefs(safe_list(definition.get("xrefs"))),
        "synonyms": synonyms,
        "children": children,
        "ancestors": ancestors,
        "secondary_ids": [normalize_space(item) for item in safe_list(term.get("secondaryIds")) if normalize_space(item)],
        "replaces": [normalize_relation(item) for item in safe_list(term.get("replaces")) if isinstance(item, dict)],
        "xrefs": unique_xrefs(xrefs),
        "relation": relation,
        "parent_id": parent_id,
        "url": quickgo_term_url(go_id, website_base_url),
        "api_url": quickgo_api_url(f"ontology/go/terms/{go_id}", api_base_url, {}),
    }


def normalize_annotation(row: JsonObject) -> JsonObject:
    reference = normalize_space(row.get("reference"))
    return {
        "id": normalize_space(row.get("id")),
        "gene_product_id": normalize_space(row.get("geneProductId")),
        "symbol": normalize_space(row.get("symbol")),
        "name": normalize_space(row.get("name")),
        "qualifier": normalize_space(row.get("qualifier")),
        "go_id": normalize_space(row.get("goId")),
        "go_name": normalize_space(row.get("goName")),
        "go_aspect": normalize_space(row.get("goAspect")),
        "go_aspect_label": aspect_label(row.get("goAspect")),
        "go_evidence": normalize_space(row.get("goEvidence")),
        "evidence_code": normalize_space(row.get("evidenceCode")),
        "reference": reference,
        "reference_url": reference_url(reference),
        "taxon_id": normalize_space(row.get("taxonId")),
        "taxon_name": normalize_space(row.get("taxonName")),
        "assigned_by": normalize_space(row.get("assignedBy")),
        "date": normalize_space(row.get("date")),
        "target_sets": [normalize_space(item) for item in safe_list(row.get("targetSets")) if normalize_space(item)],
        "with_from": normalize_nested_xrefs(row.get("withFrom")),
        "extensions": normalize_nested_xrefs(row.get("extensions")),
        "go_url": quickgo_term_url(normalize_space(row.get("goId")), QUICKGO_WEBSITE_BASE_URL),
    }


def normalize_relation(item: JsonObject) -> JsonObject:
    return {
        "id": normalize_space(item.get("id")),
        "name": normalize_space(item.get("name")),
        "relation": normalize_space(item.get("relation") or item.get("type")),
        "has_children": bool(item.get("hasChildren")),
    }


def normalize_xrefs(items: list[Any]) -> list[JsonObject]:
    xrefs = []
    for item in items:
        if not isinstance(item, dict):
            continue
        db = normalize_space(item.get("dbCode") or item.get("db"))
        identifier = normalize_space(item.get("dbId") or item.get("id"))
        if not db and not identifier:
            continue
        xrefs.append(
            {
                "database": db,
                "id": identifier,
                "label": ":".join(part for part in [db, identifier] if part),
                "name": normalize_space(item.get("name")),
                "url": xref_url(db, identifier),
            }
        )
    return xrefs


def unique_xrefs(items: list[JsonObject]) -> list[JsonObject]:
    seen = set()
    out = []
    for item in items:
        key = (item.get("database"), item.get("id"))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def normalize_nested_xrefs(value: object) -> list[JsonObject]:
    out = []
    for group in safe_list(value):
        if not isinstance(group, dict):
            continue
        for xref in safe_list(group.get("connectedXrefs")):
            if isinstance(xref, dict):
                out.extend(normalize_xrefs([xref]))
    return out


def term_sections(normalized: JsonObject) -> list[JsonObject]:
    sections = [
        {
            "key": "overview",
            "title": "Overview",
            "kind": "table",
            "rows": [
                {"field": "GO ID", "value": normalized["id"]},
                {"field": "Name", "value": normalized["name"]},
                {"field": "Aspect", "value": normalized["aspect_label"]},
                {"field": "Usage", "value": normalized["usage"]},
                {"field": "Definition", "value": normalized["definition_text"]},
            ],
        }
    ]
    if normalized["synonyms"]:
        sections.append({"key": "synonyms", "title": "Synonyms", "kind": "table", "rows": normalized["synonyms"]})
    if normalized["children"]:
        sections.append({"key": "children", "title": "Children", "kind": "table", "rows": normalized["children"]})
    if normalized["ancestors"]:
        sections.append(
            {
                "key": "ancestors",
                "title": "Ancestors",
                "kind": "table",
                "rows": [{"id": item, "url": quickgo_term_url(item, QUICKGO_WEBSITE_BASE_URL)} for item in normalized["ancestors"]],
            }
        )
    if normalized["xrefs"]:
        sections.append({"key": "xrefs", "title": "Cross-references", "kind": "table", "rows": normalized["xrefs"]})
    return sections


def term_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews = [
        {
            "kind": "table",
            "title": "GO term details",
            "section_key": "overview",
            "data": {
                "columns": ["field", "value"],
                "rows": term_sections(normalized)[0]["rows"],
            },
        }
    ]
    if normalized["children"] or normalized["ancestors"]:
        nodes = [{"id": normalized["id"], "label": normalized["name"] or normalized["id"], "kind": "term"}]
        edges = []
        for child in normalized["children"]:
            nodes.append({"id": child["id"], "label": child["name"] or child["id"], "kind": "child"})
            edges.append({"source": normalized["id"], "target": child["id"], "relation": child["relation"]})
        for ancestor in normalized["ancestors"]:
            nodes.append({"id": ancestor, "label": ancestor, "kind": "ancestor"})
            edges.append({"source": ancestor, "target": normalized["id"], "relation": "ancestor"})
        previews.append(
            {
                "kind": "network",
                "title": "Ontology relations",
                "provider": "QuickGO",
                "id": normalized["id"],
                "url": normalized["url"],
                "section_key": "children" if normalized["children"] else "ancestors",
                "actions": display_actions(links[:1]),
                "data": {"nodes": nodes, "edges": edges},
            }
        )
    if normalized["xrefs"]:
        previews.append(
            {
                "kind": "xref_groups",
                "title": "Cross-references",
                "section_key": "xrefs",
                "data": {"groups": xref_groups(normalized["xrefs"])},
            }
        )
    return previews


def annotation_previews(annotations: list[JsonObject], links: list[JsonObject]) -> list[JsonObject]:
    previews = [
        {
            "kind": "table",
            "title": "Annotation evidence",
            "section_key": "annotations",
            "actions": display_actions(links[:1]),
            "data": {
                "columns": [
                    "gene_product_id",
                    "symbol",
                    "qualifier",
                    "go_id",
                    "go_evidence",
                    "evidence_code",
                    "reference",
                    "taxon_id",
                    "assigned_by",
                    "date",
                ],
                "rows": annotations,
            },
        }
    ]
    xrefs = []
    for row in annotations:
        xrefs.append({"database": "GO", "id": row["go_id"], "label": row["go_id"], "url": row["go_url"]})
        if row["reference"]:
            xrefs.append({"database": reference_database(row["reference"]), "id": row["reference"], "label": row["reference"], "url": row["reference_url"]})
    previews.append({"kind": "xref_groups", "title": "Annotation links", "data": {"groups": xref_groups(unique_xrefs(xrefs))}})
    return previews


def term_links(normalized: JsonObject) -> list[JsonObject]:
    return [
        {"label": "Open QuickGO term", "url": normalized["url"], "kind": "external", "primary": True},
        {"label": "Open QuickGO API record", "url": normalized["api_url"], "kind": "external"},
    ]


def term_identifiers(normalized: JsonObject) -> JsonObject:
    identifiers: JsonObject = {
        "go": {
            "namespace": "go",
            "id": normalized["id"],
            "label": normalized["id"],
            "url": normalized["url"],
        }
    }
    if normalized["secondary_ids"]:
        identifiers["secondary_go"] = [
            {"namespace": "go.secondary", "id": item, "label": item, "url": quickgo_term_url(item, QUICKGO_WEBSITE_BASE_URL)}
            for item in normalized["secondary_ids"]
        ]
    return identifiers


def annotation_identifiers(query: JsonObject) -> JsonObject:
    identifiers: JsonObject = {}
    if query.get("geneProductId"):
        identifiers["gene_product"] = {
            "namespace": "quickgo.gene_product",
            "id": normalize_space(query.get("geneProductId")),
            "label": normalize_space(query.get("geneProductId")),
        }
    if query.get("goId"):
        go_id = normalize_space(query.get("goId"))
        identifiers["go"] = {"namespace": "go", "id": go_id, "label": go_id, "url": quickgo_term_url(go_id, QUICKGO_WEBSITE_BASE_URL)}
    return identifiers


def term_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("GO ID", normalized["id"]),
        ("Aspect", normalized["aspect_label"]),
        ("Usage", normalized["usage"]),
        ("Obsolete", "yes" if normalized["is_obsolete"] else "no"),
        ("Synonyms", str(len(normalized["synonyms"]))),
        ("Children", str(len(normalized["children"]))),
        ("Ancestors", str(len(normalized["ancestors"]))),
    )


def term_subtitle(normalized: JsonObject) -> str:
    return " | ".join(part for part in [normalized["id"], normalized["aspect_label"], normalized["relation"]] if part)


def annotation_title(query: JsonObject) -> str:
    label = annotation_query_label(query)
    return f"QuickGO annotations for {label}" if label else "QuickGO annotation search"


def annotation_query_label(query: JsonObject) -> str:
    parts = [
        normalize_space(query.get("geneProductId")),
        normalize_space(query.get("goId")),
        f"taxon {normalize_space(query.get('taxonId'))}" if normalize_space(query.get("taxonId")) else "",
        normalize_space(query.get("evidenceCode")),
    ]
    return " | ".join(part for part in parts if part)


def aspect_label(value: object) -> str:
    text = normalize_space(value)
    mapping = {
        "biological_process": "biological process",
        "molecular_function": "molecular function",
        "cellular_component": "cellular component",
        "P": "biological process",
        "F": "molecular function",
        "C": "cellular component",
    }
    return mapping.get(text, text)


def xref_groups(xrefs: list[JsonObject]) -> list[JsonObject]:
    groups: dict[str, list[JsonObject]] = {}
    for xref in xrefs:
        database = normalize_space(xref.get("database")) or "xref"
        groups.setdefault(database, []).append(xref)
    return [{"label": database, "items": items, "count": len(items)} for database, items in sorted(groups.items())]


def display_actions(links: list[JsonObject]) -> list[JsonObject]:
    actions = []
    for link in links:
        if link.get("url"):
            actions.append(
                {
                    "label": normalize_space(link.get("label")),
                    "url": normalize_space(link.get("url")),
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


def quickgo_term_url(go_id: str, website_base_url: str) -> str:
    quoted = urllib.parse.quote(go_id, safe=":")
    return f"{website_base_url.rstrip('/')}/term/{quoted}"


def quickgo_annotations_url(query: JsonObject, website_base_url: str) -> str:
    params = {
        key: value
        for key, value in query.items()
        if value not in {None, ""}
    }
    encoded = urllib.parse.urlencode(params, doseq=True)
    base = f"{website_base_url.rstrip('/')}/annotations"
    return f"{base}?{encoded}" if encoded else base


def quickgo_api_url(endpoint: str, api_base_url: str, params: JsonObject) -> str:
    base = f"{api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    if not params:
        return base
    return f"{base}?{urllib.parse.urlencode(params, doseq=True)}"


def reference_url(reference: str) -> str:
    if reference.startswith("PMID:"):
        return f"https://pubmed.ncbi.nlm.nih.gov/{reference.split(':', 1)[1]}/"
    if reference.startswith("GO_REF:"):
        return f"https://geneontology.org/docs/go-references/{reference.split(':', 1)[1]}/"
    return ""


def reference_database(reference: str) -> str:
    if ":" in reference:
        return reference.split(":", 1)[0]
    return "reference"


def xref_url(database: str, identifier: str) -> str:
    if database == "PMID" and identifier:
        return f"https://pubmed.ncbi.nlm.nih.gov/{identifier}/"
    if database == "Reactome" and identifier:
        return f"https://reactome.org/content/detail/{urllib.parse.quote(identifier, safe=':-')}"
    if database == "Wikipedia" and identifier:
        return f"https://en.wikipedia.org/wiki/{urllib.parse.quote(identifier.replace(' ', '_'))}"
    if database == "UniProtKB-KW" and identifier:
        return f"https://www.uniprot.org/keywords/{urllib.parse.quote(identifier)}"
    return ""

