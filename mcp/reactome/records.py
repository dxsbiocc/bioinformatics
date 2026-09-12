"""Front-end compatible record envelopes for Reactome pathways and events."""

from __future__ import annotations

from .constants import (
    MAX_PREVIEW_PARTICIPANTS,
    RECORD_SCHEMA_VERSION,
    REACTOME_CONTENT_API_BASE_URL,
    REACTOME_WEBSITE_BASE_URL,
    JsonObject,
)
from .utils import clean_html, first_text, normalize_space


def reactome_pathway_record(
    event: JsonObject,
    *,
    participants: list[JsonObject] | None = None,
    search_score: object = "",
    mapping_resource: str = "",
    query_identifier: str = "",
) -> JsonObject:
    normalized = normalize_event(
        event,
        participants=participants or [],
        search_score=search_score,
        mapping_resource=mapping_resource,
        query_identifier=query_identifier,
    )
    stable_id = normalized["stable_id"]
    title = normalized["display_name"] or stable_id
    links = pathway_links(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "pathway",
        "record_type": "reactome_pathway"
        if normalized["schema_class"].lower() == "pathway"
        else "reactome_event",
        "database": "reactome",
        "id": stable_id or str(normalized["db_id"]),
        "stable_id": f"Reactome:{stable_id}" if stable_id else f"ReactomeDB:{normalized['db_id']}",
        "label": stable_id or str(normalized["db_id"]),
        "title": title,
        "description": normalized["summary"],
        "url": normalized["url"],
        "icon": "reactome",
        "identifiers": pathway_identifiers(normalized),
        "links": links,
        "display": {
            "component": "pathway",
            "chip_label": stable_id or title,
            "icon": "reactome",
            "title": title,
            "subtitle": " | ".join(
                part
                for part in [
                    stable_id,
                    normalized["species_name"],
                    normalized["schema_class"],
                ]
                if part
            ),
            "description": normalized["summary"],
            "metadata": pathway_metadata(normalized),
            "badges": compact_badges(
                ("Reactome", "source"),
                (stable_id, "identifier"),
                (normalized["schema_class"], "record_type"),
                (normalized["species_name"], "context"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": " | ".join(
                    part
                    for part in [
                        stable_id,
                        normalized["species_name"],
                        normalized["schema_class"],
                    ]
                    if part
                ),
                "icon": "reactome",
                "fields": compact_fields(
                    ("Reactome ID", stable_id),
                    ("DB ID", str(normalized["db_id"]) if normalized["db_id"] else ""),
                    ("Class", normalized["schema_class"]),
                    ("Species", normalized["species_name"]),
                    ("Participants", str(len(normalized["participants"]))),
                    ("Child events", str(len(normalized["child_events"]))),
                    ("References", str(len(normalized["references"]))),
                    ("Has diagram", yes_no(normalized["has_diagram"])),
                    ("Disease", yes_no(normalized["is_disease"]) if normalized["is_disease"] else ""),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": pathway_sections(normalized),
            "previews": pathway_previews(normalized, links),
        },
        "related": {
            "participants": normalized["participants"],
            "references": normalized["references"],
            "child_events": normalized["child_events"],
            "mapping": normalized["mapping"],
        },
        "data": normalized,
    }


def normalize_event(
    event: JsonObject,
    *,
    participants: list[JsonObject],
    search_score: object,
    mapping_resource: str,
    query_identifier: str,
) -> JsonObject:
    stable_id = normalize_space(event.get("stId") or event.get("id"))
    db_id = event.get("dbId", "")
    species_name = normalize_species_name(event)
    references = normalize_references(event.get("literatureReference"))
    normalized_participants = [normalize_participant(item) for item in participants]
    normalized_participants = [item for item in normalized_participants if item.get("label")]
    child_events = normalize_child_events(event.get("hasEvent"))
    summary = first_summary(event)
    return {
        "db_id": db_id if db_id is not None else "",
        "stable_id": stable_id,
        "stable_id_version": normalize_space(event.get("stIdVersion")),
        "display_name": clean_html(event.get("displayName")) or first_text(event.get("name")),
        "names": [clean_html(item) for item in event.get("name", []) if clean_html(item)]
        if isinstance(event.get("name"), list)
        else [],
        "schema_class": clean_html(event.get("schemaClass") or event.get("type") or event.get("exactType")),
        "class_name": clean_html(event.get("className")),
        "species_name": species_name,
        "summary": summary,
        "summaries": summaries(event.get("summation")),
        "has_diagram": bool(event.get("hasDiagram")),
        "has_ehld": bool(event.get("hasEHLD")),
        "is_disease": bool(event.get("isInDisease") or event.get("isDisease")),
        "is_inferred": bool(event.get("isInferred")),
        "release_date": normalize_space(event.get("releaseDate")),
        "last_updated_date": normalize_space(event.get("lastUpdatedDate")),
        "doi": normalize_space(event.get("doi")),
        "go_biological_process": normalize_go_terms(event.get("goBiologicalProcess")),
        "child_events": child_events,
        "participants": normalized_participants,
        "participant_count": len(normalized_participants),
        "references": references,
        "reference_count": len(references),
        "search_score": search_score if search_score not in {None, ""} else "",
        "mapping": {
            "resource": mapping_resource,
            "identifier": query_identifier,
        }
        if mapping_resource or query_identifier
        else {},
        "url": reactome_detail_url(stable_id, db_id),
        "pathway_browser_url": reactome_browser_url(stable_id),
        "api_url": reactome_api_url(stable_id),
    }


def normalize_species_name(event: JsonObject) -> str:
    species_name = clean_html(event.get("speciesName"))
    if species_name:
        return species_name
    species = event.get("species")
    if isinstance(species, list):
        for item in species:
            if isinstance(item, dict):
                text = clean_html(item.get("displayName") or item.get("name"))
            else:
                text = clean_html(item)
            if text:
                return text
    if isinstance(species, dict):
        return clean_html(species.get("displayName") or species.get("name"))
    return ""


def first_summary(event: JsonObject) -> str:
    values = summaries(event.get("summation"))
    if values:
        return values[0]
    return clean_html(event.get("summation")) or clean_html(event.get("summary"))


def summaries(value: object) -> list[str]:
    if not isinstance(value, list):
        text = clean_html(value)
        return [text] if text else []
    normalized = []
    for item in value:
        if isinstance(item, dict):
            text = clean_html(item.get("text") or item.get("displayName"))
        else:
            text = clean_html(item)
        if text:
            normalized.append(text)
    return normalized


def normalize_participant(item: object) -> JsonObject:
    if not isinstance(item, dict):
        return {}
    pe_db_id = item.get("peDbId") or item.get("dbId") or ""
    label = clean_html(item.get("displayName") or item.get("name"))
    ref_entities = normalize_reference_entities(item.get("refEntities"))
    primary_ref = ref_entities[0] if ref_entities else {}
    node_id = str(pe_db_id) if pe_db_id else label
    return {
        "id": node_id,
        "pe_db_id": pe_db_id,
        "stable_id": normalize_space(item.get("stId")),
        "label": label,
        "schema_class": clean_html(item.get("schemaClass")),
        "species_name": clean_html(item.get("speciesName")),
        "reference_identifier": normalize_space(primary_ref.get("identifier")),
        "reference_label": clean_html(primary_ref.get("display_name")),
        "reference_url": normalize_space(primary_ref.get("url")),
        "reference_entities": ref_entities,
    }


def normalize_reference_entities(value: object) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    refs = []
    for item in value:
        if not isinstance(item, dict):
            continue
        refs.append(
            {
                "db_id": item.get("dbId", ""),
                "stable_id": normalize_space(item.get("stId")),
                "identifier": normalize_space(item.get("identifier")),
                "schema_class": clean_html(item.get("schemaClass")),
                "display_name": clean_html(item.get("displayName")),
                "icon": normalize_space(item.get("icon")),
                "url": normalize_space(item.get("url")),
            }
        )
    return refs


def normalize_references(value: object) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    references = []
    for item in value:
        if not isinstance(item, dict):
            continue
        pmid = item.get("pubMedIdentifier") or item.get("pmid") or ""
        title = clean_html(item.get("title") or item.get("displayName"))
        url = normalize_space(item.get("url")) or pubmed_url(pmid)
        references.append(
            {
                "db_id": item.get("dbId", ""),
                "pmid": str(pmid) if pmid else "",
                "title": title,
                "journal": clean_html(item.get("journal")),
                "year": str(item.get("year")) if item.get("year") else "",
                "volume": str(item.get("volume")) if item.get("volume") else "",
                "pages": clean_html(item.get("pages")),
                "url": url,
            }
        )
    return references


def normalize_child_events(value: object) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    events = []
    for item in value:
        if not isinstance(item, dict):
            continue
        stable_id = normalize_space(item.get("stId"))
        db_id = item.get("dbId", "")
        events.append(
            {
                "db_id": db_id,
                "stable_id": stable_id,
                "display_name": clean_html(item.get("displayName")),
                "schema_class": clean_html(item.get("schemaClass")),
                "species_name": clean_html(item.get("speciesName")),
                "url": reactome_detail_url(stable_id, db_id),
            }
        )
    return events


def normalize_go_terms(value: object) -> list[JsonObject]:
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []
    terms = []
    for item in value:
        if not isinstance(item, dict):
            continue
        accession = normalize_space(item.get("accession"))
        terms.append(
            {
                "accession": accession,
                "display_name": clean_html(item.get("displayName")),
                "url": f"https://amigo.geneontology.org/amigo/term/{accession}" if accession else "",
            }
        )
    return terms


def pathway_identifiers(normalized: JsonObject) -> JsonObject:
    stable_id = normalize_space(normalized.get("stable_id"))
    identifiers: JsonObject = {}
    if stable_id:
        identifiers["reactome"] = {
            "namespace": "reactome",
            "id": stable_id,
            "label": f"Reactome:{stable_id}",
            "url": reactome_detail_url(stable_id, normalized.get("db_id", "")),
        }
    db_id = normalized.get("db_id")
    if db_id:
        identifiers["reactome_db_id"] = {
            "namespace": "reactome_db_id",
            "id": str(db_id),
            "label": f"ReactomeDB:{db_id}",
            "url": reactome_detail_url(stable_id, db_id),
        }
    return identifiers


def pathway_links(normalized: JsonObject) -> list[JsonObject]:
    stable_id = normalize_space(normalized.get("stable_id"))
    return compact_links(
        link("Reactome detail", reactome_detail_url(stable_id, normalized.get("db_id", "")), primary=True),
        link("Pathway Browser", reactome_browser_url(stable_id), kind="related"),
        link("ContentService API", reactome_api_url(stable_id), kind="related"),
    )


def pathway_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Reactome ID", normalize_space(normalized.get("stable_id"))),
        ("DB ID", str(normalized.get("db_id")) if normalized.get("db_id") else ""),
        ("Class", normalize_space(normalized.get("schema_class"))),
        ("Species", normalize_space(normalized.get("species_name"))),
        ("Participants", str(len(normalized.get("participants", [])))),
        ("Child events", str(len(normalized.get("child_events", [])))),
        ("References", str(len(normalized.get("references", [])))),
        ("Released", normalize_space(normalized.get("release_date"))),
        ("Updated", normalize_space(normalized.get("last_updated_date"))),
    )


def pathway_sections(normalized: JsonObject) -> list[JsonObject]:
    return [
        {
            "key": "overview",
            "title": "Overview",
            "kind": "fields",
            "fields": pathway_metadata(normalized),
        },
        {
            "key": "summary",
            "title": "Summary",
            "kind": "text",
            "text": normalize_space(normalized.get("summary")),
        },
        {
            "key": "participants",
            "title": "Participants",
            "kind": "table",
            "summary": {
                "rows": len(normalized.get("participants", [])),
                "truncated": len(normalized.get("participants", [])) > MAX_PREVIEW_PARTICIPANTS,
            },
            "rows": normalized.get("participants", []),
        },
        {
            "key": "child_events",
            "title": "Child events",
            "kind": "table",
            "rows": normalized.get("child_events", []),
        },
        {
            "key": "references",
            "title": "References",
            "kind": "table",
            "rows": normalized.get("references", []),
        },
    ]


def pathway_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    participants = normalized.get("participants", [])
    references = normalized.get("references", [])
    preview_participants = participants[:MAX_PREVIEW_PARTICIPANTS]
    previews: list[JsonObject] = [
        {
            "kind": "network",
            "title": "Pathway participants",
            "provider": "Reactome",
            "id": normalize_space(normalized.get("stable_id")),
            "url": normalize_space(normalized.get("pathway_browser_url")) or normalize_space(normalized.get("url")),
            "section_key": "participants",
            "actions": display_actions(links),
            "data": {
                "source": "Reactome",
                "layout": "pathway",
                "nodes": pathway_network_nodes(normalized, preview_participants),
                "edges": pathway_network_edges(normalized, preview_participants),
                "total_participants": len(participants),
                "truncated": len(participants) > len(preview_participants),
            },
        },
        {
            "kind": "table",
            "title": "Participants",
            "provider": "Reactome",
            "id": normalize_space(normalized.get("stable_id")),
            "section_key": "participants",
            "data": {
                "columns": participant_columns(),
                "rows": preview_participants,
                "total_rows": len(participants),
                "truncated": len(participants) > len(preview_participants),
            },
        },
    ]
    if references:
        previews.append(
            {
                "kind": "citation_list",
                "title": "Pathway references",
                "provider": "Reactome",
                "id": normalize_space(normalized.get("stable_id")),
                "section_key": "references",
                "data": {
                    "citations": references,
                },
            }
        )
    previews.append(
        {
            "kind": "xref_groups",
            "title": "Reactome identifiers",
            "provider": "Reactome",
            "id": normalize_space(normalized.get("stable_id")),
            "url": normalize_space(normalized.get("url")),
            "section_key": "overview",
            "actions": display_actions(links),
            "data": {
                "groups": [
                    {
                        "database": "Reactome",
                        "items": [
                            {
                                "id": normalize_space(normalized.get("stable_id")),
                                "label": f"Reactome:{normalize_space(normalized.get('stable_id'))}",
                                "url": normalize_space(normalized.get("url")),
                            }
                        ],
                    }
                ],
            },
        }
    )
    return previews


def pathway_network_nodes(normalized: JsonObject, participants: list[JsonObject]) -> list[JsonObject]:
    pathway_id = normalize_space(normalized.get("stable_id")) or str(normalized.get("db_id"))
    nodes = [
        {
            "id": pathway_id,
            "label": normalize_space(normalized.get("display_name")) or pathway_id,
            "role": "pathway",
            "database": "Reactome",
            "url": normalize_space(normalized.get("url")),
        }
    ]
    for participant in participants:
        node_id = participant_node_id(participant)
        nodes.append(
            {
                "id": node_id,
                "label": normalize_space(participant.get("label")) or node_id,
                "role": "participant",
                "database": "Reactome",
                "schema_class": normalize_space(participant.get("schema_class")),
                "reference_identifier": normalize_space(participant.get("reference_identifier")),
                "url": normalize_space(participant.get("reference_url")),
            }
        )
    return nodes


def pathway_network_edges(normalized: JsonObject, participants: list[JsonObject]) -> list[JsonObject]:
    pathway_id = normalize_space(normalized.get("stable_id")) or str(normalized.get("db_id"))
    return [
        {
            "source": pathway_id,
            "target": participant_node_id(participant),
            "type": "has_participant",
            "label": "participant",
        }
        for participant in participants
    ]


def participant_node_id(participant: JsonObject) -> str:
    value = (
        normalize_space(participant.get("reference_identifier"))
        or normalize_space(participant.get("stable_id"))
        or normalize_space(participant.get("id"))
        or normalize_space(participant.get("label"))
    )
    return value or "participant"


def participant_columns() -> list[JsonObject]:
    return [
        {"key": "label", "label": "Participant"},
        {"key": "schema_class", "label": "Class"},
        {"key": "reference_identifier", "label": "Reference ID"},
        {"key": "reference_label", "label": "Reference"},
    ]


def compact_fields(*fields: tuple[str, str | None]) -> list[JsonObject]:
    return [
        {"label": label, "value": value}
        for label, value in fields
        if value
    ]


def compact_badges(*badges: tuple[str | None, str]) -> list[JsonObject]:
    return [
        {"label": label, "kind": kind}
        for label, kind in badges
        if label
    ]


def compact_links(*links: JsonObject) -> list[JsonObject]:
    return [
        item
        for item in links
        if normalize_space(item.get("label")) and normalize_space(item.get("url"))
    ]


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


def link(
    label: str,
    url: str,
    *,
    kind: str = "external",
    primary: bool = False,
) -> JsonObject:
    return {
        "label": label,
        "url": normalize_space(url),
        "kind": kind,
        "primary": primary,
    }


def yes_no(value: object) -> str:
    return "yes" if bool(value) else "no"


def reactome_detail_url(stable_id: object, db_id: object = "") -> str:
    value = normalize_space(stable_id) or normalize_space(db_id)
    return f"{REACTOME_WEBSITE_BASE_URL}/content/detail/{value}" if value else REACTOME_WEBSITE_BASE_URL


def reactome_browser_url(stable_id: object) -> str:
    value = normalize_space(stable_id)
    return f"{REACTOME_WEBSITE_BASE_URL}/PathwayBrowser/#/{value}" if value else REACTOME_WEBSITE_BASE_URL


def reactome_api_url(stable_id: object) -> str:
    value = normalize_space(stable_id)
    return f"{REACTOME_CONTENT_API_BASE_URL}/data/query/{value}" if value else REACTOME_CONTENT_API_BASE_URL


def pubmed_url(pmid: object) -> str:
    value = normalize_space(pmid)
    return f"https://pubmed.ncbi.nlm.nih.gov/{value}/" if value else ""

