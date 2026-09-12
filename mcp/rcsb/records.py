"""Front-end compatible record envelopes for RCSB PDB entries."""

from __future__ import annotations

from .constants import (
    RCSB_FILES_BASE_URL,
    RCSB_WEBSITE_BASE_URL,
    RECORD_SCHEMA_VERSION,
    JsonObject,
)
from .utils import first_value, normalize_space


def rcsb_structure_record(
    entry: JsonObject,
    *,
    polymer_entities: list[JsonObject] | None = None,
    nonpolymer_entities: list[JsonObject] | None = None,
    search_score: object = "",
) -> JsonObject:
    normalized = normalize_entry(
        entry,
        polymer_entities=polymer_entities or [],
        nonpolymer_entities=nonpolymer_entities or [],
        search_score=search_score,
    )
    pdb_id = normalized["pdb_id"]
    links = structure_links(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "protein.structure",
        "record_type": "rcsb_pdb_entry",
        "database": "rcsb_pdb",
        "id": pdb_id,
        "stable_id": f"PDB:{pdb_id}",
        "label": pdb_id,
        "title": normalized["title"] or pdb_id,
        "description": structure_description(normalized),
        "url": normalized["url"],
        "icon": "rcsb",
        "identifiers": structure_identifiers(normalized),
        "links": links,
        "display": {
            "component": "protein_structure",
            "chip_label": pdb_id,
            "icon": "rcsb",
            "title": normalized["title"] or pdb_id,
            "subtitle": " | ".join(
                part
                for part in [
                    ", ".join(normalized["methods"]),
                    resolution_text(normalized),
                    organism_text(normalized),
                ]
                if part
            ),
            "description": structure_description(normalized),
            "metadata": structure_metadata(normalized),
            "badges": compact_badges(
                ("RCSB PDB", "source"),
                (f"PDB:{pdb_id}", "identifier"),
                (", ".join(normalized["methods"]), "method"),
                (resolution_text(normalized), "quality"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": normalized["title"] or pdb_id,
                "subtitle": " | ".join(
                    part
                    for part in [
                        f"PDB:{pdb_id}",
                        ", ".join(normalized["methods"]),
                        resolution_text(normalized),
                    ]
                    if part
                ),
                "icon": "rcsb",
                "fields": compact_fields(
                    ("PDB ID", pdb_id),
                    ("Method", ", ".join(normalized["methods"])),
                    ("Resolution", resolution_text(normalized)),
                    ("Organism", organism_text(normalized)),
                    ("Polymer entities", str(len(normalized["polymer_entities"]))),
                    ("Ligands", ", ".join(normalized["ligand_ids"][:8])),
                    ("Released", normalized["initial_release_date"]),
                    ("Revised", normalized["revision_date"]),
                    ("PubMed", str(normalized["pubmed_id"]) if normalized["pubmed_id"] else ""),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": structure_sections(normalized),
            "previews": structure_previews(normalized),
        },
        "related": {
            "polymer_entities": normalized["polymer_entities"],
            "nonpolymer_entities": normalized["nonpolymer_entities"],
            "uniprot_ids": normalized["uniprot_ids"],
            "taxids": normalized["taxids"],
            "pubmed_id": normalized["pubmed_id"],
            "downloads": file_links(normalized),
        },
        "data": normalized,
    }


def rcsb_fasta_record(pdb_id: str, fasta_text: str) -> JsonObject:
    pdb_id = normalize_space(pdb_id).upper()
    sequence_count = sum(1 for line in fasta_text.splitlines() if line.startswith(">"))
    first_header = next((line[1:] for line in fasta_text.splitlines() if line.startswith(">")), "")
    url = structure_url(pdb_id)
    fasta_url = fasta_download_url(pdb_id)
    links = compact_links(
        link("RCSB PDB", url, primary=True),
        link("FASTA", fasta_url, kind="download"),
    )
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "protein.sequence",
        "record_type": "rcsb_pdb_fasta",
        "database": "rcsb_pdb",
        "id": pdb_id,
        "stable_id": f"PDB:{pdb_id}:FASTA",
        "label": pdb_id,
        "title": first_header or f"{pdb_id} FASTA",
        "description": f"{sequence_count} sequence records" if sequence_count else "FASTA",
        "url": url,
        "icon": "rcsb",
        "identifiers": {
            "pdb": {
                "namespace": "pdb",
                "id": pdb_id,
                "label": f"PDB:{pdb_id}",
                "url": url,
            }
        },
        "links": links,
        "display": {
            "component": "protein",
            "chip_label": f"{pdb_id} FASTA",
            "icon": "rcsb",
            "title": first_header or f"{pdb_id} FASTA",
            "subtitle": f"{sequence_count} sequence records" if sequence_count else "FASTA",
            "description": "",
            "metadata": compact_fields(
                ("PDB ID", pdb_id),
                ("Sequences", str(sequence_count) if sequence_count else ""),
                ("FASTA", fasta_url),
            ),
            "badges": compact_badges(
                ("RCSB PDB", "source"),
                ("FASTA", "format"),
                (f"PDB:{pdb_id}", "identifier"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": first_header or f"{pdb_id} FASTA",
                "subtitle": f"{sequence_count} sequence records" if sequence_count else "FASTA",
                "icon": "rcsb",
                "fields": compact_fields(
                    ("PDB ID", pdb_id),
                    ("Sequences", str(sequence_count) if sequence_count else ""),
                    ("URL", url),
                    ("FASTA", fasta_url),
                ),
            },
            "primary_url": url,
            "previews": [
                {
                    "kind": "sequence",
                    "title": "Entry FASTA",
                    "provider": "RCSB PDB",
                    "id": pdb_id,
                    "url": fasta_url,
                    "format": "fasta",
                    "mime_type": "text/x-fasta",
                    "section_key": "sequence",
                    "actions": display_actions(links),
                    "data": {
                        "alphabet": "protein",
                        "pdb_id": pdb_id,
                        "sequence_count": sequence_count,
                        "header": first_header,
                        "fasta": fasta_text,
                    },
                }
            ],
        },
        "data": {
            "pdb_id": pdb_id,
            "sequence_count": sequence_count,
            "header": first_header,
            "fasta": fasta_text,
        },
    }


def normalize_entry(
    entry: JsonObject,
    *,
    polymer_entities: list[JsonObject],
    nonpolymer_entities: list[JsonObject],
    search_score: object,
) -> JsonObject:
    pdb_id = normalize_space(entry.get("rcsb_id")).upper()
    struct = entry.get("struct") if isinstance(entry.get("struct"), dict) else {}
    entry_info = entry.get("rcsb_entry_info") if isinstance(entry.get("rcsb_entry_info"), dict) else {}
    accession = entry.get("rcsb_accession_info") if isinstance(entry.get("rcsb_accession_info"), dict) else {}
    identifiers = (
        entry.get("rcsb_entry_container_identifiers")
        if isinstance(entry.get("rcsb_entry_container_identifiers"), dict)
        else {}
    )
    normalized_entities = [normalize_polymer_entity(item) for item in polymer_entities]
    normalized_nonpolymers = [normalize_nonpolymer_entity(item) for item in nonpolymer_entities]
    citations = normalize_citations(entry.get("citation"))
    return {
        "pdb_id": pdb_id,
        "title": normalize_space(struct.get("title")),
        "methods": normalize_methods(entry, entry_info),
        "experimental_method": normalize_space(entry_info.get("experimental_method")),
        "resolution": normalize_resolution(entry_info),
        "molecular_weight": entry_info.get("molecular_weight", ""),
        "polymer_composition": normalize_space(entry_info.get("polymer_composition")),
        "selected_polymer_entity_types": normalize_space(entry_info.get("selected_polymer_entity_types")),
        "nonpolymer_bound_components": entry_info.get("nonpolymer_bound_components")
        if isinstance(entry_info.get("nonpolymer_bound_components"), list)
        else [],
        "assembly_ids": identifiers.get("assembly_ids") if isinstance(identifiers.get("assembly_ids"), list) else [],
        "polymer_entity_ids": identifiers.get("polymer_entity_ids")
        if isinstance(identifiers.get("polymer_entity_ids"), list)
        else [],
        "nonpolymer_entity_ids": identifiers.get("non_polymer_entity_ids")
        if isinstance(identifiers.get("non_polymer_entity_ids"), list)
        else [],
        "pubmed_id": identifiers.get("pubmed_id", ""),
        "initial_release_date": date_text(accession.get("initial_release_date")),
        "revision_date": date_text(accession.get("revision_date")),
        "deposit_date": date_text(accession.get("deposit_date")),
        "status": normalize_space(accession.get("status_code")),
        "url": structure_url(pdb_id),
        "polymer_entities": normalized_entities,
        "nonpolymer_entities": normalized_nonpolymers,
        "ligand_ids": ligand_ids(normalized_nonpolymers, entry_info),
        "uniprot_ids": sorted(
            {
                uniprot_id
                for entity in normalized_entities
                for uniprot_id in entity.get("uniprot_ids", [])
                if uniprot_id
            }
        ),
        "taxids": sorted(
            {
                taxid
                for entity in normalized_entities
                for taxid in entity.get("taxids", [])
                if taxid
            }
        ),
        "organisms": sorted(
            {
                organism
                for entity in normalized_entities
                for organism in entity.get("organisms", [])
                if organism
            }
        ),
        "citations": citations,
        "primary_citation": next((item for item in citations if item.get("primary")), citations[0] if citations else {}),
        "search_score": search_score,
    }


def normalize_polymer_entity(entity: JsonObject) -> JsonObject:
    entity_poly = entity.get("entity_poly") if isinstance(entity.get("entity_poly"), dict) else {}
    polymer = entity.get("rcsb_polymer_entity") if isinstance(entity.get("rcsb_polymer_entity"), dict) else {}
    identifiers = (
        entity.get("rcsb_polymer_entity_container_identifiers")
        if isinstance(entity.get("rcsb_polymer_entity_container_identifiers"), dict)
        else {}
    )
    organisms = entity.get("rcsb_entity_source_organism")
    if not isinstance(organisms, list):
        organisms = []
    taxids = [
        item.get("ncbi_taxonomy_id")
        for item in organisms
        if isinstance(item, dict) and item.get("ncbi_taxonomy_id")
    ]
    organism_names = [
        normalize_space(item.get("scientific_name") or item.get("ncbi_scientific_name"))
        for item in organisms
        if isinstance(item, dict)
    ]
    genes = []
    for item in organisms:
        if not isinstance(item, dict):
            continue
        for gene in item.get("rcsb_gene_name", []):
            if isinstance(gene, dict):
                genes.append(normalize_space(gene.get("value")))
    return {
        "entity_id": normalize_space(identifiers.get("entity_id")),
        "rcsb_id": normalize_space(entity.get("rcsb_id")),
        "description": normalize_space(polymer.get("pdbx_description")),
        "type": normalize_space(entity_poly.get("rcsb_entity_polymer_type") or entity_poly.get("type")),
        "sequence_length": entity_poly.get("rcsb_sample_sequence_length", ""),
        "sequence": normalize_space(entity_poly.get("pdbx_seq_one_letter_code_can")),
        "chains": identifiers.get("auth_asym_ids") if isinstance(identifiers.get("auth_asym_ids"), list) else [],
        "asym_ids": identifiers.get("asym_ids") if isinstance(identifiers.get("asym_ids"), list) else [],
        "uniprot_ids": identifiers.get("uniprot_ids") if isinstance(identifiers.get("uniprot_ids"), list) else [],
        "organisms": [item for item in organism_names if item],
        "taxids": taxids,
        "genes": [gene for gene in genes if gene],
        "formula_weight": polymer.get("formula_weight", ""),
    }


def normalize_nonpolymer_entity(entity: JsonObject) -> JsonObject:
    nonpolymer = entity.get("pdbx_entity_nonpoly") if isinstance(entity.get("pdbx_entity_nonpoly"), dict) else {}
    identifiers = (
        entity.get("rcsb_nonpolymer_entity_container_identifiers")
        if isinstance(entity.get("rcsb_nonpolymer_entity_container_identifiers"), dict)
        else {}
    )
    return {
        "entity_id": normalize_space(identifiers.get("entity_id") or nonpolymer.get("entity_id")),
        "rcsb_id": normalize_space(entity.get("rcsb_id")),
        "comp_id": normalize_space(identifiers.get("nonpolymer_comp_id") or nonpolymer.get("comp_id")),
        "name": normalize_space(nonpolymer.get("name")),
        "chains": identifiers.get("auth_asym_ids") if isinstance(identifiers.get("auth_asym_ids"), list) else [],
        "asym_ids": identifiers.get("asym_ids") if isinstance(identifiers.get("asym_ids"), list) else [],
    }


def normalize_citations(citations: object) -> list[JsonObject]:
    if not isinstance(citations, list):
        return []
    normalized = []
    for citation in citations:
        if not isinstance(citation, dict):
            continue
        normalized.append(
            {
                "id": normalize_space(citation.get("id")),
                "title": normalize_space(citation.get("title")),
                "journal": normalize_space(citation.get("rcsb_journal_abbrev") or citation.get("journal_abbrev")),
                "year": citation.get("year", ""),
                "doi": normalize_space(citation.get("pdbx_database_id_DOI")),
                "pmid": citation.get("pdbx_database_id_PubMed", ""),
                "authors": citation.get("rcsb_authors") if isinstance(citation.get("rcsb_authors"), list) else [],
                "primary": normalize_space(citation.get("rcsb_is_primary")).upper() == "Y",
            }
        )
    return normalized


def normalize_methods(entry: JsonObject, entry_info: JsonObject) -> list[str]:
    methods = []
    experiments = entry.get("exptl")
    if isinstance(experiments, list):
        methods.extend(
            normalize_space(item.get("method"))
            for item in experiments
            if isinstance(item, dict)
        )
    if not methods and entry_info.get("experimental_method"):
        methods.append(normalize_space(entry_info.get("experimental_method")))
    return [method for method in methods if method]


def normalize_resolution(entry_info: JsonObject) -> float | str:
    combined = entry_info.get("resolution_combined")
    value = first_value(combined)
    if value:
        return value
    resolution = entry_info.get("diffrn_resolution_high")
    if isinstance(resolution, dict) and resolution.get("value"):
        return resolution.get("value")
    return ""


def ligand_ids(nonpolymers: list[JsonObject], entry_info: JsonObject) -> list[str]:
    ids = [normalize_space(item.get("comp_id")) for item in nonpolymers]
    if not ids and isinstance(entry_info.get("nonpolymer_bound_components"), list):
        ids = [normalize_space(item) for item in entry_info.get("nonpolymer_bound_components", [])]
    return sorted({item for item in ids if item})


def structure_identifiers(normalized: JsonObject) -> JsonObject:
    pdb_id = normalized["pdb_id"]
    identifiers: JsonObject = {
        "pdb": {
            "namespace": "pdb",
            "id": pdb_id,
            "label": f"PDB:{pdb_id}",
            "url": structure_url(pdb_id),
        }
    }
    if normalized["uniprot_ids"]:
        identifiers["uniprot"] = [
            {
                "namespace": "uniprotkb",
                "id": uniprot_id,
                "label": f"UniProtKB:{uniprot_id}",
                "url": uniprot_url(uniprot_id),
            }
            for uniprot_id in normalized["uniprot_ids"]
        ]
    if normalized["taxids"]:
        identifiers["taxonomy"] = [
            {
                "namespace": "taxonomy",
                "id": str(taxid),
                "label": f"TaxID:{taxid}",
                "url": taxonomy_url(taxid),
            }
            for taxid in normalized["taxids"]
        ]
    if normalized["pubmed_id"]:
        identifiers["pubmed"] = {
            "namespace": "pubmed",
            "id": str(normalized["pubmed_id"]),
            "label": f"PMID:{normalized['pubmed_id']}",
            "url": pubmed_url(normalized["pubmed_id"]),
        }
    return identifiers


def structure_links(normalized: JsonObject) -> list[JsonObject]:
    pdb_id = normalized["pdb_id"]
    links = [
        link("RCSB PDB", structure_url(pdb_id), primary=True),
        *file_links(normalized),
    ]
    if normalized["pubmed_id"]:
        links.append(link("PubMed", pubmed_url(normalized["pubmed_id"]), kind="related"))
    for uniprot_id in normalized["uniprot_ids"][:4]:
        links.append(link(f"UniProtKB {uniprot_id}", uniprot_url(uniprot_id), kind="related"))
    return compact_links(*links)


def file_links(normalized: JsonObject) -> list[JsonObject]:
    pdb_id = normalized["pdb_id"]
    return compact_links(
        link("PDB file", pdb_download_url(pdb_id), kind="download"),
        link("mmCIF", cif_download_url(pdb_id), kind="download"),
        link("FASTA", fasta_download_url(pdb_id), kind="download"),
    )


def structure_previews(normalized: JsonObject) -> list[JsonObject]:
    pdb_id = normalized["pdb_id"]
    previews: list[JsonObject] = [
        {
            "kind": "structure_3d",
            "title": "Experimental 3D structure",
            "provider": "RCSB PDB",
            "id": pdb_id,
            "url": structure_url(pdb_id),
            "format": "pdb_entry",
            "section_key": "overview",
            "actions": display_actions(structure_links(normalized)),
            "data": {
                "pdb_id": pdb_id,
                "method": ", ".join(normalized["methods"]),
                "resolution": normalized["resolution"],
                "pdb_url": pdb_download_url(pdb_id),
                "cif_url": cif_download_url(pdb_id),
                "fasta_url": fasta_download_url(pdb_id),
                "assembly_ids": normalized["assembly_ids"],
            },
        },
        {
            "kind": "download_manifest",
            "title": "Structure files",
            "provider": "RCSB PDB",
            "id": pdb_id,
            "url": structure_url(pdb_id),
            "section_key": "downloads",
            "actions": display_actions(file_links(normalized)),
            "data": {
                "files": file_links(normalized),
            },
        },
    ]
    if normalized["polymer_entities"]:
        previews.append(
            {
                "kind": "table",
                "title": "Polymer entities",
                "provider": "RCSB PDB",
                "id": pdb_id,
                "section_key": "polymer_entities",
                "data": {
                    "columns": [
                        {"key": "entity_id", "label": "Entity"},
                        {"key": "description", "label": "Description"},
                        {"key": "chains", "label": "Chains"},
                        {"key": "uniprot_ids", "label": "UniProt"},
                    ],
                    "rows": normalized["polymer_entities"],
                },
            }
        )
    if normalized["citations"]:
        previews.append(
            {
                "kind": "citation_list",
                "title": "Structure citations",
                "provider": "RCSB PDB/PubMed",
                "id": pdb_id,
                "url": pubmed_url(normalized["pubmed_id"]) if normalized["pubmed_id"] else structure_url(pdb_id),
                "section_key": "citations",
                "data": {
                    "references": normalized["citations"][:10],
                    "pubmed_ids": [str(normalized["pubmed_id"])] if normalized["pubmed_id"] else [],
                    "count": len(normalized["citations"]),
                },
            }
        )
    return previews


def structure_sections(normalized: JsonObject) -> list[JsonObject]:
    sections: list[JsonObject] = [
        {
            "key": "overview",
            "title": "Overview",
            "kind": "fields",
            "fields": structure_metadata(normalized),
        },
        {
            "key": "downloads",
            "title": "Downloads",
            "kind": "table",
            "rows": file_links(normalized),
        },
    ]
    if normalized["polymer_entities"]:
        sections.append(
            {
                "key": "polymer_entities",
                "title": "Polymer entities",
                "kind": "table",
                "rows": normalized["polymer_entities"],
            }
        )
    if normalized["nonpolymer_entities"]:
        sections.append(
            {
                "key": "ligands",
                "title": "Ligands and non-polymer entities",
                "kind": "table",
                "rows": normalized["nonpolymer_entities"],
            }
        )
    if normalized["citations"]:
        sections.append(
            {
                "key": "citations",
                "title": "Citations",
                "kind": "references",
                "items": normalized["citations"],
            }
        )
    return sections


def structure_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("PDB ID", normalized["pdb_id"]),
        ("Title", normalized["title"]),
        ("Method", ", ".join(normalized["methods"])),
        ("Resolution", resolution_text(normalized)),
        ("Polymer composition", normalized["polymer_composition"]),
        ("Polymer type", normalized["selected_polymer_entity_types"]),
        ("Organism", organism_text(normalized)),
        ("UniProt", ", ".join(normalized["uniprot_ids"][:8])),
        ("Ligands", ", ".join(normalized["ligand_ids"][:8])),
        ("Molecular weight", numeric_text(normalized["molecular_weight"], suffix=" kDa")),
        ("Released", normalized["initial_release_date"]),
        ("Revised", normalized["revision_date"]),
        ("PubMed", str(normalized["pubmed_id"]) if normalized["pubmed_id"] else ""),
        ("Search score", numeric_text(normalized["search_score"])),
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


def structure_description(normalized: JsonObject) -> str:
    return " | ".join(
        part
        for part in [
            ", ".join(normalized["methods"]),
            resolution_text(normalized),
            organism_text(normalized),
        ]
        if part
    )


def resolution_text(normalized: JsonObject) -> str:
    value = normalized.get("resolution")
    if value in {"", None}:
        return ""
    return f"{numeric_text(value)} A"


def organism_text(normalized: JsonObject) -> str:
    return ", ".join(normalized.get("organisms", [])[:3])


def numeric_text(value: object, *, suffix: str = "") -> str:
    if value in {"", None}:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".") + suffix
    if isinstance(value, int):
        return f"{value}{suffix}"
    return normalize_space(value)


def date_text(value: object) -> str:
    text = normalize_space(value)
    return text.split("T", 1)[0] if "T" in text else text


def structure_url(pdb_id: str) -> str:
    pdb_id = normalize_space(pdb_id).upper()
    return f"{RCSB_WEBSITE_BASE_URL}/structure/{pdb_id}" if pdb_id else ""


def pdb_download_url(pdb_id: str) -> str:
    pdb_id = normalize_space(pdb_id).upper()
    return f"{RCSB_FILES_BASE_URL}/download/{pdb_id}.pdb" if pdb_id else ""


def cif_download_url(pdb_id: str) -> str:
    pdb_id = normalize_space(pdb_id).upper()
    return f"{RCSB_FILES_BASE_URL}/download/{pdb_id}.cif" if pdb_id else ""


def fasta_download_url(pdb_id: str) -> str:
    pdb_id = normalize_space(pdb_id).upper()
    return f"{RCSB_WEBSITE_BASE_URL}/fasta/entry/{pdb_id}/download" if pdb_id else ""


def uniprot_url(accession: str) -> str:
    accession = normalize_space(accession)
    return f"https://www.uniprot.org/uniprotkb/{accession}/entry" if accession else ""


def taxonomy_url(taxid: object) -> str:
    value = normalize_space(taxid)
    return (
        "https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id="
        f"{value}"
    ) if value else ""


def pubmed_url(pmid: object) -> str:
    value = normalize_space(pmid)
    return f"https://pubmed.ncbi.nlm.nih.gov/{value}/" if value else ""

