"""Front-end compatible record envelopes for EFO/OLS4 ontology terms."""

from __future__ import annotations

from .constants import OLS4_API_BASE_URL, OLS4_WEBSITE_BASE_URL, RECORD_SCHEMA_VERSION, JsonObject
from .utils import normalize_space, ols_api_url, ols_term_url, safe_dict, safe_list, term_endpoint


def efo_term_record(
    term: JsonObject,
    *,
    relation: str = "",
    parent_id: str = "",
    website_base_url: str = OLS4_WEBSITE_BASE_URL,
    api_base_url: str = OLS4_API_BASE_URL,
) -> JsonObject:
    normalized = normalize_term(term, relation=relation, parent_id=parent_id, website_base_url=website_base_url, api_base_url=api_base_url)
    term_id = normalized["id"]
    title = normalized["label"] or term_id
    description = normalized["description"][0] if normalized["description"] else "EFO ontology term"
    links = term_links(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "ontology.term",
        "record_type": "efo_term",
        "database": "efo",
        "id": term_id,
        "stable_id": f"EFO:{term_id}",
        "label": term_id,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "efo",
        "identifiers": term_identifiers(normalized),
        "links": links,
        "display": {
            "component": "ontology_term",
            "chip_label": term_id,
            "icon": "efo",
            "title": title,
            "subtitle": term_subtitle(normalized),
            "description": description,
            "metadata": term_metadata(normalized),
            "badges": compact_badges(
                ("EFO", "source"),
                (term_id, "identifier"),
                (normalized["type"], "record_type"),
                ("obsolete" if normalized["is_obsolete"] else "", "warning"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": term_subtitle(normalized),
                "icon": "efo",
                "fields": compact_fields(
                    ("ID", term_id),
                    ("Label", title),
                    ("IRI", normalized["iri"]),
                    ("Ontology", normalized["ontology_name"]),
                    ("Synonyms", len(normalized["synonyms"])),
                    ("Cross references", len(normalized["xrefs"])),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": term_sections(normalized),
            "previews": term_previews(normalized, links),
        },
        "related": {
            "synonyms": normalized["synonyms"],
            "xrefs": normalized["xrefs"],
            "children": normalized["children"],
            "replaced_by": normalized["replaced_by"],
        },
        "data": normalized,
    }


def normalize_term(term: JsonObject, *, relation: str, parent_id: str, website_base_url: str, api_base_url: str) -> JsonObject:
    iri = normalize_space(term.get("iri"))
    obo_id = normalize_space(term.get("obo_id"))
    short_form = normalize_space(term.get("short_form"))
    term_id = obo_id or short_form.replace("_", ":", 1) or iri
    links = safe_dict(term.get("_links"))
    self_link = safe_dict(links.get("self")).get("href")
    return {
        "id": term_id,
        "iri": iri,
        "short_form": short_form,
        "obo_id": obo_id,
        "label": normalize_space(term.get("label")),
        "ontology_name": normalize_space(term.get("ontology_name")) or "efo",
        "ontology_prefix": normalize_space(term.get("ontology_prefix")) or "EFO",
        "type": normalize_space(term.get("type")) or "class",
        "description": normalize_descriptions(term.get("description")),
        "synonyms": normalize_synonyms(term),
        "xrefs": unique_xrefs(normalize_obo_xrefs(term) + normalize_annotation_xrefs(safe_dict(term.get("annotation")))),
        "annotation": compact_annotation(safe_dict(term.get("annotation"))),
        "is_obsolete": bool(term.get("is_obsolete") or term.get("isObsolete")),
        "is_defining_ontology": bool(term.get("is_defining_ontology")),
        "has_children": bool(term.get("has_children") or term.get("hasChildren")),
        "is_root": bool(term.get("is_root")),
        "replaced_by": normalize_space(term.get("term_replaced_by") or safe_dict(term.get("annotation")).get("term replaced by")),
        "relation": relation,
        "parent_id": parent_id,
        "children": normalize_child_terms(safe_list(term.get("children"))),
        "url": ols_term_url(iri, website_base_url),
        "api_url": term_api_url(iri=iri, short_form=short_form, self_link=self_link, api_base_url=api_base_url),
    }


def term_api_url(*, iri: str, short_form: str, self_link: object, api_base_url: str) -> str:
    link = normalize_space(self_link)
    if link.startswith(("http://", "https://")):
        return link
    term_value = iri or short_form
    if not term_value:
        return ""
    endpoint, _ = term_endpoint(term_value)
    return ols_api_url(endpoint, {}, api_base_url)


def normalize_descriptions(value: object) -> list[str]:
    if isinstance(value, str):
        return [normalize_space(value)] if normalize_space(value) else []
    return [normalize_space(item) for item in safe_list(value) if normalize_space(item)]


def normalize_synonyms(term: JsonObject) -> list[JsonObject]:
    synonyms: list[JsonObject] = []
    for key, kind in [
        ("synonyms", "synonym"),
        ("exact_synonyms", "exact"),
        ("narrow_synonyms", "narrow"),
        ("related_synonyms", "related"),
    ]:
        for item in safe_list(term.get(key)):
            text = normalize_space(item)
            if text:
                synonyms.append({"name": text, "type": kind})
    for item in safe_list(term.get("obo_synonym")):
        if isinstance(item, dict):
            text = normalize_space(item.get("name") or item.get("synonym"))
            kind = normalize_space(item.get("scope") or item.get("type")) or "obo"
            if text:
                synonyms.append({"name": text, "type": kind})
    return unique_synonyms(synonyms)


def normalize_obo_xrefs(term: JsonObject) -> list[JsonObject]:
    xrefs = []
    for item in safe_list(term.get("obo_xref")):
        if not isinstance(item, dict):
            continue
        database = normalize_space(item.get("database"))
        identifier = normalize_space(item.get("id"))
        if database or identifier:
            xrefs.append(
                {
                    "database": database,
                    "id": identifier,
                    "label": ":".join(part for part in [database, identifier] if part),
                    "description": normalize_space(item.get("description")),
                    "url": normalize_space(item.get("url")) or xref_url(database, identifier),
                }
            )
    return xrefs


def normalize_annotation_xrefs(annotation: JsonObject) -> list[JsonObject]:
    xrefs = []
    for text in safe_list(annotation.get("database_cross_reference")):
        value = normalize_space(text)
        if not value:
            continue
        database, identifier = split_xref(value)
        xrefs.append({"database": database, "id": identifier, "label": value, "url": xref_url(database, identifier)})
    return xrefs


def compact_annotation(annotation: JsonObject) -> JsonObject:
    return {
        key: value
        for key, value in annotation.items()
        if key in {"database_cross_reference", "reason_for_obsolescence", "term replaced by", "organizational_class"}
    }


def normalize_child_terms(children: list[object]) -> list[JsonObject]:
    rows = []
    for item in children:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "id": normalize_space(item.get("obo_id") or item.get("short_form") or item.get("iri")),
                "label": normalize_space(item.get("label")),
                "iri": normalize_space(item.get("iri")),
                "relation": normalize_space(item.get("relation") or item.get("type")),
                "url": ols_term_url(normalize_space(item.get("iri"))),
            }
        )
    return rows


def term_links(normalized: JsonObject) -> list[JsonObject]:
    return compact_links(
        link("Open EFO term", normalized["url"], primary=True),
        link("Open OLS4 API record", normalized["api_url"], kind="api"),
        link("Open replacement term", ols_term_url(normalized["replaced_by"]) if normalized["replaced_by"].startswith(("http://", "https://")) else "", kind="related"),
    )


def term_identifiers(normalized: JsonObject) -> JsonObject:
    identifiers: JsonObject = {
        "ontology": {
            "namespace": "efo",
            "id": normalized["id"],
            "label": normalized["id"],
            "url": normalized["url"],
        }
    }
    if normalized["iri"]:
        identifiers["iri"] = {"namespace": "iri", "id": normalized["iri"], "label": normalized["iri"], "url": normalized["iri"]}
    return identifiers


def term_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("ID", normalized["id"]),
        ("Short form", normalized["short_form"]),
        ("Ontology", normalized["ontology_name"]),
        ("Type", normalized["type"]),
        ("Obsolete", "yes" if normalized["is_obsolete"] else "no"),
        ("Synonyms", len(normalized["synonyms"])),
        ("Cross references", len(normalized["xrefs"])),
        ("Has children", "yes" if normalized["has_children"] else "no"),
        ("Replacement", normalized["replaced_by"]),
    )


def term_subtitle(normalized: JsonObject) -> str:
    return " | ".join(part for part in [normalized["id"], normalized["ontology_prefix"], normalized["relation"]] if part)


def term_sections(normalized: JsonObject) -> list[JsonObject]:
    sections: list[JsonObject] = [
        {"key": "overview", "title": "Overview", "kind": "fields", "fields": term_metadata(normalized)}
    ]
    if normalized["description"]:
        sections.append({"key": "description", "title": "Description", "kind": "text", "text": normalized["description"][0]})
    if normalized["synonyms"]:
        sections.append({"key": "synonyms", "title": "Synonyms", "kind": "table", "rows": normalized["synonyms"]})
    if normalized["xrefs"]:
        sections.append({"key": "xrefs", "title": "Cross-references", "kind": "table", "rows": normalized["xrefs"]})
    if normalized["children"]:
        sections.append({"key": "children", "title": "Children", "kind": "table", "rows": normalized["children"]})
    return sections


def term_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews: list[JsonObject] = [
        {
            "kind": "table",
            "title": "EFO term details",
            "provider": "EFO",
            "id": normalized["id"],
            "url": normalized["url"],
            "section_key": "overview",
            "actions": display_actions(links),
            "data": {"columns": ["label", "value"], "rows": term_metadata(normalized)},
        }
    ]
    if normalized["children"] or normalized["parent_id"]:
        nodes = [{"id": normalized["id"], "label": normalized["label"] or normalized["id"], "kind": "term"}]
        edges = []
        if normalized["parent_id"]:
            nodes.append({"id": normalized["parent_id"], "label": normalized["parent_id"], "kind": "parent"})
            edges.append({"source": normalized["parent_id"], "target": normalized["id"], "relation": normalized["relation"] or "child"})
        for child in normalized["children"]:
            nodes.append({"id": child["id"], "label": child["label"] or child["id"], "kind": "child"})
            edges.append({"source": normalized["id"], "target": child["id"], "relation": child["relation"] or "child"})
        previews.append(
            {
                "kind": "network",
                "title": "Ontology relations",
                "provider": "EFO",
                "id": normalized["id"],
                "url": normalized["url"],
                "section_key": "children",
                "actions": display_actions(links[:1]),
                "data": {"nodes": nodes, "edges": edges},
            }
        )
    if normalized["xrefs"]:
        previews.append(
            {
                "kind": "xref_groups",
                "title": "Cross-references",
                "provider": "EFO",
                "id": normalized["id"],
                "url": normalized["url"],
                "section_key": "xrefs",
                "data": {"groups": xref_groups(normalized["xrefs"])},
            }
        )
    if normalized["description"]:
        previews.append(
            {
                "kind": "text",
                "title": "Definition",
                "provider": "EFO",
                "id": normalized["id"],
                "url": normalized["url"],
                "section_key": "description",
                "data": {"text": normalized["description"][0]},
            }
        )
    return previews


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


def unique_synonyms(items: list[JsonObject]) -> list[JsonObject]:
    seen = set()
    out = []
    for item in items:
        key = item.get("name", "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def xref_groups(xrefs: list[JsonObject]) -> list[JsonObject]:
    groups: dict[str, list[JsonObject]] = {}
    for xref in xrefs:
        database = normalize_space(xref.get("database")) or "xref"
        groups.setdefault(database, []).append(xref)
    return [{"database": database, "items": items, "count": len(items)} for database, items in sorted(groups.items())]


def split_xref(value: str) -> tuple[str, str]:
    if ":" not in value:
        return "xref", value
    return value.split(":", 1)


def xref_url(database: str, identifier: str) -> str:
    if database == "PMID" and identifier:
        return f"https://pubmed.ncbi.nlm.nih.gov/{identifier}/"
    if database == "MESH" and identifier:
        return f"https://id.nlm.nih.gov/mesh/{identifier}"
    if database == "OMIM" and identifier:
        return f"https://omim.org/entry/{identifier}"
    if database == "ICD10" and identifier:
        return f"https://icd.who.int/browse10/2019/en#/{identifier}"
    if database == "DOID" and identifier:
        return f"http://purl.obolibrary.org/obo/DOID_{identifier}"
    if database in {"NCIt", "NCIT"} and identifier:
        return f"http://purl.obolibrary.org/obo/NCIT_{identifier}"
    return ""


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
