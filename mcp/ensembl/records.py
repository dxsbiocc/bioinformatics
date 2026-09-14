"""Front-end compatible record envelopes for Ensembl results."""

from __future__ import annotations

from .constants import (
    ENSEMBL_REST_BASE_URL,
    ENSEMBL_WEBSITE_BASE_URL,
    MAX_TRANSCRIPTS,
    RECORD_SCHEMA_VERSION,
    JsonObject,
)
from .utils import ensembl_species_path, normalize_space, species_label


def ensembl_feature_record(
    feature: JsonObject,
    *,
    xrefs: list[JsonObject] | None = None,
    source_region: str = "",
) -> JsonObject:
    normalized = normalize_feature(feature, xrefs=xrefs or [], source_region=source_region)
    stable_id = normalized["id"]
    title = normalized["display_name"] or stable_id
    component = "gene" if normalized["object_type"].lower() == "gene" else "genomic_feature"
    links = feature_links(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "gene" if component == "gene" else "genomic.feature",
        "record_type": f"ensembl_{normalized['object_type'].lower() or 'feature'}",
        "database": "ensembl",
        "id": stable_id,
        "stable_id": f"Ensembl:{stable_id}",
        "label": title,
        "title": title,
        "description": normalized["description"],
        "url": normalized["url"],
        "icon": "ensembl",
        "identifiers": feature_identifiers(normalized),
        "links": links,
        "display": {
            "component": component,
            "chip_label": title,
            "icon": "ensembl",
            "title": title,
            "subtitle": " | ".join(
                part
                for part in [
                    stable_id,
                    normalized["species_label"],
                    normalized["location"],
                    normalized["biotype"],
                ]
                if part
            ),
            "description": normalized["description"],
            "metadata": feature_metadata(normalized),
            "badges": compact_badges(
                ("Ensembl", "source"),
                (stable_id, "identifier"),
                (normalized["object_type"], "record_type"),
                (normalized["assembly_name"], "assembly"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": " | ".join(
                    part
                    for part in [
                        stable_id,
                        normalized["species_label"],
                        normalized["location"],
                    ]
                    if part
                ),
                "icon": "ensembl",
                "fields": compact_fields(
                    ("Ensembl ID", stable_id),
                    ("Name", normalized["display_name"]),
                    ("Type", normalized["object_type"]),
                    ("Biotype", normalized["biotype"]),
                    ("Species", normalized["species_label"]),
                    ("Assembly", normalized["assembly_name"]),
                    ("Location", normalized["location"]),
                    ("Strand", strand_text(normalized["strand"])),
                    ("Canonical transcript", normalized["canonical_transcript"]),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": feature_sections(normalized),
            "previews": feature_previews(normalized, links),
        },
        "related": {
            "xrefs": normalized["xrefs"],
            "transcripts": normalized["transcripts"],
            "source_region": source_region,
        },
        "data": normalized,
    }


def ensembl_xrefs_record(ensembl_id: str, xrefs: list[JsonObject], *, total: int) -> JsonObject:
    normalized = [normalize_xref(item) for item in xrefs]
    normalized = [item for item in normalized if item.get("database") or item.get("display_id")]
    url = ensembl_id_url(ensembl_id)
    links = compact_links(
        link("Ensembl record", url, primary=True),
        link("REST xrefs", ensembl_xrefs_api_url(ensembl_id), kind="related"),
    )
    groups = xref_groups(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "identifier.mapping",
        "record_type": "ensembl_xrefs",
        "database": "ensembl",
        "id": ensembl_id,
        "stable_id": f"Ensembl:{ensembl_id}:xrefs",
        "label": f"{ensembl_id} xrefs",
        "title": f"Ensembl cross-references for {ensembl_id}",
        "description": f"{len(normalized)} of {total} cross-references returned",
        "url": url,
        "icon": "ensembl",
        "identifiers": {
            "ensembl": {
                "namespace": "ensembl",
                "id": ensembl_id,
                "label": f"Ensembl:{ensembl_id}",
                "url": url,
            }
        },
        "links": links,
        "display": {
            "component": "identifier_conversion",
            "chip_label": f"{ensembl_id} xrefs",
            "icon": "ensembl",
            "title": f"Cross-references for {ensembl_id}",
            "subtitle": f"{len(normalized)} shown | {total} total",
            "description": "External database references returned by Ensembl.",
            "metadata": compact_fields(
                ("Ensembl ID", ensembl_id),
                ("Shown", str(len(normalized))),
                ("Total", str(total)),
                ("Truncated", "yes" if total > len(normalized) else ""),
            ),
            "badges": compact_badges(
                ("Ensembl", "source"),
                ("cross-reference", "record_type"),
                (f"{len(groups)} groups", "count"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": f"Cross-references for {ensembl_id}",
                "subtitle": f"{len(normalized)} shown | {total} total",
                "icon": "ensembl",
                "fields": compact_fields(
                    ("Ensembl ID", ensembl_id),
                    ("Shown", str(len(normalized))),
                    ("Total", str(total)),
                    ("URL", url),
                ),
            },
            "primary_url": url,
            "sections": [
                {
                    "key": "xrefs",
                    "title": "Cross-references",
                    "kind": "table",
                    "summary": {"total": total, "shown": len(normalized), "truncated": total > len(normalized)},
                    "rows": normalized,
                }
            ],
            "previews": [
                {
                    "kind": "xref_groups",
                    "title": "Cross-reference groups",
                    "provider": "Ensembl",
                    "id": ensembl_id,
                    "url": url,
                    "section_key": "xrefs",
                    "actions": display_actions(links),
                    "data": {"groups": groups, "total": total, "truncated": total > len(normalized)},
                },
                {
                    "kind": "table",
                    "title": "Cross-references",
                    "provider": "Ensembl",
                    "id": ensembl_id,
                    "section_key": "xrefs",
                    "data": {
                        "columns": xref_columns(),
                        "rows": normalized,
                        "total_rows": total,
                        "truncated": total > len(normalized),
                    },
                },
            ],
        },
        "related": {"xrefs": normalized},
        "data": {"ensembl_id": ensembl_id, "xrefs": normalized, "total": total},
    }


def ensembl_variant_record(variant: JsonObject, *, species: str, source_region: str = "") -> JsonObject:
    normalized = normalize_variant(variant, species=species, source_region=source_region)
    variant_id = normalized["id"]
    title = variant_id
    links = variant_links(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "genomic.variant",
        "record_type": "ensembl_variant",
        "database": "ensembl",
        "id": variant_id,
        "stable_id": f"EnsemblVariant:{variant_id}",
        "label": variant_id,
        "title": title,
        "description": variant_description(normalized),
        "url": normalized["url"],
        "icon": "ensembl",
        "identifiers": variant_identifiers(normalized),
        "links": links,
        "display": {
            "component": "variant",
            "chip_label": variant_id,
            "icon": "ensembl",
            "title": title,
            "subtitle": " | ".join(
                part
                for part in [
                    normalized["var_class"],
                    normalized["most_severe_consequence"],
                    normalized["primary_location"],
                ]
                if part
            ),
            "description": variant_description(normalized),
            "metadata": variant_metadata(normalized),
            "badges": compact_badges(
                ("Ensembl", "source"),
                (variant_id, "identifier"),
                (normalized["var_class"], "variant_class"),
                (normalized["most_severe_consequence"], "consequence"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": variant_description(normalized),
                "icon": "ensembl",
                "fields": compact_fields(
                    ("Variant", variant_id),
                    ("Class", normalized["var_class"]),
                    ("Most severe consequence", normalized["most_severe_consequence"]),
                    ("Location", normalized["primary_location"]),
                    ("Alleles", normalized["allele_string"]),
                    ("Clinical significance", ", ".join(normalized["clinical_significance"])),
                    ("Evidence", ", ".join(normalized["evidence"][:8])),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": variant_sections(normalized),
            "previews": variant_previews(normalized, links),
        },
        "related": {
            "mappings": normalized["mappings"],
            "synonyms": normalized["synonyms"],
            "evidence": normalized["evidence"],
        },
        "data": normalized,
    }


def normalize_feature(
    feature: JsonObject,
    *,
    xrefs: list[JsonObject],
    source_region: str,
) -> JsonObject:
    object_type = normalize_space(feature.get("object_type") or feature.get("feature_type") or "feature")
    species = normalize_space(feature.get("species")) or "homo_sapiens"
    transcripts = normalize_transcripts(feature.get("Transcript"))
    normalized_xrefs = [normalize_xref(item) for item in xrefs]
    normalized_xrefs = [item for item in normalized_xrefs if item.get("database") or item.get("display_id")]
    stable_id = normalize_space(feature.get("id"))
    return {
        "id": stable_id,
        "display_name": normalize_space(feature.get("display_name") or feature.get("external_name")),
        "description": normalize_space(feature.get("description")),
        "object_type": object_type,
        "species": species,
        "species_label": species_label(species),
        "seq_region_name": normalize_space(feature.get("seq_region_name")),
        "start": feature.get("start", ""),
        "end": feature.get("end", ""),
        "strand": feature.get("strand", ""),
        "location": feature_location(feature),
        "assembly_name": normalize_space(feature.get("assembly_name")),
        "version": feature.get("version", ""),
        "biotype": normalize_space(feature.get("biotype")),
        "source": normalize_space(feature.get("source")),
        "canonical_transcript": normalize_space(feature.get("canonical_transcript")),
        "transcripts": transcripts,
        "transcript_count": len(transcripts),
        "xrefs": normalized_xrefs,
        "source_region": source_region,
        "url": ensembl_feature_url(stable_id, object_type, species),
        "location_url": ensembl_location_url(species, feature),
        "api_url": ensembl_lookup_api_url(stable_id),
    }


def normalize_transcripts(value: object) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    transcripts = []
    for item in value[:MAX_TRANSCRIPTS]:
        if not isinstance(item, dict):
            continue
        transcripts.append(
            {
                "id": normalize_space(item.get("id")),
                "display_name": normalize_space(item.get("display_name")),
                "biotype": normalize_space(item.get("biotype")),
                "seq_region_name": normalize_space(item.get("seq_region_name")),
                "start": item.get("start", ""),
                "end": item.get("end", ""),
                "strand": item.get("strand", ""),
                "is_canonical": bool(item.get("is_canonical")),
                "version": item.get("version", ""),
            }
        )
    return transcripts


def normalize_xref(item: JsonObject) -> JsonObject:
    return {
        "database": normalize_space(item.get("dbname")),
        "display_id": normalize_space(item.get("display_id")),
        "primary_id": normalize_space(item.get("primary_id")),
        "description": normalize_space(item.get("description")),
        "info_type": normalize_space(item.get("info_type")),
        "version": normalize_space(item.get("version")),
        "synonyms": item.get("synonyms") if isinstance(item.get("synonyms"), list) else [],
    }


def normalize_variant(variant: JsonObject, *, species: str, source_region: str) -> JsonObject:
    mappings = normalize_mappings(variant.get("mappings"))
    primary_mapping = mappings[0] if mappings else {}
    variant_id = normalize_space(variant.get("name") or variant.get("id"))
    return {
        "id": variant_id,
        "species": species,
        "species_label": species_label(species),
        "source": normalize_space(variant.get("source")),
        "var_class": normalize_space(variant.get("var_class")),
        "most_severe_consequence": normalize_space(variant.get("most_severe_consequence") or variant.get("consequence_type")),
        "ambiguity": normalize_space(variant.get("ambiguity")),
        "minor_allele": normalize_space(variant.get("minor_allele")),
        "maf": variant.get("MAF") if variant.get("MAF") is not None else "",
        "clinical_significance": variant.get("clinical_significance")
        if isinstance(variant.get("clinical_significance"), list)
        else [],
        "evidence": variant.get("evidence") if isinstance(variant.get("evidence"), list) else [],
        "synonyms": variant.get("synonyms") if isinstance(variant.get("synonyms"), list) else [],
        "mappings": mappings,
        "mapping_count": len(mappings),
        "primary_location": normalize_space(primary_mapping.get("location")),
        "allele_string": normalize_space(primary_mapping.get("allele_string")),
        "assembly_name": normalize_space(primary_mapping.get("assembly_name")),
        "source_region": source_region,
        "url": ensembl_variant_url(variant_id, species),
        "api_url": ensembl_variant_api_url(variant_id, species),
    }


def normalize_mappings(value: object) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    mappings = []
    for item in value:
        if not isinstance(item, dict):
            continue
        mappings.append(
            {
                "location": normalize_space(item.get("location")),
                "seq_region_name": normalize_space(item.get("seq_region_name")),
                "start": item.get("start", ""),
                "end": item.get("end", ""),
                "strand": item.get("strand", ""),
                "assembly_name": normalize_space(item.get("assembly_name")),
                "allele_string": normalize_space(item.get("allele_string")),
                "ancestral_allele": normalize_space(item.get("ancestral_allele")),
                "coord_system": normalize_space(item.get("coord_system")),
            }
        )
    return mappings


def feature_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Ensembl ID", normalize_space(normalized.get("id"))),
        ("Name", normalize_space(normalized.get("display_name"))),
        ("Type", normalize_space(normalized.get("object_type"))),
        ("Biotype", normalize_space(normalized.get("biotype"))),
        ("Species", normalize_space(normalized.get("species_label"))),
        ("Assembly", normalize_space(normalized.get("assembly_name"))),
        ("Location", normalize_space(normalized.get("location"))),
        ("Canonical transcript", normalize_space(normalized.get("canonical_transcript"))),
        ("Transcripts", str(normalized.get("transcript_count")) if normalized.get("transcript_count") else ""),
    )


def feature_sections(normalized: JsonObject) -> list[JsonObject]:
    return [
        {
            "key": "overview",
            "title": "Overview",
            "kind": "fields",
            "fields": feature_metadata(normalized),
        },
        {
            "key": "transcripts",
            "title": "Transcripts",
            "kind": "table",
            "summary": {"rows": len(normalized.get("transcripts", []))},
            "rows": normalized.get("transcripts", []),
        },
        {
            "key": "xrefs",
            "title": "Cross-references",
            "kind": "table",
            "rows": normalized.get("xrefs", []),
        },
    ]


def feature_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    return [
        {
            "kind": "table",
            "title": "Transcripts",
            "provider": "Ensembl",
            "id": normalize_space(normalized.get("id")),
            "url": normalize_space(normalized.get("url")),
            "section_key": "transcripts",
            "actions": display_actions(links),
            "data": {
                "columns": transcript_columns(),
                "rows": normalized.get("transcripts", []),
                "total_rows": len(normalized.get("transcripts", [])),
            },
        },
        {
            "kind": "xref_groups",
            "title": "Ensembl identifiers",
            "provider": "Ensembl",
            "id": normalize_space(normalized.get("id")),
            "url": normalize_space(normalized.get("url")),
            "section_key": "xrefs",
            "actions": display_actions(links),
            "data": {
                "groups": xref_groups(normalized.get("xrefs", []))
                or [
                    {
                        "database": "Ensembl",
                        "items": [
                            {
                                "id": normalize_space(normalized.get("id")),
                                "label": f"Ensembl:{normalize_space(normalized.get('id'))}",
                                "url": normalize_space(normalized.get("url")),
                            }
                        ],
                    }
                ],
            },
        },
    ]


def variant_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Variant", normalize_space(normalized.get("id"))),
        ("Class", normalize_space(normalized.get("var_class"))),
        ("Most severe consequence", normalize_space(normalized.get("most_severe_consequence"))),
        ("Location", normalize_space(normalized.get("primary_location"))),
        ("Alleles", normalize_space(normalized.get("allele_string"))),
        ("Assembly", normalize_space(normalized.get("assembly_name"))),
        ("Clinical significance", ", ".join(normalized.get("clinical_significance", []))),
        ("Evidence", ", ".join(normalized.get("evidence", [])[:8])),
    )


def variant_sections(normalized: JsonObject) -> list[JsonObject]:
    return [
        {
            "key": "overview",
            "title": "Overview",
            "kind": "fields",
            "fields": variant_metadata(normalized),
        },
        {
            "key": "mappings",
            "title": "Mappings",
            "kind": "table",
            "rows": normalized.get("mappings", []),
        },
        {
            "key": "evidence",
            "title": "Evidence",
            "kind": "list",
            "items": normalized.get("evidence", []),
        },
    ]


def variant_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    return [
        {
            "kind": "table",
            "title": "Variant mappings",
            "provider": "Ensembl",
            "id": normalize_space(normalized.get("id")),
            "url": normalize_space(normalized.get("url")),
            "section_key": "mappings",
            "actions": display_actions(links),
            "data": {
                "columns": mapping_columns(),
                "rows": normalized.get("mappings", []),
                "total_rows": len(normalized.get("mappings", [])),
            },
        },
        {
            "kind": "xref_groups",
            "title": "Variant identifiers",
            "provider": "Ensembl",
            "id": normalize_space(normalized.get("id")),
            "url": normalize_space(normalized.get("url")),
            "section_key": "overview",
            "actions": display_actions(links),
            "data": {
                "groups": [
                    {
                        "database": "Ensembl",
                        "items": [
                            {
                                "id": normalize_space(normalized.get("id")),
                                "label": normalize_space(normalized.get("id")),
                                "url": normalize_space(normalized.get("url")),
                            }
                        ],
                    },
                    {
                        "database": "Synonyms",
                        "items": [
                            {"id": synonym, "label": synonym}
                            for synonym in normalized.get("synonyms", [])[:20]
                        ],
                    },
                ],
            },
        },
    ]


def feature_identifiers(normalized: JsonObject) -> JsonObject:
    stable_id = normalize_space(normalized.get("id"))
    identifiers: JsonObject = {
        "ensembl": {
            "namespace": "ensembl",
            "id": stable_id,
            "label": f"Ensembl:{stable_id}",
            "url": normalize_space(normalized.get("url")),
        }
    }
    xrefs = normalized.get("xrefs", [])
    hgnc = first_xref(xrefs, "HGNC")
    if hgnc:
        identifiers["hgnc"] = {
            "namespace": "hgnc",
            "id": hgnc.get("primary_id") or hgnc.get("display_id"),
            "label": hgnc.get("display_id") or hgnc.get("primary_id"),
        }
    entrez = first_xref(xrefs, "EntrezGene")
    if entrez:
        identifiers["ncbi_gene"] = {
            "namespace": "geneid",
            "id": entrez.get("primary_id"),
            "label": f"GeneID:{entrez.get('primary_id')}",
            "url": f"https://www.ncbi.nlm.nih.gov/gene/{entrez.get('primary_id')}",
        }
    return identifiers


def variant_identifiers(normalized: JsonObject) -> JsonObject:
    variant_id = normalize_space(normalized.get("id"))
    identifiers: JsonObject = {
        "ensembl_variant": {
            "namespace": "ensembl_variant",
            "id": variant_id,
            "label": variant_id,
            "url": normalize_space(normalized.get("url")),
        }
    }
    if variant_id.lower().startswith("rs"):
        identifiers["dbsnp"] = {
            "namespace": "dbsnp",
            "id": variant_id,
            "label": variant_id,
            "url": dbsnp_url(variant_id),
        }
    return identifiers


def feature_links(normalized: JsonObject) -> list[JsonObject]:
    return compact_links(
        link("Ensembl", normalize_space(normalized.get("url")), primary=True),
        link("Location view", normalize_space(normalized.get("location_url")), kind="related"),
        link("REST lookup", normalize_space(normalized.get("api_url")), kind="related"),
    )


def variant_links(normalized: JsonObject) -> list[JsonObject]:
    variant_id = normalize_space(normalized.get("id"))
    return compact_links(
        link("Ensembl variation", normalize_space(normalized.get("url")), primary=True),
        link("REST variation", normalize_space(normalized.get("api_url")), kind="related"),
        link("dbSNP", dbsnp_url(variant_id), kind="related"),
    )


def xref_groups(xrefs: list[JsonObject]) -> list[JsonObject]:
    grouped: dict[str, list[JsonObject]] = {}
    for xref in xrefs:
        database = normalize_space(xref.get("database")) or "External"
        grouped.setdefault(database, []).append(
            {
                "id": normalize_space(xref.get("primary_id")) or normalize_space(xref.get("display_id")),
                "label": normalize_space(xref.get("display_id")) or normalize_space(xref.get("primary_id")),
                "description": normalize_space(xref.get("description")),
            }
        )
    return [
        {"database": database, "items": items}
        for database, items in sorted(grouped.items())
    ]


def first_xref(xrefs: list[JsonObject], database: str) -> JsonObject:
    for item in xrefs:
        if normalize_space(item.get("database")).lower() == database.lower():
            return item
    return {}


def feature_location(feature: JsonObject) -> str:
    seq_region = normalize_space(feature.get("seq_region_name"))
    start = feature.get("start")
    end = feature.get("end")
    if not seq_region or start in {"", None} or end in {"", None}:
        return ""
    return f"{seq_region}:{start}-{end}"


def variant_description(normalized: JsonObject) -> str:
    return " | ".join(
        part
        for part in [
            normalize_space(normalized.get("var_class")),
            normalize_space(normalized.get("most_severe_consequence")),
            normalize_space(normalized.get("primary_location")),
        ]
        if part
    )


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


def transcript_columns() -> list[JsonObject]:
    return [
        {"key": "id", "label": "Transcript"},
        {"key": "biotype", "label": "Biotype"},
        {"key": "start", "label": "Start"},
        {"key": "end", "label": "End"},
        {"key": "is_canonical", "label": "Canonical"},
    ]


def xref_columns() -> list[JsonObject]:
    return [
        {"key": "database", "label": "Database"},
        {"key": "display_id", "label": "Display ID"},
        {"key": "primary_id", "label": "Primary ID"},
        {"key": "description", "label": "Description"},
    ]


def mapping_columns() -> list[JsonObject]:
    return [
        {"key": "location", "label": "Location"},
        {"key": "allele_string", "label": "Alleles"},
        {"key": "assembly_name", "label": "Assembly"},
        {"key": "strand", "label": "Strand"},
    ]


def strand_text(value: object) -> str:
    if value == 1 or value == "1":
        return "+"
    if value == -1 or value == "-1":
        return "-"
    return normalize_space(value)


def ensembl_feature_url(stable_id: object, object_type: object, species: object) -> str:
    stable_id_text = normalize_space(stable_id)
    species_path = ensembl_species_path(species)
    object_type_text = normalize_space(object_type).lower()
    if object_type_text == "gene":
        return f"{ENSEMBL_WEBSITE_BASE_URL}/{species_path}/Gene/Summary?g={stable_id_text}"
    if object_type_text == "transcript":
        return f"{ENSEMBL_WEBSITE_BASE_URL}/{species_path}/Transcript/Summary?t={stable_id_text}"
    return ensembl_id_url(stable_id_text)


def ensembl_id_url(stable_id: object) -> str:
    stable_id_text = normalize_space(stable_id)
    return f"{ENSEMBL_WEBSITE_BASE_URL}/id/{stable_id_text}" if stable_id_text else ENSEMBL_WEBSITE_BASE_URL


def ensembl_location_url(species: object, feature: JsonObject) -> str:
    region = feature_location(feature)
    species_path = ensembl_species_path(species)
    return f"{ENSEMBL_WEBSITE_BASE_URL}/{species_path}/Location/View?r={region}" if region else ""


def ensembl_variant_url(variant_id: object, species: object) -> str:
    variant_id_text = normalize_space(variant_id)
    species_path = ensembl_species_path(species)
    return f"{ENSEMBL_WEBSITE_BASE_URL}/{species_path}/Variation/Explore?v={variant_id_text}"


def ensembl_lookup_api_url(stable_id: object) -> str:
    stable_id_text = normalize_space(stable_id)
    return f"{ENSEMBL_REST_BASE_URL}/lookup/id/{stable_id_text}"


def ensembl_xrefs_api_url(stable_id: object) -> str:
    stable_id_text = normalize_space(stable_id)
    return f"{ENSEMBL_REST_BASE_URL}/xrefs/id/{stable_id_text}"


def ensembl_variant_api_url(variant_id: object, species: object) -> str:
    return f"{ENSEMBL_REST_BASE_URL}/variation/{normalize_space(species)}/{normalize_space(variant_id)}"


def dbsnp_url(variant_id: object) -> str:
    variant_id_text = normalize_space(variant_id)
    return f"https://www.ncbi.nlm.nih.gov/snp/{variant_id_text}" if variant_id_text.lower().startswith("rs") else ""

