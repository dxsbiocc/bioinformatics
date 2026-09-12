"""Front-end compatible record envelopes for STRING results."""

from __future__ import annotations

import hashlib

from .constants import RECORD_SCHEMA_VERSION, STRING_WEBSITE_BASE_URL, JsonObject
from .utils import normalize_score, normalize_space


EVIDENCE_SCORE_LABELS = {
    "nscore": "Neighborhood",
    "fscore": "Gene fusion",
    "pscore": "Co-occurrence",
    "ascore": "Co-expression",
    "escore": "Experiments",
    "dscore": "Databases",
    "tscore": "Text mining",
}


def string_mapping_record(mapping: JsonObject) -> JsonObject:
    normalized = normalize_mapping(mapping)
    string_id = normalized["string_id"]
    preferred_name = normalized["preferred_name"]
    query_item = normalized["query_item"]
    title = preferred_name or string_id
    url = string_network_url(string_id)
    links = compact_links(
        link("STRING network", url, primary=True),
        link("NCBI Taxonomy", taxonomy_url(normalized["taxid"]), kind="related"),
    )
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "protein.identifier_mapping",
        "record_type": "string_id_mapping",
        "database": "string",
        "id": string_id,
        "stable_id": f"STRING:{string_id}",
        "label": string_id,
        "title": title,
        "description": normalized["annotation"],
        "url": url,
        "icon": "string",
        "identifiers": mapping_identifiers(normalized),
        "links": links,
        "display": {
            "component": "identifier_conversion",
            "chip_label": f"STRING:{preferred_name or string_id}",
            "icon": "string",
            "title": title,
            "subtitle": " | ".join(
                part
                for part in [
                    f"{query_item} -> {string_id}" if query_item else string_id,
                    normalized["taxon_name"],
                ]
                if part
            ),
            "description": normalized["annotation"],
            "metadata": compact_fields(
                ("Query", query_item),
                ("STRING ID", string_id),
                ("Preferred name", preferred_name),
                ("Organism", normalized["taxon_name"]),
                ("TaxID", str(normalized["taxid"]) if normalized["taxid"] else ""),
                ("URL", url),
            ),
            "badges": compact_badges(
                ("STRING", "source"),
                (f"STRING:{string_id}", "identifier"),
                (normalized["taxon_name"], "context"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": normalized["taxon_name"],
                "icon": "string",
                "fields": compact_fields(
                    ("Query", query_item),
                    ("STRING ID", string_id),
                    ("Preferred name", preferred_name),
                    ("Organism", normalized["taxon_name"]),
                    ("TaxID", str(normalized["taxid"]) if normalized["taxid"] else ""),
                    ("URL", url),
                ),
            },
            "primary_url": url,
            "sections": [
                {
                    "key": "overview",
                    "title": "Overview",
                    "kind": "fields",
                    "fields": compact_fields(
                        ("Query", query_item),
                        ("STRING ID", string_id),
                        ("Preferred name", preferred_name),
                        ("Organism", normalized["taxon_name"]),
                        ("TaxID", str(normalized["taxid"]) if normalized["taxid"] else ""),
                    ),
                },
                {
                    "key": "annotation",
                    "title": "Annotation",
                    "kind": "text",
                    "text": normalized["annotation"],
                },
            ],
            "previews": [
                {
                    "kind": "xref_groups",
                    "title": "STRING mapping",
                    "provider": "STRING",
                    "id": string_id,
                    "url": url,
                    "section_key": "overview",
                    "actions": display_actions(links),
                    "data": {
                        "groups": [
                            {
                                "database": "STRING",
                                "items": [
                                    {
                                        "id": string_id,
                                        "label": preferred_name or string_id,
                                        "url": url,
                                    }
                                ],
                            }
                        ],
                    },
                }
            ],
        },
        "related": {
            "query_item": query_item,
            "taxid": normalized["taxid"],
            "string_network": url,
        },
        "data": normalized,
    }


def string_network_record(
    *,
    query: list[str],
    mappings: list[JsonObject],
    interactions: list[JsonObject],
    nodes: list[JsonObject],
    edges: list[JsonObject],
    species: int,
    limit: int,
) -> JsonObject:
    seed_ids = [normalize_space(mapping.get("string_id")) for mapping in mappings]
    seed_ids = [seed_id for seed_id in seed_ids if seed_id]
    seed_labels = [
        normalize_space(mapping.get("preferred_name")) or normalize_space(mapping.get("query_item"))
        for mapping in mappings
    ]
    seed_labels = [label for label in seed_labels if label]
    title = "STRING interaction network"
    if seed_labels:
        title = f"{title}: {', '.join(seed_labels[:4])}"
    primary_id = seed_ids[0] if seed_ids else normalize_space(query[0] if query else "")
    url = string_network_url(primary_id)
    network_id = network_stable_id(seed_ids or query)
    links = compact_links(
        link("STRING network", url, primary=True),
        link("STRING API", f"{STRING_WEBSITE_BASE_URL}/help/api/", kind="related"),
        link("NCBI Taxonomy", taxonomy_url(species), kind="related"),
    )
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "protein.interaction_network",
        "record_type": "string_interaction_network",
        "database": "string",
        "id": network_id,
        "stable_id": f"STRING_NETWORK:{network_id}",
        "label": ", ".join(seed_labels[:4]) or network_id,
        "title": title,
        "description": (
            f"{len(edges)} interactions among {len(nodes)} nodes"
            if edges
            else "No interaction partners returned for the requested identifiers"
        ),
        "url": url,
        "icon": "string",
        "identifiers": network_identifiers(seed_ids, species),
        "links": links,
        "display": {
            "component": "protein_network",
            "chip_label": "STRING network",
            "icon": "string",
            "title": title,
            "subtitle": f"{len(nodes)} nodes | {len(edges)} interactions | TaxID {species}",
            "description": (
                "STRING protein-protein association network with combined "
                "and evidence-channel scores."
            ),
            "metadata": compact_fields(
                ("Seeds", ", ".join(seed_labels[:8]) or ", ".join(query[:8])),
                ("Species TaxID", str(species)),
                ("Mapped seeds", str(len(mappings))),
                ("Nodes", str(len(nodes))),
                ("Interactions", str(len(edges))),
                ("Limit", str(limit)),
                ("Top score", score_range_text(edges, "max")),
                ("Lowest score", score_range_text(edges, "min")),
            ),
            "badges": compact_badges(
                ("STRING", "source"),
                ("protein network", "record_type"),
                (f"{len(edges)} edges", "count"),
                (f"TaxID:{species}", "context"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": f"{len(nodes)} nodes | {len(edges)} interactions",
                "icon": "string",
                "fields": compact_fields(
                    ("Seeds", ", ".join(seed_labels[:8]) or ", ".join(query[:8])),
                    ("Species TaxID", str(species)),
                    ("Mapped seeds", str(len(mappings))),
                    ("Nodes", str(len(nodes))),
                    ("Interactions", str(len(edges))),
                    ("URL", url),
                ),
            },
            "primary_url": url,
            "sections": network_sections(
                mappings=mappings,
                nodes=nodes,
                edges=edges,
            ),
            "previews": [
                {
                    "kind": "network",
                    "title": "Protein interaction network",
                    "provider": "STRING",
                    "id": network_id,
                    "url": url,
                    "section_key": "network",
                    "actions": display_actions(links),
                    "data": {
                        "source": "STRING",
                        "layout": "force",
                        "species": species,
                        "seeds": seed_ids,
                        "nodes": nodes,
                        "edges": edges,
                        "score_fields": evidence_score_fields(),
                    },
                },
                {
                    "kind": "table",
                    "title": "Top interactions",
                    "provider": "STRING",
                    "id": network_id,
                    "section_key": "interactions",
                    "data": {
                        "columns": interaction_columns(),
                        "rows": edges,
                    },
                },
            ],
        },
        "related": {
            "mappings": mappings,
            "seed_string_ids": seed_ids,
            "taxid": species,
        },
        "data": {
            "query": query,
            "mappings": mappings,
            "interactions": interactions,
            "nodes": nodes,
            "edges": edges,
        },
    }


def normalize_mapping(mapping: JsonObject) -> JsonObject:
    taxid = mapping.get("ncbiTaxonId")
    return {
        "query_index": mapping.get("queryIndex", ""),
        "query_item": normalize_space(mapping.get("queryItem")),
        "string_id": normalize_space(mapping.get("stringId")),
        "taxid": taxid if taxid is not None else "",
        "taxon_name": normalize_space(mapping.get("taxonName")),
        "preferred_name": normalize_space(mapping.get("preferredName")),
        "annotation": normalize_space(mapping.get("annotation")),
    }


def normalize_interaction(interaction: JsonObject) -> JsonObject:
    evidence_scores = {
        key: normalize_score(interaction.get(key))
        for key in EVIDENCE_SCORE_LABELS
        if interaction.get(key) not in {"", None}
    }
    return {
        "source": normalize_space(interaction.get("stringId_A")),
        "target": normalize_space(interaction.get("stringId_B")),
        "source_label": normalize_space(interaction.get("preferredName_A")),
        "target_label": normalize_space(interaction.get("preferredName_B")),
        "taxid": interaction.get("ncbiTaxonId") if interaction.get("ncbiTaxonId") is not None else "",
        "score": normalize_score(interaction.get("score")),
        "evidence_scores": evidence_scores,
        "score_label": score_label(interaction.get("score")),
    }


def build_network_nodes(
    mappings: list[JsonObject],
    edges: list[JsonObject],
) -> list[JsonObject]:
    nodes: dict[str, JsonObject] = {}
    for mapping in mappings:
        string_id = normalize_space(mapping.get("string_id"))
        if not string_id:
            continue
        nodes[string_id] = {
            "id": string_id,
            "label": normalize_space(mapping.get("preferred_name")) or string_id,
            "role": "query",
            "database": "STRING",
            "taxid": mapping.get("taxid", ""),
            "taxon_name": normalize_space(mapping.get("taxon_name")),
            "query_item": normalize_space(mapping.get("query_item")),
            "annotation": normalize_space(mapping.get("annotation")),
            "url": string_network_url(string_id),
        }
    for edge in edges:
        for id_key, label_key in [
            ("source", "source_label"),
            ("target", "target_label"),
        ]:
            string_id = normalize_space(edge.get(id_key))
            if not string_id:
                continue
            existing = nodes.get(string_id)
            if existing:
                if normalize_space(edge.get(label_key)) and not normalize_space(existing.get("label")):
                    existing["label"] = normalize_space(edge.get(label_key))
                continue
            nodes[string_id] = {
                "id": string_id,
                "label": normalize_space(edge.get(label_key)) or string_id,
                "role": "interactor",
                "database": "STRING",
                "taxid": edge.get("taxid", ""),
                "url": string_network_url(string_id),
            }
    return list(nodes.values())


def network_sections(
    *,
    mappings: list[JsonObject],
    nodes: list[JsonObject],
    edges: list[JsonObject],
) -> list[JsonObject]:
    return [
        {
            "key": "overview",
            "title": "Overview",
            "kind": "fields",
            "fields": compact_fields(
                ("Mapped seeds", str(len(mappings))),
                ("Nodes", str(len(nodes))),
                ("Interactions", str(len(edges))),
                ("Evidence fields", ", ".join(EVIDENCE_SCORE_LABELS.values())),
            ),
        },
        {
            "key": "network",
            "title": "Network",
            "kind": "network",
            "summary": {
                "nodes": len(nodes),
                "edges": len(edges),
            },
            "items": nodes,
            "rows": edges,
        },
        {
            "key": "interactions",
            "title": "Interactions",
            "kind": "table",
            "summary": {
                "columns": interaction_columns(),
                "score_fields": evidence_score_fields(),
            },
            "rows": edges,
        },
        {
            "key": "mappings",
            "title": "Identifier mappings",
            "kind": "table",
            "rows": mappings,
        },
    ]


def mapping_identifiers(normalized: JsonObject) -> JsonObject:
    identifiers: JsonObject = {
        "string": {
            "namespace": "string",
            "id": normalized["string_id"],
            "label": f"STRING:{normalized['string_id']}",
            "url": string_network_url(normalized["string_id"]),
        }
    }
    taxid = normalized.get("taxid")
    if taxid:
        identifiers["taxonomy"] = {
            "namespace": "taxonomy",
            "id": str(taxid),
            "label": f"TaxID:{taxid}",
            "url": taxonomy_url(taxid),
        }
    query_item = normalize_space(normalized.get("query_item"))
    if query_item:
        identifiers["query"] = {
            "namespace": "query",
            "id": query_item,
            "label": query_item,
        }
    return identifiers


def network_identifiers(seed_ids: list[str], species: int) -> JsonObject:
    identifiers: JsonObject = {
        "taxonomy": {
            "namespace": "taxonomy",
            "id": str(species),
            "label": f"TaxID:{species}",
            "url": taxonomy_url(species),
        }
    }
    if seed_ids:
        identifiers["string"] = [
            {
                "namespace": "string",
                "id": seed_id,
                "label": f"STRING:{seed_id}",
                "url": string_network_url(seed_id),
            }
            for seed_id in seed_ids
        ]
    return identifiers


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


def evidence_score_fields() -> list[JsonObject]:
    return [
        {
            "key": key,
            "label": label,
        }
        for key, label in EVIDENCE_SCORE_LABELS.items()
    ]


def interaction_columns() -> list[JsonObject]:
    return [
        {"key": "source_label", "label": "Source"},
        {"key": "target_label", "label": "Target"},
        {"key": "score", "label": "Combined score"},
        {"key": "score_label", "label": "Confidence"},
    ]


def score_range_text(edges: list[JsonObject], mode: str) -> str:
    values = [
        edge.get("score")
        for edge in edges
        if isinstance(edge.get("score"), (int, float))
    ]
    if not values:
        return ""
    value = max(values) if mode == "max" else min(values)
    return f"{value:.3f}".rstrip("0").rstrip(".")


def score_label(score: object) -> str:
    normalized = normalize_score(score)
    if not isinstance(normalized, (int, float)):
        return ""
    if normalized >= 0.9:
        return "highest confidence"
    if normalized >= 0.7:
        return "high confidence"
    if normalized >= 0.4:
        return "medium confidence"
    return "low confidence"


def network_stable_id(values: list[str]) -> str:
    seed = "\n".join(normalize_space(value) for value in values if normalize_space(value))
    if not seed:
        return "empty"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    first = normalize_space(values[0]).replace(":", "_").replace(".", "_")[:40]
    return f"{first}-{digest}"


def string_network_url(string_id: object) -> str:
    value = normalize_space(string_id)
    return f"{STRING_WEBSITE_BASE_URL}/network/{value}" if value else ""


def taxonomy_url(taxid: object) -> str:
    value = normalize_space(taxid)
    return (
        "https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id="
        f"{value}"
    ) if value else ""

