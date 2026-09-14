"""Front-end compatible record envelopes for RNAcentral results."""

from __future__ import annotations

from .constants import RECORD_SCHEMA_VERSION, JsonObject
from .utils import compact_strings, normalize_space, rnacentral_api_url, rnacentral_website_url, safe_dict, safe_list


def rna_entry_record(entry: JsonObject) -> JsonObject:
    normalized = normalize_entry(entry)
    links = entry_links(normalized)
    title = normalized["short_description"] or normalized["description"] or normalized["rnacentral_id"]
    description = normalized["description"] or "RNAcentral non-coding RNA sequence"
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "rna",
        "record_type": "rnacentral_rna",
        "database": "rnacentral",
        "id": normalized["rnacentral_id"],
        "stable_id": normalized["stable_id"],
        "label": normalized["rnacentral_id"],
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "rnacentral",
        "identifiers": entry_identifiers(normalized),
        "links": links,
        "display": {
            "component": "genomic_feature",
            "chip_label": normalized["rnacentral_id"],
            "icon": "rnacentral",
            "title": title,
            "subtitle": entry_subtitle(normalized),
            "description": description,
            "metadata": entry_metadata(normalized),
            "badges": compact_badges(
                ("RNAcentral", "source"),
                (normalized["rnacentral_id"], "identifier"),
                (normalized["rna_type"], "rna_type"),
                (normalized["species"], "context"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": entry_subtitle(normalized),
                "icon": "rnacentral",
                "fields": compact_fields(
                    ("RNAcentral ID", normalized["rnacentral_id"]),
                    ("Species", normalized["species"]),
                    ("TaxID", normalized["taxid"]),
                    ("RNA type", normalized["rna_type"]),
                    ("Length", normalized["length"]),
                    ("Databases", ", ".join(normalized["distinct_databases"])),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": entry_sections(normalized),
            "previews": entry_previews(normalized, links),
        },
        "related": {
            "genes": normalized["genes"],
            "distinct_databases": normalized["distinct_databases"],
            "publications": normalized["publications"],
            "xrefs_url": normalized["xrefs_api_url"],
            "publications_url": normalized["publications_api_url"],
        },
        "data": normalized,
    }


def xrefs_record(rnacentral_id: str, xrefs: list[JsonObject], *, total: int) -> JsonObject:
    normalized_id = normalize_space(rnacentral_id).split("_", 1)[0].upper()
    normalized = [normalize_xref(item) for item in xrefs]
    normalized = [item for item in normalized if item["database"] or item["accession_id"]]
    url = rnacentral_website_url(normalized_id)
    api_url = rnacentral_api_url(f"rna/{normalized_id}/xrefs/")
    links = compact_links(
        link("RNAcentral entry", url, primary=True),
        link("RNAcentral xrefs API", api_url, kind="api"),
    )
    groups = xref_groups(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "identifier.mapping",
        "record_type": "rnacentral_xrefs",
        "database": "rnacentral",
        "id": normalized_id,
        "stable_id": f"RNAcentral:{normalized_id}:xrefs",
        "label": f"{normalized_id} xrefs",
        "title": f"RNAcentral cross-references for {normalized_id}",
        "description": f"{len(normalized)} of {total} cross-references returned",
        "url": url,
        "icon": "rnacentral",
        "identifiers": {
            "rnacentral": {
                "namespace": "rnacentral",
                "id": normalized_id,
                "label": f"RNAcentral:{normalized_id}",
                "url": url,
            }
        },
        "links": links,
        "display": {
            "component": "identifier_conversion",
            "chip_label": f"{normalized_id} xrefs",
            "icon": "rnacentral",
            "title": f"Cross-references for {normalized_id}",
            "subtitle": f"{len(normalized)} shown | {total} total",
            "description": "External database references indexed by RNAcentral.",
            "metadata": compact_fields(
                ("RNAcentral ID", normalized_id),
                ("Shown", len(normalized)),
                ("Total", total),
                ("Databases", len(groups)),
                ("Truncated", "yes" if total > len(normalized) else ""),
            ),
            "badges": compact_badges(
                ("RNAcentral", "source"),
                ("cross-reference", "record_type"),
                (f"{len(groups)} groups", "count"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": f"Cross-references for {normalized_id}",
                "subtitle": f"{len(normalized)} shown | {total} total",
                "icon": "rnacentral",
                "fields": compact_fields(
                    ("RNAcentral ID", normalized_id),
                    ("Shown", len(normalized)),
                    ("Total", total),
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
                    "provider": "RNAcentral",
                    "id": normalized_id,
                    "url": url,
                    "section_key": "xrefs",
                    "actions": display_actions(links),
                    "data": {"groups": groups, "total": total, "truncated": total > len(normalized)},
                },
                {
                    "kind": "table",
                    "title": "Cross-references",
                    "provider": "RNAcentral",
                    "id": normalized_id,
                    "url": url,
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
        "data": {"rnacentral_id": normalized_id, "xrefs": normalized, "total": total},
    }


def normalize_entry(entry: JsonObject) -> JsonObject:
    raw_id = normalize_space(entry.get("rnacentral_id") or entry.get("upi"))
    rnacentral_id, taxid_from_id = split_rnacentral_id(raw_id)
    taxid = normalize_space(entry.get("taxid") or taxid_from_id)
    sequence = normalize_space(entry.get("sequence"))
    length = int(entry.get("length") or len(sequence) or 0)
    distinct_databases = normalize_distinct_databases(entry.get("distinct_databases"))
    publications_value = entry.get("publications")
    publications_url = normalize_space(publications_value) if isinstance(publications_value, str) and normalize_space(publications_value).startswith(("http://", "https://")) else ""
    publications_count = int(publications_value) if isinstance(publications_value, (int, float)) and not isinstance(publications_value, bool) else None
    url = rnacentral_website_url(rnacentral_id, taxid or None)
    return {
        "rnacentral_id": rnacentral_id,
        "raw_id": raw_id,
        "taxid": taxid,
        "stable_id": f"RNAcentral:{rnacentral_id}{'_' + taxid if taxid else ''}",
        "url": url,
        "api_url": normalize_space(entry.get("url")) or rnacentral_api_url(f"rna/{rnacentral_id}/{taxid}/" if taxid else f"rna/{rnacentral_id}/"),
        "xrefs_api_url": normalize_space(entry.get("xrefs")) or rnacentral_api_url(f"rna/{rnacentral_id}/xrefs/"),
        "publications_api_url": publications_url or rnacentral_api_url(f"rna/{rnacentral_id}/publications/"),
        "sequence": sequence,
        "length": length,
        "description": normalize_space(entry.get("description")),
        "short_description": normalize_space(entry.get("short_description")),
        "species": normalize_space(entry.get("species")),
        "genes": normalize_genes(entry.get("genes")),
        "publications": publications_count if publications_count is not None else normalize_space(publications_value),
        "rna_type": normalize_space(entry.get("rna_type")),
        "is_active": bool(entry.get("is_active")) if entry.get("is_active") is not None else None,
        "distinct_databases": distinct_databases,
        "count_distinct_organisms": entry.get("count_distinct_organisms"),
        "md5": normalize_space(entry.get("md5")),
    }


def normalize_xref(row: JsonObject) -> JsonObject:
    accession = safe_dict(row.get("accession"))
    accession_id = normalize_space(accession.get("id") or accession.get("external_id"))
    return {
        "database": normalize_space(row.get("database")),
        "accession_id": accession_id,
        "external_id": normalize_space(accession.get("external_id")),
        "description": normalize_space(accession.get("description")),
        "species": normalize_space(accession.get("species")),
        "taxid": normalize_space(row.get("taxid") or accession.get("taxid")),
        "rna_type": normalize_space(accession.get("rna_type")),
        "gene": normalize_space(accession.get("gene")),
        "product": normalize_space(accession.get("product")),
        "feature_name": normalize_space(accession.get("feature_name")),
        "feature_start": accession.get("feature_start"),
        "feature_end": accession.get("feature_end"),
        "is_active": bool(row.get("is_active")) if row.get("is_active") is not None else None,
        "first_seen": normalize_space(row.get("first_seen")),
        "last_seen": normalize_space(row.get("last_seen")),
        "url": first_url(
            accession.get("expert_db_url"),
            accession.get("ena_url"),
            row.get("ensembl_url"),
            row.get("gencode_ensembl_url"),
            accession.get("url"),
        ),
        "ena_url": normalize_space(accession.get("ena_url")),
        "ensembl_url": normalize_space(row.get("ensembl_url") or row.get("gencode_ensembl_url") or accession.get("ensembl_species_url")),
        "citations_url": normalize_space(accession.get("citations")),
        "raw": row,
    }


def split_rnacentral_id(value: str) -> tuple[str, str]:
    text = normalize_space(value).upper()
    if "_" in text:
        identifier, taxid = text.split("_", 1)
        return identifier, taxid
    return text, ""


def normalize_distinct_databases(value: object) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return compact_strings(value)


def normalize_genes(value: object) -> list[JsonObject]:
    genes = []
    for item in safe_list(value):
        if isinstance(item, dict):
            gene_id = normalize_space(item.get("id") or item.get("gene") or item.get("symbol"))
            label = normalize_space(item.get("label") or item.get("symbol") or item.get("name") or gene_id)
            if gene_id or label:
                genes.append({"id": gene_id or label, "label": label or gene_id})
        else:
            text = normalize_space(item)
            if text:
                genes.append({"id": text, "label": text})
    return genes


def entry_links(normalized: JsonObject) -> list[JsonObject]:
    return compact_links(
        link("RNAcentral entry", normalized["url"], primary=True),
        link("RNAcentral API", normalized["api_url"], kind="api"),
        link("Cross-references API", normalized["xrefs_api_url"], kind="api"),
        link("Publications API", normalized["publications_api_url"], kind="api"),
    )


def entry_identifiers(normalized: JsonObject) -> JsonObject:
    identifiers: JsonObject = {
        "rnacentral": {
            "namespace": "rnacentral",
            "id": normalized["rnacentral_id"],
            "label": f"RNAcentral:{normalized['rnacentral_id']}",
            "url": normalized["url"],
        }
    }
    if normalized["taxid"]:
        identifiers["taxon"] = {
            "namespace": "taxonomy",
            "id": normalized["taxid"],
            "label": f"TaxID:{normalized['taxid']}",
            "url": f"https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id={normalized['taxid']}",
        }
    if normalized["genes"]:
        identifiers["gene"] = [
            {"namespace": "gene", "id": gene["id"], "label": gene["label"], "url": ""}
            for gene in normalized["genes"]
            if gene.get("id")
        ]
    return identifiers


def entry_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("RNAcentral ID", normalized["rnacentral_id"]),
        ("RNA type", normalized["rna_type"]),
        ("Species", normalized["species"]),
        ("TaxID", normalized["taxid"]),
        ("Length", normalized["length"]),
        ("Active", active_label(normalized["is_active"])),
        ("Databases", ", ".join(normalized["distinct_databases"])),
        ("Publications", normalized["publications"] if isinstance(normalized["publications"], int) else ""),
        ("Organisms", normalized["count_distinct_organisms"]),
    )


def entry_sections(normalized: JsonObject) -> list[JsonObject]:
    sections: list[JsonObject] = [
        {"key": "overview", "title": "Overview", "kind": "fields", "fields": entry_metadata(normalized)},
        {
            "key": "databases",
            "title": "Source databases",
            "kind": "table",
            "rows": [{"database": database} for database in normalized["distinct_databases"]],
        },
    ]
    if normalized["sequence"]:
        sections.append({"key": "sequence", "title": "RNA sequence", "kind": "sequence", "sequence": normalized["sequence"]})
    if normalized["genes"]:
        sections.append({"key": "genes", "title": "Genes", "kind": "table", "rows": normalized["genes"]})
    if normalized["description"]:
        sections.append({"key": "description", "title": "Description", "kind": "text", "text": normalized["description"]})
    return sections


def entry_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews: list[JsonObject] = [
        {
            "kind": "table",
            "title": "RNA metadata",
            "provider": "RNAcentral",
            "id": normalized["rnacentral_id"],
            "url": normalized["url"],
            "section_key": "overview",
            "actions": display_actions(links),
            "data": {"columns": ["label", "value"], "rows": entry_metadata(normalized)},
        },
        {
            "kind": "xref_groups",
            "title": "RNAcentral links",
            "provider": "RNAcentral",
            "id": normalized["rnacentral_id"],
            "url": normalized["url"],
            "actions": display_actions(links),
            "data": {"groups": entry_xref_groups(normalized)},
        },
    ]
    if normalized["sequence"]:
        previews.insert(
            0,
            {
                "kind": "sequence",
                "title": "RNA sequence",
                "provider": "RNAcentral",
                "id": normalized["rnacentral_id"],
                "url": normalized["url"],
                "section_key": "sequence",
                "data": {
                    "sequence": normalized["sequence"],
                    "length": normalized["length"],
                    "alphabet": "RNA",
                    "format": "raw",
                    "mime_type": "text/plain",
                },
            },
        )
    if normalized["description"]:
        previews.append(
            {
                "kind": "text",
                "title": "Description",
                "provider": "RNAcentral",
                "id": normalized["rnacentral_id"],
                "url": normalized["url"],
                "section_key": "description",
                "data": {"text": normalized["description"]},
            }
        )
    return previews


def entry_xref_groups(normalized: JsonObject) -> list[JsonObject]:
    groups = [
        {
            "database": "RNAcentral",
            "items": [{"id": normalized["rnacentral_id"], "label": normalized["rnacentral_id"], "url": normalized["url"]}],
        }
    ]
    if normalized["taxid"]:
        groups.append(
            {
                "database": "NCBI Taxonomy",
                "items": [
                    {
                        "id": normalized["taxid"],
                        "label": f"TaxID:{normalized['taxid']}",
                        "url": f"https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id={normalized['taxid']}",
                    }
                ],
            }
        )
    if normalized["distinct_databases"]:
        groups.append(
            {
                "database": "Source databases",
                "items": [{"id": database, "label": database, "url": ""} for database in normalized["distinct_databases"]],
            }
        )
    if normalized["genes"]:
        groups.append({"database": "Genes", "items": normalized["genes"]})
    return groups


def xref_groups(xrefs: list[JsonObject]) -> list[JsonObject]:
    grouped: dict[str, list[JsonObject]] = {}
    for item in xrefs:
        database = item["database"] or "External"
        grouped.setdefault(database, []).append(
            {
                "id": item["accession_id"] or item["external_id"] or item["description"],
                "label": item["accession_id"] or item["external_id"] or item["description"],
                "url": item["url"],
            }
        )
    return [{"database": database, "items": values} for database, values in sorted(grouped.items())]


def xref_columns() -> list[str]:
    return [
        "database",
        "accession_id",
        "description",
        "species",
        "taxid",
        "rna_type",
        "gene",
        "feature_start",
        "feature_end",
        "url",
    ]


def entry_subtitle(normalized: JsonObject) -> str:
    return " | ".join(
        part
        for part in [
            normalized["rna_type"],
            normalized["species"],
            f"{normalized['length']} nt" if normalized["length"] else "",
        ]
        if part
    )


def active_label(value: object) -> str:
    if value is True:
        return "active"
    if value is False:
        return "inactive"
    return ""


def first_url(*values: object) -> str:
    for value in values:
        text = normalize_space(value)
        if text.startswith(("http://", "https://")):
            return text
    return ""


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
