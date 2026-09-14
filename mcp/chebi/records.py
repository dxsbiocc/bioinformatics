"""Front-end compatible record envelopes for ChEBI compounds and ontology edges."""

from __future__ import annotations

from typing import Any

from .constants import (
    CHEBI_API_BASE_URL,
    CHEBI_WEBSITE_BASE_URL,
    MAX_SYNONYMS,
    MAX_XREFS,
    RECORD_SCHEMA_VERSION,
    JsonObject,
)
from .utils import (
    chebi_image_url,
    chebi_numeric_id,
    chebi_page_url,
    first_text,
    normalize_chebi_id,
    normalize_space,
    safe_dict,
    safe_list,
)


def chebi_compound_record(
    payload: JsonObject,
    *,
    website_base_url: str = CHEBI_WEBSITE_BASE_URL,
    api_base_url: str = CHEBI_API_BASE_URL,
) -> JsonObject:
    normalized = normalize_compound(payload, website_base_url=website_base_url, api_base_url=api_base_url)
    chebi_id = normalized["id"]
    title = normalized["name"] or chebi_id
    description = normalized["definition"] or "ChEBI compound record"
    links = compound_links(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "chemical.compound",
        "record_type": "chebi_compound",
        "database": "chebi",
        "id": chebi_id,
        "stable_id": chebi_id,
        "label": title,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "chebi",
        "identifiers": compound_identifiers(normalized),
        "links": links,
        "display": {
            "component": "compound",
            "chip_label": chebi_id,
            "icon": "chebi",
            "title": title,
            "subtitle": compound_subtitle(normalized),
            "description": description,
            "metadata": compound_metadata(normalized),
            "badges": compact_badges(
                ("ChEBI", "source"),
                (chebi_id, "identifier"),
                (normalized["formula"], "formula"),
                (f"{normalized['stars']} stars" if normalized["stars"] else "", "quality"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": compound_subtitle(normalized),
                "icon": "chebi",
                "fields": compact_fields(
                    ("ChEBI ID", chebi_id),
                    ("Name", title),
                    ("Formula", normalized["formula"]),
                    ("Mass", normalized["mass"]),
                    ("Monoisotopic mass", normalized["monoisotopic_mass"]),
                    ("InChIKey", normalized["inchikey"]),
                    ("Synonyms", len(normalized["synonyms"])),
                    ("Cross references", len(normalized["xrefs"])),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": compound_sections(normalized),
            "previews": compound_previews(normalized, links),
        },
        "related": {
            "synonyms": normalized["synonyms"],
            "xrefs": normalized["xrefs"],
            "citations": normalized["citations"],
            "origins": normalized["origins"],
            "ontology_relations": normalized["ontology_relations"],
        },
        "data": normalized,
    }


def chebi_relation_record(
    relation: JsonObject,
    *,
    direction: str,
    query_id: str,
    query_name: str = "",
    website_base_url: str = CHEBI_WEBSITE_BASE_URL,
) -> JsonObject:
    normalized = normalize_relation(
        relation,
        direction=direction,
        query_id=query_id,
        query_name=query_name,
        website_base_url=website_base_url,
    )
    related_id = normalized["id"]
    title = normalized["name"] or related_id
    links = relation_links(normalized)
    description = f"{normalized['relation_type']} relation for {normalized['query_id']}"
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "ontology.term",
        "record_type": "chebi_ontology_relation",
        "database": "chebi",
        "id": related_id,
        "stable_id": f"ChEBI relation:{normalized['query_id']}:{normalized['relation_type']}:{related_id}",
        "label": title,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "chebi",
        "identifiers": {
            "chebi": {"namespace": "chebi", "id": related_id, "label": related_id, "url": normalized["url"]},
        },
        "links": links,
        "display": {
            "component": "ontology_term",
            "chip_label": related_id,
            "icon": "chebi",
            "title": title,
            "subtitle": relation_subtitle(normalized),
            "description": description,
            "metadata": relation_metadata(normalized),
            "badges": compact_badges(("ChEBI", "source"), (related_id, "identifier"), (normalized["direction"], "context")),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": relation_subtitle(normalized),
                "icon": "chebi",
                "fields": compact_fields(
                    ("ChEBI ID", related_id),
                    ("Name", title),
                    ("Relation", normalized["relation_type"]),
                    ("Direction", normalized["direction"]),
                    ("Query", normalized["query_id"]),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": relation_sections(normalized),
            "previews": relation_previews(normalized, links),
        },
        "related": {"query": normalized["query"], "edge": normalized["edge"]},
        "data": normalized,
    }


def normalize_compound(payload: JsonObject, *, website_base_url: str, api_base_url: str) -> JsonObject:
    row = safe_dict(payload.get("_source")) if isinstance(payload.get("_source"), dict) else payload
    chemical_data = safe_dict(row.get("chemical_data"))
    chebi_id = normalize_chebi_id(row.get("chebi_accession") or row.get("id") or row.get("_id"))
    if not chebi_id and normalize_space(row.get("_id")).isdigit():
        chebi_id = normalize_chebi_id(row.get("_id"))
    names = normalize_names(safe_dict(row.get("names")))
    synonyms = normalize_synonyms(names, row)
    xrefs, citations = normalize_database_accessions(safe_dict(row.get("database_accessions")))
    structure = safe_dict(row.get("default_structure"))
    formula = first_text(row, "formula") or normalize_space(chemical_data.get("formula"))
    mass = first_text(row, "mass") or normalize_space(chemical_data.get("mass"))
    monoisotopic_mass = first_text(row, "monoisotopicmass", "monoisotopic_mass") or normalize_space(chemical_data.get("monoisotopic_mass"))
    url = chebi_page_url(chebi_id, website_base_url)
    return {
        "id": chebi_id,
        "numeric_id": chebi_numeric_id(chebi_id),
        "name": first_text(row, "name", "ascii_name"),
        "ascii_name": first_text(row, "ascii_name", "name"),
        "definition": first_text(row, "definition"),
        "stars": normalize_space(row.get("stars")),
        "formula": formula,
        "mass": mass,
        "monoisotopic_mass": monoisotopic_mass,
        "charge": first_text(row, "charge") or normalize_space(chemical_data.get("charge")),
        "smiles": first_text(row, "smiles") or normalize_space(structure.get("smiles")),
        "inchi": first_text(row, "inchi") or normalize_space(structure.get("standard_inchi") or structure.get("inchi")),
        "inchikey": first_text(row, "inchikey", "inchi_key") or normalize_space(structure.get("standard_inchi_key") or structure.get("inchi_key")),
        "names": names,
        "synonyms": synonyms[:MAX_SYNONYMS],
        "synonyms_truncated": len(synonyms) > MAX_SYNONYMS,
        "secondary_ids": [normalize_chebi_id(item) for item in safe_list(row.get("secondary_ids")) if normalize_space(item)],
        "default_structure": normalize_space(structure.get("id")) or normalize_space(row.get("default_structure")),
        "structures": [normalize_space(item) for item in safe_list(row.get("structures")) if normalize_space(item)],
        "xrefs": xrefs[:MAX_XREFS],
        "xrefs_truncated": len(xrefs) > MAX_XREFS,
        "citations": citations[:20],
        "origins": normalize_origins(safe_list(row.get("compound_origins"))),
        "ontology_relations": safe_dict(row.get("ontology_relations")),
        "is_released": row.get("is_released"),
        "modified_on": normalize_space(row.get("modified_on")),
        "url": url,
        "api_url": f"{api_base_url.rstrip('/')}/chebi/backend/api/public/compound/{chebi_id}/",
        "image_url": chebi_image_url(chebi_id, website_base_url),
        "raw_keys": sorted(str(key) for key in row.keys()),
    }


def normalize_names(groups: JsonObject) -> JsonObject:
    out: JsonObject = {}
    for key, value in groups.items():
        names = []
        for item in safe_list(value):
            if isinstance(item, dict):
                name = normalize_space(item.get("name") or item.get("source_name"))
                if name:
                    names.append(
                        {
                            "name": name,
                            "source": normalize_space(item.get("source") or item.get("source_name")),
                            "type": normalize_space(item.get("type") or key),
                        }
                    )
            else:
                text = normalize_space(item)
                if text:
                    names.append({"name": text, "source": "", "type": key})
        if names:
            out[str(key)] = names
    return out


def normalize_synonyms(names: JsonObject, row: JsonObject) -> list[str]:
    values: list[str] = []
    for key in ["SYNONYM", "IUPAC NAME", "UNIPROT NAME", "BRAND NAME"]:
        for item in safe_list(names.get(key)):
            if isinstance(item, dict):
                text = normalize_space(item.get("name"))
                if text:
                    values.append(text)
    for key in ["synonyms", "secondary_ids"]:
        for item in safe_list(row.get(key)):
            text = normalize_space(item)
            if text:
                values.append(text)
    return unique_texts(values)


def normalize_database_accessions(groups: JsonObject) -> tuple[list[JsonObject], list[JsonObject]]:
    xrefs: list[JsonObject] = []
    citations: list[JsonObject] = []
    for group, items in groups.items():
        for item in safe_list(items):
            if not isinstance(item, dict):
                continue
            identifier = normalize_space(item.get("accession_number") or item.get("accession") or item.get("id"))
            source = normalize_space(item.get("source_name") or item.get("source") or group)
            url = normalize_space(item.get("url"))
            prefix = normalize_space(item.get("prefix"))
            label = normalize_space(item.get("label") or item.get("description")) or ":".join(part for part in [source, identifier] if part)
            record = {
                "database": source or group,
                "category": normalize_space(group),
                "id": identifier,
                "label": label or identifier,
                "url": url,
                "prefix": prefix,
            }
            if group == "CITATION":
                citations.append(record)
            elif identifier or label:
                xrefs.append(record)
    return unique_xrefs(xrefs), unique_xrefs(citations)


def normalize_origins(items: list[Any]) -> list[JsonObject]:
    origins: list[JsonObject] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        origin = {
            "species_text": normalize_space(item.get("species_text") or item.get("species")),
            "source_type": normalize_space(item.get("source_type")),
            "component_text": normalize_space(item.get("component_text")),
            "strain_text": normalize_space(item.get("strain_text")),
        }
        if any(origin.values()):
            origins.append(origin)
    return origins


def normalize_relation(
    relation: JsonObject,
    *,
    direction: str,
    query_id: str,
    query_name: str,
    website_base_url: str,
) -> JsonObject:
    normalized_query_id = normalize_chebi_id(query_id)
    if direction == "children":
        related_id = normalize_chebi_id(relation.get("init_id"))
        related_name = normalize_space(relation.get("init_name"))
        edge_source = related_id
        edge_target = normalized_query_id
    else:
        related_id = normalize_chebi_id(relation.get("final_id"))
        related_name = normalize_space(relation.get("final_name"))
        edge_source = normalized_query_id
        edge_target = related_id
    relation_type = normalize_space(relation.get("relation_type")) or "related to"
    return {
        "id": related_id,
        "numeric_id": chebi_numeric_id(related_id),
        "name": related_name,
        "relation_type": relation_type,
        "direction": direction,
        "query_id": normalized_query_id,
        "query_name": normalize_space(query_name) or normalized_query_id,
        "url": chebi_page_url(related_id, website_base_url),
        "edge": {"source": edge_source, "target": edge_target, "label": relation_type},
        "query": {"id": normalized_query_id, "name": normalize_space(query_name) or normalized_query_id, "url": chebi_page_url(normalized_query_id, website_base_url)},
    }


def compound_subtitle(data: JsonObject) -> str:
    return " | ".join(part for part in [data["id"], data["formula"], data["mass"]] if part)


def relation_subtitle(data: JsonObject) -> str:
    return " | ".join(part for part in [data["relation_type"], data["query_id"], data["direction"]] if part)


def compound_metadata(data: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("ChEBI ID", data["id"]),
        ("Formula", data["formula"]),
        ("Mass", data["mass"]),
        ("Monoisotopic mass", data["monoisotopic_mass"]),
        ("Charge", data["charge"]),
        ("Stars", data["stars"]),
        ("InChIKey", data["inchikey"]),
        ("Synonyms", len(data["synonyms"])),
        ("Cross references", len(data["xrefs"])),
        ("Citations", len(data["citations"])),
    )


def relation_metadata(data: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("ChEBI ID", data["id"]),
        ("Name", data["name"]),
        ("Relation", data["relation_type"]),
        ("Direction", data["direction"]),
        ("Query", data["query_id"]),
    )


def compound_sections(data: JsonObject) -> list[JsonObject]:
    out: list[JsonObject] = [{"key": "overview", "title": "Overview", "kind": "fields", "fields": compound_metadata(data)}]
    if data["definition"]:
        out.append({"key": "definition", "title": "Definition", "kind": "text", "text": data["definition"]})
    if data["synonyms"]:
        out.append({"key": "synonyms", "title": "Synonyms", "kind": "table", "rows": [{"name": item} for item in data["synonyms"]]})
    if data["xrefs"]:
        out.append({"key": "xrefs", "title": "Cross-references", "kind": "table", "rows": data["xrefs"]})
    if data["citations"]:
        out.append({"key": "citations", "title": "Citations", "kind": "table", "rows": data["citations"]})
    if data["origins"]:
        out.append({"key": "origins", "title": "Compound origins", "kind": "table", "rows": data["origins"]})
    return out


def relation_sections(data: JsonObject) -> list[JsonObject]:
    return [
        {"key": "overview", "title": "Relation", "kind": "fields", "fields": relation_metadata(data)},
        {"key": "network", "title": "Relation network", "kind": "network", "summary": data["edge"]},
    ]


def compound_previews(data: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    out: list[JsonObject] = [
        {
            "kind": "table",
            "title": "ChEBI compound details",
            "provider": "ChEBI",
            "id": data["id"],
            "url": data["url"],
            "section_key": "overview",
            "actions": display_actions(links),
            "data": {"columns": ["label", "value"], "rows": compound_metadata(data)},
        }
    ]
    if data["smiles"] or data["inchi"] or data["inchikey"] or data["image_url"]:
        out.append(
            {
                "kind": "chemical_structure",
                "title": "Chemical structure",
                "provider": "ChEBI",
                "id": data["id"],
                "url": data["url"],
                "data": {
                    "smiles": data["smiles"],
                    "inchi": data["inchi"],
                    "inchikey": data["inchikey"],
                    "formula": data["formula"],
                    "image_url": data["image_url"],
                },
            }
        )
    if data["xrefs"]:
        out.append(
            {
                "kind": "xref_groups",
                "title": "Cross-references",
                "provider": "ChEBI",
                "id": data["id"],
                "url": data["url"],
                "section_key": "xrefs",
                "data": {"groups": xref_groups(data["xrefs"])},
            }
        )
    if data["citations"]:
        out.append(
            {
                "kind": "citation_list",
                "title": "Citations",
                "provider": "ChEBI",
                "id": data["id"],
                "url": data["url"],
                "section_key": "citations",
                "data": {"items": data["citations"]},
            }
        )
    if data["definition"]:
        out.append(
            {
                "kind": "text",
                "title": "Definition",
                "provider": "ChEBI",
                "id": data["id"],
                "url": data["url"],
                "section_key": "definition",
                "data": {"text": data["definition"]},
            }
        )
    return out


def relation_previews(data: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    return [
        {
            "kind": "table",
            "title": "ChEBI ontology relation",
            "provider": "ChEBI",
            "id": data["id"],
            "url": data["url"],
            "section_key": "overview",
            "actions": display_actions(links),
            "data": {"columns": ["label", "value"], "rows": relation_metadata(data)},
        },
        {
            "kind": "network",
            "title": "Relation network",
            "provider": "ChEBI",
            "id": data["id"],
            "url": data["url"],
            "section_key": "network",
            "data": {
                "nodes": [
                    {"id": data["query"]["id"], "label": data["query"]["name"], "url": data["query"]["url"], "group": "query"},
                    {"id": data["id"], "label": data["name"] or data["id"], "url": data["url"], "group": "related"},
                ],
                "edges": [data["edge"]],
            },
        },
    ]


def compound_links(data: JsonObject) -> list[JsonObject]:
    return compact_links(
        link("Open ChEBI compound", data["url"], primary=True),
        link("Open ChEBI API record", data["api_url"], kind="api"),
        link("Open ChEBI image", data["image_url"], kind="image"),
    )


def relation_links(data: JsonObject) -> list[JsonObject]:
    return compact_links(
        link("Open ChEBI term", data["url"], primary=True),
        link("Open query term", data["query"]["url"]),
    )


def compound_identifiers(data: JsonObject) -> JsonObject:
    identifiers: JsonObject = {"chebi": {"namespace": "chebi", "id": data["id"], "label": data["id"], "url": data["url"]}}
    if data["inchikey"]:
        identifiers["inchikey"] = {"namespace": "inchikey", "id": data["inchikey"], "label": data["inchikey"]}
    return identifiers


def xref_groups(xrefs: list[JsonObject]) -> list[JsonObject]:
    groups: dict[str, list[JsonObject]] = {}
    for xref in xrefs:
        database = normalize_space(xref.get("database")) or "xref"
        groups.setdefault(database, []).append(xref)
    return [{"database": database, "items": items, "count": len(items)} for database, items in sorted(groups.items())]


def unique_xrefs(items: list[JsonObject]) -> list[JsonObject]:
    seen = set()
    out = []
    for item in items:
        key = (item.get("database"), item.get("category"), item.get("id"), item.get("label"))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def unique_texts(values: list[str]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        normalized = normalize_space(value)
        lowered = normalized.lower()
        if not normalized or lowered in seen:
            continue
        seen.add(lowered)
        out.append(normalized)
    return out


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
