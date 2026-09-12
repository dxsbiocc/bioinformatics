"""Front-end compatible record envelopes for ChEMBL results."""

from __future__ import annotations

import urllib.parse

from .constants import (
    CHEMBL_REST_BASE_URL,
    CHEMBL_WEBSITE_BASE_URL,
    MAX_SYNONYMS,
    MAX_XREFS,
    RECORD_SCHEMA_VERSION,
    JsonObject,
)
from .utils import normalize_space, safe_list


def chembl_molecule_record(
    molecule: JsonObject,
    *,
    website_base_url: str = CHEMBL_WEBSITE_BASE_URL,
    api_base_url: str = CHEMBL_REST_BASE_URL,
    max_synonyms: int = MAX_SYNONYMS,
    max_xrefs: int = MAX_XREFS,
) -> JsonObject:
    normalized = normalize_molecule(
        molecule,
        website_base_url=website_base_url,
        api_base_url=api_base_url,
        max_synonyms=max_synonyms,
        max_xrefs=max_xrefs,
    )
    molecule_id = normalized["molecule_chembl_id"]
    title = normalized["pref_name"] or molecule_id
    links = molecule_links(normalized)
    description = molecule_description(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "chemical.compound",
        "record_type": "chembl_molecule",
        "database": "chembl",
        "id": molecule_id,
        "stable_id": f"ChEMBL:{molecule_id}",
        "label": title,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "chembl",
        "identifiers": molecule_identifiers(normalized),
        "links": links,
        "display": {
            "component": "compound",
            "chip_label": title,
            "icon": "chembl",
            "title": title,
            "subtitle": molecule_subtitle(normalized),
            "description": description,
            "metadata": molecule_metadata(normalized),
            "badges": compact_badges(
                ("ChEMBL", "source"),
                (molecule_id, "identifier"),
                (normalized["molecule_type"], "type"),
                (f"phase {normalized['max_phase']}" if normalized["max_phase"] else "", "phase"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": description,
                "icon": "chembl",
                "fields": compact_fields(
                    ("ChEMBL ID", molecule_id),
                    ("Name", normalized["pref_name"]),
                    ("Type", normalized["molecule_type"]),
                    ("Formula", normalized["properties"].get("full_molformula")),
                    ("Molecular weight", normalized["properties"].get("full_mwt")),
                    ("Max phase", normalized["max_phase"]),
                    ("First approval", normalized["first_approval"]),
                    ("InChIKey", normalized["standard_inchi_key"]),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": molecule_sections(normalized),
            "previews": molecule_previews(normalized, links),
        },
        "related": {
            "synonyms": normalized["synonyms"],
            "cross_references": normalized["cross_references"],
            "atc_classifications": normalized["atc_classifications"],
        },
        "data": normalized,
    }


def chembl_target_record(
    target: JsonObject,
    *,
    website_base_url: str = CHEMBL_WEBSITE_BASE_URL,
    api_base_url: str = CHEMBL_REST_BASE_URL,
    max_xrefs: int = MAX_XREFS,
) -> JsonObject:
    normalized = normalize_target(
        target,
        website_base_url=website_base_url,
        api_base_url=api_base_url,
        max_xrefs=max_xrefs,
    )
    target_id = normalized["target_chembl_id"]
    title = normalized["pref_name"] or target_id
    links = target_links(normalized)
    description = " | ".join(part for part in [normalized["target_type"], normalized["organism"]] if part)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "protein",
        "record_type": "chembl_target",
        "database": "chembl",
        "id": target_id,
        "stable_id": f"ChEMBL:target:{target_id}",
        "label": title,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "chembl",
        "identifiers": target_identifiers(normalized),
        "links": links,
        "display": {
            "component": "protein",
            "chip_label": title,
            "icon": "chembl",
            "title": title,
            "subtitle": description,
            "description": description,
            "metadata": target_metadata(normalized),
            "badges": compact_badges(
                ("ChEMBL", "source"),
                (target_id, "identifier"),
                (normalized["target_type"], "target_type"),
                (normalized["organism"], "organism"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": description,
                "icon": "chembl",
                "fields": compact_fields(
                    ("Target ID", target_id),
                    ("Name", normalized["pref_name"]),
                    ("Type", normalized["target_type"]),
                    ("Organism", normalized["organism"]),
                    ("TaxID", normalized["tax_id"]),
                    ("Components", str(len(normalized["components"]))),
                    ("Accessions", ", ".join(component["accession"] for component in normalized["components"] if component.get("accession"))),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": target_sections(normalized),
            "previews": target_previews(normalized, links),
        },
        "related": {
            "components": normalized["components"],
            "cross_references": normalized["xref_groups"],
        },
        "data": normalized,
    }


def chembl_activity_record(
    *,
    query_label: str,
    activities: list[JsonObject],
    total: int,
    params: JsonObject,
    website_base_url: str = CHEMBL_WEBSITE_BASE_URL,
    api_base_url: str = CHEMBL_REST_BASE_URL,
) -> JsonObject:
    normalized = normalize_activity_search(
        query_label=query_label,
        activities=activities,
        total=total,
        params=params,
        website_base_url=website_base_url,
        api_base_url=api_base_url,
    )
    links = activity_links(normalized)
    title = f"ChEMBL activities: {query_label}"
    description = f"{total} activity records matched {query_label}"
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "dataset",
        "record_type": "chembl_activity_search",
        "database": "chembl",
        "id": query_label,
        "stable_id": f"ChEMBL:activities:{query_label}",
        "label": query_label,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "chembl",
        "identifiers": {"chembl_activity_query": {"namespace": "chembl.activity_query", "id": query_label, "label": query_label, "url": normalized["url"]}},
        "links": links,
        "display": dataset_display(
            title=title,
            label=query_label,
            description=description,
            metadata=compact_fields(
                ("Query", query_label),
                ("Activities", str(total)),
                ("Returned", str(len(normalized["activities"]))),
                ("Molecules", ", ".join(unique_values(normalized["activities"], "molecule_chembl_id", 3))),
                ("Targets", ", ".join(unique_values(normalized["activities"], "target_pref_name", 3))),
            ),
            badges=compact_badges(("ChEMBL", "source"), ("activities", "record_type"), (f"{total} activities", "count")),
            links=links,
            sections=activity_sections(normalized),
            previews=activity_previews(normalized, links),
            url=normalized["url"],
        ),
        "related": {"activities": normalized["activities"]},
        "data": normalized,
    }


def chembl_assay_record(
    assay: JsonObject,
    *,
    website_base_url: str = CHEMBL_WEBSITE_BASE_URL,
    api_base_url: str = CHEMBL_REST_BASE_URL,
) -> JsonObject:
    normalized = normalize_assay(
        assay,
        website_base_url=website_base_url,
        api_base_url=api_base_url,
    )
    assay_id = normalized["assay_chembl_id"]
    title = f"ChEMBL assay: {assay_id}"
    description = normalized["description"] or normalized["assay_type_description"] or assay_id
    links = assay_links(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "dataset",
        "record_type": "chembl_assay",
        "database": "chembl",
        "id": assay_id,
        "stable_id": f"ChEMBL:assay:{assay_id}",
        "label": assay_id,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "chembl",
        "identifiers": {
            "chembl_assay": {
                "namespace": "chembl.assay",
                "id": assay_id,
                "label": f"ChEMBL:{assay_id}",
                "url": normalized["url"],
            }
        },
        "links": links,
        "display": dataset_display(
            title=title,
            label=assay_id,
            description=description,
            metadata=assay_metadata(normalized),
            badges=compact_badges(
                ("ChEMBL", "source"),
                ("assay", "record_type"),
                (normalized["assay_type"], "assay_type"),
                (normalized["organism"], "organism"),
                (f"confidence {normalized['confidence_score']}" if normalized["confidence_score"] else "", "confidence"),
            ),
            links=links,
            sections=assay_sections(normalized),
            previews=assay_previews(normalized, links),
            url=normalized["url"],
        ),
        "related": {
            "target_chembl_id": normalized["target_chembl_id"],
            "document_chembl_id": normalized["document_chembl_id"],
            "parameters": normalized["parameters"],
            "classifications": normalized["classifications"],
        },
        "data": normalized,
    }


def chembl_document_record(
    document: JsonObject,
    *,
    website_base_url: str = CHEMBL_WEBSITE_BASE_URL,
    api_base_url: str = CHEMBL_REST_BASE_URL,
) -> JsonObject:
    normalized = normalize_document(
        document,
        website_base_url=website_base_url,
        api_base_url=api_base_url,
    )
    document_id = normalized["document_chembl_id"]
    title = normalized["title"] or document_id
    description = document_citation_text(normalized)
    links = document_links(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "citation",
        "record_type": "chembl_document",
        "database": "chembl",
        "id": document_id,
        "stable_id": f"ChEMBL:document:{document_id}",
        "label": document_id,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "chembl",
        "identifiers": document_identifiers(normalized),
        "links": links,
        "display": {
            "component": "citation",
            "chip_label": document_chip_label(normalized),
            "icon": "chembl",
            "title": title,
            "subtitle": description,
            "description": normalize_space(normalized["abstract"]),
            "metadata": document_metadata(normalized),
            "badges": compact_badges(
                ("ChEMBL", "source"),
                (document_id, "identifier"),
                (normalized["doc_type"], "type"),
                (normalized["year"], "year"),
                ("PMID" if normalized["pubmed_id"] else "", "identifier"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": description,
                "icon": "chembl",
                "fields": document_metadata(normalized) + compact_fields(("URL", normalized["url"])),
            },
            "primary_url": normalized["primary_url"],
            "sections": document_sections(normalized),
            "previews": document_previews(normalized, links),
        },
        "related": {
            "pubmed_id": normalized["pubmed_id"],
            "doi": normalized["doi"],
            "chembl_release": normalized["chembl_release"],
        },
        "data": normalized,
    }


def chembl_mechanism_record(
    *,
    query_label: str,
    mechanisms: list[JsonObject],
    total: int,
    params: JsonObject,
    website_base_url: str = CHEMBL_WEBSITE_BASE_URL,
    api_base_url: str = CHEMBL_REST_BASE_URL,
) -> JsonObject:
    normalized = normalize_mechanism_search(
        query_label=query_label,
        mechanisms=mechanisms,
        total=total,
        params=params,
        website_base_url=website_base_url,
        api_base_url=api_base_url,
    )
    links = mechanism_links(normalized)
    title = f"ChEMBL mechanisms: {query_label}"
    description = f"{total} mechanism records matched {query_label}"
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "dataset",
        "record_type": "chembl_mechanism_search",
        "database": "chembl",
        "id": query_label,
        "stable_id": f"ChEMBL:mechanisms:{query_label}",
        "label": query_label,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "chembl",
        "identifiers": {"chembl_mechanism_query": {"namespace": "chembl.mechanism_query", "id": query_label, "label": query_label, "url": normalized["url"]}},
        "links": links,
        "display": dataset_display(
            title=title,
            label=query_label,
            description=description,
            metadata=compact_fields(
                ("Query", query_label),
                ("Mechanisms", str(total)),
                ("Returned", str(len(normalized["mechanisms"]))),
                ("Actions", ", ".join(unique_values(normalized["mechanisms"], "action_type", 3))),
                ("Targets", ", ".join(unique_values(normalized["mechanisms"], "target_chembl_id", 3))),
            ),
            badges=compact_badges(("ChEMBL", "source"), ("mechanisms", "record_type"), (f"{total} mechanisms", "count")),
            links=links,
            sections=mechanism_sections(normalized),
            previews=mechanism_previews(normalized, links),
            url=normalized["url"],
        ),
        "related": {"mechanisms": normalized["mechanisms"]},
        "data": normalized,
    }


def chembl_drug_indication_record(
    *,
    molecule_chembl_id: str,
    indications: list[JsonObject],
    total: int,
    params: JsonObject,
    website_base_url: str = CHEMBL_WEBSITE_BASE_URL,
    api_base_url: str = CHEMBL_REST_BASE_URL,
) -> JsonObject:
    normalized = normalize_drug_indication_search(
        molecule_chembl_id=molecule_chembl_id,
        indications=indications,
        total=total,
        params=params,
        website_base_url=website_base_url,
        api_base_url=api_base_url,
    )
    links = drug_indication_links(normalized)
    title = f"ChEMBL drug indications: {molecule_chembl_id}"
    description = f"{total} indication records matched {molecule_chembl_id}"
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "dataset",
        "record_type": "chembl_drug_indications",
        "database": "chembl",
        "id": molecule_chembl_id,
        "stable_id": f"ChEMBL:drug_indications:{molecule_chembl_id}",
        "label": molecule_chembl_id,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "chembl",
        "identifiers": {
            "chembl_molecule": {
                "namespace": "chembl.molecule",
                "id": molecule_chembl_id,
                "label": f"ChEMBL:{molecule_chembl_id}",
                "url": normalized["url"],
            }
        },
        "links": links,
        "display": dataset_display(
            title=title,
            label=molecule_chembl_id,
            description=description,
            metadata=compact_fields(
                ("Molecule", molecule_chembl_id),
                ("Indications", str(total)),
                ("Returned", str(len(normalized["indications"]))),
                ("Terms", ", ".join(unique_values(normalized["indications"], "term", 3))),
                ("Max phases", ", ".join(unique_values(normalized["indications"], "max_phase_for_ind", 3))),
            ),
            badges=compact_badges(("ChEMBL", "source"), ("drug indications", "record_type"), (f"{total} indications", "count")),
            links=links,
            sections=drug_indication_sections(normalized),
            previews=drug_indication_previews(normalized, links),
            url=normalized["url"],
        ),
        "related": {"indications": normalized["indications"]},
        "data": normalized,
    }


def normalize_molecule(
    molecule: JsonObject,
    *,
    website_base_url: str,
    api_base_url: str,
    max_synonyms: int,
    max_xrefs: int,
) -> JsonObject:
    molecule_id = normalize_space(molecule.get("molecule_chembl_id"))
    structures = molecule.get("molecule_structures") if isinstance(molecule.get("molecule_structures"), dict) else {}
    properties = molecule.get("molecule_properties") if isinstance(molecule.get("molecule_properties"), dict) else {}
    return {
        "molecule_chembl_id": molecule_id,
        "pref_name": normalize_space(molecule.get("pref_name")),
        "molecule_type": normalize_space(molecule.get("molecule_type")),
        "max_phase": normalize_space(molecule.get("max_phase")),
        "first_approval": normalize_space(molecule.get("first_approval")),
        "therapeutic_flag": boolish(molecule.get("therapeutic_flag")),
        "black_box_warning": boolish(molecule.get("black_box_warning")),
        "withdrawn_flag": boolish(molecule.get("withdrawn_flag")),
        "oral": boolish(molecule.get("oral")),
        "parenteral": boolish(molecule.get("parenteral")),
        "topical": boolish(molecule.get("topical")),
        "molecule_properties": {key: properties.get(key) for key in property_keys() if properties.get(key) is not None},
        "properties": {key: properties.get(key) for key in property_keys() if properties.get(key) is not None},
        "canonical_smiles": normalize_space(structures.get("canonical_smiles")),
        "standard_inchi": normalize_space(structures.get("standard_inchi")),
        "standard_inchi_key": normalize_space(structures.get("standard_inchi_key")),
        "molfile": structures.get("molfile") if isinstance(structures.get("molfile"), str) else "",
        "atc_classifications": [normalize_space(item) for item in safe_list(molecule.get("atc_classifications")) if normalize_space(item)],
        "synonyms": normalize_synonyms(molecule.get("molecule_synonyms"), max_synonyms=max_synonyms),
        "synonyms_truncated": len(safe_list(molecule.get("molecule_synonyms"))) > max_synonyms,
        "cross_references": normalize_molecule_xrefs(molecule.get("cross_references"), max_xrefs=max_xrefs),
        "cross_references_truncated": len(safe_list(molecule.get("cross_references"))) > max_xrefs,
        "url": chembl_molecule_url(molecule_id, website_base_url),
        "api_url": chembl_api_url(f"molecule/{molecule_id}.json", api_base_url),
        "image_url": chembl_image_url(molecule_id, api_base_url),
        "svg_url": chembl_image_url(molecule_id, api_base_url, fmt="svg"),
    }


def normalize_target(
    target: JsonObject,
    *,
    website_base_url: str,
    api_base_url: str,
    max_xrefs: int,
) -> JsonObject:
    target_id = normalize_space(target.get("target_chembl_id"))
    components = normalize_components(target.get("target_components"), max_xrefs=max_xrefs)
    return {
        "target_chembl_id": target_id,
        "pref_name": normalize_space(target.get("pref_name")),
        "target_type": normalize_space(target.get("target_type")),
        "organism": normalize_space(target.get("organism")),
        "tax_id": normalize_space(target.get("tax_id")),
        "components": components,
        "xref_groups": component_xref_groups(components),
        "url": chembl_target_url(target_id, website_base_url),
        "api_url": chembl_api_url(f"target/{target_id}.json", api_base_url),
    }


def normalize_assay(
    assay: JsonObject,
    *,
    website_base_url: str,
    api_base_url: str,
) -> JsonObject:
    assay_id = normalize_space(assay.get("assay_chembl_id"))
    target_id = normalize_space(assay.get("target_chembl_id"))
    document_id = normalize_space(assay.get("document_chembl_id"))
    bao_format = normalize_space(assay.get("bao_format"))
    return {
        "assay_chembl_id": assay_id,
        "description": normalize_space(assay.get("description")),
        "assay_type": normalize_space(assay.get("assay_type")),
        "assay_type_description": normalize_space(assay.get("assay_type_description")),
        "organism": normalize_space(assay.get("assay_organism")),
        "tax_id": normalize_space(assay.get("assay_tax_id")),
        "tissue": normalize_space(assay.get("assay_tissue")),
        "cell_type": normalize_space(assay.get("assay_cell_type")),
        "cell_chembl_id": normalize_space(assay.get("cell_chembl_id")),
        "strain": normalize_space(assay.get("assay_strain")),
        "subcellular_fraction": normalize_space(assay.get("assay_subcellular_fraction")),
        "test_type": normalize_space(assay.get("assay_test_type")),
        "category": normalize_space(assay.get("assay_category")),
        "group": normalize_space(assay.get("assay_group")),
        "bao_format": bao_format,
        "bao_label": normalize_space(assay.get("bao_label")),
        "bao_url": ontology_term_url(bao_format),
        "confidence_score": normalize_space(assay.get("confidence_score")),
        "confidence_description": normalize_space(assay.get("confidence_description")),
        "relationship_type": normalize_space(assay.get("relationship_type")),
        "relationship_description": normalize_space(assay.get("relationship_description")),
        "target_chembl_id": target_id,
        "target_url": chembl_target_url(target_id, website_base_url),
        "document_chembl_id": document_id,
        "document_url": chembl_document_url(document_id, website_base_url),
        "src_id": normalize_space(assay.get("src_id")),
        "src_assay_id": normalize_space(assay.get("src_assay_id")),
        "aidx": normalize_space(assay.get("aidx")),
        "variant_sequence": normalize_space(assay.get("variant_sequence")),
        "parameters": normalize_assay_parameters(assay.get("assay_parameters")),
        "classifications": normalize_assay_classifications(assay.get("assay_classifications")),
        "url": chembl_assay_url(assay_id, website_base_url),
        "api_url": chembl_api_url(f"assay/{assay_id}.json", api_base_url),
    }


def normalize_document(
    document: JsonObject,
    *,
    website_base_url: str,
    api_base_url: str,
) -> JsonObject:
    document_id = normalize_space(document.get("document_chembl_id"))
    pubmed_id = normalize_space(document.get("pubmed_id"))
    doi = normalize_space(document.get("doi") or document.get("doi_chembl"))
    release = document.get("chembl_release") if isinstance(document.get("chembl_release"), dict) else {}
    url = chembl_document_url(document_id, website_base_url)
    pubmed = pubmed_url(pubmed_id)
    doi_link = doi_url(doi)
    return {
        "document_chembl_id": document_id,
        "title": normalize_space(document.get("title")),
        "abstract": normalize_space(document.get("abstract")),
        "authors": normalize_space(document.get("authors")),
        "journal": normalize_space(document.get("journal")),
        "journal_full_title": normalize_space(document.get("journal_full_title")),
        "year": normalize_space(document.get("year")),
        "volume": normalize_space(document.get("volume")),
        "issue": normalize_space(document.get("issue")),
        "first_page": normalize_space(document.get("first_page")),
        "last_page": normalize_space(document.get("last_page")),
        "doc_type": normalize_space(document.get("doc_type")),
        "doi": doi,
        "doi_url": doi_link,
        "pubmed_id": pubmed_id,
        "pubmed_url": pubmed,
        "patent_id": normalize_space(document.get("patent_id")),
        "src_id": normalize_space(document.get("src_id")),
        "contact": normalize_space(document.get("contact")),
        "chembl_release": normalize_space(release.get("chembl_release")),
        "chembl_release_date": normalize_space(release.get("creation_date")),
        "url": url,
        "api_url": chembl_api_url(f"document/{document_id}.json", api_base_url),
        "primary_url": pubmed or doi_link or url,
    }


def normalize_activity_search(
    *,
    query_label: str,
    activities: list[JsonObject],
    total: int,
    params: JsonObject,
    website_base_url: str,
    api_base_url: str,
) -> JsonObject:
    rows = [normalize_activity(item, website_base_url=website_base_url) for item in activities]
    return {
        "query": query_label,
        "params": dict(params),
        "activities": rows,
        "total_activities": total,
        "activities_truncated": total > len(rows),
        "url": activity_browser_url(params, website_base_url),
        "api_url": chembl_api_url("activity.json", api_base_url, params),
    }


def normalize_mechanism_search(
    *,
    query_label: str,
    mechanisms: list[JsonObject],
    total: int,
    params: JsonObject,
    website_base_url: str,
    api_base_url: str,
) -> JsonObject:
    rows = [normalize_mechanism(item, website_base_url=website_base_url) for item in mechanisms]
    return {
        "query": query_label,
        "params": dict(params),
        "mechanisms": rows,
        "total_mechanisms": total,
        "mechanisms_truncated": total > len(rows),
        "url": mechanism_browser_url(params, website_base_url),
        "api_url": chembl_api_url("mechanism.json", api_base_url, params),
    }


def normalize_drug_indication_search(
    *,
    molecule_chembl_id: str,
    indications: list[JsonObject],
    total: int,
    params: JsonObject,
    website_base_url: str,
    api_base_url: str,
) -> JsonObject:
    rows = [normalize_drug_indication(item, website_base_url=website_base_url) for item in indications]
    return {
        "molecule_chembl_id": molecule_chembl_id,
        "params": dict(params),
        "indications": rows,
        "total_indications": total,
        "indications_truncated": total > len(rows),
        "url": chembl_molecule_url(molecule_chembl_id, website_base_url),
        "api_url": chembl_api_url("drug_indication.json", api_base_url, params),
    }


def normalize_activity(item: JsonObject, *, website_base_url: str) -> JsonObject:
    molecule_id = normalize_space(item.get("molecule_chembl_id"))
    target_id = normalize_space(item.get("target_chembl_id"))
    document_id = normalize_space(item.get("document_chembl_id"))
    assay_id = normalize_space(item.get("assay_chembl_id"))
    return {
        "activity_id": item.get("activity_id"),
        "molecule_chembl_id": molecule_id,
        "molecule_pref_name": normalize_space(item.get("molecule_pref_name")),
        "target_chembl_id": target_id,
        "target_pref_name": normalize_space(item.get("target_pref_name")),
        "target_organism": normalize_space(item.get("target_organism")),
        "assay_chembl_id": assay_id,
        "assay_type": normalize_space(item.get("assay_type")),
        "assay_description": normalize_space(item.get("assay_description")),
        "standard_type": normalize_space(item.get("standard_type") or item.get("type")),
        "standard_relation": normalize_space(item.get("standard_relation") or item.get("relation")),
        "standard_value": normalize_space(item.get("standard_value") or item.get("value")),
        "standard_units": normalize_space(item.get("standard_units") or item.get("units")),
        "pchembl_value": normalize_space(item.get("pchembl_value")),
        "document_chembl_id": document_id,
        "document_journal": normalize_space(item.get("document_journal")),
        "document_year": normalize_space(item.get("document_year")),
        "molecule_url": chembl_molecule_url(molecule_id, website_base_url),
        "target_url": chembl_target_url(target_id, website_base_url),
        "assay_url": chembl_assay_url(assay_id, website_base_url),
        "document_url": chembl_document_url(document_id, website_base_url),
    }


def normalize_mechanism(item: JsonObject, *, website_base_url: str) -> JsonObject:
    molecule_id = normalize_space(item.get("molecule_chembl_id"))
    target_id = normalize_space(item.get("target_chembl_id"))
    return {
        "mec_id": item.get("mec_id"),
        "molecule_chembl_id": molecule_id,
        "target_chembl_id": target_id,
        "mechanism_of_action": normalize_space(item.get("mechanism_of_action")),
        "action_type": normalize_space(item.get("action_type")),
        "max_phase": normalize_space(item.get("max_phase")),
        "direct_interaction": boolish(item.get("direct_interaction")),
        "disease_efficacy": boolish(item.get("disease_efficacy")),
        "molecular_mechanism": boolish(item.get("molecular_mechanism")),
        "refs": normalize_mechanism_refs(item.get("mechanism_refs")),
        "molecule_url": chembl_molecule_url(molecule_id, website_base_url),
        "target_url": chembl_target_url(target_id, website_base_url),
    }


def normalize_drug_indication(item: JsonObject, *, website_base_url: str) -> JsonObject:
    molecule_id = normalize_space(item.get("molecule_chembl_id"))
    parent_id = normalize_space(item.get("parent_molecule_chembl_id"))
    efo_id = normalize_space(item.get("efo_id"))
    mesh_id = normalize_space(item.get("mesh_id"))
    efo_term = normalize_space(item.get("efo_term"))
    mesh_heading = normalize_space(item.get("mesh_heading"))
    return {
        "drugind_id": item.get("drugind_id"),
        "molecule_chembl_id": molecule_id,
        "parent_molecule_chembl_id": parent_id,
        "term": efo_term or mesh_heading,
        "efo_id": efo_id,
        "efo_term": efo_term,
        "efo_url": ontology_term_url(efo_id),
        "mesh_id": mesh_id,
        "mesh_heading": mesh_heading,
        "mesh_url": mesh_url(mesh_id),
        "max_phase_for_ind": normalize_space(item.get("max_phase_for_ind")),
        "refs": normalize_indication_refs(item.get("indication_refs")),
        "molecule_url": chembl_molecule_url(molecule_id, website_base_url),
        "parent_molecule_url": chembl_molecule_url(parent_id, website_base_url),
    }


def molecule_sections(normalized: JsonObject) -> list[JsonObject]:
    sections = [
        {"key": "properties", "title": "Molecule properties", "kind": "table", "rows": property_rows(normalized["properties"])},
        {"key": "structure", "title": "Chemical structure", "kind": "chemical_structure", "fields": compact_fields(("SMILES", normalized["canonical_smiles"]), ("InChIKey", normalized["standard_inchi_key"]))},
    ]
    if normalized["synonyms"]:
        sections.append({"key": "synonyms", "title": "Synonyms", "kind": "table", "rows": normalized["synonyms"], "summary": {"truncated": normalized["synonyms_truncated"]}})
    if normalized["cross_references"]:
        sections.append({"key": "cross_references", "title": "Cross-references", "kind": "table", "rows": normalized["cross_references"], "summary": {"truncated": normalized["cross_references_truncated"]}})
    return sections


def molecule_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews = [
        {
            "kind": "chemical_structure",
            "title": "Chemical structure",
            "provider": "ChEMBL",
            "id": normalized["molecule_chembl_id"],
            "url": normalized["image_url"],
            "section_key": "structure",
            "actions": display_actions(links),
            "data": {
                "smiles": normalized["canonical_smiles"],
                "inchi": normalized["standard_inchi"],
                "inchi_key": normalized["standard_inchi_key"],
                "molfile": normalized["molfile"],
                "image_url": normalized["image_url"],
                "svg_url": normalized["svg_url"],
            },
        },
        table_preview("properties", "Molecule properties", normalized["molecule_chembl_id"], normalized["url"], property_columns(), property_rows(normalized["properties"]), actions=display_actions(links)),
        xref_preview(normalized["molecule_chembl_id"], normalized["url"], molecule_xref_groups(normalized), links),
    ]
    if normalized["synonyms"]:
        previews.append(table_preview("synonyms", "Synonyms", normalized["molecule_chembl_id"], normalized["url"], synonym_columns(), normalized["synonyms"], actions=display_actions(links), truncated=normalized["synonyms_truncated"]))
    return previews


def target_sections(normalized: JsonObject) -> list[JsonObject]:
    sections = [{"key": "components", "title": "Target components", "kind": "table", "rows": normalized["components"]}]
    if normalized["xref_groups"]:
        sections.append({"key": "xref_groups", "title": "Cross-reference groups", "kind": "xref_groups", "groups": normalized["xref_groups"]})
    return sections


def target_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    return [
        table_preview("components", "Target components", normalized["target_chembl_id"], normalized["url"], component_columns(), normalized["components"], actions=display_actions(links)),
        xref_preview(normalized["target_chembl_id"], normalized["url"], normalized["xref_groups"], links),
    ]


def assay_sections(normalized: JsonObject) -> list[JsonObject]:
    sections = [
        {
            "key": "overview",
            "title": "Assay overview",
            "kind": "table",
            "rows": assay_overview_rows(normalized),
        }
    ]
    if normalized["parameters"]:
        sections.append({"key": "parameters", "title": "Assay parameters", "kind": "table", "rows": normalized["parameters"]})
    if normalized["classifications"]:
        sections.append({"key": "classifications", "title": "Assay classifications", "kind": "table", "rows": normalized["classifications"]})
    return sections


def assay_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews = [
        table_preview("overview", "Assay overview", normalized["assay_chembl_id"], normalized["url"], property_columns(), assay_overview_rows(normalized), actions=display_actions(links)),
        xref_preview(normalized["assay_chembl_id"], normalized["url"], assay_xref_groups(normalized), links),
    ]
    if normalized["parameters"]:
        previews.append(table_preview("parameters", "Assay parameters", normalized["assay_chembl_id"], normalized["url"], assay_parameter_columns(), normalized["parameters"], actions=display_actions(links)))
    if normalized["classifications"]:
        previews.append(table_preview("classifications", "Assay classifications", normalized["assay_chembl_id"], normalized["url"], assay_classification_columns(), normalized["classifications"], actions=display_actions(links)))
    return previews


def document_sections(normalized: JsonObject) -> list[JsonObject]:
    sections = [
        {
            "key": "metadata",
            "title": "Document metadata",
            "kind": "table",
            "rows": document_metadata(normalized),
        }
    ]
    if normalized["abstract"]:
        sections.append({"key": "abstract", "title": "Abstract", "kind": "text", "text": normalized["abstract"]})
    return sections


def document_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews = [
        table_preview("metadata", "Document metadata", normalized["document_chembl_id"], normalized["primary_url"], property_columns(), document_metadata(normalized), actions=display_actions(links)),
        xref_preview(normalized["document_chembl_id"], normalized["primary_url"], document_xref_groups(normalized), links),
    ]
    if normalized["abstract"]:
        previews.append(
            {
                "kind": "text",
                "title": "Abstract",
                "provider": "ChEMBL",
                "id": normalized["document_chembl_id"],
                "url": normalized["primary_url"],
                "section_key": "abstract",
                "actions": display_actions(links),
                "data": {"text": normalized["abstract"]},
            }
        )
    return previews


def activity_sections(normalized: JsonObject) -> list[JsonObject]:
    return [{"key": "activities", "title": "Activities", "kind": "table", "rows": normalized["activities"], "summary": {"total": normalized["total_activities"], "truncated": normalized["activities_truncated"]}}]


def activity_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    return [
        table_preview("activities", "Activities", normalized["query"], normalized["url"], activity_columns(), normalized["activities"], actions=display_actions(links), total=normalized["total_activities"], truncated=normalized["activities_truncated"]),
        xref_preview(normalized["query"], normalized["url"], activity_xref_groups(normalized), links),
    ]


def mechanism_sections(normalized: JsonObject) -> list[JsonObject]:
    return [{"key": "mechanisms", "title": "Mechanisms", "kind": "table", "rows": normalized["mechanisms"], "summary": {"total": normalized["total_mechanisms"], "truncated": normalized["mechanisms_truncated"]}}]


def mechanism_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    return [
        table_preview("mechanisms", "Mechanisms", normalized["query"], normalized["url"], mechanism_columns(), normalized["mechanisms"], actions=display_actions(links), total=normalized["total_mechanisms"], truncated=normalized["mechanisms_truncated"]),
        xref_preview(normalized["query"], normalized["url"], mechanism_xref_groups(normalized), links),
    ]


def drug_indication_sections(normalized: JsonObject) -> list[JsonObject]:
    return [
        {
            "key": "indications",
            "title": "Drug indications",
            "kind": "table",
            "rows": normalized["indications"],
            "summary": {
                "total": normalized["total_indications"],
                "truncated": normalized["indications_truncated"],
            },
        }
    ]


def drug_indication_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    return [
        table_preview(
            "indications",
            "Drug indications",
            normalized["molecule_chembl_id"],
            normalized["url"],
            drug_indication_columns(),
            normalized["indications"],
            actions=display_actions(links),
            total=normalized["total_indications"],
            truncated=normalized["indications_truncated"],
        ),
        xref_preview(normalized["molecule_chembl_id"], normalized["url"], drug_indication_xref_groups(normalized), links),
    ]


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
        "icon": "chembl",
        "title": title,
        "subtitle": description,
        "description": description,
        "metadata": metadata,
        "badges": badges,
        "actions": display_actions(links),
        "hover": {"title": title, "subtitle": description, "icon": "chembl", "fields": metadata + [{"label": "URL", "value": url}]},
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
        "provider": "ChEMBL",
        "id": identifier,
        "url": url,
        "section_key": section_key,
        "actions": actions,
        "data": {"columns": columns, "rows": rows, "total_rows": total if total is not None else len(rows), "shown_rows": len(rows), "truncated": truncated},
    }


def xref_preview(identifier: str, url: str, groups: list[JsonObject], links: list[JsonObject]) -> JsonObject:
    return {"kind": "xref_groups", "title": "Cross-reference groups", "provider": "ChEMBL", "id": identifier, "url": url, "actions": display_actions(links), "data": {"groups": groups}}


def molecule_links(normalized: JsonObject) -> list[JsonObject]:
    return compact_links(
        link("Open in ChEMBL", normalized["url"], primary=True),
        link("ChEMBL API record", normalized["api_url"], kind="related"),
        link("Structure image", normalized["image_url"], kind="related"),
    )


def target_links(normalized: JsonObject) -> list[JsonObject]:
    links = [link("Open in ChEMBL", normalized["url"], primary=True), link("ChEMBL API record", normalized["api_url"], kind="related")]
    for component in normalized["components"][:1]:
        accession = normalize_space(component.get("accession"))
        if accession:
            links.append(link("Open in UniProt", f"https://www.uniprot.org/uniprotkb/{urllib.parse.quote(accession)}/entry", kind="related"))
    return compact_links(*links)


def assay_links(normalized: JsonObject) -> list[JsonObject]:
    return compact_links(
        link("Open in ChEMBL", normalized["url"], primary=True),
        link("ChEMBL API record", normalized["api_url"], kind="related"),
        link("Open target", normalized["target_url"], kind="related"),
        link("Open document", normalized["document_url"], kind="related"),
        link("Open BAO term", normalized["bao_url"], kind="related"),
    )


def document_links(normalized: JsonObject) -> list[JsonObject]:
    return compact_links(
        link("Open PubMed", normalized["pubmed_url"], primary=bool(normalized["pubmed_url"])),
        link("Open DOI", normalized["doi_url"], primary=not bool(normalized["pubmed_url"]) and bool(normalized["doi_url"])),
        link("Open in ChEMBL", normalized["url"], primary=not bool(normalized["pubmed_url"] or normalized["doi_url"])),
        link("ChEMBL API record", normalized["api_url"], kind="related"),
    )


def activity_links(normalized: JsonObject) -> list[JsonObject]:
    return compact_links(link("Open ChEMBL query", normalized["url"], primary=True), link("ChEMBL API query", normalized["api_url"], kind="related"))


def mechanism_links(normalized: JsonObject) -> list[JsonObject]:
    return compact_links(link("Open ChEMBL query", normalized["url"], primary=True), link("ChEMBL API query", normalized["api_url"], kind="related"))


def drug_indication_links(normalized: JsonObject) -> list[JsonObject]:
    return compact_links(link("Open ChEMBL molecule", normalized["url"], primary=True), link("ChEMBL API query", normalized["api_url"], kind="related"))


def molecule_identifiers(normalized: JsonObject) -> JsonObject:
    identifiers: JsonObject = {"chembl": {"namespace": "chembl.molecule", "id": normalized["molecule_chembl_id"], "label": f"ChEMBL:{normalized['molecule_chembl_id']}", "url": normalized["url"]}}
    if normalized["standard_inchi_key"]:
        identifiers["inchi_key"] = {"namespace": "inchi_key", "id": normalized["standard_inchi_key"], "label": normalized["standard_inchi_key"]}
    return identifiers


def target_identifiers(normalized: JsonObject) -> JsonObject:
    identifiers: JsonObject = {"chembl": {"namespace": "chembl.target", "id": normalized["target_chembl_id"], "label": f"ChEMBL:{normalized['target_chembl_id']}", "url": normalized["url"]}}
    accessions = [{"namespace": "uniprot", "id": component["accession"], "label": component["accession"], "url": f"https://www.uniprot.org/uniprotkb/{urllib.parse.quote(component['accession'])}/entry"} for component in normalized["components"] if component.get("accession")]
    if accessions:
        identifiers["uniprot"] = accessions
    return identifiers


def assay_xref_groups(normalized: JsonObject) -> list[JsonObject]:
    groups = [{"database": "ChEMBL Assay", "items": [{"id": normalized["assay_chembl_id"], "label": normalized["assay_chembl_id"], "url": normalized["url"]}]}]
    if normalized["target_chembl_id"]:
        groups.append({"database": "ChEMBL Target", "items": [{"id": normalized["target_chembl_id"], "label": normalized["target_chembl_id"], "url": normalized["target_url"]}]})
    if normalized["document_chembl_id"]:
        groups.append({"database": "ChEMBL Document", "items": [{"id": normalized["document_chembl_id"], "label": normalized["document_chembl_id"], "url": normalized["document_url"]}]})
    if normalized["bao_format"]:
        groups.append({"database": "BioAssay Ontology", "items": [{"id": normalized["bao_format"], "label": normalized["bao_label"] or normalized["bao_format"], "url": normalized["bao_url"]}]})
    return groups


def document_xref_groups(normalized: JsonObject) -> list[JsonObject]:
    groups = [{"database": "ChEMBL Document", "items": [{"id": normalized["document_chembl_id"], "label": normalized["document_chembl_id"], "url": normalized["url"]}]}]
    if normalized["pubmed_id"]:
        groups.append({"database": "PubMed", "items": [{"id": normalized["pubmed_id"], "label": f"PMID:{normalized['pubmed_id']}", "url": normalized["pubmed_url"]}]})
    if normalized["doi"]:
        groups.append({"database": "DOI", "items": [{"id": normalized["doi"], "label": normalized["doi"], "url": normalized["doi_url"]}]})
    if normalized["chembl_release"]:
        groups.append({"database": "ChEMBL Release", "items": [{"id": normalized["chembl_release"], "label": normalized["chembl_release"]}]})
    return groups


def molecule_xref_groups(normalized: JsonObject) -> list[JsonObject]:
    groups = [{"database": "ChEMBL", "items": [{"id": normalized["molecule_chembl_id"], "label": normalized["molecule_chembl_id"], "url": normalized["url"]}]}]
    if normalized["standard_inchi_key"]:
        groups.append({"database": "InChIKey", "items": [{"id": normalized["standard_inchi_key"], "label": normalized["standard_inchi_key"]}]})
    by_source: dict[str, list[JsonObject]] = {}
    for item in normalized["cross_references"]:
        by_source.setdefault(item["source"], []).append({"id": item["id"], "label": item["label"] or item["id"], "url": item.get("url", "")})
    for source, items in sorted(by_source.items()):
        groups.append({"database": source, "items": items})
    return groups


def activity_xref_groups(normalized: JsonObject) -> list[JsonObject]:
    return compact_entity_groups(normalized["activities"], [("Molecules", "molecule_chembl_id", "molecule_url", "molecule_pref_name"), ("Targets", "target_chembl_id", "target_url", "target_pref_name"), ("Assays", "assay_chembl_id", "assay_url", "assay_description"), ("Documents", "document_chembl_id", "document_url", "document_journal")])


def mechanism_xref_groups(normalized: JsonObject) -> list[JsonObject]:
    groups = compact_entity_groups(normalized["mechanisms"], [("Molecules", "molecule_chembl_id", "molecule_url", "molecule_chembl_id"), ("Targets", "target_chembl_id", "target_url", "target_chembl_id")])
    refs = []
    for mechanism in normalized["mechanisms"]:
        refs.extend(mechanism.get("refs", []))
    if refs:
        groups.append({"database": "References", "items": refs})
    return groups


def drug_indication_xref_groups(normalized: JsonObject) -> list[JsonObject]:
    groups = compact_entity_groups(
        normalized["indications"],
        [
            ("Molecules", "molecule_chembl_id", "molecule_url", "molecule_chembl_id"),
            ("EFO/HPO terms", "efo_id", "efo_url", "efo_term"),
            ("MeSH terms", "mesh_id", "mesh_url", "mesh_heading"),
        ],
    )
    refs = []
    for indication in normalized["indications"]:
        refs.extend(indication.get("refs", []))
    if refs:
        by_type: dict[str, list[JsonObject]] = {}
        for ref in refs:
            source = normalize_space(ref.get("source")) or "References"
            identifier = normalize_space(ref.get("id"))
            if not identifier:
                continue
            by_type.setdefault(source, []).append({"id": identifier, "label": normalize_space(ref.get("label")) or identifier, "url": normalize_space(ref.get("url"))})
        for source, items in sorted(by_type.items()):
            groups.append({"database": source, "items": deduplicate_items(items)[:30]})
    return groups


def compact_entity_groups(rows: list[JsonObject], specs: list[tuple[str, str, str, str]]) -> list[JsonObject]:
    groups = []
    for database, id_key, url_key, label_key in specs:
        seen: set[str] = set()
        items = []
        for row in rows:
            identifier = normalize_space(row.get(id_key))
            if not identifier or identifier in seen:
                continue
            seen.add(identifier)
            items.append({"id": identifier, "label": normalize_space(row.get(label_key)) or identifier, "url": normalize_space(row.get(url_key))})
        if items:
            groups.append({"database": database, "items": items})
    return groups


def deduplicate_items(items: list[JsonObject]) -> list[JsonObject]:
    rows = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = (normalize_space(item.get("id")), normalize_space(item.get("url")))
        if key in seen:
            continue
        seen.add(key)
        rows.append(item)
    return rows


def molecule_metadata(normalized: JsonObject) -> list[JsonObject]:
    properties = normalized["properties"]
    return compact_fields(
        ("ChEMBL ID", normalized["molecule_chembl_id"]),
        ("Name", normalized["pref_name"]),
        ("Type", normalized["molecule_type"]),
        ("Formula", properties.get("full_molformula")),
        ("Molecular weight", properties.get("full_mwt")),
        ("ALogP", properties.get("alogp")),
        ("Max phase", normalized["max_phase"]),
        ("First approval", normalized["first_approval"]),
        ("Therapeutic", yes_no(normalized["therapeutic_flag"])),
        ("Withdrawn", yes_no(normalized["withdrawn_flag"])),
    )


def target_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Target ID", normalized["target_chembl_id"]),
        ("Name", normalized["pref_name"]),
        ("Type", normalized["target_type"]),
        ("Organism", normalized["organism"]),
        ("TaxID", normalized["tax_id"]),
        ("Components", str(len(normalized["components"]))),
        ("Accessions", ", ".join(component["accession"] for component in normalized["components"] if component.get("accession"))),
    )


def assay_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Assay ID", normalized["assay_chembl_id"]),
        ("Type", normalized["assay_type_description"] or normalized["assay_type"]),
        ("Organism", normalized["organism"]),
        ("TaxID", normalized["tax_id"]),
        ("Target", normalized["target_chembl_id"]),
        ("Document", normalized["document_chembl_id"]),
        ("BAO format", normalized["bao_label"] or normalized["bao_format"]),
        ("Confidence", normalized["confidence_score"]),
        ("Relationship", normalized["relationship_description"] or normalized["relationship_type"]),
    )


def document_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("ChEMBL Document", normalized["document_chembl_id"]),
        ("PMID", normalized["pubmed_id"]),
        ("DOI", normalized["doi"]),
        ("Type", normalized["doc_type"]),
        ("Journal", normalized["journal_full_title"] or normalized["journal"]),
        ("Year", normalized["year"]),
        ("Authors", normalized["authors"]),
        ("Volume", normalized["volume"]),
        ("Issue", normalized["issue"]),
        ("Pages", document_pages(normalized)),
        ("ChEMBL release", normalized["chembl_release"]),
    )


def document_identifiers(normalized: JsonObject) -> JsonObject:
    identifiers: JsonObject = {
        "chembl_document": {
            "namespace": "chembl.document",
            "id": normalized["document_chembl_id"],
            "label": f"ChEMBL:{normalized['document_chembl_id']}",
            "url": normalized["url"],
        }
    }
    if normalized["pubmed_id"]:
        identifiers["pubmed"] = {"namespace": "pubmed", "id": normalized["pubmed_id"], "label": f"PMID:{normalized['pubmed_id']}", "url": normalized["pubmed_url"]}
    if normalized["doi"]:
        identifiers["doi"] = {"namespace": "doi", "id": normalized["doi"], "label": normalized["doi"], "url": normalized["doi_url"]}
    return identifiers


def molecule_description(normalized: JsonObject) -> str:
    properties = normalized["properties"]
    parts = [normalized["molecule_type"], properties.get("full_molformula"), f"MW {properties.get('full_mwt')}" if properties.get("full_mwt") else "", f"phase {normalized['max_phase']}" if normalized["max_phase"] else ""]
    return " | ".join(normalize_space(part) for part in parts if normalize_space(part))


def molecule_subtitle(normalized: JsonObject) -> str:
    return " | ".join(part for part in [normalized["molecule_chembl_id"], normalized["molecule_type"], f"phase {normalized['max_phase']}" if normalized["max_phase"] else ""] if part)


def document_chip_label(normalized: JsonObject) -> str:
    if normalized["pubmed_id"]:
        return f"PMID:{normalized['pubmed_id']}"
    if normalized["doi"]:
        return normalized["doi"]
    return normalized["document_chembl_id"]


def document_citation_text(normalized: JsonObject) -> str:
    parts = [
        normalized["journal"],
        normalized["year"],
        document_pages(normalized),
    ]
    return " | ".join(part for part in parts if part)


def document_pages(normalized: JsonObject) -> str:
    first = normalized["first_page"]
    last = normalized["last_page"]
    if first and last:
        return f"{first}-{last}"
    return first or last


def normalize_synonyms(value: object, *, max_synonyms: int) -> list[JsonObject]:
    rows = []
    seen: set[str] = set()
    for item in safe_list(value):
        if not isinstance(item, dict):
            continue
        synonym = normalize_space(item.get("molecule_synonym") or item.get("synonyms"))
        if not synonym or synonym.casefold() in seen:
            continue
        seen.add(synonym.casefold())
        rows.append({"synonym": synonym, "type": normalize_space(item.get("syn_type"))})
        if len(rows) >= max_synonyms:
            break
    return rows


def normalize_molecule_xrefs(value: object, *, max_xrefs: int) -> list[JsonObject]:
    rows = []
    for item in safe_list(value)[:max_xrefs]:
        if not isinstance(item, dict):
            continue
        rows.append({"id": normalize_space(item.get("xref_id")), "label": normalize_space(item.get("xref_name")), "source": normalize_space(item.get("xref_src")), "url": ""})
    return [row for row in rows if row["id"] or row["label"]]


def normalize_components(value: object, *, max_xrefs: int) -> list[JsonObject]:
    rows = []
    for item in safe_list(value):
        if not isinstance(item, dict):
            continue
        synonyms = []
        for synonym in safe_list(item.get("target_component_synonyms")):
            if isinstance(synonym, dict):
                text = normalize_space(synonym.get("component_synonym"))
                if text:
                    synonyms.append({"synonym": text, "type": normalize_space(synonym.get("syn_type"))})
        xrefs = []
        for xref in safe_list(item.get("target_component_xrefs"))[:max_xrefs]:
            if isinstance(xref, dict):
                xrefs.append({"id": normalize_space(xref.get("xref_id")), "label": normalize_space(xref.get("xref_name")), "source": normalize_space(xref.get("xref_src_db"))})
        rows.append({"accession": normalize_space(item.get("accession")), "description": normalize_space(item.get("component_description")), "component_type": normalize_space(item.get("component_type")), "relationship": normalize_space(item.get("relationship")), "synonyms": synonyms, "xrefs": xrefs})
    return rows


def component_xref_groups(components: list[JsonObject]) -> list[JsonObject]:
    groups = []
    accessions = [{"id": component["accession"], "label": component["accession"], "url": f"https://www.uniprot.org/uniprotkb/{urllib.parse.quote(component['accession'])}/entry"} for component in components if component.get("accession")]
    if accessions:
        groups.append({"database": "UniProt", "items": accessions})
    by_source: dict[str, list[JsonObject]] = {}
    for component in components:
        for xref in component.get("xrefs", []):
            source = normalize_space(xref.get("source"))
            identifier = normalize_space(xref.get("id"))
            if source and identifier:
                by_source.setdefault(source, []).append({"id": identifier, "label": normalize_space(xref.get("label")) or identifier})
    for source, items in sorted(by_source.items()):
        groups.append({"database": source, "items": items[:30]})
    return groups


def normalize_assay_parameters(value: object) -> list[JsonObject]:
    rows = []
    for item in safe_list(value):
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "name": normalize_space(item.get("standard_type") or item.get("parameter_name") or item.get("name")),
                "type": normalize_space(item.get("standard_type") or item.get("parameter_type") or item.get("type")),
                "relation": normalize_space(item.get("standard_relation") or item.get("relation")),
                "value": normalize_space(item.get("standard_value") or item.get("value")),
                "units": normalize_space(item.get("standard_units") or item.get("units")),
            }
        )
    return [row for row in rows if any(row.values())]


def normalize_assay_classifications(value: object) -> list[JsonObject]:
    rows = []
    for item in safe_list(value):
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "class_type": normalize_space(item.get("assay_class_type") or item.get("class_type")),
                "class_name": normalize_space(item.get("assay_classification") or item.get("class_name")),
                "description": normalize_space(item.get("description")),
            }
        )
    return [row for row in rows if any(row.values())]


def normalize_mechanism_refs(value: object) -> list[JsonObject]:
    rows = []
    for item in safe_list(value):
        if not isinstance(item, dict):
            continue
        rows.append({"id": normalize_space(item.get("ref_id")), "label": normalize_space(item.get("ref_type")) or normalize_space(item.get("ref_id")), "url": normalize_space(item.get("ref_url"))})
    return rows


def normalize_indication_refs(value: object) -> list[JsonObject]:
    rows = []
    for item in safe_list(value):
        if not isinstance(item, dict):
            continue
        ref_id = normalize_space(item.get("ref_id"))
        ref_type = normalize_space(item.get("ref_type"))
        rows.append(
            {
                "id": ref_id,
                "label": ref_type or ref_id,
                "source": ref_type,
                "url": normalize_space(item.get("ref_url")),
            }
        )
    return [row for row in rows if row["id"] or row["url"]]


def property_rows(properties: JsonObject) -> list[JsonObject]:
    labels = {
        "full_molformula": "Formula",
        "full_mwt": "Molecular weight",
        "alogp": "ALogP",
        "psa": "PSA",
        "hba": "HBA",
        "hbd": "HBD",
        "rtb": "Rotatable bonds",
        "aromatic_rings": "Aromatic rings",
        "heavy_atoms": "Heavy atoms",
        "num_ro5_violations": "Rule-of-five violations",
        "qed_weighted": "QED weighted",
    }
    return [{"property": key, "label": label, "value": properties[key]} for key, label in labels.items() if properties.get(key) is not None]


def assay_overview_rows(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Description", normalized["description"]),
        ("Type", normalized["assay_type_description"] or normalized["assay_type"]),
        ("Organism", normalized["organism"]),
        ("Tissue", normalized["tissue"]),
        ("Cell type", normalized["cell_type"]),
        ("BAO format", normalized["bao_label"] or normalized["bao_format"]),
        ("Confidence", normalized["confidence_description"] or normalized["confidence_score"]),
        ("Relationship", normalized["relationship_description"] or normalized["relationship_type"]),
        ("Target", normalized["target_chembl_id"]),
        ("Document", normalized["document_chembl_id"]),
    )


def property_keys() -> list[str]:
    return ["full_molformula", "full_mwt", "mw_freebase", "alogp", "psa", "hba", "hbd", "heavy_atoms", "aromatic_rings", "rtb", "num_ro5_violations", "qed_weighted", "np_likeness_score", "ro3_pass"]


def unique_values(rows: list[JsonObject], key: str, limit: int) -> list[str]:
    out = []
    seen: set[str] = set()
    for row in rows:
        value = normalize_space(row.get(key))
        if value and value not in seen:
            seen.add(value)
            out.append(value)
        if len(out) >= limit:
            break
    return out


def boolish(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value == 1:
            return True
        if value == 0:
            return False
    return None


def yes_no(value: object) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return ""


def chembl_molecule_url(molecule_id: str, website_base_url: str) -> str:
    return f"{website_base_url.rstrip('/')}/explore/compound/{urllib.parse.quote(molecule_id)}" if molecule_id else website_base_url.rstrip("/")


def chembl_target_url(target_id: str, website_base_url: str) -> str:
    return f"{website_base_url.rstrip('/')}/explore/target/{urllib.parse.quote(target_id)}" if target_id else website_base_url.rstrip("/")


def chembl_assay_url(assay_id: str, website_base_url: str) -> str:
    return f"{website_base_url.rstrip('/')}/explore/assay/{urllib.parse.quote(assay_id)}" if assay_id else website_base_url.rstrip("/")


def chembl_document_url(document_id: str, website_base_url: str) -> str:
    return f"{website_base_url.rstrip('/')}/explore/document/{urllib.parse.quote(document_id)}" if document_id else ""


def pubmed_url(pubmed_id: str) -> str:
    return f"https://pubmed.ncbi.nlm.nih.gov/{urllib.parse.quote(pubmed_id)}/" if pubmed_id else ""


def doi_url(doi: str) -> str:
    return f"https://doi.org/{urllib.parse.quote(doi, safe='/')}" if doi else ""


def chembl_search_url(query: str, website_base_url: str) -> str:
    return f"{website_base_url.rstrip('/')}/g/#search_results/all/query={urllib.parse.quote(query)}"


def activity_browser_url(params: JsonObject, website_base_url: str) -> str:
    molecule_id = normalize_space(params.get("molecule_chembl_id"))
    target_id = normalize_space(params.get("target_chembl_id"))
    if molecule_id:
        return chembl_molecule_url(molecule_id, website_base_url)
    if target_id:
        return chembl_target_url(target_id, website_base_url)
    return website_base_url.rstrip("/")


def mechanism_browser_url(params: JsonObject, website_base_url: str) -> str:
    return activity_browser_url(params, website_base_url)


def chembl_api_url(endpoint: str, api_base_url: str, params: JsonObject | None = None) -> str:
    url = f"{api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
    return url


def chembl_image_url(molecule_id: str, api_base_url: str, *, fmt: str = "png") -> str:
    return f"{api_base_url.rstrip('/')}/image/{urllib.parse.quote(molecule_id)}.{fmt}" if molecule_id else ""


def property_columns() -> list[JsonObject]:
    return [{"key": "label", "label": "Property"}, {"key": "value", "label": "Value"}]


def synonym_columns() -> list[JsonObject]:
    return [{"key": "synonym", "label": "Synonym"}, {"key": "type", "label": "Type"}]


def component_columns() -> list[JsonObject]:
    return [{"key": "accession", "label": "Accession"}, {"key": "description", "label": "Description"}, {"key": "component_type", "label": "Type"}, {"key": "relationship", "label": "Relationship"}]


def assay_parameter_columns() -> list[JsonObject]:
    return [{"key": "name", "label": "Name"}, {"key": "relation", "label": "Relation"}, {"key": "value", "label": "Value"}, {"key": "units", "label": "Units"}]


def assay_classification_columns() -> list[JsonObject]:
    return [{"key": "class_type", "label": "Type"}, {"key": "class_name", "label": "Class"}, {"key": "description", "label": "Description"}]


def activity_columns() -> list[JsonObject]:
    return [
        {"key": "molecule_chembl_id", "label": "Molecule"},
        {"key": "target_pref_name", "label": "Target"},
        {"key": "standard_type", "label": "Type"},
        {"key": "standard_relation", "label": "Relation"},
        {"key": "standard_value", "label": "Value"},
        {"key": "standard_units", "label": "Units"},
        {"key": "pchembl_value", "label": "pChEMBL"},
        {"key": "document_year", "label": "Year"},
    ]


def mechanism_columns() -> list[JsonObject]:
    return [
        {"key": "molecule_chembl_id", "label": "Molecule"},
        {"key": "target_chembl_id", "label": "Target"},
        {"key": "mechanism_of_action", "label": "Mechanism"},
        {"key": "action_type", "label": "Action"},
        {"key": "max_phase", "label": "Max phase"},
    ]


def drug_indication_columns() -> list[JsonObject]:
    return [
        {"key": "term", "label": "Indication"},
        {"key": "efo_id", "label": "EFO/HPO"},
        {"key": "mesh_id", "label": "MeSH"},
        {"key": "max_phase_for_ind", "label": "Max phase"},
        {"key": "drugind_id", "label": "Record ID"},
    ]


def ontology_term_url(term_id: str) -> str:
    return f"https://www.ebi.ac.uk/ols4/search?q={urllib.parse.quote(term_id)}" if term_id else ""


def mesh_url(mesh_id: str) -> str:
    return f"https://www.ncbi.nlm.nih.gov/mesh/{urllib.parse.quote(mesh_id)}" if mesh_id else ""


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
