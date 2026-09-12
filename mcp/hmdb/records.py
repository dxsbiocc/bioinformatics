"""Front-end compatible record envelopes for HMDB search results."""

from __future__ import annotations

import re
from typing import Any

from .constants import HMDB_BASE_URL, RECORD_SCHEMA_VERSION, JsonObject
from .utils import first_text, hmdb_record_url, normalize_space, pick_list, safe_list


def hmdb_record(row: JsonObject, *, category: str, query: str, base_url: str = HMDB_BASE_URL) -> JsonObject:
    normalized = normalize_record(row, category=category, query=query, base_url=base_url)
    component = component_for_category(category)
    record_type = f"hmdb_{category[:-1] if category.endswith('s') else category}"
    title = normalized["name"] or normalized["id"]
    description = normalized["description"] or f"HMDB {category[:-1]} record"
    links = record_links(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": type_for_category(category),
        "record_type": record_type,
        "database": "hmdb",
        "id": normalized["id"],
        "stable_id": f"HMDB:{category}:{normalized['id']}",
        "label": title,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "hmdb",
        "identifiers": record_identifiers(normalized),
        "links": links,
        "display": {
            "component": component,
            "chip_label": normalized["id"],
            "icon": "hmdb",
            "title": title,
            "subtitle": subtitle(normalized),
            "description": description,
            "metadata": metadata(normalized),
            "badges": compact_badges(
                ("HMDB", "source"),
                (category[:-1].title() if category.endswith("s") else category.title(), "record_type"),
                (normalized["id"], "identifier"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": subtitle(normalized),
                "icon": "hmdb",
                "fields": compact_fields(
                    ("ID", normalized["id"]),
                    ("Category", category),
                    ("Formula", normalized["formula"]),
                    ("InChIKey", normalized["inchikey"]),
                    ("Gene", normalized["gene_name"]),
                    ("Organism", normalized["organism"]),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": sections(normalized),
            "previews": previews(normalized, links),
        },
        "related": {
            "synonyms": normalized["synonyms"],
            "xrefs": normalized["xrefs"],
            "pathways": normalized["pathways"],
            "diseases": normalized["diseases"],
        },
        "data": normalized,
    }


def normalize_record(row: JsonObject, *, category: str, query: str, base_url: str) -> JsonObject:
    identifier = record_identifier(row, category=category, query=query)
    name = first_text(row, "name", "title", "common_name", "protein_name", "pathway_name", "disease_name")
    description = first_text(row, "description", "summary", "definition", "overview")
    formula = first_text(row, "chemical_formula", "molecular_formula", "formula")
    smiles = first_text(row, "smiles", "SMILES", "canonical_smiles")
    inchi = first_text(row, "inchi", "InChI")
    inchikey = first_text(row, "inchikey", "inchi_key", "InChIKey")
    sequence = first_text(row, "sequence", "protein_sequence", "amino_acid_sequence")
    xrefs = normalize_xrefs(row)
    url = first_text(row, "url", "hmdb_url", "record_url") or hmdb_record_url(category, identifier, base_url=base_url)
    return {
        "id": identifier,
        "category": category,
        "query": query,
        "name": name,
        "description": description,
        "url": url,
        "accession": first_text(row, "hmdb_id", "accession", "hmdb_accession", "metabolite_id", "protein_id", "pathway_id", "disease_id"),
        "formula": formula,
        "molecular_weight": first_text(row, "molecular_weight", "average_molecular_weight", "monisotopic_molecular_weight"),
        "smiles": smiles,
        "inchi": inchi,
        "inchikey": inchikey,
        "kingdom": first_text(row, "kingdom"),
        "super_class": first_text(row, "super_class", "superclass"),
        "chemical_class": first_text(row, "class", "chemical_class"),
        "sub_class": first_text(row, "sub_class", "subclass"),
        "gene_name": first_text(row, "gene_name", "gene", "gene_symbol"),
        "uniprot_id": first_text(row, "uniprot_id", "uniprot", "uniprotkb_id"),
        "organism": first_text(row, "organism", "species"),
        "sequence": sequence,
        "synonyms": pick_list(row, "synonyms", "synonym", "secondary_accessions"),
        "xrefs": xrefs,
        "pathways": pick_list(row, "pathways", "associated_pathways"),
        "diseases": pick_list(row, "diseases", "associated_diseases"),
        "raw_keys": sorted(str(key) for key in row.keys()),
    }


def record_identifier(row: JsonObject, *, category: str, query: str) -> str:
    for key in [
        "hmdb_id",
        "accession",
        "hmdb_accession",
        "metabolite_id",
        "protein_id",
        "pathway_id",
        "disease_id",
        "id",
        "identifier",
    ]:
        text = normalize_space(row.get(key))
        if text:
            return text
    name = first_text(row, "name", "title", "protein_name", "pathway_name", "disease_name") or query
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", name).strip("-")
    return slug or category


def normalize_xrefs(row: JsonObject) -> list[JsonObject]:
    xrefs: list[JsonObject] = []
    explicit = row.get("xrefs") or row.get("external_references")
    for item in safe_list(explicit):
        if isinstance(item, dict):
            database = first_text(item, "database", "source", "namespace")
            identifier = first_text(item, "id", "identifier", "accession")
            label = first_text(item, "label", "name") or ":".join(part for part in [database, identifier] if part)
            url = first_text(item, "url")
            if label or identifier:
                xrefs.append({"database": database, "id": identifier, "label": label, "url": url})
        else:
            text = normalize_space(item)
            if text:
                database, identifier = split_xref(text)
                xrefs.append({"database": database, "id": identifier, "label": text, "url": xref_url(database, identifier)})
    for database, keys in {
        "PubChem": ["pubchem_compound_id", "pubchem_cid", "cid"],
        "ChEBI": ["chebi_id", "chebi"],
        "KEGG": ["kegg_id", "kegg"],
        "UniProt": ["uniprot_id", "uniprot", "uniprotkb_id"],
        "Gene": ["gene_name", "gene", "gene_symbol"],
    }.items():
        identifier = first_text(row, *keys)
        if identifier:
            xrefs.append({"database": database, "id": identifier, "label": f"{database}:{identifier}", "url": xref_url(database, identifier)})
    return unique_xrefs(xrefs)


def component_for_category(category: str) -> str:
    return {
        "metabolites": "compound",
        "proteins": "protein",
        "pathways": "pathway",
        "diseases": "dataset",
    }.get(category, "dataset")


def type_for_category(category: str) -> str:
    return {
        "metabolites": "chemical.compound",
        "proteins": "protein",
        "pathways": "pathway",
        "diseases": "dataset",
    }.get(category, "dataset")


def subtitle(data: JsonObject) -> str:
    if data["category"] == "metabolites":
        return " | ".join(part for part in [data["id"], data["formula"], data["chemical_class"]] if part)
    if data["category"] == "proteins":
        return " | ".join(part for part in [data["id"], data["gene_name"], data["organism"]] if part)
    return " | ".join(part for part in [data["id"], data["category"]] if part)


def metadata(data: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("ID", data["id"]),
        ("Category", data["category"]),
        ("Formula", data["formula"]),
        ("Molecular weight", data["molecular_weight"]),
        ("Class", data["chemical_class"]),
        ("Sub class", data["sub_class"]),
        ("Gene", data["gene_name"]),
        ("UniProt", data["uniprot_id"]),
        ("Organism", data["organism"]),
        ("Synonyms", len(data["synonyms"])),
        ("Cross references", len(data["xrefs"])),
    )


def sections(data: JsonObject) -> list[JsonObject]:
    out: list[JsonObject] = [{"key": "overview", "title": "Overview", "kind": "fields", "fields": metadata(data)}]
    if data["description"]:
        out.append({"key": "description", "title": "Description", "kind": "text", "text": data["description"]})
    if data["synonyms"]:
        out.append({"key": "synonyms", "title": "Synonyms", "kind": "table", "rows": [{"name": item} for item in data["synonyms"]]})
    if data["xrefs"]:
        out.append({"key": "xrefs", "title": "Cross-references", "kind": "table", "rows": data["xrefs"]})
    if data["pathways"]:
        out.append({"key": "pathways", "title": "Pathways", "kind": "table", "rows": [{"name": item} for item in data["pathways"]]})
    if data["diseases"]:
        out.append({"key": "diseases", "title": "Diseases", "kind": "table", "rows": [{"name": item} for item in data["diseases"]]})
    return out


def previews(data: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    out: list[JsonObject] = [
        {
            "kind": "table",
            "title": "HMDB record details",
            "provider": "HMDB",
            "id": data["id"],
            "url": data["url"],
            "section_key": "overview",
            "actions": display_actions(links),
            "data": {"columns": ["label", "value"], "rows": metadata(data)},
        }
    ]
    if data["category"] == "metabolites" and (data["smiles"] or data["inchi"] or data["inchikey"]):
        out.append(
            {
                "kind": "chemical_structure",
                "title": "Chemical structure",
                "provider": "HMDB",
                "id": data["id"],
                "url": data["url"],
                "data": {"smiles": data["smiles"], "inchi": data["inchi"], "inchikey": data["inchikey"], "formula": data["formula"]},
            }
        )
    if data["category"] == "proteins" and data["sequence"]:
        out.append(
            {
                "kind": "sequence",
                "title": "Protein sequence",
                "provider": "HMDB",
                "id": data["id"],
                "url": data["url"],
                "data": {"sequence": data["sequence"], "alphabet": "protein", "length": len(data["sequence"])},
            }
        )
    if data["xrefs"]:
        out.append(
            {
                "kind": "xref_groups",
                "title": "Cross-references",
                "provider": "HMDB",
                "id": data["id"],
                "url": data["url"],
                "section_key": "xrefs",
                "data": {"groups": xref_groups(data["xrefs"])},
            }
        )
    if data["description"]:
        out.append(
            {
                "kind": "text",
                "title": "Description",
                "provider": "HMDB",
                "id": data["id"],
                "url": data["url"],
                "section_key": "description",
                "data": {"text": data["description"]},
            }
        )
    return out


def record_links(data: JsonObject) -> list[JsonObject]:
    return compact_links(link("Open HMDB record", data["url"], primary=True))


def record_identifiers(data: JsonObject) -> JsonObject:
    identifiers: JsonObject = {"hmdb": {"namespace": "hmdb", "id": data["id"], "label": data["id"], "url": data["url"]}}
    if data["uniprot_id"]:
        identifiers["uniprot"] = {"namespace": "uniprot", "id": data["uniprot_id"], "label": data["uniprot_id"], "url": xref_url("UniProt", data["uniprot_id"])}
    if data["inchikey"]:
        identifiers["inchikey"] = {"namespace": "inchikey", "id": data["inchikey"], "label": data["inchikey"]}
    return identifiers


def split_xref(value: str) -> tuple[str, str]:
    if ":" not in value:
        return "xref", value
    return value.split(":", 1)


def xref_url(database: str, identifier: str) -> str:
    if not identifier:
        return ""
    if database == "PubChem":
        return f"https://pubchem.ncbi.nlm.nih.gov/compound/{identifier}"
    if database == "ChEBI":
        return f"https://www.ebi.ac.uk/chebi/searchId.do?chebiId={identifier}"
    if database == "KEGG":
        return f"https://www.kegg.jp/entry/{identifier}"
    if database == "UniProt":
        return f"https://www.uniprot.org/uniprotkb/{identifier}/entry"
    return ""


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
        key = (item.get("database"), item.get("id"), item.get("label"))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
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
