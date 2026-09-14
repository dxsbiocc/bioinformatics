"""Front-end compatible record envelopes for PubChem results."""

from __future__ import annotations

import urllib.parse

from .constants import (
    MAX_SYNONYMS,
    MAX_XREFS,
    PUBCHEM_PUG_BASE_URL,
    PUBCHEM_WEBSITE_BASE_URL,
    RECORD_SCHEMA_VERSION,
    JsonObject,
)
from .utils import normalize_space, safe_list


def pubchem_compound_record(
    properties: JsonObject,
    *,
    descriptions: list[JsonObject] | None = None,
    synonyms: list[str] | None = None,
    synonyms_truncated: bool = False,
    website_base_url: str = PUBCHEM_WEBSITE_BASE_URL,
    api_base_url: str = PUBCHEM_PUG_BASE_URL,
) -> JsonObject:
    normalized = normalize_compound(
        properties,
        descriptions=descriptions or [],
        synonyms=synonyms or [],
        synonyms_truncated=synonyms_truncated,
        website_base_url=website_base_url,
        api_base_url=api_base_url,
    )
    cid = normalized["cid"]
    title = normalized["title"] or f"CID {cid}"
    links = compound_links(normalized)
    description = compound_description(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "chemical.compound",
        "record_type": "pubchem_compound",
        "database": "pubchem",
        "id": cid,
        "stable_id": f"PubChem CID:{cid}",
        "label": title,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "pubchem",
        "identifiers": compound_identifiers(normalized),
        "links": links,
        "display": {
            "component": "compound",
            "chip_label": title,
            "icon": "pubchem",
            "title": title,
            "subtitle": compound_subtitle(normalized),
            "description": description,
            "metadata": compound_metadata(normalized),
            "badges": compact_badges(
                ("PubChem", "source"),
                (f"CID {cid}", "identifier"),
                (normalized["molecular_formula"], "formula"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": description,
                "icon": "pubchem",
                "fields": compact_fields(
                    ("CID", cid),
                    ("Title", title),
                    ("Formula", normalized["molecular_formula"]),
                    ("Molecular weight", normalized["molecular_weight"]),
                    ("InChIKey", normalized["inchi_key"]),
                    ("SMILES", normalized["canonical_smiles"]),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": compound_sections(normalized),
            "previews": compound_previews(normalized, links),
        },
        "related": {
            "descriptions": normalized["descriptions"],
            "synonyms": normalized["synonyms"],
        },
        "data": normalized,
    }


def pubchem_assay_record(
    assay: JsonObject,
    *,
    website_base_url: str = PUBCHEM_WEBSITE_BASE_URL,
    api_base_url: str = PUBCHEM_PUG_BASE_URL,
) -> JsonObject:
    normalized = normalize_assay(
        assay,
        website_base_url=website_base_url,
        api_base_url=api_base_url,
    )
    aid = normalized["aid"]
    title = normalized["name"] or f"PubChem BioAssay {aid}"
    description = normalize_space(normalized["description"]) or "PubChem BioAssay summary"
    links = assay_links(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "dataset",
        "record_type": "pubchem_assay",
        "database": "pubchem",
        "id": aid,
        "stable_id": f"PubChem AID:{aid}",
        "label": title,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "pubchem",
        "identifiers": {
            "pubchem_aid": {
                "namespace": "pubchem.aid",
                "id": aid,
                "label": f"AID {aid}",
                "url": normalized["url"],
            }
        },
        "links": links,
        "display": dataset_display(
            title=title,
            label=f"AID {aid}",
            description=description,
            metadata=assay_metadata(normalized),
            badges=compact_badges(("PubChem", "source"), (f"AID {aid}", "identifier"), ("BioAssay", "record_type")),
            links=links,
            sections=assay_sections(normalized),
            previews=assay_previews(normalized, links),
            url=normalized["url"],
        ),
        "related": {"summary": normalized["summary_rows"]},
        "data": normalized,
    }


def pubchem_substance_record(
    substance: JsonObject,
    *,
    website_base_url: str = PUBCHEM_WEBSITE_BASE_URL,
    api_base_url: str = PUBCHEM_PUG_BASE_URL,
    max_synonyms: int = MAX_SYNONYMS,
    max_xrefs: int = MAX_XREFS,
) -> JsonObject:
    normalized = normalize_substance(
        substance,
        website_base_url=website_base_url,
        api_base_url=api_base_url,
        max_synonyms=max_synonyms,
        max_xrefs=max_xrefs,
    )
    sid = normalized["sid"]
    title = normalized["title"] or f"PubChem Substance {sid}"
    description = normalized["source_label"] or "PubChem Substance record"
    links = substance_links(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "dataset",
        "record_type": "pubchem_substance",
        "database": "pubchem",
        "id": sid,
        "stable_id": f"PubChem SID:{sid}",
        "label": title,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "pubchem",
        "identifiers": substance_identifiers(normalized),
        "links": links,
        "display": dataset_display(
            title=title,
            label=f"SID {sid}",
            description=description,
            metadata=substance_metadata(normalized),
            badges=compact_badges(("PubChem", "source"), (f"SID {sid}", "identifier"), ("Substance", "record_type")),
            links=links,
            sections=substance_sections(normalized),
            previews=substance_previews(normalized, links),
            url=normalized["url"],
        ),
        "related": {
            "synonyms": normalized["synonyms"],
            "comments": normalized["comments"],
            "xrefs": normalized["xrefs"],
            "compound_cids": normalized["compound_cids"],
        },
        "data": normalized,
    }


def normalize_compound(
    properties: JsonObject,
    *,
    descriptions: list[JsonObject],
    synonyms: list[str],
    synonyms_truncated: bool,
    website_base_url: str,
    api_base_url: str,
) -> JsonObject:
    cid = normalize_space(properties.get("CID"))
    normalized_synonyms = unique_texts(synonyms, MAX_SYNONYMS)
    return {
        "cid": cid,
        "title": normalize_space(properties.get("Title")),
        "molecular_formula": normalize_space(properties.get("MolecularFormula")),
        "molecular_weight": normalize_space(properties.get("MolecularWeight")),
        "smiles": normalize_space(properties.get("SMILES")),
        "connectivity_smiles": normalize_space(properties.get("ConnectivitySMILES")),
        "canonical_smiles": normalize_space(
            properties.get("CanonicalSMILES") or properties.get("ConnectivitySMILES") or properties.get("SMILES")
        ),
        "isomeric_smiles": normalize_space(properties.get("IsomericSMILES")),
        "inchi": normalize_space(properties.get("InChI")),
        "inchi_key": normalize_space(properties.get("InChIKey")),
        "iupac_name": normalize_space(properties.get("IUPACName")),
        "xlogp": normalize_space(properties.get("XLogP")),
        "tpsa": normalize_space(properties.get("TPSA")),
        "h_bond_donor_count": normalize_space(properties.get("HBondDonorCount")),
        "h_bond_acceptor_count": normalize_space(properties.get("HBondAcceptorCount")),
        "rotatable_bond_count": normalize_space(properties.get("RotatableBondCount")),
        "exact_mass": normalize_space(properties.get("ExactMass")),
        "monoisotopic_mass": normalize_space(properties.get("MonoisotopicMass")),
        "charge": normalize_space(properties.get("Charge")),
        "descriptions": normalize_descriptions(descriptions),
        "synonyms": normalized_synonyms,
        "synonyms_truncated": synonyms_truncated or len(synonyms) > len(normalized_synonyms),
        "url": pubchem_compound_url(cid, website_base_url),
        "api_url": pubchem_api_url(f"compound/cid/{cid}/property/{property_path()}/JSON", api_base_url),
        "image_url": pubchem_api_url(f"compound/cid/{cid}/PNG", api_base_url),
    }


def normalize_assay(
    assay: JsonObject,
    *,
    website_base_url: str,
    api_base_url: str,
) -> JsonObject:
    aid = normalize_space(assay.get("AID") or assay.get("aid"))
    name = normalize_space(assay.get("Name") or assay.get("Title") or assay.get("SourceName"))
    description = normalize_space(
        assay.get("Description")
        or assay.get("AssayDescription")
        or assay.get("Comment")
        or assay.get("TargetName")
    )
    return {
        "aid": aid,
        "name": name,
        "source_name": normalize_space(assay.get("SourceName")),
        "description": description,
        "activity_outcome_method": normalize_space(assay.get("ActivityOutcomeMethod")),
        "assay_type": normalize_space(assay.get("AssayType")),
        "target_name": normalize_space(assay.get("TargetName")),
        "target_gene_id": normalize_space(assay.get("TargetGeneID")),
        "target_tax_id": normalize_space(assay.get("TargetTaxID")),
        "active_count": normalize_space(assay.get("ActiveCount")),
        "tested_count": normalize_space(assay.get("TestedCount")),
        "summary_rows": [{"property": key, "label": readable_label(key), "value": value} for key, value in assay.items() if value not in (None, "", [])],
        "url": pubchem_assay_url(aid, website_base_url),
        "api_url": pubchem_api_url(f"assay/aid/{aid}/summary/JSON", api_base_url),
    }


def normalize_substance(
    substance: JsonObject,
    *,
    website_base_url: str,
    api_base_url: str,
    max_synonyms: int,
    max_xrefs: int,
) -> JsonObject:
    sid_block = substance.get("sid") if isinstance(substance.get("sid"), dict) else {}
    source = substance.get("source") if isinstance(substance.get("source"), dict) else {}
    source_db = source.get("db") if isinstance(source.get("db"), dict) else {}
    sid = normalize_space(sid_block.get("id") or substance.get("sid"))
    source_name = normalize_space(source_db.get("name"))
    source_id = normalize_space(source_db.get("source_id"))
    synonyms = unique_texts([normalize_space(item) for item in safe_list(substance.get("synonyms"))], max_synonyms)
    comments = [normalize_space(item) for item in safe_list(substance.get("comment")) if normalize_space(item)]
    xrefs = normalize_substance_xrefs(substance.get("xref"), max_xrefs=max_xrefs)
    compound_cids = extract_compound_cids(substance.get("compound"))
    title = synonyms[0] if synonyms else source_id or f"SID {sid}"
    return {
        "sid": sid,
        "version": normalize_space(sid_block.get("version")),
        "title": title,
        "source_name": source_name,
        "source_id": source_id,
        "source_label": " | ".join(part for part in [source_name, source_id] if part),
        "synonyms": synonyms,
        "synonyms_truncated": len(safe_list(substance.get("synonyms"))) > len(synonyms),
        "comments": comments[:10],
        "comments_truncated": len(comments) > 10,
        "xrefs": xrefs,
        "xrefs_truncated": len(safe_list(substance.get("xref"))) > len(xrefs),
        "compound_cids": compound_cids,
        "url": pubchem_substance_url(sid, website_base_url),
        "api_url": pubchem_api_url(f"substance/sid/{sid}/JSON", api_base_url),
    }


def compound_sections(normalized: JsonObject) -> list[JsonObject]:
    sections = [
        {
            "key": "properties",
            "title": "Compound properties",
            "kind": "table",
            "rows": compound_property_rows(normalized),
        },
        {
            "key": "structure",
            "title": "Chemical structure",
            "kind": "chemical_structure",
            "fields": compact_fields(
                ("SMILES", normalized["canonical_smiles"]),
                ("Isomeric SMILES", normalized["isomeric_smiles"]),
                ("InChIKey", normalized["inchi_key"]),
            ),
        },
    ]
    if normalized["descriptions"]:
        sections.append({"key": "descriptions", "title": "Descriptions", "kind": "table", "rows": normalized["descriptions"]})
    if normalized["synonyms"]:
        sections.append(
            {
                "key": "synonyms",
                "title": "Synonyms",
                "kind": "table",
                "rows": [{"synonym": item} for item in normalized["synonyms"]],
                "summary": {"truncated": normalized["synonyms_truncated"]},
            }
        )
    return sections


def compound_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews = [
        {
            "kind": "chemical_structure",
            "title": "Chemical structure",
            "provider": "PubChem",
            "id": normalized["cid"],
            "url": normalized["image_url"],
            "section_key": "structure",
            "actions": display_actions(links),
            "data": {
                "cid": normalized["cid"],
                "smiles": normalized["canonical_smiles"],
                "isomeric_smiles": normalized["isomeric_smiles"],
                "inchi": normalized["inchi"],
                "inchi_key": normalized["inchi_key"],
                "image_url": normalized["image_url"],
            },
        },
        table_preview("properties", "Compound properties", normalized["cid"], normalized["url"], property_columns(), compound_property_rows(normalized), actions=display_actions(links)),
        xref_preview(normalized["cid"], normalized["url"], compound_xref_groups(normalized), links),
    ]
    if normalized["descriptions"]:
        previews.append(table_preview("descriptions", "Descriptions", normalized["cid"], normalized["url"], description_columns(), normalized["descriptions"], actions=display_actions(links)))
    if normalized["synonyms"]:
        previews.append(table_preview("synonyms", "Synonyms", normalized["cid"], normalized["url"], [{"key": "synonym", "label": "Synonym"}], [{"synonym": item} for item in normalized["synonyms"]], actions=display_actions(links), truncated=normalized["synonyms_truncated"]))
    return previews


def assay_sections(normalized: JsonObject) -> list[JsonObject]:
    return [{"key": "summary", "title": "Assay summary", "kind": "table", "rows": normalized["summary_rows"]}]


def assay_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    return [
        table_preview("summary", "Assay summary", normalized["aid"], normalized["url"], property_columns(), normalized["summary_rows"], actions=display_actions(links)),
        xref_preview(normalized["aid"], normalized["url"], assay_xref_groups(normalized), links),
    ]


def substance_sections(normalized: JsonObject) -> list[JsonObject]:
    sections = [{"key": "overview", "title": "Substance overview", "kind": "table", "rows": substance_overview_rows(normalized)}]
    if normalized["synonyms"]:
        sections.append(
            {
                "key": "synonyms",
                "title": "Synonyms",
                "kind": "table",
                "rows": [{"synonym": item} for item in normalized["synonyms"]],
                "summary": {"truncated": normalized["synonyms_truncated"]},
            }
        )
    if normalized["comments"]:
        sections.append({"key": "comments", "title": "Comments", "kind": "table", "rows": [{"comment": item} for item in normalized["comments"]], "summary": {"truncated": normalized["comments_truncated"]}})
    if normalized["xrefs"]:
        sections.append({"key": "xrefs", "title": "Cross-references", "kind": "table", "rows": normalized["xrefs"], "summary": {"truncated": normalized["xrefs_truncated"]}})
    return sections


def substance_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews = [
        table_preview("overview", "Substance overview", normalized["sid"], normalized["url"], property_columns(), substance_overview_rows(normalized), actions=display_actions(links)),
        xref_preview(normalized["sid"], normalized["url"], substance_xref_groups(normalized), links),
    ]
    if normalized["synonyms"]:
        previews.append(table_preview("synonyms", "Synonyms", normalized["sid"], normalized["url"], [{"key": "synonym", "label": "Synonym"}], [{"synonym": item} for item in normalized["synonyms"]], actions=display_actions(links), truncated=normalized["synonyms_truncated"]))
    return previews


def dataset_display(
    *,
    title: str,
    label: str,
    description: str,
    metadata: list[JsonObject],
    badges: list[JsonObject],
    links: list[JsonObject],
    sections: list[JsonObject],
    previews: list[JsonObject],
    url: str,
) -> JsonObject:
    return {
        "component": "dataset",
        "chip_label": label,
        "icon": "pubchem",
        "title": title,
        "subtitle": description,
        "description": description,
        "metadata": metadata,
        "badges": badges,
        "actions": display_actions(links),
        "hover": {"title": title, "subtitle": description, "icon": "pubchem", "fields": metadata + [{"label": "URL", "value": url}]},
        "primary_url": url,
        "sections": sections,
        "previews": previews,
    }


def table_preview(
    section_key: str,
    title: str,
    identifier: str,
    url: str,
    columns: list[JsonObject],
    rows: list[JsonObject],
    *,
    actions: list[JsonObject],
    total: int | None = None,
    truncated: bool = False,
) -> JsonObject:
    return {
        "kind": "table",
        "title": title,
        "provider": "PubChem",
        "id": identifier,
        "url": url,
        "section_key": section_key,
        "actions": actions,
        "data": {"columns": columns, "rows": rows, "total_rows": total if total is not None else len(rows), "shown_rows": len(rows), "truncated": truncated},
    }


def xref_preview(identifier: str, url: str, groups: list[JsonObject], links: list[JsonObject]) -> JsonObject:
    return {"kind": "xref_groups", "title": "Cross-reference groups", "provider": "PubChem", "id": identifier, "url": url, "actions": display_actions(links), "data": {"groups": groups}}


def compound_links(normalized: JsonObject) -> list[JsonObject]:
    return compact_links(
        link("Open in PubChem", normalized["url"], primary=True),
        link("PubChem PUG REST record", normalized["api_url"], kind="related"),
        link("Structure image", normalized["image_url"], kind="related"),
    )


def assay_links(normalized: JsonObject) -> list[JsonObject]:
    return compact_links(
        link("Open in PubChem", normalized["url"], primary=True),
        link("PubChem PUG REST assay", normalized["api_url"], kind="related"),
    )


def substance_links(normalized: JsonObject) -> list[JsonObject]:
    links = [
        link("Open in PubChem", normalized["url"], primary=True),
        link("PubChem PUG REST substance", normalized["api_url"], kind="related"),
    ]
    for cid in normalized["compound_cids"][:1]:
        links.append(link("Open linked compound", pubchem_compound_url(cid, PUBCHEM_WEBSITE_BASE_URL), kind="related"))
    return compact_links(*links)


def compound_identifiers(normalized: JsonObject) -> JsonObject:
    identifiers: JsonObject = {
        "pubchem_cid": {
            "namespace": "pubchem.cid",
            "id": normalized["cid"],
            "label": f"CID {normalized['cid']}",
            "url": normalized["url"],
        }
    }
    if normalized["inchi_key"]:
        identifiers["inchi_key"] = {"namespace": "inchi_key", "id": normalized["inchi_key"], "label": normalized["inchi_key"]}
    return identifiers


def substance_identifiers(normalized: JsonObject) -> JsonObject:
    identifiers: JsonObject = {
        "pubchem_sid": {
            "namespace": "pubchem.sid",
            "id": normalized["sid"],
            "label": f"SID {normalized['sid']}",
            "url": normalized["url"],
        }
    }
    if normalized["compound_cids"]:
        identifiers["pubchem_cid"] = [
            {"namespace": "pubchem.cid", "id": cid, "label": f"CID {cid}", "url": pubchem_compound_url(cid, PUBCHEM_WEBSITE_BASE_URL)}
            for cid in normalized["compound_cids"]
        ]
    return identifiers


def compound_xref_groups(normalized: JsonObject) -> list[JsonObject]:
    groups = [{"database": "PubChem", "items": [{"id": normalized["cid"], "label": f"CID {normalized['cid']}", "url": normalized["url"]}]}]
    if normalized["inchi_key"]:
        groups.append({"database": "InChIKey", "items": [{"id": normalized["inchi_key"], "label": normalized["inchi_key"]}]})
    for description in normalized["descriptions"]:
        if description.get("source") and description.get("url"):
            groups.append({"database": description["source"], "items": [{"id": description["source"], "label": description["source"], "url": description["url"]}]})
    return groups


def assay_xref_groups(normalized: JsonObject) -> list[JsonObject]:
    groups = [{"database": "PubChem", "items": [{"id": normalized["aid"], "label": f"AID {normalized['aid']}", "url": normalized["url"]}]}]
    if normalized["target_gene_id"]:
        groups.append({"database": "NCBI Gene", "items": [{"id": normalized["target_gene_id"], "label": normalized["target_gene_id"], "url": f"https://www.ncbi.nlm.nih.gov/gene/{urllib.parse.quote(normalized['target_gene_id'])}"}]})
    return groups


def substance_xref_groups(normalized: JsonObject) -> list[JsonObject]:
    groups = [{"database": "PubChem", "items": [{"id": normalized["sid"], "label": f"SID {normalized['sid']}", "url": normalized["url"]}]}]
    if normalized["compound_cids"]:
        groups.append({"database": "Linked compounds", "items": [{"id": cid, "label": f"CID {cid}", "url": pubchem_compound_url(cid, PUBCHEM_WEBSITE_BASE_URL)} for cid in normalized["compound_cids"]]})
    if normalized["xrefs"]:
        groups.append({"database": "Depositor cross-references", "items": [{"id": row["value"], "label": row["label"], "url": row.get("url", "")} for row in normalized["xrefs"] if row.get("value")]})
    return groups


def compound_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("CID", normalized["cid"]),
        ("Title", normalized["title"]),
        ("Formula", normalized["molecular_formula"]),
        ("Molecular weight", normalized["molecular_weight"]),
        ("XLogP", normalized["xlogp"]),
        ("TPSA", normalized["tpsa"]),
        ("H-bond donors", normalized["h_bond_donor_count"]),
        ("H-bond acceptors", normalized["h_bond_acceptor_count"]),
        ("InChIKey", normalized["inchi_key"]),
    )


def assay_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("AID", normalized["aid"]),
        ("Name", normalized["name"]),
        ("Source", normalized["source_name"]),
        ("Assay type", normalized["assay_type"]),
        ("Outcome method", normalized["activity_outcome_method"]),
        ("Target", normalized["target_name"]),
        ("Active count", normalized["active_count"]),
        ("Tested count", normalized["tested_count"]),
    )


def substance_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("SID", normalized["sid"]),
        ("Version", normalized["version"]),
        ("Source", normalized["source_name"]),
        ("Source ID", normalized["source_id"]),
        ("Linked CIDs", ", ".join(normalized["compound_cids"][:5])),
    )


def compound_description(normalized: JsonObject) -> str:
    parts = [
        normalized["molecular_formula"],
        f"MW {normalized['molecular_weight']}" if normalized["molecular_weight"] else "",
        normalized["inchi_key"],
    ]
    return " | ".join(part for part in parts if part)


def compound_subtitle(normalized: JsonObject) -> str:
    return " | ".join(part for part in [f"CID {normalized['cid']}", normalized["molecular_formula"], f"MW {normalized['molecular_weight']}" if normalized["molecular_weight"] else ""] if part)


def compound_property_rows(normalized: JsonObject) -> list[JsonObject]:
    return [
        {"property": "MolecularFormula", "label": "Formula", "value": normalized["molecular_formula"]},
        {"property": "MolecularWeight", "label": "Molecular weight", "value": normalized["molecular_weight"]},
        {"property": "SMILES", "label": "SMILES", "value": normalized["canonical_smiles"]},
        {"property": "IsomericSMILES", "label": "Isomeric SMILES", "value": normalized["isomeric_smiles"]},
        {"property": "InChIKey", "label": "InChIKey", "value": normalized["inchi_key"]},
        {"property": "IUPACName", "label": "IUPAC name", "value": normalized["iupac_name"]},
        {"property": "XLogP", "label": "XLogP", "value": normalized["xlogp"]},
        {"property": "TPSA", "label": "TPSA", "value": normalized["tpsa"]},
        {"property": "HBondDonorCount", "label": "H-bond donors", "value": normalized["h_bond_donor_count"]},
        {"property": "HBondAcceptorCount", "label": "H-bond acceptors", "value": normalized["h_bond_acceptor_count"]},
        {"property": "RotatableBondCount", "label": "Rotatable bonds", "value": normalized["rotatable_bond_count"]},
        {"property": "ExactMass", "label": "Exact mass", "value": normalized["exact_mass"]},
        {"property": "Charge", "label": "Charge", "value": normalized["charge"]},
    ]


def substance_overview_rows(normalized: JsonObject) -> list[JsonObject]:
    return [
        {"property": "SID", "label": "SID", "value": normalized["sid"]},
        {"property": "Version", "label": "Version", "value": normalized["version"]},
        {"property": "Source", "label": "Source", "value": normalized["source_name"]},
        {"property": "SourceID", "label": "Source ID", "value": normalized["source_id"]},
        {"property": "LinkedCIDs", "label": "Linked CIDs", "value": ", ".join(normalized["compound_cids"])},
    ]


def normalize_descriptions(value: list[JsonObject]) -> list[JsonObject]:
    rows = []
    for item in value:
        if not isinstance(item, dict):
            continue
        description = normalize_space(item.get("Description"))
        title = normalize_space(item.get("Title"))
        source = normalize_space(item.get("DescriptionSourceName") or item.get("SourceName"))
        url = normalize_space(item.get("DescriptionURL") or item.get("URL"))
        if description or title:
            rows.append({"title": title, "description": description, "source": source, "url": url})
    return rows[:10]


def normalize_substance_xrefs(value: object, *, max_xrefs: int) -> list[JsonObject]:
    rows = []
    for item in safe_list(value)[:max_xrefs]:
        if not isinstance(item, dict):
            continue
        for key, raw in item.items():
            text = normalize_space(raw)
            if text:
                rows.append({"kind": key, "label": readable_label(key), "value": text, "url": text if text.startswith(("http://", "https://")) else ""})
    return rows


def extract_compound_cids(value: object) -> list[str]:
    cids: list[str] = []
    for item in safe_list(value):
        cid = extract_cid(item)
        if cid and cid not in cids:
            cids.append(cid)
    return cids


def extract_cid(value: object) -> str:
    if isinstance(value, dict):
        for key in ("cid", "CID"):
            text = normalize_space(value.get(key))
            if text:
                return text
        nested = value.get("id")
        if nested is not value:
            text = extract_cid(nested)
            if text:
                return text
    return ""


def unique_texts(values: list[str], limit: int) -> list[str]:
    rows = []
    seen: set[str] = set()
    for value in values:
        text = normalize_space(value)
        if not text or text.casefold() in seen:
            continue
        seen.add(text.casefold())
        rows.append(text)
        if len(rows) >= limit:
            break
    return rows


def property_path() -> str:
    from .constants import COMPOUND_PROPERTY_FIELDS

    return ",".join(COMPOUND_PROPERTY_FIELDS)


def pubchem_compound_url(cid: str, website_base_url: str) -> str:
    return f"{website_base_url.rstrip('/')}/compound/{urllib.parse.quote(str(cid))}" if cid else website_base_url.rstrip("/")


def pubchem_assay_url(aid: str, website_base_url: str) -> str:
    return f"{website_base_url.rstrip('/')}/bioassay/{urllib.parse.quote(str(aid))}" if aid else website_base_url.rstrip("/")


def pubchem_substance_url(sid: str, website_base_url: str) -> str:
    return f"{website_base_url.rstrip('/')}/substance/{urllib.parse.quote(str(sid))}" if sid else website_base_url.rstrip("/")


def pubchem_api_url(endpoint: str, api_base_url: str) -> str:
    return f"{api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"


def property_columns() -> list[JsonObject]:
    return [{"key": "label", "label": "Property"}, {"key": "value", "label": "Value"}]


def description_columns() -> list[JsonObject]:
    return [{"key": "source", "label": "Source"}, {"key": "description", "label": "Description"}]


def readable_label(key: object) -> str:
    text = normalize_space(key)
    out = []
    for index, char in enumerate(text):
        if index > 0 and char.isupper() and text[index - 1].islower():
            out.append(" ")
        elif char in {"_", "-"}:
            out.append(" ")
            continue
        out.append(char)
    return "".join(out).strip().title() or text


def link(label: str, url: str, *, kind: str = "external", primary: bool = False) -> JsonObject:
    return {"label": label, "url": url, "kind": kind, "primary": primary} if url else {}


def compact_links(*links: JsonObject) -> list[JsonObject]:
    return [item for item in links if item.get("url")]


def display_actions(links: list[JsonObject]) -> list[JsonObject]:
    return [{"label": item["label"], "url": item["url"], "kind": item.get("kind", "external"), "primary": bool(item.get("primary"))} for item in links if item.get("url")]


def compact_fields(*pairs: tuple[str, object]) -> list[JsonObject]:
    rows = []
    for label_text, value in pairs:
        text = normalize_space(value)
        if text:
            rows.append({"label": label_text, "value": text})
    return rows


def compact_badges(*pairs: tuple[object, str]) -> list[JsonObject]:
    rows = []
    for label_value, badge_type in pairs:
        text = normalize_space(label_value)
        if text:
            rows.append({"label": text, "kind": badge_type})
    return rows
